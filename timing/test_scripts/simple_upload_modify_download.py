
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

code="""
print('beginning...')
with open('test.txt','r+') as f:
    s = f.read()
    f.seek(0)
    f.write(s.replace('test','finished'))
print('ending...')
"""

FILE_CONTENTS = 'This is a test file'
FILE_RESULT_CONTENTS = FILE_CONTENTS.replace('test','finished')

class Transaction(object):
    def __init__(self, **kwargs):
        self.custom_timers={}
        self.BASE_URL=kwargs.get('base_url', 'http://localhost:8080/')
        self.POLL_INTERVAL=kwargs.get('poll_interval', 0.1)
        with open('test.txt', 'w') as f:
            f.write(FILE_CONTENTS)

    def run(self):
        """
        Upload a file, change it, and then download it again
        """
        computation_times=[]
        response_times=[]

        s=Session(self.BASE_URL)
        request=s.prepare_execution_request(code,files=['test.txt'])
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
                    if (m['msg_type']=="extension"
                        and m['content']['msg_type']=="files"):
                        returned_file=m['content']['content']['files'][0]
                        if returned_file!='test.txt':
                            print("RETURNED FILENAME NOT CORRECT")
                            raise ValueError("Returned filename not correct: %s"%returned_file)
                        with timing(response_times):
                            f=s.get_file(returned_file)
                        if f!=FILE_RESULT_CONTENTS:
                            print("RETURNED FILE CONTENTS NOT CORRECT")
                            raise ValueError("Returned file contents not correct: %s"%f)
                        # if we've made it this far, we're done
                        done=True
                        break

        self.custom_timers['Computation']=computation_times
        self.custom_timers['Response']=response_times

__all__=['Transaction']

if __name__ == '__main__':
    trans = Transaction()
    trans.run()
    print(trans.custom_timers)
