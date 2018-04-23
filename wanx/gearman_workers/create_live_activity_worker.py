# -*- coding: utf8 -*-
"""直播参赛
"""
from bson.objectid import ObjectId
from os.path import dirname, abspath

import argparse
import gearman
import json
import os
import sys


def do_task(worker, job):
    from wanx.base.log import print_log
    from wanx.base import const, util, jpush
    from wanx.models.user import User
    from wanx.models.game import Game
    from wanx.models.live import Live_Activity
    from wanx.models.activity import ActivityConfig
    from wanx.models.game import GameActivity
    from wanx.models.task import BEGIN_LIVE, UserTask
    from wanx.base.xredis import Redis
    from wanx.base.xmysql import MYDB
    from wanx.platforms.xmatch import Xmatch

    data = job.data
    # 记录日志
    print_log('create_live_activity', data)

    data = json.loads(data)
    # 记录日志
    print_log('create_live_activity', '%s ==========================> Start' % (data['event_id']))

    user = User.get_one(data['user_id'], check_online=False)
    if not user:
        return ''
    # 主播上线push推送
    push_content = u"您关注的主播 {0} 正在直播，点击围观".format(user.nickname)
    message_content = u"您关注的主播 {0} 正在直播，速速去围观吧！".format(user.nickname)
    an_link = "playsdk://video_live/{0}/".format(data['event_id'])
    ios_link = "playsdk://live/{0}".format(data['event_id'])
    jpush.jpush_schedule_create(data['event_id'], user, push_content, message_content, an_link, ios_link)

    # 赛事预约直播上线推送
    battle = Xmatch.getbattle(user._id, data['name'])
    if battle:
        battle = battle['data']['battle']
        push_title = u'您预约的比赛正在进行'
        push_content = u"{0}  vs  {1}正在直播，点击围观".format(battle['team_1'], battle['team_2'])
        message_content = u"您预约的比赛{0}  vs  {1}正在直播！".format(
            battle['team_1'], battle['team_2'])
        if battle.get('players', '') != "":
            push_content = message_content = battle['live_name']
        an_link = "playsdk://video_live/{0}/".format(data['event_id'])
        ios_link = "playsdk://live/{0}".format(data['event_id'])
        jpush.jpush_withtitle_create(data['event_id'], battle['_id'], push_title, push_content, message_content, an_link, ios_link)

    game = Game.get_one(data['game_id'], check_online=False)
    if not game:
        return ''

    aid = None
    aids = ActivityConfig.get_by_type(const.FROM_LIVE)
    for a in ActivityConfig.get_list(aids):
        gids = GameActivity.game_activity_ids(a['_id'])
        if gids and data['game_id'] not in gids:
            continue
        aid = a['_id']
        break

    if not aid:
        return ''
    print_log('create_live_activity', '%s ==========================> activity_id' % (aid))
    activity_live = Live_Activity.get_activity_live(str(user._id), aid)
    if not activity_live:
        key = 'lock:activity:live:%s:%s' % (str(user._id), aid)
        with util.Lockit(Redis, key) as locked:
            if locked:
                return ''
        activity_live = Live_Activity.init()
        activity_live.author = ObjectId(data['user_id'])
        activity_live.game = ObjectId(data['game_id'])
        activity_live.event_id = data['event_id']
        activity_live.activity_id = ObjectId(aid)
        activity_live.create_model()
        # 如果没有活动任务则创建
        UserTask.create_and_init_user_tasks(str(user._id))
    if not MYDB.is_closed():
        MYDB.close()
    try:
        UserTask.check_user_tasks(user._id, BEGIN_LIVE, 1, data['game_id'], aid)
    except Exception as e:
        print_log('create_live_activity', '%s ========' % e)
    if not MYDB.is_closed():
        MYDB.close()

    # 记录日志
    print_log('create_live_activity', '%s ==========================> Finished' % (data['event_id']))
    return ''


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-env', action='store', dest='wxenv', required=True,
                        help='Test|Stage|Production')
    args = parser.parse_args(sys.argv[1:])
    wxenv = args.wxenv
    if wxenv not in ['Local', 'Test', 'Stage', 'Production', 'UnitTest']:
        raise EnvironmentError('The environment variable (WXENV) is invalid ')
    os.environ['WXENV'] = wxenv
    sys.path.append(dirname(dirname(dirname(abspath(__file__)))))
    from wanx import app
    servers = app.config.get("GEARMAN_SERVERS")
    gm_worker = gearman.GearmanWorker(servers)
    gm_worker.set_client_id('create_live_activity')
    gm_worker.register_task('create_live_activity', do_task)
    try:
        gm_worker.work()
    except:
        pass

    gm_worker.unregister_task('create_live_activity')
