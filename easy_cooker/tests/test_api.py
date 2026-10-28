import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from app.api import make_server
from app.clock import ManualClock
from app.service import RestaurantService


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clock = ManualClock(1000)
        cls.server = make_server(RestaurantService(clock=cls.clock), port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def call(self, path, data=None, method=None):
        request = Request(self.base + path, method=method,
                          data=json.dumps(data).encode() if data is not None else None)
        try:
            response = urlopen(request, timeout=3)
        except HTTPError as exc:
            response = exc
        with response:
            return response.code, json.load(response)

    def test_full_http_flow(self):
        self.assertEqual(len(self.call('/menu')[1]), 5)
        code, accepted = self.call('/orders', {'request_id': 'http-a', 'table_id': 1,
            'items': [{'dish_id': 'greens', 'quantity': 1}]})
        self.assertEqual(code, 200)
        self.assertTrue(accepted['accepted'])
        task = self.call('/chefs/1/task')[1]['task']
        path = f"/chefs/1/tasks/{task['id']}/complete"
        self.assertEqual(self.call(path, method='POST')[0], 409)
        self.clock.advance(180)
        self.assertEqual(self.call(path, method='POST')[1]['status'], 'completed')
        session = f"/sessions/{accepted['session_id']}"
        self.assertEqual(self.call(session)[1]['first_course_status'], 'on_time')
        self.assertEqual(self.call(session+'/close', method='POST')[0], 200)

    def test_errors(self):
        self.assertEqual(self.call('/health')[1], {'status': 'ok'})
        self.assertEqual(self.call('/orders', {'bad': True})[0], 400)
        self.assertEqual(self.call('/missing')[0], 404)
        self.assertEqual(self.call('/chefs/99/task')[0], 404)
        request = Request(self.base+'/orders', data=b'{bad', method='POST')
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=3)
        self.assertEqual(caught.exception.code, 400)
        caught.exception.close()

    def test_http_verification_script(self):
        import io
        from contextlib import redirect_stdout
        from unittest.mock import patch
        import verify_http
        with patch('sys.argv', ['verify_http.py', '--base-url', self.base, '--table', '3']):
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(verify_http.main(), 0)
        self.assertIn('验证通过', output.getvalue())
