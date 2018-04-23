# -*- coding: utf8 -*-
"""
调用游玩直播接口相关
"""
from urlparse import urljoin

from flask import request

from wanx.base.log import print_log
from wanx.base.xredis import Redis
from wanx.models.xconfig import Config
from wanx.models.user import User
from wanx.models.game import Game

import requests
import json


class Xlive(object):
    ALL_LIVES = 'lives:all'
    GIFT_COUNTER = 'live:gift:counter:%(event_id)s:%(user_id)s:%(gift_id)s'

    @classmethod
    def format(cls, live, exclude_fields=[]):
        user_ex_fields = []
        game_ex_fields = []
        for field in exclude_fields:
            if field.startswith('user__'):
                _, _field = field.split('__')
                user_ex_fields.append(_field)
            elif field.startswith('game__'):
                _, _field = field.split('__')
                game_ex_fields.append(_field)

        ut = request.values.get("ut", None)
        uid = User.uid_from_token(ut)

        user_id = live.get('user_id', None)

        from wanx.models.home import Share
        share_title = None
        if str(user_id) == uid:
            share_title = Share.get_by_self_live().title
        else:
            share_title = Share.get_by_others_live().title

        game = Game.get_one(str(live['game_id']), check_online=False)
        user = User.get_one(str(live['user_id']), check_online=False)
        live['user'] = user and user.format(exclude_fields=user_ex_fields)
        live['game'] = game and game.format(exclude_fields=game_ex_fields)
        live['from_following'] = live.get('from_following', False)
        live['share_title'] = share_title
        # 强行移除ut
        live.pop('ut', None)
        return live

    @classmethod
    def get_all_lives(cls):
        """所有直播间列表
        """
        # 后台配置是否开启直播服务, 默认开启
        api_url = Config.fetch('live_api_url', None, str)
        if not api_url:
            return []

        api_url = urljoin(api_url, '/events')
        lives = Redis.get(cls.ALL_LIVES)
        if not lives:
            try:
                resp = requests.get(api_url, timeout=2)
            except requests.exceptions.Timeout:
                print_log('xlive', '[get_all_lives]: connection timeout')
                return []
            except:
                print_log('xlive', '[get_all_lives]: connection error')
                return []

            if resp.status_code != requests.codes.ok:
                print_log('xlive', '[get_all_lives]: status_code not ok')
                return []

            lives = resp.content
            lives = json.loads(lives)['data']['live']
            Redis.setex(cls.ALL_LIVES, 5, json.dumps(lives))
        else:
            lives = json.loads(lives)

        # 按照人气排序
        lives.sort(key=lambda x: x['count'], reverse=True)
        return lives

    @classmethod
    def get_live(cls, live_id):
        all_lives = cls.get_all_lives()
        lives = filter(lambda x: x['event_id'] == live_id, all_lives)
        return lives[0] if lives else None

    @classmethod
    def get_user_live(cls, user_id):
        all_lives = cls.get_all_lives()
        lives = filter(lambda x: x['user_id'] == user_id, all_lives)
        return lives[0] if lives else None

    @classmethod
    def get_game_lives(cls, gid):
        """游戏所有直播间列表
        """
        all_lives = cls.get_all_lives()
        game_lives = filter(lambda x: x['game_id'] == gid, all_lives)
        # 按照观看人数排序
        game_lives.sort(key=lambda x: x['count'], reverse=True)
        return game_lives

    @classmethod
    def get_user_lives(cls, uid):
        """单用户的直播间列表
        """
        all_lives = cls.get_all_lives()
        user_lives = filter(lambda x: x['user_id'] == uid, all_lives)
        # 按照创建时间排序
        user_lives.sort(key=lambda x: x['create_at'], reverse=True)
        return user_lives

    @classmethod
    def get_users_lives(cls, uids):
        """多个用户的直播间列表
        """
        all_lives = cls.get_all_lives()
        users_lives = filter(lambda x: x['user_id'] in uids, all_lives)
        # 按照创建时间排序
        users_lives.sort(key=lambda x: x['create_at'], reverse=True)
        return users_lives

    @classmethod
    def send_live_msg(cls, data, mode='gift'):
        """发送直播弹幕信息
        """
        # 后台配置是否开启直播服务, 默认开启
        api_url = Config.fetch('live_api_url', None, str)
        if not api_url:
            return

        uri = '/events/%s/notify' % (data['event_id'])
        api_url = urljoin(api_url, uri)
        msg = {'type': mode, 'data': data}
        try:
            requests.post(api_url, json=msg, timeout=2)
        except requests.exceptions.Timeout:
            print_log('xlive', '[send_live_msg]: connection timeout')
        except:
            print_log('xlive', '[send_live_msg]: connection error')

    @classmethod
    def get_match_live(cls, uid, name):
        """根据主播id和直播间name获取赛事直播
        """
        all_lives = cls.get_all_lives()
        print_log('xlive', '[get_match_live - all_lives]: {0}'.format(all_lives))

        match_live = filter(lambda x: x['user_id'] == uid and x['name'] == name, all_lives)
        match_live.sort(key=lambda x: x['create_at'], reverse=True)

        print_log('xlive', '[get_match_live - match_live]: {0}'.format(match_live))

        return match_live

    @classmethod
    def get_user_send_gift_count(cls, event_id, user_id, gift_id, num):
        key = cls.GIFT_COUNTER % {'event_id': event_id, 'user_id': user_id, 'gift_id': gift_id}
        return Redis.incrby(key, num)

    @classmethod
    def get_event(cls, event_id):
        """获取直播
        """
        # 后台配置是否开启直播服务, 默认开启
        api_url = Config.fetch('live_api_url', None, str)
        if not api_url:
            return []

        api_url = urljoin(api_url, '/events/{0}'.format(event_id))
        try:
            resp = requests.get(api_url, timeout=2)
        except requests.exceptions.Timeout:
            print_log('xlive', '[get_event]: connection timeout')
            return []
        except:
            print_log('xlive', '[get_event]: connection error')
            return []

        if resp.status_code != requests.codes.ok:
            print_log('xlive', '[get_event]: status_code not ok')
            return []

        live = resp.content
        live = json.loads(live)['data']

        return live
