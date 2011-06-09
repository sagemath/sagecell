
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

class Transaction(object):
    def __init__(self, **kwargs):
        self.custom_timers={}
        self.BASE_URL=kwargs.get('base_url', 'http://localhost:8080')
        
    def run(self):
        """
        Simply query for the configuration, which involves a database query and running git on the command line.
        """
        response_times=[]
        config_url=self.BASE_URL+'/ping_json'

        with timing(response_times):
            response = json_request(config_url)
        if response['reply']!='pong':
            raise ValueError("Reply is not the expected reply")

        self.custom_timers['Response']=response_times

__all__=['Transaction']

if __name__ == '__main__':
    trans = Transaction()
    trans.run()
    print trans.custom_timers
