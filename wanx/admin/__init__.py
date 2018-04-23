# -*- coding: utf8 -*-
from flask import Flask, request, session
from flask_babelex import Babel
from flask.ext.admin import Admin, AdminIndexView

from wanx.admin.comment import CommentAdmin
from wanx.admin.comment import ReplyAdmin
from wanx.base.xmongo import DB
from wanx.models.home import BugReport
from .base import WxFileAdmin
from .msg import SysMsgAdmin, LetterAdmin, SuggestionAdmin, BugReportAdmin
from .user import UserAdmin, UserTrafficLogAdmin, GroupAdmin, UserGroupAdmin
from .xconfig import ConfigAdmin, VersionConfigAdmin, ProvinceAdmin
from .activity import (GameActivityAdmin, ActivityConfigAdmin, ActivityCommentAdmin,
                       ActivityVideoAdmin, VoteVideoAdmin, VideoTopicAdmin)
from .game import (GameAdmin, CategoryAdmin, CategoryGameAdmin, GameRecommendSubscribeAdmin,
                   WebGameAdmin, OfflineGameAdmin)
from .video import VideoAdmin, GameRecommendVideoAdmin, CategoryVideoAdmin, VideoCategoryAdmin, VideoReport, \
    DisableVideoAdmin
from .home import (BannerAdmin, BannerSdkAdmin, WelcomeAdmin, HomeCategoryAdmin,
                   HomeCategoryConfigAdmin, LaunchAdsAdmin, PopupAdmin, ChannelsAdmin,
                   FixedBannerAdmin)
from .credit import (TaskAdmin, ProductAdmin, GiftAdmin, StoreAdmin, StoreItemAdmin,
                     UserOrderAdmin, UserOrderAddressAdmin, WatchLiveTaskAdmin, WatchLiveTaskItemAdmin)
from wanx.models.task import Task
from wanx.models.product import Product
from wanx.models.gift import Gift
from wanx.models.store import Store, StoreItem, UserOrder, UserOrderAddress

import os


# 通过环境变量来进行配置切换
env = os.environ.get('WXENV')
if env not in ['Local', 'Test', 'Stage', 'Production', 'UnitTest']:
    raise EnvironmentError('The environment variable (WXENV) is invalid ')

app = Flask(__name__)
app.config.from_object("config.%s" % (env))


@app.before_request
def before_request():
    from wanx.base.xmysql import MYDB
    MYDB.connect()


@app.teardown_request
def teardown_request(exception):
    from wanx.base.xmysql import MYDB
    if not MYDB.is_closed():
        MYDB.close()


babel = Babel(app)


@babel.localeselector
def get_locale():
    if request.args.get('lang'):
        session['lang'] = request.args.get('lang')
    return session.get('lang', 'zh_Hans_CN')


index_view = AdminIndexView(name=u'首页', template='home.html')

admin = Admin(app, name=u'玩星基地', index_view=index_view, template_mode='bootstrap3')
admin.add_view(UserAdmin(DB['users'], name=u'用户', category=u'用户管理'))
admin.add_view(GroupAdmin(DB['groups'], name=u'分组', category=u'用户管理'))
admin.add_view(UserGroupAdmin(DB['user_group'], name=u'分组用户', category=u'用户管理'))

admin.add_view(GameAdmin(DB['games'], name=u'游戏', category=u'游戏管理'))
admin.add_view(WebGameAdmin(DB['web_games'], name=u'页游', category=u'游戏管理'))
admin.add_view(CategoryAdmin(DB['category'], name=u'游戏分类', category=u'游戏管理'))
admin.add_view(CategoryGameAdmin(DB['category_game'], name=u'游戏分类配置', category=u'游戏管理'))
admin.add_view(GameRecommendVideoAdmin(DB['game_recommend_video'],
               name=u'游戏推荐视频', category=u'游戏管理'))
admin.add_view(GameRecommendSubscribeAdmin(DB['game_recommend_subscribe'],
                                           name=u'游戏推荐订阅', category=u'游戏管理'))

admin.add_view(VideoAdmin(DB['videos'], name=u'视频', category=u'视频管理'))
admin.add_view(VideoCategoryAdmin(DB['video_category'], name=u'视频分类', category=u'视频管理'))
admin.add_view(CategoryVideoAdmin(DB['category_video'], name=u'视频分类配置', category=u'视频管理'))

admin.add_view(SysMsgAdmin(DB['sys_messages'], name=u'系统消息', category=u'消息管理'))
admin.add_view(VideoReport( name=u'举报消息', category=u'消息管理'))
admin.add_view(LetterAdmin(DB['letters'], name=u'私信发送', category=u'消息管理'))
admin.add_view(SuggestionAdmin(DB['suggestions'], name=u'意见反馈', category=u'消息管理'))
admin.add_view(BugReportAdmin(BugReport, name=u'BUG报告', category=u'消息管理'))

admin.add_view(BannerAdmin(DB['top_banner'], name=u'首页广告', category=u'首页管理'))
admin.add_view(WelcomeAdmin(DB['welcome'], name=u'首页配置', category=u'首页管理'))
admin.add_view(FixedBannerAdmin(DB['fixed_banner'], name=u'固定Banner配置', category=u'首页管理'))
admin.add_view(HomeCategoryAdmin(DB['home_category'], name=u'首页分类',
               category=u'首页管理'))
admin.add_view(HomeCategoryConfigAdmin(DB['home_category_config'], name=u'首页分类配置',
               category=u'首页管理'))
admin.add_view(BannerSdkAdmin(DB['sdk_banner'], name=u'SDK活动', category=u'首页管理'))
admin.add_view(LaunchAdsAdmin(DB['launch_ads'], name=u'开屏页配置', category=u'首页管理'))
admin.add_view(PopupAdmin(DB['popup'], name=u'弹窗配置', category=u'首页管理'))

# admin.add_view(UserTrafficLogAdmin(DB['user_traffic_log'], name=u'推广用户统计', category=u'推广活动'))
admin.add_view(GameActivityAdmin(DB['game_activity'], name=u'活动页游戏配置', category=u'推广活动'))
admin.add_view(ActivityConfigAdmin(DB['activity_config'], name=u'活动配置', category=u'推广活动'))
admin.add_view(VideoTopicAdmin(DB['video_topic'], name=u'视频专题配置', category=u'推广活动'))
admin.add_view(ActivityCommentAdmin(DB['activity_comments'], name=u'活动评论管理', category=u'推广活动'))
admin.add_view(ActivityVideoAdmin(DB['activity_videos'], name=u'参赛视频管理', category=u'推广活动'))
admin.add_view(VoteVideoAdmin(DB['vote_video'], name=u'投票管理', category=u'推广活动'))

admin.add_view(OfflineGameAdmin(DB['games'], endpoint='offline_games', name=u'下线游戏', category=u'统计管理'))
admin.add_view(DisableVideoAdmin(DB['videos'], endpoint='disable_videos', name=u'无效视频', category=u'统计管理'))
admin.add_view(CommentAdmin(DB['comments'], name=u'视频评论', category=u'统计管理'))
admin.add_view(ReplyAdmin(DB['replies'], name=u'评论回复', category=u'统计管理'))

admin.add_view(ProductAdmin(Product, name=u'物品配置', category=u'经济管理'))
admin.add_view(TaskAdmin(Task, name=u'任务配置', category=u'经济管理'))
admin.add_view(GiftAdmin(Gift, name=u'礼物配置', category=u'经济管理'))
admin.add_view(StoreAdmin(Store, name=u'营销商店配置', category=u'经济管理'))
admin.add_view(StoreItemAdmin(StoreItem, name=u'营销商店物品配置', category=u'经济管理'))
admin.add_view(UserOrderAdmin(UserOrder, name=u'用户订单管理', category=u'经济管理'))
admin.add_view(UserOrderAddressAdmin(UserOrderAddress, name=u'用户订单地址管理', category=u'经济管理'))
admin.add_view(WatchLiveTaskAdmin(DB['watch_live_task'], name=u'观看直播时长活动配置', category=u'经济管理'))
admin.add_view(WatchLiveTaskItemAdmin(DB['watch_live_task_item'],
                                      name=u'观看直播时长活动物品配置', category=u'经济管理'))

admin.add_view(ConfigAdmin(DB['configs'], name=u'服务端配置', category=u'参数配置'))
admin.add_view(VersionConfigAdmin(DB['version_config'], name=u'版本管理', category=u'参数配置'))
admin.add_view(ChannelsAdmin(DB['channels'], name=u'渠道配置', category=u'参数配置'))
admin.add_view(ProvinceAdmin(DB['province'], name=u'省份管理', category=u'参数配置'))

_static_url = app.config.get('STATIC_URL')
admin.add_view(WxFileAdmin(app.config.get('STATIC_BASE'), _static_url, name=u'文件上传'))
