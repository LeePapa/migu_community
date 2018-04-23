# -*- coding: utf8 -*-
"""从营销平台同步用户抽奖活动的奖励到账情况
"""
from os.path import dirname, abspath

import argparse
import sys
import os


def get_orders_in_hand():
    """ 获取有营销平台订单号并且状态为"营销平台处理中"的订单
    """
    orders = UserOrder.get_orders_in_hand()
    return orders


def sync_order(order):
    """同步订单状态
    """
    user = User.get_one(order.user_id, check_online=False)
    page = 1
    sync_completed = False  # 同步是否完成
    page_retry = 0  # 每页调用api错误次数, 3次不成功直接放弃此订单的同步
    while True:
        _prizes, end_page = Marketing.query_exchenged_prizes(user.partner_migu['id'],
                                                             order.campaign_id,
                                                             page=page, pagesize=10)
        # 营销平台接口调用错误重试5次
        if isinstance(_prizes, error.ApiError):
            page_retry += 1
            if page_retry < 3:
                continue
            else:
                break

        for _prize in _prizes:
            # issueStatus: 0:未发放, 1:已发放
            if _prize['recId'] == order.recid and _prize['issueStatus'] == '1':
                order.status = const.ORDER_FINISHED
                order.save()
                sync_completed = True
                break

        if sync_completed or end_page:
            break

        page += 1
        page_retry = 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-env', action='store', dest='wxenv', required=True,
                        help='Test|Stage|Production')
    args = parser.parse_args(sys.argv[1:])
    wxenv = args.wxenv
    if wxenv not in ['Local', 'Test', 'Stage', 'Production', 'UnitTest']:
        raise EnvironmentError('The environment variable (WXENV) is invalid ')

    os.environ['WXENV'] = wxenv
    sys.path.append(dirname(dirname(dirname(abspath(__file__)))))

    from wanx.base import const, error
    from wanx.models.store import UserOrder
    from wanx.models.user import User
    from wanx.platforms.migu import Marketing

    orders = get_orders_in_hand()
    for order in orders:
        sync_order(order)
