import os
import web_server
import unittest
import tempfile

class SinglecellTestCase(unittest.TestCase):

    def setUp(self):
        web_server.app.config['TESTING'] = True
        self.app = web_server.app.test_client()

    def tearDown(self):
        pass

    def test_front_page(self):
        rv = self.app.get('/')
        assert '<title>Simple Compute Server</title>' in rv.data


if __name__ == '__main__':
    unittest.main()
