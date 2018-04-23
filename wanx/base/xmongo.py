# -*- coding: utf8 -*-
from pymongo import MongoClient
from wanx import app


__all__ = ["DB", "client"]

# api主mongodb
client = MongoClient(app.config.get('MONGO_HOST'), app.config.get('MONGO_PORT'), connect=False)
DB = client[app.config.get('MONGO_DBNAME')]

# live主mongodb
live_client = MongoClient(app.config.get('MONGO_LIVEHOST', app.config.get('MONGO_HOST')),
                          app.config.get('MONGO_LIVEPORT', app.config.get('MONGO_PORT')), connect=False)
LIVE_DB = live_client[app.config.get('MONGO_LIVEDBNAME')]
