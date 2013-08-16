import json

LOG_VERSION=0

class StatsMessage(object):
    def __init__(self, kernel_id, code, execute_type, remote_ip, referer):
        self.msg = [LOG_VERSION, remote_ip, referer, execute_type, kernel_id, code]
    def __str__(self):
        return json.dumps(self.msg)
