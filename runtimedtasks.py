#!/usr/bin/env python
# -*- coding: utf8 -*-

import os
import sys
import threading
import time


def check_live_red_packets(interval_time):
    ts = time.time()
    try:
        _ids = LiveRedPacket.all_ids()
        lives = Xlive.get_all_lives()
        # print "ts", ts, _ids
        for rp in LiveRedPacket.get_list(_ids):
            data = dict(id=str(rp._id), expire_at=rp.expire_at)
            live_authors = [] if not rp.live_authors else rp.live_authors.split('\r\n')
            live_games = [] if not rp.live_games else rp.live_games.split('\r\n')
            key_words = [] if not rp.keyword else rp.keyword.split(u',')
            # 如果是定时发红包，则到时间即刻触发弹幕通知
            for live in lives:
                # 过滤非定时及主播开播时长任务
                if rp.mode not in [0, 1]:
                    continue

                # 过滤主播
                if live_authors and live['user_id'] not in live_authors:
                    # print "1", live_authors, live['user_id']
                    continue
                # 过滤游戏
                if live_games and live['game_id'] not in live_games:
                    # print "2", live_games, live['game_id']
                    continue
                # 过滤关键字
                if key_words and not any(map(lambda x: x in live['name'], key_words)):
                    # print "3", key_words, live['name']
                    continue
                # 如果是定时任务，只在第一次发送
                if rp.mode == 0 and ts-rp.begin_at > interval_time:
                    # print "5", ts, rp.begin_at, rp.mode, interval_time
                    continue
                # 如果是主播开播时长任务，在主播时长达到时发送一次
                count_at = max(live['create_at'], rp.begin_at)
                if rp.mode == 1 and not 0 <= ts-count_at-rp.delay*60 <= interval_time:
                    # print "6", ts, count_at, rp.mode, rp.delay, interval_time
                    continue

                data.update({'event_id': str(live['event_id'])})
                # print "Xlive.send_live_msg", data, 'red_packet', ts
                record = '[%s] event_id=%s, active_id=%s' % ('Red Packet', live['event_id'], data['id'])
                print_log('timed_task', record)
                Xlive.send_live_msg(data, 'red_packet')
    except Exception, e:
        print_log('timed_task', '[%s] %s' % ('Red Packet', str(e)))


if __name__ == "__main__":
    env = sys.argv[1] if len(sys.argv) > 1 else 'Local'
    if env not in ['Local', 'Test', 'Stage', 'Production', 'UnitTest']:
        raise EnvironmentError('The environment variable (WXENV) is invalid ')
    os.environ['WXENV'] = env
    reload(sys)
    sys.setdefaultencoding('utf-8')

    from wanx.models.live import LiveRedPacket
    from wanx.platforms import Xlive
    from wanx.base.log import print_log
    interval_time = 5   #执行间隔时间，单位秒
    while True:
        t = threading.Thread(target=check_live_red_packets, args=(interval_time,))
        t.start()
        time.sleep(interval_time)

