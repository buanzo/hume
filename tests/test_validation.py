import sys
import os
import types
import unittest

# Ensure repository root is on sys.path so local modules can be imported when
# tests are executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Provide a dummy zmq module so humed can be imported without optional deps
dummy = types.ModuleType('dummy')
for name in [
    'zmq',
    'psutil',
    'requests',
    'webhook_listener',
    'logstash_async'
]:
    sys.modules[name] = dummy

# Provide logstash_async.handler with required class so humed import works
ls_handler = types.ModuleType('logstash_async.handler')
class AsynchronousLogstashHandler:
    pass
ls_handler.AsynchronousLogstashHandler = AsynchronousLogstashHandler
sys.modules['logstash_async.handler'] = ls_handler

# Minimal confuse stub
confuse_mod = types.ModuleType('confuse')
class _C:
    def __init__(self, *a, **kw):
        pass
def _factory(*a, **kw):
    return _C()
for attr in ['String', 'OneOf', 'Integer', 'Choice']:
    setattr(confuse_mod, attr, _factory)
confuse_mod.Configuration = _C
sys.modules['confuse'] = confuse_mod

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

from humed import Humed
from hume import MESSAGE_VERSION

class TestIsValidHume(unittest.TestCase):
    def setUp(self):
        self.humed = Humed.__new__(Humed)  # bypass __init__

    def valid_msg(self):
        return {
            'hume': {
                'version': MESSAGE_VERSION,
                'timestamp': '2020-01-01T00:00:00',
                'hostname': 'example.com',
                'level': 'info',
                'msg': 'ok',
                'tags': ['a', 'b'],
                'task': 'TASK1',
                'extra': {}
            }
        }

    def test_valid_packet(self):
        self.assertTrue(self.humed.is_valid_hume(self.valid_msg()))

    def test_invalid_version(self):
        msg = self.valid_msg()
        msg['hume']['version'] = 999
        self.assertFalse(self.humed.is_valid_hume(msg))

    def test_missing_hostname(self):
        msg = self.valid_msg()
        del msg['hume']['hostname']
        self.assertFalse(self.humed.is_valid_hume(msg))

    def test_tags_must_be_list(self):
        msg = self.valid_msg()
        msg['hume']['tags'] = 'notalist'
        self.assertFalse(self.humed.is_valid_hume(msg))

if __name__ == '__main__':
    unittest.main()
