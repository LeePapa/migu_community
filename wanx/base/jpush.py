# -*- coding: utf8 -*-
import base64
import requests
import json
import uuid
import hashlib
import os
from wanx import app
from Crypto.Cipher import AES


def translate_md5(string):
    m = hashlib.md5()
    m.update(string)
    return m.hexdigest().lower()

BS = AES.block_size
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s: s[0:-ord(s[-1])]


def jpush_schedule_auth(app_key, master_secret):
    base_url = "https://api.jpush.cn/"
    schedule_url = base_url + 'v3/push'
    session = requests.Session()
    session.auth = (app_key, master_secret)
    headers = {}
    headers['user-agent'] = 'jpush-api-python-client'
    headers['connection'] = 'keep-alive'
    headers['content-type'] = 'application/json;charset:utf-8'
    headers['Authorization'] = base64.encodestring(app_key + ":" + master_secret)
    session = requests.Session()
    session.auth = (app_key, master_secret)
    return session, headers, schedule_url

def get_post_str(link):
    key = app.config.get("JPUSH_AES_KEY")
    mode = AES.MODE_CBC
    encryptor = AES.new(key, mode, IV=b"17d91d02fd04a5da")
    app_post_value = {}
    app_post_value['link'] = link
    app_post_value["my_message_id"] = str(uuid.uuid1())
    ciphertext = encryptor.encrypt(pad(json.dumps(app_post_value)))
    app_post_str = base64.encodestring(ciphertext)
    return app_post_str

def jpush_schedule_create(event_id, user, push_content, message_content, an_link, ios_link):
    from wanx.base.log import print_log
    push_title = u"{0} 正在直播！".format(user.nickname)
    # 主播上线推送
    an_post_str = get_post_str(an_link)
    ios_post_str = get_post_str(ios_link)

    push_data = {"audience": {'tag': []}}
    push_data['platform'] = "all"
    push_tag = [translate_md5(str(user.phone)+'push')]
    push_data['audience']['tag'] = push_tag
    push_data['notification'] = {}
    push_data['notification']['alert'] = push_content
    push_data['notification']['android'] = {"extras": {"key": an_post_str,
                                                       "title": push_title,
                                                       "content": push_content,
                                                       "event_id": event_id}}
    push_data['notification']['ios'] = {'extras': {"key": ios_post_str,
                                                   "title": push_title,
                                                   "content": push_content,
                                                   "event_id": event_id}}
    push_data['options'] = {"apns_production": not app.config.get("TESTING")}
    def postdata(app_key=app.config.get("JPUSH_APP_KEY"), master_secret=app.config.get("JPUSH_MASTER_SECRET")):
        session, headers, schedule_url = jpush_schedule_auth(app_key, master_secret)
        r = session.request("POST", schedule_url, data=json.dumps(push_data), params=None,
                            headers=headers, timeout=30)
        print_log('jpush_create_response_log', r.text)

        message_tag = [translate_md5(str(user.phone)+'message')]
        push_data['audience']['tag'] = message_tag
        del push_data['notification']
        push_data['message'] = {"content_type": "text", "title": "msg"}
        push_data['message']['msg_content'] = message_content
        push_data['message']['extras'] = {"an_url": an_post_str,
                                          "ios_url": ios_post_str,
                                          "nickname": user.nickname,
                                          "title": push_title,
                                          "content": push_content,
                                          "event_id": event_id,
                                          "key": an_post_str}
        r = session.request("POST", schedule_url, data=json.dumps(push_data), params=None,
                            headers=headers, timeout=30)
        print_log('jpush_create_response_log', r.text)
    postdata()

    # yxpush
    postdata(app_key=app.config.get("JPUSH_YX_APP_KEY"), master_secret=app.config.get("JPUSH_YX_MASTER_SECRET"))


def jpush_withtitle_create(event_id, id, push_title, push_content, message_content, an_link, ios_link):
    from wanx.base.log import print_log
    an_post_str = get_post_str(an_link)
    ios_post_str = get_post_str(ios_link)

    push_data = {"audience": {'tag': []}}
    push_data['platform'] = "all"
    push_tag = [translate_md5(str(id)+'push')]
    push_data['audience']['tag'] = push_tag
    push_data['notification'] = {}
    push_data['notification']['alert'] = push_content
    push_data['notification']['title'] = push_title
    push_data['notification']['android'] = {"extras": {"key": an_post_str,
                                                       "title": push_title,
                                                       "content": push_content,
                                                       "event_id": event_id}}
    push_data['notification']['ios'] = {'extras': {"key": ios_post_str,
                                                   "title": push_title,
                                                   "content": push_content,
                                                   "event_id": event_id}}
    push_data['options'] = {"apns_production": not app.config.get("TESTING")}
    def postdata(app_key=app.config.get("JPUSH_APP_KEY"), master_secret=app.config.get("JPUSH_MASTER_SECRET")):
        session, headers, schedule_url = jpush_schedule_auth(app_key, master_secret)
        r = session.request("POST", schedule_url, data=json.dumps(push_data), params=None,
                            headers=headers, timeout=30)
        print_log('jpush_create_response_log', r.text)

        message_tag = [translate_md5(str(id)+'message')]
        push_data['audience']['tag'] = message_tag
        del push_data['notification']
        push_data['message'] = {"content_type": "text", "title": "msg"}
        push_data['message']['msg_content'] = message_content
        push_data['message']['extras'] = {"an_url": an_post_str,
                                          "ios_url": ios_post_str,
                                          "title": push_title,
                                          "content": push_content,
                                          "event_id": event_id}
        r = session.request("POST", schedule_url, data=json.dumps(push_data), params=None,
                            headers=headers, timeout=30)
        print_log('jpush_create_response_log', r.text)
    postdata()

    # yxpush
    postdata(app_key=app.config.get("JPUSH_YX_APP_KEY"), master_secret=app.config.get("JPUSH_YX_MASTER_SECRET"))

if __name__ == '__main__':
    # 测试用
    import sys
    from os.path import dirname, abspath
    os.environ['WXENV'] = 'Test'
    sys.path.append(dirname(dirname(dirname(abspath(__file__)))))
    from wanx.models.user import User
    phone = sys.argv[1] if len(sys.argv) > 1 else ''
    user = User.get_by_phone(phone)
    jpush_schedule_create(user, '我来测试，这是push', '我来测试，这是message', 'http://www.baidu.com', 'http://www.bing.com')