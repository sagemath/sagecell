
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

maxint=2**30

@contextlib.contextmanager
def timing(results=None):
    """
    Time the execution of the block of code. If a results list is
    passed in, the time is appended to the list. Also returns a list
    of one element containing the time the execution took.

    To use, do something like:

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

class Transaction(object):
    def __init__(self):
        self.custom_timers={}


    def run(self):
        computation_times=[]
        response_times=[]
        a=int(random()*maxint)
        b=int(random()*maxint)
        computation='print %d+%d'%(a,b)
        eval_url='http://127.0.0.1:8080/eval?%s'%urlencode(dict(commands=computation))
        with timing(computation_times):
            with timing(response_times):
                computation_id=json.load(urlopen(eval_url))[u'computation_id']
            poll_url='http://127.0.0.1:8080/output_poll?computation_id=%s'%computation_id
            output=None
            while True:
                sleep(0.1)
                with timing(response_times):
                    response=urlopen(poll_url).read()
                r=json.loads(response)
                if ('output' in r 
                    and 'closed' in r['output'] 
                    and r['output']['closed'] is True):
                    ans=int(r['output']['stream_0']['content'])
                    if a+b!=ans:
                        print "COMPUTATION NOT CORRECT"
                        raise ValueError("Computation not correct: %s+%s!=%s, off by %s "%(a,b,ans, ans-a-b))
                    else:
                        break
        self.custom_timers['Computation']=computation_times
        self.custom_timers['Response']=response_times

if __name__ == '__main__':
    trans = Transaction()
    trans.run()
    print trans.custom_timers
    # processes=int(sys.argv[1])
    # iterations=int(sys.argv[2])
    # pool = Pool(processes=processes)
    # result = [pool.apply_async(compute, [iterations]) for _ in range(processes)]
    # response_times=[]
    # eval_times=[]
    # for p in range(processes):
    #     results=result[p].get()
    #     eval_times.extend(results['eval'])
    #     response_times.extend(results['response'])

    # print 'RESPONSE: Average: ', numpy.average(response_times), ', Std Dev: ', numpy.std(response_times)
    # print 'EVAL: Average: ', numpy.average(eval_times), ', Std Dev: ', numpy.std(eval_times)
