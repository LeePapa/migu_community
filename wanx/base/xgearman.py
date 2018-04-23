# -*- coding: utf8 -*-
from wanx import app
from wanx.base.log import print_log

import gearman


class Gearman(object):

    def __init__(self):
        servers = app.config.get("GEARMAN_SERVERS")
        gm_client = gearman.GearmanClient(servers)
        self.client = gm_client

    def check_request_status(self, job_request):
        if job_request.complete:
            return True
        elif job_request.timed_out:
            print_log('gearman', 'Job(%s):time out' % (job_request.unique))
        else:
            print_log('gearman', 'Job(%s): failed status(%s)'
                      % (job_request.unique, job_request.state))
        return False

    def do_background(self, task_name, data):
        completed_job_request = self.client.submit_job(task_name, data, background=True,
                                                       wait_until_complete=False, max_retries=5)
        return self.check_request_status(completed_job_request)
