# -*- coding: utf8 -*-
from fabric.api import env, run, roles, task, cd, local

import time


# 跳板机
env.gateway = 'root@119.254.103.104:2222'
env.forward_agent = True

# 目标服务器
env.roledefs = {
    'admin': {
        'hosts': ['root@mg.w1:60022'],
        'pwd': '/apps2/migu_community'
    },
    'w12': {
        'hosts': ['root@mg.w1:60022', 'root@mg.w2:60022'],
        'pwd': '/apps2/migu_community'
    },
    'v12': {
        'hosts': ['root@mg.v1:60022', 'root@mg.v2:60022'],
        'pwd': '/apps/migu_community'
    }
}

env.key_filename = "files/deploy.rsa"


def _on_w12():
    return env.host_string in env.roledefs['w12']['hosts']


def _on_v12():
    return env.host_string in env.roledefs['v12']['hosts']


@task
def prepare_deploy():
    local('git checkout master')
    local('git merge dev')
    local('python runtest.py')
    local('git push')


@task
@roles('w12')
def reload_supervisord():
    run('supervisorctl reload')
    time.sleep(5)
    run('supervisorctl status')


@task
@roles('admin')
def deploy_admin():
    cwd = env.roledefs['admin']['pwd']
    with cd(cwd):
        run('git pull')
        run('venv/bin/pip install -r requirements.txt')
        run('service uwsgi reload admin_uwsgi')


@task
@roles('w12', 'v12')
def deploy_api():
    cwd = env.roledefs['w12']['pwd'] if _on_w12() else env.roledefs['v12']['pwd']
    with cd(cwd):
        run('git pull')
        run('venv/bin/pip install -r requirements.txt')
        if _on_w12():
            run('service uwsgi reload uwsgi')

        if _on_v12():
            run('venv/bin/uwsgi --reload /apps/migu_community/logs/uwsgi/migu_vc.pid')
