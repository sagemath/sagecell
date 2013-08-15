import json

class StatsMessage(object):
    def __init__(self, kernel_id, code, execute_type, remote_ip):
        self.msg = [0, remote_ip, kernel_id, execute_type, code]
    def __str__(self):
        return json.dumps(self.msg)
