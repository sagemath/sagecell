#! /usr/bin/env python

import client
import time
import random

class Transaction(object):
    """
    A transaction that simulates loading the page
    and performing a simple addition
    """

    def __init__(self):
        self.custom_timers = {}

    def run(self):
        t  = time.time()
        client.load_root()
        self.custom_timers["root load"] = time.time() - t
        time.sleep(5)
        t = time.time()
        with client.SageCellSession() as s:
            self.custom_timers["initial connection"] = time.time() - t
            t = time.time()
            num1 = random.randint(1, 10 ** 20)
            num2 = random.randint(1, 10 ** 20)
            s.execute("print %d + %d" % (num1, num2))
            output = ""
            while True:
                msg = s.iopub_recv()
                if msg["msg_type"] == "status" and msg["content"]["execution_state"] == "idle":
                    break
                elif msg["msg_type"] == "stream" and msg["content"]["name"] == "stdout":
                    output += msg["content"]["data"]
            assert int(output.strip()) == num1 + num2, "Incorrect output: %r" % (output,)
        self.custom_timers["computation"] = time.time() - t

if __name__ == "__main__":
    t = Transaction()
    t.run()
    print t.custom_timers
