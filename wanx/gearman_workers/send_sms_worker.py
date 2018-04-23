# -*- coding: utf8 -*-

"""
短信发送功能
由于移动短信推送平台没有支持短信群发，
因此创建轮询发送任务。
"""

from os.path import dirname, abspath

import argparse
import gearman
import json
import os
import sys


def do_task(worker, job):
    from wanx.base.log import print_log
    from wanx.platforms.sms import SendSmsService
    from wanx.models.user import User, UserGroup
    data = job.data
    # 记录日志
    print_log('send_sms', data)

    data = json.loads(data)
    if 'phones' in data:
        phones = data['phones']
    else:
        uids = UserGroup.group_user_ids(data['group'])
        phones = [user.phone for user in User.get_list(uids, check_online=False)]
    content = data['content']
    for phone in phones:
        if not phone:
            continue
        SendSmsService.send_report_warning(phone, content)

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
    gm_worker.set_client_id('send_sms')
    gm_worker.register_task('send_sms', do_task)
    try:
        gm_worker.work()
    except:
        pass

    gm_worker.unregister_task('send_sms')
