# -*- coding: utf8 -*-
from wtforms import form, fields, validators
from .base import WxModelView
from .util import format_image, ObjectIdField, format_user, format_timestamp
from .filter import LikeFilter
from wanx.models.msg import SysMessage, Letter, Suggestion
from flask.ext.admin.contrib.peewee import ModelView


class SysMsgForm(form.Form):
    title = fields.StringField(u'标题', [validators.Required()])
    content = fields.StringField(u'内容', [validators.Required()])
    image = fields.StringField(u'图片', [validators.Optional()])
    link = fields.StringField(u'链接', [validators.Optional()])


class SysMsgAdmin(WxModelView):
    Model = SysMessage
    form = SysMsgForm
    column_list = ('_id', 'title', 'content', 'image', 'link')
    column_labels = dict(_id=u'消息ID', title=u'标题', content=u'内容', image=u'图片', link=u'链接')
    column_formatters = dict(image=format_image)
    column_filters = (
        LikeFilter('content', u'内容'),
    )


class LetterForm(form.Form):
    owner = ObjectIdField(u'接收者', [validators.Required()])
    sender = ObjectIdField(u'发送者', [validators.Required()])
    content = fields.StringField(u'内容', [validators.Required()])


class LetterAdmin(WxModelView):
    Model = Letter
    form = LetterForm

    can_edit = False
    column_list = ('_id', 'content', 'sender', 'owner')
    column_labels = dict(_id=u'私信ID', content=u'内容', sender=u'发送者', owner=u'接收者')

    column_formatters = dict(owner=format_user, sender=format_user)


class SuggestionForm(form.Form):
    contact = ObjectIdField(u'接收者', [validators.Required()])
    content = fields.StringField(u'内容', [validators.Required()])
    user = ObjectIdField(u'发送人', [validators.Optional()])


class SuggestionAdmin(WxModelView):
    Model = Suggestion
    form = SuggestionForm

    can_edit = False
    can_create = False
    column_list = ('content', 'contact', 'user', 'create_at')
    column_labels = dict(content=u'内容', contact=u'联系方式', user=u'发送人', create_at=u'发送时间')
    column_formatters = dict(user=format_user, create_at=format_timestamp)


class BugReportForm(form.Form):
    err_type = fields.StringField(u'错误类型')
    create_at = fields.StringField(u'创建时间')
    exception = fields.StringField(u'异常类型')
    phone_model = fields.StringField(u'手机型号')
    os_version = fields.StringField(u'系统版本')
    phone_number = fields.StringField(u'手机号码')
    app_version = fields.StringField(u'APP版本')
    err_msg = fields.StringField(u'错误信息')
    err_app = fields.StringField(u'发生APP')
    extention = fields.StringField(u'自定义信息')


class BugReportAdmin(ModelView):
    form = BugReportForm
    can_view_details = True
    can_edit = False
    can_delete = False
    can_create = False
    details_modal = True
    column_details_list = ('err_type', 'create_at', 'exception', 'phone_model', 'os_version', 'phone_number',
                           'app_version', 'err_msg', 'err_app', 'extention')
    column_list = ('err_type', 'exception', 'phone_model', 'os_version',
                   'app_version', 'err_app')
    column_labels = dict(err_type=u'错误类型', exception=u'异常类型', phone_model=u'手机型号',
                         os_version=u'系统版本', app_version=u'APP版本', err_app=u'发生APP',
                         create_at=u'创建时间', err_msg=u'错误信息', phone_number=u'手机号码',
                         extention=u'自定义信息')

