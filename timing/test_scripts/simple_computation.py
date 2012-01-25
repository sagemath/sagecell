
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

from timing_util import timing, json, json_request

from sagecell import Session

class Transaction(object):
    def __init__(self, **kwargs):
        self.custom_timers={}
        self.MAXRAND=kwargs.get('maxrand', 2**30)
        self.BASE_URL=kwargs.get('base_url', 'http://localhost:8080/')
        self.POLL_INTERVAL=kwargs.get('poll_interval', 0.1)
        
    def run(self):
        """
        Ask for the sum of two random numbers and check the result
        """
        computation_times=[]
        response_times=[]
        a=int(random()*self.MAXRAND)
        b=int(random()*self.MAXRAND)
        code='print %d+%d'%(a,b)
        s=Session(self.BASE_URL)
        request=s.prepare_execution_request(code)
        sequence=0
        with timing(computation_times):
            with timing(response_times):
                s.send_execution_request(request)

            done=False
            while not done:
                sleep(self.POLL_INTERVAL)
                with timing(response_times):
                    r=s.output_poll(sequence)
                if len(r)==0 or 'content' not in r:
                    continue
                for m in r['content']:
                    sequence+=1
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
