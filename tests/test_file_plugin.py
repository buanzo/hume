import os
import sys
import json
import tempfile
import types
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Dummy modules for optional dependencies
for name in ['zmq', 'psutil', 'requests', 'webhook_listener', 'logstash_async']:
    sys.modules[name] = types.ModuleType('dummy')

ls_handler = types.ModuleType('logstash_async.handler')
class AsynchronousLogstashHandler:
    pass
ls_handler.AsynchronousLogstashHandler = AsynchronousLogstashHandler
sys.modules['logstash_async.handler'] = ls_handler

import humed_plugins.file as file_plugin
from humed_plugins import load_plugins, get_plugin


class TestFilePlugin(unittest.TestCase):
    def test_send_writes_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'humed.log')
            packet = {'hume': {'version': 1, 'timestamp': '0', 'hostname': 'host'}}
            cfg = {'path': path}
            self.assertTrue(file_plugin.send(humepkt=packet, config=cfg))
            with open(path) as f:
                data = json.loads(f.read().strip())
            self.assertEqual(data, packet)

    def test_plugin_loader(self):
        plugins = load_plugins()
        self.assertIn('file', plugins)
        self.assertIs(get_plugin('file'), file_plugin)


if __name__ == '__main__':
    unittest.main()
