_INTERACTS={}

__single_cell_timeout__=0

def interact(f):
    import inspect
    from uuid import uuid4
    from sys import _sage_messages as MESSAGE
    global _INTERACTS
    
    (args, varargs, varkw, defaults) = inspect.getargspec(f)
    if defaults is None:
        defaults=[]
    n = len(args) - len(defaults)
    
    controls = [automatic_control(defaults[i] if i >= n else None) 
        for (i, arg) in enumerate(args)]
    
    import sys
    function_id=uuid4().get_hex()
    _INTERACTS[function_id]=f
    MESSAGE.message('interact_start',
                    {'function_code':'_get_interact_function("%s")'%function_id,
                     'controls':dict(zip(args,[c.message() for c in controls])),
                     'layout':args})
    global __single_cell_timeout__
    __single_cell_timeout__=60
    f(**dict(zip(args,[c.default() for c in controls])))
    MESSAGE.message('interact_end',{})

class InteractControl:
    def __init__(self, *args, **kwargs):
        self.args=args
        self.kwargs=kwargs

class InputBox(InteractControl):
    def message(self):
        return {'control_type':'input_box',
                'default':self.kwargs.get('default',""),
                'raw':self.kwargs.get('raw',False),
                'label':self.kwargs.get('label',"")}
    def default(self):
        return self.kwargs.get('default',None)

class Selector(InteractControl):
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.values = self.kwargs.get('values',[0])
        self.default_value = self.kwargs.get('default',0)
    def message(self):
        return {'control_type': 'selector',
                'values': self.values,
                'default': self.default_value,
                'raw': self.kwargs.get('raw',False),
                'label':self.kwargs.get('label',"")}
    def default(self):
        return self.values[self.default_value]

class Slider(InteractControl):
    def message(self):
        return {'control_type':'slider',
                'default':self.kwargs.get('default',0),
                'range':self.kwargs.get('range',[0,100]),
                'step':self.kwargs.get('step',1),
                'raw':self.kwargs.get('raw',True),
                'label':self.kwargs.get('label',"")}
    def default(self):
        return self.kwargs.get('default',0)

def automatic_control(default):
    from numbers import Number
    label = ""
    default_value = 0
    
    for _ in range(2):
        if isinstance(default, tuple) and len(default) == 2 and isinstance(default[0], str):
            label, default = default
        if isinstance(default, tuple) and len(default) == 2 and isinstance(default[1], (tuple, list)):
            default_value, default = default
    
    if isinstance(default, str):
        C = input_box(default = default, label = label)
    elif isinstance(default, Number):
        C = input_box(default = default, label = label, raw = True)
    elif isinstance(default, bool):
        C = input_box(default = default, label = label, raw = True)
    elif isinstance(default, list):
        C = selector(default = default_value, label = label, values = default)
    elif isinstance (default, tuple):
        if len(default) == 2:
            C = slider(default = default_value, range = (default[0], default[1]), label = label)
        elif len(default) == 3:
            C = slider(default = default_value, range = (default[0], default[1]), step = default[2], label = label)
        else:
            C = slider(list(default), default = default_value, label = label)
    else:
        C = input_box(default = default, label=label)
    
    return C


# aliases for backwards compatibility
slider=Slider
selector=Selector
input_box=InputBox
