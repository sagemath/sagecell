import uuid
import sys
import io

class InteractControl(object):
    def control_dict(self):
        raise NotImplementedError

class InputBox(InteractControl):
    def __init__(self, default=u"", label=None):
        self.default = default
        self.label = label

    def control_dict(self):
        return {"control_type": "input_box",
                 "label": self.label,
                 "default": self.default}

class Slider(InteractControl):
    def __init__(self, min, max, step=1, default=None, label=None):
        self.min = min
        self.max = max
        self.step = step
        self.default = default if default is not None else min
        self.label = label

    def control_dict(self):
        return {"control_type": "slider",
                 "label": self.label,
                 "default": self.default,
                 "min": self.min,
                 "max": self.max,
                 "step": self.step}

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
    def interact(controls=None, **kwargs):
        if controls is None:
            controls = []
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
                               "content": {"controls": [(name, control.control_dict()) for name, control in cs],
                                           "new_interact_id": interact_id}}}
            if hasattr(sys.stdout, "interact_id"):
                msg["content"]["interact_id"] = sys.stdout.interact_id
            session.send(pub_socket, msg)
            def adapted_function(**kwargs):
                old_streams = (sys.stdout, sys.stderr)
                sys.stdout = InteractStream(session, pub_socket, "stdout", interact_id, getattr(sys.stdout, "parent_header", {}))
                sys.stderr = InteractStream(session, pub_socket, "stderr", interact_id, getattr(sys.stderr, "parent_header", {}))
                f(**kwargs)
                sys.stdout, sys.stderr = old_streams
            interacts[interact_id] = adapted_function
            adapted_function(**dict([(name,control.default) for name, control in cs]))
        return interact_decorator
    return interact

classes = {"InputBox": InputBox, "Slider": Slider}
interacts = {}
