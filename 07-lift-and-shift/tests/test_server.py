import json
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from server import create_server


class RehostingAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(host='127.0.0.1', port=0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def get_json(self, path):
        with urlopen(f'http://127.0.0.1:{self.port}{path}', timeout=3) as response:
            return response.status, json.loads(response.read())

    def test_health(self):
        status, body = self.get_json('/health')
        self.assertEqual(status, 200)
        self.assertEqual(body, {'status': 'ok'})

    def test_main_page(self):
        status, body = self.get_json('/')
        self.assertEqual(status, 200)
        self.assertEqual(body['app'], 'legacy-demo')
        self.assertEqual(body['version'], '1.0')
        self.assertTrue(body['hostname'])

    def test_unknown_route_returns_404(self):
        with self.assertRaises(HTTPError) as ctx:
            urlopen(f'http://127.0.0.1:{self.port}/missing', timeout=3)
        self.assertEqual(ctx.exception.code, 404)


if __name__ == '__main__':
    unittest.main()
