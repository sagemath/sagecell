
from urllib2 import urlopen
from urllib import urlencode
import json
from random import random
from time import sleep, time
import sys
import numpy
from multiprocessing import Pool
import contextlib
import traceback

MAXRAND=2**30
BASE_URL="http://127.0.0.1:8080"
POLL_INTERVAL=0.1

from timing_util import timing, json, json_request

class Transaction(object):
    def __init__(self):
        self.custom_timers={}


    def run(self):
        """
        Ask for the sum of two random numbers and check the result
        """
        computation_times=[]
        response_times=[]
        a=int(random()*MAXRAND)
        b=int(random()*MAXRAND)
        code='print %d+%d'%(a,b)
        msg_id=str(random())
        session=str(random())
        execute_msg={'message': json.dumps({"parent_header": {},
                                            "header": {"msg_id": msg_id,
                                                       "session": session},
                                            "msg_type": "execute_request",
                                            "content": {"code": code}})}
        eval_url=BASE_URL+'/eval'

        poll_url=BASE_URL+'/output_poll?'
        poll_values={'computation_id': session, 'sequence':0}

        with timing(computation_times):
            with timing(response_times):
                returned_session=json_request(eval_url,execute_msg)['computation_id']
            if returned_session!=session:
                raise ValueError("Session id returned does not match session id sent")
            output=None
            done=False
            while not done:
                sleep(POLL_INTERVAL)
                with timing(response_times):
                    r=json_request(poll_url+urlencode(poll_values))
                if len(r)==0 or 'content' not in r:
                    continue
                for m in r['content']:
                    poll_values['sequence']+=1
                    if (m['msg_type']=="stream"
                        and m['content']['name']=="stdout"):
                        ans=int(m['content']['data'])
                        if ans!=a+b:
                            print "COMPUTATION NOT CORRECT"
                            raise ValueError("Computation not correct: %s+%s!=%s, off by %s "%(a,b,ans, ans-a-b))
                        else:
                            done=True
                            break
        self.custom_timers['Computation']=computation_times
        self.custom_timers['Response']=response_times

__all__=['Transaction']

if __name__ == '__main__':
    trans = Transaction()
    trans.run()
    print trans.custom_timers
