=================
 Web Service API
=================

Here is an example of a session with the web service.

We POST to the ``/eval`` URL with these form fields::

  "commands": "1+1"
  "msg_id": "62a64774-7834-46b3-a9cc-63cb19d44ab8"
  "sage_mod": on

You can make up your own ``msg_id``.  It will be returned in the parent_header JSON dicts below.

We get back this response::

    {"session_id": "ba4a022c-c346-4e7d-83f7-9e8486dacf7a",
    "codeurl": "http://aleph.sagemath.org/?c=1%2B1",
    "zipurl": "http://aleph.sagemath.org/?z=eJwz1DYEAAEdAI4%3D",
    "queryurl": "http://aleph.sagemath.org/?q=57278e13-cd10-4340-b2a0-71d1d0adebd2"}

Now we make a GET request to ``/output_poll?computation_id=ba4a022c-c346-4e7d-83f7-9e8486dacf7a&sequence=0&rand=0.16124823689460754``

The ``rand`` is there to make sure that no caching happens; it isn't used on the server.

We receive back this JSON dictionary::

  {
  "content": [
    {
      "header": {
        "msg_id": "2549680186731169168"
      }
      "parent_header": {
        "username": "",
        "msg_id": "62a64774-7834-46b3-a9cc-63cb19d44ab8",
        "session": "ba4a022c-c346-4e7d-83f7-9e8486dacf7a"
      },
      "msg_type": "pyout",
      "sequence": 0,
      "output_block": null,
      "content": {
        "data": {
          "text/plain": "2"
        }
      },
    },
    {
      "header": {
        "msg_id": "7875127234914760589"
      }
      "parent_header": {
        "username": "",
        "msg_id": "62a64774-7834-46b3-a9cc-63cb19d44ab8",
        "session": "ba4a022c-c346-4e7d-83f7-9e8486dacf7a"
      },
      "msg_type": "execute_reply",
      "sequence": 1,
      "output_block": null,
      "content": {
        "status": "ok"
      },
    },
    {
      "header": {
        "msg_id": "2e28834f-323c-44f7-bd1c-ec61800d5a9e"
      }
      "parent_header": {
        "username": "",
        "msg_id": "62a64774-7834-46b3-a9cc-63cb19d44ab8",
        "session": "ba4a022c-c346-4e7d-83f7-9e8486dacf7a"
      },
      "msg_type": "extension",
      "sequence": 2,
      "output_block": null,
      "content": {
        "msg_type": "session_end"
      },
    }
  ]}
