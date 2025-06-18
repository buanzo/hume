import os
import sys
import unittest
import json
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from humesaas import SaaSServer, EVENTS

class TestSaaSServer(unittest.TestCase):
    def setUp(self):
        EVENTS.clear()
        self.server = SaaSServer(port=0)
        self.server.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.stop()

    def test_post_and_get(self):
        data = {'hume': {'version': 1, 'msg': 'hello'}}
        req = urllib.request.Request(
            f'http://127.0.0.1:{self.port}/events',
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        urllib.request.urlopen(req).read()
        resp = urllib.request.urlopen(f'http://127.0.0.1:{self.port}/events').read().decode()
        items = json.loads(resp)
        self.assertEqual(items[0], data)

if __name__ == '__main__':
    unittest.main()
