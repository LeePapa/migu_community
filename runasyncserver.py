# -*- coding: utf8 -*-
import os
import sys


if __name__ == "__main__":
    env = sys.argv[1] if len(sys.argv) > 1 else 'Local'
    if env not in ['Local', 'Test', 'Stage', 'Production', 'UnitTest']:
        raise EnvironmentError('The environment variable (WXENV) is invalid ')
    os.environ['WXENV'] = env
    os.environ['WXASYNC'] = 'YES'
    from gevent import wsgi, monkey
    monkey.patch_all()
    from wanx import app
    server = wsgi.WSGIServer(('0.0.0.0', 8087), app)
    server.serve_forever()
