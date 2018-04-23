# -*- coding: utf8 -*-
from bson.objectid import ObjectId
from wtforms import form, fields, validators
from .base import WxModelView
from .util import (format_game, format_image, format_user, ObjectIdField,
                   TimeStampField, format_timestamp, format_activity, format_video)
from .filter import EqualFilter, SmallerFilter, GreaterFilter, LikeFilter
from wanx.base import const, util
from wanx.models.user import User
from wanx.models.game import Game, GameActivity
from wanx.models.video import VideoTopic, TopicVideo
from wanx.models.activity import ActivityConfig, ActivityComment, ActivityVideo, VoteVideo

import csv
from datetime import datetime
from StringIO import StringIO
from flask.ext.admin import BaseView, expose


class GameActivityForm(form.Form):
    game = fields.SelectField(u'游戏', [validators.InputRequired()], coerce=ObjectId)
    game_name = fields.StringField(u'游戏展示名', [validators.Required()])
    game_icon = fields.StringField(u'游戏图标', [validators.Required()])
    activity = fields.SelectField(u'活动', [validators.InputRequired()], coerce=ObjectId)
    is_download = fields.BooleanField(u'是否可下载', default=False)
    package_id = fields.StringField(u'游戏软件包ID', [validators.Required()])


class GameActivityAdmin(WxModelView):
    Model = GameActivity
    form = GameActivityForm
    column_list = ('game', 'game_name', 'game_icon', 'activity')
    column_labels = dict(game=u'游戏', game_name=u'游戏显示名称',
                         game_icon=u'游戏显示图标', activity=u'活动')
    column_formatters = dict(game=format_game, game_icon=format_image, activity=format_activity)
    column_filters = (
        EqualFilter('game', u'游戏ID', ObjectId),
    )

    def create_form(self, obj=None):
        form = super(GameActivityAdmin, self).create_form(obj)
        form.game.choices = Game.online_games()
        form.activity.choices = ActivityConfig.activity()
        return form

    def edit_form(self, obj=None):
        form = super(GameActivityAdmin, self).edit_form(obj)
        form.game.choices = Game.online_games()
        form.activity.choices = ActivityConfig.activity()
        return form


class ActivityConfigForm(form.Form):
    name = fields.StringField(u'活动名称', [validators.Required()])
    type = fields.SelectField(u'活动类型', [validators.InputRequired()], coerce=int,
                              choices=[
                                  (const.FROM_LIVE, u'直播活动'),
                                  (const.FROM_RECORD, u'活动')]
                              )
    video_duration = fields.IntegerField(u'视频时长(秒)', [validators.InputRequired()])
    begin_at = TimeStampField(u'创建时间大于',  [validators.Optional()])
    end_at = TimeStampField(u'创建时间小于',  [validators.Optional()])
    max_video = fields.IntegerField(u'参赛作品上限', [validators.InputRequired()])
    max_prize = fields.IntegerField(u'单人获奖上限', [validators.InputRequired()])
    max_rank = fields.IntegerField(u'获奖名次上限', [validators.InputRequired()])
    vote_description = fields.StringField(u'投票提示语', [validators.Required()])
    vote_text = fields.StringField(u'投票按钮显示文字', [validators.Required()])
    voted_text = fields.StringField(u'已投票按钮显示文字', [validators.Required()])
    activity_url = fields.StringField(u'活动URL', [validators.Required()])
    share_banner = fields.StringField(u'活动分享页广告url',)
    share_description = fields.StringField(u'活动分享页活动介绍')
    share_vote_text = fields.StringField(u'分享页投票按钮显示文字', [validators.Required()])
    share_voted_text = fields.StringField(u'分享页已投票按钮显示文字', [validators.Required()])
    sort = fields.SelectField(u'排名依据', [validators.InputRequired()], coerce=str,
                              choices=[
                                  ('vote', u'投票'),
                                  ('like_count', u'点赞数'),
                                  ('comment_count', u'评论数'),
                                  ('vv', u'播放量')]
                              )
    status = fields.SelectField(u'活动状态', [validators.InputRequired()], coerce=str,
                                choices=[
                                    (const.ACTIVITY_BEGIN, u'开始'),
                                    (const.ACTIVITY_END, u'结束'),
                                    (const.ACTIVITY_PAUSE, u'暂停')]
                                )
    activity_rule = fields.StringField(u'活动规则')
    activity_banner = fields.StringField(u'活动页banner')
    button_join = fields.StringField(u'我要参加按钮')
    rule_image = fields.StringField(u'游玩大礼图片')
    button_lp = fields.StringField(u'拉票按钮')
    button_tp = fields.StringField(u'投票按钮')
    button_tp_link = fields.StringField(u'投票按钮链接')


class ActivityConfigAdmin(WxModelView):
    Model = ActivityConfig
    form = ActivityConfigForm

    can_view_details = True
    details_modal = True
    column_details_list = ('_id', 'name', 'status', 'activity_id')
    column_list = ('_id', 'name', 'status')
    column_labels = dict(_id=u'活动id', name=u'活动名称', status=u'活动状态')


class ActivityCommentForm(form.Form):
    author = ObjectIdField(u'创建用户', [validators.Required()])
    content = fields.StringField(u'评论内容', [validators.Required()])
    activity = fields.SelectField(u'活动', [validators.InputRequired()], coerce=ObjectId)
    create_at = TimeStampField(u'创建时间', [validators.Optional()])


class ActivityCommentAdmin(WxModelView):
    Model = ActivityComment
    form = ActivityCommentForm

    list_template = 'model_list.html'

    can_create = True
    can_export = True

    column_list = ('author', 'content', 'like', 'activity', 'create_at')
    column_labels = dict(author=u'创建用户', content=u'评论内容', like=u'被赞次数',
                         activity=u'活动名称', create_at=u'创建时间')

    column_formatters = dict(
        author=format_user,
        activity=format_activity,
        create_at=format_timestamp
    )

    column_filters = (
        EqualFilter('_id', u'用户ID', ObjectId),
        SmallerFilter('create_at', u'创建时间', util.str2timestamp),
        GreaterFilter('create_at', u'创建时间', util.str2timestamp),
    )

    def create_form(self, obj=None):
        form = super(ActivityCommentAdmin, self).create_form(obj)
        form.activity.choices = ActivityConfig.activity()
        return form

    def edit_form(self, obj=None):
        form = super(ActivityCommentAdmin, self).edit_form(obj)
        form.activity.choices = ActivityConfig.activity()
        return form

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
                if column == 'author':
                    obj = User.get_one(item[column], check_online=False)
                    item[column] = obj.nickname
                elif column == 'activity':
                    obj = ActivityConfig.get_one(item[column], check_online=False)
                    item[column] = obj.name
                elif column == 'create_at':
                    item[column] = datetime.fromtimestamp(item[column]).strftime('%Y-%m-%d %H:%M:%S')
                elif column not in item:
                    item[column] = None

                row.update({column: unicode(item[column]).encode("utf8")})

            # print row
            rows.writerow(row)

        io.seek(0)
        return io.getvalue()


class ActivityVideoForm(form.Form):
    author = ObjectIdField(u'参赛用户', [validators.Required()])
    video_id = ObjectIdField(u'参赛视频', [validators.Required()])
    vv = fields.IntegerField(u'播放量', [validators.InputRequired()], default=0)
    like_count = fields.IntegerField(u'点赞数', [validators.InputRequired()], default=0)
    comment_count = fields.IntegerField(u'评论数', [validators.InputRequired()], default=0)
    vote = fields.IntegerField(u'投票数', [validators.InputRequired()], default=0)
    activity_id = ObjectIdField(u'参赛活动', [validators.Required()])
    top_author = fields.IntegerField(u'排名', [validators.Optional()])


class ActivityVideoAdmin(WxModelView):
    Model = ActivityVideo
    form = ActivityVideoForm

    list_template = 'model_list.html'

    can_export = True
    can_create = True

    export_columns = ['nickname', 'phone', 'author', 'like_count', 'vv', 'vote', 'comment_count',
                      'create_at', 'video_id', 'activity_id', 'duration', 'top_author']
    column_list = ('author', 'like_count', 'vv', 'comment_count', 'vote', 'create_at', 'video_id',
                   'activity_id', 'top_author')
    column_labels = dict(author=u'视频作者', like_count=u'点赞数', vv=u'播放量', comment_count=u'评论数',
                         vote=u'投票数', create_at=u'参赛时间', video_id=u'视频',
                         activity_id=u'活动', duration=u'视频时长', top_author=u'排名')

    column_sortable_list = ['like_count', 'vv', 'comment_count', 'vote', 'create_at', 'top_author']

    column_formatters = dict(
        create_at=format_timestamp,
        activity_id=format_activity,
        author=format_user,
        video_id=format_video,
    )

    column_filters = (
        SmallerFilter('duration', u'视频时长', int),
        GreaterFilter('duration', u'视频时长', int),
        SmallerFilter('create_at', u'参赛时间', util.str2timestamp),
        GreaterFilter('create_at', u'参赛时间', util.str2timestamp),
        LikeFilter('title', u'视频标题')

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
                if column in ['nickname', 'phone']:
                    obj = User.get_one(item['author'], check_online=False)
                    item['nickname'] = obj.nickname
                    item['phone'] = obj.phone

                elif column == 'activity':
                    obj = ActivityConfig.get_one(item[column], check_online=False)
                    item[column] = obj.name
                elif column == 'create_at':
                    item[column] = datetime.fromtimestamp(item[column]).strftime('%Y-%m-%d %H:%M:%S')
                elif column not in item:
                    item[column] = None

                row.update({column: unicode(item[column]).encode("utf8")})

            rows.writerow(row)

        io.seek(0)
        return io.getvalue()


class VoteVideoForm(form.Form):
    pass


class VoteVideoAdmin(WxModelView):
    Model = VoteVideo
    form = VoteVideoForm

    list_template = 'model_list.html'

    can_export = True
    can_create = True

    export_columns = ['source', 'nickname', 'phone', 'device', 'create_at', 'target', 'author']
    column_list = ('source', 'device', 'author', 'create_at', 'target', 'activity')
    column_labels = dict(author=u'投票者', device=u'设备ID', source=u'投票来源',
                         create_at=u'投票时间', target=u'视频', activity=u'活动名称')

    column_formatters = dict(
        create_at=format_timestamp,
        author=format_user,
        target=format_video,
        activity=format_activity,
    )

    column_filters = (
        SmallerFilter('create_at', u'参赛时间', util.str2timestamp),
        GreaterFilter('create_at', u'参赛时间', util.str2timestamp),
        EqualFilter('target', u'视频ID', ObjectId),
        EqualFilter('source', u'投票来源', str)
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
                if column in ['nickname', 'phone']:
                    obj = User.get_one(item['author'], check_online=False)
                    if obj:
                        item['nickname'] = obj.nickname
                        item['phone'] = obj.phone
                    else:
                        item[column] = None
                elif column == 'create_at':
                    item[column] = datetime.fromtimestamp(item[column]).strftime('%Y-%m-%d %H:%M:%S')
                elif column == 'activity':
                    obj = ActivityConfig.get_one(item[column])
                    if obj:
                        item[column] = obj.name
                elif column not in item:
                    item[column] = None

                row.update({column: unicode(item[column]).encode("utf8")})

            rows.writerow(row)

        io.seek(0)
        return io.getvalue()


class VideoTopicForm(form.Form):
    name = fields.StringField(u'专题名称', [validators.InputRequired(), validators.length(max=15)])
    image = fields.StringField(u'专题背景图', [validators.Required()])
    description = fields.StringField(u'描述文字', [validators.Required(), validators.length(max=100)])
    share_title = fields.StringField(u'分享标题')
    share_desc = fields.StringField(u'分享摘要')
    count = fields.IntegerField(u'视频数量')
    order = fields.IntegerField(u'专题显示顺序', [validators.InputRequired()])


class VideoTopicAdmin(WxModelView):
    Model = VideoTopic
    form = VideoTopicForm
    can_view_details = True
    details_modal = True
    column_details_list = ('name', 'image', 'description', 'share_title',
                           'share_desc', 'count', 'order')
    column_list = ('name', 'image', 'count')
    column_labels = dict(name=u'专题名称', image=u'专题背景图片', count=u'视频数量')
    column_formatters = dict(image=format_image)
    column_filters = (
        EqualFilter('name', u'专题名称', str),
    )

    def create_form(self, obj=None):
        form = super(VideoTopicAdmin, self).create_form(obj)
        del form.count
        return form

    def edit_form(self, obj=None):
        form = super(VideoTopicAdmin, self).edit_form(obj)
        del form.count
        return form

    def _get_topic_video_count(self, tid):
        return TopicVideo.topic_video_count(tid)

    def get_list(self, page, sort_column, sort_desc, search, filters,
                 execute=True, page_size=None):
        count, data = WxModelView.get_list(self, page, sort_column, sort_desc, search, filters,
                                           execute, page_size)
        for model in data:
            model['count'] = self._get_topic_video_count(model['_id'])
        return count, data

    def get_one(self, id):
        model = WxModelView.get_one(self, id)
        model['count'] = self._get_topic_video_count(model['_id'])
        return model
