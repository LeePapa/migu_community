# -*- coding: utf8 -*-
from wanx import app

import hashlib
import os
import random
import requests
import json


class WeiXin(object):
    api_url = 'https://api.weixin.qq.com/sns/userinfo'

    def __init__(self, token, openid):
        self._token = token
        self._api_url = self.api_url
        self._openid = openid

    def get_open_info(self, first_login=False):
        payload = {
            'access_token': self._token,
            'openid': self._openid
        }
        try:
            resp = requests.get(self._api_url, params=payload, timeout=5)
        except requests.exceptions.RequestException:
            return {}
        data = json.loads(resp.content)
        info = {}
        if 'openid' in data:
            try:
                info = dict(
                    openid=data['openid'],
                    name='$wx$%s%s' % (self._openid[-4:], random.randint(1000, 9999)),
                    nickname=data['nickname'],
                    gender=data['sex'],
                )
                # 第一次存储头像
                if data['headimgurl'] and first_login:
                    req = requests.get(data['headimgurl'])
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
