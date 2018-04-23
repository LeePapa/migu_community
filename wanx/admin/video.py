# -*- coding: utf8 -*-
from bson.objectid import ObjectId
from wtforms import form, fields, validators

from wanx.models.msg import SysMessage
from .base import WxModelView
from .util import (ObjectIdField, TimeStampField, format_game, format_user, format_video,
                   format_video_url, format_image, format_status, format_timestamp,
                   format_video_category, format_choices)
from .filter import EqualFilter, LikeFilter, SmallerFilter, GreaterFilter, GreaterTimeFileter, SmallerTimeFileter, \
    GameFileter, UserFileter
from wanx.base import const, util
from wanx.models.video import (Video, GameRecommendVideo, VideoCategory, CategoryVideo,
                               ReportVideo, VideoTopic, TopicVideo)
from wanx.models.game import Game
from wanx.models.user import User
from flask.ext.admin import BaseView, expose
from flask import request, redirect, jsonify
import datetime, time


class VideoForm(form.Form):
    author = ObjectIdField(u'创建用户', [validators.Required()])
    url = fields.StringField(u'链接', [validators.Required()])
    title = fields.StringField(u'标题', [validators.Required()])
    cover = fields.StringField(u'背景图', [validators.Required()])
    game = ObjectIdField(u'所属游戏', [validators.Required()])
    ratio = fields.StringField(u'分辨率(宽x高)', [validators.Required()])
    duration = fields.IntegerField(u'视频时长(秒)', [validators.InputRequired()])
    vv = fields.IntegerField(u'播放次数', [validators.InputRequired()], default=0)
    release_time = TimeStampField(u'发布精华时间', [validators.Optional()])
    status = fields.SelectField(u'状态', [validators.InputRequired()], coerce=int,
                                choices=[
                                    (const.ONLINE, u'在线'),
                                    (const.OFFLINE, u'下线'),
                                    (const.ELITE, u'精选'),
                                    (const.UPLOADING, u'上传中')],
                                default=const.ONLINE
                                )
    categories = fields.SelectMultipleField(u'分类', [validators.Optional()],
                                            coerce=ObjectId)
    topics = fields.SelectMultipleField(u'专题', [validators.Optional()],
                                            coerce=ObjectId)


class VideoAdmin(WxModelView):
    Model = Video
    form = VideoForm
    can_view_details = True
    details_modal = True
    column_details_list = ('author', 'url', 'game', 'vv', 'status', 'release_time', 'create_at')
    column_list = ('author', 'url', 'game', 'vv', 'status', 'release_time', 'create_at')
    column_sortable_list = ['release_time']
    column_labels = dict(author=u'创建用户', url=u'链接', game=u'所属游戏', vv=u'播放数',
                         status=u'状态', release_time=u'发布精华', create_at=u'创建时间')
    column_formatters = dict(
        url=format_video_url,
        cover=format_image,
        status=format_status,
        release_time=format_timestamp,
        create_at=format_timestamp,
        game=format_game,
        author=format_user
    )
    column_filters = (
        EqualFilter('_id', u'视频ID', ObjectId),
        EqualFilter('status', u'状态', int, [
            (const.ONLINE, u'在线'),
            (const.OFFLINE, u'下线'),
            (const.ELITE, u'精选'),
            (const.UPLOADING, u'上传中')]
        ),
        EqualFilter('game', u'游戏ID', ObjectId),
        EqualFilter('author', u'用户ID', ObjectId),
        LikeFilter('title', u'标题'),
        SmallerFilter('create_at', u'创建时间', util.str2timestamp),
        GreaterFilter('create_at', u'创建时间', util.str2timestamp)
    )

    def process_form_data(self, data):
        data.pop('categories')
        data.pop('topics')
        return data

    def create_model(self, form):
        new_cate_ids = form.categories.data
        new_topic_ids = form.topics.data
        model = super(VideoAdmin, self).create_model(form)
        video = self.get_pk_value(model)
        for cate_id in new_cate_ids:
            cv = CategoryVideo.init()
            cv.game = form.game.data
            cv.category = cate_id
            cv.video = video
            cv.create_model()

        for topic_id in new_topic_ids:
            tv = TopicVideo.init()
            tv.topic = topic_id
            tv.video = video
            tv.create_model()

        return model

    def update_model(self, form, model):
        new_cate_ids = form.categories.data
        new_topic_ids = form.topics.data
        ret = super(VideoAdmin, self).update_model(form, model)
        if ret:
            video = self.get_pk_value(model)
            old_cate_ids = CategoryVideo.video_category_ids(str(video))
            need_delete_ids = [cid for cid in old_cate_ids if cid not in new_cate_ids]
            need_create_ids = [cid for cid in new_cate_ids if cid not in old_cate_ids]
            for cate_id in need_create_ids:
                cv = CategoryVideo.init()
                cv.game = form.game.data
                cv.category = cate_id
                cv.video = video
                cv.create_model()

            for cate_id in need_delete_ids:
                cv = CategoryVideo.get_by_ship(str(video), str(cate_id))
                cv.delete_model() if cv else None

            old_topic_ids = TopicVideo.video_topic_ids(str(video))
            need_delete_ids = list(set(old_topic_ids).difference(new_topic_ids))
            need_create_ids = list(set(new_topic_ids).difference(old_topic_ids))
            for topic_id in need_create_ids:
                tv = TopicVideo.init()
                tv.topic = topic_id
                tv.video = video
                tv.create_model()

            for topic_id in need_delete_ids:
                tv = TopicVideo.get_by_ship(str(video), str(topic_id))
                tv.delete_model() if tv else None

        return ret

    def create_form(self, obj=None):
        form = super(VideoAdmin, self).create_form(obj)
        cids = VideoCategory.all_category_ids()
        categories = VideoCategory.get_list(cids)
        form.categories.choices = [(c._id, c.name) for c in categories]
        tids = VideoTopic.all_topic_ids()
        topics = VideoTopic.get_list(tids)
        form.topics.choices = [(c._id, c.name) for c in topics]
        return form

    def edit_form(self, obj=None):
        obj['categories'] = CategoryVideo.video_category_ids(obj['_id'])
        obj['topics'] = TopicVideo.video_topic_ids(obj['_id'])
        form = super(VideoAdmin, self).edit_form(obj)
        cids = VideoCategory.all_category_ids()
        categories = VideoCategory.get_list(cids)
        form.categories.choices = [(c._id, c.name) for c in categories]
        tids = VideoTopic.all_topic_ids()
        topics = VideoTopic.get_list(tids)
        form.topics.choices = [(c._id, c.name) for c in topics]
        return form


class GameRecommendVideoForm(form.Form):
    game = fields.SelectField(u'游戏', [validators.InputRequired()], coerce=ObjectId)
    video = ObjectIdField(u'视频', [validators.Required()])
    order = fields.IntegerField(u'显示顺序', [validators.InputRequired()], default=0)


class GameRecommendVideoAdmin(WxModelView):
    Model = GameRecommendVideo
    form = GameRecommendVideoForm
    column_list = ('game', 'video', 'order')
    column_labels = dict(game=u'游戏', video=u'视频', order=u'显示顺序')
    column_sortable_list = ('game',)
    column_formatters = dict(
        game=format_game,
        video=format_video
    )
    column_filters = (
        EqualFilter('game', u'游戏', ObjectId),
    )

    def create_form(self, obj=None):
        form = super(GameRecommendVideoAdmin, self).create_form(obj)
        form.game.choices = Game.online_games()
        return form

    def edit_form(self, obj=None):
        form = super(GameRecommendVideoAdmin, self).edit_form(obj)
        form.game.choices = Game.online_games()
        return form


class VideoCategoryForm(form.Form):
    name = fields.StringField(u'分类名', [validators.Required()])
    order = fields.IntegerField(u'显示顺序', [validators.InputRequired()], default=0)


class VideoCategoryAdmin(WxModelView):
    Model = VideoCategory
    form = VideoCategoryForm
    column_list = ('_id', 'name', 'order')
    column_labels = dict(_id=u'分类ID', name=u'分类名', order=u'显示顺序')
    column_filters = (
        EqualFilter('_id', u'分类ID', ObjectId),
    )


class CategoryVideoForm(form.Form):
    category = fields.SelectField(u'分类ID', [validators.InputRequired()], coerce=ObjectId)
    video = ObjectIdField(u'视频ID', [validators.Required()])


class CategoryVideoAdmin(WxModelView):
    Model = CategoryVideo
    form = CategoryVideoForm
    column_list = ('category', 'video', 'game')
    column_labels = dict(game=u'游戏', category=u'分类', video=u'视频')
    column_formatters = dict(
        game=format_game,
        category=format_video_category,
        video=format_video
    )
    column_filters = (
        EqualFilter('game', u'游戏ID', ObjectId),
        EqualFilter('category', u'分类ID', ObjectId),
        EqualFilter('video', u'视频ID', ObjectId)
    )

    def create_form(self, obj=None):
        form = super(CategoryVideoAdmin, self).create_form(obj)
        cids = VideoCategory.all_category_ids()
        categories = VideoCategory.get_list(cids)
        form.category.choices = [(c._id, c.name) for c in categories]
        return form

    def edit_form(self, obj=None):
        form = super(CategoryVideoAdmin, self).edit_form(obj)
        cids = VideoCategory.all_category_ids()
        categories = VideoCategory.get_list(cids)
        form.category.choices = [(c._id, c.name) for c in categories]
        return form

    def process_form_data(self, data):
        video = Video.get_one(str(data['video']))
        data['game'] = video.game if video else None
        return data


class VideoReport(BaseView):
    @expose('/')
    def index(self):
        values = request.values
        page = int(values.get("page", 1))
        nbr = max(int(values.get("nbr", 10)), 1)
        vid = values.get("vid", "")
        if vid:
            vids = [vid]
        else:
            vids, total = ReportVideo.get_reported_videos(page, nbr)
        lastpage = vids.__len__() != nbr
        reports = ReportVideo.get_list_by_vids(vids)
        total_page = total/nbr + int(bool(total % nbr))
        rtypes = [u"", u"广告", u"色情低俗", u"政治敏感", u"人身攻击", u"盗用作品", u"其他"]
        return self.render('reported_videos.html',
                           reports=reports,
                           rtypes=rtypes,
                           page=page,
                           nbr=nbr,
                           lastpage=lastpage,
                           filter_vid=vid,
                           total_page=total_page,
                           url=request.url)

    @expose('/info/')
    def info(self):
        values = request.values
        rid = values.get("report_id", None)
        report = ReportVideo.get_one(rid)
        if report is None:
            return jsonify({"status": -1, "errmsg": "找不到记录。"})
        return jsonify({"status": 0, "errmsg": "成功", "data": report.format()})

    @expose('/details/')
    def details(self):
        values = request.values
        vid = values.get("video_id", None)
        page = int(values.get("page", 1))
        nbr = max(int(values.get("nbr", 10)),1)
        reports, total = ReportVideo.get_reports_by_vid(vid, page, nbr)
        total_page = total/nbr + int(bool(total % nbr))
        result = {"reports": reports, "total_page": total_page}
        return jsonify(result)

    @expose('/delete/', methods=["POST"])
    def delete_msg(self):
        result = {"status": 0, "errmsg": "成功"}
        values = request.values
        _ids = values.getlist("ids[]", None)
        mode = values.get("mode", None)
        if _ids is None or not isinstance(_ids, list) or mode not in ["video","report"]:
            return jsonify({"status": -10001, "errmsg": "参数错误"})

        if mode == "video":
            ReportVideo.delete_reports_by_vids(_ids)
        else:
            ReportVideo.delete_reports(_ids)
        return jsonify(result)

    @expose('/ban/', methods=["POST"])
    def ban_user(self):
        result = {"status": 0, "errmsg": "成功"}
        values = request.values
        user_id = values.get("user_id", None)
        day_choice = values.get("day_choice", None)
        ban_days = values.get("ban_days", None)
        limits = values.getlist("limits[]", None)
        reason = values.get("reason", None)
        if filter(lambda x: x is None, [user_id, day_choice, ban_days, limits, reason]):
            return jsonify({"status": -10001, "errmsg": "参数错误"})

        try:
            day_choice = int(day_choice)
            ban_days = int(ban_days)
            limits = sorted([int(i) for i in limits])
        except:
            return jsonify({"status": -10001, "errmsg": "参数错误1"})

        now = datetime.datetime.now()
        days = (7, 15, 182, 36524, ban_days)
        lift_day = now + datetime.timedelta(days=days[day_choice])
        lift_at = time.mktime(lift_day.timetuple())

        user = User.get_one(user_id)
        create_mode = user['status'] == 0

        User.user_bans(user_id, lift_at, limits, reason)

        # 给被封禁用户发送私信
        if create_mode:
            mode = u"因违反社区规则您的帐号已被封禁"
        else:
            mode = u"您的帐号封禁状态被修改"
        limits_txts = (u"禁止开直播", u"禁止上传视频", u"禁止发评论/弹幕",
                       u"禁止私信", u"禁止登录")
        limits_str = u"、".join([limits_txts[i] for i in limits])
        msg = u"{5}，封禁原因为：{0}，解封日期为{1}年{2}月{3}日，在此期间您将被限制{4}。"
        content = msg.format(reason, lift_day.year, lift_day.month, lift_day.day, limits_str, mode)
        sysmsg = SysMessage.init()
        sysmsg.title = u"用户封禁通知"
        sysmsg.owner = ObjectId(user_id)
        sysmsg.content = content
        _id = sysmsg.create_model()
        return jsonify(result)


class DisableVideoForm(form.Form):
    status = fields.SelectField(u'状态', [validators.InputRequired()], coerce=int,
                                choices=[
                                    (const.ONLINE, u'在线'),
                                    (const.OFFLINE, u'下线'),
                                    (const.ELITE, u'精选'),
                                    (const.UPLOADING, u'上传中')],
                                default=const.ONLINE
                                )


class DisableVideoAdmin(WxModelView):
    Model = Video
    form = DisableVideoForm
    _can_create = False
    column_details_list = ('author', 'url', 'game',
                           'vv', 'status', 'release_time')
    column_list = ('author', 'url', 'game', 'vv', 'status', 'release_time')
    column_sortable_list = ['release_time']
    column_labels = dict(author=u'创建用户', url=u'链接', game=u'所属游戏', vv=u'播放数',
                         status=u'状态', release_time=u'发布精华')
    column_formatters = dict(
        url=format_video_url,
        cover=format_image,
        status=format_choices,
        release_time=format_timestamp,
        game=format_game,
        author=format_user,

    )
    column_filters = (
        SmallerFilter('duration', u'大于视频时长', int),
        GreaterFilter('duration', u'小于视频时长', int),
        EqualFilter('_id', u'视频ID', ObjectId),
        EqualFilter('game', u'游戏ID', ObjectId),
        EqualFilter('author', u'用户ID', ObjectId),
        GreaterTimeFileter('create_at', u'开始时间', '', 'datetimepicker'),
        SmallerTimeFileter('create_at', u'结束时间', '', 'datetimepicker'),
        LikeFilter('title', u'标题'),
        EqualFilter('status', u'状态', int, [
            (None, ''),
            (const.ONLINE, u'在线'),
            (const.OFFLINE, u'下线'),
            (const.ELITE, u'精选'),
            (const.UPLOADING, u'上传中')]
                    ),
        GameFileter('game', u'游戏名称'),
        UserFileter('author', u'用户名称'),

        EqualFilter('editor', u'采编状态', int, [
            (None, ''),
            (1, u'是'),
            (0, u'否')]
                    )
    )

    def get_list(self, *args, **kwargs):
        count, data = super(DisableVideoAdmin,
                            self).get_list(*args, **kwargs)
        data_ = list()
        # print 'data', data
        for item in data:
            if 'status' in item.keys():
                if item['status'] == const.UPLOADING:
                    data_.append(item)
        return count, data_

