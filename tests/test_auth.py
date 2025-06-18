import sys
import os
import types
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# dummy modules for optional dependencies
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

# pid.decorator stub
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

# Minimal jinja2 stub required by humetools
jinja2_mod = types.ModuleType('jinja2')
class Dummy:
    def __init__(self, *a, **kw):
        pass
jinja2_mod.FileSystemLoader = Dummy
jinja2_mod.Environment = Dummy
jinja2_mod.TemplateNotFound = Dummy
jinja2_mod.FunctionLoader = Dummy
sys.modules['jinja2'] = jinja2_mod

from humed import Humed
from hume import MESSAGE_VERSION

class TestAuthToken(unittest.TestCase):
    def setUp(self):
        self.humed = Humed.__new__(Humed)
        self.humed.auth_token = 'secret'

    def sample_msg(self, token='secret'):
        return {
            'token': token,
            'hume': {
                'version': MESSAGE_VERSION,
                'timestamp': '2020-01-01T00:00:00',
                'hostname': 'example.com',
                'level': 'info',
                'msg': 'ok',
                'tags': [],
                'task': 'TASK1',
                'extra': {}
            }
        }

    def test_check_auth_token(self):
        msg = self.sample_msg()
        self.assertTrue(self.humed.check_auth_token(msg))
        msg = self.sample_msg(token='wrong')
        self.assertFalse(self.humed.check_auth_token(msg))

if __name__ == '__main__':
    unittest.main()
