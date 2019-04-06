#! /usr/bin/env python

import client
import time
import random

computation = """@interact
def f(x=(1, 100, 1)):
    print(x^2)"""

class Transaction(object):
    """
    A transaction that simulates loading the page
    and manipulating an interact
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
            s.execute(computation)
            output = ""
            while True:
                msg = s.iopub_recv()
                if msg["header"]["msg_type"] == "status" and msg["content"]["execution_state"] == "idle":
                    break
                elif msg["header"]["msg_type"] == "display_data" and "application/sage-interact" in msg["content"]["data"]:
                    interact_id = msg["content"]["data"]["application/sage-interact"]["new_interact_id"]
                elif msg["header"]["msg_type"] == "stream" and msg["content"]["name"] == "stdout" and msg["metadata"]["interact_id"] == interact_id:
                    output += msg["content"]["data"]
            assert output == "1\n", "Incorrect output: %r" % (output,)
            times = []
            self.custom_timers["initial computation"] = time.time() - t
            for i in xrange(10):
                time.sleep(1)
                num = random.randint(1, 100)
                t = time.time()
                s.update_interact(interact_id, {"x": num})
                output = ""
                while True:
                    msg = s.iopub_recv()
                    if msg["header"]["msg_type"] == "status" and msg["content"]["execution_state"] == "idle":
                        break
                    elif msg["header"]["msg_type"] == "stream" and msg["content"]["name"] == "stdout" and msg["metadata"]["interact_id"] == interact_id:
                        output += msg["content"]["data"]
                assert int(output.strip()) == num * num, "Incorrect output: %r" % (output,)
                times.append(time.time() - t)
            self.custom_timers["interact update (average of 10)"] = sum(times) / len(times)

if __name__ == "__main__":
    t = Transaction()
    t.run()
    print(t.custom_timers)
