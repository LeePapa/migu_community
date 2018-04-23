# -*- coding: utf8 -*-
from bson import ObjectId
from flask.ext.admin.contrib.peewee import ModelView
from flask.ext.admin.form import widgets as admin_widgets
from wtforms import form, fields, validators, FileField

from wanx.admin.base import WxModelView
from wanx.base import const
from wanx.base.xredis import Redis
from wanx.base.util import get_choices_desc
from wanx.models.activity import ActivityConfig
from wanx.models.home import Channels
from wanx.models.live import WatchLiveTask, WatchLiveTaskItem
from wanx.models.task import TASK_TYPE, TASK_ACTION, TASK_KEY, UserTask, TASK_PLATFORMS, Task
from wanx.models.product import PRODUCT_TYPE, PRODUCT_KEY, Product
from wanx.models.gift import CREDIT_TYPE, ONSALE_GIFT_KEY
from wanx.models import store
from wanx.admin.util import format_image, format_game, format_user, TimeStampField, format_timestamp, format_choices, \
    format_model
from wanx.admin.filter import PeeweeEqualFilter
from wanx.models.xconfig import VersionConfig, Province
from wanx.models.user import Group


class ProductForm(form.Form):
    product_name = fields.StringField(u'物品名称', [validators.Required()])
    product_image = fields.StringField(u'图片', [validators.Optional()])
    product_type = fields.SelectField(u'物品类型', [validators.InputRequired()], coerce=int,
                                      choices=PRODUCT_TYPE)
    recycle_gem_price = fields.IntegerField(u'回购游票价格', [validators.InputRequired()], default=0)


class ProductAdmin(ModelView):
    form = ProductForm
    can_view_details = True
    details_modal = True
    column_details_list = ('product_id', 'product_name', 'product_image', 'product_type',
                           'recycle_gem_price')
    column_list = ('product_id', 'product_name', 'product_image', 'product_type',
                   'recycle_gem_price')
    column_labels = dict(product_id=u'物品ID', product_name=u'名称', product_image=u'图片',
                         product_type=u'物品类型', recycle_gem_price=u'回购游票价格')
    column_formatters = dict(
        product_image=format_image,
        product_type=lambda v, c, m, n: get_choices_desc(PRODUCT_TYPE, m.product_type),
    )

    def after_model_change(self, form, model, is_created):
        super(ProductAdmin, self).after_model_change(form, model, is_created)
        Redis.delete(PRODUCT_KEY)

    def after_model_delete(self, model):
        super(ProductAdmin, self).after_model_delete(model)
        Redis.delete(PRODUCT_KEY)


class TaskForm(form.Form):
    title = fields.StringField(u'标题', [validators.Required()])
    description = fields.StringField(u'描述', [validators.Required()])
    image = fields.StringField(u'标签图片', [validators.Optional()])
    cover = fields.StringField(u'封面图片', [validators.Optional()])
    task_type = fields.SelectField(u'任务类型', [validators.InputRequired()], coerce=int,
                                   choices=TASK_TYPE)
    action = fields.SelectField(u'任务条件', [validators.InputRequired()], coerce=int,
                                choices=TASK_ACTION)
    activity_id = fields.StringField(u'活动ID')
    task_platform = fields.SelectField(u"任务平台", [validators.InputRequired()], coerce=int,
                                   choices=TASK_PLATFORMS)
    num = fields.IntegerField(u'条件数值', [validators.InputRequired()], default=1)
    game_id = fields.StringField(u'游戏ID', [validators.Optional()])
    product_id = fields.SelectField(u'奖励物品ID', [validators.InputRequired()], coerce=int)
    product_num = fields.IntegerField(u'奖励物品数量', [validators.InputRequired()])
    button_action = fields.StringField(u'按钮跳转链接', [validators.Optional()])
    order = fields.IntegerField(u'显示顺序', [validators.InputRequired()], default=1)
    topest = fields.BooleanField(u'置顶任务')


class TaskAdmin(ModelView):
    form = TaskForm
    can_view_details = True
    details_modal = True
    column_details_list = ('title', 'description', 'image', 'task_type', 'action', 'activity_id',
                           'task_platform', 'game_id', 'num', 'product_id', 'product_num')
    column_list = ('title', 'description', 'image', 'task_type', 'action', 'task_platform', 'num',
                   'product_id', 'product_num')
    column_labels = dict(title=u'标题', description=u'描述', image=u'图片', task_type=u'任务类型',
                         action=u'任务条件', game_id=u'游戏ID', num=u'条件数值', product_id=u'奖励物品',
                         product_num=u'奖励物品数量', task_platform=u'任务平台', activity_id=u'活动ID')
    column_formatters = dict(
        image=format_image,
        task_type=lambda v, c, m, n: get_choices_desc(TASK_TYPE, m.task_type),
        action=lambda v, c, m, n: get_choices_desc(TASK_ACTION, m.action),
        game_id=format_game,
        product_id=lambda v, c, m, n: get_choices_desc(Product.all_products_for_admin(),
                                                       m.product_id),
        task_platform=lambda v, c, m, n: get_choices_desc(TASK_PLATFORMS, m.task_platform),
    )

    def create_form(self, obj=None):
        form = super(TaskAdmin, self).create_form(obj)
        form.product_id.choices = Product.all_products_for_admin()
        # aids = [('', u'不限定')]
        # aids.extend(ActivityConfig.activity())
        # form.activity_id.choices = aids
        return form

    def edit_form(self, obj=None):
        form = super(TaskAdmin, self).edit_form(obj)
        form.product_id.choices = Product.all_products_for_admin()
        # aids = [('', u'不限定')]
        # aids.extend(ActivityConfig.activity())
        # form.activity_id.choices = aids
        form.task_type.choices = filter(lambda x:x[0] == obj.task_type, TASK_TYPE)
        return form

    def after_model_change(self, form, model, is_created):
        super(TaskAdmin, self).after_model_change(form, model, is_created)
        Redis.delete(TASK_KEY)

    def after_model_delete(self, model):
        super(TaskAdmin, self).after_model_delete(model)
        UserTask.delete().where(UserTask.task_id==model.task_id).execute()
        Redis.delete(TASK_KEY)

    def create_model(self, form):
        if form.topest.data:
            Task.reset_topest_task()
        return super(TaskAdmin, self).create_model(form)

    def update_model(self, form, model):
        if form.topest.data:
            Task.reset_topest_task()
        return super(TaskAdmin, self).update_model(form, model)


class GiftForm(form.Form):
    product_id = fields.SelectField(u'物品ID', [validators.InputRequired()], coerce=int)
    credit_type = fields.SelectField(u'价格类型', [validators.InputRequired()], coerce=int,
                                     choices=CREDIT_TYPE)
    credit_value = fields.IntegerField(u'价格数值', [validators.InputRequired()])
    on_sale = fields.BooleanField(u'是否在售', default=True)


class GiftAdmin(ModelView):
    form = GiftForm
    can_view_details = True
    details_modal = True
    column_details_list = ('gift_id', 'product_id', 'credit_type', 'credit_value', 'on_sale')
    column_list = ('gift_id', 'product_id', 'credit_type', 'credit_value', 'on_sale')
    column_labels = dict(gift_id=u'礼物ID', product_id=u'物品', credit_type=u'价格类型',
                         credit_value=u'价格数值', on_sale=u'是否在售')
    column_formatters = dict(
        credit_type=lambda v, c, m, n: get_choices_desc(CREDIT_TYPE, m.credit_type),
        product_id=lambda v, c, m, n: get_choices_desc(Product.all_gifts_for_admin(),
                                                       m.product_id)
    )

    def create_form(self, obj=None):
        form = super(GiftAdmin, self).create_form(obj)
        form.product_id.choices = Product.all_gifts_for_admin()
        return form

    def edit_form(self, obj=None):
        form = super(GiftAdmin, self).edit_form(obj)
        form.product_id.choices = Product.all_gifts_for_admin()
        return form

    def after_model_change(self, form, model, is_created):
        super(GiftAdmin, self).after_model_change(form, model, is_created)
        Redis.delete(ONSALE_GIFT_KEY)

    def after_model_delete(self, model):
        super(GiftAdmin, self).after_model_delete(model)
        Redis.delete(ONSALE_GIFT_KEY)


class StoreForm(form.Form):
    store_type = fields.SelectField(u'商店类型', [validators.InputRequired()], coerce=int,
                                    choices=store.STORE_TYPE)
    title = fields.StringField(u'标题', [validators.Required()])
    credit_type = fields.SelectField(u'价格类型', [validators.InputRequired()], coerce=int,
                                     choices=store.CREDIT_TYPE)
    credit_value = fields.IntegerField(u'价格数值', [validators.InputRequired()], default=0)
    status = fields.SelectField(u'状态', [validators.InputRequired()], coerce=int,
                                choices=store.STORE_STATUS)
    begin_at = fields.DateTimeField(u'开始时间', [validators.Required()], format='%Y-%m-%d %H:%M:%S',
                                    widget=admin_widgets.DateTimePickerWidget())
    expire_at = fields.DateTimeField(u'结束时间', [validators.Required()], format='%Y-%m-%d %H:%M:%S',
                                     widget=admin_widgets.DateTimePickerWidget())
    order = fields.IntegerField(u'显示顺序', [validators.Required()])
    action = fields.StringField(u'活动链接', [validators.Optional()])
    campaign_id = fields.StringField(u'营销平台活动ID', [validators.Optional()])
    resource_campaign_id = fields.StringField(u'营销平台流量话费发放活动ID', [validators.Optional()])
    share_image = fields.StringField(u'分享图片', [validators.Optional()])
    share_title = fields.StringField(u'分享标题', [validators.Optional()])


class StoreAdmin(ModelView):
    form = StoreForm
    can_view_details = True
    details_modal = True
    column_details_list = ('store_id', 'store_type', 'title', 'credit_type', 'credit_value',
                           'status', 'begin_at', 'expire_at', 'action', 'campaign_id',
                           'resource_campaign_id', 'order', 'share_image', 'share_title')
    column_list = ('store_id', 'store_type', 'title', 'credit_type', 'credit_value', 'status',
                   'campaign_id', 'resource_campaign_id', 'order')
    column_labels = dict(store_id=u'商店ID', store_type=u'商店类型', title=u'标题', credit_type=u'价格类型',
                         credit_value=u'价格数值', status=u'状态', begin_at=u'开始时间',
                         expire_at=u'结束时间', campaign_id=u'营销平台活动ID',
                         resource_campaign_id=u'营销平台流量话费发放活动ID',
                         action=u'活动链接', order=u'显示顺序', share_image=u'分享图片', share_title=u'分享标题')
    column_formatters = dict(
        store_type=lambda v, c, m, n: get_choices_desc(store.STORE_TYPE, m.store_type),
        credit_type=lambda v, c, m, n: get_choices_desc(store.CREDIT_TYPE, m.credit_type),
        status=lambda v, c, m, n: get_choices_desc(store.STORE_STATUS, m.status),
    )

    def after_model_change(self, form, model, is_created):
        super(StoreAdmin, self).after_model_change(form, model, is_created)
        Redis.delete(store.ALL_STORE_KEY)

    def after_model_delete(self, model):
        super(StoreAdmin, self).after_model_delete(model)
        Redis.delete(store.ALL_STORE_KEY)


class StoreItemForm(form.Form):
    store_id = fields.SelectField(u'商店ID', [validators.InputRequired()], coerce=int)
    product_id = fields.SelectField(u'物品ID', [validators.InputRequired()], coerce=int)
    product_num = fields.IntegerField(u'物品数量', default=1)
    title = fields.StringField(u'商品描述', [validators.InputRequired()])
    credit_type = fields.SelectField(u'价格类型', [validators.InputRequired()], coerce=int,
                                     choices=store.CREDIT_TYPE)
    credit_value = fields.IntegerField(u'价格数值', [validators.InputRequired()], default=0)
    total_num = fields.IntegerField(u'总库存(份)')
    use_num = fields.IntegerField(u'消耗库存(份)', default=0)
    left_num = fields.IntegerField(u'剩余库存(份)')
    order = fields.IntegerField(u'显示顺序')
    identity = fields.StringField(u'营销平台奖项ID', [validators.Optional()])


class StoreItemAdmin(ModelView):
    form = StoreItemForm
    can_view_details = True
    details_modal = True
    column_details_list = ('store_id', 'product_id', 'product_num', 'title', 'credit_type',
                           'credit_value', 'total_num', 'use_num', 'left_num', 'order', 'identity')
    column_list = ('store_id', 'product_id', 'product_num', 'credit_type', 'credit_value',
                   'left_num', 'order', 'identity')
    column_labels = dict(store_id=u'商店', product_id=u'物品', product_num=u'物品数量', title=u'商品描述',
                         credit_type=u'价格类型', credit_value=u'价格数值', total_num=u'总库存',
                         use_num=u'已用库存', left_num=u'剩余库存', order=u'显示顺序', identity=u'营销平台奖项ID')
    column_formatters = dict(
        store_id=lambda v, c, m, n: get_choices_desc(store.Store.all_stores_for_admin(),
                                                     m.store_id),
        product_id=lambda v, c, m, n: get_choices_desc(Product.all_products_for_admin(),
                                                       m.product_id),
        credit_type=lambda v, c, m, n: get_choices_desc(store.CREDIT_TYPE, m.credit_type),
    )
    column_filters = ('store_id',)

    def create_form(self, obj=None):
        form = super(StoreItemAdmin, self).create_form(obj)
        form.store_id.choices = store.Store.all_stores_for_admin()
        form.product_id.choices = Product.all_products_for_admin()
        return form

    def edit_form(self, obj=None):
        form = super(StoreItemAdmin, self).edit_form(obj)
        form.store_id.choices = filter(lambda x: x[0] == obj.store_id, store.Store.all_stores_for_admin())
        # form.store_id.choices = store.Store.all_stores_for_admin()
        form.product_id.choices = Product.all_products_for_admin()
        return form

    def after_model_change(self, form, model, is_created):
        super(StoreItemAdmin, self).after_model_change(form, model, is_created)
        key = store.STORE_ITEM_KEY % ({'store_id': model.store_id})
        Redis.delete(key)

    def after_model_delete(self, model):
        super(StoreItemAdmin, self).after_model_delete(model)
        key = store.STORE_ITEM_KEY % ({'store_id': model.store_id})
        Redis.delete(key)


class UserOrderForm(form.Form):
    order_id = fields.IntegerField(u'订单ID', [validators.InputRequired()])
    status = fields.SelectField(u'状态', [validators.InputRequired()], coerce=int,
                                choices=store.STATUS)


class UserOrderAdmin(ModelView):
    form = UserOrderForm
    can_create = False
    can_delete = False
    can_view_details = True
    details_modal = True
    column_details_list = ('order_id', 'user_id', 'item_id', 'store_id', 'store_type',
                           'campaign_id', 'title', 'product_id', 'product_num', 'status',
                           'result', 'recid', 'create_at')
    column_list = ('order_id', 'user_id', 'title', 'product_num', 'store_id', 'status')
    column_labels = dict(order_id=u'订单ID', user_id=u'用户', item_id=u'商品', store_id=u'商店',
                         store_type=u'商店类型', campaign_id=u'营销平台活动ID', title=u'商品描述',
                         product_id=u'物品', product_num=u'物品数量', status=u'状态',
                         result=u'抽奖结果', recid=u'营销平台兑换订单', create_at=u'创建时间')
    column_formatters = dict(
        store_id=lambda v, c, m, n: get_choices_desc(store.Store.all_stores_for_admin(),
                                                     m.store_id),
        product_id=lambda v, c, m, n: get_choices_desc(Product.all_products_for_admin(),
                                                       m.product_id),
        store_type=lambda v, c, m, n: get_choices_desc(store.STORE_TYPE, m.store_type),
        status=lambda v, c, m, n: get_choices_desc(store.STATUS, m.status),
        user_id=format_user
    )
    column_filters = (
        'user_id',
        PeeweeEqualFilter(
            column=store.UserOrder.store_id, name='商店',
            options=store.Store.all_stores_for_admin()
        ),
        PeeweeEqualFilter(
            column=store.UserOrder.status, name='订单状态',
            options=store.STATUS
        ),
        PeeweeEqualFilter(
            column=store.UserOrder.product_id, name='物品',
            options=Product.all_products_for_admin()
        ),
    )


class UserOrderAddressForm(form.Form):
    pass


class UserOrderAddressAdmin(ModelView):
    form = UserOrderAddressForm
    can_create = False
    can_delete = False
    can_edit = False
    can_view_details = True
    details_modal = True
    column_details_list = ('order_id', 'user_id', 'name', 'phone', 'id_card', 'address',
                           'create_at')
    column_list = ('order_id', 'user_id', 'name', 'phone', 'id_card', 'address')
    column_labels = dict(order_id=u'订单ID', user_id=u'用户', name=u'真实名字', phone=u'手机号',
                         id_card=u'身份证', address=u'地址', create_at=u'创建时间')
    column_formatters = dict(
        user_id=format_user
    )
    column_filters = ('user_id', 'order_id')


class WatchLiveTaskForm(form.Form):
    name = fields.StringField(u'活动标题', [validators.DataRequired()])
    status = fields.SelectField(u'状态',
                                [validators.InputRequired()],
                                coerce=int,
                                choices=[
                                    (const.ONLINE, u'在线'),
                                    (const.OFFLINE, u'下线')
                                ])
    begin_at = TimeStampField(u'开始时间', [validators.DataRequired()])
    expire_at = TimeStampField(u'结束时间', [validators.DataRequired()])
    duration = fields.IntegerField(u'观看时长要求\n单位：分钟', [validators.InputRequired()], default=5)
    chance = fields.IntegerField(u'每日上限次数', [validators.InputRequired()], default=3)
    icon = fields.StringField(u'按钮图标', [validators.DataRequired()])
    os = fields.SelectField(u'平台要求', [validators.InputRequired()],
                            choices=[
                                ('all', u'全部'),
                                ('android', u'Android'),
                                ('ios', u'IOS')], default=u'全部')
    channels = fields.SelectMultipleField(u'推广渠道', [validators.Optional()])
    group = fields.SelectField(u'用户组', coerce=ObjectId)
    version_code_mix = fields.SelectField(u'版本要求(版本号大于等于)', [validators.Optional()],
                                          coerce=int)
    version_code_max = fields.SelectField(u'版本要求(版本号小于等于)', [validators.Optional()],
                                          coerce=int)
    province = fields.SelectMultipleField(u'省份', [validators.Optional()])
    campaign_id = fields.StringField(u'营销平台活动ID', [validators.InputRequired()])


class WatchLiveTaskAdmin(WxModelView):
    Model = WatchLiveTask
    form = WatchLiveTaskForm
    column_list = ('_id', 'name', 'status', 'campaign_id', 'os', 'begin_at', 'expire_at')
    column_labels = dict(_id=u'活动ID', name=u'活动标题', status=u'活动状态', campaign_id=u'营销平台活动ID',
                         os=u'平台要求', begin_at=u'开始时间', expire_at=u'结束时间')
    column_formatters = dict(
        icon=format_image,
        status=format_choices,
        os=format_choices,
        begin_at=format_timestamp,
        expire_at=format_timestamp,
    )

    def create_form(self, obj=None):
        form = super(WatchLiveTaskAdmin, self).create_form(obj)
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
        form = super(WatchLiveTaskAdmin, self).edit_form(obj)
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

    def create_model(self, form=None):
        model = super(WatchLiveTaskAdmin, self).create_model(form)
        self.Model.clear_redis()
        return model

    def delete_model(self, model):
        super(WatchLiveTaskAdmin, self).delete_model(model)
        self.Model.clear_redis()


class WatchLiveTaskItemForm(form.Form):
    wlt_id = fields.SelectField(
        u'观看直播时长任务ID', [validators.InputRequired()], coerce=ObjectId)
    product_id = fields.SelectField(
        u'物品ID', [validators.InputRequired()], coerce=int)
    product_num = fields.IntegerField(u'物品数量', default=1)
    title = fields.StringField(u'商品描述', [validators.InputRequired()])
    identity = fields.StringField(u'营销平台奖项ID', [validators.Optional()])


class WatchLiveTaskItemAdmin(WxModelView):
    Model = WatchLiveTaskItem
    form = WatchLiveTaskItemForm
    can_view_details = True
    details_modal = True
    column_details_list = ('wlt_id', 'product_id', 'product_num', 'title',  'identity')
    column_labels = dict(wlt_id=u'观看直播时长任务ID', product_id=u'物品', product_num=u'物品数量', title=u'商品描述',
                         identity=u'营销平台奖项ID')
    column_formatters = dict(
        wlt_id=lambda v, c, m, n: format_model(m, n, WatchLiveTask),
        product_id=lambda v, c, m, n: get_choices_desc(Product.all_products_for_admin(), m[n]),
    )

    def create_form(self, obj=None):
        form = super(WatchLiveTaskItemAdmin, self).create_form(obj)
        form.wlt_id.choices = WatchLiveTask.all_tasks_for_admin()
        form.product_id.choices = Product.all_products_for_admin()
        return form

    def edit_form(self, obj=None):
        form = super(WatchLiveTaskItemAdmin, self).edit_form(obj)
        form.wlt_id.choices = WatchLiveTask.all_tasks_for_admin()
        form.product_id.choices = Product.all_products_for_admin()
        return form

    def after_model_change(self, form, model, is_created):
        super(WatchLiveTaskItemAdmin, self).after_model_change(form, model, is_created)
        self.Model.clear_redis(form.wlt_id.data)
        self.Model.clear_redis(model['wlt_id'])

    def after_model_delete(self, model):
        super(WatchLiveTaskItemAdmin, self).after_model_delete(model)
        self.Model.clear_redis(model['wlt_id'])

