"""
Nose tests for the web server
"""

import web_server

def skipped(func):
    from nose.plugins.skip import SkipTest
    def _(*args, **kwds):
        raise SkipTest("Test %s is skipped" % func.__name__)
    _.__name__ = func.__name__
    return _

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
        assert '<title>Sage Cell Server</title>' in rv.data

    #only passes if the config url is available, so turn this test on selectively
    @skipped
    def test_config(self):
        rv = self.app.get('/config')
        assert 'webserver=' in rv.data

