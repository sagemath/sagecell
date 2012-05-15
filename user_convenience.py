r"""
User code can interact with the device through a module of convenience functions named
``_sagecell`` that is automatically present in the user namespace.

The user convenience module contains functions for user code to interact with the device
process. Current functionality includes:

* Uploading files
* Displaying files
* Sending arbitrary message types
"""

import json

class UserConvenience(object):
    """
    User convenience module containing convenience functions
    
    :arg output_handler: context wrapper that sends IPython-style messages in a queue to the client
    :arg upload_send: Connection object that is one end of a Pipe used by the device to send and receive files
    """
    def __init__(self, output_handler, upload_send):
        self.output_handler = output_handler
        self.upload_send = upload_send

    def display_file(self, filename):
        """
        Uploads and displays a file in the working directory

        :arg str filename: The name of the file to be displayed
        """
        self.upload_file(filename)
        self.output_handler.message_queue.display({'text/filename':filename})

    def send_message(self, message_type, content_dict):
        """
        Sends an arbitrary message back to the client

        :arg str message_type: Message type
        :arg content_dict: JSON-like dictionary containing message content
        """
        self.output_handler.message_queue.raw_message(message_type, content_dict)

    def upload_file(self,filename):
        """
        Upload a file in the working directory

        :arg str filename: The name of the file to be uploaded
        """
        self.upload_send.send_bytes(json.dumps([filename]))
        self.upload_send.recv_bytes() # blocks until upload is finished
