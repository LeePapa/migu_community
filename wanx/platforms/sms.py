# -*- coding: utf8 -*-

import base64
import hashlib
import json
import re
import requests
import random
import time
from datetime import datetime

from wanx.base import des, error
from wanx.base.log import print_log
from wanx.base.xredis import Redis


class YunTongXun(object):
    """http://www.yuntongxun.com/
    短信验证格式：
    【咪咕游玩】xxxx（验证码）。10分钟内有效，为了保护您的账户安全，此验证码请勿转发他人。
    """
    # send_url = "https://sandboxapp.cloopen.com:8883"  #  测试地址
    send_url = "https://app.cloopen.com:8883"
    send_uri = "/2013-12-26/Accounts/%s/SMS/TemplateSMS?sig=%s"
    sid = "8a48b551516c09cd01517b18de151bac"
    token = "5a7f5b7698404e019927d64348f5d0c2"
    appid = "8a48b551516c09cd01517b63450e1c8f"

    @classmethod
    def send_code(cls, phone):
        ts = datetime.now().strftime('%Y%m%d%H%M%S')
        sig_str = '%s%s%s' % (cls.sid, cls.token, ts)
        sign = hashlib.md5(sig_str).hexdigest().upper()
        code = random.randint(1000, 9999)
        _send_uri = cls.send_uri % (cls.sid, sign)
        url = '%s%s' % (cls.send_url, _send_uri)
        data = dict(
            to=phone,
            appId=cls.appid,
            templateId='1',
            datas=[code, 10],
        )
        data = json.dumps(data)
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json;charset=utf-8',
            'Content-Length': len(data),
            'Authorization': base64.b64encode('%s:%s' % (cls.sid, ts))
        }
        resp = requests.post(url, data=data, headers=headers)
        if resp.status_code != requests.codes.ok:
            return False
        data = resp.json()
        ret = data['statusCode'] == '000000'
        if ret:
            key = 'sms:code:%s' % (phone)
            Redis.setex(key, 600, code)

        return ret

    @classmethod
    def verify_code(cls, phone, code):
        key = 'sms:code:%s' % (phone)
        valid_code = Redis.get(key)
        return code and valid_code == code


class Sp106(object):
    """http://www.106sp.com/
    """
    send_url = "http://api.106sp.com/verifysms/v1/send.json"
    client_id = '11854326420766044860'
    client_key = '98b81ed314babe7365f8c2df16e20282'

    @classmethod
    def send_code(cls, phone):
        ts = str(int(time.time()))
        sig_str = '%s%s%s' % (cls.client_id, cls.client_key, ts)
        sign = hashlib.md5(sig_str).hexdigest()
        code = random.randint(1000, 9999)
        data = dict(
            client_id=cls.client_id,
            timestamp=ts,
            sign=sign,
            code=code,
            company='咪咕游玩',
            phone=phone
        )
        resp = requests.post(cls.send_url, data=data, verify=False)
        if resp.status_code != requests.codes.ok:
            return False
        data = resp.json()
        ret = int(data['error']) == 0
        if ret:
            key = 'sms:code:%s' % (phone)
            Redis.setex(key, 600, code)

        return ret

    @classmethod
    def verify_code(cls, phone, code):
        key = 'sms:code:%s' % (phone)
        valid_code = Redis.get(key)
        return code and valid_code == code


SMS = Sp106


class MobileSMS(object):
    api_url = 'http://service.gamehall.cmgame.com/SecureProxy4/servlet/queryVerificeCode'
    verify_url = 'http://service.gamehall.cmgame.com/SecureProxy4/servlet/checkverificecode'
    secret = 'DSkfek9890EIFe98OEL00eIf'
    desecret = 'emag@)!)'

    @classmethod
    def send_code(cls, phone):
        des_phone = cls._encrypt(phone.encode('latin-1'), cls.secret)
        des_phone = base64.b64encode(des_phone)
        headers = {'accountName': des_phone, 'accountType': 3}
        resp = requests.get(cls.api_url, headers=headers, timeout=5)
        if resp.status_code != requests.codes.ok:
            return False
        return base64.b64encode(resp.content)

    @classmethod
    def verify_code(cls, phone, code):
        des_phone = cls._encrypt(phone.encode('latin-1'), cls.secret)
        des_phone = base64.b64encode(des_phone)
        headers = {'accountName': des_phone,
                   'accountType': 3, 'verificeCode': code}
        resp = requests.get(cls.verify_url, headers=headers, timeout=5)
        if resp.status_code != requests.codes.ok:
            return False
        content = cls._decrypt(resp.content, cls.desecret)
        pattern = re.compile(r'<status>(\d+)</status>')
        ret = pattern.findall(content)
        return int(ret[0]) == 0 if ret else False

    @classmethod
    def _encrypt(cls, data, key):
        k = des.des(key[:8], des.ECB, "\0\0\0\0\0\0\0\0",
                    pad=None, padmode=des.PAD_PKCS5)
        d = k.encrypt(data)
        return d

    @classmethod
    def _decrypt(cls, data, key):
        k = des.des(key[:8], des.ECB, "\0\0\0\0\0\0\0\0",
                    pad=None, padmode=des.PAD_PKCS5)
        d = k.decrypt(data)
        return d


class SendSmsService(object):
    url = 'http://112.4.3.52:8310/SendSmsService/services/SendSms'
    key = ''

    @classmethod
    def send_sms(cls, phone, content, smsid, log_func=None, log_id=None):
        human_errors = {
            'send_report_warning': '发送举报消息告警失败',
        }
        human_error = human_errors.get(log_func, '未知错误')

        timeStamp = time.strftime('%Y%m%d%H%M%S')
        spId = '990123'
        PASSWORD = '990123'
        OA = '106588997803'
        tel = '86' + phone

        code = spId + PASSWORD + timeStamp

        md5 = hashlib.md5()
        md5.update(code.encode())
        spPassword = md5.hexdigest()

        headers = {'Content-Type': 'text/xml; charset=utf-8'}
        xml = '''
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" \
            xmlns:v2="http://www.huawei.com.cn/schema/common/v2_1" \
            xmlns:loc="http://www.csapi.org/schema/parlayx/sms/send/v2_2/local">
               <soapenv:Header>
                  <v2:RequestSOAPHeader>
                     <v2:spId>{spId}</v2:spId>
                     <v2:spPassword>{spPassword}</v2:spPassword>
                     <v2:serviceId>{spId}</v2:serviceId>
                     <v2:timeStamp>{timeStamp}</v2:timeStamp>
                     <v2:OA>{OA}</v2:OA>
                     <v2:FA>tel:{tel}</v2:FA>
                     <v2:localCarrierID>0</v2:localCarrierID>
                  </v2:RequestSOAPHeader>
               </soapenv:Header>
               <soapenv:Body>
                  <loc:sendSms>
                     <loc:addresses>tel:{tel}</loc:addresses>
                     <loc:senderName>{OA}</loc:senderName>
                     <loc:charging>
                        <description>jifei</description>
                        <currency>RMB</currency>
                        <amount>0</amount>
                        <code>223323</code>
                      </loc:charging>
                     <loc:message>{content}</loc:message>
                     <loc:receiptRequest>
                        <endpoint>http://172.16.4.15:8310/SendSmsService/services/Sen</endpoint>
                        <interfaceName>SmsNotification</interfaceName>
                        <correlator>123</correlator>
                     </loc:receiptRequest>
                  </loc:sendSms>
               </soapenv:Body>
            </soapenv:Envelope>
            '''.format(spId=spId, spPassword=spPassword, timeStamp=timeStamp, OA=OA, tel=tel,
                       content=content)
        try:
            resp = requests.post(cls.url, data=xml, headers=headers, timeout=5)
        except requests.exceptions.Timeout:
            print_log('portalone_sms', '[%s][%s]: connection timeout' % (log_func, log_id))
            return error.MiguError('网络连接超时')
        except:
            print_log('portalone_sms', '[%s][%s]: connection error' % (log_func, log_id))
            return error.MiguError('网络连接失败')

        print_log('portalone_sms', '[%s][%s]: (%s) %s'
                  % (log_func, log_id, resp.status_code, resp.content.decode('utf8')))

        if resp.status_code != requests.codes.ok:
            return error.MiguError('网络请求错误')

        st = re.compile(r'<status>(\d+)</status>')
        ret = st.findall(resp.content)

        if ret and int(ret[0]) != 0:
            errmsg = error.MIGU_ERROR.get(ret[0], human_error)
            return error.MiguError(errmsg)

        return resp.content if ret else error.MiguError(human_error)


    @classmethod
    def send_report_warning(cls, phone, content):
        return cls.send_sms(phone, content, '10000', 'send_report_warning', phone)


