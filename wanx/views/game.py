# -*- coding: utf8 -*-
import json

from bson.objectid import ObjectId
from flask import request
from wanx.base.xredis import Redis
from wanx.models.game import (UserSubGame, Game, WebGame, Category, CategoryGame,
                              GameRecommendSubscribe, GameDownload, GameGrid, GameAds, GameTopic,
                              TopicGame, WebGameAds, GameMainstay, HotGame, GameModule, ModuleGame, HotRecommendGame,
                              UserPopularGame, LiveHotGame, TopList, TopListGames, ChessConfig, ChessGames, VipConfig,
                              VipGames, VipGiftCode)
from wanx.models.home import Share
from wanx.models.store import UserGiftCodeOrder
from wanx.models.task import UserTask, SUB_GAME, DOWNLOAD_GAME
from wanx.platforms import Migu
from wanx import app
from wanx.base import util, const, error
import time
from wanx.platforms.migu import Marketing

from wanx.platforms.migu import Marketing, MiguPay


@app.route('/games', methods=['GET'])
@util.jsonapi()
def online_games():
    """获取所有在线游戏列表 (GET)

    :uri: /games
    :return: {'games': list}
    """
    games = Game.online_games()
    gids = [str(gid) for gid, _ in games]
    games = [g.format() for g in Game.get_list(gids)]
    return {'games': games}


@app.route('/games/host', methods=['GET'])
@util.jsonapi()
def game_host():
    """获取API的URL (GET)

    :uri: /games/host
    :param game_id: 游戏id
    :returns: {'host': url, 'live_host': url, 'under_test': bool,
               'migu_app': {'appid': string, 'secret': string}}
    """
    params = request.values
    gid = params.get('game_id', None)
    game = Game.get_one(gid, check_online=False)
    if not game:
        return error.GameNotExist

    if game.status is None or game.status == const.ONLINE:
        host = app.config.get('SERVER_URL')
        live_host = app.config.get('LIVE_SERVER_URL')
    elif game.status == const.OFFLINE:
        live_host = host = 'http://localhost'
    elif game.status == const.UNDER_TEST:
        from config import Stage
        host = Stage.SERVER_URL
        live_host = Stage.LIVE_SERVER_URL
    else:
        live_host = host = app.config.get('SERVER_URL')
    return {'host': host, 'live_host': live_host,
            'under_test': game.status == const.UNDER_TEST, 'migu_app': game.migu}


@app.route("/games/<string:gid>/download", methods=("GET", "POST"))
@util.jsonapi()
def game_download(gid):
    """获取游戏下载地址(GET|POST)

    :uri: /games/<string:gid>/download
    :returns: {'url': url, 'download_id': string}
    """
    ua = request.headers.get('User-Agent')
    game = Game.get_one(gid, check_online=False)
    if not game:
        return error.GameNotExist

    url = game.format(exclude_fields=['subscribed'])['url']
    if game.bid and game.bcode:
        url = Migu.ota_download(ua, game.bcode, game.bid) or url

    # 增加下载记录
    gd = GameDownload.init()
    gd.user = request.authed_user._id if request.authed_user else None
    gd.device = request.values.get('device', None)
    gd.game = game._id
    gd.finish = False
    download_id = gd.create_model()

    #咪咕汇活动
    user = request.authed_user
    if user:
        Marketing.trigger_report(user.partner_migu['id'], user.phone, 'download_game')
    return {'url': url, 'download_id': str(download_id)}


@app.route("/games/<string:download_id>/finish_download", methods=("POST",))
@util.jsonapi()
def game_download_finish(download_id):
    """游戏下载完成(POST)

    :uri: /games/<string:download_id>/finish_download
    :returns: {}
    """
    gd = GameDownload.get_one(download_id)
    if gd:
        gd.update_model({'$set': {'finish': True}})
        # 下载游戏任务检查
        if request.authed_user:
            UserTask.check_user_tasks(str(request.authed_user._id), DOWNLOAD_GAME, 1, str(gd.game))
    return {}


@app.route('/users/<string:uid>/games', methods=['GET'])
@util.jsonapi()
def user_sub_games(uid):
    """获取用户已订阅游戏 (GET)

    :uri: /users/<string:uid>/games
    :param maxs: 最后时间, 0代表当前时间, 无此参数按page来分页
    :param page: 页码(数据可能有重复, 建议按照maxs分页)
    :param nbr: 每页数量
    :returns: {'games': list, 'end_page': bool, 'maxs': timestamp}
    """
    params = request.values
    maxs = params.get('maxs', None)
    maxs = time.time() if maxs is not None and int(float(maxs)) == 0 else maxs and float(maxs)
    page = int(params.get('page', 1))
    pagesize = int(params.get('nbr', 10))

    games = list()
    gids = list()
    while len(games) < pagesize:
        gids = UserSubGame.sub_game_ids(uid, page, pagesize, maxs)
        # 下线游戏也需要展示在用户订阅列表中
        games.extend([g.format(exclude_fields=['subscribed'])
                      for g in Game.get_list(gids, check_online=False)])

        # 如果按照maxs分页, 不足pagesize个记录则继续查询
        if maxs is not None:
            obj = UserSubGame.get_by_ship(uid, gids[-1]) if gids else None
            maxs = obj.create_at if obj else 1000
            if len(gids) < pagesize:
                break
        else:
            break

    return {'games': games, 'end_page': len(gids) != pagesize, 'maxs': maxs}


@app.route('/games/<string:gid>', methods=['GET'])
@util.jsonapi()
def get_game(gid):
    """获取游戏详细信息 (GET)

    :uri: /games/<string:gid>
    :returns: object
    """
    game = Game.get_one(gid, check_online=False)
    if not game:
        return error.GameNotExist

    return game.format()


# TODO: delete opt from url
@app.route('/user/opt/subscribe-game', methods=['GET', 'POST'])
@util.jsonapi(login_required=True)
def sub_game():
    """订阅游戏 (GET|POST&LOGIN)

    :uri: /user/opt/subscribe-game
    :param game_id: 游戏id(批量订阅游戏id以逗号隔开)
    :returns: {}
    """
    user = request.authed_user
    gids = request.values.get('game_id', None)
    if not gids:
        return error.GameNotExist
    gids = [gid.strip() for gid in gids.split(',')]
    games = Game.get_list(gids, check_online=False)
    if not games:
        return error.GameNotExist

    key = 'lock:subgame:%s' % (str(user._id))
    with util.Lockit(Redis, key) as locked:
        if locked:
            return error.SubGameFailed

        sub_num = 0
        for game in games:
            usg = UserSubGame.get_by_ship(str(user._id), str(game._id))
            if not usg:
                usg = UserSubGame.init()
                usg.source = ObjectId(str(user._id))
                usg.target = ObjectId(str(game._id))
                usg.create_model()
                sub_num += 1

        # 订阅游戏任务检查
        if user:
            UserTask.check_user_tasks(str(user._id), SUB_GAME, sub_num)

    return {}


# TODO: delete opt from url
@app.route('/user/opt/popular_game', methods=['GET', 'POST'])
@util.jsonapi(login_required=True)
def pop_game():
    """设置常用游戏 (GET|POST&LOGIN)

        :uri: /user/opt/popular_game
        :param game_id: 游戏id(批量订阅游戏id以逗号隔开)
        :returns: {}
        """
    user = request.authed_user
    gids = request.values.get('game_id', None)
    uid = UserPopularGame.get_user_id(user._id)
    game_ids_list = UserPopularGame.get_game_ids(user._id)
    if not gids:
        for game_id in game_ids_list:
            usg = UserPopularGame.get_by_ship(str(user._id), str(game_id))
            usg.delete_model() if usg else None

        if not uid:
            usg = UserPopularGame.init()
            usg.source = ObjectId(str(user._id))
            usg.create_model()

        return {}
    gids = [gid.strip() for gid in gids.split(',')]
    games = Game.get_list(gids, check_online=False)
    if not games:
        return error.GameNotExist

    key = 'lock:popgame:%s' % (str(user._id))
    with util.Lockit(Redis, key) as locked:
        if locked:
            return error.PopGameFailed

        # 删除游戏
        for game_id in game_ids_list:
            # if game_id not in gids:
            usg = UserPopularGame.get_by_ship(str(user._id), str(game_id))
            usg.delete_model() if usg else None

        # 保存游戏
        for index, game in enumerate(games):
            # usg = UserPopularGame.get_by_ship(str(user._id), str(game._id))
            # if not usg:
            usg = UserPopularGame.init()
            usg.source = ObjectId(str(user._id))
            usg.target = ObjectId(str(game._id))
            usg.order = index
            usg.create_model()

    return {}


@app.route('/user/opt/live_games', methods=['GET'])
@util.jsonapi()
def live_games():
    """
    获取直播标签游戏列表 (GET)
    :uri: /user/opt/live_games
    :return: {'games': list}
    """
    user = request.authed_user
    games = Game.live_games()  # 设置直播标签的游戏
    gids = [str(gid) for gid, _ in games]
    if user:
        pids = UserPopularGame.get_game_ids(user._id)
        if pids:
            [gids.remove(p) for p in pids if p in gids]
    else:
        pids = LiveHotGame.hot_game_ids()
        if pids:
            [gids.remove(p) for p in pids if p in gids]

    games = [g.format() for g in Game.get_list(gids)]

    return {'games': games}


# TODO: delete opt from url
@app.route('/user/opt/unsubscribe-game', methods=['GET', 'POST'])
@util.jsonapi(login_required=True)
def unsub_game():
    """取消订阅游戏 (GET|POST&LOGIN)

    :uri: /user/opt/unsubscribe-game
    :param game_id: 游戏id
    :returns: {}
    """
    user = request.authed_user
    gid = request.values.get('game_id', None)
    game = Game.get_one(gid, check_online=False)
    if not game:
        return error.GameNotExist
    key = 'lock:unsubgame:%s' % (str(user._id))
    with util.Lockit(Redis, key) as locked:
        if locked:
            return error.SubGameFailed('取消订阅失败')
        usg = UserSubGame.get_by_ship(str(user._id), gid)
        usg.delete_model() if usg else None
    return {}


@app.route('/channels/games', methods=['GET'])
@util.jsonapi()
def channel_game():
    """获取频道内容 (GET)

    :uri: /channels/games
    :returns: [{'tag_id': string, 'name': string, 'games': list}, ...]
    """
    ret = list()
    cids = Category.all_category_ids()
    categories = Category.get_list(cids)
    for category in categories:
        gids = CategoryGame.category_game_ids(str(category._id))
        games = [g.format(exclude_fields=['subscribed']) for g in Game.get_list(gids)]
        ret.append(
            dict(games=games,
                 tag_id=str(category._id),
                 name=category.name,
                 icon_type=category.icon_type or 'icon')
        )
    return ret


@app.route('/migu/tags/<string:cid>/games/')
@app.route('/tags/<string:cid>/games', methods=['GET'])
@util.jsonapi()
def category_games(cid):
    """获取分类下的所有游戏 (GET)

    :uri: /tags/<string:cid>/games
    :uri migu: /migu/tags/<string:cid>/games/
    :returns: {'games': list}
    """
    gids = CategoryGame.category_game_ids(cid)
    games = [g.format(exclude_fields=['subscribed']) for g in Game.get_list(gids)]
    return {'games': games}


@app.route('/recommend/subscribe/games', methods=['GET'])
@util.jsonapi()
def recommend_subscribe_games():
    """获取推荐订阅游戏 (GET)

    :uri: /recommend/subscribe/games
    :returns: {'games': list}
    """
    gids = GameRecommendSubscribe.recommend_sub_ids()
    games = [g.format() for g in Game.get_list(gids)]
    return {'games': games}


@app.route('/webgames', methods=['GET'])
@util.jsonapi()
def online_web_games():
    """获取所有在线游戏列表 (GET)

    :uri: /webgames
    :param os: 平台 android, ios
    :return: {'games': list}
    """
    values = request.values
    platform = values.get('os', 'android')
    if platform == 'android':
        platforms = ['android', 'all']
    elif platform == 'ios':
        platforms = ['ios', 'all']
    else:
        return error.InvalidArguments
    games = WebGame.online_games()
    gids = [str(gid) for gid, _ in games]
    games = [g.format() for g in WebGame.get_list(gids) if g.os in platforms]
    games.sort(key=lambda x: x['order'])
    return {'games': games}


@app.route('/games/grids', methods=['GET'])
@util.jsonapi()
def all_game_grids():
    """
    获取游戏页所有宫格
    uri: /games/grids
    :param: os
    :return:  {'grids': list}
    """
    user = request.authed_user
    params = request.values
    os = params.get('os', None)
    channels = params.get('channels', None)
    version_code = int(params.get('version_code', 1))

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

    grids = list()
    _ids = GameGrid.all_ids()
    for b in GameGrid.get_list(_ids):
        if b.os and b.os != os:
            continue

        if (b.version_code_mix and b.version_code_mix > version_code) or\
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
        grids.append(b.format())

    return {'grids': grids}


@app.route('/games/ads', methods=['GET'])
@util.jsonapi()
def game_ads():
    """获取游戏页广告 (GET)

    :uri: /games/ads
    :param os: 平台
    :param channels: 渠道(可选)
    :param version_code: 版本号
    :returns: {'ads': list}
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
    _ids = GameAds.all_ad_ids()
    for b in GameAds.get_list(_ids):
        if b.os and b.os != os:
            continue

        if (b.version_code_mix and b.version_code_mix > version_code) or\
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

    return {'ads': sorted(banners, key=lambda x: x['order'])}


@app.route('/games/topics', methods=['GET'])
@util.jsonapi()
def game_topics():
    """获取游戏页专题 (GET)

    :uri: /games/topics
    :param os: 平台
    :param channels: 渠道(可选)
    :param version_code: 版本号
    :returns: {'topics': list}
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

    topics = list()
    _ids = GameTopic.all_ids()
    for b in GameTopic.get_list(_ids):
        if b.os and b.os != os:
            continue

        if (b.version_code_mix and b.version_code_mix > version_code) or\
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
        topics.append(b.format())

    return {'topics': topics}


@app.route('/games/topic_games', methods=['GET'])
@util.jsonapi()
def topic_games():
    """获取专题游戏 (GET)

    :uri: /games/topic_games
    :param: topic_id: 专题ID
    :param maxs: 最后时间, 0代表当前时间, 无此参数按page来分页
    :param page: 页码(数据可能有重复, 建议按照maxs分页)
    :param nbr: 每页数量
    :return: {'games': <Game>list, 'topic':<GameTopic>, 'end_page': bool, 'maxs': timestamp}
    """
    tid = request.values.get('topic_id', None)
    maxs = request.values.get('maxs', None)
    page = int(request.values.get('page', 1))
    pagesize = int(request.values.get('nbr', 10))

    if not tid:
        return error.InvalidArguments

    topic = GameTopic.get_one(tid)
    if not topic:
        return error.GameTopicNotExist
    # 增加访问次数
    count = int(topic.get('visitor_count', 0)+1)
    topic.update_model({'$set': {'visitor_count': count}})
    topic.visitor_count = count

    topic = topic.format()

    games = list()
    while len(games) < pagesize:
        ids = TopicGame.topic_game_ids(tid, page, pagesize, maxs)
        tgids, gids = [i[0] for i in ids], [i[1] for i in ids]
        gms = [g.format() for g in Game.get_list(gids)]
        games.extend(gms)

        # 如果按照maxs分页, 不足pagesize个记录则继续查询
        if maxs is not None:
            obj = TopicGame.get_one(tgids[-1], check_online=False) if tgids else None
            maxs = obj.order if obj else 0
            if len(gids) < pagesize:
                break
        else:
            break
    return {'games': games, 'topic': topic, 'end_page': len(gids) != pagesize, 'maxs': maxs}


@app.route('/webgames/ads', methods=['GET'])
@util.jsonapi()
def webgame_ads():
    """获取页游广告 (GET)

    :uri: /webgames/ads
    :param os: 平台
    :param channels: 渠道(可选)
    :param version_code: 版本号
    :returns: {'ads': list}
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
    _ids = WebGameAds.all_ad_ids()
    for b in WebGameAds.get_list(_ids):
        if b.os and b.os != os:
            continue

        if (b.version_code_mix and b.version_code_mix > version_code) or\
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

    return {'ads': sorted(banners, key=lambda x: x['order'])}


@app.route('/games/home', methods=['GET'])
@util.jsonapi()
def game_home():
    """
    获取游戏页首页内容
    uri: /games/home
    :param os: 平台
    :param channels: 渠道(可选)
    :param version_code: 版本号
    :return:  {'grids': list}
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

    def my_filter(data):
        result = list()
        for b in data:
            if b.os and b.os != os:
                continue

            if (b.version_code_mix and b.version_code_mix > version_code) or\
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

            result.append(b.format())
        return result

    # 游戏页宫格
    _ids = GameGrid.all_ids()
    grids = my_filter(GameGrid.get_list(_ids))

    # 游戏页广告
    _ids = GameAds.all_ad_ids()
    banners = my_filter(GameAds.get_list(_ids))

    # 游戏页主推游戏
    _ids = GameMainstay.all_ids()
    mainstays = my_filter(GameMainstay.get_list(_ids))

    # 游戏页热门游戏
    _ids = HotRecommendGame.hot_game_ids()
    hot_games = [g.format() for g in Game.get_list(_ids)]

    # 游戏页模块内容
    _ids = GameModule.all_ids_by_os(os)
    modules = [i.format() for i in GameModule.get_list(_ids)
               if ModuleGame.module_game_ids(str(i._id))]

    return {'grids': grids, 'ads': banners, 'mainstays': mainstays,
            'hot_games': hot_games, 'modules': modules}


@app.route('/games/mainstays', methods=['GET'])
@util.jsonapi()
def game_mainstays():
    """获取主推游戏 (GET)

    :uri: /games/mainstays
    :param os: 平台
    :param channels: 渠道(可选)
    :param version_code: 版本号
    :returns: {'mainstays': list}
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
    _ids = GameMainstay.all_ids()
    for b in GameMainstay.get_list(_ids):
        if b.os and b.os != os:
            continue

        if (b.version_code_mix and b.version_code_mix > version_code) or\
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

    return {'mainstays': sorted(banners, key=lambda x: x['order'])}


@app.route('/games/modules', methods=['GET'])
@util.jsonapi()
def game_modules():
    """
    获取游戏页所有游戏模块
    uri: /games/modules
    :param os: 平台
    :return:  {'modules': <GameModule>list}
    """
    params = request.values
    os = params.get('os', None)

    if not os:
        return error.InvalidArguments

    _ids = GameModule.all_ids_by_os(os)
    modules = [i.format() for i in GameModule.get_list(_ids)
               if ModuleGame.module_game_ids(str(i._id))]
    return {'modules': modules}


@app.route('/games/module_games', methods=['GET'])
@util.jsonapi()
def module_games():
    """获取分类下的所有游戏 (GET)

    :uri: /games/module_games
    :param module_id: 游戏模块id
    :returns: {'games': list}
    """
    params = request.values
    module_id = params.get('module_id', None)

    if not module_id:
        return error.InvalidArguments

    module = GameModule.get_one(module_id)
    if not module:
        return error.GameModuleNotExist

    gids = ModuleGame.module_game_ids(module_id)
    games = [g.format(exclude_fields=['subscribed']) for g in Game.get_list(gids)]
    return {'games': games}


@app.route('/games/hot_games', methods=['GET'])
@util.jsonapi()
def hot_games():
    """获取游戏页的所有热门游戏 (GET)
    :uri: /games/hot_games
    :returns: {'games': list}
    """
    gids = HotRecommendGame.hot_game_ids()
    games = [g.format(exclude_fields=['subscribed']) for g in Game.get_list(gids)]
    return {'games': games}


@app.route('/games/toplists', methods=['GET'])
@util.jsonapi()
def game_poplists():
    """
    获取所有游戏排行
    :uri: /games/toplists
    :param os: 平台
    :param channels: 渠道号【可选】
    :param version_code: 版本号
    :return: {'toplists': <TopList> list}
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

    toplists = list()
    _ids = TopList.all_ids_by_os(os)
    for b in TopList.get_list(_ids):
        if b.os and b.os != os:
            continue

        if (b.version_code_mix and b.version_code_mix > version_code) or\
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

        toplists.append(b.format())

    return {'toplists': toplists}


@app.route('/games/toplist_games', methods=['GET'])
@util.jsonapi()
def toplist_games():
    """获取排行游戏 (GET)

    :uri: /games/toplist_games
    :param: toplist_id: 排行ID
    :return: {'games': <Game>list, 'toplist':<TopList>list}
    """
    tid = request.values.get('toplist_id', None)

    if not tid:
        return error.InvalidArguments

    toplist = TopList.get_one(tid)
    if not toplist:
        return error.GameTopListNotExist

    ids = TopListGames.toplist_game_ids(tid)
    games = [g.format() for g in Game.get_list(ids)]
    return {'games': games, 'toplist': toplist.format()}


@app.route('/games/chess_configs', methods=['GET'])
@util.jsonapi()
def game_chess_configs():
    """
    获取所有棋牌分类
    :uri: /games/chess_configs
    :param os: 平台
    :param channels: 渠道号【可选】
    :param version_code: 版本号
    :return: {'chess_configs': <ChessConfig> list}
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

    configs = list()
    _ids = ChessConfig.all_ids_by_os(os)
    for b in ChessConfig.get_list(_ids):
        if b.os and b.os != os:
            continue

        if (b.version_code_mix and b.version_code_mix > version_code) or\
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

        configs.append(b.format())

    return {'chess_configs': configs}


@app.route('/games/chess_games', methods=['GET'])
@util.jsonapi()
def chess_games():
    """获取棋牌分类下的游戏 (GET)

    :uri: /games/chess_games
    :param: chess_id: 棋牌分类ID
    :return: {'games': <Game>list, 'chess_config':<ChessConfig>}
    """
    tid = request.values.get('chess_id', None)

    if not tid:
        return error.InvalidArguments

    chess_config = ChessConfig.get_one(tid)
    if not chess_config:
        return error.ChessConfigNotExist

    ids = ChessGames.chess_game_ids(tid)
    games = [g.format() for g in Game.get_list(ids)]
    return {'games': games, 'chess_config': chess_config.format()}


@app.route('/games/vip_configs', methods=['GET'])
@util.jsonapi()
def game_vip_configs():
    """
    获取所有会员专区
    :uri: /games/vip_configs
    :param os: 平台
    :param channels: 渠道号【可选】
    :param version_code: 版本号
    :return: {'vip_configs': <VipConfig> list}
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

    configs = list()
    _ids = VipConfig.all_ids_by_os(os)
    for b in VipConfig.get_list(_ids):
        if b.os and b.os != os:
            continue

        if (b.version_code_mix and b.version_code_mix > version_code) or\
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

        configs.append(b.format())

    return {'vip_configs': configs}


@app.route('/games/vip_games', methods=['GET'])
@util.jsonapi()
def vip_games():
    """获取会员专区下的游戏 (GET)

    :uri: /games/vip_games
    :param: vip_id: 会员专区ID
    :return: {'games': <Game>list, 'vip_config':<VipConfig>}
    """
    tid = request.values.get('vip_id', None)

    if not tid:
        return error.InvalidArguments

    vip_config = VipConfig.get_one(tid)
    if not vip_config:
        return error.VipConfigNotExist

    ids = VipGames.vip_game_ids(tid)
    games = [g.format() for g in Game.get_list(ids)]
    return {'games': games, 'vip_config': vip_config.format()}


@app.route('/games/vip/giftcode/list', methods=['GET'])
@util.jsonapi()
def vip_gift_codes():
    """
    获取会员专区下的会员礼包
    :uri: /games/vip/giftcode/list
    :param: vip_id：会员专区ID
    :return:  {'gift_codes': <GiftCode>list, 'vip_config': <VipConfig>}
    """
    tid = request.values.get('vip_id', None)

    if not tid:
        return error.InvalidArguments

    vip_config = VipConfig.get_one(tid)
    if not vip_config:
        return error.VipConfigNotExist

    ids = VipGiftCode.vip_giftcode_ids(tid)
    gift_codes = [g.format() for g in VipGiftCode.get_list(ids)]
    return {'gift_codes': gift_codes, 'vip_config': vip_config.format()}


@app.route('/games/vip/giftcode/draw', methods=['POST', 'GET'])
@util.jsonapi(login_required=True)
def draw_gift_code():
    """
    VIP用户获取礼包兑换码
    :uri: /games/vip/giftcode/draw
    :param: giftcode_id 会员游戏礼包id
    :return:
    """
    user = request.authed_user
    uid = str(user._id)
    gcid = request.values.get('giftcode_id')
    if not gcid:
        return error.InvalidArguments

    giftcode = VipGiftCode.get_one(gcid, check_online=True)
    if not giftcode:
        return error.GiftCodeNotExist

    if giftcode.left <= 0:
        return error.StoreError('没有可领取的礼包了！')

    vip = MiguPay.check_user_vip_level(user.phone)
    if isinstance(vip, error.ApiError):
        return vip
    if not (vip['vip5']['subscribed'] or vip['vip10']['subscribed']):
        return error.StoreError('没有领取权限！')

    # 查看是否有抽奖机会
    left_chances = Marketing.query_lottery_chance(user.partner_migu['id'], giftcode.campaign_id)
    if isinstance(left_chances, error.ApiError):
        return error.StoreError('领取礼包失败，请稍后重试')

    # 当前没有剩余机会的时候，需要先验证是否可以抽奖并获取抽奖机会
    if left_chances <= 0:
        key = 'lock:store:%s' % (str(user._id))
        with util.Lockit(Redis, key) as locked:
            if locked:
                return error.StoreError('领取礼包太频繁')

            if gcid in UserGiftCodeOrder.get_user_gift_code_ids(uid):
                return error.StoreError('已经领取过该礼包')

            # 进行抽奖机会的兑换
            ret = Marketing.execute_campaign(user.partner_migu['id'], user.phone,
                                             [giftcode.campaign_id], trigger=10218)
            if not ret or isinstance(ret, error.ApiError):
                return error.StoreError('兑换领取机会失败')

    # 调用营销平台进行抽奖
    prize = Marketing.draw_lottery(user.partner_migu['id'], giftcode.campaign_id)
    if isinstance(prize, error.ApiError):
        return prize
    if not prize:
        return error.StoreError('获取游戏兑换码失败')

    exchange_code = None
    for row in prize.get('extensionInfo', []):
        if row['key'] == 'exchangeCode':
            exchange_code = row['value']
            break
    if not exchange_code:
        return error.StoreError('获取游戏兑换码失败')

    order = UserGiftCodeOrder.create(
        user_id=str(user._id),
        vgc_id=gcid,
        vgc_name=giftcode.name,
        campaign_id=giftcode.campaign_id,
        gift_code=exchange_code,
        result=json.dumps(prize),
        recid=prize.get('id', ''),
        expire_at=util.timestamp2datetime(giftcode.exchange_expire_at),
        status=const.ORDER_FINISHED,
        user_ip=request.access_route[0]
    )
    UserGiftCodeOrder.clear_redis(str(user._id))

    # 更新库存
    giftcode.update_model({'$inc': {'left': -1, 'used': 1}})
    return {'order': order.format()}


@app.route('/games/vip/giftcode/orders', methods=['GET'])
@util.jsonapi(login_required=True)
def user_giftcode_orders():
    """
    用户获得游玩发放礼包兑换码的订单列表
    :uri: /games/vip/giftcode/orders
    :param: page 页码
    :param: nbr  每页长度
    :return: {'orders': <Order>list, 'end_page': bool}
    """
    user = request.authed_user
    page = int(request.values.get('page', 1))
    pagesize = int(request.values.get('nbr', 10))

    # 获得游玩发放礼包兑换码的订单
    orders = UserGiftCodeOrder.get_user_orders(str(user._id), page, pagesize)
    orders = [order.format() for order in orders]
    return {'orders': orders, 'end_page': len(orders) != pagesize}

