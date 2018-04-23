# -*- coding: utf8 -*-
"""下线视频更新用户收藏视频数量
"""
from os.path import dirname, abspath

import argparse
import gearman
import json
import os
import sys


def do_task(worker, job):
    from wanx.base.log import print_log
    from wanx.base.xredis import Redis
    from wanx.models.video import UserFaverVideo
    from wanx.models.user import User
    data = job.data
    # 记录日志
    print_log('modify_video', data)

    data = json.loads(data)
    vid = data['vid']
    # action = data['action']
    # delta_count = 0
    # if action == 'offline':
    #     delta_count = -1
    # elif action == 'online':
    #     delta_count = 1
    # 更新收藏了此视频的用户计数
    uids = UserFaverVideo.favor_video_uids(vid)
    for uid in uids:
        user = User.get_one(uid, check_online=False)
        if user:
            key = UserFaverVideo.FAVER_VIDEO_IDS % ({'uid': uid})
            Redis.delete(key)
            count = UserFaverVideo.faver_video_count(uid)
            user.update_model({'$set': {'favor_count': count}})
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
    gm_worker.set_client_id('modify_video')
    gm_worker.register_task('modify_video', do_task)
    try:
        gm_worker.work()
    except:
        pass

    gm_worker.unregister_task('modify_video')
