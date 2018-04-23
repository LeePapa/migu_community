# -*- coding: utf8 -*-
import sys
import datetime, time
from bson import ObjectId
from flask_admin.contrib.pymongo import filters
from flask_admin.contrib.peewee.filters import BasePeeweeFilter
from flask_admin.babel import lazy_gettext
from wanx.base import const
from wanx.models.game import CategoryGame, Game
from wanx.models.user import User


class WxMongoFilter(filters.BasePyMongoFilter):
    def __init__(self, column, name, field_func=str, options=None, data_type=None):
        super(WxMongoFilter, self).__init__(column, name, options, data_type)

        self.column = column
        self.field_func = field_func


class EqualFilter(WxMongoFilter):
    def apply(self, query, value):
        value = apply(self.field_func, [value])
        query.append({self.column: value})
        return query

    def operation(self):
        return lazy_gettext(u'等于')


class LikeFilter(filters.FilterLike):
    def operation(self):
        return lazy_gettext(u'包含')


class BooleanEqualFilter(filters.BooleanEqualFilter):
    def operation(self):
        return lazy_gettext(u'等于')


class GreaterFilter(WxMongoFilter):
    def apply(self, query, value):
        value = apply(self.field_func, [value])
        query.append({self.column: {'$gt': value}})
        return query

    def operation(self):
        return lazy_gettext(u'大于')


class SmallerFilter(WxMongoFilter):
    def apply(self, query, value):
        value = apply(self.field_func, [value])
        query.append({self.column: {'$lt': value}})
        return query

    def operation(self):
        return lazy_gettext(u'小于')


class PeeweeEqualFilter(BasePeeweeFilter):
    def apply(self, query, value):
        return query.filter(self.column == int(value))

    def operation(self):
        return lazy_gettext(u'等于')


class CategoryFileter(WxMongoFilter):
    def apply(self, query, value):
        value = apply(self.field_func, [value])
        gids = CategoryGame._load_category_game_ids(value)
        gidobj = [ObjectId(g) for g in gids]
        query.append({self.column: {'$in': gidobj}})
        return query

    def operation(self):
        return lazy_gettext(u'等于')


class GreaterTimeFileter(filters.FilterGreater):
    def apply(self, query, value):
        try:
            d = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            s = time.mktime(d.timetuple())
            t = float(s)
        except ValueError:
            t = 0
        query.append({self.column: {'$gt': t}})
        return query

    def operation(self):
        return lazy_gettext(u'大于')


class SmallerTimeFileter(filters.FilterSmaller):
    def apply(self, query, value):
        try:
            d = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            s = time.mktime(d.timetuple())
            t = float(s)
        except ValueError:
            t = 0
        query.append({self.column: {'$lt': t}})
        return query

    def operation(self):
        return lazy_gettext(u'小于')


# 通过游戏名称关键字查询视频
class GameFileter(WxMongoFilter):
    def apply(self, query, value):
        reload(sys)
        sys.setdefaultencoding('utf-8')
        value = apply(self.field_func, [value])
        gids = Game.get_by_name(value)
        gidobj = [ObjectId(g) for g in gids]
        query.append({self.column: {'$in': gidobj}})
        return query

    def operation(self):
        return lazy_gettext(u'包含')


# 通过用户名称查询视频
class UserFileter(WxMongoFilter):
    def apply(self, query, value):
        reload(sys)
        sys.setdefaultencoding('utf-8')
        value = apply(self.field_func, [value])
        user = User.get_by_nickname(value)
        uidobj = []
        if user:
            uidobj = [user._id]
        query.append({self.column: {'$in': uidobj}})
        return query

    def operation(self):
        return lazy_gettext(u'包含')


