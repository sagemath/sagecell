import uuid
import sys
import io

class InteractControl(object):
    control_type = None
    default = None

    def __init__(self, label=None, default=None):
        self.label = label
        if default is not None:
            self.default = default

    def control_dict(self):
        return {"control_type": self.control_type,
                 "label": self.label,
                 "default": self.default}

class InputBox(InteractControl):
    control_type = "input_box"
    default = ""

class InteractStream(io.StringIO):
    def __init__(self, session, pub_socket, name, interact_id, parent_header):
        self.session = session
        self.pub_socket = pub_socket
        self.name = name
        self.interact_id = interact_id
        self.parent_header = parent_header

    def write(self, output):
        msg_id = str(uuid.uuid4())
        msg = {"header": {"msg_id": msg_id,
                          "username": self.session.username,
                          "session": self.session.session,
                          "msg_type": "stream"},
               "msg_id": msg_id,
               "msg_type": "stream",
               "parent_header": self.parent_header,
               "content": {"name": self.name,
                           "data": output,
                           "interact_id": self.interact_id}}  
        self.session.send(self.pub_socket, msg)

def interact_func(session, pub_socket):
    def interact(controls=[], **kwargs):
        def interact_decorator(f):
            msg_id = str(uuid.uuid4())
            interact_id = str(uuid.uuid4())
            cs = controls
            if isinstance(cs, dict):
                cs = cs.items()
            cs.extend(kwargs.items())
            msg = {"header": {"msg_id": msg_id,
                              "username": session.username,
                              "session": session.session,
                              "msg_type": "extension"},
                   "msg_id": msg_id,
                   "msg_type": "extension",
                   "parent_header": getattr(sys.stdout, "parent_header", {}),
                   "content": {"msg_type": "interact_prepare",
                               "content": {"controls": {name: control.control_dict() for name, control in cs},
                                           "interact_id": interact_id}}}
            session.send(pub_socket, msg)
            def adapted_function(*args, **kwargs):
                old_streams = (sys.stdout, sys.stderr)
                sys.stdout = InteractStream(session, pub_socket, "stdout", interact_id, getattr(sys.stdout, "parent_header", {}))
                sys.stderr = InteractStream(session, pub_socket, "stderr", interact_id, getattr(sys.stderr, "parent_header", {}))
                f(*args, **kwargs)
                sys.stdout, sys.stderr = old_streams
            interacts[interact_id] = adapted_function
            adapted_function(**{c[0]: c[1].default for c in cs})
        return interact_decorator
    return interact

classes = {"InputBox": InputBox}

interacts = {}
