# -*- coding: utf8 -*-
from urlparse import urljoin

import pymongo
from redis import exceptions
from flask import request
from bson.objectid import ObjectId

from wanx.models import Document
from wanx.base.xredis import Redis
from wanx.base.xmongo import DB
from wanx.base import util, const
from wanx import app


class Show(Document):
    """
    栏目
    """
    collection = DB.shows
    ALL_IDS = 'shows:all'

    def format(self, exclude_fields=[]):
        sid = str(self._id)
        data = {
            'id': sid,
            'create_at': self.create_at,
            'name': self.name,
            'icon': urljoin(app.config.get("MEDIA_URL"), self.icon),
            'description': self.desc,
            'subscribed': False,
            'subscription_count': max(self.sub_count or 0, 0),
            'video_count': max(self.video_count or 0, 0)
        }
        if 'subscribed' not in exclude_fields:
            uid = request.authed_user and str(request.authed_user._id)
            data['subscribed'] = UserSubShow.is_followed(uid, sid)
        if 'obj_type' in exclude_fields:
            data['obj_type'] = 'show'
        return data

    @classmethod
    @util.cached_list(lambda cls: cls.ALL_IDS, snowslide=True)
    def _load_all_ids(cls):
        ids = list(cls.collection.find(
            {},
            {'_id': 1, 'order': 1, 'create_at': 1}
        ).sort([('order', pymongo.ASCENDING), ('create_at', pymongo.DESCENDING)]))
        return [i['_id'] for i in ids]

    @classmethod
    def get_show_ids(cls, page, pagesize):
        key = cls.ALL_IDS
        if not Redis.exists(key):
            cls._load_all_ids()
        try:
            start = (page - 1) * pagesize
            stop = start + pagesize - 1
            ids = Redis.lrange(key, start, stop)
        except exceptions.ResponseError:
            ids = []
        return list(ids)


class ShowChannel(Document):
    """
    栏目频道
    """
    collection = DB.show_channels
    SHOW_CHANNEL_IDS = 'show:channel:%(sid)s'

    def format(self):
        data = {
            'id': str(self._id),
            'create_at': self.create_at,
            'name': self.name,
            'icon': urljoin(app.config.get("MEDIA_URL"), self.icon),
            'description': self.desc,
            'video_count': max(self.video_count or 0, 0),
            'vv': max(self.play_count or 0, 0),
            'update_at': self.update_at or self.create_at,
        }
        return data

    @classmethod
    @util.cached_list(lambda cls, sid: cls.SHOW_CHANNEL_IDS % {'sid': sid}, snowslide=True)
    def _load_show_channels(cls, sid):
        channels = list(cls.collection.find(
            {'show': ObjectId(sid)},
            {'_id': 1, 'update_at': 1}
        ).sort([('order', pymongo.ASCENDING), ('create_at', pymongo.DESCENDING)]))

        latest = reduce(lambda x, y: x if x.get('update_at', 0) > y.get('update_at', 0) else y, channels)
        ids = [latest['_id']]
        ids.extend([c['_id'] for c in channels if c['_id'] != latest['_id']])
        return tuple(ids)

    @classmethod
    def all_channel_ids(cls, sid):
        key = cls.SHOW_CHANNEL_IDS % {'sid': sid}
        if not Redis.exists(key):
            cls._load_show_channels(sid)
        try:
            ids = Redis. lrange(key, 0, -1)
        except exceptions.ResponseError:
            ids = []
        return list(ids)


class UserSubShow(Document):
    """
    用户订阅栏目
    """
    collection = DB.user_sub_show
    SUB_SHOW_IDS = 'show:usub:%(uid)s'  # 用户订阅的游戏队列

    @classmethod
    @util.cached_zset(lambda cls, uid: cls.SUB_SHOW_IDS % {'uid': uid}, snowslide=True)
    def _load_sub_show_ids(cls, uid):
        games = list(cls.collection.find(
            {'source': ObjectId(uid)},
            {'target': 1, 'create_at': 1}
        ).sort("create_at", pymongo.DESCENDING))
        ret = list()
        for g in games:
            ret.extend([g['create_at'], str(g['target'])])
        return tuple(ret)

    @classmethod
    def sub_show_ids(cls, uid, page=None, pagesize=None, maxs=None):
        key = cls.SUB_SHOW_IDS % {'uid': uid}
        if not Redis.exists(key):
            cls._load_sub_show_ids(uid)
        try:
            # 不进行分页
            if page is None and pagesize is None and maxs is None:
                return Redis.zrevrange(key, 0, -1)
            if maxs:
                ids = Redis.zrevrangebyscore(key, '(%.6f' % (maxs), '-inf', start=0, num=pagesize)
            else:
                start = (page - 1) * pagesize
                stop = start + pagesize - 1
                ids = Redis.zrevrange(key, start, stop)
        except exceptions.ResponseError:
            ids = []
        return list(ids)

    @classmethod
    def get_by_ship(cls, uid, sid):
        uss = cls.collection.find_one({
            'source': ObjectId(uid),
            'target': ObjectId(sid)
        })
        return cls(uss) if uss else None

    @classmethod
    def is_followed(cls, uid, sid):
        key = cls.SUB_SHOW_IDS % {'uid': uid}
        if not Redis.exists(key):
            cls._load_sub_show_ids(uid)
        if not Redis.exists(key):
            return False
        try:
            followed = Redis.zrank(key, str(sid))
        except exceptions.ResponseError:
            followed = None
        return followed is not None

    def create_model(self):
        _id = super(UserSubShow, self).create_model()
        if _id:
            # 更新栏目订阅人数
            game = Show.get_one(str(self.target), check_online=False)
            game.update_model({'$inc': {'sub_count': 1}})

            # 更新用户订阅游戏数量
            from wanx.models.user import User
            user = User.get_one(str(self.source), check_online=False)
            user.update_model({'$inc': {'subscription_count': 1}})

            key = self.SUB_SHOW_IDS % ({'uid': str(self.source)})
            # 订阅后需要删除Redis缓存以便与订阅游戏合并
            Redis.delete(key)

        return _id

    def delete_model(self):
        ret = super(UserSubShow, self).delete_model()
        if ret:
            # 更新栏目订阅人数
            game = Show.get_one(str(self.target), check_online=False)
            game.update_model({'$inc': {'sub_count': -1}})

            # 更新用户订阅游戏数量
            from wanx.models.user import User
            user = User.get_one(str(self.source), check_online=False)
            user.update_model({'$inc': {'subscription_count': -1}})

            key = self.SUB_SHOW_IDS % ({'uid': str(self.source)})
            try:
                Redis.zrem(key, str(self.target))
            except exceptions.ResponseError:
                Redis.delete(key)

        return ret


