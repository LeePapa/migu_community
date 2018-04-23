# -*- coding: utf8 -*-
from urlparse import urljoin

from flask import request
from wanx import app
from wanx.base import util, error, const
from wanx.base.xredis import Redis
from wanx.models.credit import UserCredit
from wanx.models.live import AnchorWlist
from wanx.models.product import Product, UserProduct, GiftExchangeCfg
from wanx.models.gift import Gift, UserGiftLog, PayForGift, PayOrder
from wanx.models.user import User, UserCertify
from wanx.models.msg import Message, GiftNum
from wanx.models.video import Video
from wanx.models.xconfig import Config
from wanx.platforms.xlive import Xlive
from wanx.platforms.migu import Marketing

import datetime
import json
import time


def _gift_num():
    totals = GiftNum.collection.find({})
    available_num = sorted([i['num'] for i in totals])
    if not available_num:
        available_num = Config.fetch('available_num', [1, 10, 30, 66, 188, 520], json.loads)
    return sorted(available_num, reverse=True)


@app.route('/gifts/all_gifts', methods=['GET'])
@util.jsonapi()
def all_gifts():
    """获取所有可赠送礼物 (GET)

    :uri: /gifts/all_gifts
    :return: {'gifts': list, 'available_num': list}
    """
    user = request.authed_user
    if user:
        # 刷新每日免费礼物
        uc = UserCredit.get_or_create_user_credit(str(user._id))
        if uc.gift_at.date() < datetime.date.today():
            UserProduct.refresh_daily_free_gifts(str(user._id))

    gifts = []

    #
    video_type = int(request.values.get('video_type', '0'))
    #
    for gf in Gift.get_onsale_gifts():
        tmp = gf.format()
        # 每日免费礼物显示剩余数量
        if gf.credit_type == const.DAILY_FREE:
            if user:
                up = UserProduct.get_or_create_user_product(str(user._id), gf.product_id)
                tmp['free_num'] = up.gift_free
            else:
                tmp['free_num'] = 0
        if gf.credit_type == const.MONEY:
            if not video_type:
                continue
            if video_type == 2:
                continue
            # 单位分
            tmp['credit_value'] = tmp['credit_value'] / 100.0
        gifts.append(tmp)

    available_num = _gift_num()
    return {'gifts': gifts, 'available_num': available_num}


@app.route('/gifts/anchor', methods=['GET'])
@util.jsonapi(login_required=True)
def gifts_anchor():
    """
    主播兑换信息

    :uri: /gifts/anchor
    :return: {}
    """
    user = request.authed_user
    cfg = GiftExchangeCfg.get_gift_config()

    break_rate = cfg.break_rate  # 折损率
    _gift_value = UserProduct.get_total_money(user)  # 当前用户礼物价值

    gift_value = float(_gift_value) / 100

    _value = gift_value * float(break_rate)
    exchange_value = int(_value) + 1 if _value > int(_value) else int(_value)  # 折损后的价值

    is_anchor_wlist = AnchorWlist.is_anchor_wlist(user._id)  # 是否是签约主播
    is_exchange_time = GiftExchangeCfg.is_exchange_time()  # 是否在兑换时间内

    if cfg.exchange_begin and cfg.exchange_end:
        begin = time.strftime("%Y-%m-%d %H:%M:%S",
                              time.localtime(util.datetime2timestamp(cfg.exchange_begin)))
        end = time.strftime("%Y-%m-%d %H:%M:%S",
                            time.localtime(util.datetime2timestamp(cfg.exchange_end)))
        exchange_word = '本月仅在{0} - {1}日可兑换'.format(begin[8:10], end[8:10])

    else:
        exchange_word = '本月不可兑换'

    return {'gifts_config': cfg.format(), 'gift_value': gift_value,
            'is_anchor_wlist': is_anchor_wlist,
            'is_exchange_time': is_exchange_time,
            'exchange_value': exchange_value,
            'exchange_word': exchange_word,
            }


@app.route('/gifts/exchange', methods=['GET'])
@util.jsonapi(login_required=True)
def gifts_exchange():
    user = request.authed_user

    requ_type = request.values.get('requ_type')

    value = PayForGift.get_all_value()  # 现已兑换的总金额

    cfg = GiftExchangeCfg.get_gift_config()
    total_exchange_value = cfg.total_exchange_value  # 兑换上限
    break_rate = cfg.break_rate  # 折损率
    exchange_thresthold = cfg.exchange_thresthold  # 兑换下限

    gift_value = UserProduct.get_total_money(user)  # 当前用户礼物价值
    _gift_value = float(gift_value) / float(100)
    # gift_value = UserCredit.get_or_create_user_credit(user._id).current_money  # 当前用户礼物价值

    _value = _gift_value * float(break_rate)
    exchange_value = int(_value) + 1 if _value > int(_value) else int(_value)  # 折损后的价值

    current_exchange_value = int(total_exchange_value) - int(value)  # 当前还可兑换的金额

    # 营销数据入库经分
    data_dict = dict(
        cmd="exchange_huafei",
        deviceid=request.values.get('device', ''),
        mobile=user.phone,
        source=request.values.get('source', 'activity'),
        activityid="0",
        activityname=u"兑换话费活动"
    )

    if requ_type == 'get_judge':

        certify_status = UserCertify.get_certify_status(user._id)

        is_anchor_wlist = AnchorWlist.is_anchor_wlist(user._id)  # 是否是签约主播
        if is_anchor_wlist:
            return {'exchange_status': 1, 'exchange_msg': '签约主播无法兑换'}

        user_certify = True if certify_status == 3 else False
        if not user_certify:
            return {'exchange_status': 2, 'exchange_msg': '只有实名认证的用户才可以兑换哦，快去认证吧'}

        is_exchange_time = GiftExchangeCfg.is_exchange_time()  # 是否在兑换时间内
        if not is_exchange_time:
            return {'exchange_status': 3, 'exchange_msg': '当前时间不在礼物兑换期内，请在兑换期内进行礼物兑换'}

        if int(exchange_value) >= int(current_exchange_value):  # 超过总额度
            return {'exchange_status': 4, 'exchange_msg': '本月额度已经被全部兑换完啦，下个月请早了'}

        is_exchange = PayForGift.is_exchange(user)  # 兑换次数
        if is_exchange:
            return {'exchange_status': 5, 'exchange_msg': '每个月只能兑换一次哦，您本月已经兑换过啦'}

        if int(exchange_value) < int(exchange_thresthold):  # 不满足兑换门槛
            return {'exchange_status': 6, 'exchange_msg': '您的礼物还不够提现哦'}

        data_dict["opt"] = "1:{0}:{1}".format(gift_value, exchange_value)
        Marketing.jf_report(data_dict)
        return {'exchange_status': 0,
                'exchange_msg': '您有价值{0}元的礼物，可以兑换{1}元话费，话费将发放到您登录的手机号码内，兑换完成后付费礼物全部清零'.format(
                    _gift_value, exchange_value)}

    elif requ_type == 'pay_exchange':
        is_anchor_wlist = AnchorWlist.is_anchor_wlist(user._id)  # 是否是签约主播
        if is_anchor_wlist:
            return error.StoreError

        certify_status = UserCertify.get_certify_status(user._id)
        user_certify = True if certify_status == 3 else False
        if not user_certify:
            return error.StoreError

        is_exchange_time = GiftExchangeCfg.is_exchange_time()
        if not is_exchange_time:
            return error.StoreError

        if int(exchange_value) >= int(current_exchange_value):
            return error.StoreError

        is_exchange = PayForGift.is_exchange(user)
        if is_exchange:
            return error.StoreError

        if int(exchange_value) < int(exchange_thresthold):
            return error.StoreError

        lock_key = 'lock:exchange_fee:%s' % (str(user._id))
        with util.Lockit(Redis, lock_key) as locked:
            if locked:
                return error.StoreError('兑换太频繁')

            try:
                uc = UserCredit.get_or_create_user_credit(user._id)
                uc.reduce_money(gift_value)

                UserProduct.clear_gifts_num(user, True)

                PayForGift.create_log(user, const.SUCCESS, _gift_value, exchange_value,
                                      const.GIFT_EXCHANGE)
                data_dict["opt"] = "1:{0}:{1}".format(gift_value, exchange_value)
                Marketing.jf_report(data_dict)
                return {'exchange_status': 0,
                        'exchange_msg': '兑换成功，{0}元的话费将在30个工作日内发到您登录的咪咕游玩手机账户'.format(
                            exchange_value)}

            except:
                PayForGift.create_log(user, const.FAIL, _gift_value, exchange_value,
                                      const.GIFT_EXCHANGE)
                return {'exchange_status': 7, 'exchange_msg': '兑换失败，请稍后再试哦'}

    elif requ_type == 'gold_exchange':
        lock_key = 'lock:exchange_gold:%s' % (str(user._id))
        with util.Lockit(Redis, lock_key) as locked:
            if locked:
                return error.StoreError('兑换太频繁')

            try:
                total_gold_value = UserProduct.get_total_gold(user)
                uc = UserCredit.get_or_create_user_credit(user._id)
                uc.add_gold(total_gold_value, const.GIFT_EXCHANGE)

                UserProduct.clear_gifts_num(user, False)

                data_dict["opt"] = "1:{0}:{1}".format(gift_value, exchange_value)
                Marketing.jf_report(data_dict)
                return {'exchange_status': 0, 'exchange_msg': '您已兑换成功，请去游米账户中进行查询'}

            except:
                data_dict["opt"] = "0:0:0"
                Marketing.jf_report(data_dict)
                return {'exchange_status': 7, 'exchange_msg': '兑换失败，请稍后再试哦'}

    else:
        return {'exchange_status': 7, 'exchange_msg': '兑换失败，请稍后再试哦'}


@app.route('/gifts/user_gifts_class', methods=['GET'])
@util.jsonapi(login_required=True)
def user_gifts_class():
    """获取用户所有礼物分类 (GET&LOGIN)

    :uri: /gifts/user_gifts_class
    :return: {'gifts': list}
    """
    requ_type = request.values['requ_type']
    user = request.authed_user
    pdict = {}
    for p in Product.get_all_gifts():
        pdict[p.product_id] = p.format()

    uproducts = UserProduct.get_user_products(str(user._id))
    from wanx.base.log import print_log
    print_log('activity/team_vote', '[uproducts]: {0}'.format(uproducts))
    for up in uproducts:
        if up.product_id not in pdict:
            continue
        pdict[up.product_id].update(up.format())

    if requ_type == 'get_pay_gifts':
        pay_gifts = []
        for gift in pdict.values():
            if gift['product_type'] == 3 and gift.get('is_money', '') and gift.get('num', 0) != 0:
                g = Gift.get_gift_by_product_id(gift['product_id'])
                if g:
                    gift['credit_value'] = float(g.credit_value) / float(100)

                    pay_gifts.append(gift)

        cfg = GiftExchangeCfg.get_gift_config()
        is_exchange_time = GiftExchangeCfg.is_exchange_time()  # 是否在兑换时间内

        total_credit_value = UserProduct.get_current_money(pay_gifts)
        return {'gifts': pay_gifts, 'total_credit_value': total_credit_value,
                'is_exchange_time': is_exchange_time, 'gifts_config': cfg.format()}

    elif requ_type == 'get_gold_gifts':
        gold_gifts = []
        from wanx.base.log import print_log
        print_log('activity/team_vote', '[pdict]: {0}'.format(pdict))
        for gift in pdict.values():
            if gift['product_type'] == 3 and not gift.get('is_money', '') and gift.get('num',
                                                                                       0) != 0:
                g = Gift.get_gift_by_product_id(gift['product_id'])
                if g:
                    if int(g.gift_id) == 1:
                        gift['credit_value'] = 0
                    else:
                        gift['credit_value'] = g.credit_value

                    gold_gifts.append(gift)

        total_gold_value = UserProduct.get_current_gold(gold_gifts)
        return {'gifts': gold_gifts, 'total_credit_value': total_gold_value}


@app.route('/gifts/user_gifts', methods=['GET'])
@util.jsonapi(login_required=True)
def user_gifts():
    """获取用户所有礼物 (GET&LOGIN)

    :uri: /gifts/user_gifts
    :return: {'gifts': list}
    """
    user = request.authed_user
    pdict = {}
    for p in Product.get_all_gifts():
        pdict[p.product_id] = p.format()

    uproducts = UserProduct.get_user_products(str(user._id))
    for up in uproducts:
        if up.product_id not in pdict:
            continue
        pdict[up.product_id].update(up.format())

    return {'gifts': pdict.values()}


@app.route('/gifts/send_gift', methods=['GET', 'POST'])
@util.jsonapi(login_required=True)
def send_gift():
    """赠送礼物 (GET|POST&LOGIN)

    :uri: /gifts/send_gift
    :param user_id: 主播ID
    :param gift_id: 礼物ID
    :param num: 礼物数量
    :param gift_from: 礼物来源(1:直播, 2:录播)
    :param from_id:来源ID(直播ID或者录播视频ID)
    :return: {'ret: bool}

    :if money need cs(充值来源)，SDKVersion，dId 
    """
    user = request.authed_user
    gift_id = int(request.values.get('gift_id'))
    to_user_id = request.values.get('user_id')
    num = int(request.values.get('num', 1))
    gift_from = int(request.values.get('gift_from'))
    from_id = request.values.get('from_id')
    user_ip = request.remote_addr
    device = request.values.get('device', None)

    if not gift_id or not to_user_id or num < 1 or not gift_from:
        return error.InvalidArguments

    if to_user_id == str(user._id):
        return error.GiftError('不能给自己赠送礼物哦')

    to_user = User.get_one(to_user_id, check_online=False)
    if not to_user:
        return error.UserNotExist('该视频没有主播')

    available_num = _gift_num()
    if num not in available_num:
        return error.GiftError('礼物数量不符合规则')

    gift = Gift.get_gift(gift_id)
    if not gift:
        return error.GiftError('该礼物不能赠送')
    money_data = {}
    transactionId = ''
    if gift.credit_type == const.MONEY:
        # today_times = UserGiftLog.user_today_gift_id_times(user._id,gift_id,num)
        gift_data = gift.format()
        # max_times = gift_data['per_piece_limit'].get(num)
        # if max_times <= today_times:
        #     return error.GiftError('该档礼物今天的次数已用完')
        from wanx.platforms.migu import PayByMg
        consumeCode = gift_data['per_piece_id'].get(num)
        cs = 6
        SDKVersion = request.values.get('SDKVersion')
        dId = request.values.get('dId', 'null')
        goodsname = gift_data['product_name'] + '_' + str(num)

        pay_mg_data = PayByMg.get_payurl(user, cs, SDKVersion, dId, consumeCode, 1,
                                         goodsname=goodsname)

        if isinstance(pay_mg_data, error.ApiError):
            return pay_mg_data
        # 创建订单
        pay_order_obj = PayOrder.init()
        # [set(pay_order_obj,attr,value) for attr,value in pay_mg_data.items()]
        pay_order_obj.pay_mg_data = pay_mg_data
        transactionId = pay_mg_data['resultData']['transactionId']
        pay_order_obj.transactionId = transactionId
        pay_order_obj.phone = user.phone
        pay_order_obj.nickname = user.nickname
        pay_order_obj.credit_value = gift.credit_value
        pay_order_obj.total_value = gift.credit_value * num
        pay_order_obj.gift_num = num
        pay_order_obj.finished = 0
        pay_order_obj.product_name = gift_data['product_name']
        pay_order_obj.check_pay_data = {}
        pay_order_obj.pay_info = {"from_user_id": user._id, 'to_user_id': to_user_id, "num": num,
                                  'gift_id': gift_id, \
                                  'gift_from': gift_from, "from_id": from_id}
        pay_order_obj.create_model()
        money_data = {'is_money': True, "pay_data": pay_mg_data.get("resultData", {})}

    ret = False
    key = 'lock:send_gift:%s' % (str(user._id))
    with util.Lockit(Redis, key) as locked:
        if locked:
            return error.GiftError('赠送礼物失败')

        ret = gift.send_to_user(str(user._id), to_user_id, num, gift_from, from_id,
                                transactionId=transactionId)

    if isinstance(ret, error.ApiError):
        return ret

    if money_data:
        return money_data
    # 录播发送消息到中心消息
    if ret and gift_from == const.FROM_RECORD:
        video = Video.get_one(from_id, check_online=False)
        if video:
            Message.send_gift_msg(str(user._id), from_id, 'gift')
            video.update_model({'$inc': {'gift_count': 1, 'gift_num': num}})

    # 直播发送广播信息
    if ret and gift_from == const.FROM_LIVE:
        total = Xlive.get_user_send_gift_count(from_id, str(user._id), gift_id, num)
        data = dict(
            user_id=str(user._id),
            username=user.nickname or user.name,
            userphoto=user.get_photo(),
            gift_name=gift.format()['product_name'],
            gift_image=gift.format()['product_image'],
            gift_num=num,
            event_id=from_id,
            total=total
        )
        Xlive.send_live_msg(data)

    # 营销数据入库经分  打赏活动
    from wanx.models.activity import ActivityConfig, ActivityVideo
    from wanx.platforms.migu import Marketing
    activity_config = None
    if gift_from == const.FROM_RECORD:
        activity_video = ActivityVideo.get_activity_video_by_vid(from_id)
        if activity_video:
            activity_config = ActivityConfig.get_one(activity_video['activity_id'])
    else:
        aids = ActivityConfig.get_by_type(const.FROM_LIVE)
        for a in ActivityConfig.get_list(aids):
            activity_config = a
            break
    if activity_config:
        data_dict = dict(
            cmd="deliver_gift",
            opt="{0}/{1}".format(gift.gold_price, to_user_id),
            deviceid=request.values.get('device', ''),
            mobile=user.phone,
            source=request.values.get('source', 'activity'),
            activityid=str(activity_config['_id']),
            activityname=activity_config['name']
        )
        Marketing.jf_report(data_dict)
    # 1118 task1
    # Marketing.trigger_report(user.partner_migu['id'], user.phone, 'send_gift')
    return {'ret': ret}


@app.route('/gifts/top_users', methods=['GET', 'POST'])
@util.jsonapi()
def gift_top_users():
    """获取赠送主播礼物用户排行 (GET|POST&LOGIN)

    :uri: /gifts/top_users
    :param user_id: 主播ID
    :param page: 页码
    :param nbr: 每页数量
    :return: {'users: list, 'end_page': bool}
    """
    user = request.authed_user
    page = int(request.values.get('page', 1))
    pagesize = int(request.values.get('nbr', 10))
    user_id = request.values.get('user_id')
    if not user_id:
        error.InvalidArguments

    uids = UserGiftLog.get_top_sender_ids(user_id, page, pagesize)
    users = []
    for uid, gold in uids:
        user = User.get_one(uid).format(exclude_fields=['is_followed'])
        user['total_gold'] = gold
        users.append(user)

    return {'users': users, 'end_page': len(uids) != pagesize}


@app.route('/gifts/log', methods=('GET', 'POST'))
@util.jsonapi(login_required=True)
def gifts_history():
    """
    查询礼物交易记录
    :uri: /gifts/log
    :param mode: 类型 1:送礼记录，2：收礼记录
    :param page: 页码
    :param nbr: 每页数量
    :return: {'logs': list, 'end_page': bool}
    """
    user = request.authed_user
    mode = int(request.values.get('mode', 1))
    page = int(request.values.get('page', 1))
    pagesize = int(request.values.get('nbr', 10))

    logs = UserGiftLog.get_user_logs(str(user._id), mode, page, pagesize)
    if mode==1:
        query = [-1,0,1]
    else:
        query = [-1,1]
    logs = [log.format_log() for log in logs if log.format_log()["send_success"] in query]
    return {'logs': logs, 'end_page': len(logs) != pagesize}


@app.route('/gifts/log', methods=('GET', 'POST'))
@util.jsonapi(login_required=True)
def gifts_history_search():
    """
    查询礼物交易记录
    :uri: /gifts/log
    :param mode: 类型 1:送礼记录，2：收礼记录
    :param page: 页码
    :param nbr: 每页数量
    :return: {'logs': list, 'end_page': bool}
    """
    user = request.authed_user
    mode = int(request.values.get('mode', 1))
    page = int(request.values.get('page', 1))
    pagesize = int(request.values.get('nbr', 10))

    logs = UserGiftLog.get_user_logs(str(user._id), mode, page, pagesize)
    if mode==1:
        query = [-1,0,1]
    else:
        query = [-1,1]
    logs = [log.format_log() for log in logs if log.format_log()["send_success"] in query]
    return {'logs': logs, 'end_page': len(logs) != pagesize}
