# -*- coding: utf8 -*-
from bson import ObjectId
from wtforms import form
from .base import WxModelView
from .util import format_timestamp, format_model, format_video, format_user
from .filter import GreaterTimeFileter, SmallerTimeFileter, EqualFilter
from wanx.models.comment import Comment, Reply
from wanx.models.user import User
from wanx.models.video import Video


class CommentsForm(form.Form):
    pass


class CommentAdmin(WxModelView):

    form = CommentsForm
    can_edit = False
    can_create = False
    can_view_details = True
    Model = Comment
    details_template = 'details_comment.html'

    column_details_list = ('_id', 'content', 'author', 'video', 'create_at')
    column_list = ('_id', 'video', 'author',
                   'content', 'create_at', 'reply', 'like')
    column_sortable_list = ['create_at']
    column_labels = dict(author=u'评论作者', _id=u'ID', video=u'视频', content=u'评论内容',
                         create_at=u'评论时间', reply=u'被回复次数', like=u'被点赞次数')
    column_formatters = dict(
        create_at=format_timestamp,
        video=format_video,
        author=format_user,
    )
    column_filters = (
        GreaterTimeFileter('create_at', u'开始时间', '', 'datetimepicker'),
        SmallerTimeFileter('create_at', u'结束时间', '', 'datetimepicker'),
        EqualFilter('author', u'评论作者ID', ObjectId),
        EqualFilter('video', u'视频ID', ObjectId),
        EqualFilter('_id', u'视频评论ID', ObjectId),
    )

    column_groupby = (
        ('author', u'评论作者ID', 'flt1_2'),
        ('video', u'视频ID', 'flt1_3'),
    )


class ReplyForm(form.Form):
    pass


class ReplyAdmin(WxModelView):

    form = ReplyForm
    can_edit = False
    can_create = False
    can_view_details = True
    details_template = 'details_reply.html'
    Model = Reply

    column_details_list = ('_id', 'content', 'owner', 'reply', 'create_at')
    column_list = ('_id', 'owner', 'reply',
                   'content', 'create_at', 'reply_count')
    column_sortable_list = ['create_at']
    column_labels = dict(owner=u'回复者', _id=u'回复唯一标识', reply=u'被回复信息唯一标识', content=u'回复内容',
                         create_at=u'评论时间', reply_count=u'被回复次数')
    column_formatters = dict(
        create_at=format_timestamp,
        owner=format_user,
    )
    column_filters = (
        GreaterTimeFileter('create_at', u'开始时间', '', 'datetimepicker'),
        SmallerTimeFileter('create_at', u'结束时间', '', 'datetimepicker'),
        EqualFilter('owner', u'回复者ID', ObjectId),
        EqualFilter('_id', u'评论回复ID', ObjectId),
    )

    column_groupby = (
        ('owner', u'回复者ID', 'flt1_2'),
    )
