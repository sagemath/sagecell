This is an example session that shows the some of the types of messages that may be sent between the client, the server, and the kernel.

The user loads http://sagecell.sagemath.org and types the following computation into the browser:

```python
@interact
def f(x=(1, 1000, 1)):
    print(factor(x))
```

The user then presses the “Evaluate” button. The client (the browser) sends an HTTP `POST` request to `http://sagecell.sagemath.org/kernel`. The following JSON is returned:

```json
{
    "id": "7b3a5b89-7125-4031-b33c-cefd01c8d808",
    "ws_url": "ws://sagecell.sagemath.org/"
}
```

The client establishes a WebSocket connection to the URLs `ws://sagecell.sagemath.org/kernel/7b3a5b89-7125-4031-b33c-cefd01c8d808/iopub` and `ws://sagecell.sagemath.org/kernel/7b3a5b89-7125-4031-b33c-cefd01c8d808/shell`. These WebSocket connections will act as the IPython IOPub and Shell sockets in the communication with the kernel. If WebSockets are not available, a SockJS connection will be created to the URL `http://sagecell.sagemath.org/sockjs`, and all messages will be have the prefix `7b3a5b89-7125-4031-b33c-cefd01c8d808/iopub,` or `7b3a5b89-7125-4031-b33c-cefd01c8d808/shell,`.

The client sends the following message to initiate the computation:

```json
{
    "header": {
        "msg_id": "37B1EF5AB1A14230BC9251C65E3220C9",
        "username": "username",
        "session": "313C08D5FC16438E9C35D48771EC74D7",
        "msg_type": "execute_request"
    },
    "metadata": {},
    "content": {
        "code": "@interact\ndef f(x=(1, 1000, 1)):\n    print(factor(x))",
        "silent": false,
        "user_variables": [],
        "user_expressions": {
            "_sagecell_files": "sys._sage_.new_files()"
        },
        "allow_stdin": false
    },
    "parent_header": {}
}
```

It also sends an HTTP `POST` request to `http://sagecell.sagemath.org/permalink`. The request has a parameter called `message` whose value is

```json
{
    "header": {
        "msg_type": "execute_request"
    },
    "metadata": {},
    "content": {
        "code": "@interact\ndef f(x=(1, 1000, 1)):\n print(factor(x))"
    }
}
```

The response to this request is

```json
{
    "query": "9da718c3-df3d-4e6a-b20a-6a0b9a655ff5",
    "zip": "eJxzyMwrSS1KTC7hSklNU0jTqLDVMNRRMDQwMACSmppWXApAUFAEVKWQBlSVX6RRoQkAjPkOxQ=="
}
```

These values can be used to create the following URLs that serve as permanent links to the computation:

* `http://sagecell.sagemath.org/?q=9da718c3-df3d-4e6a-b20a-6a0b9a655ff5`
* `http://sagecell.sagemath.org/?z=eJxzyMwrSS1KTC7hSklNU0jTqLDVMNRRMDQwMACSmppWXApAUFAEVKWQBlSVX6RRoQkAjPkOxQ==`.

The client now listens on the WebSocket connection for messages from the kernel. The client receives the following messages:

```json
{
    "parent_header": {
        "username": "username",
        "msg_id": "37B1EF5AB1A14230BC9251C65E3220C9",
        "msg_type": "execute_request",
        "session": "313C08D5FC16438E9C35D48771EC74D7"
    },
    "msg_type": "status",
    "msg_id": "de16f9e3-b184-4d31-ba47-34ca0866fa39",
    "content": {
        "execution_state": "busy"
    },
    "header": {
        "username": "kernel",
        "session": "4c12d051-d964-46aa-a635-50bcb3f170ee",
        "msg_id": "de16f9e3-b184-4d31-ba47-34ca0866fa39",
        "msg_type": "status"
    },
    "metadata": {}
}
```

This message tells the client that the kernel is working. When the client receives this message, a spinning icon appears to the user to indicate this status.

```json
{
    "parent_header": {
        "username": "username",
        "msg_id":"37B1EF5AB1A14230BC9251C65E3220C9",
        "msg_type": "execute_request",
        "session": "313C08D5FC16438E9C35D48771EC74D7"
    },
    "msg_type": "pyin",
    "msg_id": "58116112-3d66-4a9f-b35f-18fa6b2ee155",
    "content": {
        "execution_count": 1,
        "code": "@interact\ndef f(x=(1, 1000, 1)):\n    print(factor(x))"
    },
    "header": {
        "username": "kernel",
        "session": "4c12d051-d964-46aa-a635-50bcb3f170ee",
        "msg_id": "58116112-3d66-4a9f-b35f-18fa6b2ee155",
        "msg_type": "pyin"
    },
    "metadata": {}
}
```

The kernel echoes the computation to the client. This message is ignored.

```json
{
    "parent_header": {
        "username": "username",
        "msg_id": "37B1EF5AB1A14230BC9251C65E3220C9",
        "msg_type": "execute_request",
        "session": "313C08D5FC16438E9C35D48771EC74D7"
    },
    "msg_type": "display_data",
    "msg_id": "8b569581-7616-4867-acc0-2d49c6056e28",
    "content": {
        "source": "sagecell",
        "data": {
            "application/sage-interact": {
                "new_interact_id": "cd552fd2-4caa-4f7c-84a4-6d5842e48a3d",
                "layout": {
                    "top_center": [["x"]]
                },
                "update": {
                    "x":["x"]
                },
                "controls": {
                    "x": {
                        "control_type": "slider",
                        "subtype": "continuous",
                        "default": 1.0,
                        "step": 1.0,
                        "label": null,
                        "raw": true,
                        "range": [1.0,1000.0],
                        "display_value": true
                    }
                }
            },
            "text/plain": "Sage Interact"
        }
    },
    "header": {
        "username": "kernel",
        "session": "4c12d051-d964-46aa-a635-50bcb3f170ee",
        "msg_id": "8b569581-7616-4867-acc0-2d49c6056e28",
        "msg_type": "display_data"
    },
    "metadata": {}
}
```

Add an interact to the output of this computation. This interact has a single control (a slider) and an ID with which its output will be identified.

```json
{
    "parent_header": {
        "username": "username",
        "msg_id": "37B1EF5AB1A14230BC9251C65E3220C9",
        "msg_type": "execute_request",
        "session": "313C08D5FC16438E9C35D48771EC74D7"
    },
    "msg_type": "stream",
    "msg_id": "170a0ea4-966d-4fa7-8fdc-bda924f7d776",
    "content": {
        "data": "1\n",
        "name": "stdout"
    },
    "header": {
        "username": "kernel",
        "session": "4c12d051-d964-46aa-a635-50bcb3f170ee",
        "msg_id": "170a0ea4-966d-4fa7-8fdc-bda924f7d776",
        "msg_type": "stream"
    },
    "metadata": {
        "interact_id": "cd552fd2-4caa-4f7c-84a4-6d5842e48a3d"
    }
}
```

Print `1` to the output block associated with the interact with the given ID.

```json
{
    "parent_header": {
        "username": "username",
        "msg_id": "37B1EF5AB1A14230BC9251C65E3220C9",
        "msg_type": "execute_request",
        "session": "313C08D5FC16438E9C35D48771EC74D7"
    },
    "msg_type": "status",
    "msg_id": "68e57f96-537c-410c-a4d4-9b504ce1690b",
    "content": {
        "execution_state": "idle"
    },
    "header": {
        "username": "kernel",
        "session": "4c12d051-d964-46aa-a635-50bcb3f170ee",
        "msg_id": "68e57f96-537c-410c-a4d4-9b504ce1690b",
        "msg_type": "status"
    },
    "metadata": {}
}
```

The kernel has stopped processing. The browser will now hide the spinning icon.

```json
{
    "parent_header": {
                    "username": "username",
                    "msg_id": "37B1EF5AB1A14230BC9251C65E3220C9",
                    "msg_type": "execute_request",
                    "session": "313C08D5FC16438E9C35D48771EC74D7"
    },
    "msg_type": "execute_reply",
    "msg_id": "2a1ef28a-78d6-40e3-8eb8-311ebf79bbe0",
    "content": {
        "status": "ok",
        "execution_count": 1,
        "user_variables": {},
        "payload": [
            {
                            "new_files": []
            }
        ],
        "user_expressions": {
            "_sagecell_files": "''"
        }
    },
    "header": {
        "username": "kernel",
        "session": "4c12d051-d964-46aa-a635-50bcb3f170ee",
        "msg_id": "2a1ef28a-78d6-40e3-8eb8-311ebf79bbe0",
        "msg_type": "execute_reply"
    },
    "metadata": {
        "dependencies_met": true,
        "engine": "9ca1c47b-48c6-4c66-b552-d438067ff2db",
        "status": "ok",
    }
}
```

This message is sent over the Shell channel. It indicates that the computation has completed. If any files were created, they would be reported here.

---

The user has moved the slider to the value 517. The client sends this message over the shell channel:
<pre>
{
    "header": {
        "msg_id": "D90385D5E16445BFA25B18438219F03F",
        "username": "username",
        "session": "313C08D5FC16438E9C35D48771EC74D7",
        "msg_type": "execute_request"
    },
    "metadata": {},
    "content": {
        "code": "sys._sage_.update_interact(\"cd552fd2-4caa-4f7c-84a4-6d5842e48a3d\",{\"x\":517})",
        "silent": false,
        "user_variables": [],
        "user_expressions": {
            "_sagecell_files": "sys._sage_.new_files()"
        },
        "allow_stdin": false
    },
    "parent_header": {}
}
</pre>

The client receives the following message indicating that the kernel is again busy.

```json
{
    "parent_header": {
        "username": "username",
        "msg_id": "D90385D5E16445BFA25B18438219F03F",
        "msg_type": "execute_request",
        "session": "313C08D5FC16438E9C35D48771EC74D7"
    },
    "msg_type": "status",
    "msg_id": "86ed02c3-1c38-42f9-9902-deac5cb34fc6",
    "content": {
        "execution_state": "busy"
    },
    "header": {
        "username": "kernel",
        "session": "4c12d051-d964-46aa-a635-50bcb3f170ee",
        "msg_id": "86ed02c3-1c38-42f9-9902-deac5cb34fc6",
        "msg_type": "status"
    },
    "metadata": {}
}
```

<pre>
{
    "parent_header": {
        "username": "username",
        "msg_id": "D90385D5E16445BFA25B18438219F03F",
        "msg_type": "execute_request",
        "session": "313C08D5FC16438E9C35D48771EC74D7"
    },
    "msg_type": "pyin",
    "msg_id": "611f1bbc-c0c3-4dc2-9d97-ae0c7557366d",
    "content": {
        "execution_count": 2,
        "code": "sys._sage_.update_interact(\"cd552fd2-4caa-4f7c-84a4-6d5842e48a3d\",{\"x\":517})"
    },
    "header": {
        "username": "kernel",
        "session": "4c12d051-d964-46aa-a635-50bcb3f170ee",
        "msg_id": "611f1bbc-c0c3-4dc2-9d97-ae0c7557366d",
        "msg_type": "pyin"
    },
    "metadata": {}
}
</pre>

The kernel echoes the code through the `pyin` stream. Again, this message is ignored.

```json
{
    "parent_header": {
        "username": "username",
        "msg_id": "D90385D5E16445BFA25B18438219F03F",
        "msg_type": "execute_request",
        "session": "313C08D5FC16438E9C35D48771EC74D7"
    },
    "msg_type": "stream",
    "msg_id": "f3997906-85cf-47ef-b72e-ed0d0eb904b0",
    "content": {
        "data": "11 * 47\n",
        "name": "stdout"
    },
    "header": {
        "username": "kernel",
        "session": "4c12d051-d964-46aa-a635-50bcb3f170ee",
        "msg_id": "f3997906-85cf-47ef-b72e-ed0d0eb904b0",
        "msg_type": "stream"
    },
    "metadata": {
        "interact_id": "cd552fd2-4caa-4f7c-84a4-6d5842e48a3d"
    }
}
```

Output `11 * 47` to the output block for this interact.

```json
{
    "parent_header": {
        "username": "username",
        "msg_id": "D90385D5E16445BFA25B18438219F03F",
        "msg_type": "execute_request",
        "session": "313C08D5FC16438E9C35D48771EC74D7"
    },
    "msg_type": "status",
    "msg_id": "76aca188-3bc9-45f1-9322-3bf6fc17e408",
    "content": {
        "execution_state": "idle"
    },
    "header": {
        "username": "kernel",
        "session": "4c12d051-d964-46aa-a635-50bcb3f170ee",
        "msg_id": "76aca188-3bc9-45f1-9322-3bf6fc17e408",
        "msg_type": "status"
    },
    "metadata": {}
}
```

The kernel is now idle.

```json
{
    "parent_header": {
        "username": "username",
        "msg_id": "D90385D5E16445BFA25B18438219F03F",
        "msg_type": "execute_request",
        "session": "313C08D5FC16438E9C35D48771EC74D7"
    },
    "msg_type": "execute_reply",
    "msg_id": "1e1a5cd3-7c39-4efe-b954-422ab80df001",
    "content": {
        "status": "ok",
        "execution_count": 2,
        "user_variables": {},
        "payload": [
            {
                "new_files": []
            }
        ],
        "user_expressions": {
            "_sagecell_files": "''"
        }
    },
    "header": {
        "username": "kernel",
        "session": "4c12d051-d964-46aa-a635-50bcb3f170ee",
        "msg_id": "1e1a5cd3-7c39-4efe-b954-422ab80df001",
        "msg_type": "execute_reply"
    },
    "metadata": {
        "dependencies_met": true,
        "engine": "9ca1c47b-48c6-4c66-b552-d438067ff2db",
        "status": "ok",
    }
}
```

The computation has finished.

```json
{
    "content": {
        "execution_state": "dead"
    },
    "header": {
        "msg_type": "status"
    },
    "parent_header": {},
    "metadata": {}
}
```

After some time, the kernel is killed. This means that no more updates can be sent. (If the “Evaluate” button is pressed again, a new kernel will start.) The client disables the interact controls to indicate this state.
