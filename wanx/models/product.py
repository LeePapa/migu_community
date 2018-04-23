# -*- coding: utf8 -*-
from urlparse import urljoin
from playhouse.shortcuts import model_to_dict, dict_to_model
from wanx import app
from wanx.base import const, util
from wanx.base.xredis import Redis
from wanx.base.xmysql import MYDB
from wanx.models import BaseModel
from wanx.models.credit import UserCredit
from wanx.platforms.migu import Marketing

import cPickle as cjson
import datetime
import peewee as pw
import time

PRODUCT_KEY = 'product:all'
USER_PRODUCT_KEY = 'product:user:%s'

EMPTY = 0
GEM = 1
GOLD = 2
GIFT = 3
WHOLE_TRAFFIC = 4
MOBILE_TRAFFIC = 5
UNICOM_TRAFFIC = 6
TELECOM_TRAFFIC = 7
PHYSICAL_OBJECT = 8
GIFT_BAG = 9
PHONE_FEE = 10

PRODUCT_TYPE = (
    (EMPTY, u'空物品'),
    (GEM, u'游票'),
    (GOLD, u'游米'),
    (GIFT, u'游玩礼物'),
    (WHOLE_TRAFFIC, u'全网流量'),
    (MOBILE_TRAFFIC, u'移动流量'),
    (UNICOM_TRAFFIC, u'联通流量'),
    (TELECOM_TRAFFIC, u'电信流量'),
    (PHYSICAL_OBJECT, u'实物'),
    (GIFT_BAG, u'礼包'),
    (PHONE_FEE, u'全网话费'),
)

CREDIT_TYPE = (
    (1, u'游票'),
    (2, u'游米'),
    (3, u'每日免费'),
)

GIFT_FROM = (
    (const.FROM_LIVE, u'直播'),
    (const.FROM_RECORD, u'录播'),
)


class Product(BaseModel):
    product_id = pw.PrimaryKeyField(verbose_name='物品ID')
    product_name = pw.CharField(default='', max_length=64, verbose_name='物品名称')
    product_image = pw.CharField(default='', max_length=512, verbose_name='物品图片')
    product_type = pw.IntegerField(choices=PRODUCT_TYPE, verbose_name='物品类型')
    recycle_gem_price = pw.IntegerField(default=0, verbose_name='回购游票价格')

    class Meta:
        db_table = 'product'
        constraints = [pw.Check('recycle_gem_price > 0')]

    @classmethod
    def all_products_for_admin(cls):
        products = list(cls.select())
        return [(p.product_id, p.product_name) for p in products]

    @classmethod
    def all_gifts_for_admin(cls):
        products = list(cls.select().where(cls.product_type == GIFT))
        return [(p.product_id, p.product_name) for p in products]

    @classmethod
    def get_all_products(cls):
        products = Redis.get(PRODUCT_KEY)
        if products:
            products = cjson.loads(products)
            products = [dict_to_model(Product, p) for p in products]
        else:
            products = list(cls.select())
            _products = [model_to_dict(p) for p in products]
            Redis.setex(PRODUCT_KEY, 86400, cjson.dumps(_products, 2))

        return products

    @classmethod
    def get_all_gifts(cls):
        gifts = filter(lambda x: x.product_type == GIFT, cls.get_all_products())
        return gifts

    @classmethod
    def get_product(cls, product_id):
        products = filter(lambda x: x.product_id == int(product_id), cls.get_all_products())
        return products[0] if products else None

    def format(self):
        data = {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'product_image': self.product_image and urljoin(app.config.get("MEDIA_URL"),
                                                            self.product_image),
            'product_type': self.product_type,
        }
        return data

    def add_product2user(self, user_id, num, action=None, extra={}):
        if self.product_type == EMPTY:  # 空
            return const.ORDER_FINISHED
        elif self.product_type == GEM:  # 游票
            uc = UserCredit.get_or_create_user_credit(user_id)
            uc.add_gem(num, action)
            return const.ORDER_FINISHED
        elif self.product_type == GOLD:  # 游米
            uc = UserCredit.get_or_create_user_credit(user_id)
            uc.add_gold(num, action)
            return const.ORDER_FINISHED
        elif self.product_type == GIFT:  # 礼物
            up = UserProduct.get_or_create_user_product(user_id, self.product_id,
                                                        extra.get("is_money", False))
            up.add_product(num)

            return const.ORDER_FINISHED
        elif self.product_type in [WHOLE_TRAFFIC, MOBILE_TRAFFIC, UNICOM_TRAFFIC, TELECOM_TRAFFIC]:
            ret = Marketing.draw_resource(extra['migu_id'], extra['phone'], extra['campaign_id'],
                                          6, num)
            status = const.ORDER_IN_HAND if ret == True else const.ORDER_FAILED
            return status
        elif self.product_type == PHYSICAL_OBJECT:  # 实物物品, 比如：手机
            return const.ORDER_IN_HAND
        elif self.product_type == GIFT_BAG:  # 礼包, 比如：途牛券、游戏礼包
            return const.ORDER_FINISHED
        elif self.product_type == PHONE_FEE:  # 全网话费
            ret = Marketing.draw_resource(extra['migu_id'], extra['phone'], extra['campaign_id'],
                                          4, num)
            status = const.ORDER_NEED_DRAW if ret == True else const.ORDER_IN_HAND
            return status

        return None


class UserProduct(BaseModel):
    user_id = pw.CharField(max_length=64, verbose_name='用户ID')
    product_id = pw.IntegerField(verbose_name='物品ID')
    num = pw.IntegerField(default=0, verbose_name='拥有数量')
    gift_free = pw.IntegerField(default=0, verbose_name='剩余每日免费数')
    is_money = pw.BooleanField(default=False, verbose_name='金否是金钱礼物')

    class Meta:
        db_table = 'user_product'
        primary_key = pw.CompositeKey('user_id', 'product_id')

    @classmethod
    def get_user_products(cls, user_id):
        key = USER_PRODUCT_KEY % (user_id)
        uproducts = Redis.get(key)
        if uproducts:
            uproducts = cjson.loads(uproducts)
            uproducts = [dict_to_model(UserProduct, up) for up in uproducts]
            return uproducts

        uproducts = list(cls.select().where(UserProduct.user_id == user_id))
        _uproducts = [model_to_dict(up) for up in uproducts]
        Redis.setex(key, 86400, cjson.dumps(_uproducts, 2))
        return uproducts

    @classmethod
    def get_total_gold(cls, user):
        pdict = {}
        for p in Product.get_all_gifts():
            pdict[p.product_id] = p.format()

        uproducts = UserProduct.get_user_products(str(user._id))
        for up in uproducts:
            if up.product_id not in pdict:
                continue
            pdict[up.product_id].update(up.format())

        gold_gifts = []
        for gift in pdict.values():
            if gift['product_type'] == 3 and not gift.get('is_money', False):
                g = Gift.get_gift_by_product_id(gift['product_id'])
                if g:
                    gift['credit_value'] = g.credit_value

                    gold_gifts.append(gift)

        total_gold_value = UserProduct.get_current_gold(gold_gifts)

        return total_gold_value

    @classmethod
    def get_total_money(cls, user):
        pdict = {}
        for p in Product.get_all_gifts():
            pdict[p.product_id] = p.format()

        uproducts = UserProduct.get_user_products(str(user._id))
        for up in uproducts:
            if up.product_id not in pdict:
                continue
            pdict[up.product_id].update(up.format())

        pay_gifts = []
        for gift in pdict.values():
            if gift['product_type'] == 3 and gift.get('is_money', False):
                g = Gift.get_gift_by_product_id(gift['product_id'])
                if g:
                    gift['credit_value'] = g.credit_value

                    pay_gifts.append(gift)

        total_money_value = UserProduct.get_current_money(pay_gifts)

        return total_money_value

    @classmethod
    def get_current_gold(cls, gold_gifts):
        total_gold = 0
        for gift in gold_gifts:
            total_gold += gift.get('credit_value', 0) * gift.get('num', 0)

        return total_gold

    @classmethod
    def get_current_money(cls, pay_gifts):
        total_money = 0
        for gift in pay_gifts:
            total_money += gift.get('credit_value', 0) * gift.get('num', 0)

        return total_money

    @classmethod
    def clear_gifts_num(cls, user, is_money):
        pdict = {}
        for p in Product.get_all_gifts():
            pdict[p.product_id] = p.format()

        uproducts = cls.get_user_products(str(user._id))

        if is_money:
            for up in uproducts:
                if up.product_id not in pdict and not up.is_money:
                    continue
                cls.update(num=0).where(UserProduct.user_id == str(user._id),
                                        UserProduct.is_money == is_money,
                                        UserProduct.product_id == int(up.product_id)).execute()

            key = USER_PRODUCT_KEY % (str(user._id))
            Redis.delete(key)
            return

        else:
            for up in uproducts:
                if up.product_id not in pdict and up.is_money:
                    continue
                cls.update(num=0).where(UserProduct.user_id == str(user._id),
                                        UserProduct.is_money == is_money,
                                        UserProduct.product_id == int(up.product_id)).execute()

            key = USER_PRODUCT_KEY % (str(user._id))
            Redis.delete(key)
            return

    @classmethod
    def get_or_create_user_product(cls, user_id, product_id, is_money=False):
        up, _ = cls.get_or_create(user_id=user_id, product_id=product_id, is_money=is_money)
        return up

    @classmethod
    def refresh_daily_free_gifts(cls, user_id):
        from wanx.models.gift import Gift
        with MYDB.atomic():
            for gift in Gift.get_free_gifts():
                up = cls.get_or_create_user_product(user_id, gift.product_id)
                up.gift_free = gift.credit_value
                up.save()

            # 修改免费刷新时间
            UserCredit.update(
                gift_at=datetime.datetime.now()
            ).where(UserCredit.user_id == user_id).execute()

        key = USER_PRODUCT_KEY % (user_id)
        Redis.delete(key)

    def format(self):
        data = model_to_dict(self)
        return data

    def _change_product(self, num):
        self.num += num
        self.save()

        key = USER_PRODUCT_KEY % (self.user_id)
        Redis.delete(key)

    def add_product(self, num):
        self._change_product(num) if num > 0 else None

    def reduce_product(self, num):
        self._change_product(-num) if num > 0 else None


from wanx.models.gift import EXCHANGE_STATUS, Gift


class GiftExchangeCfg(BaseModel):
    exchange_thresthold = pw.IntegerField(default=1, verbose_name='兑换门槛')
    break_rate = pw.FloatField(default=1, verbose_name='折损率')
    exchange_begin = pw.DateTimeField(constraints=[pw.SQL('DEFAULT CURRENT_TIMESTAMP')],
                                      formats='%Y-%m-%d %H:%M:%S', verbose_name='开始时间')
    exchange_end = pw.DateTimeField(constraints=[pw.SQL('DEFAULT CURRENT_TIMESTAMP')],
                                    formats='%Y-%m-%d %H:%M:%S', verbose_name='结束时间')
    total_exchange_value = pw.IntegerField(default=0, verbose_name='兑换总额')
    exchange_status = pw.IntegerField(choices=EXCHANGE_STATUS, verbose_name='显示状态')

    class Meta:
        db_table = 'gift_exchange_cfg'

    @classmethod
    def get_gift_config(cls):
        cfg = cls.select().where(cls.exchange_status == 0).get()
        return cfg

    @classmethod
    def is_exchange_time(cls):
        try:
            cfg = cls.select().where(cls.exchange_status == 0).get()
        except:
            cfg = None
        if cfg:
            if not cfg.exchange_begin or not cfg.exchange_end:
                return False

            exchange_begin = int(
                time.mktime(time.strptime(str(cfg.exchange_begin), '%Y-%m-%d %H:%M:%S')))
            exchange_end = int(
                time.mktime(time.strptime(str(cfg.exchange_end), '%Y-%m-%d %H:%M:%S')))

            current_time = int(time.time())

            if exchange_begin < current_time < exchange_end:
                return True
            else:
                return False
        else:
            return False

    def format(self):

        data = {
            'exchange_thresthold': self.exchange_thresthold,
            'break_rate': self.break_rate,
            'exchange_begin': util.datetime2timestamp(self.exchange_begin) if self.exchange_begin else None,
            'exchange_end': util.datetime2timestamp(self.exchange_end) if self.exchange_end else None,
            'total_exchange_value': self.total_exchange_value,
            'exchange_status': self.exchange_status,
        }

        return data
