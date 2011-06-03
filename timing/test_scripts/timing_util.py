"""
Provide a timing utility context manager
"""
import contextlib
@contextlib.contextmanager
def timing(results=None):
    """
    Time the execution of the block of code. If a results list is
    passed in, the time is appended to the list. Also returns a list
    of one element containing the time the execution took.

    To use, do something like::

        from time import sleep
        results_list=[]
        with timing(results_list) as t:
            sleep(1)
        print results_list, t

    Exceptions in the code should be re-raised and the timing should
    correctly be set regardless of the exceptions.
    """
    from time import time
    try:
        # code in the context is executed when we yield
        start=[time()]
        yield start
    except:
        # any exceptions in the code should get propogated
        raise
    finally:
        start.append(time()-start[0])
        if results is not None:
            results.append(start)

import urllib
import urllib2

try: import simplejson as json
except ImportError: import json

def json_request(url, data=None):
    """
    Send a JSON message to the URL and return the result as a
    dictionary.

    :param data: a JSON-stringifiable object, passed in the POST
      variable ``message``
    :returns: a JSON-parsed dict/list/whatever from the server reply
    """
    if data is not None:
        data = urllib.urlencode(data)
    response = urllib2.urlopen(url, data)
    return json.loads(response.read())

