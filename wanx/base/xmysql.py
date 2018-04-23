# -*- coding: utf8 -*-
from wanx import app
from peewee import MySQLDatabase
from playhouse.pool import PooledDatabase


# 由于pip版本的peewee的mysql连接池有bug,  所以自己实现，暂时没用连接池
class PooledMySQLDatabase(PooledDatabase, MySQLDatabase):
    def _is_closed(self, key, conn):
        is_closed = super(PooledMySQLDatabase, self)._is_closed(key, conn)
        if not is_closed:
            try:
                conn.ping(False)
            except:
                is_closed = True
        return is_closed


config = app.config.get('MYSQL_MASTER')
MYDB = MySQLDatabase(config['name'], user=config['user'], password=config['password'],
                     host=config['host'], port=config['port'], charset=config['charset'])
