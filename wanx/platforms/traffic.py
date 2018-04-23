# -*- coding: utf8 -*-
from wanx.base.log import print_log

import re
import requests
import hashlib


class Traffic(object):
    send_url = 'http://www.ll-lm.com:8091/interfaces/free_recharge'
    query_url = 'http://www.ll-lm.com:8091/interfaces/MeberShipQuery'
    key = '953B814F5E7AF9FE1E42E4339DAAD809'

    @classmethod
    def send_traffic(cls, requestid, phone):
        """

        :param requestid: 唯一标识字符串,客户端生成，
        :param phone: 手机号码
        :return:
        """
        m = hashlib.md5()
        _m = hashlib.md5()
        m.update(cls.key)
        _m.update(requestid + '+' + str(m.hexdigest()).upper())
        requesttoken = str(_m.hexdigest()).upper()

        xml = '''<?xml version='1.0' encoding='utf-8'?>
                    <REQUEST>
                        <ACTION>MeberShipRequest</ACTION>
                        <RequestID>%s</RequestID>
                        <RequestToken>%s</RequestToken>
                        <ECCode>2000001040</ECCode>
                        <ChannelID>1</ChannelID>
                        <BODY>
                            <Member>
                                <CRMApplyCode>10001</CRMApplyCode>
                                <UsecyCle>1</UsecyCle>
                                <Mobile>%s</Mobile>
                                <UserName>全网流量150M套餐</UserName>
                                <EffType>2</EffType>
                                <PrdCode>prod.10000008585103</PrdCode>
                                <OptType>0</OptType>
                            </Member>
                        </BODY>
                    </REQUEST>''' % (str(requestid), requesttoken, str(phone))

        headers = {'content-type': 'text/xml'}
        try:
            resp = requests.post(cls.send_url, data=xml, headers=headers, timeout=10)
        except requests.exceptions.Timeout:
            print_log('migu_traffic', '[send_traffic][%s]: connection timeout' % (requestid))
            return False
        except:
            print_log('migu_traffic', '[send_traffic][%s]: connection error' % (requestid))
            return False

        print_log('migu_traffic', '[send_traffic][%s]: (%s) %s'
                  % (requestid, resp.status_code, resp.content))

        if resp.status_code != requests.codes.ok:
            return False

        st = re.compile(r'<ResultCode>(\d+)</ResultCode>')
        ret = st.findall(resp.content)

        return int(ret[0]) == 0 if ret else False

    @classmethod
    def query_traffic(cls, requestid):
        """

        :param requestid: 唯一标识字符串,客户端生成，
        :returns: 0＝成功，-1 = 失败, 1 = 正在处理中  该接口返回含义与充值接口不同，代表提交到上游接口的状态
                该接口返回成功仅代表上游接口成功处理（多数情况为成功送出流量，个别省份只能代表已成功收到请求）
        """
        m = hashlib.md5()
        _m = hashlib.md5()
        m.update(cls.key)
        _m.update(requestid + '+' + str(m.hexdigest()).upper())
        requesttoken = str(_m.hexdigest()).upper()
        xml = '''<?xml version='1.0' encoding='utf-8'?>
                    <REQUEST>
                        <ACTION>MeberShipQuery</ACTION>
                        <RequestID>%s</RequestID>
                        <RequestToken>%s</RequestToken>
                        <ECCode>2000001040</ECCode>
                    </REQUEST>
                    ''' % (str(requestid), requesttoken)

        headers = {'content-type': 'text/xml'}
        try:
            resp = requests.post(cls.query_url, data=xml, headers=headers, timeout=10)
        except requests.exceptions.Timeout:
            print_log('migu_traffic', '[query_traffic][%s]: connection timeout' % (requestid))
            return False
        except:
            print_log('migu_traffic', '[query_traffic][%s]: connection error' % (requestid))
            return False

        print_log('migu_traffic', '[query_traffic][%s]: (%s) %s'
                  % (requestid, resp.status_code, resp.content))

        if resp.status_code != requests.codes.ok:
            return False

        st = re.compile(r'<ResultCode>(\S+)</ResultCode>')
        ret = st.findall(resp.content)
        return ret[0]
