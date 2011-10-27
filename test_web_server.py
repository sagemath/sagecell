"""
Nose tests for the web server
"""

import web_server

class TestWebReplies:
    def setUp(self):
        web_server.app.config['TESTING'] = True
        self.app = web_server.app.test_client()
        # set up temp mongodb instance

    def tearDown(self):
        # clean up temp mongodb instance
        pass

    def test_front_page(self):
        rv = self.app.get('/')
        assert '<title>Simple Compute Server</title>' in rv.data
    
    def test_config(self):
        rv = self.app.get('/config')
        assert 'webserver=' in rv.data

