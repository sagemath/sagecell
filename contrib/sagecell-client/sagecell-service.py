#! /usr/bin/env python3

from datetime import datetime
import random
import requests
import sys
import time


retries = 3

def message(s):
    print('{}: {} attempts left. {}'.format(datetime.now(), retries, s))

while retries:
    retries -= 1
    a, b = random.randint(-2**31, 2**31), random.randint(-2**31, 2**31)
    code = 'print({} + {})'.format(a, b)
    try:
        r = requests.post(sys.argv[1] + '/service',
                          data={"code": code, "accepted_tos": "true"},
                          timeout=5)
        reply = r.json()
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
        if (reply['success']
            and 'stdout' in reply
            and int(reply['stdout'].strip()) == a + b):
            exit(0)
        message(reply)
    except Exception as e:
        message(e)
    time.sleep(0.5)
message('The server is not working!')
exit(1)
