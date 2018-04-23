# -*- coding: utf8 -*-
"""
调用比赛接口相关
"""
from urlparse import urljoin
from wanx import app
import requests
from wanx.base.log import print_log
import json


class Xmatch(object):
    @classmethod
    def getbattle(cls, live_user_id, live_name):
        """所有直播用户id和直播间名称获取对战id
        """
        api_url = app.config.get('MATCH_SERVER_URL', None)
        if not api_url:
            return None

        api_url = urljoin(api_url, '/migu_match/getbattlebylive?live_user_id={0}&live_name={1}'
                          .format(live_user_id, live_name))
        try:
            resp = requests.get(api_url, timeout=2)
        except requests.exceptions.Timeout:
            print_log('xmatch', '[getbattle]: connection timeout')
            return None
        except:
            print_log('xmatch', '[getbattle]: connection error')
            return None
        battle = resp.content
        battle = json.loads(battle)
        return battle
