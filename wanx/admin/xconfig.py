# -*- coding: utf8 -*-
from flask import flash
from wtforms import form, fields, validators
from .base import WxModelView
from wanx.models.xconfig import Config, VersionConfig, Province
from wanx.base import const


class ConfigForm(form.Form):
    title = fields.StringField(u'描述', [validators.Required()])
    key = fields.StringField(u'唯一标识', [validators.Required()])
    value = fields.StringField(u'数值', [validators.Required()])


class ConfigAdmin(WxModelView):
    Model = Config
    form = ConfigForm
    column_list = ('title', 'key', 'value')
    column_labels = dict(title=u'描述', key=u'唯一标识', value=u'数值')

    def create_model(self, form):
        value = self.Model.fetch(form.data['key'], None, None)
        if value is not None:
            return flash(u"唯一标识已存在", 'error')
        ret = super(ConfigAdmin, self).create_model(form)
        return ret

    def update_model(self, form, model):
        if model['key'] != form.data['key']:
            value = self.Model.fetch(form.data['key'], None, None)
            if value is not None:
                return flash(u"唯一标识已存在", 'error')
        ret = super(ConfigAdmin, self).update_model(form, model)
        return ret


class VersionConfigForm(form.Form):
    version_code = fields.IntegerField(u'版本号', [validators.InputRequired()])
    version_name = fields.StringField(u'版本名称', [validators.Required()])
    os = fields.SelectField(u'所属平台', [validators.InputRequired()], coerce=str,
                            choices=[
                                ('android', 'Android'),
                                ('ios', 'IOS')],
                            default='Android'
                            )
    status = fields.SelectField(u'状态', [validators.InputRequired()], coerce=int,
                                choices=[
                                    (const.ONLINE, u'已上线'),
                                    (const.OFFLINE, u'未上线')],
                                default=const.ONLINE
                                )
    note = fields.StringField(u'备注')


class VersionConfigAdmin(WxModelView):
    Model = VersionConfig
    form = VersionConfigForm

    column_list = ('version_code', 'version_name', 'os', 'status', 'note')
    column_labels = dict(version_code=u'版本号', version_name=u'版本名', os=u'所属平台',
                         status=u'上线情况', note=u'备注')


class ProvinceForm(form.Form):
    name = fields.StringField(u'省份名称', [validators.Required()])
    code = fields.StringField(u'省份代码', [validators.Required()])
    operators = fields.StringField(u'运营商', [validators.Required()])


class ProvinceAdmin(WxModelView):
    Model = Province
    form = ProvinceForm

    column_list = ('name', 'code', 'operators')
    column_labels = dict(name=u'省份名称', code=u'省份代码', operators=u'运营商')
