# -*- coding: utf8 -*-
from bson.objectid import ObjectId
from wtforms import form, fields, validators
from .base import WxModelView
from .filter import EqualFilter
from .util import (ObjectIdField, TimeStampField, HourStampField, format_image,
                   format_timestamp, format_game, format_ctype, format_home_category,
                   format_video, format_user)
from wanx.models.home import (Banner, BannerSdk, HomeCategory, HomeCategoryConfig,
                              LaunchAds, Popup, Channels, FixedBanner)
from wanx.models.game import HotGame, LiveHotGame
from wanx.models.user import Group
from wanx.models.xconfig import VersionConfig, Province
from wanx.base.util import get_choices_desc
from wanx.base import const
from flask import flash


class LaunchAdsForm(form.Form):
    image = fields.StringField(u'图片', [validators.Required()])
    action = fields.StringField(u'链接', [validators.Optional()])
    duration = fields.IntegerField(u'显示时长', [validators.Required()])
    rate = fields.IntegerField(u'显示概率基数', [validators.InputRequired()])
    begin_at = TimeStampField(u'开始时间', [validators.Required()])
    expire_at = TimeStampField(u'结束时间', [validators.Required()])


class LaunchAdsAdmin(WxModelView):
    Model = LaunchAds
    form = LaunchAdsForm
    column_list = ('image', 'action', 'duration', 'rate', 'begin_at', 'expire_at')
    column_labels = dict(image=u'图片', action=u'链接', duration=u'显示时长',
                         rate=u'显示概率基数', begin_at=u'开始时间', expire_at=u'结束时间')
    column_formatters = dict(image=format_image, begin_at=format_timestamp,
                             expire_at=format_timestamp)


class BannerForm(form.Form):
    image = fields.StringField(u'图片链接', [validators.Required()])
    action = fields.StringField(u'链接', [validators.Required()])
    duration = fields.IntegerField(u'显示时长', [validators.Required()])
    order = fields.IntegerField(u'显示顺序', [validators.InputRequired()], default=0)
    begin_at = TimeStampField(u'开始时间', [validators.Required()])
    expire_at = TimeStampField(u'结束时间', [validators.Required()])
    os = fields.SelectField(u'平台要求', [validators.InputRequired()],
                            choices=[
                                ('android', 'Android'),
                                ('ios', 'IOS')], default='Android')
    login = fields.SelectField(u'登录要求', [validators.InputRequired()],
                               choices=[
                                   ('all', u'全部'),
                                   ('login', u'登录')], default='login')
    channels = fields.SelectMultipleField(u'推广渠道', [validators.Optional()])
    group = fields.SelectField(u'用户组', coerce=ObjectId)
    version_code_mix = fields.SelectField(u'版本要求(版本号大于等于)', [validators.Optional()],
                                          coerce=int)
    version_code_max = fields.SelectField(u'版本要求(版本号小于等于)', [validators.Optional()],
                                          coerce=int)
    province = fields.SelectMultipleField(u'省份', [validators.Optional()])


class BannerAdmin(WxModelView):
    Model = Banner
    form = BannerForm
    column_list = ('_id', 'image', 'action', 'duration', 'order', 'begin_at', 'expire_at')
    column_labels = dict(_id=u'广告ID', image=u'图片', action=u'链接', duration=u'显示时长',
                         order=u'显示顺序', begin_at=u'开始时间', expire_at=u'结束时间')
    column_formatters = dict(image=format_image, begin_at=format_timestamp,
                             expire_at=format_timestamp)

    def create_form(self, obj=None):
        form = super(BannerAdmin, self).create_form(obj)
        cids = Channels.all_channels_ids()
        channels = Channels.get_list(cids)
        form.channels.choices = [(c.sign, c.channels_name) for c in channels]

        vids = VersionConfig.all_version_ids()
        version = VersionConfig.get_list(vids)
        form.version_code_mix.choices = [(v.version_code, v.version_name) for v in version]
        form.version_code_max.choices = [(v.version_code, v.version_name) for v in version]

        pids = Province.all_province_ids()
        province = Province.get_list(pids)
        form.province.choices = [(p.code, ''.join((p.name, p.operators))) for p in province]

        form.group.choices = Group.groups_for_admin()
        return form

    def edit_form(self, obj):
        form = super(BannerAdmin, self).edit_form(obj)
        cids = Channels.all_channels_ids()
        channels = Channels.get_list(cids)
        form.channels.choices = [(c.sign, c.channels_name) for c in channels]

        vids = VersionConfig.all_version_ids()
        version = VersionConfig.get_list(vids)
        form.version_code_mix.choices = [(v.version_code, v.version_name) for v in version]
        form.version_code_max.choices = [(v.version_code, v.version_name) for v in version]

        pids = Province.all_province_ids()
        province = Province.get_list(pids)
        form.province.choices = [(p.code, ''.join((p.name, p.operators))) for p in province]

        form.group.choices = Group.groups_for_admin()
        return form


class HomeCategoryForm(form.Form):
    name = fields.StringField(u'名称', [validators.Required()])
    icon = fields.StringField(u'图标', [validators.Optional()])
    ctype = fields.SelectField(u'内容类型', [validators.InputRequired()], coerce=str,
                               choices=[
                                   ('video', u'视频'),
                                   ('game', u'游戏'),
                                   ('user', u'主播')],
                               default='video')
    action = fields.StringField(u'链接', [validators.Required()])
    order = fields.IntegerField(u'显示顺序', [validators.InputRequired()], default=0)


class HomeCategoryAdmin(WxModelView):
    Model = HomeCategory
    form = HomeCategoryForm
    column_list = ('_id', 'name', 'icon', 'ctype', 'action', 'order')
    column_labels = dict(_id=u'分类ID', name=u'名称', icon=u'图标', ctype=u'内容类型',
                         action=u'链接', order=u'显示顺序')
    column_formatters = dict(icon=format_image, ctype=format_ctype)
    column_filters = (
        EqualFilter('_id', u'分类ID', ObjectId),
    )


class HomeCategoryConfigForm(form.Form):
    category = fields.SelectField(u'分类', [validators.InputRequired()], coerce=ObjectId)
    target = fields.StringField(u'对象ID', [validators.Required()])
    order = fields.IntegerField(u'显示顺序', [validators.InputRequired()], default=0)


def _format_ctarget(view, context, model, name):
    _value = model.get(name, None)
    category = HomeCategory.get_one(model.get('category'))
    if category.ctype == 'video':
        _value = format_video(view, context, model, name)
    elif category.ctype == 'user':
        _value = format_user(view, context, model, name)
    elif category.ctype == 'game':
        _value = format_game(view, context, model, name)
    return _value


class HomeCategoryConfigAdmin(WxModelView):
    Model = HomeCategoryConfig
    form = HomeCategoryConfigForm
    column_list = ('category', 'target', 'order')
    column_labels = dict(category=u'分类名称', target=u'对象ID', order=u'显示顺序')
    column_formatters = dict(icon=format_image, target=_format_ctarget,
                             category=format_home_category)

    column_filters = (
        EqualFilter('category', u'分类ID', ObjectId),
    )

    def create_form(self, obj=None):
        form = super(HomeCategoryConfigAdmin, self).create_form(obj)
        form.category.choices = HomeCategory.all_categories_for_admin()
        return form

    def edit_form(self, obj=None):
        form = super(HomeCategoryConfigAdmin, self).edit_form(obj)
        form.category.choices = HomeCategory.all_categories_for_admin()
        return form


class WelcomeForm(form.Form):
    target = ObjectIdField(u'对象id', [validators.Required()])
    type = fields.SelectField(
        u'类型',
        [validators.Required()],
        choices=[
            ('LINK_HOT_GAME', u'热门游戏'),
            ('LIVE_HOT_GAME', u'热门游戏(直播)'),
        ]
    )
    order = fields.IntegerField(u'显示顺序', [validators.InputRequired()], default=0)
    available = fields.BooleanField(u'是否可用', default=True)


def _format_type(view, context, model, name):
    _value = model.get(name, None)
    if _value == 'LINK_HOT_GAME':
        _value = u'热门游戏'
    elif _value == 'LIVE_HOT_GAME':
        _value = u'热门游戏(直播)'
    return _value


def _format_target(view, context, model, name):
    _value = model.get(name, None)
    if model.get('type') == 'LINK_HOT_GAME':
        _value = format_game(view, context, model, name)
    elif model.get('type') == 'LIVE_HOT_GAME':
        _value = format_game(view, context, model, name)
    return _value


class WelcomeAdmin(WxModelView):
    form = WelcomeForm
    column_list = ('target', 'type', 'available', 'order')
    column_labels = dict(target=u'对象ID', type=u'类型', available=u'是否可用', order=u'显示顺序')
    column_formatters = dict(target=_format_target, type=_format_type)
    column_filters = (
        EqualFilter('type', u'类型', str, [
            ('LINK_HOT_GAME', u'热门游戏'),
            ('LIVE_HOT_GAME', u'热门游戏(直播)')
        ]),
    )

    def create_model(self, form):
        if form.data['type'] == 'LINK_HOT_GAME':
            self.Model = HotGame
        elif form.data['type'] == 'LIVE_HOT_GAME':
            self.Model = LiveHotGame
        ret = super(WelcomeAdmin, self).create_model(form)
        return ret

    def update_model(self, form, model):
        if form.data['type'] == 'LINK_HOT_GAME':
            self.Model = HotGame
        elif form.data['type'] == 'LIVE_HOT_GAME':
            self.Model = LiveHotGame
        ret = super(WelcomeAdmin, self).update_model(form, model)
        return ret

    def delete_model(self, model):
        if model['type'] == 'LINK_HOT_GAME':
            self.Model = HotGame
        elif model['type'] == 'LIVE_HOT_GAME':
            self.Model = LiveHotGame
        ret = super(WelcomeAdmin, self).delete_model(model)
        return ret


class BannerSdkForm(form.Form):
    vertical_image = fields.StringField(u'竖版图片链接', [validators.Required()])
    transverse_image = fields.StringField(u'横版图片链接', [validators.Required()])
    action = fields.StringField(u'链接', [validators.Required()])
    duration = fields.IntegerField(u'显示时长', [validators.Required()])
    order = fields.IntegerField(u'显示顺序', [validators.InputRequired()], default=0)
    begin_at = TimeStampField(u'开始时间', [validators.Required()])
    expire_at = TimeStampField(u'结束时间', [validators.Required()])


class BannerSdkAdmin(WxModelView):
    Model = BannerSdk
    form = BannerSdkForm
    column_list = ('vertical_image', 'transverse_image', 'action', 'duration', 'order',
                   'begin_at', 'expire_at')
    column_labels = dict(vertical_image=u'竖版图片', transverse_image=u'横版图片', action=u'链接',
                         duration=u'显示时长', order=u'显示顺序', begin_at=u'开始时间', expire_at=u'结束时间')
    column_formatters = dict(vertical_image=format_image, transverse_image=format_image,
                             begin_at=format_timestamp, expire_at=format_timestamp)


class PopupForm(form.Form):
    image = fields.StringField(u'图片', [validators.Required()])
    image_link = fields.StringField(u'图片链接', [validators.Required()])
    image_link_type = fields.SelectField(u'图片链接类型', [validators.InputRequired()],
                                         choices=[
                                             ('app', u'app内'),
                                             ('app_h5', u'H5页面'),
                                             ('h5', u'外部H5页面')], default='app')
    begin_at = TimeStampField(u'开始时间', [validators.Required()])
    expire_at = TimeStampField(u'结束时间', [validators.Required()])
    login = fields.SelectField(u'登录要求', [validators.InputRequired()],
                               choices=[
                                   ('all', u'全部'),
                                   ('login', u'登录')], default='login')
    os = fields.SelectField(u'平台要求', [validators.InputRequired()],
                            choices=[
                                ('android', 'Android'),
                                ('ios', 'IOS')], default='Android')
    channels = fields.SelectMultipleField(u'推广渠道', [validators.Optional()])
    push_begin_at = HourStampField(u'推送开始时段')
    push_expire_at = HourStampField(u'推送结束时段')
    button_text = fields.StringField(u'按钮文字', [validators.Required()])
    button_link = fields.StringField(u'按钮链接', [validators.Required()])
    show_button = fields.BooleanField(u'是否显示按钮', default=False)
    group = fields.SelectField(u'用户组', coerce=ObjectId)
    province = fields.SelectMultipleField(u'省份', [validators.Optional()])

    version_code_mix = fields.SelectField(u'版本要求(版本号大于等于)', [validators.Optional()],
                                          coerce=int)
    version_code_max = fields.SelectField(u'版本要求(版本号小于等于)', [validators.Optional()],
                                          coerce=int)


class PopupAdmin(WxModelView):
    Model = Popup
    form = PopupForm

    column_list = ('image', 'image_link', 'begin_at', 'expire_at')
    column_labels = dict(image=u'图片', image_link=u'链接', begin_at=u'开始时间', expire_at=u'结束时间')

    column_formatters = dict(image=format_image, begin_at=format_timestamp,
                             expire_at=format_timestamp)

    def create_form(self, obj=None):
        form = super(PopupAdmin, self).create_form(obj)
        cids = Channels.all_channels_ids()
        channels = Channels.get_list(cids)
        form.channels.choices = [(c.sign, c.channels_name) for c in channels]

        vids = VersionConfig.all_version_ids()
        version = VersionConfig.get_list(vids)
        form.version_code_mix.choices = [(v.version_code, v.version_name) for v in version]
        form.version_code_max.choices = [(v.version_code, v.version_name) for v in version]

        pids = Province.all_province_ids()
        province = Province.get_list(pids)
        form.province.choices = [(p.code, ''.join((p.name, p.operators))) for p in province]

        form.group.choices = Group.groups_for_admin()
        return form

    def edit_form(self, obj):
        form = super(PopupAdmin, self).edit_form(obj)
        cids = Channels.all_channels_ids()
        channels = Channels.get_list(cids)
        form.channels.choices = [(c.sign, c.channels_name) for c in channels]

        vids = VersionConfig.all_version_ids()
        version = VersionConfig.get_list(vids)
        form.version_code_mix.choices = [(v.version_code, v.version_name) for v in version]
        form.version_code_max.choices = [(v.version_code, v.version_name) for v in version]

        pids = Province.all_province_ids()
        province = Province.get_list(pids)
        form.province.choices = [(p.code, ''.join((p.name, p.operators))) for p in province]

        form.group.choices = Group.groups_for_admin()
        return form


class ChannelsForm(form.Form):
    sign = fields.StringField(u'打包标示', [validators.Required()])
    channels_name = fields.StringField(u'渠道注解', [validators.Required()])
    note = fields.StringField(u'渠道备注')


class ChannelsAdmin(WxModelView):
    Model = Channels
    form = ChannelsForm

    column_list = ('sign', 'channels_name', 'note')
    column_labels = dict(sign=u'打包标示', channels_name=u'渠道注解', note=u'渠道备注')


# class ShareAdmin(WxModelView):
#     Model = Share

FB_STATUS = ((const.ONLINE, u"进行中"),
             (const.OFFLINE, u"结束"),)

FB_POSITION = ((1, u"热门直播上方"), (2, u"热门直播下方"), (3, u"每日精选上方"))


class FixedBannerForm(form.Form):
    name = fields.StringField(u"banner名称", [validators.Required()])
    image = fields.StringField(u"banner图片", [validators.Required()])
    url = fields.StringField(u"跳转链接", [validators.Required()])
    status = fields.SelectField(u"状态", [validators.InputRequired()], coerce=int,
                                choices=FB_STATUS)
    begin_at = TimeStampField(u'开始时间', [validators.Required()])
    expire_at = TimeStampField(u'结束时间', [validators.Required()])
    os = fields.SelectField(u'平台要求', [validators.InputRequired()],
                            choices=[
                                ('android', 'Android'),
                                ('ios', 'IOS')], default='Android')
    login = fields.SelectField(u'登录要求', [validators.InputRequired()],
                               choices=[
                                   ('all', u'全部'),
                                   ('login', u'登录')], default='login')
    channels = fields.SelectMultipleField(u'推广渠道', [validators.Optional()])
    group = fields.SelectField(u'用户组', coerce=ObjectId)
    version_code_mix = fields.SelectField(u'版本要求(版本号大于等于)', [validators.Optional()],
                                          coerce=int)
    version_code_max = fields.SelectField(u'版本要求(版本号小于等于)', [validators.Optional()],
                                          coerce=int)
    province = fields.SelectMultipleField(u'省份', [validators.Optional()])
    position = fields.SelectField(u"显示位置", [validators.InputRequired()], coerce=int,
                                  choices=FB_POSITION)


class FixedBannerAdmin(WxModelView):
    Model = FixedBanner
    form = FixedBannerForm

    column_list = ('name', 'image', 'position', 'os', 'status')
    column_labels = dict(name=u'banner名称', image=u'banner图片', url=u"跳转链接",
                         begin_at=u'开始时间', expire_at=u'结束时间', status=u'状态',
                         login=u'登录要求', os=u'平台要求', version_code_mix=u'最低版本要求',
                         version_code_max=u'最高版本要求', channels=u'推送渠道',
                         province=u'推送省份', position=u'显示位置',
                         )
    column_details_list = ('name', 'image', 'url', 'begin_at', 'expire_at', 'status',
                           'login', 'os', 'version_code_mix', 'version_code_max',
                           'channels', 'province', 'position')

    can_view_details = True
    details_modal = True

    column_formatters = dict(
        image=format_image,
        begin_at=format_timestamp,
        expire_at=format_timestamp,
        position=lambda v, c, m, n: get_choices_desc(FB_POSITION, m['position']),
        status=lambda v, c, m, n: get_choices_desc(FB_STATUS, m['status']),
    )

    def create_form(self, obj=None):
        form = super(FixedBannerAdmin, self).create_form(obj)
        cids = Channels.all_channels_ids()
        channels = Channels.get_list(cids)
        form.channels.choices = [(c.sign, c.channels_name) for c in channels]

        vids = VersionConfig.all_version_ids()
        version = VersionConfig.get_list(vids)
        form.version_code_mix.choices = [(v.version_code, v.version_name) for v in version]
        form.version_code_max.choices = [(v.version_code, v.version_name) for v in version]

        pids = Province.all_province_ids()
        province = Province.get_list(pids)
        form.province.choices = [(p.code, ''.join((p.name, p.operators))) for p in province]

        form.group.choices = Group.groups_for_admin()
        return form

    def edit_form(self, obj=None):
        form = super(FixedBannerAdmin, self).edit_form(obj)
        cids = Channels.all_channels_ids()
        channels = Channels.get_list(cids)
        form.channels.choices = [(c.sign, c.channels_name) for c in channels]

        vids = VersionConfig.all_version_ids()
        version = VersionConfig.get_list(vids)
        form.version_code_mix.choices = [(v.version_code, v.version_name) for v in version]
        form.version_code_max.choices = [(v.version_code, v.version_name) for v in version]

        pids = Province.all_province_ids()
        province = Province.get_list(pids)
        form.province.choices = [(p.code, ''.join((p.name, p.operators))) for p in province]

        form.group.choices = Group.groups_for_admin()
        return form

    def create_model(self, obj=None):
        crash,msg = FixedBanner.check_crash(obj.data)
        if crash:
            flash(u"创建失败，发现有冲突的记录（%s）！" % msg, 'error')
            return False
        model = super(FixedBannerAdmin, self).create_model(obj)
        return model

    def update_model(self, obj=None, model=None, exclude_fields=[]):
        crash,msg = FixedBanner.check_crash(obj.data, model['_id'])
        if crash:
            flash(u"更新失败，发现有冲突的记录（%s）！" % msg, 'error')
            return False
        model = super(FixedBannerAdmin, self).update_model(obj, model, exclude_fields)
        return model

