# -*- coding: utf8 -*-
from bson.objectid import ObjectId
from wtforms import form, fields, validators

from wanx.models.msg import SysMessage
from .base import WxModelView
from .util import (format_image, format_status, format_gender, format_timestamp, ObjectIdField,
                   format_traffic_status, format_traffic_type, format_user, format_user_phone,
                   format_group)
from .filter import EqualFilter, LikeFilter, SmallerFilter, GreaterFilter
from wanx.base import const, util
from wanx.models.user import User, UserTrafficLog, Group, UserGroup, GROUP_TYPE
from htmls import HTML_BANS

import csv
from StringIO import StringIO
from datetime import datetime


class MyUserField(fields.Field):
    def __call__(self, *args, **kwargs):
        html = HTML_BANS
        ban_button = u"""<button class="btn btn-default" type="button"
        onclick="show_bans_page();">封禁</button>"""
        lift_button = u"""<button class="btn btn-default" type="button"
        onclick="lift_user();">解封</button>"""
        alter_button = u"""<button class="btn btn-default" type="button"
        onclick="show_bans_page();">修改</button>"""

        ban = lift_button if self.bans.get('status') else ban_button
        alter = alter_button if self.bans.get('status') else ""
        stat = u"封禁" if self.bans.get('status') else u"在线"
        uid = self.bans.get('uid')
        uname = self.bans.get('uname')
        lift_time = self.bans.get("lift_at", None)
        if lift_time:
            lift_time = datetime.fromtimestamp(lift_time).strftime("%Y-%m-%d %H:%M:%S")
        else:
            lift_time = u"--"
        lift_at = u"解封时间："+lift_time
        limits = u"权限限制："
        _limits = list()
        if self.bans.get('login', None):
            _limits.append(u"禁止登录")
        if self.bans.get('message', None):
            _limits.append(u"禁止私信")
        if self.bans.get('live', None):
            _limits.append(u"禁止发起直播")
        if self.bans.get('video', None):
            _limits.append(u"禁止上传视频")
        if self.bans.get('comment', None):
            _limits.append(u"禁止发表评论")
        limits += u"、".join(_limits)

        return html.format(ban=ban, alter=alter, stat=stat, lift_at=lift_at, limits=limits,
                           uid=uid, uname=uname)

    def process_data(self, value):
        self.bans = value or {}

    @property
    def data(self):
        return self.bans


class UserForm(form.Form):
    name = fields.StringField(u'用户名', [validators.Required()])
    nickname = fields.StringField(u'用户昵称', [validators.Required()])
    logo = fields.StringField(u'小头像',
                              [validators.Required()],
                              default='/images/2b9/2b9d71591440825ce8dab573b07d38a3.png')
    photo = fields.StringField(u'大头像',
                               [validators.Required()],
                               default='/images/2b9/2b9d71591440825ce8dab573b07d38a3.png')
    birthday = fields.StringField(u'生日', [validators.Optional()])
    gender = fields.SelectField(u'性别', [validators.InputRequired()],
                                coerce=int, choices=[(0, u'未知'), (1, u'男'), (2, u'女')])
    email = fields.StringField(u'邮箱', [validators.Optional(), validators.Email()])
    phone = fields.StringField(u'电话', [validators.Optional()])
    status = fields.SelectField(u'状态', [validators.InputRequired()], coerce=int,
                                choices=[
                                    (const.ONLINE, u'在线'),
                                    (const.OFFLINE, u'封禁')]
                                )
    bans = MyUserField(u"状态")


class UserAdmin(WxModelView):
    Model = User
    form = UserForm
    can_view_details = True
    details_modal = True
    column_details_list = ['_id', 'name', 'nickname', 'logo', 'photo', 'birthday',
                           'email', 'phone', 'gender', 'status', 'partner_migu']
    column_list = ('_id', 'name', 'nickname', 'phone', 'photo', 'status')
    column_labels = dict(_id=u'用户ID', name=u'用户名', nickname=u'昵称', logo=u'小头像',
                         photo=u'大头像', birthday=u'生日', email=u'邮箱', phone=u'手机号',
                         gender=u'性别', status=u'状态', partner_migu=u'咪咕用户信息')
    column_formatters = dict(
        logo=format_image,
        photo=format_image,
        status=format_status,
        gender=format_gender
    )
    column_filters = (
        EqualFilter('_id', u'用户ID', ObjectId),
        EqualFilter('phone', u'手机号', str),
        EqualFilter('status', u'状态', int, [
            (const.ONLINE, u'在线'),
            (const.OFFLINE, u'封禁')]
        ),
        LikeFilter('nickname', u'昵称'),
        EqualFilter('partner_migu.id', u'咪咕平台ID', str),
    )

    def edit_form(self, obj):
        info = {'status': obj['status'], 'uid': str(obj['_id']), 'uname': obj['nickname']}
        if obj['status'] and 'bans' in obj:
            obj['bans'].update(info)
        else:
            obj['bans'] = info
        return super(UserAdmin, self).edit_form(obj)

    def update_model(self, form, model, exclude_fields=[]):
        user_lift_bans = form.status.data == 0 and model['status'] == 1
        ret = super(UserAdmin, self).update_model(form, model, exclude_fields)
        if ret is False or user_lift_bans is False:
            return ret
        uid = model['_id']
        sysmsg = SysMessage.init()
        sysmsg.title = u"用户解封禁通知"
        sysmsg.owner = ObjectId(uid)
        sysmsg.content = u"您的帐号已解除封禁，请遵守社区规定，维护健康文明的网络环境。"
        _id = sysmsg.create_model()
        return ret


class GroupForm(form.Form):
    name = fields.StringField(u'组名', [validators.Required()])
    gtype = fields.SelectField(u'组类型', [validators.InputRequired()],
                               coerce=str, choices=GROUP_TYPE)
    memo = fields.StringField(u'备注', [validators.Optional()])


class GroupAdmin(WxModelView):
    Model = Group
    form = GroupForm
    can_view_details = True
    details_modal = True
    column_details_list = ['_id', 'name', 'gtype', 'memo', 'create_at']
    column_list = ('_id', 'name', 'gtype', 'memo')
    column_labels = dict(_id=u'组ID', name=u'组名', gtype=u'类型', memo=u'备注', create_at=u'创建时间')
    column_formatters = dict(
        gtype=lambda v, c, m, n: util.get_choices_desc(GROUP_TYPE, m['gtype']),
    )
    column_filters = (
        EqualFilter('_id', u'组ID', ObjectId),
        EqualFilter('gtype', u'类型', str, GROUP_TYPE),
        LikeFilter('name', u'组名'),
    )


class UserGroupForm(form.Form):
    group = fields.SelectField(u'组名', [validators.InputRequired()], coerce=ObjectId)
    user = ObjectIdField(u'用户ID', [validators.Optional()])
    phone = fields.StringField(u'手机号', [validators.Optional()])

    def validate(self):
        if not form.Form.validate(self):
            return False

        if not self.user.data and not self.phone.data:
            self.phone.errors.append(u'用户和手机号必须要填一个')

        user1 = User.get_one(self.user.data) if self.user.data else None
        user2 = User.get_by_phone(self.phone.data) if self.phone.data else None
        if self.user.data and not user1:
            self.user.errors.append(u'用户不存在')
            return False

        if self.phone.data and not user2:
            self.phone.errors.append(u'用户不存在')
            return False

        if self.phone.data and self.user.data:
            if user1 != user2:
                self.user.errors.append(u'用户字段和手机号字段对应的用户不匹配')
                self.phone.errors.append(u'用户字段和手机号字段对应的用户不匹配')
                return False

        user = user1 or user2
        if UserGroup.user_in_group(str(self.group.data), str(user._id)):
            if user1:
                self.user.errors.append(u'该组已包含此用户')
            if user2:
                self.phone.errors.append(u'该组已包含此用户')
            return False

        return True


class UserGroupAdmin(WxModelView):
    Model = UserGroup
    form = UserGroupForm
    can_view_details = True
    details_modal = True
    column_details_list = ['_id', 'group', 'user', 'phone', 'create_at']
    column_list = ('_id', 'group', 'user', 'phone')
    column_labels = dict(_id=u'分组ID', group=u'组名', user=u'用户', phone=u'手机号',
                         create_at=u'创建时间')
    column_formatters = dict(
        group=format_group,
        user=format_user,
    )
    column_filters = (
        EqualFilter('group', u'组ID', ObjectId),
        EqualFilter('user', u'用户ID', ObjectId),
        EqualFilter('phone', u'手机号'),
    )

    def process_form_data(self, data):
        if data['phone'] and not data['user']:
            user = User.get_by_phone(data['phone'])
            data['user'] = user._id
        if data['user'] and not data['phone']:
            user = User.get_one(data['user'])
            data['phone'] = user.phone

        return data

    def create_model(self, form):
        model = super(UserGroupAdmin, self).create_model(form)
        return model

    def update_model(self, form, model):
        ret = super(UserGroupAdmin, self).update_model(form, model)
        return ret

    def create_form(self, obj=None):
        form = super(UserGroupAdmin, self).create_form(obj)
        form.group.choices = Group.groups_for_admin()
        return form

    def edit_form(self, obj=None):
        form = super(UserGroupAdmin, self).edit_form(obj)
        form.group.choices = Group.groups_for_admin()
        return form


class UserTrafficLogForm(form.Form):
    source = ObjectIdField(u'创建用户', [validators.Required()])
    order_id = fields.StringField(u'订单号', [validators.Required()])
    status = fields.SelectField(u'状态', [validators.InputRequired()], coerce=int,
                                choices=[
                                    (const.TRAFFIC_SUCCESS, u'充值成功'),
                                    (const.TRAFFIC_PROCESS, u'充值中'),
                                    (const.TRAFFIC_RECEIVED_PROCESS, u'流量到账正在处理中'),
                                    (const.TRAFFIC_RECEIVED_SUCCESS, u'流量到账成功'),
                                    (const.TRAFFIC_RECEIVED_FAIL, u'流量到账失败'),
                                    (const.TRAFFIC_FAIL, u'充值失败')]
                                )
    traffic_type = fields.SelectField(u'流量类型', [validators.InputRequired()], coerce=str,
                                      choices=[
                                          ('first_login', u'首次登录'),
                                          ('video_share', u'视频分享')]
                                      )


def _filter_phone(value):
    user = User.get_by_phone(value)
    return user._id if user else None


class UserTrafficLogAdmin(WxModelView):
    Model = UserTrafficLog
    form = UserTrafficLogForm

    list_template = 'model_list.html'

    can_create = True
    can_export = True

    column_details_list = ('order_id', 'source', 'status', 'traffic_type', 'phone',
                           'device', 'create_at')

    column_list = ('order_id', 'source', 'status', 'traffic_type', 'phone',
                   'device', 'create_at')
    column_labels = dict(order_id=u'订单号', source=u'用户ID', status=u'充值状态',
                         traffic_type=u'流量类型', create_at=u'分享时间')

    column_formatters = dict(
        phone=format_user_phone,
        source=format_user,
        status=format_traffic_status,
        traffic_type=format_traffic_type,
        create_at=format_timestamp
    )

    column_filters = (
        SmallerFilter('create_at', u'创建时间', util.str2timestamp),
        GreaterFilter('create_at', u'创建时间', util.str2timestamp),
        EqualFilter('order_id', u'订单号', str),
        EqualFilter('source', u'用户ID', ObjectId),
        EqualFilter('device', u'device', str),
        EqualFilter('source', u'手机号', _filter_phone),
        EqualFilter('traffic_type', u'流量类型', str, [
            ('first_login', u'首次登录'),
            ('video_share', u'视频分享')
        ]),
        EqualFilter('status', u'充值状态', int, [
            (const.TRAFFIC_SUCCESS, u'充值成功'),
            (const.TRAFFIC_PROCESS, u'充值中'),
            (const.TRAFFIC_RECEIVED_PROCESS, u'流量到账正在处理中'),
            (const.TRAFFIC_RECEIVED_SUCCESS, u'流量到账成功'),
            (const.TRAFFIC_RECEIVED_FAIL, u'流量到账失败'),
            (const.TRAFFIC_FAIL, u'充值失败')
        ])
    )

    def get_export_csv(self):
        if not self.export_columns:
            self.export_columns = [column_name for column_name, _ in self._list_columns]

        io = StringIO()
        rows = csv.DictWriter(io, self.export_columns)

        data = self._get_data_for_export()

        rows.writeheader()
        for item in data:
            row = dict()
            for column in self.export_columns:
                if column == 'phone':
                    obj = User.get_one(item['source'], check_online=False)
                    item[column] = obj.phone
                elif column == 'create_at':
                    item[column] = util.timestamp2str(item['column'])
                elif column == 'status':
                    _value = item[column]
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
                    item[column] = _value
                elif column not in item:
                    item[column] = None

                row.update({column: unicode(item[column]).encode("utf8")})

            # print row
            rows.writerow(row)

        io.seek(0)
        return io.getvalue()
