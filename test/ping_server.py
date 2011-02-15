
from urllib2 import urlopen
from urllib import urlencode
import json
from random import random
from time import sleep, time
import sys
import numpy

def compute(iterations=10):
    response_times=[]
    while iterations>0:
        computation='%s+%s'%(random(), random())
        eval_url='http://127.0.0.1:8080/eval?%s'%urlencode(dict(commands=computation))
        start_time=time()
        computation_id=json.load(urlopen(eval_url))[u'computation_id']
        response_times.append(time()-start_time)
        poll_url='http://127.0.0.1:8080/output_poll?computation_id=%s'%computation_id
        output=None
        while output is None:
            start_time=time()
            output=json.load(urlopen(poll_url)).get(u'output', None)
            response_times.append(time()-start_time)
            print '.',
            sleep(0.5)
        print computation, ':', output
        iterations-=1
    return response_times

if __name__ == "__main__":
    response_times=compute(int(sys.argv[1]))
    print 'Average: ', numpy.average(response_times), ', Std Dev: ', numpy.std(response_times)
