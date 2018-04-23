# -*- coding: utf8 -*-

from bson.objectid import ObjectId
from flask import request
from wanx.models.info import EsInformation

from wanx import app
from wanx.base import util, const, error


@app.route('/info/electronic_sport/list', methods=['GET', 'POST'])
@util.jsonapi()
def es_info_list():
    """
    获取电竞资讯列表(GET|POST)
    :uri: /info/electronic_sport/list
    :param: page: 页码【可选，默认值1】
    :param: nbr: 每页显示数量【可选，默认10】
    :return:
    """
    params = request.values
    page = int(params.get('page', 1))
    pagesize = int(params.get('nbr', 10))
    os = params.get('os', 'android')

    ids = EsInformation.info_ids(page, pagesize)
    infos = [i.format(os) for i in EsInformation.get_list(ids)]

    return {'info': infos, 'end_page': len(ids) != pagesize}


@app.route('/info/electronic_sport', methods=['GET', 'POST'])
@util.jsonapi()
def es_info():
    """
    获取电竞资讯(GET|POST)
    :uri: /info/electronic_sport
    :param: info_id: 资讯id
    :return:
    """
    info_id = request.values.get('info_id', None)
    if not info_id:
        return error.InvalidArguments
    info = EsInformation.get_one(info_id)
    if not info:
        return error.InfoNotExist
    return {'info': info.format()}
