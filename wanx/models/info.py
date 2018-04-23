# -*- coding: utf8 -*-
from urlparse import urljoin

import pymongo
from bson.objectid import ObjectId
from wanx import app
from wanx.base.spam import Spam
from wanx.base.xmongo import DB
from wanx.base.xredis import Redis
from wanx.base import util
from wanx.models import Document
from redis import exceptions

import os


class EsInformation(Document):
    """
    Electronic Sports Information
    """
    collection = DB.es_information
    ALL_IDS = 'info:es'
    if os.environ.get('WXENV') == 'Production':
        action = 'http://api.cmgame.com/client/newsDetail.html?WXpage=newsDetail&newsId=%s'
    elif os.environ.get('WXENV') == 'Stage':
        action = 'http://test.cmgame.com/client/newsDetail.html?WXpage=newsDetail&newsId=%s'
    else:
        action = 'http://test-api.molizhen.com/client/newsDetail.html?WXpage=newsDetail&newsId=%s'

    def format(self, platform='android'):
        covers = [urljoin(app.config.get("MEDIA_URL"), i) for i in [self.cover1, self.cover2, self.cover3] if i]
        url = self.action % str(self._id)
        share_url = self.action % str(self._id)+'&outapp=1'
        data = {
            'id': str(self._id),
            'create_at': self.create_at,
            'title': self.title,
            'covers': covers,
            'order': self.order,
            'content': self.content,
            'author': self.author_name,
            'action': util.format_action(url, share_url, platform=platform)
        }
        return data

    @classmethod
    @util.cached_list(lambda cls: cls.ALL_IDS, snowslide=True)
    def _load_all_ids(cls):
        infos = list(cls.collection.find(
            {'status': 0},
            {'_id': 1, 'create_at': 1}
        ).sort([('order', pymongo.ASCENDING), ('create_at', pymongo.DESCENDING)]))
        return [str(i['_id']) for i in infos]

    @classmethod
    def info_ids(cls, page, pagesize):
        key = cls.ALL_IDS
        if not Redis.exists(key):
            cls._load_all_ids()
        try:
            start = (page - 1) * pagesize
            stop = start + pagesize - 1
            ids = Redis.lrange(key, start, stop)
        except exceptions.ResponseError:
            # 列表为空时key对应的value是一个string
            ids = []
        return list(ids)



