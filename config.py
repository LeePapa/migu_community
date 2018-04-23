# -*- coding: utf8 -*-
import os

BASE_DIR = os.path.abspath((os.path.dirname(__file__)))


class Local(object):
    DEBUG = True
    TESTING = True
    SECRET_KEY = '\x820\x91\xdb\x1cAQ\x1f\xa2\xa4\xb7)x\xdf\x8e\xb1%fZ\xfedm\xca\xdf'
    BASE_DIR = BASE_DIR
    STATIC_BASE = BASE_DIR + '/static'
    LIVE_SERVER_URL = 'http://127.0.0.1:8088'
    MATCH_SERVER_URL = 'http://127.0.0.1:10021'
    SERVER_URL = 'http://127.0.0.1:8088'
    MATCH_URL = 'http://127.0.0.1:8004'
    SHARE_URL = 'http://127.0.0.1:8088'
    STATIC_URL = 'http://staticmg2.molizhen.com'
    MEDIA_URL = 'http://staticmg2.molizhen.com'
    VIDEO_URL = 'http://staticmg2.molizhen.com'
    SMS_URL = 'http://112.4.3.52:8310/SendSmsService/services/SendSms'  # 移动短信地址
    SMS_OTHER_URL = 'http://wap.cmgame.com:18080/portalone/sendSmsCode'  # 异网短信地址
    MONGO_HOST = 'localhost'
    MONGO_PORT = 27017
    MONGO_DBNAME = 'community'
    MONGO_LIVEDBNAME = 'live'
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    MREDIS_HOST = 'localhost'
    MREDIS_PORT = 6379
    GEARMAN_SERVERS = ['localhost:4730']
    MYSQL_MASTER = {
        'name': 'community',
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '',
        'charset': 'utf8mb4'
    }
    # 当前正式和测试一样。
    JPUSH_APP_KEY = u'33709e40747e70cb1606a4f6'
    JPUSH_MASTER_SECRET = u'96c33146a4ee3defdc6d112e'
    JPUSH_AES_KEY = u'7fbf9d72fa60f243'
    JPUSH_YX_APP_KEY = u'1d45a02a23f386345009d309'
    JPUSH_YX_MASTER_SECRET = u'5ba98111b0be3e623172f20b'


class UnitTest(object):
    DEBUG = True
    TESTING = True
    SECRET_KEY = '\x820\x91\xdb\x1cAQ\x1f\xa2\xa4\xb7)x\xdf\x8e\xb1%fZ\xfedm\xca\xdf'
    BASE_DIR = BASE_DIR
    STATIC_BASE = BASE_DIR + '/static'
    LIVE_SERVER_URL = 'http://127.0.0.1:8088'
    MATCH_SERVER_URL = 'http://127.0.0.1:10021'
    SERVER_URL = 'http://www.molizhen.com:8084'
    MATCH_URL = 'http://127.0.0.1:8004'
    SHARE_URL = 'http://www.molizhen.com:8084'
    STATIC_URL = 'http://staticmg2.molizhen.com'
    MEDIA_URL = 'http://staticmg2.molizhen.com'
    VIDEO_URL = 'http://staticmg2.molizhen.com'
    SMS_URL = 'http://112.4.3.52:8310/SendSmsService/services/SendSms'  # 移动短信地址
    SMS_OTHER_URL = 'http://wap.cmgame.com:18080/portalone/sendSmsCode'  # 异网短信地址
    MONGO_HOST = 'localhost'
    MONGO_PORT = 27017
    MONGO_DBNAME = 'test_community'
    MONGO_LIVEDBNAME = 'test_live'
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    MREDIS_HOST = 'localhost'
    MREDIS_PORT = 6379
    GEARMAN_SERVERS = ['localhost:4730']
    MYSQL_MASTER = {
        'name': 'test_community',
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '',
        'charset': 'utf8mb4'
    }
    JPUSH_APP_KEY = u'33709e40747e70cb1606a4f6'
    JPUSH_MASTER_SECRET = u'96c33146a4ee3defdc6d112e'
    JPUSH_AES_KEY = u'7fbf9d72fa60f243'
    JPUSH_YX_APP_KEY = u'1d45a02a23f386345009d309'
    JPUSH_YX_MASTER_SECRET = u'5ba98111b0be3e623172f20b'


class Test(object):
    DEBUG = True
    TESTING = True
    SECRET_KEY = '\x820\x91\xdb\x1cAQ\x1f\xa2\xa4\xb7)x\xdf\x8e\xb1%fZ\xfedm\xca\xdf'
    BASE_DIR = BASE_DIR
    STATIC_BASE = BASE_DIR + '/static'
    LIVE_SERVER_URL = 'http://112.4.19.166'
    MATCH_SERVER_URL = 'http://test-api.molizhen.com'
    SERVER_URL = 'http://test-api.molizhen.com'
    MATCH_URL = 'http://127.0.0.1'
    SHARE_URL = 'http://test-api.molizhen.com'
    STATIC_URL = 'http://test-video.molizhen.com'
    MEDIA_URL = 'http://test-video.molizhen.com'
    VIDEO_URL = 'http://test-video.molizhen.com'
    SMS_URL = 'http://112.4.3.52:8310/SendSmsService/services/SendSms'  # 移动短信地址
    SMS_OTHER_URL = 'http://wap.cmgame.com:18080/portalone/sendSmsCode'  # 异网短信地址
    MONGO_HOST = 'localhost'
    MONGO_PORT = 27017
    MONGO_DBNAME = 'community'
    MONGO_LIVEDBNAME = 'live'
    REDIS_HOST = 'localhost'
    REDIS_PORT = 63079
    MREDIS_HOST = 'localhost'
    MREDIS_PORT = 63079
    GEARMAN_SERVERS = ['localhost:4730']
    MYSQL_MASTER = {
        'name': 'community',
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '',
        'charset': 'utf8mb4'
    }
    JPUSH_APP_KEY = u'33709e40747e70cb1606a4f6'
    JPUSH_MASTER_SECRET = u'96c33146a4ee3defdc6d112e'
    JPUSH_AES_KEY = u'7fbf9d72fa60f243'
    JPUSH_YX_APP_KEY = u'1d45a02a23f386345009d309'
    JPUSH_YX_MASTER_SECRET = u'5ba98111b0be3e623172f20b'
    MONGO_LIVEHOST = '192.168.56.93'
    MONGO_LIVEPORT = 27017


class Stage(object):
    DEBUG = False
    TESTING = False
    SECRET_KEY = '\x820\x91\xdb\x1cAQ\x1f\xa2\xa4\xb7)x\xdf\x8e\xb1%fZ\xfedm\xca\xdf'
    BASE_DIR = BASE_DIR
    STATIC_BASE = BASE_DIR + '/static'
    LIVE_SERVER_URL = 'http://112.4.19.166'
    MATCH_SERVER_URL = 'http://test-api.molizhen.com'
    SERVER_URL = 'http://apimg3.molizhen.com'
    MATCH_URL = 'http://127.0.0.1'
    SHARE_URL = 'http://apimg3.molizhen.com'
    STATIC_URL = 'http://videomg3.molizhen.com'
    MEDIA_URL = 'http://videomg3.molizhen.com'
    VIDEO_URL = 'http://videomg3.molizhen.com'
    SMS_URL = 'http://112.4.3.52:8310/SendSmsService/services/SendSms'  # 移动短信地址
    SMS_OTHER_URL = 'http://wap.cmgame.com:18080/portalone/sendSmsCode'  # 异网短信地址
    MONGO_HOST = '192.168.99.17'
    MONGO_PORT = 62717
    MONGO_DBNAME = 'new_community'
    MONGO_LIVEDBNAME = 'live'
    REDIS_HOST = '192.168.99.17'
    REDIS_PORT = 62223
    MREDIS_HOST = '192.168.99.17'
    MREDIS_PORT = 62223
    GEARMAN_SERVERS = ['192.168.99.17:64731']
    MYSQL_MASTER = {
        'name': 'community_stage',
        'host': '192.168.99.17',
        'port': 63306,
        'user': 'root',
        'password': '',
        'charset': 'utf8mb4'
    }
    JPUSH_APP_KEY = u'33709e40747e70cb1606a4f6'
    JPUSH_MASTER_SECRET = u'96c33146a4ee3defdc6d112e'
    JPUSH_AES_KEY = u'7fbf9d72fa60f243'
    JPUSH_YX_APP_KEY = u'1d45a02a23f386345009d309'
    JPUSH_YX_MASTER_SECRET = u'5ba98111b0be3e623172f20b'


class Production(object):
    DEBUG = False
    TESTING = False
    SECRET_KEY = '\x820\x91\xdb\x1cAQ\x1f\xa2\xa4\xb7)x\xdf\x8e\xb1%fZ\xfedm\xca\xdf'
    BASE_DIR = BASE_DIR
    STATIC_BASE = '/data/video_community/static'
    LIVE_SERVER_URL = 'http://liveapi.cmgame.com'
    MATCH_SERVER_URL = 'http://api.cmgame.com'
    SERVER_URL = 'http://api.cmgame.com'
    MATCH_URL = 'http://api.cmgame.com'
    SHARE_URL = 'http://video.cmgame.com'
    STATIC_URL = 'http://video.cmgame.com'
    MEDIA_URL = 'http://video.cmgame.com'
    VIDEO_URL = 'http://video.cmgame.com'
    SMS_URL = 'http://112.4.3.52:8310/SendSmsService/services/SendSms'  # 移动短信地址
    SMS_OTHER_URL = 'http://wap.cmgame.com:18080/portalone/sendSmsCode'  # 异网短信地址
    MONGO_HOST = '192.168.99.17'
    MONGO_PORT = 62717
    MONGO_DBNAME = 'community'
    MONGO_LIVEDBNAME = 'live'
    REDIS_HOST = '192.168.99.17'
    REDIS_PORT = 62222
    MREDIS_HOST = '192.168.99.17'
    MREDIS_PORT = 62222
    GEARMAN_SERVERS = ['192.168.99.17:64730']
    MYSQL_MASTER = {
        'name': 'community',
        'host': '192.168.99.17',
        'port': 63306,
        'user': 'root',
        'password': '',
        'charset': 'utf8mb4'
    }
    JPUSH_APP_KEY = u'33709e40747e70cb1606a4f6'
    JPUSH_MASTER_SECRET = u'96c33146a4ee3defdc6d112e'
    JPUSH_AES_KEY = u'7fbf9d72fa60f243'
    JPUSH_YX_APP_KEY = u'1d45a02a23f386345009d309'
    JPUSH_YX_MASTER_SECRET = u'5ba98111b0be3e623172f20b'
