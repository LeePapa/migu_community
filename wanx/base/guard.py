# -*- coding: utf8 -*-
from wanx.base.xredis import Redis

import uuid
import hashlib


class Guard(object):
    SECRET_MAP = {
        '49172158': 'cc9258b4f2971398bf016b835d2d1406',  # web使用
        '81020848': 'cbfbd1e785e804c6c1456fd712c40ef0',  # app使用
        '58749073': 'f0d2749d80deda21f706f52e84563664',  # sdk使用
        '92332706': '66bddb70a6ec11e6a5ece2cda15bfe64',  # 营销活动使用
    }

    PARTNER_MAP = {
        'xdwLC-nREOpBXmH3KVEGKMCMvqTsJsRsxIhQrNoUsJY=': 'yougame',          # 游戏访问
    }

    DEVICE_KEY = 'guard:device:%(device)s'
    SIG_KEY = 'guard:sig:%(sig)s'
    BLOCK_KEY = 'guard:block:%(device)s'
    MARKET_KEY = 'guard:market:%(mid)s'

    @classmethod
    def verify_block(cls, device):
        bkey = cls.BLOCK_KEY % ({'device': device})
        count = Redis.get(bkey)
        return not count or count <= 0

    @classmethod
    def verify_interval(cls, key, interval, valid_count):
        count = Redis.incr(key)
        Redis.expire(key, interval)
        if count > valid_count:
            return False

        return True

    @classmethod
    def verify_request_interval(cls, device, sig):
        bkey = cls.BLOCK_KEY % ({'device': device})

        key = cls.SIG_KEY % ({'sig': sig})
        # 同样sig一分钟访问不能超过5次
        valid = cls.verify_interval(key, 60, 5)
        if not valid:
            Redis.incr(bkey, 1)
            Redis.expire(bkey, 600)
            return False

        key = cls.DEVICE_KEY % ({'device': device})
        # 同样的device一分钟访问不能超过500次
        valid = cls.verify_interval(key, 60, 500)
        if not valid:
            Redis.incr(bkey, 1)
            Redis.expire(bkey, 600)
            return False

        return True

    @classmethod
    def verify_comment_interval(cls, uid):
        pass

    @classmethod
    def verify_letter_interval(cls, uid):
        pass

    @classmethod
    def verify_register(cls, device):
        pass

    @classmethod
    def verify_sig(cls, params):
        if 'xsig' in params and 'appid' in params:
            valid_sig = params.pop('xsig', None)
            appid = params.get('appid', None)
            sd = ['%s=%s' % (k, v.encode('utf8'))
                  for k, v in sorted(params.iteritems())]
            raw_str = '#'.join(sd)
            md5 = hashlib.md5(raw_str)
            secret = '&' + cls.SECRET_MAP.get(appid, 'invalid_appid')
            md5.update(secret)
            if valid_sig == md5.hexdigest():
                return True

        return False

    @classmethod
    def new_market_id(cls):
        qid = uuid.uuid1().get_hex()
        md5 = hashlib.md5(qid)
        secret = cls.SECRET_MAP.get('92332706', 'invalid_appid')
        md5.update(secret)
        mid = md5.hexdigest()
        key = cls.MARKET_KEY % {'mid': mid}
        Redis.setex(key, 60, 1)
        return qid

    @classmethod
    def verify_market_id(cls, mid):
        key = cls.MARKET_KEY % {'mid': mid}
        count = Redis.incr(key, 1)
        Redis.delete(key)
        return count == 2

    @classmethod
    def verify_partner(cls, pk):
        return cls.PARTNER_MAP.get(pk, None)
