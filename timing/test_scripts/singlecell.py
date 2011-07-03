import random
from MultipartPostHandler import encode_request
from urllib2 import urlopen, Request
from urllib import urlencode
from json import loads


EVAL_PATH='/eval'
POLL_PATH='/output_poll'
FILE_PATH='/files'


class Session:
    def __init__(self, server):
        server=server.rstrip('/')
        self.server=server
        self.session=random.random()
        
    def prepare_execution_request(self, code, files=None, sage_mode=True):
        """
        Prepare an execution request prior to sending it.

        We break up the preparation and sending phases so that it is easy 
        to time just the request.
        """
        msg=[('session_id', self.session),
             ('commands', code),
             ('msg_id', random.random()),
             ('sage_mode', True if sage_mode else False)]
        if files is not None:
            for filename in files:
                msg.append(('file', open(filename,"rb")))
        request=Request(self.server+EVAL_PATH, msg)
        return encode_request(request)

    def send_execution_request(self, request):
        """
        Send an execution request along with a number of files.

        TODO: break into a "prepare" and "send" function for timing?
        """
        result=urlopen(request).read()
        if result:
            return loads(result)
        else:
            return result
                                    
    def output_poll(self, sequence=0):
        query=urlencode([('computation_id', self.session),
                         ('sequence',sequence)])
        url=self.server+POLL_PATH+'?'+query
        return loads(urlopen(url).read())

    def get_file(self, filename):
        return urlopen(self.server+"%s/%s/%s"%(FILE_PATH,self.session,filename)).read()
        
