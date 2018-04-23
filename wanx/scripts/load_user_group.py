# -*- coding: utf8 -*-
"""从txt文件中导入分租
使用方法：
到项目根目录下执行
python-path wanx/scripts/load_user_group.py -env=xxx -group=xxx -txt=xxx
"""
from os.path import dirname, abspath

import argparse
import sys
import os


def load_user(gid, txt):
    g = Group.get_one(gid)
    if not g:
        print('\033[91m指定的组不存在')
        return

    total = 0
    not_exists = 0
    in_group = 0
    success = 0
    with open(txt, 'r') as f:
        for line in f:
            total += 1
            phone = line.strip()
            user = User.get_by_phone(phone)
            if not user:
                not_exists += 1
            else:
                if UserGroup.user_in_group(group, str(user._id)):
                    in_group += 1
                else:
                    ug = UserGroup.init()
                    ug.group = g._id
                    ug.user = user._id
                    ug.phone = user.phone
                    ug.create_model()
                    success += 1

    print('用户导入完成结果：\n\t总用户: %s \n\t成功添加用户: %s \n\t不存在用户: %s \n\t组已存在用户: %s '
          % (total, success, not_exists, in_group))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-env', action='store', dest='wxenv', required=True,
                        help='Test|Stage|Production')
    parser.add_argument('-group', action='store', dest='group', required=True,
                        help='组ID')
    parser.add_argument('-txt', action='store', dest='txt', required=True,
                        help='导入文件地址')

    args = parser.parse_args(sys.argv[1:])
    wxenv = args.wxenv
    group = args.group
    txt = args.txt
    if wxenv not in ['Local', 'Test', 'Stage', 'Production', 'UnitTest']:
        raise EnvironmentError('The environment variable (WXENV) is invalid ')

    os.environ['WXENV'] = wxenv
    sys.path.append(dirname(dirname(dirname(abspath(__file__)))))

    from wanx.models.user import User, Group, UserGroup
    load_user(group, txt)
