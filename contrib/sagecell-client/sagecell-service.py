#!/usr/bin/env python

# curl -k -sS -L --data-urlencode "accepted_tos=true" --data-urlencode "code=myvar,myothervar=3,4\nprint 1+2" --data-urlencode "user_variables=myvar" --data-urlencode "user_variables=myothervar" $url

import urllib
import urllib2
import json
import sys
from random import randint
import time
from datetime import datetime

retries = 3

def message(s):
    print "%s: %s"%(datetime.now(), s)

for i in range(retries):
    reply = {'success': False, 'msg': 'default message'}
    try:
        a,b = randint(-2**31,2**31), randint(-2**31,2**31)
        code = "print %s+%s"%(a,b)
        # if you agree with the terms of service at /tos.html
        data = urllib.urlencode(dict(code=code, accepted_tos="true"))
        request = urllib2.urlopen(sys.argv[1]+'/service', data, timeout = 30)
        reply = json.loads(request.read())
        assert reply['success'] is True

        # this retry business is a temporary kludge until we figure out why, every few hours, we
        # have a request that comes back as executed, but the stdout is not in the dictionary
        # drilling down, it seems that the compute message never actually gets sent to the kernel
        # and it appears the problem is in the zmq connection between the webserver and the kernel
        if 'stdout' in reply or i==retries-1:
            # check answer if we are in the last retry loop, no matter what
            answer = int(reply['stdout'].strip())
            assert a+b == answer
            break
        else:
            message("stdout not in reply on try %d; retrying..."%i)
            time.sleep(0.5)
            continue

    except Exception as e:
        import traceback
        traceback.print_exc()
        message("Reply: %s"%reply)
        exit(1)
