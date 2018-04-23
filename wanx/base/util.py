# -*- coding: utf8 -*-
from datetime import datetime
from flask import jsonify, request
from wanx.base.xredis import Redis
from wanx.base.guard import Guard
from functools import wraps
from . import error

import cPickle as cjson
import functools
import json
import random
import time
import os
from xml.parsers.expat import ParserCreate


def is_mobile_phone(phone):
    """是否为移动号"""

    # 后台配置移动号段
    from wanx.models.xconfig import Config
    default_prefix = ["134", "135", "136", "137", "138", "139",
                             "147", "150", "151", "152", "157", "158",
                             "159", "178", "182", "183", "184", "187", "188"]
    prefixs = Config.fetch('mobile_phone_prefix', default_prefix, json.loads)
    return phone[:3] in prefixs


def is_unicom_phone(phone):
    """是否为联通号"""

    # 后台配置号段
    from wanx.models.xconfig import Config
    default_prefix = ["130", "131", '132', '155', '156', '185', '186', '145', '176']
    prefixs = Config.fetch('unicom_phone_prefix', default_prefix, json.loads)
    return phone[:3] in prefixs


def is_telecom_phone(phone):
    """是否为电信号"""

    # 后台配置号段
    from wanx.models.xconfig import Config
    default_prefix = ["133", "153", "177", "180", "181", "189"]
    prefixs = Config.fetch('telecom_phone_prefix', default_prefix, json.loads)
    return phone[:3] in prefixs


def get_choices_desc(choices, value):
    for _value, _desc in choices:
        if value == _value:
            return _desc
    return None


def random_pick(sequence, key):
    if not sequence:
        return None

    total = sum([key(obj) if callable(key) else obj[key] for obj in sequence])
    if total < 0:
        return None

    rad = random.randint(1, total)

    cur_total = 0
    res = None
    for obj in sequence:
        cur_total += key(obj) if callable(key) else obj[key]
        if rad <= cur_total:
            res = obj
            break

    return res


def datetime2timestamp(dt):
    return time.mktime(dt.timetuple())


def str2timestamp(value):
    return time.mktime(time.strptime(value.strip(), "%Y-%m-%d %H:%M:%S"))

def timestamp2datetime(value):
    return datetime.fromtimestamp(value)

def timestamp2str(value):
    return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')


def datetime2str(value):
    return datetime.fromtimestamp(value).strftime('%Y-%m-%d')


def hot_live_user_score(value, timestamp):
    return value * 1000000000 + (2411395200 - timestamp)


def validate_request():
    if os.environ['WXENV'] == 'UnitTest':
        return True

    params = dict()
    if request.method == 'GET':
        params = request.args.to_dict()
    elif request.method == 'POST':
        params = request.form.to_dict()
    else:
        return True

    # 强制校验营销活动相关接口
    qid = params.get('xmqid', None)
    market_paths = (
        # '/task/receive_reward',          # 获取任务奖励
        '/store/draw_lottery',          # 抽奖
        '/store/exchange_product',      # 兑换物品
        '/lives/task',                   # 领取直播间活动礼品
        '/lives/redpacket/grab',        # 直播间红包抢夺
        '/activity/vote'                 # 投票接口
    )
    if request.path in market_paths and not Guard.verify_market_id(qid):
        return False

    # 后台配置是否开启接口加密, 默认不开启
    from wanx.models.xconfig import Config
    verify = Config.fetch('verify_api', False, int)
    if not verify:
        return True

    device = params.get('device', None)
    sig = params.get('xsig', None)
    appid = params.get('appid', None)
    if not device or not sig or not appid:
        return False
    # 加密串验证
    if not Guard.verify_sig(params):
        return False
    # 黑名单验证
    if not Guard.verify_block(device):
        return False
    # device和sig频率验证
    if not Guard.verify_request_interval(device, sig):
        return False

    return True


def validate_login(func, data):
    # 如果返回错误，直接返回
    if isinstance(data, error.ApiError):
        return data

    # 后台配置是否开启登录白名单验证, 默认不开启
    from wanx.models.xconfig import Config
    verify = Config.fetch('verify_login', False, int)
    if not verify:
        return data

    from wanx.models.user import Group, UserGroup
    gid = Group.allowed_login_group()
    whitelist = UserGroup.group_user_ids(gid) if gid else []
    # 因为装饰器已经重新构造了函数，所以需要通过函数名（或函数代码，比较麻烦）来判断
    login_func_names = ('login', 'partner_login', 'platform_login', 'register_phone', 'refresh_token')
    if func.__name__ in login_func_names and data['user']['user_id'] not in whitelist:
        return error.LoginRefuse
    return data


def jsonapi(login_required=False, verify=True):
    """API接口统一处理
    """
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            start = int(time.time() * 1000)
            if verify and not validate_request():
                data = error.InvalidRequest
            else:
                ut = request.values.get("ut", None)
                from wanx.models.user import User
                uid = User.uid_from_token(ut)
                user = User.get_one(uid)
                request.authed_user = user
                if login_required and not user:
                    data = error.AuthRequired
                else:
                    data = func(*args, **kwargs)
                    data = validate_login(func, data)
            status = data.errno if isinstance(data, error.ApiError) else 0
            errmsg = data.errmsg if isinstance(data, error.ApiError) else '成功'
            if isinstance(data, error.ApiError):
                data()
                data = {}
            result = {
                'status': status,
                'errmsg': errmsg,
                'data': data,
                'time': int(time.time() * 1000) - start,
            }
            return jsonify(result)
        return decorated_function
    return decorator


class Lockit(object):
    def __init__(self, cache, key, expire=5, mock=False):
        self._cache = cache
        self._key = key
        self._expire = expire
        self._mock = mock

    def __enter__(self):
        if self._mock:  # 加锁开关 mock为True 永远不加锁
            return False
        if self._cache.set(self._key, 1, ex=self._expire, nx=True):  # 当key存在时不加锁
            return False  # 没有key,返回没有锁
        else:
            return True

    def __exit__(self, *args):
        if not self._mock:
            self._cache.delete(self._key)
        return True


def _cached_result(key_func, timeout=86400, snowslide=False, rtype='String'):
    """根据rtype参数选择相应的redis结构进行缓存
    rtype: String, Hash, Set, List, SortedSet
    """
    def wrapper(func):
        @wraps(func)
        def inner_func(*args):
            key = key_func(*args) if callable(key_func) else key_func
            result = None
            mock = not snowslide
            with Lockit(Redis, 'lock:%s' % (key), mock=mock) as locked:
                if locked:
                    time.sleep(0.5)  # 当对key第二次操作的时候停止0.5秒
                else:
                    result = func(*args)
                    if rtype == 'Object' and result:
                        Redis.setex(key, timeout, cjson.dumps(result, 2))
                    elif rtype == 'Hash' and result:
                        Redis.hmset(key, result)
                        Redis.expire(key, timeout)
                    elif rtype == 'List':
                        Redis.delete(key)
                        # 处理结果为空数据, 防止穿透db, 在增加和查询的时候需要判断数据结构
                        Redis.rpush(key, *result) if result else Redis.set(key, 'empty')
                        Redis.expire(key, timeout)
                    elif rtype == 'Set':
                        Redis.delete(key)
                        # 处理结果为空数据, 防止穿透db, 在增加和查询的时候需要判断数据结构
                        Redis.sadd(key, *result) if result else Redis.set(key, 'empty')
                        Redis.expire(key, timeout)
                    elif rtype == 'SortedSet':
                        Redis.delete(key)
                        # 处理结果为空数据, 防止穿透db, 在增加和查询的时候需要判断数据结构
                        Redis.zadd(key, *result) if result else Redis.set(key, 'empty')
                        Redis.expire(key, timeout)
            return result
        return inner_func
    return wrapper

cached_object = functools.partial(_cached_result, rtype='Object')
cached_hash = functools.partial(_cached_result, rtype='Hash')
cached_set = functools.partial(_cached_result, rtype='Set')
cached_list = functools.partial(_cached_result, rtype='List')
cached_zset = functools.partial(_cached_result, rtype='SortedSet')


def format_action(url, shar_url, shar_title='', share_summary='', share_image='', platform='android'):
    if platform == 'ios':
        action = u"""{{"share":{{"webUrl":"{0}","url":"{1}","title":"{2}","content":"{3}",\
"image":"{4}"}}}}""".format(url, shar_url, shar_title, share_summary, share_image)
    else:
        action = u"""{{"intent":"intent:#Intent;\
component=com.migu.yiyue.qingyun/com.molizhen.ui.WebBrowserAty;\
S.url={0};S.shareUrl={1};S.shareTitle={2};S.shareSummary={3};\
S.shareImage={4};end"}}""".format(url, shar_url, shar_title, share_summary, share_image)
    return action


class Xml2Json:
    LIST_TAGS = ['COMMANDS']

    def __init__(self, data=None):
        self._parser = ParserCreate()
        self._parser.StartElementHandler = self.start
        self._parser.EndElementHandler = self.end
        self._parser.CharacterDataHandler = self.data
        self.result = None
        if data:
            self.feed(data)
            self.close()

    def feed(self, data):
        self._stack = []
        self._data = ''
        self._parser.Parse(data, 0)

    def close(self):
        self._parser.Parse("", 1)
        del self._parser

    def start(self, tag, attrs):
        assert attrs == {}
        assert self._data.strip() == ''
        self._stack.append([tag])
        self._data = ''

    def end(self, tag):
        last_tag = self._stack.pop()
        assert last_tag[0] == tag
        if len(last_tag) == 1:  # leaf
            data = self._data
        else:
            if tag not in Xml2Json.LIST_TAGS:
                # build a dict, repeating pairs get pushed into lists
                data = {}
                for k, v in last_tag[1:]:
                    if k not in data:
                        data[k] = v
                    else:
                        el = data[k]
                        if type(el) is not list:
                            data[k] = [el, v]
                        else:
                            el.append(v)
            else:  # force into a list
                data = [{k: v} for k, v in last_tag[1:]]
        if self._stack:
            self._stack[-1].append((tag, data))
        else:
            self.result = {tag: data}
        self._data = ''

    def data(self, data):
        self._data = data