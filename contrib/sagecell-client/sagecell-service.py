#!/usr/bin/env python
try:
    import urllib
    import urllib2
    import json
    from random import randint
    a,b = randint(-2**31,2**31), randint(-2**31,2**31)
    code = "print %s+%s"%(a,b)
    data = urllib.urlencode(dict(code=code))
    request = urllib2.urlopen('http://aleph2.sagemath.org/service', data, timeout = 8)
    reply = json.loads(request.read())
    answer = int(reply['stdout'].strip())

    assert reply['success'] is True
    assert a+b == answer
    assert 1==0
except Exception as e:
    import traceback
    traceback.print_exc()
    exit(1)