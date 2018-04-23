# -*- coding: utf8 -*-
import uuid

from playhouse.shortcuts import model_to_dict, dict_to_model
from redis import exceptions
from wanx.models import BaseModel
from wanx.base.xredis import Redis
from wanx.base.xmysql import MYDB
from wanx.base import error, util, const
from wanx.models.credit import UserCredit, TRADE_ACTION
from wanx.models.product import Product, UserProduct
from wanx.models.user import User
from wanx.base.xmongo import DB
from wanx.models import Document

import cPickle as cjson
import peewee as pw
from datetime import datetime,timedelta
import time


ONSALE_GIFT_KEY = 'gift:onsale'
ALL_GIFT_KEY = 'gift:all'
VIDEO_GIFT_KEY = 'gift:video:%s'
TOP_SENDER_KEY = 'gift:top_senders:%s'
USER_TOTAL_GOLD = 'user:total:gold:%(uid)s'

CREDIT_TYPE = (
    (const.SALE_GEM, u'游票价格'),
    (const.SALE_GOLD, u'游米价格'),
    (const.DAILY_FREE, u'每日免费次数'),
)

GIFT_FROM = (
    (const.FROM_LIVE, '直播'),
    (const.FROM_RECORD, '录播'),
)

EXCHANGE_STATUS = (
    (const.OFFLINE, u'下线'),
    (const.ONLINE, u'上线'),
)

EXCHANGE_RESULT = (
    (const.SUCCESS, u'成功'),
    (const.FAIL, u'失败'),
)


class Gift(BaseModel):
    gift_id = pw.PrimaryKeyField(verbose_name='礼物ID')
    product_id = pw.IntegerField(verbose_name='物品ID')
    credit_type = pw.IntegerField(choices=CREDIT_TYPE, verbose_name='价格类型')
    credit_value = pw.IntegerField(verbose_name='价格数值')
    per_piece_limit = pw.CharField(verbose_name='单用户各档位:大厅id(1:id1,10:id2)')
    order_num = pw.IntegerField(verbose_name='显示顺序')
    os = pw.CharField(max_length=64, verbose_name='平台要求')
    version_code_max = pw.CharField(max_length=64, verbose_name='版本要求(版本号小于等于)')
    version_code_mix = pw.CharField(max_length=64, verbose_name='版本要求(版本号大于等于)')
    on_sale = pw.BooleanField(default=True, verbose_name='是否在售')

    class Meta:
        db_table = 'gift'
        constraints = [pw.Check('credit_value > 0')]

    @classmethod
    @util.cached_object(ALL_GIFT_KEY)
    def _load_all_gifts(cls):
        gifts = list(cls.select())
        gifts = [model_to_dict(gf) for gf in gifts]
        return gifts

    @classmethod
    def get_all_gifts(cls):
        gifts = Redis.get(ALL_GIFT_KEY)
        if not gifts:
            gifts = cls._load_all_gifts()
        else:
            gifts = cjson.loads(gifts)

        gifts = [dict_to_model(Gift, gf) for gf in gifts]
        return gifts

    @classmethod
    @util.cached_object(ONSALE_GIFT_KEY)
    def _load_onsale_gifts(cls):
        gifts = list(cls.select().where(Gift.on_sale == True))
        gifts = [model_to_dict(gf) for gf in gifts]
        return gifts

    @classmethod
    def get_onsale_gifts(cls):
        gifts = Redis.get(ONSALE_GIFT_KEY)
        if not gifts:
            gifts = cls._load_onsale_gifts()
        else:
            gifts = cjson.loads(gifts)

        gifts = [dict_to_model(Gift, gf) for gf in gifts]
        return gifts

    @classmethod
    def get_free_gifts(cls):
        gifts = filter(lambda x: x.credit_type == const.DAILY_FREE, cls.get_onsale_gifts())
        return gifts

    @classmethod
    def get_gift(cls, gift_id):
        gifts = filter(lambda x: x.gift_id == gift_id, cls.get_onsale_gifts())
        return gifts[0] if gifts else None

    @classmethod
    def get_gift_by_product_id(cls, product_id):
        gifts = filter(lambda x: x.product_id == product_id, cls.get_all_gifts())
        return gifts[0] if gifts else None

    def format(self):
        data = model_to_dict(self)
        if self.credit_type == const.MONEY and data.get("per_piece_limit"):
            data['per_piece_id'] = {
                int(k_v.split(":")[0]): k_v.split(":")[1] for k_v in self.per_piece_limit.split(",") if k_v}
        product = Product.get_product(self.product_id)
        if product:
            data.update(product.format())
        return data

    @property
    def gold_price(self):
        if self.credit_type == const.DAILY_FREE:
            return 100
        elif self.credit_type == const.SALE_GOLD:
            return self.credit_value
        elif self.credit_type == const.SALE_GEM:
            return self.credit_value * 100
        elif self.credit_type == const.MONEY:
            return self.credit_value
        return 0

    def send_to_user(self, from_user, to_user, num, gift_from, from_id,**kwargs):
        if num < 1:
            return error.InvalidArguments

        uc = from_user_uc = UserCredit.get_or_create_user_credit(from_user)
        product = Product.get_product(self.product_id)
        if self.credit_type == const.SALE_GOLD:
            total_gold = self.credit_value * num
            if uc.gold < total_gold:
                return error.GiftError('你的游米不足，做任务可获取游米')

            with MYDB.atomic():
                uc.reduce_gold(total_gold, const.GIFT)
                product.add_product2user(to_user, num, const.GIFT)
                UserGiftLog.create(
                    user_id=to_user,
                    from_user=from_user,
                    product_id=self.product_id,
                    credit_type=self.credit_type,
                    credit_value=self.credit_value,
                    num=num,
                    gold_price=self.gold_price * num,
                    gift_from=gift_from,
                    from_id=from_id,
                    send_success=1)
        elif self.credit_type == const.SALE_GEM:
            total_gem = self.credit_value * num
            if uc.gem < total_gem:
                return error.GiftError('你的游票不足')

            with MYDB.atomic():
                uc.reduce_gem(total_gem, const.GIFT)
                product.add_product2user(to_user, num, const.GIFT)
                UserGiftLog.create(
                    user_id=to_user,
                    from_user=from_user,
                    product_id=self.product_id,
                    credit_type=self.credit_type,
                    credit_value=self.credit_value,
                    num=num,
                    gold_price=self.gold_price * num,
                    gift_from=gift_from,
                    from_id=from_id,
                    send_success=1)
        elif self.credit_type == const.DAILY_FREE:
            from_up = UserProduct.get_or_create_user_product(from_user, self.product_id)
            if from_up.gift_free < num:
                return error.GiftError('对不起，您今天的免费礼物已用完')

            with MYDB.atomic():
                from_up.gift_free -= num
                from_up.save()
                product.add_product2user(to_user, num, const.GIFT)
                UserGiftLog.create(
                    user_id=to_user,
                    from_user=from_user,
                    product_id=self.product_id,
                    credit_type=self.credit_type,
                    credit_value=self.credit_value,
                    num=num,
                    gold_price=self.gold_price * num,
                    gift_from=gift_from,
                    from_id=from_id,
                    send_success=1)
        elif self.credit_type == const.MONEY:
            # 请求支付 
            with MYDB.atomic():
                # uc.reduce_gem(total_gem, const.GIFT)
                # 
                send_success = kwargs.get("send_success",0)
                if not send_success:
                    UserGiftLog.create(
                        user_id=to_user,
                        from_user=from_user,
                        product_id=self.product_id,
                        credit_type=self.credit_type,
                        credit_value=self.credit_value,
                        num=num,
                        gold_price=self.gold_price * num,
                        gift_from=gift_from,
                        from_id=from_id,
                        gift_id=self.gift_id,
                        send_success=0,
                        transaction_id=kwargs.get("transactionId"))
                else:
                    total_money = self.gold_price * num
                    from_user_uc.add_cost_money(total_money)
                    to_user_uc = UserCredit.get_or_create_user_credit(to_user)
                    to_user_uc.add_get_money(total_money)
                    # 状态为1
                    log = UserGiftLog.get_by_transaction_id(kwargs.get("transactionId"))
                    if not log:
                        return error.GiftError('未发现支付记录')
                    log.send_success = 1
                    log.save()
                    # redis 更新
                    UserGiftLog.update_redis_gift(log)
                    product.add_product2user(to_user, num, const.GIFT,extra={"is_money":True})
        return True


class UserGiftLog(BaseModel):
    user_id = pw.CharField(max_length=64, verbose_name='用户ID')
    from_user = pw.CharField(max_length=64, verbose_name='赠送者ID')
    product_id = pw.IntegerField(verbose_name='物品ID')
    credit_type = pw.IntegerField(choices=CREDIT_TYPE, verbose_name='价格类型')
    credit_value = pw.IntegerField(verbose_name='价格数值')
    num = pw.IntegerField(verbose_name='赠送数量')
    gold_price = pw.IntegerField(verbose_name='折算为游米价格')
    gift_from = pw.IntegerField(choices=GIFT_FROM, verbose_name='礼物来源')
    from_id = pw.CharField(max_length=64, verbose_name='来源ID(视频ID、直播ID)')
    gift_id = pw.IntegerField(verbose_name='礼物ID')
    send_success = pw.IntegerField(verbose_name='人民币礼物赠送是否成功') # 赠送人民币礼物，要一开始就记录。
    transaction_id = pw.CharField(max_length=64,verbose_name='订单号') # 当时人民币礼物的时候，需用订单号对应

    class Meta:
        db_table = 'user_gift_log'

    @classmethod
    def get_user_logs(cls, user_id, mode, page, pagesize):
        if mode == 1:
            logs = list(cls.select(
                pw.fn.max(cls.create_at).alias('create_at'),
                cls.product_id,
                cls.user_id,
                cls.credit_type,
                cls.credit_value,
                cls.send_success,
                pw.fn.Sum(cls.num).alias('daily_sum')
            ).where(
                cls.from_user == user_id
            ).order_by(
                cls.create_at.desc()
            ).group_by(
                cls.create_at.year,
                cls.create_at.month,
                cls.create_at.day,
                cls.user_id,
                cls.product_id,
                cls.send_success
            ).paginate(page, pagesize))
        elif mode == 2:
            logs = list(cls.select(
                pw.fn.max(cls.create_at).alias('create_at'),
                cls.product_id,
                cls.from_user,
                cls.credit_type,
                cls.credit_value,
                cls.send_success,
                pw.fn.Sum(cls.num).alias('daily_sum')
            ).where(
                cls.user_id == user_id
            ).order_by(
                cls.create_at.desc()
            ).group_by(
                cls.create_at.year,
                cls.create_at.month,
                cls.create_at.day,
                cls.from_user,
                cls.product_id,
                cls.send_success
            ).paginate(page, pagesize))
        else:
            logs = []
        return logs

    @classmethod
    def user_today_gift_id_times(cls, user_id, gift_id,num):
        #该档位送了几次
        start_time = datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
        end_time = start_time+timedelta(days=1)
        times = cls.select().where(cls.gift_id == gift_id, 
                                    cls.user_id ==user_id,
                                    cls.create_at >= start_time,
                                    cls.create_at < end_time,
                                    cls.num == num,
                            ).count()
        return times

    @classmethod
    def get_by_transaction_id(cls, transaction_id):
        logs = list(cls.select().where(cls.transaction_id == transaction_id))
        if len(logs)>=1:
            return logs[0]
        else:
            return {}


    def format_log(self):
        product = Product.get_product(self.product_id)
        uid = self.user_id if 'user_id' in self.__dict__['_data'] else self.from_user
        user = User.get_one(uid)
        data = {
            'user': user and user.format(exclude_fields=['is_followed']),
            'product': product and product.format(),
            'num': self.daily_sum,
            'credit_type':self.credit_type,
            'credit_value':self.credit_value,
            'send_success':self.send_success,
            'create_at': util.datetime2timestamp(self.create_at)
        }
        return data

    @classmethod
    @util.cached_zset(lambda cls, video_id: VIDEO_GIFT_KEY % (video_id))
    def _load_video_gifts(cls, video_id):
        gifts = list(cls.select().where(
            UserGiftLog.gift_from == const.FROM_RECORD,
            UserGiftLog.from_id == video_id,
            UserGiftLog.send_success == 1,
        ))
        ret = list()
        for gift in gifts:
            ret.extend([util.datetime2timestamp(gift.create_at), cjson.dumps(gift, 2)])

        return tuple(ret)

    @classmethod
    def get_video_gifts(cls, video_id, maxs=None, pagesize=None):
        key = VIDEO_GIFT_KEY % (video_id)
        if not Redis.exists(key):
            cls._load_video_gifts(video_id)
        try:
            # 不进行分页
            if pagesize is None and maxs is None:
                return Redis.zrevrange(key, 0, -1)
            gifts = Redis.zrevrangebyscore(key, '(%.6f' % (maxs), '-inf', start=0, num=pagesize)
        except exceptions.ResponseError:
            gifts = []

        return [cjson.loads(gf) for gf in gifts]

    @classmethod
    @util.cached_zset(lambda cls, user_id: TOP_SENDER_KEY % (user_id))
    def _load_top_sender_ids(cls, user_id):
        total_gold = pw.fn.Sum(UserGiftLog.gold_price)
        senders = cls.select(
            UserGiftLog.from_user,
            total_gold.alias('gold')
        ).where(UserGiftLog.user_id == user_id).group_by(UserGiftLog.from_user)
        ret = list()
        for sender in senders:
            ret.extend([sender.gold, sender.from_user])

        return tuple(ret)

    @classmethod
    def get_top_sender_ids(cls, user_id, page=None, pagesize=None):
        key = TOP_SENDER_KEY % (user_id)
        if not Redis.exists(key):
            cls._load_top_sender_ids(user_id)

        start = (page - 1) * pagesize if page else 0
        stop = (start + pagesize - 1) if pagesize else -1
        try:
            uids = Redis.zrevrange(key, start, stop, withscores=True)
        except exceptions.ResponseError:
            uids = []

        return list(uids)

    @classmethod
    def get_user_total_gold(cls, uid, begin_at, end_at):
        key = USER_TOTAL_GOLD % ({'uid': uid})
        total_gold = Redis.get(key)
        if not total_gold:
            total_gold = pw.fn.Sum(UserGiftLog.gold_price)
            total_gold = cls.select(
                total_gold.alias('gold')
            ).where(UserGiftLog.user_id == uid,
                    UserGiftLog.gift_from == const.FROM_LIVE,
                    UserGiftLog.create_at > datetime.fromtimestamp(int(begin_at)),
                    UserGiftLog.create_at < datetime.fromtimestamp(int(end_at)))
            total_gold = total_gold.get()
            total_gold = 0 if not total_gold.gold else total_gold.gold
            Redis.setex(key, 86400, total_gold)
        return int(total_gold)

    @classmethod
    def create(cls, **query):
        inst = super(UserGiftLog, cls).create(**query)
        if inst:
            if inst.gift_from == const.FROM_RECORD:
                key = VIDEO_GIFT_KEY % (inst.from_id)
                try:
                    if Redis.exists(key) and query.get("send_success"):
                        Redis.zadd(key, util.datetime2timestamp(inst.create_at),
                                   cjson.dumps(inst, 2))
                except exceptions.ResponseError:
                    Redis.delete(key)

            key = TOP_SENDER_KEY % (inst.user_id)
            try:
                if Redis.exists(key) and query.get("send_success"):
                    Redis.zincrby(key, inst.gold_price, inst.from_user)
            except exceptions.ResponseError:
                Redis.delete(key)

            if inst.gift_from == const.FROM_LIVE:
                key = USER_TOTAL_GOLD % ({'uid': inst.user_id})
                Redis.delete(key)

        return inst

    @classmethod
    def update_redis_gift(cls, inst):
        if inst:
            if inst.gift_from == const.FROM_RECORD:
                key = VIDEO_GIFT_KEY % (inst.from_id)
                try:
                    if Redis.exists(key) and inst.send_success:
                        Redis.zadd(key, util.datetime2timestamp(inst.create_at),
                                   cjson.dumps(inst, 2))
                except exceptions.ResponseError:
                    Redis.delete(key)

            key = TOP_SENDER_KEY % (inst.user_id)
            try:
                if Redis.exists(key) and inst.send_success:
                    Redis.zincrby(key, inst.gold_price, inst.from_user)
            except exceptions.ResponseError:
                Redis.delete(key)

            if inst.gift_from == const.FROM_LIVE:
                key = USER_TOTAL_GOLD % ({'uid': inst.user_id})
                Redis.delete(key)

        return inst

    def format(self):
        product = Product.get_product(self.product_id)
        data = {
            'from_user': User.get_one(self.from_user).format(exclude_fields=['is_followed']),
            'product': product and product.format(),
            'num': self.num,
            'create_at': util.datetime2timestamp(self.create_at)
        }
        return data


class PayForGift(BaseModel):
    order_id = pw.PrimaryKeyField(verbose_name='订单号')
    user_id = pw.CharField(max_length=64, verbose_name='用户ID')
    phone = pw.CharField(max_length=64, verbose_name='手机号')
    exchange_time = pw.DateTimeField(formats='%Y-%m-%d %H:%M:%S', verbose_name='申请兑换时间')
    exchange_mon = pw.CharField(max_length=64, verbose_name='申请兑换月份')
    exchange_status = pw.IntegerField(choices=EXCHANGE_RESULT, verbose_name='兑换状态')
    gift_value = pw.FloatField(default=0.0, verbose_name='礼物总价')
    exchange_value = pw.IntegerField(default=0, verbose_name='兑换总价')
    action = pw.IntegerField(choices=TRADE_ACTION, verbose_name='交易描述')

    class Meta:
        db_table = 'pay_for_gift'

    @classmethod
    def get_all_value(cls):
        mon = time.strftime('%Y-%m', time.localtime(time.time()))

        key = 'PayForGift:all_exchange_value:{0}'.format(mon)

        value = Redis.get(key)
        if not value:
            value = 0
            pay_for_gift_logs = list(cls.select())
            for log in pay_for_gift_logs:
                value += log.exchange_value

                Redis.set(key, value)

        return value

    @classmethod
    def is_exchange(cls, user):
        mon = time.strftime('%Y-%m', time.localtime(time.time()))
        try:
            log = cls.select().where(cls.user_id == user._id, cls.exchange_mon == mon).get()
            is_exchange = True if log else False
        except:
            is_exchange = False

        return is_exchange

    @classmethod
    def get_user_logs(cls, user_id, page, pagesize):
        logs = list(cls.select().where(
            cls.user_id == user_id, cls.exchange_status == 1
        ).order_by(cls.create_at.desc()).paginate(page, pagesize))
        return logs

    @classmethod
    def create_log(cls, user, exchange_status, gift_value, exchange_value, action):
        if float(gift_value) > 0:
            exchange_time = datetime.now()
            order_id = uuid.uuid1()
            mon = time.strftime('%Y-%m', time.localtime(time.time()))

            return cls.create(order_id=order_id, user_id=user._id, phone=user.phone,
                              exchange_time=exchange_time, exchange_mon=mon,
                              exchange_status=exchange_status,
                              gift_value=gift_value,
                              exchange_value=exchange_value, action=action)
        else:
            return

    def format(self):
        data = {
            'exchange_time': util.datetime2timestamp(self.exchange_time),
            'gift_value': self.gift_value,
            'exchange_value': self.exchange_value,
            'action': self.action,
            'desc': util.get_choices_desc(TRADE_ACTION, self.action),
            'create_at': util.datetime2timestamp(self.create_at)
        }
        return data


class PayOrder(Document):
    """付费订单
    """
    collection = DB.pay_order

    def format(self):
        pass

    def create_model(self):
        _id = super(PayOrder, self).create_model()
        return _id

    def delete_model(self):
        ret = super(PayOrder, self).delete_model()
        return ret

    @classmethod
    def get_order(cls, transactionId):
        order = cls.collection.find_one({"pay_mg_data.resultData.transactionId":transactionId})
        if order:
            return cls(order)
        else:
            return None

