# -*- coding: utf8 -*-
"""直播视频转为录播视频
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
    from wanx.base import const
    from wanx.models.video import Video
    from wanx.models.user import User
    from wanx.models.game import Game
    data = job.data
    # 记录日志
    print_log('create_live_video', data)

    data = json.loads(data)
    # 记录日志
    print_log('create_live_video', '%s ==========================> Start' % (data['event_id']))

    user = User.get_one(data['user_id'], check_online=False)
    if not user:
        return ''

    game = Game.get_one(data['game_id'], check_online=False)
    if not game:
        return ''

    video_id = Video.get_video_by_event_id(data['event_id'], str(user._id))
    video = Video.get_one(str(video_id), check_online=False)

    if not video:
        video = Video.init()
        video.author = ObjectId(data['user_id'])
        video.game = ObjectId(data['game_id'])
        video.title = data['title']
        video.duration = data['duration']
        video.ratio = data['ratio']
        video.cover = data['cover']
        video.url = data['url']
        video.event_id = data['event_id']
        video.status = const.ONLINE
        video.create_model()
    else:
        data['author'] = ObjectId(data.pop('user_id'))
        data['game'] = ObjectId(data.pop('game_id'))
        video.update_model({'$set': data})

    # 记录日志
    print_log('create_live_video', '%s ==========================> Finished' % (data['event_id']))

    from wanx.models.activity import Battle
    battle = Battle.get_live_battle(data['user_id'],
                                    data['title'].decode('unicode-escape').encode('utf-8'), None)
    if battle:
        Battle.set_video_id(battle['_id'], video_id)

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
    gm_worker.set_client_id('create_live_video')
    gm_worker.register_task('create_live_video', do_task)
    try:
        gm_worker.work()
    except:
        pass

    gm_worker.unregister_task('create_live_video')
