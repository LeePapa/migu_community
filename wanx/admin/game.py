# -*- coding: utf8 -*-
from bson.objectid import ObjectId
from wtforms import form, fields, validators

from wanx.base.util import get_choices_desc
from .base import WxModelView
from .util import (JsonField, format_category, format_icon,
                   format_game, format_image, format_status, format_choices)
from .filter import EqualFilter, LikeFilter, CategoryFileter
from wanx.base import const
from wanx.models.game import Game, Category, CategoryGame, GameRecommendSubscribe, WebGame


class GamePlatformForm(form.Form):
    url = fields.StringField(u"下载链接", [validators.Optional()])
    package_id = fields.StringField(u'软件包ID', [validators.Required()])
    package_segment = fields.StringField(u'主播工具匹配包名特征', [validators.Optional()])
    bid = fields.StringField(u'咪咕平台游戏ID', [validators.Optional()])
    bcode = fields.StringField(u'咪咕平台CODE', [validators.Optional()])
    version = fields.StringField(u'版本号', [validators.Required()])
    size = fields.FloatField(u'包大小(M)', [validators.Required()], default=0.0)
    contain_sdk = fields.BooleanField(u'是否包含SDK', default=False)
    cover = fields.StringField(u'封面图片', [validators.Required()])
    icon = fields.StringField(u'图标', [validators.Required()])
    big_icon = fields.StringField(u'大图标', [validators.Required()])
    status = fields.SelectField(u'状态',
                                [validators.InputRequired()],
                                coerce=int,
                                choices=[
                                    (const.ONLINE, u'在线'),
                                    (const.OFFLINE, u'下线'),
                                    (const.UNDER_TEST, u'测试')
                                ])
    migu = JsonField(u'咪咕信息', [validators.Optional()])
    is_download = fields.BooleanField(u'是否可下载', default=False)
    is_subscribe = fields.BooleanField(u'是否可订阅', default=False)


class GameForm(form.Form):
    name = fields.StringField(u'游戏名', [validators.Required()])
    url = fields.StringField(u'Android下载链接', [validators.Optional()])
    url_ios = fields.StringField(u'IOS跳转链接', [validators.Optional()])
    description = fields.TextAreaField(u'描述', [validators.Required()])
    intro = fields.StringField(u'简介', [validators.Optional()])
    slogan = fields.StringField(u'标语', [validators.Optional()])
    developer = fields.StringField(u'开发者', [validators.Required()])
    package_id = fields.StringField(u'软件包ID', [validators.Required()])
    package_segment = fields.StringField(u'主播工具匹配包名特征', [validators.Optional()])
    bid = fields.StringField(u'咪咕平台游戏ID', [validators.Optional()])
    bcode = fields.StringField(u'咪咕平台CODE', [validators.Optional()])
    version = fields.StringField(u'版本号', [validators.Required()])
    size = fields.FloatField(u'包大小(M)', [validators.Required()], default=0.0)
    contain_sdk = fields.BooleanField(u'是否包含SDK', default=False)
    cover = fields.StringField(u'封面图片', [validators.Required()])
    icon = fields.StringField(u'图标', [validators.Required()])
    big_icon = fields.StringField(u'大图标', [validators.Required()])
    status = fields.SelectField(u'状态',
                                [validators.InputRequired()],
                                coerce=int,
                                choices=[
                                    (const.ONLINE, u'上架'),
                                    (const.OFFLINE, u'下线'),
                                    (const.UNDER_TEST, u'测试'),
                                    (const.OFFSHELF, u'非上架')
                                ])
    migu = JsonField(u'咪咕信息', [validators.Optional()])
    is_download = fields.BooleanField(u'是否可下载（Android）', default=False)
    is_subscribe = fields.BooleanField(u'是否可订阅（Android）', default=False)
    is_download_ios = fields.BooleanField(u'是否可下载（IOS）', default=False)
    is_subscribe_ios = fields.BooleanField(u'是否可订阅（IOS）', default=False)
    on_assistant = fields.BooleanField(u'是否在游玩助手上架', default=True)
    categories = fields.SelectMultipleField(u'分类', [validators.Optional()], coerce=ObjectId)
    # platform = fields.FieldList(fields.FormField(GamePlatformForm),min_entries=1,default=("Android","IOS"))

class GameAdmin(WxModelView):
    Model = Game
    form = GameForm
    can_view_details = True
    details_modal = True
    column_details_list = ['_id', 'name', 'url', 'url_ios', 'bid', 'bcode', 'package_id',
                           'package_segment','version', 'size', 'contain_sdk', 'cover',
                           'icon', 'big_icon', 'status']
    column_list = ('_id', 'name', 'cover', 'icon', 'big_icon', 'status')
    column_labels = dict(_id=u'游戏ID', name=u'游戏名', url=u'Android下载链接',
                         url_ios=u'IOS跳转链接', bid=u'咪咕平台游戏ID',
                         bcode=u'咪咕平台CODE', package_id=u'软件包ID', version=u'版本号',
                         size=u'包大小(M)', contain_sdk=u'是否包含SDK', cover=u'封面图片',
                         icon=u'图标', big_icon=u'大图标', status=u'状态',
                         on_assistant=u'是否在游玩助手上架',package_segment=u'主播工具匹配包名特征')
    column_formatters = dict(icon=format_image, big_icon=format_image,
                             cover=format_image, status=format_choices)
    column_filters = (
        EqualFilter('_id', u'游戏ID', ObjectId),
        EqualFilter('status', u'状态', int, [
            (const.ONLINE, u'上架'),
            (const.OFFLINE, u'下线'),
            (const.UNDER_TEST, u'测试'),
            (const.OFFSHELF, u'非上架')]
        ),
        EqualFilter('bid', u'咪咕平台游戏ID'),
        LikeFilter('name', u'游戏名'),
    )

    def process_form_data(self, data):
        data.pop('categories')
        return data

    def create_model(self, form):
        new_cate_ids = form.categories.data
        model = super(GameAdmin, self).create_model(form)
        game = self.get_pk_value(model)
        for cate_id in new_cate_ids:
            cg = CategoryGame.init()
            cg.game = game
            cg.category = cate_id
            cg.order = 0
            cg.create_model()

        # 正式环境创建游戏时, 给stage环境也创建一个
        import os
        env = os.environ.get('WXENV')
        if env == 'Production':
            from pymongo import MongoClient
            from config import Stage
            client = MongoClient(Stage.MONGO_HOST, Stage.MONGO_PORT)
            stage_db = client[Stage.MONGO_DBNAME]
            pk = self.get_pk_value(model)
            obj = self.Model.get_one(pk, check_online=False)
            obj.status = const.ONLINE
            stage_db.games.insert_one(obj)
        return model

    def update_model(self, form, model):
        new_cate_ids = form.categories.data
        ret = super(GameAdmin, self).update_model(form, model)
        if ret:
            game = self.get_pk_value(model)
            old_cate_ids = CategoryGame.game_category_ids(str(game))
            need_delete_ids = [cid for cid in old_cate_ids if cid not in new_cate_ids]
            need_create_ids = [cid for cid in new_cate_ids if cid not in old_cate_ids]
            for cate_id in need_create_ids:
                cg = CategoryGame.init()
                cg.game = game
                cg.category = cate_id
                cg.order = 0
                cg.create_model()

            for cate_id in need_delete_ids:
                cg = CategoryGame.get_by_ship(str(game), str(cate_id))
                cg.delete_model() if cg else None

        return ret

    def create_form(self, obj=None):
        form = super(GameAdmin, self).create_form(obj)
        cids = Category.all_category_ids()
        categories = Category.get_list(cids)
        form.categories.choices = [(c._id, c.name) for c in categories]
        return form

    def edit_form(self, obj=None):
        obj['categories'] = CategoryGame.game_category_ids(obj['_id'])
        form = super(GameAdmin, self).edit_form(obj)
        cids = Category.all_category_ids()
        categories = Category.get_list(cids)
        form.categories.choices = [(c._id, c.name) for c in categories]
        return form


class CategoryForm(form.Form):
    name = fields.StringField(u'分类名', [validators.Required()])
    icon_type = fields.SelectField(
        u'游戏图标',
        [validators.Required()],
        choices=[
            ('icon', u'小图标'),
            ('big_icon', u'大图标')
        ]
    )
    order = fields.IntegerField(u'显示顺序', [validators.InputRequired()], default=0)


class CategoryAdmin(WxModelView):
    Model = Category
    form = CategoryForm
    column_list = ('_id', 'name', 'icon_type', 'order')
    column_labels = dict(_id=u'分类ID', name=u'分类名', icon_type=u'游戏图标', order=u'显示顺序')
    column_formatters = dict(icon_type=format_icon)
    column_filters = (
        EqualFilter('_id', u'分类ID', ObjectId),
    )


class CategoryGameForm(form.Form):
    game = fields.SelectField(u'游戏', [validators.InputRequired()], coerce=ObjectId)
    category = fields.SelectField(u'分类', [validators.InputRequired()], coerce=ObjectId)
    order = fields.IntegerField(u'显示顺序', [validators.InputRequired()], default=0)


class CategoryGameAdmin(WxModelView):
    Model = CategoryGame
    form = CategoryGameForm
    column_list = ('game', 'category', 'order')
    column_labels = dict(game=u'游戏', category=u'分类', order=u'显示顺序')
    column_formatters = dict(game=format_game, category=format_category)
    column_filters = (
        EqualFilter('game', u'游戏ID', ObjectId),
        EqualFilter('category', u'分类', ObjectId)
    )

    def create_form(self, obj=None):
        form = super(CategoryGameAdmin, self).create_form(obj)
        cids = Category.all_category_ids()
        categories = Category.get_list(cids)
        form.category.choices = [(c._id, c.name) for c in categories]
        form.game.choices = Game.online_games()
        return form

    def edit_form(self, obj=None):
        form = super(CategoryGameAdmin, self).edit_form(obj)
        cids = Category.all_category_ids()
        categories = Category.get_list(cids)
        form.category.choices = [(c._id, c.name) for c in categories]
        form.game.choices = Game.online_games()
        return form


class GameRecommendSubscribeForm(form.Form):
    game = fields.SelectField(u'游戏', [validators.InputRequired()], coerce=ObjectId)
    order = fields.IntegerField(u'显示顺序', [validators.InputRequired()], default=0)


class GameRecommendSubscribeAdmin(WxModelView):
    Model = GameRecommendSubscribe
    form = GameRecommendSubscribeForm
    column_list = ('game', 'order')
    column_labels = dict(game=u'游戏', order=u'显示顺序')
    column_formatters = dict(game=format_game, category=format_category)
    column_filters = (
        EqualFilter('game', u'游戏ID', ObjectId),
    )

    def create_form(self, obj=None):
        form = super(GameRecommendSubscribeAdmin, self).create_form(obj)
        form.game.choices = Game.online_games()
        return form

    def edit_form(self, obj=None):
        form = super(GameRecommendSubscribeAdmin, self).edit_form(obj)
        form.game.choices = Game.online_games()
        return form


class WebGameForm(form.Form):
    migu_code = fields.StringField(u"业务代码", [validators.Required()])
    name = fields.StringField(u'游戏名', [validators.Required()])
    url = fields.StringField(u'访问地址', [validators.Optional()])
    description = fields.TextAreaField(u'描述', [validators.Required()])
    categories = fields.StringField(u'分类名称', [validators.Optional()])
    engine = fields.SelectField(u'引擎',
                                [validators.Optional()],
                                coerce=int,
                                choices=[
                                    (1, u'普通'),
                                    (2, u'laya'),
                                    (3, u'白鹭'),
                                ])
    os = fields.SelectField(u'平台',
                                [validators.Optional()],
                                coerce=str,
                                choices=[
                                    ('android', u'Android'),
                                    ('ios', u'IOS')
                                ])
    intro = fields.StringField(u'简介', [validators.Optional()])
    slogan = fields.StringField(u'标语', [validators.Optional()])
    developer = fields.StringField(u'开发者', [validators.Required()])
    cover = fields.StringField(u'封面图片', [validators.Required()])
    icon = fields.StringField(u'图标', [validators.Required()])
    big_icon = fields.StringField(u'大图标', [validators.Required()])
    order = fields.IntegerField(u'显示顺序', [validators.Required()])
    status = fields.SelectField(u'状态',
                                [validators.InputRequired()],
                                coerce=int,
                                choices=[
                                    (const.ONLINE, u'在线'),
                                    (const.OFFLINE, u'下线'),
                                    (const.UNDER_TEST, u'测试')
                                ])


class WebGameAdmin(WxModelView):
    Model = WebGame
    form = WebGameForm
    can_view_details = True
    details_modal = True
    column_details_list = ['_id', 'migu_code', 'name', 'url', 'description', 'categories',
                           'engine', 'os', 'intro', 'slogan', 'developer', 'cover',
                           'icon', 'big_icon', 'order', 'status']
    column_list = ('_id', 'name', 'cover', 'icon', 'big_icon', 'status')
    column_labels = dict(_id=u'游戏ID', migu_code=u'业务代码', name=u'游戏名', url=u'访问地址',
                         description=u'描述', categories=u'分类', engine=u'引擎',
                         intro=u'简介', slogan=u'标语', cover=u'封面图片', os=u'平台',
                         icon=u'图标', big_icon=u'大图标', status=u'状态', order=u'显示顺序')
    column_formatters = dict(icon=format_image, big_icon=format_image,
                             cover=format_image, status=format_status,
                             engine=lambda v, c, m, n: get_choices_desc([
                                 (1, u'普通'),
                                 (2, u'laya'),
                                 (3, u'白鹭'),], m['engine']),)
    column_filters = (
        EqualFilter('_id', u'游戏ID', ObjectId),
        EqualFilter('status', u'状态', int, [
            (const.ONLINE, u'在线'),
            (const.OFFLINE, u'下线'),
            (const.UNDER_TEST, u'测试')]
        ),
        EqualFilter('os', u'平台', str, [
            ('android', u'Android'),
            ('ios', u'IOS')]
        ),
        LikeFilter('name', u'游戏名'),
    )
    # Modal Templates
    edit_template = 'edit.html'
    """edit modal template"""

    create_template = 'create.html'
    """create modal template"""

    def process_form_data(self, data):
        return data

    def create_model(self, form):
        model = super(WebGameAdmin, self).create_model(form)

        # 正式环境创建游戏时, 给stage环境也创建一个
        import os
        env = os.environ.get('WXENV')
        if env == 'Production':
            from pymongo import MongoClient
            from config import Stage
            client = MongoClient(Stage.MONGO_HOST, Stage.MONGO_PORT)
            stage_db = client[Stage.MONGO_DBNAME]
            pk = self.get_pk_value(model)
            obj = self.Model.get_one(pk, check_online=False)
            obj.status = const.ONLINE
            stage_db.web_games.insert_one(obj)
        return model

    def update_model(self, form, model):
        ret = super(WebGameAdmin, self).update_model(form, model)
        return ret

    def create_form(self, obj=None):
        form = super(WebGameAdmin, self).create_form(obj)
        return form

    def edit_form(self, obj=None):
        form = super(WebGameAdmin, self).edit_form(obj)
        return form


class OfflineGameForm(form.Form):
    status = fields.SelectField(u'状态',
                                [validators.InputRequired()],
                                coerce=int,
                                choices=[
                                    (const.ONLINE, u'在线'),
                                    (const.OFFLINE, u'下线'),
                                    (const.UNDER_TEST, u'测试')
                                ])


class OfflineGameAdmin(WxModelView):
    Model = Game
    form = OfflineGameForm
    _can_create = False
    column_details_list = ['_id', 'name', 'url', 'bid', 'package_id', 'version',
                           'size', 'cover', 'icon', 'big_icon', 'status']
    column_list = ('_id', 'name', 'cover', 'icon', 'big_icon', 'status')
    column_labels = dict(_id=u'游戏ID', name=u'游戏名', url=u'下载链接', bid=u'咪咕平台游戏ID',
                         package_id=u'软件包ID', version=u'版本号', size=u'包大小(M)', cover=u'封面图片',
                         icon=u'图标', big_icon=u'大图标', status=u'状态')
    column_formatters = dict(
        _id=format_game,
        icon=format_image,
        big_icon=format_image,
        cover=format_image,
        status=format_choices,
    )
    cids = Category.all_category_ids()
    categories = Category.get_list(cids)
    categories_list = list()
    categories_list.append(('', ''))
    for c in range(len(categories)):
        a_ = str(categories[c]._id)
        b_ = categories[c].name
        categories_list.append((a_, b_))

    column_filters = (
        EqualFilter('_id', u'游戏ID', ObjectId),
        LikeFilter('name', u'游戏名'),
        CategoryFileter('_id', u'游戏类型', str,
                        categories_list
                        )
    )

    def get_list(self, *args, **kwargs):
        self._filters.append(EqualFilter('status', '', int))
        args[4].append((-1, '', 1))
        count, data = super(OfflineGameAdmin,
                            self).get_list(*args, **kwargs)
        self._filters.pop(-1)
        args[4].pop(-1)
        return count, data

