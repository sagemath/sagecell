
from urllib2 import urlopen
from urllib import urlencode
import json
from random import random
from time import sleep, time
import sys
from multiprocessing import Pool
import contextlib
import traceback

from timing_util import timing, json, json_request
from time import time

from sagecell import Session

class Transaction(object):
    def __init__(self, **kwargs):
        self.custom_timers={}
        self.MAXRAND=kwargs.get('maxrand', 2**30)
        self.BASE_URL=kwargs.get('base_url', 'http://localhost:8080/')
        self.POLL_INTERVAL=kwargs.get('poll_interval', 0.25)
        self.TIMEOUT=kwargs.get('timeout', 30)

    def run(self):
        """
        Ask for the sum of two random numbers and check the result
        """
        computation_times=[]
        response_times=[]
        a=int(random()*self.MAXRAND)
        b=int(random()*self.MAXRAND)
        code=json.dumps('print %d+%d'%(a,b))
        s=Session(self.BASE_URL)
        request=s.prepare_execution_request(code)
        sequence=0

        with timing(computation_times):
            with timing(response_times):
                s.send_execution_request(request)
            start_time = time()
            done=False
            while not done:
                if time()-start_time>self.TIMEOUT:
                    raise Exception("TIMEOUT")
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
    import argparse

    parser = argparse.ArgumentParser(description='Run simple additionc computation.')
    parser.add_argument('--base_url', default='http://localhost:8080',
                        help='the base url for the sage server')
    parser.add_argument('-q','--quiet', dest='quiet', action='store_true')
    parser.add_argument('--timeout', dest='timeout', default=30, type=float)
    args = parser.parse_args()

    trans = Transaction(base_url=args.base_url, timeout=args.timeout)
    trans.run()
    if not args.quiet:
        print trans.custom_timers
