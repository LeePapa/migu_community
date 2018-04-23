# -*- coding: utf8 -*-
from bson import json_util as bjson
from bson.objectid import ObjectId
from datetime import datetime
from urlparse import urljoin
from wanx import app
from wanx.base import const, util
from wanx.models.home import HomeCategory
from wanx.models.game import Game, Category
from wanx.models.video import Video, VideoCategory
from wanx.models.user import User, Group
from wanx.models.activity import ActivityConfig
from wtforms import widgets, fields
from flask.ext.admin.form import widgets as admin_widgets
from playhouse.shortcuts import model_to_dict


def format_ctype(view, context, model, name):
    model = model if isinstance(model, dict) else model_to_dict(model)
    _value = model.get(name, None)
    if _value == 'video':
        _value = u'视频'
    elif _value == 'game':
        _value = u'游戏'
    elif _value == 'user':
        _value = u'主播'
    return _value


def format_icon(view, context, model, name):
    model = model if isinstance(model, dict) else model_to_dict(model)
    _value = model.get(name, None)
    if _value is None or _value == 'icon':
        _value = u'小图标'
    elif _value == 'big_icon':
        _value = u'大图标'
    return _value


def format_home_category(view, context, model, name):
    model = model if isinstance(model, dict) else model_to_dict(model)
    _value = model.get(name, None)
    obj = HomeCategory.get_one(str(_value), check_online=False)
    if obj:
        _value = '%s (%s)' % (obj.name, _value)
        html = u'<a href="/admin/home_categoryview/?flt1_0=%s">%s</a>' % (str(obj._id), _value)
        _value = widgets.HTMLString(html)
    else:
        _value = u'分类不存在'
    return _value


def format_game(view, context, model, name):
    model = model if isinstance(model, dict) else model_to_dict(model)
    _value = model.get(name, None)
    obj = Game.get_one(str(_value), check_online=False)
    if obj:
        _value = '%s (%s)' % (obj.name, _value)
        html = u'<a href="/admin/gamesview/?flt1_0=%s">%s</a>' % (str(obj._id), _value)
        _value = widgets.HTMLString(html)
    else:
        _value = u'游戏不存在'
    return _value


def format_video(view, context, model, name):
    model = model if isinstance(model, dict) else model_to_dict(model)
    _value = model.get(name, None)
    obj = Video.get_one(str(_value), check_online=False)
    if obj:
        _value = '%s (%s)' % (obj.title, _value)
        html = u'<a href="/admin/videosview/?flt1_0=%s">%s</a>' % (str(obj._id), _value)
        _value = widgets.HTMLString(html)
    else:
        _value = u'视频不存在'
    return _value


def format_category(view, context, model, name):
    model = model if isinstance(model, dict) else model_to_dict(model)
    _value = model.get(name, None)
    obj = Category.get_one(str(_value), check_online=False)
    if obj:
        _value = '%s (%s)' % (obj.name, _value)
        html = u'<a href="/admin/categoryview/?flt1_0=%s">%s</a>' % (str(obj._id), _value)
        _value = widgets.HTMLString(html)
    else:
        _value = u'分类不存在'
    return _value


def format_video_category(view, context, model, name):
    model = model if isinstance(model, dict) else model_to_dict(model)
    _value = model.get(name, None)
    obj = VideoCategory.get_one(str(_value), check_online=False)
    if obj:
        _value = '%s (%s)' % (obj.name, _value)
        html = u'<a href="/admin/categoryview/?flt1_0=%s">%s</a>' % (str(obj._id), _value)
        _value = widgets.HTMLString(html)
    else:
        _value = u'分类不存在'
    return _value


def format_user(view, context, model, name):
    model = model if isinstance(model, dict) else model_to_dict(model)
    _value = model.get(name, None)
    obj = User.get_one(str(_value), check_online=False)
    if obj:
        _value = '%s (%s)' % (obj.nickname, _value)
        html = u'<a href="/admin/usersview/?flt1_0=%s">%s</a>' % (str(obj._id), _value)
        _value = widgets.HTMLString(html)
    else:
        _value = u'用户不存在'
    return _value


def format_group(view, context, model, name):
    model = model if isinstance(model, dict) else model_to_dict(model)
    _value = model.get(name, None)
    obj = Group.get_one(str(_value), check_online=False)
    if obj:
        _value = '%s (%s)' % (obj.name, _value)
        html = u'<a href="/admin/groupview/?flt1_0=%s">%s</a>' % (str(obj._id), _value)
        _value = widgets.HTMLString(html)
    else:
        _value = u'分组不存在'
    return _value


def format_image(view, context, model, name):
    model = model if isinstance(model, dict) else model_to_dict(model)
    _value = model.get(name, None)
    img_src = urljoin(app.config.get("MEDIA_URL"), _value) if _value else '#'
    _value = widgets.HTMLString('<img src="%s" width="100px"/>'
                                % (img_src))
    return _value


def format_video_url(view, context, model, name):
    model = model if isinstance(model, dict) else model_to_dict(model)
    _value = model.get(name, None)
    video_src = urljoin(app.config.get('VIDEO_URL'), _value) if _value else '#'
    img_src = urljoin(app.config.get("MEDIA_URL"),
                      model.get('cover')) if model.get('cover') else '#'
    html = u"""
        <div style="text-align:center">视频ID(%s)</div>
        <div style="text-align:center; width:300px; word-wrap:break-word;">%s</div>
        <div style="text-align:center">
            <video src="%s" controls="controls" poster="%s" width="300px" preload="none"></video>
        </div>
    """ % (
        model.get('_id'),
        model.get('title'),
        video_src,
        img_src
    )
    _value = widgets.HTMLString(html)
    return _value


def format_status(view, context, model, name):
    model = model if isinstance(model, dict) else model_to_dict(model)
    _value = model.get(name, None)
    if _value is None or int(_value) == const.ONLINE:
        _value = u'在线'
    elif int(_value) == const.OFFLINE:
        _value = u'下线'
    elif int(_value) == const.UNDER_TEST:
        _value = u'测试'
    elif int(_value) == const.ELITE:
        _value = u'精选'
    elif int(_value) == const.UPLOADING:
        _value = u'上传中'
    elif int(_value) == const.OFFSHELF:
        _value = u'非上架'
    return _value


def format_timestamp(view, context, model, name):
    model = model if isinstance(model, dict) else model_to_dict(model)
    _value = model.get(name, None)
    if _value:
        _value = datetime.fromtimestamp(_value).strftime('%Y-%m-%d %H:%M:%S')
    return _value


def format_gender(view, context, model, name):
    model = model if isinstance(model, dict) else model_to_dict(model)
    _value = model.get(name, 0)
    if int(_value) == 0:
        _value = u'未知'
    elif int(_value) == 1:
        _value = u'男'
    elif int(_value) == 2:
        _value = u'女'
    return _value


def format_model(model, name, model_view, url='', extend_name=None):
    _value = model.get(name, None)
    obj = model_view.get_one(str(_value), check_online=False)
    if obj:
        if extend_name is None:
            _value = '%s (%s)' % (obj.name, _value)
        else:
            # 显示组合字段
            _value = '%s(%s) (%s)' % (obj.name, obj.get(extend_name), _value)
        if url:
            html = u'<a href="%s=%s">%s</a>' % (
                url, str(obj._id), _value)
            _value = widgets.HTMLString(html)
    else:
        _value = u'ID不存在'
    return _value


def format_choices(view, context, model, name, urls=None):
    widget = getattr(view.form, name)
    choices = widget.kwargs.get('choices', [])
    value = model[name]
    name = dict(choices).get(value, u'ID不存在')
    if urls is None:
        return name
    url = dict(urls).get(value, '')
    if not url:
        return name
    html = u'<a href="{url}">{name}</a>'.format(name=name, url=url)
    return widgets.HTMLString(html)


class JsonField(fields.StringField):
    def _value(self):
        if self.data:
            return bjson.dumps(self.data)
        else:
            return u''

    def process_formdata(self, valuelist):
        self.data = bjson.loads(valuelist[0]) if valuelist[0] else {}


class ObjectIdField(fields.StringField):
    def _value(self):
        if self.data:
            return str(self.data)
        else:
            return u''

    def process_formdata(self, valuelist):
        self.data = ObjectId(valuelist[0]) if valuelist[0] else u''


class TimeStampField(fields.FloatField):
    widget = admin_widgets.DateTimePickerWidget()

    def _value(self):
        return util.timestamp2str(self.data) if self.data else u''

    def process_formdata(self, valuelist):
        if valuelist[0]:
            self.data = util.str2timestamp(valuelist[0])
        else:
            self.data = None


class HourStampField(fields.StringField):
    widget = admin_widgets.TimePickerWidget()

    def _value(self):
        return self.data if self.data is not None else ''

    def process_formdata(self, valuelist):
        if valuelist[0]:
            self.data = valuelist[0]
        else:
            self.data = None


def format_traffic_status(view, context, model, name):
    _value = model.get(name, None)
    if _value is None or int(_value) == const.TRAFFIC_RECEIVED_SUCCESS:
        _value = u'流量到账成功'
    elif int(_value) == const.TRAFFIC_FAIL:
        _value = u'充值失败'
    elif int(_value) == const.TRAFFIC_RECEIVED_PROCESS:
        _value = u'流量到账正在处理中'
    elif int(_value) == const.TRAFFIC_SUCCESS:
        _value = u'充值成功'
    elif int(_value) == const.TRAFFIC_PROCESS:
        _value = u'充值中'
    elif int(_value) == const.TRAFFIC_RECEIVED_FAIL:
        _value = u'流量到账失败'
    return _value


def format_traffic_type(view, context, model, name):
    _value = model.get(name, None)
    if _value == 'first_login':
        _value = u'首次登录'
    elif _value == 'video_share':
        _value = u'视频分享'
    return _value


def format_user_phone(view, context, model, name):
    _value = model.get('source', None)
    obj = User.get_one(str(_value), check_online=False)
    if obj:
        _value = '%s' % (obj.phone)
    else:
        _value = u'用户不存在'
    return _value


def format_activity(view, context, model, name):
    _value = model.get(name, None)
    obj = ActivityConfig.get_one(str(_value), check_online=False)
    if obj:
        _value = '%s (%s)' % (obj.name, _value)
        html = u'<a href="/admin/activity_configview/?flt1_0=%s">%s</a>' % (str(obj._id), _value)
        _value = widgets.HTMLString(html)
    else:
        _value = u'活动不存在'
    return _value
