# -*- coding: utf8 -*-
from flask import request
from bson import ObjectId
from wanx import app
from wanx.base.guard import Guard
from wanx.models.home import (Banner, HomeCategory, HomeCategoryConfig, BannerSdk, LaunchAds,
                              Popup, PopupLog, FixedBanner, BugReport, H5Counter, BottomPhoto,
                              BottomColor, TitleColor, GameRecommend)
from wanx.models.video import Video, GameRecommendVideo
from wanx.models.game import Game, HotGame, UserSubGame
from wanx.models.user import User, UserDevice
from wanx.models.activity import ActivityVideo
from wanx.models.xconfig import Config
from wanx.platforms.xlive import Xlive
from wanx.platforms.migu import Migu
from wanx.base import util, error
import json
from wanx.models.msg import JpushCollect
from wanx.platforms.migu import Marketing,PayByMg
from wanx.models.gift import PayOrder,Gift
from wanx.base import const, util


@app.route('/check')
def check_service():
    return 'OK'


@app.route('/daily_visit')
@util.jsonapi()
def daily_visit():
    """每日访问信息（GET）

    :uri: /daily_visit
    :param action: 动作('active':活跃, 'awake':唤醒)
    :return: {}
    """
    user = request.authed_user
    device = request.values.get('device', None)
    appid = request.values.get('appid', None)
    action = request.values.get('action', 'active')
    if device and appid:
        uid = str(user._id) if user else None
        UserDevice.create_or_update_device(device, uid, appid, action)
    return {}


@app.route('/is_mobile_phone', methods=['GET'])
@util.jsonapi()
def is_mobile_phone():
    """是否为移动手机号(GET)

    :uri: /is_mobile_phone
    :param phone: 手机号
    :return: {'ret': bool}
    """
    phone = request.values.get('phone', None)
    return {'ret': util.is_mobile_phone(phone)}


@app.route('/app_in_review', methods=['GET'])
@util.jsonapi()
def app_in_review():
    """判断版本是否审核状态(GET)

    :uri: /app_in_review
    :param version: 版本号
    :return: {'in_review': bool}
    """
    version = request.values.get('version', None)
    # 后台配置版本是否审核状态
    key = 'app_in_review_%s' % (version)
    in_review = Config.fetch(key, False, int)
    return {'in_review': bool(in_review)}


@app.route('/launch_ads')
@util.jsonapi()
def launch_ads():
    """获取开屏广告

    :uri: /launch_ads
    :return: {'ad': object}
    """
    ad_ids = LaunchAds.all_ad_ids()
    ads = [ad.format() for ad in LaunchAds.get_list(ad_ids)]
    ad = util.random_pick(ads, 'rate')
    return {'ad': ad}


@app.route('/jpush_collect', methods=['POST', 'GET'])
@util.jsonapi()
def jpush_collect():
    """push 收集
    """
    params = request.values
    message = json.loads(params.get("message", ''))
    # message = {u'imei': u'211ECB2D5D67FA63CA73AF542D6AD6F0', u'jpush_mid': u'3382201628','jpush_registration_id':u'3382201628'}
    if not message or not message.get('jpush_registration_id') or not message.get('my_message_id'):
        return error.MissArguments
    jpush_collect_obj = JpushCollect.init()
    jpush_collect_obj.save(**message)
    return {'jpush_collect': 'ok'}


@app.route('/home', methods=['GET'])
@util.jsonapi()
def home():
    """获取首页信息 (GET)

    :uri: /home
    :param os: 平台
    :param channels: 渠道(可选)
    :param version_code: 版本号
    :returns: {'banners': list, 'categories': list,
               'sub_games': list, 'hot_games': list,
               'hot_lives': list}
    """
    user = request.authed_user
    ret = dict()

    # banner广告
    params = request.values
    os = params.get('os', None)
    channels = params.get('channels', None)
    version_code = int(params.get('version_code', 0))

    no_gamefy = False   # 不返回游戏风云视频及内容
    if not os or not version_code:
        no_gamefy = True
    elif (os == 'ios' and version_code < 5920) or (os == 'android' and version_code < 416):
        no_gamefy = True

    uid = None
    province = None
    if user:
        uid = str(user._id)
        phone = str(user.phone)

        if user.province:
            province = user.province

        if not user.province and util.is_mobile_phone(phone):
            province = Migu.get_user_info_by_account_name(phone)
            if not isinstance(province, error.ApiError):
                user.update_model({'$set': {'province': province}})
            else:
                province = None
    banners = list()
    _ids = Banner.all_banner_ids()
    for b in Banner.get_list(_ids):
        if b.os and b.os != os:
            continue
        if (b.version_code_mix and b.version_code_mix > version_code) or \
                (b.version_code_max and b.version_code_max < version_code):
            continue
        if channels and b.channels and channels not in b.channels:
            continue
        if b.login == 'login' and (not uid or not b.user_in_group(str(b.group), uid)):
            continue
        if b.province and province and province not in b.province:
            continue
        banners.append(b.format())

    if version_code == 0 and not banners:
        _ids = Banner.all_banners_by_version()
        banners = [b.format() for b in Banner.get_list(_ids)]
    ret['banners'] = banners

    support_cates = ['video', 'game', 'user', 'show-video']
    if no_gamefy:
        support_cates.pop(-1)
    categories = []
    cate_ids = HomeCategory.all_category_ids()
    cates = HomeCategory.get_list(cate_ids)
    for cate in cates:
        ids = HomeCategoryConfig.category_object_ids(str(cate._id))
        if not ids or cate.ctype not in support_cates:
            continue
        _category = cate.format()
        if cate.ctype in ['video', 'show-video']:
            ex_fields = ['is_favored', 'is_liked', 'author__is_followed', 'game__subscribed']
            if no_gamefy:
                _category['objects'] = [v.format(exclude_fields=ex_fields) for v in Video.get_list(ids) if v.author]
            else:
                _category['objects'] = [v.format(exclude_fields=ex_fields) for v in Video.get_list(ids)]
        elif cate.ctype == 'game':
            ex_fields = ['subscribed']
            _category['objects'] = [g.format(exclude_fields=ex_fields) for g in Game.get_list(ids)]
        elif cate.ctype == 'user':
            ex_fields = ['is_followed']
            _category['objects'] = [u.format(exclude_fields=ex_fields) for u in User.get_list(ids)]
        _category['objects'] = _category['objects'][:4]
        categories.append(_category)
    ret['categories'] = categories

    # 兼容老版本
    ret['hottest_of_today'] = []

    # 热门直播
    all_lives = Xlive.get_all_lives()
    hot_lives = all_lives[:4] if len(all_lives) >= 4 else all_lives[:2]
    hot_lives = hot_lives if len(hot_lives) > 1 else []
    ret['hot_lives'] = [Xlive.format(l) for l in hot_lives]

    # 用户已订阅游戏
    sub_game_ids = []
    if user:
        sub_game_ids = UserSubGame.sub_game_ids(str(user._id))
        tmp = []
        for game_id in sub_game_ids:
            ex_fields = ['is_favored', 'is_liked', 'author__is_followed', 'game__subscribed']
            vids = GameRecommendVideo.game_video_ids(game_id) or []
            videos = [v.format(exclude_fields=ex_fields) for v in Video.get_list(vids)]
            # 补齐4个人气视频
            if len(videos) < 4:
                hot_vids = Video.game_hotvideo_ids(game_id, 1, 4)
                for _vid in hot_vids:
                    if len(videos) == 4:
                        break
                    if _vid in vids:
                        continue
                    v = Video.get_one(_vid, check_online=True)
                    v and videos.append(v.format(exclude_fields=ex_fields))
            if videos:
                tmp.append({'game': videos[0]['game'], 'videos': videos})
    else:
        tmp = list()
    ret['sub_games'] = tmp

    # 热门游戏
    gids = HotGame.hot_game_ids()
    # 去掉用户已订阅游戏
    gids = [gid for gid in gids if gid not in sub_game_ids]
    tmp = []
    for game_id in gids:
        ex_fields = ['is_favored', 'is_liked', 'author__is_followed', 'game__subscribed']
        vids = GameRecommendVideo.game_video_ids(game_id) or []
        videos = [v.format(exclude_fields=ex_fields) for v in Video.get_list(vids)]
        # 补齐4个人气视频
        if len(videos) < 4:
            hot_vids = Video.game_hotvideo_ids(game_id, 1, 4)
            for _vid in hot_vids:
                if len(videos) == 4:
                    break
                if _vid in vids:
                    continue
                v = Video.get_one(_vid, check_online=True)
                v and videos.append(v.format(exclude_fields=ex_fields))
        if videos:
            tmp.append({'game': videos[0]['game'], 'videos': videos})
    ret['hot_games'] = tmp

    return ret


@app.route('/home/recommend_module', methods=['GET'])
@util.jsonapi()
def recommend_module():
    """获取游戏模块分类 (GET)

    :uri: /home/recommend_module
    :param os: 平台
    :param channels: 渠道(可选)
    :param version_code: 版本号
    :returns: {'modules': list}
    """

    user = request.authed_user
    params = request.values
    os = params.get('os', None)
    channels = params.get('channels', None)
    version_code = int(params.get('version_code', 0))

    uid = None
    province = None
    if user:
        uid = str(user._id)
        phone = str(user.phone)

        if user.province:
            province = user.province

        if not user.province and util.is_mobile_phone(phone):
            province = Migu.get_user_info_by_account_name(phone)
            if not isinstance(province, error.ApiError):
                user.update_model({'$set': {'province': province}})
            else:
                province = None

    modules = list()
    _ids = GameRecommend.all_module_ids()
    for b in GameRecommend.get_list(_ids):
        if b.os and b.os != os:
            continue

        if (b.version_code_mix and b.version_code_mix > version_code) or \
                (b.version_code_max and b.version_code_max < version_code):
            continue

        if channels and b.channels and channels not in b.channels:
            continue

        if b.login == 'login' and (not uid or not b.user_in_group(str(b.group), uid)):
            continue

        if b.province and not province:
            continue

        if b.province and province and province not in b.province:
            continue
        modules.append(b.format())

    return {'modules': modules}


@app.route('/banners', methods=['GET'])
@util.jsonapi()
def banner():
    """获取Banner信息 (GET)

    :uri: /banners
    :param os: 平台
    :param channels: 渠道(可选)
    :param version_code: 版本号
    :returns: {'banners': list}
    """
    user = request.authed_user
    params = request.values
    os = params.get('os', None)
    channels = params.get('channels', None)
    version_code = int(params.get('version_code', 0))

    if not os or not version_code:
        return error.InvalidArguments

    uid = None
    province = None
    if user:
        uid = str(user._id)
        phone = str(user.phone)

        if user.province:
            province = user.province

        if not user.province and util.is_mobile_phone(phone):
            province = Migu.get_user_info_by_account_name(phone)
            if not isinstance(province, error.ApiError):
                user.update_model({'$set': {'province': province}})
            else:
                province = None

    banners = list()
    _ids = Banner.all_banner_ids()
    for b in Banner.get_list(_ids):
        if b.os and b.os != os:
            continue

        if (b.version_code_mix and b.version_code_mix > version_code) or \
                (b.version_code_max and b.version_code_max < version_code):
            continue

        if channels and b.channels and channels not in b.channels:
            continue

        if b.login == 'login' and (not uid or not b.user_in_group(str(b.group), uid)):
            continue

        if b.province and not province:
            continue

        if b.province and province and province not in b.province:
            continue
        banners.append(b.format())

    return {'banners': banners}


@app.route('/banners/icon', methods=['GET'])
@util.jsonapi()
def banner_icon():
    """获取Banner图标信息 (GET)

    :uri: /banners/icon
    :param os: 平台
    :param channels: 渠道(可选)
    :param version_code: 版本号
    :returns: {'title_color': title_color, 'bottom_color': bottom_color, 'bottom_photo': bottom_photo}
    """
    user = request.authed_user
    params = request.values
    os = params.get('os', None)
    channels = params.get('channels', None)
    version_code = int(params.get('version_code', 0))

    if not os or not version_code:
        return error.InvalidArguments

    uid = None
    province = None
    if user:
        uid = str(user._id)
        phone = str(user.phone)

        if user.province:
            province = user.province

        if not user.province and util.is_mobile_phone(phone):
            province = Migu.get_user_info_by_account_name(phone)
            if not isinstance(province, error.ApiError):
                user.update_model({'$set': {'province': province}})
            else:
                province = None

    title_color = list()
    _ids = TitleColor.get_banner_title_color()
    for t in TitleColor.get_list(_ids):
        if t.os and t.os != os:
            continue

        if (t.version_code_mix and t.version_code_mix > version_code) or \
                (t.version_code_max and t.version_code_max < version_code):
            continue

        if channels and t.channels and channels not in t.channels:
            continue

        if t.login == 'login' and (not uid or not t.user_in_group(str(t.group), uid)):
            continue

        if t.province and not province:
            continue

        if t.province and province and province not in t.province:
            continue
        title_color.append(t.format())
    title_color = title_color[0] if title_color else {}

    bottom_color = list()
    _ids = BottomColor.get_banner_bottom_color()
    for b in BottomColor.get_list(_ids):
        if b.os and b.os != os:
            continue

        if (b.version_code_mix and b.version_code_mix > version_code) or \
                (b.version_code_max and b.version_code_max < version_code):
            continue

        if channels and b.channels and channels not in b.channels:
            continue

        if b.login == 'login' and (not uid or not b.user_in_group(str(b.group), uid)):
            continue

        if b.province and not province:
            continue

        if b.province and province and province not in b.province:
            continue
        bottom_color.append(b.format())
    bottom_color = bottom_color[0] if bottom_color else {}

    bottom_photo = list()
    _ids = BottomPhoto.get_banner_bottom_photo()
    for b in BottomPhoto.get_list(_ids):
        if b.os and b.os != os:
            continue

        if (b.version_code_mix and b.version_code_mix > version_code) or \
                (b.version_code_max and b.version_code_max < version_code):
            continue

        if channels and b.channels and channels not in b.channels:
            continue

        if b.login == 'login' and (not uid or not b.user_in_group(str(b.group), uid)):
            continue

        if b.province and not province:
            continue

        if b.province and province and province not in b.province:
            continue
        bottom_photo.append(b.format())

    return {'title_color': title_color, 'bottom_color': bottom_color, 'bottom_photo': bottom_photo}


@app.route('/banners/sdk', methods=['GET'])
@util.jsonapi()
def banner_sdk():
    """获取SDK banner 信息(GET)

    :uri: /banners/sdk
    :return: {'banners_sdk': list}
    """
    _ids = BannerSdk.all_sdk_banner_ids()
    banners = [b.format() for b in BannerSdk.get_list(_ids)]
    return {'banners_sdk': banners}


@app.route('/popup', methods=['GET'])
@util.jsonapi()
def popup():
    """弹窗
    :uri: /popup
    :param os: 平台
    :param device: 设备ID
    :param channels: 渠道(可选)
    :return:{'popup': list}
    """
    user = request.authed_user
    params = request.values
    os = params.get('os', None)
    channels = params.get('channels', None)
    device = params.get('device', None)
    version_code = int(params.get('version_code', 0))

    if not os or not device:
        return error.InvalidArguments

    uid = None
    province = None
    if user:
        uid = str(user._id)
        phone = str(user.phone)

        if user.province:
            province = user.province

        if not user.province and util.is_mobile_phone(phone):
            province = Migu.get_user_info_by_account_name(phone)
            if not isinstance(province, error.ApiError):
                user.update_model({'$set': {'province': province}})
            else:
                province = None
    pids = Popup.popup_platform_ids(os)
    list_popup = list()
    for p in Popup.get_list(pids):
        if p.os != os:
            continue

        if version_code and (p.version_code_mix and p.version_code_mix > version_code) or \
                (p.version_code_max and p.version_code_max < version_code):
            continue

        if channels and p.channels and channels not in p.channels:
            continue

        if p.login == 'login' and (not uid or not p.user_in_group(str(p.group), uid)):
            continue

        if p.province and not province:
            continue

        if p.province and province and province not in p.province:
            continue

        list_popup.append(p.format())
    popup = list()
    if list_popup:
        _pids = PopupLog.get_by_device(device)
        for p in list_popup:
            if p['popup_id'] in _pids:
                continue
            plg = PopupLog.init()
            plg.device = device
            plg.target = ObjectId(p['popup_id'])
            id = plg.create_model()
            if id:
                popup = p
                break

    return {'popup': [popup] if popup else []}


@app.route('/search', methods=['GET', 'POST'])
@util.jsonapi()
def search():
    """搜索 (GET|POST)

    :uri: /search
    :param type: 搜索类型{'all':全部, 'user':用户, 'game':游戏, 'video':视频,
                           'activity_video':活动视频, 'live_number':直播间房号}
    :param keyword: 关键字
    :returns: {'user':list, 'game':list, 'video':list}
    """
    ua = request.headers.get('User-Agent')
    params = request.values
    stype = params.get('type', 'all')
    keyword = params.get('keyword', '')
    keyword = keyword.strip()
    platform = params.get('os')
    version_code = params.get('version_code', 0)

    if not stype or not keyword:
        return error.InvalidArguments

    users = games = videos = activity_videos = lives = list()

    if stype in ['user', 'all']:
        uids = User.search(keyword)
        users = [u.format() for u in User.get_list(uids)]
        users = sorted(users, key=lambda x: x['follower_count'])

    if stype in ['game', 'all']:
        ua_filter = None
        if ua and platform == 'android' and int(version_code) >= 64:
            ua_filter = ua
        gids = Game.search(keyword, ua_filter)
        games = [g.format() for g in Game.get_list(gids, check_online=False)]

    if stype in ['video', 'all']:
        vids = Video.search(keyword)
        videos = [v.format() for v in Video.get_list(vids)]

    if stype in ['activity_video']:
        activity_id = params.get('activity_id', None)
        uids = User.search(keyword)
        _ids = ActivityVideo.get_activity_video_by_authors(uids, activity_id)
        avids = ActivityVideo.search(keyword, activity_id)
        avids.extend(_ids)
        activity_videos = [v.format() for v in ActivityVideo.get_list(set(avids))]

    if stype in ['live_number', 'all']:
        uids = User.search_live_number(keyword)
        livers = [u.format() for u in User.get_list(uids)]
        livers = sorted(livers, key=lambda x: x['follower_count'])
        lives_map = {}
        for live in Xlive.get_all_lives():
            lives_map.update({live['user_id']: live})
        lives = list()
        ex_fields = ['user__is_followed', 'game__subscribed']
        for uid in uids:
            uid = str(uid)
            if uid in lives_map:
                ulive = Xlive.format(lives_map[uid], exclude_fields=ex_fields)
                lives.append({'live': ulive, 'user': None})
                continue
            lives.append({'live': None, 'user': User.get_one(uid).format()})

    return {'users': users, 'games': games, 'videos': videos,
            'activity_videos': activity_videos, 'lives': lives}


@app.route('/fixed_banners', methods=['GET'])
@util.jsonapi()
def fixed_banner():
    """获取Banner信息 (GET)

    :uri: /fixed_banners
    :param os: 平台
    :param channels: 渠道(可选)
    :param version_code: 版本号
    :returns: {'banners': list}
    """
    user = request.authed_user
    params = request.values
    os = params.get('os', None)
    channels = params.get('channels', None)
    version_code = int(params.get('version_code', 0))

    if not os or not version_code:
        return error.InvalidArguments

    uid = None
    province = None
    if user:
        uid = str(user._id)
        phone = str(user.phone)

        if user.province:
            province = user.province

        if not user.province and util.is_mobile_phone(phone):
            province = Migu.get_user_info_by_account_name(phone)
            if not isinstance(province, error.ApiError):
                user.update_model({'$set': {'province': province}})
            else:
                province = None

    banners = list()
    _ids = FixedBanner.all_banner_ids()
    for b in FixedBanner.get_list(_ids):
        if b.os and b.os != os:
            continue

        if (b.version_code_mix and b.version_code_mix > version_code) or \
                (b.version_code_max and b.version_code_max < version_code):
            continue

        if channels and b.channels and channels not in b.channels:
            continue

        if b.login == 'login' and (not uid or not b.user_in_group(str(b.group), uid)):
            continue

        if b.province and not province:
            continue

        if b.province and province and province not in b.province:
            continue
        banners.append(b.format())

    return {'banners': banners}


@app.route('/bug_report', methods=['GET', 'POST'])
@util.jsonapi()
def bug_report():
    """BUG提交 (POST)

    :uri: /bug_report
    :param err_type: 错误类型
    :param exception: 异常类型
    :param phone_model: 手机型号
    :param os_version: 系统版本
    :param phone_number: 手机号码
    :param app_version: APP版本
    :param err_msg: 错误信息
    :param err_app: 发生APP
    :param extention: 自定义信息
    :returns: {'ret': bool}
    """
    params = request.values
    err_type = params.get('err_type', '')
    exception = params.get('exception', '')
    phone_model = params.get('phone_model', '')
    os_version = params.get('os_version', '')
    phone_number = params.get('phone_number', '')
    app_version = params.get('app_version', '')
    err_msg = params.get('err_msg', None)
    err_app = params.get('err_app', None)
    extention = params.get('extention', '')

    argvs = [err_type, exception, phone_model, os_version, phone_number,
             app_version, err_msg, err_app, extention]

    if any(map(lambda x: x is None, argvs)):
        return error.InvalidArguments

    stat = BugReport.add_report(argvs)

    return {'ret': stat}


@app.route('/count', methods=['GET', 'POST'])
@util.jsonapi()
def count():
    """网页访问量计数器 (POST)

    :uri: /count
    :param countid: 计数器id
    :returns: {'num': int}
    """
    ALLKEY = ['count0', 'count1', 'count2', 'count3', 'count4',
              'count5', 'count6', 'count7', 'count8', 'count9']
    countid = request.values.get('countid', '')
    if countid not in ALLKEY:
        return error.InvalidArguments
    num = H5Counter.update_counter(countid)
    return {'num': num}


@app.route('/video_stay_time', methods=['GET', 'POST'])
@util.jsonapi()
def video_stay_time():
    # 1118 task2 
    params = request.values
    user = request.authed_user
    video_stay_time = int(params.get('video_stay_time', 0))
    if video_stay_time > 180 and user:
        Marketing.trigger_report(user.partner_migu['id'], user.phone, 'watch_video_3m')
    return {}


@app.route('/request_id', methods=['GET', 'POST'])
@util.jsonapi()
def get_request_id():
    """
    获取请求id
    :return:
    """
    qid = Guard.new_market_id()
    return {'qid': qid}

@app.route("/shipment_mg",methods=['GET','POST'])
def shipment_mg():
    params = request.values
    transactionId = params.get("transactionId")
    #200 成功，201 已发 , 202 无效transactionId
    data = {"resultCode":'200',"desc":'ok','transactionId':transactionId}
    pay_order_obj = PayOrder.get_order(transactionId)
    if not pay_order_obj:
        data['resultCode'] = '202'
        return json.dumps(data)
    pay_info = pay_order_obj.pay_info
    if pay_order_obj.finished:
        data['resultCode'] = '201'
        return json.dumps(data)

    result = {}
    # 检查订单是否成功  
    result = PayByMg.check_order(transactionId)
    if isinstance(result, error.ApiError):
        return result

    gift = Gift.get_gift(pay_info['gift_id'])
    # {"from_user_id":user._id,'to_user_id':to_user_id,"num":num,'gift_id':gift_id,\
            # 'gift_from':gift_from,"from_id":from_id}
    ret = gift.send_to_user(pay_info['from_user_id'], pay_info['to_user_id'],\
         pay_info['num'], pay_info['gift_from'], pay_info['from_id'],send_success=1,transactionId=transactionId)
    if ret == True:
        pay_order_obj.update_model({'$set': {'finished': 1}})
        pay_order_obj.update_model({'$set': {'check_pay_data': result}})
        data['resultCode'] = "200"
        # 营销数据入库经分
        user = User.get_one(pay_info['from_user_id'])
        data_dict = dict(
            cmd="deliver_money_gift",
            deviceid=request.values.get('device', ''),
            mobile=user.phone,
            source=request.values.get('source', 'activity'),
            activityid="1",
            activityname=u"付费礼物打赏活动",
            opt="1:{0}:{1}:{2}:{3}:{4}".format(
                pay_order_obj["product_name"],
                pay_order_obj["credit_value"],
                pay_order_obj["gift_num"],
                float(pay_order_obj["gift_num"]) * float(pay_order_obj["credit_value"]),
                pay_info['to_user_id']
            )
        )
        Marketing.jf_report(data_dict)

    gift_from = pay_info['gift_from']
    from_user_id = pay_info['from_user_id']
    user = User.get_one(from_user_id)
    from_id = pay_info['from_id']
    gift_id = pay_info['gift_id']
    num = pay_info['num'] 
    # 录播发送消息到中心消息
    if ret and gift_from == const.FROM_RECORD:
        video = Video.get_one(from_id, check_online=False)
        if video:
            Message.send_gift_msg(str(user._id), from_id, 'gift')
            video.update_model({'$inc': {'gift_count': 1, 'gift_num': num}})

    # 直播发送广播信息
    if ret and gift_from == const.FROM_LIVE:
        total = Xlive.get_user_send_gift_count(from_id, str(user._id), gift_id, num)
        data_1 = dict(
            user_id=str(user._id),
            username=user.nickname or user.name,
            userphoto=user.get_photo(),
            gift_name=gift.format()['product_name'],
            gift_image=gift.format()['product_image'],
            gift_num=num,
            event_id=from_id,
            total=total
        )
        Xlive.send_live_msg(data_1)
    data.update(data_1)
    return json.dumps(data)

@app.route("/report_result",methods=['GET','POST'])
@util.jsonapi(login_required=True)
def report_result():
    params = request.values
    user = request.authed_user
    transactionId = params.get("transactionId")
    pay_order_obj = PayOrder.get_order(transactionId)
    if not pay_order_obj:
        return error.GiftError('订单号不存在')
    code = params.get("code")
    orderResult = params.get("orderResult")
    result = PayByMg.report_result(user,code,orderResult,transactionId,pay_order_obj._id)
    if isinstance(result, error.ApiError):
        return result
    return {'report':'ok'}

@app.route("/check_pay_result",methods=['GET','POST'])
@util.jsonapi(login_required=True)
def check_result():
    params = request.values
    user = request.authed_user
    transactionId = params.get("transactionId")
    pay_order_obj = PayOrder.get_order(transactionId)
    if not pay_order_obj:
        return error.GiftError('订单号不存在')

    result = PayByMg.check_order(transactionId)
    if isinstance(result, error.ApiError):
        return result
    orderStatus = result['resultData']['orderDetails']['orderStatus']
    return {"orderStatus":orderStatus}