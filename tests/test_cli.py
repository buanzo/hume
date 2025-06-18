import sys
import os
import types
import unittest

# Ensure repository root is on sys.path so local modules can be imported when
# tests are executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Provide dummy modules so Hume can be imported without optional deps
for name in ['zmq', 'psutil']:
    sys.modules[name] = types.ModuleType('dummy')

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

from types import SimpleNamespace
from hume import Hume

class TestHumeCLI(unittest.TestCase):
    def test_message_construction(self):
        args = SimpleNamespace(
            verbose=False,
            level='warning',
            humecmd='',
            task='TASK1',
            append_pstree=False,
            tags=['a', 'b'],
            encrypt_to=None,
            token=None,
            recvtimeout=1000,
            hostname='example.com',
            extra=None,
            msg='hello'
        )
        h = Hume(args)
        pkt = h.reqObj
        self.assertEqual(pkt['hume']['level'], 'warning')
        self.assertEqual(pkt['hume']['hostname'], 'example.com')
        self.assertEqual(pkt['hume']['tags'], ['a', 'b'])
        self.assertEqual(pkt['hume']['msg'], 'hello')

    def test_auth_token_included(self):
        args = SimpleNamespace(
            verbose=False,
            level='info',
            humecmd='',
            task='TASK1',
            append_pstree=False,
            tags=[],
            encrypt_to=None,
            token='secret',
            recvtimeout=1000,
            hostname='host',
            extra=None,
            msg='hello'
        )
        h = Hume(args)
        self.assertEqual(h.reqObj['token'], 'secret')

if __name__ == '__main__':
    unittest.main()
