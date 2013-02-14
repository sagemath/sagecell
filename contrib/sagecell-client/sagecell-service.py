#!/usr/bin/env python
try:
    import urllib
    import urllib2
    import json
    import sys
    from random import randint
    a,b = randint(-2**31,2**31), randint(-2**31,2**31)
    code = "print %s+%s"%(a,b)
    data = urllib.urlencode(dict(code=code))
    request = urllib2.urlopen(sys.argv[1]+'/service', data, timeout = 30)
    reply = json.loads(request.read())
    answer = int(reply['stdout'].strip())

    assert reply['success'] is True
    assert a+b == answer
except Exception as e:
    import traceback
    traceback.print_exc()
    exit(1)
