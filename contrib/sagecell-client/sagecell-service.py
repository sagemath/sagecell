#!/usr/bin/env python

import urllib
import urllib2
import json
import sys
from random import randint
import time
from datetime import datetime

retries = 2

def message(s):
    print('{}: {}'.format(datetime.now(), s))

for i in range(retries):
    a, b = randint(-2**31, 2**31), randint(-2**31, 2**31)
    code = 'print({} + {})'.format(a, b)
    # if you agree with the terms of service at /tos.html
    data = urllib.urlencode(dict(code=code, accepted_tos="true"))
    try:
        request = urllib2.urlopen(sys.argv[1] + '/service', data, timeout=30)
        reply = json.loads(request.read())
        # Every few hours we have a request that comes back as executed, but the
        # stdout is not in the dictionary. It seems that the compute message
        # never actually gets sent to the kernel and it appears the problem is
        # in the zmq connection between the webserver and the kernel.
        #
        # Also sometimes reply is unsuccessful, yet the server keeps running
        # and other requests are serviced. Since a restart breaks all active
        # interacts, better not to restart the server that "mostly works" and
        # instead we'll just accumulate statistics on these random errors to
        # help resolve them.
        if ('success' in reply
            and reply['success']
            and 'stdout' in reply
            and int(reply['stdout'].strip()) == a + b):
            exit(0)
        message("Reply %s. %d attempts left." % (reply, retries - 1 - i))
    except Exception as e:
        # Even exceptions may be transient...
        import traceback
        message(traceback.format_exc())
    time.sleep(0.5)
message("%d unsuccessful attempts, the server is not working!" % retries)
exit(1)
