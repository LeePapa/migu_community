# coding:utf-8
# usage :python 1118_task3.py Production
import sys,os
from os.path import abspath, dirname, join
import pymongo
import datetime,time
from bson.code import Code
from bson.objectid import ObjectId
_curr_path = abspath(dirname(__file__))
sys.path.append(join(_curr_path, '..'))
env = sys.argv[1] if len(sys.argv) > 1 else 'Local'
os.environ['WXENV'] = env
from wanx.platforms.migu import Marketing

now_time = datetime.datetime.now()
if env == "Local":
    start_time = datetime.datetime(2016,10,20,0,0,0)
    end_time = datetime.datetime(2016,11,19,0,0,0)
    con = pymongo.MongoClient('127.0.0.1')
else:
    con = pymongo.MongoClient('192.168.99.18', 62717)
    start_time = datetime.datetime(2016,11,9,0,0,0)
    if start_time<=now_time:
        end_time = now_time
    else:
        start_time = datetime.datetime(2016,10,28,0,0,0)
        end_time = datetime.datetime(2016,11,9,0,0,0)

live = con.live
community = con.community
map_fun =  Code("""function () {
                var gap = 0;
                gap = this.finish_at-this.create_at;
                emit(this.user_id,gap);
                }""")

reduce_fun = Code("""function (key, values) {
                  var total = 0;
                  for (var i = 0; i < values.length; i++) {
                    total += values[i];
                  }
                   if (total>1800){
                      return parseInt(total)
                    }
                }
              """)

if end_time>start_time:
    start_timestamp = time.mktime(start_time.timetuple())
    end_timestamp = time.mktime(end_time.timetuple())
    query = {"create_at":{"$gt":start_timestamp,"$lt":end_timestamp}}
    out_put = 'result'
    result = live.event.map_reduce(map_fun,reduce_fun,out_put,query=query)
    result = {ObjectId(i['_id']):i['value'] for i in result.find() if i['value']}
    suit_uids = result.keys()
    # 测试用户
    suit_uids.append(ObjectId('5704b0d2268b6c0ff789b35e'))  # 海军手机号
    result = community.users.find({"_id":{"$in":suit_uids}},{"phone":1,'partner_migu':1})
    items = [ (i['phone'],i['partner_migu'],i['_id']) for i in result if i.get("phone")]
    print env,now_time,'num',len(items)
    for phone,partner_migu,user_id in items:
        tag = Marketing.trigger_report(partner_migu['id'], phone, 'live_30m',str(user_id))
        print phone,partner_migu['id'],tag
