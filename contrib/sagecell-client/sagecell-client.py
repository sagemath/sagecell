
# Now open two websocket connections with the "ws_url"/kernel/<kernel_id>/iopub for the iopub channel, and <ws_url>/kernel/<kernel_id>/shell for the shell channel.

import time
import websocket
import threading
import json

class SageCell(object):
    def __init__(self, url):
        import requests
        if not url.endswith('/'):
            url+='/'
        # POST or GET <url>/kernel
        r = requests.get(url+'kernel',headers={'Accept': 'application/json'})

        # RESPONSE: {"kernel_id": "ce20fada-f757-45e5-92fa-05e952dd9c87", "ws_url": "ws://localhost:8888/"}
        # construct the iopub and shell websocket channel urls from that

        self.kernel_url = r.json['ws_url']+'kernel/'+r.json['kernel_id']+'/'
        self._shell = websocket.create_connection(self.kernel_url+'shell')
        self._iopub = websocket.create_connection(self.kernel_url+'iopub')

        # initialize our list of messages
        self.shell_messages = []
        self.iopub_messages = []

    def execute_request(self, code):
        # zero out our list of messages, in case this is not the first request
        self.shell_messages = []
        self.iopub_messages = []

        # We use threads so that we can simultaneously get the messages on both channels.
        threads = [threading.Thread(target=self._get_iopub_messages), 
                    threading.Thread(target=self._get_shell_messages)]
        for t in threads:
            t.start()

        # Send the JSON execute_request message string down the shell channel
        msg = self._make_execute_request(code)
        self._shell.send(msg)

        # Wait until we get both a kernel status idle message and an execute_reply message
        for t in threads:
            t.join()

        return [self.shell_messages, self.iopub_messages]

    def _get_shell_messages(self):
        while True:
            msg = json.loads(self._shell.recv())
            self.shell_messages.append(msg)
            # an execute_reply message signifies the computation is done
            if msg['header']['msg_type'] == 'execute_reply':
                break

    def _get_iopub_messages(self):
        while True:
            msg = json.loads(self._iopub.recv())
            self.iopub_messages.append(msg)
            # the kernel status idle message signifies the kernel is done
            if msg['header']['msg_type'] == 'status' and msg['content']['execution_state'] == 'idle':
                break

    def _make_execute_request(self, code):
        from uuid import uuid4
        import json
        session = str(uuid4())

        # Here is the general form for an execute_request message
        execute_request = {'header': {'msg_type': 'execute_request', 'msg_id': str(uuid4()), 'username': '', 'session': session},
                            'parent_header':{},
                            'metadata': {},
                            'content': {'code': code, 'silent': False, 'user_variables': [], 'user_expressions': {'_sagecell_files': 'sys._sage_.new_files()'}, 'allow_stdin': False}}

        return json.dumps(execute_request)

    def close(self):
        # If we define this, we can use the closing() context manager to automatically close the channels
        self._shell.close()
        self._iopub.close()




# Send an execute_request message down the shell channel


# import requests
# r = requests.get('http://localhost:8888/kernel',headers={'Accept': 'application/json'})
# kernel_url = r.json['ws_url']+'kernel/'+r.json['kernel_id']+'/'

# import websocket
# import threading
# import json

############# Using run_forever

# shell_messages = []
# def shell_on_message(ws, message):
#     msg = json.loads(message)
#     if msg['header']['msg_type'] == 'execute_reply':
#         ws.keep_running = False
#     shell_messages.append(msg)
# shell = websocket.WebSocketApp(kernel_url+'shell', on_message = shell_on_message)


# iopub_messages = []
# def iopub_on_message(ws, message):
#     msg = json.loads(message)
#     if msg['header']['msg_type'] == 'status' and msg['content']['execution_state'] == 'idle':
#         ws.keep_running = False
#     iopub_messages.append(msg)
# iopub = websocket.WebSocketApp(kernel_url+'iopub', on_message = iopub_on_message)

# threads=[threading.Thread(target=iopub.run_forever), threading.Thread(target=shell.run_forever)]
# for t in threads:
#     t.start()

# # send message

# for t in threads:
#     t.join()

##################### Using my own looping code
# websocket.enableTrace(True)
# shell_messages = []
# shell = websocket.create_connection(kernel_url+'shell')
# def get_shell_messages():
#     global shell_messages
#     shell_messages = []
#     while True:
#         msg = json.loads(shell.recv())
#         shell_messages.append(msg)
#         if msg['header']['msg_type'] == 'execute_reply':
#             break

# iopub_messages = []
# iopub = websocket.create_connection(kernel_url+'iopub')
# def get_iopub_messages():
#     global iopub_messages
#     iopub_messages = []
#     while True:
#         msg = json.loads(iopub.recv())
#         iopub_messages.append(msg)
#         if msg['header']['msg_type'] == 'status' and msg['content']['execution_state'] == 'idle':
#             break

# threads = [threading.Thread(target=get_iopub_messages), threading.Thread(target=get_shell_messages)]
# for t in threads:
#     t.start()


# code="""1+1"""

# def make_execute_request(code):
#     from uuid import uuid4
#     import json
#     session = str(uuid4())


#     execute_request = {'header': {'msg_type': 'execute_request', 'msg_id': str(uuid4()), 'username': '', 'session': session},
#                         'parent_header':{},
#                         'metadata': {},
#                         'content': {'code': code, 'silent': False, 'user_variables': [], 'user_expressions': {'_sagecell_files': 'sys._sage_.new_files()'}, 'allow_stdin': False}}

#     return json.dumps(execute_request)

# # Send an execute_request message down the shell channel

# shell.send(make_execute_request(code))

# for t in threads:
#     t.join()



# When the kernel dies, you get a special "status" message in the iopub channel