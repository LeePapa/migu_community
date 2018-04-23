# -*- coding: utf8 -*-
import base64

from flask import request
from urlparse import urljoin
from suds.client import Client
from wanx.base.log import print_log
from wanx.base import error
import datetime

import hashlib
import json
import re
import requests
import os
import time
from Crypto.Cipher import AES
import random

from wanx.base.util import Xml2Json

class Migu(object):
    # 幻方接口 暂时保留
    # register_url = 'http://g.10086.cn/egservice/externalAuth/registerAccount.do'
    # login_url = 'http://g.10086.cn/egservice/externalAuth/authenticate.do'
    # update_pwd_url = 'http://g.10086.cn/egservice/externalServer/updatePassword.do'
    # reset_pwd_url = 'http://g.10086.cn/egservice/externalServer/resetPassword.do'
    # check_url = 'http://g.10086.cn/egservice/externalServer/checkAccountExist.do'
    download_url = 'http://112.4.3.36:18080/portalone/services/PortalService?wsdl'
    down_channel = '42102002'
    channel = '40257731896'
    recommendID = '123456789'
    # 用户中心改造
    # 用户注册、登陆验证调用 portalone_url
    # 验证账号唯一性、修改密码、重置密码调用 iduser_url
    # 注册、登陆时候 source=13表示咪咕游玩
    if os.environ.get('WXENV') in ['Production', 'Stage']:
        portalone_url = 'http://112.4.3.36:18080/portalone/upbus'
        platform_url = 'https://passport.migu.cn:8443/api/tokenValidate'
        iduser_url = 'http://112.4.3.25:18011/idm/IUser'
    else:
        # test_url
        portalone_url = 'http://112.4.3.136:8080/portalone/upbus'
        platform_url = 'https://passport.migu.cn:8443/api/tokenValidate'
        iduser_url = 'http://112.4.3.136:18011/idm/IUser'

    @classmethod
    def _post_request(cls, url, data, headers=None, timeout=5, log_func=None, log_id=None):
        human_errors = {
            'center_register': '注册失败',
            'get_identityid': '获取信息失败',
            'center_update_pwd': '更新密码失败',
            'center_reset_pwd': '重置密码失败',
            'center_check_account': '手机号验证失败',
            'center_sms_code': '获取短信验证码失败',
            'center_service_up': '升级账号失败',
            'get_user_info_by_account_name': '获取用户信息失败',
            'token_validate': '验证token失败',
        }
        human_error = human_errors.get(log_func, '未知错误')
        headers = headers or {'content-type': 'text/xml', 'charset': 'UTF-8',
                              'Authorization': "Basic sourceid='{0}', apptype='{1}', userip='{2}'".format(
                                  request.values.get('sourceid', '206014'),
                                  request.values.get('apptype', '3'),
                                  request.access_route[0])}
        try:
            resp = requests.post(url, data=data, headers=headers, timeout=5)
        except requests.exceptions.Timeout:
            print_log('migu_center', '[%s][%s]: connection timeout' % (log_func, log_id))
            return error.MiguError('网络连接超时')
        except:
            print_log('migu_center', '[%s][%s]: connection error' % (log_func, log_id))
            return error.MiguError('网络连接失败')

        print_log('migu_center', '[%s][%s]: (%s) %s'
                  % (log_func, log_id, resp.status_code, resp.content.decode('utf8')))

        if resp.status_code != requests.codes.ok:
            return error.MiguError('网络请求错误')

        st = re.compile(r'<resultCode>(\d+)</resultCode>')
        ret = st.findall(resp.content)

        if ret and int(ret[0]) != 0:
            errmsg = error.MIGU_ERROR.get(ret[0], human_error)
            return error.MiguError(errmsg)

        return resp.content if ret else error.MiguError(human_error)

    @classmethod
    def _post_request_json(cls, url, data, headers=None, timeout=5, log_func=None, log_id=None):
        human_errors = {
            'center_register': '注册失败',
            'get_identityid': '获取信息失败',
            'get_identity_token': '验证token失败',
            'center_update_pwd': '更新密码失败',
            'center_reset_pwd': '重置密码失败',
            'center_check_account': '手机号验证失败',
            'center_sms_code': '获取短信验证码失败',
            'center_service_up': '升级账号失败',
            'get_user_info_by_account_name': '获取用户信息失败'
        }
        human_error = human_errors.get(log_func, '未知错误')
        headers = headers or {'content-type': 'text/json', 'charset': 'UTF-8'}
        data = json.dumps(data)
        try:
            resp = requests.post(url, data=data, headers=headers, timeout=5, cert=(
                '/etc/pki/tls/certs/youxi.crt', '/etc/pki/tls/certs/youxi.key'), verify=False)
        except requests.exceptions.Timeout:
            print_log('migu_center', '[%s][%s]: connection timeout' % (log_func, log_id))
            return error.MiguError('网络连接超时')
        except:
            print_log('migu_center', '[%s][%s]: connection error' % (log_func, log_id))
            return error.MiguError('网络连接失败')

        print_log('migu_center', '[%s][%s]: (%s) %s'
                  % (log_func, log_id, resp.status_code, resp.content.decode('utf8')))

        if resp.status_code != requests.codes.ok:
            return error.MiguError('网络请求错误')

        resultcode = None
        if resp:
            resultcode = resp.json().get('header').get('resultcode', None)
        if resultcode and int(resultcode) != 103000:
            errmsg = error.MIGU_ERROR_2.get(str(resultcode), human_error)
            return error.MiguError(errmsg)

        return resp.json() if resultcode else error.MiguError(human_error)

    @classmethod
    def center_register(cls, name, password, accounttype, code=None, sessionid=None):
        """
        :param name:注册用户名
        :param password:密码
        :param accounttype:类型 1：个性化 3：手机
        :param code:验证码
        :param sessionid:短信sessionid
        :returns: 注册成功返回 True
        """
        xml = '''<?xml version="1.0" encoding="utf-8"?>
                    <register>
                        <registerReq>
                            <accountInfoList>
                                <accountInfo>
                                    <accountName>%s</accountName>
                                    <accountType>%s</accountType>
                                    <verified>0</verified>
                                </accountInfo>
                            </accountInfoList>
                            <password>%s</password>
                            <sessionID>%s</sessionID>
                            <validType>0</validType>
                            <validCode>%s</validCode>
                            <userIP>%s</userIP>
                            <ext>
                                <item>
                                    <key>source</key>
                                    <value>13</value>
                                </item>
                            </ext>
                        </registerReq>
                    </register>
                ''' % (name, accounttype, password, sessionid, code, request.access_route[0])
        content = cls._post_request(cls.portalone_url, xml,
                                    log_func='center_register',
                                    log_id=name)
        return content

    @classmethod
    def get_identityid(cls, name, password, accounttype):
        xml = '''<?xml version="1.0" encoding="utf-8"?>
                        <authenticate>
                            <authenticateReq>
                                <accountName>%s</accountName>
                                <accountType>%s</accountType>
                                <password>%s</password>
                                <authType>MiguPassport</authType>
                                <disableMigu>0</disableMigu>
                                <ext>
                                    <item>
                                        <key>source</key>
                                        <value>13</value>
                                    </item>
                                    <item>
                                        <value>%s</value>
                                        <key>userIP</key>
                                    </item>
                                </ext>
                            </authenticateReq>
                        </authenticate>
                ''' % (name, accounttype, password, request.access_route[0])
        content = cls._post_request(cls.portalone_url, xml,
                                    log_func='get_identityid',
                                    log_id=name)

        if isinstance(content, error.ApiError):
            return content

        pattern = re.compile(r'<identityID>(\d+)</identityID>')
        identityid = pattern.findall(content)
        return identityid[0] if identityid else error.MiguError('获取信息失败')

    @classmethod
    def get_identity_token(cls, token, accounttype, systemtime, msgid, sourceid, appid):

        data = {"header": {"version": "1.0", "msgid": msgid, "systemtime": systemtime,
                           "sourceid": sourceid, "appid": appid, "apptype": accounttype},
                "body": {
                    "token": token}
                }

        content = cls._post_request_json(cls.platform_url, data,
                                         log_func='get_identity_token',
                                         log_id=None)

        if isinstance(content, error.ApiError):
            return content

        loginid = content.get('body').get('loginid', None)
        msisdn = content.get('body').get('msisdn', None)

        data = {}
        data['loginid'] = loginid
        data['msisdn'] = msisdn

        return data if data else error.MiguError('获取信息失败')

    @classmethod
    def token_validate(cls, token):
        xml = '''<?xml version="1.0" encoding="utf-8"?>
                     <tokenValidate>
                         <tokenValidateReq>
                            <token>%s</token>
                            <ext>
                                <item>
                                    <key>source</key>
                                    <value>13</value>
                                </item>
                            </ext>
                         </tokenValidateReq>
                     </tokenValidate>
        ''' % (token)
        content = cls._post_request(cls.portalone_url, xml,
                                    log_func='token_validate',
                                    log_id=None)
        if isinstance(content, error.ApiError):
            return content

        keys = ['identityID', 'msisdn', 'passID']
        data = {}
        for _k in keys:
            pattern = re.compile(r'<%s>(\d+)</%s>' % (_k, _k))
            _d = pattern.findall(content)
            data.update({_k: _d[0] if _d else None})
        return data

    @classmethod
    def get_user_info(cls, identityid, keyword='provinceID'):
        xml = '''<?xml version="1.0" encoding="utf-8"?>
                     <getUserInfo>
                         <getUserInfoReq>
                             <identityID>%s</identityID>
                         </getUserInfoReq>
                     </getUserInfo>
        ''' % (identityid)
        content = cls._post_request(cls.iduser_url, xml,
                                    log_func='get_user_info',
                                    log_id=identityid)
        if isinstance(content, error.ApiError):
            return content

        pattern = re.compile(r'<key>%s</key><value>(\d+)</value>' % keyword)
        provinceid = pattern.findall(content)
        return provinceid if provinceid else error.MiguError('获取信息失败')

    @classmethod
    def get_user_info_by_account_name(cls, account_name, account_type=3, keyword='provinceID'):
        '''
        获取用户中心用户信息，目前只适用于纯数字的ID获取
        :param account_name: 用户账户（手机号码）
        :param account_type: 账户类型（1：业务应用自定义用户名，2：Email，3：手机号码），我们取用3
        :param keyword: 需要获取ID的返回值属性
        :return: id <str>
        '''
        xml = '''<?xml version="1.0" encoding="utf-8"?>
                     <getUserInfo>
                         <getUserInfoReq>
                             <accountName>%s</accountName>
                             <accountType>%s</accountType>
                         </getUserInfoReq>
                     </getUserInfo>
        ''' % (account_name, account_type)
        content = cls._post_request(cls.iduser_url, xml,
                                    log_func='get_user_info_by_account_name',
                                    log_id=account_name)
        if isinstance(content, error.ApiError):
            return content

        if keyword in ['identityID', 'passID']:
            pattern = re.compile(r'<%s>(\d+)</%s>' % (keyword, keyword))
        else:
            pattern = re.compile(r'<key>%s</key><value>(\d+)</value>' % keyword)
        result_ids = pattern.findall(content)

        if keyword in ['passID']:
            return result_ids[0] if result_ids else None
        return result_ids[0] if result_ids else error.MiguError('获取信息失败')

    @classmethod
    def center_update_pwd(cls, identityid, oldpassword, newpassword):
        """

        :param identityid:用户中心 用户id
        :param oldpassword:
        :param newpassword:
        :returns: 修改成功返回True 否则 False
        """
        modify_xml = '''<?xml version="1.0" encoding="utf-8"?>
                    <modifyPassword>
                        <modifyPasswordReq>
                            <identityID>%s</identityID>
                            <oldPassword>%s</oldPassword>
                            <newPassword>%s</newPassword>
                            <disableMigu>0</disableMigu>
                        </modifyPasswordReq>
                    </modifyPassword>
                    ''' % (identityid, oldpassword, newpassword)
        content = cls._post_request(cls.iduser_url, modify_xml,
                                    log_func='center_update_pwd',
                                    log_id=identityid)
        return content

    @classmethod
    def center_reset_pwd(cls, accountname, newpassword, accounttype, code, sessionid):
        """

        :param accountname:用户名
        :param newpassword:新密码
        :param accounttype:类型 1：个性化 3：手机
        :param code:验证码
        :param sessionid:短信sessionid
        :returns: 成功返回True 否则 False
        """
        reset_xml = '''<?xml version="1.0" encoding="utf-8"?>
                            <resetPassword>
                                <resetPasswordReq>
                                    <accountName>%s</accountName>
                                    <accountType>%s</accountType>
                                    <newPassword>%s</newPassword>
                                    <validCode>%s</validCode>
                                    <validType>0</validType>
                                    <sessionID>%s</sessionID>
                                    <userIP>%s</userIP>
                                    <ext>
                                        <item>
                                            <value>%s</value>
                                            <key>userIP</key>
                                        </item>
                                    </ext>
                                </resetPasswordReq>
                            </resetPassword>
                    ''' % (accountname, accounttype, newpassword,
                           code, sessionid, request.access_route[0], request.access_route[0])
        content = cls._post_request(cls.iduser_url, reset_xml,
                                    log_func='center_reset_pwd',
                                    log_id=accountname)
        return content

    @classmethod
    def center_check_account(cls, name, accounttype):
        """

        :param name:手机
        :param accounttype:类型 1：个性化 3：手机
        :returns: True 未存在, False 已存在
        """
        check_xml = '''<?xml version="1.0" encoding="utf-8"?>
                            <checkAccountUnicity>
                                <checkAccountUnicityReq>
                                    <accountName>%s</accountName>
                                    <accountType>%s</accountType>
                                </checkAccountUnicityReq>
                            </checkAccountUnicity>
                    ''' % (name, accounttype)
        content = cls._post_request(cls.iduser_url, check_xml,
                                    log_func='center_check_account',
                                    log_id=name)

        if isinstance(content, error.ApiError):
            return content

        st = re.compile(r'<isExistent>(\d+)</isExistent>')
        ret = st.findall(content)
        return int(ret[0]) == 0 if ret else False

    @classmethod
    def center_sms_code(cls, phone, accounttype):
        """
        :param phone: 手机
        :param accounttype: 验证的业务代码 0:注册  1:密码重置  5:账号升级
        :returns:
        """
        atype = {'reg': 0, 'reset': 1, 'up': 5}
        accounttype = atype.get(accounttype)

        sms_xml = '''<?xml version="1.0" encoding="utf-8"?>
                            <smsOTPRequest>
                                <smsOTPRequestReq>
                                    <msisdn>%s</msisdn>
                                    <businessID>%s</businessID>
                                    <userIP>%s</userIP>
                                <ext>
                                    <item>
                                        <key>userIP</key>
                                        <value>%s</value>
                                    </item>
                                    <item>
                                        <key>source</key>
                                        <value>13</value>
                                    </item>
                                </ext>
                                </smsOTPRequestReq>
                            </smsOTPRequest>
        ''' % (phone, accounttype, request.access_route[0], request.access_route[0])
        content = cls._post_request(cls.portalone_url, sms_xml,
                                    log_func='center_sms_code',
                                    log_id=phone)

        if isinstance(content, error.ApiError):
            return content

        sessionid = re.compile(r'<sessionID>(\S+)</sessionID>')
        sess = sessionid.findall(content)
        return sess[0] if sess else error.MiguError('获取验证码失败')

    @classmethod
    def center_service_up(cls, phone, password, code, sessionid):
        """
        :param phone: 手机
        :param password: 升级密码
        :returns:
        """
        up_xml = '''<?xml version="1.0" encoding="utf-8"?>
                        <servicePassportUpgrade>
                            <servicePassportUpgradeReq>
                                <msisdn>%s</msisdn>
                                <password>%s</password>
                                <validCode>%s</validCode>
                                <validType>0</validType>
                                <sessionID>%s</sessionID>
                                <userIP>%s</userIP>
                            </servicePassportUpgradeReq>
                        </servicePassportUpgrade>
                ''' % (phone, password, code, sessionid, request.access_route[0])
        content = cls._post_request(cls.portalone_url, up_xml,
                                    log_func='center_service_up',
                                    log_id=phone)
        return content

    @classmethod
    def ota_download(cls, ua, contentcode, serviceid):
        try:
            client = Client(cls.download_url, timeout=5)
        except:
            print_log('migu_center', '[ota_download][%s][%s]: connection error'
                      % (contentcode, serviceid))
            return None

        d = dict(accessChannelID='1',
                 timestamp='20110415152000', deviceID='9990001', language='zh_CN',
                 countryCode='86', ip='11.11.11.1',
                 security='cdf+SaiyXS+2NLK7Rp678ZNaiCHZDpnQ9fB0pmbJgAk=',
                 cardID='', chargingID='',
                 contentCode=contentcode, instance='1', isTry='',
                 packageID='',
                 payType='',
                 portalChannelID='',
                 presentId='',
                 recommendID='',
                 saleChannelId=cls.down_channel,
                 saleChannelURL='',
                 serviceID=serviceid, shortAddr='', ua=ua, useType='0',
                 isChangePhone='',
                 imei=''
                 )

        result = client.service.authenticateDownload(d)
        if int(result['resultCode']) == 201018:  # ua查询出错, 使用自己的ua再查一次
            d['ua'] = '%s %s' % (
                'Mozilla/5.0 (Linux; U; Android 2.2; zh-cn; Nexus One Build/FRF91)',
                'AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1'
            )
            result = client.service.authenticateDownload(d)

        if int(result['resultCode']) == 200000:
            return result['downloadURL']

        return None


class Marketing(object):
    """营销中心接口
    """
    if os.environ.get('WXENV') in ['Production', 'Stage']:
        api_url = 'http://wap.cmgame.com:18080/portalone/campaign/'
    else:
        # test_url
        api_url = 'http://112.4.3.58:9100/portalone/campaign/'

    @classmethod
    def get_extendtions(cls):
        user = request.authed_user
        user_id = str(user._id)
        phone = str(user.phone)
        migu_id = user.partner_migu['id']
        channel = request.values.get('channels', '')
        device = request.values.get('device', '')
        imei = request.values.get('imei', '')
        ua = request.headers.get('User-Agent')
        if request.headers.getlist("X-Forwarded-For"):
            user_ip = request.headers.getlist("X-Forwarded-For")[0]
        else:
            user_ip = request.remote_addr
        # 2017/01/16 陶媛媛指出营销平台接受的postTime字段格式为yyyyMMDDHHmmss
        post_time = time.strftime('%Y%m%d%H%M%S')
        md5 = hashlib.md5()
        md5.update(phone)
        cookie_hash = md5.hexdigest()
        extension_info = {
            'extensionInfo': [
                {
                    'key': 'externalAccount',       # 外部账号
                    'value': ''
                },
                {
                    'key': 'passId',                # 一级用户中心的用户标识
                    'value': migu_id
                },
                {
                    'key': 'externalUserId',       # 外部账号对应的用户ID
                    'value': user_id
                },
                {
                    'key': 'token',                 # 统一认证token
                    'value': ''
                },
                {
                    'key': 'accountType',           # 帐号平台类型
                    'value': '4'
                },
                {
                    'key': 'tyChannel',             # 来源
                    'value': '2'
                },
                {
                    'key': 'tyChannelId',           # 来源的渠道ID
                    'value': channel
                },
                {
                    'key': 'uid',                    # 用户ID，当accountType为4时，该字段传入手机号
                    'value': phone
                },
                {
                    'key': 'userIp',                # 操作来源IP
                    'value': user_ip
                },
                {
                    'key': 'postTime',              # 操作时间，取值为毫秒时间戳
                    'value': post_time
                },
                {
                    'key': 'cookieHash',            # 用户Http请求中的cookie
                    'value': cookie_hash
                },
                {
                    'key': 'userAgent',             # 用户Http请求的userAgent
                    'value': ua
                },
                {
                    'key': 'macAddress',            # mac地址或设备唯一标识
                    'value': device
                },
                {
                    'key': 'imei',                  # 手机设备号
                    'value': imei
                },
            ]
        }
        return extension_info

    @classmethod
    def script_get_extendtions(cls,migu_id,phone,user_id):
        # 脚本类的数据获取不到实时内容。
        channel = device = imei = ua = 'script'
        user_ip = '11.11.11.11'
        post_time = time.strftime('%Y%m%d%H%M%S')
        md5 = hashlib.md5()
        md5.update(phone)
        cookie_hash = md5.hexdigest()
        extension_info = {
            'extensionInfo': [
                {
                    'key': 'externalAccount',       # 外部账号
                    'value': ''
                },
                {
                    'key': 'passId',                # 一级用户中心的用户标识
                    'value': migu_id
                },
                {
                    'key': 'externalUserId',       # 外部账号对应的用户ID
                    'value': user_id
                },
                {
                    'key': 'token',                 # 统一认证token
                    'value': ''
                },
                {
                    'key': 'accountType',           # 帐号平台类型
                    'value': '4'
                },
                {
                    'key': 'tyChannel',             # 来源
                    'value': '2'
                },
                {
                    'key': 'tyChannelId',           # 来源的渠道ID
                    'value': channel
                },
                {
                    'key': 'uid',                    # 用户ID，当accountType为4时，该字段传入手机号
                    'value': phone
                },
                {
                    'key': 'userIp',                # 操作来源IP
                    'value': user_ip
                },
                {
                    'key': 'postTime',              # 操作时间，取值为毫秒时间戳
                    'value': post_time
                },
                {
                    'key': 'cookieHash',            # 用户Http请求中的cookie
                    'value': cookie_hash
                },
                {
                    'key': 'userAgent',             # 用户Http请求的userAgent
                    'value': ua
                },
                {
                    'key': 'macAddress',            # mac地址或设备唯一标识
                    'value': device
                },
                {
                    'key': 'imei',                  # 手机设备号
                    'value': imei
                },
            ]
        }
        return extension_info

    @classmethod
    def query_campaign(cls, campaign_id):
        _api_url = urljoin(cls.api_url, 'InstantCampaignService/queryCampaigns')
        data = dict(campaignIds=[campaign_id])  # ['1000003133']
        try:
            resp = requests.post(_api_url, json=data, timeout=5)
        except requests.exceptions.Timeout:
            print_log('marketing', '[query_campaigns]: connection timeout')
            return error.MarketingError('网络连接超时')
        except:
            print_log('marketing', '[query_campaigns]: connection error')
            return error.MarketingError('网络连接失败')

        if resp.status_code != requests.codes.ok:
            return error.MarketingError('网络请求错误')

        ret = json.loads(resp.content)
        if 'returnCode' not in ret:
            return error.MarketingError('查询抽奖活动信息失败')

        if ret['returnCode'] != '1100020000':
            errmsg = error.MARKETING_ERROR.get(ret['returnCode'], '查询抽奖活动信息失败')
            return error.MarketingError(errmsg)

        try:
            infos = ret['resultInfoList'][0]['campaignBaseInfo']['extensionInfo']
        except:
            infos = []
        ret = dict(mobile_phone_only=False, is_exchange_rule=False, prize_valid_date=None)
        for info in infos:
            if info['key'] == 'mobilePhoneOnly':
                ret['mobile_phone_only'] = info['value']
            elif info['key'] == 'isExchangeRule':
                ret['is_exchange_rule'] = info['value']
            elif info['key'] == 'prizeValidDate':
                ret['prize_valid_date'] = info['value']

        return ret

    @classmethod
    def execute_campaign(cls, migu_id, phone, campaign_ids, trigger=16):
        _api_url = urljoin(cls.api_url, 'InstantCampaignService/executeCampaign')
        data = dict(
            campaignIds=campaign_ids,  # ['1000003133']
            currentUser={
                "extensionInfo": [{"key": "phone", "value": phone}],
                "userId": migu_id,  # 1800033951
            },
            scopeCondition={
                'portalTypes': ['2', '13']
            },
            triggerEvent=trigger
        )
        # 天御防刷扩展字段
        data.update(cls.get_extendtions())
        try:
            resp = requests.post(_api_url, json=data, timeout=5)
        except requests.exceptions.Timeout:
            print_log('marketing', '[execute_campaign]: connection timeout')
            return error.MarketingError('网络连接超时')
        except:
            print_log('marketing', '[execute_campaign]: connection error')
            return error.MarketingError('网络连接失败')

        if resp.status_code != requests.codes.ok:
            return error.MarketingError('网络请求错误')

        print_log('marketing', '[%s][%s][%s]: (%s) %s'
                  % ('execute_campaign', migu_id, campaign_ids, resp.status_code,
                     resp.content.decode('utf8')))

        ret = json.loads(resp.content)
        if 'returnCode' not in ret:
            return error.MarketingError('兑换抽奖机会失败')

        if ret['returnCode'] != '1100020000':
            errmsg = error.MARKETING_ERROR.get(ret['returnCode'], '兑换抽奖机会失败')
            return error.MarketingError(errmsg)

        if not ret['resultInfoList'] or 'resultCode' not in ret['resultInfoList'][0]:
            return error.MarketingError('兑换抽奖机会失败')

        if ret['resultInfoList'][0]['resultCode'] != '1100020000':
            errmsg = error.MARKETING_ERROR.get(ret['resultInfoList'][0]['resultCode'], '兑换抽奖机会失败')
            return error.MarketingError(errmsg)

        return True

    @classmethod
    def query_lottery_chance(cls, migu_id, campaign_id):
        _api_url = urljoin(cls.api_url, 'LotteryService/queryLotteryInfo')
        data = dict(
            userId=migu_id,  # 1800033951
            campaignId=campaign_id,  # 1000003133
        )
        try:
            resp = requests.post(_api_url, json=data, timeout=5)
        except requests.exceptions.Timeout:
            print_log('marketing', '[query_lottery_chance]: connection timeout')
            return error.MarketingError('网络连接超时')
        except:
            print_log('marketing', '[query_lottery_chance]: connection error')
            return error.MarketingError('网络连接失败')

        if resp.status_code != requests.codes.ok:
            return error.MarketingError('网络请求错误')

        ret = json.loads(resp.content)
        if 'returnCode' not in ret:
            return error.MarketingError('查询抽奖机会失败')

        if ret['returnCode'] != '1100020000':
            errmsg = error.MARKETING_ERROR.get(ret['returnCode'], '查询抽奖机会失败')
            return error.MarketingError(errmsg)

        return ret['lotteryChance']

    @classmethod
    def draw_lottery(cls, migu_id, campaign_id):
        _api_url = urljoin(cls.api_url, 'LotteryService/drawLottery')
        data = dict(
            userId=migu_id,  # 1800033951
            campaignId=campaign_id,  # 1000003133
            portalType='13'
        )
        # 天御防刷扩展字段
        data.update(cls.get_extendtions())
        try:
            resp = requests.post(_api_url, json=data, timeout=5)
        except requests.exceptions.Timeout:
            print_log('marketing', '[draw_lottery]: connection timeout')
            return error.MarketingError('网络连接超时')
        except:
            print_log('marketing', '[draw_lottery]: connection error')
            return error.MarketingError('网络连接失败')

        if resp.status_code != requests.codes.ok:
            return error.MarketingError('网络请求错误')

        print_log('marketing', '[%s][%s][%s]: (%s) %s'
                  % ('draw_lottery', migu_id, campaign_id, resp.status_code,
                     resp.content.decode('utf8')))

        ret = json.loads(resp.content)
        if 'returnCode' not in ret:
            return error.MarketingError('抽奖失败')

        if ret['returnCode'] != '1100020000':
            errmsg = error.MARKETING_ERROR.get(ret['returnCode'], '抽奖失败')
            return error.MarketingError(errmsg)

        return ret['prize']

    @classmethod
    def query_exchengable_prizes(cls, migu_id, campaign_id):
        """用户/活动可兑换奖励信息查询接口
        """
        _api_url = urljoin(cls.api_url, 'CommonCampaignService/queryExchengablePrizes')
        data = dict(
            userId=migu_id,  # 1800033951
            campaignId=campaign_id,  # 1000003133
        )
        try:
            resp = requests.post(_api_url, json=data, timeout=5)
        except requests.exceptions.Timeout:
            print_log('marketing', '[query_exchengable_prizes]: connection timeout')
            return error.MarketingError('网络连接超时')
        except:
            print_log('marketing', '[query_exchengable_prizes]: connection error')
            return error.MarketingError('网络连接超时')

        if resp.status_code != requests.codes.ok:
            return error.MarketingError('网络请求错误')

        ret = json.loads(resp.content)
        if 'returnCode' not in ret:
            return error.MarketingError('查询兑换奖励信息失败')

        if ret['returnCode'] != '1100020000':
            errmsg = error.MARKETING_ERROR.get(ret['returnCode'], '查询兑换奖励信息失败')
            return error.MarketingError(errmsg)

        return ret['exchengePrizes']

    @classmethod
    def draw_exchengable_prize(cls, migu_id, campaign_id, exchenge_ids, exchengeable_id,
                               exchenge_amount, name=None, phone=None, address=None, id_card=None):
        """领取用户获得的奖励
        """
        _api_url = urljoin(cls.api_url, 'CommonCampaignService/drawExchengablePrize')
        data = dict(
            userId=migu_id,  # 1800033951
            campaignId=campaign_id,  # 1000003133
            exchengeResourceIdList=exchenge_ids,
            exchengeableResourceId=exchengeable_id,
            exchengeAmount=exchenge_amount,
            personalName=name,
            contactNumber=phone,
            address=address,
            identityNo=id_card
        )
        # 天御防刷扩展字段
        data.update(cls.get_extendtions())
        try:
            resp = requests.post(_api_url, json=data, timeout=5)
        except requests.exceptions.Timeout:
            print_log('marketing', '[draw_exchengable_prize]: connection timeout')
            return error.MarketingError('网络连接超时')
        except:
            print_log('marketing', '[draw_exchengable_prize]: connection error')
            return error.MarketingError('网络连接超时')

        if resp.status_code != requests.codes.ok:
            return error.MarketingError('网络请求错误')

        print_log('marketing', '[%s][%s][%s]: (%s) %s'
                  % ('draw_exchengable_prize', migu_id, campaign_id, resp.status_code,
                     resp.content.decode('utf8')))

        ret = json.loads(resp.content)
        if 'returnCode' not in ret:
            return error.MarketingError('兑换奖励失败')

        if ret['returnCode'] != '1100020000':
            errmsg = error.MARKETING_ERROR.get(ret['returnCode'], '兑换奖励失败')
            return error.MarketingError(errmsg)

        return ret['exchengePrize']

    @classmethod
    def query_exchenged_prizes(cls, migu_id, campaign_id, page=1, pagesize=10):
        """查询用户获得的奖励
        """
        _api_url = urljoin(cls.api_url, 'CommonCampaignService/queryExchengedPrizes')
        data = dict(
            userId=migu_id,  # 1800033951
            campaignId=[campaign_id],  # 1000003133
            currentPage=page,
            offSet=pagesize
        )
        try:
            resp = requests.post(_api_url, json=data, timeout=5)
        except requests.exceptions.Timeout:
            print_log('marketing', '[query_exchenged_prizes]: connection timeout')
            return error.MarketingError('网络连接超时'), False
        except:
            print_log('marketing', '[query_exchenged_prizes]: connection error')
            return error.MarketingError('网络连接超时'), False

        if resp.status_code != requests.codes.ok:
            return error.MarketingError('网络请求错误'), False

        print_log('marketing', '[%s][%s][%s]: (%s) %s'
                  % ('query_exchenged_prizes', migu_id, campaign_id, resp.status_code,
                     resp.content.decode('utf8')))

        ret = json.loads(resp.content)
        if 'returnCode' not in ret:
            return error.MarketingError('查询已兑换奖励失败')

        if ret['returnCode'] != '1100020000':
            errmsg = error.MARKETING_ERROR.get(ret['returnCode'], '查询已兑换奖励失败')
            return error.MarketingError(errmsg), False

        end_page = page >= ret['totalPage']
        return ret['exchangedResourceList'], end_page

    @classmethod
    def draw_resource(cls, migu_id, phone, campaign_id, rtype, amount):
        """流量、话费发放接口(暂不支持话费), rtype: {4:话费, 6:流量}
        """
        _api_url = urljoin(cls.api_url, 'ResourceService/drawResource')
        data = dict(
            campaignId=campaign_id,  # 1000003136
            mobile=phone,  # 18618420913
            resourceType=rtype,
            amount=amount
        )
        try:
            resp = requests.post(_api_url, json=data, timeout=5)
        except requests.exceptions.Timeout:
            print_log('marketing', '[draw_resource]: connection timeout')
            return error.MarketingError('网络连接超时')
        except:
            print_log('marketing', '[draw_resource]: connection error')
            return error.MarketingError('网络连接超时')

        if resp.status_code != requests.codes.ok:
            return error.MarketingError('网络请求错误')

        print_log('marketing', '[%s][%s:%s][%s]: (%s) %s'
                  % ('draw_resource', migu_id, phone, campaign_id, resp.status_code,
                     resp.content.decode('utf8')))

        ret = json.loads(resp.content)
        if 'returnCode' not in ret:
            return error.MarketingError('流量或者话费发放失败')

        if ret['returnCode'] != '1100020000':
            errmsg = error.MARKETING_ERROR.get(ret['returnCode'], '流量或者话费发放失败')
            return error.MarketingError(errmsg)

        return True

    @classmethod
    def query_resource(cls, campaign_id):
        """查询发放活动的剩余奖励
        """
        _api_url = urljoin(cls.api_url, 'ResourceService/queryResourceByCampaign')
        data = dict(
            campaignId=campaign_id,  # 1000003136
        )
        try:
            resp = requests.post(_api_url, json=data, timeout=5)
        except requests.exceptions.Timeout:
            print_log('marketing', '[query_resource]: connection timeout')
            return error.MarketingError('网络连接超时')
        except:
            print_log('marketing', '[query_resource]: connection error')
            return error.MarketingError('网络连接超时')

        if resp.status_code != requests.codes.ok:
            return error.MarketingError('网络请求错误')

        print_log('marketing', '[%s][%s]: (%s) %s'
                  % ('query_resource', campaign_id, resp.status_code,
                     resp.content.decode('utf8')))

        ret = json.loads(resp.content)
        if 'returnCode' not in ret:
            return error.MarketingError('查询发放活动信息失败')

        if ret['returnCode'] != '1100020000':
            errmsg = error.MARKETING_ERROR.get(ret['returnCode'], '查询发放活动信息失败')
            return error.MarketingError(errmsg)

        return ret['resourceList']

    @classmethod
    def query_red_package_by_user(cls, migu_id, campaign_id):
        """查询用户指定活动获取红包列表
        """
        _api_url = urljoin(cls.api_url, 'RedPackageService/queryRedPakcageByUser')
        data = dict(
            userId=migu_id,  # 1800033951
            campaignId=campaign_id,  # 1000003136
        )
        try:
            resp = requests.post(_api_url, json=data, timeout=5)
        except requests.exceptions.Timeout:
            print_log('marketing', '[query_red_package_by_user]: connection timeout')
            return error.MarketingError('网络连接超时')
        except:
            print_log('marketing', '[query_red_package_by_user]: connection error')
            return error.MarketingError('网络连接超时')

        if resp.status_code != requests.codes.ok:
            return error.MarketingError('网络请求错误')

        print_log('marketing', '[%s][%s][%s]: (%s) %s'
                  % ('query_red_package_by_user', migu_id, campaign_id, resp.status_code,
                     resp.content.decode('utf8')))

        ret = json.loads(resp.content)
        if 'returnCode' not in ret:
            return error.MarketingError('查询用户指定活动获取红包列表失败')

        if ret['returnCode'] != '1100020000':
            errmsg = error.MARKETING_ERROR.get(ret['returnCode'], '查询用户指定活动获取红包列表失败')
            return error.MarketingError(errmsg)

        if not ret.get('redPackageList'):
            return error.MarketingError('查询用户指定活动获取红包列表失败')

        return ret['redPackageList']

    @classmethod
    def grab_red_package(cls, migu_id, campaign_id, resource_id):
        _api_url = urljoin(cls.api_url, 'RedPackageService/grabRedPackage')
        data = dict(
            userId=migu_id,  # 1800033951
            campaignId=campaign_id,  # 1000003133
            resourceId=resource_id,
            portalType='13'
        )
        # 天御防刷扩展字段
        data.update(cls.get_extendtions())
        try:
            resp = requests.post(_api_url, json=data, timeout=5)
        except requests.exceptions.Timeout:
            print_log('marketing', '[grab_red_package]: connection timeout')
            return error.MarketingError('网络连接超时')
        except:
            print_log('marketing', '[grab_red_package]: connection error')
            return error.MarketingError('网络连接失败')

        if resp.status_code != requests.codes.ok:
            return error.MarketingError('网络请求错误')

        print_log('marketing', '[%s][%s][%s][%s]: (%s) %s'
                  % ('grab_red_package', migu_id, campaign_id, resource_id, resp.status_code,
                     resp.content.decode('utf8')))

        ret = json.loads(resp.content)
        if 'returnCode' not in ret:
            return error.MarketingError('抢红包失败')

        if ret['returnCode'] != '1100020000':
            errmsg = error.MARKETING_ERROR.get(ret['returnCode'], '抢红包失败')
            return error.MarketingError(errmsg)

        return ret['prize']

    @classmethod
    def jf_report(cls, data_dict):
        """
        营销中心数据入经分库
        :param data_dict:
        :return:
        """
        # 如果是单元测试模式则直接返回
        if os.environ.get('WXENV') in ['UnitTest']:
            return

        if os.environ.get('WXENV') in ['Production', 'Stage']:
            _api_url = 'http://192.168.81.176:9002/dataPost'
        else:
            _api_url = 'http://192.168.56.92:9003/dataPost'
        data_dict['time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        data_dict['ip'] = request.access_route[0]
        try:
            resp = requests.post(_api_url, json=data_dict, timeout=5)
        except requests.exceptions.Timeout:
            print_log('marketing', '[%s][%s]: %s'
                      % ('jf_report', 'connection timeout', data_dict))
        except:
            print_log('marketing', '[%s][%s]: %s'
                      % ('jf_report', 'requests error', data_dict))
            
    @classmethod
    def trigger_report(cls, migu_id, phone, event,user_id=None):
        if os.environ.get('WXENV') in ['Production', 'Stage']:
            campaign_ids = ['1000000424']
            trigger_event_dict = {"send_gift":'10118','watch_video_3m':'10119','live_30m':'10120','download_game':'10117'}
            _api_url = urljoin(cls.api_url, 'InstantCampaignService/executeCampaign')
        else:
            # hp验收环境，用测试包测
            campaign_ids = ['1000000783']
            trigger_event_dict = {"send_gift":'10092','watch_video_3m':'10093','live_30m':'10094','download_game':'10091'}
            _api_url = urljoin('http://112.4.3.136:8080/portalone/campaign/', 'InstantCampaignService/executeCampaign')
        triggerEvent = trigger_event_dict.get(event)
        data = dict(
            campaignIds=campaign_ids,
            currentUser={
                "extensionInfo": [{"key": "phone", "value": phone}],
                "userId": migu_id,  # 1800033951
            },
            triggerEvent=triggerEvent
        )
        # 天御防刷扩展字段
        if user_id:
            data.update(cls.script_get_extendtions(migu_id,phone,user_id))
        else:
            data.update(cls.get_extendtions())
        data['extensionInfo'].append({'value':'1','key':'amount'})
        data['scopeCondition'] = {'@type': 'com.huawei.jaguar.campaign.api.domain.ScopeCondition', 'portalTypes': ['13']}
        try:
            resp = requests.post(_api_url, json=data, timeout=5)
        except requests.exceptions.Timeout:
            print_log('marketing', '[execute_campaign]: connection timeout')
            return error.MarketingError('网络连接超时')
        except:
            print_log('marketing', '[execute_campaign]: connection error')
            return error.MarketingError('网络连接失败')

        if resp.status_code != requests.codes.ok:
            return error.MarketingError('网络请求错误')

        print_log('marketing', '[%s][%s][%s]: (%s) %s'
                  % ('execute_campaign_trigger_event', migu_id, triggerEvent, resp.status_code,
                     resp.content.decode('utf8')))

        ret = json.loads(resp.content)
        if 'returnCode' not in ret:
            return error.MarketingError('%s事件失败'%event)
        return True

class PayByMg(object):
    # 调用大厅的支付能力
    headers = {'content-type': 'application/json', 'charset': 'UTF-8'}
    if os.environ.get('WXENV') in ['Production', 'Stage']:
        url = "http://plaza.cmgame.com:8088/gateway/post/json"
        s = 'Mx4lt7yo+cp4xj86Xank8oIyAbBuYre4'
    else:
        url = 'http://223.111.8.96:18088/gateway/post/json'
        s = 'xzaAEf14ut98sgPWE8Tvzo6XpFsmzQ4e'
        # 原先测试服，但不稳定，所以使用大厅现网环境 (还是测试服)
        # url = 'http://223.111.8.96:18088/gateway/post/json'   
        # s = 'xzaAEf14ut98sgPWE8Tvzo6XpFsmzQ4e'

    @classmethod
    def get_payurl(cls,user,cs,SDKVersion,dId,consumeCode,buyamount,**kwargs):
        data = {"eventName":"goodsManageEventHandler","handleMethod":"getPrice",'data':{}}
        data['data']['userID'] =  user.phone
        data['data']['t'] = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + '000'
        data['data']['cs'] = cs
        data['data']['SDKVersion'] = SDKVersion.replace(".",'')
        data['data']['dId'] = '1' #唯一标示
        data['data']['paySource'] = '3'
        data['data']['consumeCode'] = consumeCode
        data['data']['buyamount'] = 1 # 每个档位 一项计费点
        data['data']['goodsname'] = kwargs.get("goodsname",'')
        data['data']['s'] = cls.s #

        try:
            resp = requests.post(cls.url, json=data, headers=cls.headers, timeout=5,verify=False)
        except requests.exceptions.Timeout:
            print_log('PayByMg', '[%s][%s]: connection timeout' % ("get_payurl", user.id))
            return error.MiguError('网络连接超时')
        except:
            print_log('PayByMg', '[%s][%s]: connection error' % ('get_payurl', user.id))
            return error.MiguError('网络连接失败')
        print_log('PayByMg', '[%s][%s]: (%s) %s'% ('get_payurl',user.id, resp.status_code, resp.content.decode('utf8')))
        # {"success":false,"errorCode":"10004","message":"数据验证失败","resultData":null}
        result = json.loads(resp.content)
        if not result['success']:
            if result['errorCode'] == '10035':
                return error.MiguError(u'您今日该礼物赠送次数超过上限，可以去给主播送其他礼物哦')
            return error.MiguError(result['message'])
        # transactionId
        return result

    @classmethod
    def report_result(cls,user,code,orderResult,transactionId,orderId):
        # {"eventName":"goodsManageEventHandler",
        # "handleMethod":"paymentResult",
        # "data":{"code":"200",
        # "resultMsg":"",
        # "otherType":"1",
        # "orderResult":"1",
        # "transactionId":"14702894518806684312",
        # "orderId":"1"
        # }}
        data = {'eventName':'goodsManageEventHandler','handleMethod':'paymentResult',"data":{}}
        data['data']['code'] = code
        data['data']['message'] = ''
        data['data']['otherType'] = '2'
        data['data']['orderResult'] = orderResult
        data['data']['transactionId'] = transactionId
        data['data']['orderId'] = str(orderId)
        try:
            resp = requests.post(cls.url, json=data, headers=cls.headers, timeout=5,verify=False)
        except requests.exceptions.Timeout:
            print_log('PayByMg', '[%s][%s][%s]: connection timeout' % ("report_result", user.id,transactionId))
            return error.MiguError('网络连接超时')
        except:
            print_log('PayByMg', '[%s][%s][%s]: connection error' % ('report_result', user.id,transactionId))
            return error.MiguError('网络连接失败')
        print_log('PayByMg', '[%s][%s][%s]: (%s) %s'% ('report_result',user.id,transactionId, resp.status_code, resp.content.decode('utf8')))

        result = json.loads(resp.content)
        if not result['success']:
            return error.MiguError(result['message'])
        return result


    @classmethod
    def check_order(cls,transactionId):
        data = {'eventName':'ordersEventHandler','handleMethod':'getOrderDetails',"data":{}}
        data['data']['orderId'] = transactionId
        try:
            resp = requests.post(cls.url, json=data, headers=cls.headers, timeout=5,verify=False)
        except requests.exceptions.Timeout:
            print_log('PayByMg', '[%s][%s]: connection timeout' % ("check_order", transactionId))
            return error.MiguError('网络连接超时')
        except:
            print_log('PayByMg', '[%s][%s]: connection error' % ('check_order', transactionId))
            return error.MiguError('网络连接失败')
        print_log('PayByMg', '[%s][%s]: (%s) %s'% ('check_order',transactionId, resp.status_code, resp.content.decode('utf8')))

        result = json.loads(resp.content)
        if not result['success']:
            return error.MiguError(result['message'])
        return result


class MiguPay(object):
    aes_mode = AES.MODE_ECB         # 获取咪咕币接口时，加密deviceID的模式
    if os.environ.get('WXENV') in ['Production', 'Stage']:
        migupay_url = 'http://112.4.3.36:18080/portalone/migupay/'      # portalone透传支付中心
        vip_url = 'http://172.17.6.40:8080/portalone/services/PortalService?wsdl'    # SOAP地址
        sha_key = 'ZAQ!@%$%'                                        # SOAP访问公共参数sha加密密文
        md5_key = 'eae18bc41e1434dd98fa2dd989531da8'            # 咪咕币余额查询md5密文
        md5_key_default = 'rlezd9e9vffxr053'                        # 咪咕币赠送记录查询md5密文
        aes_key = '15acb4a88285ed2f'                                # 咪咕币余额查询passid的AES加密密文
        passid = None
        vip10_package_id = '760000124665'
        vip5_package_id = '500230544000'
    else:
        migupay_url = 'http://112.4.3.50:8084/portalone/migupay/'
        # migupay_url = 'http://112.4.3.136:8080/portalone/migupay/'
        vip_url = 'http://112.4.3.50:8084/portalone/services/PortalService?wsdl'
        sha_key = 'ZAQ!@%$%'
        md5_key = 'eae18bc41e1434dd98fa2dd989531da8'
        md5_key_default = 'rlezd9e9vffxr053'
        aes_key = '15acb4a88285ed2f'
        passid = '6484464505210'
        vip10_package_id = '802000033950'
        vip5_package_id = '802000033959'
    soap_client = None

    @classmethod
    def _load_soap_client(cls):
        try:
            cls.soap_client = Client(cls.vip_url)
        except:
            cls.soap_client = None

    @classmethod
    def _aes_encrypt(cls, passid):
        BS = AES.block_size
        pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
        cryptor = AES.new(cls.aes_key, cls.aes_mode)
        cipherhex = cryptor.encrypt(pad(passid)).encode('hex')
        return cipherhex

    @classmethod
    def _migupay_get_request(cls, url, data, headers=None, timeout=25, log_func=None, log_id=None):
        human_errors = {
            'query_balance_available_new': '获取咪咕币失败',
            'query_record': '获取咪咕币充值/消费记录失败',
            'query_present_record': '获取咪咕币赠送记录失败',
        }
        human_error = human_errors.get(log_func, '未知错误')
        headers = headers or {'content-type': 'text/json', 'charset': 'UTF-8'}
        data = data and json.dumps(data)
        try:
            resp = requests.get(url, data=data, headers=headers, timeout=timeout)
        except requests.exceptions.Timeout:
            print_log('migu_pay', '[%s][%s]: connection timeout' % (log_func, log_id))
            return error.MiguPayError('网络连接超时')
        except:
            print_log('migu_pay', '[%s][%s]: connection error [%s]' % (log_func, log_id), url)
            return error.MiguPayError('网络连接失败')
        print_log('migu_pay', '[%s][%s]: (%s) %s [%s]'
                  % (log_func, log_id, resp.status_code, resp.content.decode('utf8'), url))

        if resp.status_code != requests.codes.ok:
            return error.MiguPayError('网络请求错误')

        if log_func in ['query_balance_available_new', 'query_present_record']:
            # 如果接口返回xml格式数据，则将xml转换为json
            try:
                result = Xml2Json(resp.content).result
            except:
                return error.MiguPayError(human_error)
            content = result.get('response', {})
            code_ok = '200'
        else:
            content = json.loads(resp.content)
            code_ok = '000000'

        result_code = content.get('code')
        if result_code and result_code != code_ok:
            errmsg = error.MIGU_PAY_ERROR.get(result_code, human_error)
            return error.MiguPayError(errmsg)

        return content

    @classmethod
    def query_balance_available_new(cls, passid):
        passid = cls.passid or passid
        action = 'queryBalanceAvailable'
        id_value = cls._aes_encrypt(passid)
        nonce = str(random.randint(100000, 999999))
        md5str = 'IDValue=%s&nonce=%s%s' % (id_value, nonce, cls.md5_key)
        md5 = hashlib.md5()
        md5.update(md5str)
        sign = md5.hexdigest()
        xml = """<request><IDValue>{id_value}</IDValue><nonce>{nonce}</nonce><digestAlg>MD5</digestAlg>\
<sign>{sign}</sign></request>""".format(id_value=id_value, nonce=nonce, sign=sign)
        url = '%s%s?xml=%s' % (cls.migupay_url, action, xml)
        content = cls._migupay_get_request(url, None,
                                    log_func='query_balance_available_new',
                                    log_id=passid)

        if isinstance(content, error.ApiError):
            return content

        data = {
            'miguTotalCount': int(content.get('miguTotalCount', 0)),
            'miguMoneyCount': int(content.get('miguMoneyCount', 0)),
            'miguMarketingCount': int(content.get('miguMarketingCount', 0))
        }

        return data

    @classmethod
    def query_record(cls, passid, query_type, start_at, end_at, page_no, page_size):
        passid = cls.passid or passid
        action = 'queryMiguRecord'
        deviceID = '9990001'
        timestamp = time.strftime('%Y%m%d%H%M%S')
        sha = hashlib.sha256()
        sha.update('%s%s%s' % (deviceID, cls.sha_key, timestamp))
        security = base64.b64encode(sha.hexdigest())
        url = '%s%s?passid=%s&type=%s&startTime=%s&endTime=%s&pageNo=%s&pageSize=%s&deviceID=%s&\
timestamp=%s&security=%s&accessChannelID=1&language=zh_CN&countryCode=86' % \
              (cls.migupay_url, action, passid, query_type, start_at, end_at,
               page_no, page_size, deviceID, timestamp, security)
        content = cls._migupay_get_request(url, None,
                                    log_func='query_record',
                                    log_id=passid)

        if isinstance(content, error.ApiError):
            return content

        end_page = content.get('hasNextPage', 'F') == 'F'

        keys = ['companyID', 'transactionId', 'orderId', 'payType', 'producatInfo', 'count', 'totalPrice',
                'priceInfo', 'miguPrice', 'couponNum', 'couponActivityId', 'orderResult', 'createTime']
        records = []
        for row in content.get('rechargeRecordList', []):
            record = dict()
            for _k in keys:
                record.update({_k: row.get(_k)})
            records.append(record)

        return {'records': records, 'end_page': end_page}

    @classmethod
    def query_present_record(cls, passid, start_at, end_at, page_no, page_size):
        passid = cls.passid or passid
        action = 'queryPresentRecordDevelop'
        md5str = 'endTime=%s&page_no=%s&page_size=%s&passid=%s&startTime=%s%s' % \
                 (end_at, page_no, page_size, passid, start_at, cls.md5_key_default)
        md5 = hashlib.md5()
        md5.update(md5str)
        sign = md5.hexdigest()
        xml = """<request><passid>{0}</passid><startTime>{1}</startTime><endTime>{2}</endTime>\
<page_no>{3}</page_no><page_size>{4}</page_size><digestAlg>MD5</digestAlg><sign>{5}</sign>\
</request>""".format(passid, start_at, end_at, page_no, page_size, sign)
        url = '%s%s?xml=%s' % (cls.migupay_url, action, xml)
        # url = urljoin(cls.migupay_url, action)
        # data = {'xml': xml}
        content = cls._migupay_get_request(url, None,
                                    log_func='query_present_record',
                                    log_id=passid)
        if isinstance(content, error.ApiError):
            return content

        end_page = content.get('has_next_page', 'F') == 'F'
        keys = ['companyID', 'transactionId', 'orderId', 'orderResult', 'count', 'presentTime']
        records = []
        present_list = content.get('PresentList')
        if isinstance(present_list, dict):
            present_list = present_list.get('PresentDetail', [])
        else:
            present_list = []
        for row in present_list:
            record = dict()
            for _k in keys:
                record.update({_k: row.get(_k)})
            records.append(record)

        return {'records': records, 'end_page': end_page}

    @classmethod
    def _post_soap(cls, func, data, log_func=None, log_id=None):
        device_id = '9990001'
        timestamp = time.strftime('%Y%m%d%H%M%S')
        sha = hashlib.sha256()
        sha.update('%s%s%s' % (device_id, cls.sha_key, timestamp))
        security = base64.b64encode(sha.digest())
        _data = dict(
            accessChannelID='1',
            countryCode='86',
            deviceID=device_id,
            language='zh_CN',
            security=security,
            timestamp=timestamp,
        )
        data.update(_data)
        try:
            resp = func(data)
        except:
            print_log('migu_pay', '[%s][%s]: connection error' % (log_func, log_id))
            return error.MiguPayError('网络连接失败')

        print_log('migu_pay', '[SOAP][%s][%s]: [%s]' % (log_func, log_id, resp))
        return resp

    @classmethod
    def check_user_vip_level(cls, phone):
        vip = {
            'vip5': {'subscribed': False, 'can_sub': True},
            'vip10': {'subscribed': False, 'can_sub': True}
        }
        if not cls.soap_client:
            cls._load_soap_client()
        if not cls.soap_client:
            return error.MiguPayError('网络请求失败')

        func = cls.soap_client.service.querySubscriptions
        data = dict(
            userID=phone,
            userIDType='1',
            pageSize='100',
            pageNum='-1'
        )
        resp = cls._post_soap(func, data)

        if isinstance(resp, error.ApiError):
            return resp

        result_code = str(resp.resultCode)
        if result_code != '200000':
            return error.MiguPayError(u'查询用户会员等级失败！')

        # 没有任何订购包时，返回vip状态为0
        if not resp.subscriptionList:
            return vip

        vip5_sub_stat = -1
        vip10_sub_stat = -1
        for row in resp.subscriptionList:
            if row.packageID == cls.vip5_package_id:
                vip5_sub_stat = row.subScriptionState
            elif row.packageID == cls.vip10_package_id:
                vip10_sub_stat = row.subScriptionState
            if vip5_sub_stat != -1 and vip10_sub_stat != -1:
                break

        # sub_stat，1：已订购，3：已退订但套餐有效
        if vip10_sub_stat == 1:
            vip['vip10'] = {'subscribed': True, 'can_sub': False}
        elif vip10_sub_stat == 3:
            vip['vip10'] = {'subscribed': True, 'can_sub': True}
        if vip5_sub_stat == 1:
            vip['vip5'] = {'subscribed': True, 'can_sub': False}
        elif vip5_sub_stat == 3:
            vip['vip5'] = {'subscribed': True, 'can_sub': True}
        return vip

    @classmethod
    def check_user_vip(cls, phone):
        """已弃用"""
        if not cls.soap_client:
            cls._load_soap_client()
        if not cls.soap_client:
            return error.MiguPayError('网络请求失败')
        func = cls.soap_client.service.authenticateSubscribe
        data = dict(
            userID='15995026012',
            packageID=cls.vip5_package_id,
            userIDType='1'
        )
        resp = cls._post_soap(func, data)

        if isinstance(resp, error.ApiError):
            return resp

        vip_status = {'201016': 0, '201017': 1, '201209': 2}
        result_code = str(resp.resultCode)
        if result_code not in vip_status:
            return error.MiguPayError(u'查询用户会员等级失败！')

        return vip_status[result_code]

    @classmethod
    def vip_unsubscribe(cls, phone):
        if not cls.soap_client:
            cls._load_soap_client()
        if not cls.soap_client:
            return error.MiguPayError('网络请求失败')
        func = cls.soap_client.service.unsubscribe
        data = dict(
            userID=phone,
            packageID=cls.vip5_package_id,
            userIDType='1'
        )
        resp = cls._post_soap(func, data)

        if isinstance(resp, error.ApiError):
            return resp

        result_code = str(resp.resultCode)
        if result_code != '200000':
            return error.MiguPayError(resp.resultMsg)

        return True
