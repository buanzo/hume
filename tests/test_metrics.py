import sys
import os
import types
import unittest
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Dummy modules for optional deps
for name in ['zmq', 'psutil', 'requests', 'webhook_listener', 'logstash_async']:
    sys.modules[name] = types.ModuleType('dummy')

ls_handler = types.ModuleType('logstash_async.handler')
class AsynchronousLogstashHandler:
    pass
ls_handler.AsynchronousLogstashHandler = AsynchronousLogstashHandler
sys.modules['logstash_async.handler'] = ls_handler

confuse_mod = types.ModuleType('confuse')
class _C:
    def __init__(self, *a, **kw):
        pass

def _factory(*a, **kw):
    return _C()
for attr in ['String', 'OneOf', 'Integer', 'Choice', 'Optional']:
    setattr(confuse_mod, attr, _factory)
confuse_mod.Configuration = _C
sys.modules['confuse'] = confuse_mod

jinja2_mod = types.ModuleType('jinja2')
class Dummy:
    def __init__(self, *a, **kw):
        pass
jinja2_mod.FileSystemLoader = Dummy
jinja2_mod.Environment = Dummy
jinja2_mod.TemplateNotFound = Dummy
jinja2_mod.FunctionLoader = Dummy
sys.modules['jinja2'] = jinja2_mod

pid_mod = types.ModuleType('pid')
decorator_mod = types.ModuleType('pid.decorator')

def pidfile(func=None):
    def decorator(f):
        return f
    if callable(func):
        return func
    return decorator

decorator_mod.pidfile = pidfile
sys.modules['pid'] = pid_mod
sys.modules['pid.decorator'] = decorator_mod

from humed import Humed, SUPPORTED_MSG_VERSIONS

class TestMetrics(unittest.TestCase):
    def setUp(self):
        self.humed = Humed.__new__(Humed)
        self.humed.status = {}
        self.humed.metrics_port = None
        self.humed.metrics_token = None

    def sample_msg(self):
        return {
            'hume': {
                'version': SUPPORTED_MSG_VERSIONS[0],
                'timestamp': '2020-01-01T00:00:00.000000',
                'hostname': 'example.com',
                'level': 'info',
                'msg': 'ok',
                'tags': [],
                'task': 'TASK1',
                'extra': {}
            }
        }

    def test_render_metrics(self):
        self.humed.update_status(self.sample_msg())
        text = self.humed.render_metrics()
        self.assertIn('hume_task_last_ts_seconds', text)
        self.assertIn('hostname="example.com"', text)
        self.assertIn('task="TASK1"', text)

    def test_metrics_server(self):
        self.humed.metrics_port = 0
        self.humed.start_metrics_server()
        port = self.humed.metrics_server.server_address[1]
        self.humed.update_status(self.sample_msg())
        data = urllib.request.urlopen(f'http://127.0.0.1:{port}/metrics').read().decode()
        self.assertIn('hume_task_last_ts_seconds', data)
        self.humed.stop_metrics_server()

    def test_metrics_auth(self):
        self.humed.metrics_port = 0
        self.humed.metrics_token = 'secret'
        self.humed.start_metrics_server()
        port = self.humed.metrics_server.server_address[1]
        self.humed.update_status(self.sample_msg())
        # request without token should fail
        req = urllib.request.Request(f'http://127.0.0.1:{port}/metrics')
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(req).read()
        # with token should succeed
        req = urllib.request.Request(f'http://127.0.0.1:{port}/metrics', headers={'Authorization': 'Bearer secret'})
        data = urllib.request.urlopen(req).read().decode()
        self.assertIn('hume_task_last_ts_seconds', data)
        self.humed.stop_metrics_server()

if __name__ == '__main__':
    unittest.main()
