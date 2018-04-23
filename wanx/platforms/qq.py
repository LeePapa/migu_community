# -*- coding: utf8 -*-
from wanx import app

import hashlib
import os
import random
import requests
import json


class QQ(object):
    api_url = 'https://graph.qq.com/user/get_user_info'
    consumer_key = '1104981500'

    def __init__(self, token, openid):
        self._token = token
        self._api_url = self.api_url
        self._consumer_key = self.consumer_key
        self._openid = openid

    def get_open_info(self, first_login=False):
        payload = {
            'access_token': self._token,
            'openid': self._openid,
            'oauth_consumer_key': self._consumer_key
        }
        try:
            resp = requests.get(self._api_url, params=payload, timeout=5)
        except requests.exceptions.RequestException:
            return {}
        data = json.loads(resp.content)
        info = {}
        if int(data['ret']) == 0:
            try:
                info = dict(
                    openid=self._openid,
                    name='$qq$%s%s' % (self._openid[-4:], random.randint(1000, 9999)),
                    nickname=data['nickname'].decode('utf8'),
                )
                # 存储头像
                if data['figureurl_qq_1'] and first_login:
                    req = requests.get(data['figureurl_qq_1'])
                    md5 = hashlib.md5(req.content)
                    name = md5.hexdigest()
                    folder = os.path.join(app.config.get("STATIC_BASE"), 'images', name[:3])
                    if not os.path.exists(folder):
                        os.makedirs(folder)
                    path = os.path.join(folder, name + ".jpeg")
                    url = os.path.join("/images/", name[:3], name + ".jpeg")
                    with open(path, "wb") as image:
                        image.write(req.content)
                    info['logo'] = url
                    info['photo'] = url
            except KeyError:
                return {}
        return info
