import os
import sys
import types
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Dummy modules for optional dependencies except requests
for name in ['zmq', 'psutil', 'webhook_listener', 'logstash_async']:
    sys.modules[name] = types.ModuleType('dummy')

ls_handler = types.ModuleType('logstash_async.handler')
class AsynchronousLogstashHandler:
    pass
ls_handler.AsynchronousLogstashHandler = AsynchronousLogstashHandler
sys.modules['logstash_async.handler'] = ls_handler

# Stub requests module with a post() function
requests_mod = types.ModuleType('requests')
class DummyResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code

def post(url, json=None, timeout=None):
    post.called.append((url, json, timeout))
    return DummyResponse(200)
post.called = []
requests_mod.post = post
sys.modules['requests'] = requests_mod

import importlib

import humed_plugins.http as http_plugin
from humed_plugins import load_plugins, get_plugin

# ensure plugin uses our stubbed requests
importlib.reload(http_plugin)


class TestHttpPlugin(unittest.TestCase):
    def test_send_posts_json(self):
        pkt = {'hume': {'version': 1}}
        cfg = {'url': 'http://example.com/api', 'timeout': 2}
        self.assertTrue(http_plugin.send(humepkt=pkt, config=cfg))
        self.assertEqual(post.called[0][0], 'http://example.com/api')
        self.assertEqual(post.called[0][1], pkt)
        self.assertEqual(post.called[0][2], 2)

    def test_plugin_loader(self):
        plugins = load_plugins()
        self.assertIn('http', plugins)
        self.assertIs(get_plugin('http'), http_plugin)


if __name__ == '__main__':
    unittest.main()
