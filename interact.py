_INTERACTS={}

def interact(f):
    import inspect
    from uuid import uuid4
    from sys import _sage_messages as MESSAGE
    global _INTERACTS
    (args, varargs, varkw, defaults) = inspect.getargspec(f)
    if defaults is None:
        defaults=[]
    defaults=[InputBox() for _ in range(len(args)-len(defaults))]+list(defaults)
    function_id=uuid4().get_hex()
    _INTERACTS[function_id]=f
    MESSAGE.message('interact_start',
                    {'function_code':'_get_interact_function("%s")'%function_id,
                     'controls':dict(zip(args,[c.message() for c in defaults])),
                     'layout':args})
    f(**dict(zip(args,[c.default() for c in defaults])))
    MESSAGE.message('interact_end',{})

class InteractControl:
    def __init__(self, *args, **kwargs):
        self.args=args
        self.kwargs=kwargs

class InputBox(InteractControl):
    def message(self):
        return {'control_type':'input_box',
                'default':self.kwargs.get('default',None),
                'label':self.kwargs.get('label',None)}
    def default(self):
        return self.kwargs.get('default',None)

def input_box(*args, **kwargs):
    return InputBox(*args, **kwargs)


class Selector(InteractControl):
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.values = self.kwargs.get('values',[0])
        self.default_value = self.kwargs.get('default',0)
    def message(self):
        return {'control_type': 'selector',
                'values': self.values,
                'default': self.default_value,
                'label':self.kwargs.get('label',None)}
    def default(self):
        return self.values[self.default_value]

def selector(*args, **kwargs):
    return Selector(*args, **kwargs)
