# -*- coding: utf8 -*-
import time
from bson.objectid import ObjectId
from flask import request, redirect, jsonify
from wanx.base import util, error, const
from wanx import app
from wanx.base.xredis import Redis
from wanx.models.game import Game
from wanx.models.home import UserSubObj

from wanx.models.show import Show, ShowChannel, UserSubShow
from wanx.models.video import Video


@app.route('/show/list', methods=['GET'])
@util.jsonapi()
def show_list():
    """
    获取栏目列表接口
    :uri: /show/list
    :param: page int default 1
    :param: nbr int default 10
    :return: {'shows': <Show>list, 'end_page': bool}
    """
    params = request.values
    page = int(params.get('page', 1))
    nbr = int(params.get('nbr', 10))

    ids = Show.get_show_ids(page, nbr)
    shows = [s.format() for s in Show.get_list(ids)]

    return {'shows': shows, 'end_page': ids.__len__() != nbr}


@app.route('/show/info', methods=['GET'])
@util.jsonapi()
def show_info():
    """
    栏目详情
    :uri: /show/info
    :param: show_id
    :return: {'show': <Show>, 'channels': <ShowChannel>list}
    """
    sid = request.values.get('show_id', '')
    show = Show.get_one(sid)
    if not show:
        return error.ShowNotExist

    cids = ShowChannel.all_channel_ids(sid)
    channels = [c.format() for c in ShowChannel.get_list(cids)]

    return {'show': show.format(), 'channels': channels}


@app.route('/show/channel/videos', methods=['GET'])
@util.jsonapi()
def show_channel_videos():
    """
    栏目频道视频列表
    :uri: /show/channel/videos
    :param: channel_id
    :param: page
    :param: nbr
    :return: {'videos': <Video>list, 'end_page': bool}
    """
    params = request.values
    channel_id = params.get('channel_id')
    page = int(params.get('page', 1))
    nbr = int(params.get('nbr', 10))

    if channel_id is None:
        return error.InvalidArguments

    channel = ShowChannel.get_one(channel_id)
    if not channel:
        return error.ShowChannelNotExist

    vids = Video.show_channel_ids(channel_id, page, nbr)
    videos = [v.format() for v in Video.get_list(vids)]

    return {'videos': videos, 'end_page': len(vids) != nbr}


@app.route('/user/opt/subscribe-show', methods=['POST', 'GET'])
@util.jsonapi(login_required=True)
def sub_show():
    """
    订阅栏目
    :uri: /show/sub
    :param: show_id
    :return: {}
    """
    show_id = request.values.get('show_id')
    if not show_id:
        return error.InvalidArguments

    show = Show.get_one(show_id)
    if not show:
        return error.ShowNotExist

    uid = str(request.authed_user._id)
    key = 'lock:subshow:%s' % uid
    with util.Lockit(Redis, key) as locked:
        if locked:
            return error.SubGameFailed

        if not UserSubShow.is_followed(uid, show_id):
            uss = UserSubShow.init()
            uss.source = ObjectId(uid)
            uss.target = ObjectId(show_id)
            uss.create_model()

    return {}


@app.route('/user/opt/unsubscribe-show', methods=['POST', 'GET'])
@util.jsonapi(login_required=True)
def unsub_show():
    """
    取消订阅栏目
    :uri: /show/sub
    :param: show_id
    :return: {}
    """
    show_id = request.values.get('show_id')
    if not show_id:
        return error.InvalidArguments

    show = Show.get_one(show_id)
    if not show:
        return error.ShowNotExist

    uid = str(request.authed_user._id)
    key = 'lock:unsubshow:%s' % uid
    with util.Lockit(Redis, key) as locked:
        if locked:
            return error.SubGameFailed('取消订阅失败')
        uss = UserSubShow.get_by_ship(uid, show_id)
        uss and uss.delete_model()

    return {}


@app.route('/user/subscribed/all', methods=['GET'])
@util.jsonapi(login_required=True)
def user_subs():
    """
    用户订阅内容
    :uri: /user/subscribed/all
    :param: page
    :param: nbr
    :param: maxs
    :return: {'objs': <SubObj>list}
    """
    user = request.authed_user;
    uid = str(user._id)

    params = request.values
    page = int(params.get('page', 1))
    pagesize = int(params.get('nbr', 10))
    maxs = params.get('maxs', None)
    maxs = time.time() if maxs is not None and int(float(maxs)) == 0 else maxs and float(maxs)

    objs = list()
    ids = list()
    while len(objs) < pagesize:
        ids = UserSubObj.user_sub_obj_ids(uid, page, pagesize, maxs)
        for _id, _ in ids:
            _obj = Game.get_one(_id) or Show.get_one(_id)
            _obj and objs.append(_obj.format(exclude_fields=['subscribed', 'obj_type']))

        # 如果按照maxs分页, 不足pagesize个记录则继续查询
        if maxs is not None:
            maxs = ids[-1][1] if ids else 1000
            if len(ids) < pagesize:
                break
        else:
            break

    return {'objs': objs, 'end_page': len(ids) != pagesize, 'maxs': maxs}


