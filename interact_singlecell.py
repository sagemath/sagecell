_INTERACTS={}

__single_cell_timeout__=0

def interact(f):
    """
    Interprets interact functions and their controls and sends interact
    start, interact evaluation, and interact end messages.

    :arg f: A function definition.
    """
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
    """
    Base class for all interact controls.
    """
    def __init__(self, *args, **kwargs):
        self.args=args
        self.kwargs=kwargs

class InputBox(InteractControl):
    """
    Defines an input box control.
    """
    def message(self):
        """
        :returns: Input box control configuration for an interact_start message.
        :rtype: Dict
        """
        return {'control_type':'input_box',
                'default':self.kwargs.get('default',""),
                'raw':self.kwargs.get('raw',False),
                'label':self.kwargs.get('label',"")}
    def default(self):
        """
        :returns: Default value of control.
        """
        return self.kwargs.get('default',None)

class Selector(InteractControl):
    """
    Defines a selector interact control.
    """
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.values = self.kwargs.get('values',[0])
        self.default_value = self.kwargs.get('default',0)
    def message(self):
        """
        :returns: Selector control configuration for an interact_start message.
        :rtype: Dict
        """
        return {'control_type': 'selector',
                'values': self.values,
                'default': self.default_value,
                'raw': self.kwargs.get('raw',False),
                'label':self.kwargs.get('label',"")}
    def default(self):
        """
        :returns: Default value of control.
        """
        return self.values[self.default_value]

class Slider(InteractControl):
    """
    Defines a slider interact control.
    """
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.interval = self.kwargs.get('range',[0,100])
        self.default_value = self.kwargs.get('default',self.interval[0])
    def message(self):
        """
        :returns: Slider control configuration for am interact_start message.
        :rtype: Dict
        """
        return {'control_type':'slider',
                'default':self.default_value,
                'range':self.interval,
                'step':self.kwargs.get('step',1),
                'raw':self.kwargs.get('raw',True),
                'label':self.kwargs.get('label',"")}
    def default(self):
        """
        :returns: Default value of control.
        """
        return self.default_value

def automatic_control(default):
    """
    Guesses the desired interact control from the syntax of the parameter.
    
    :arg default: Parameter value.
    
    :returns: An InteractControl object.
    :rtype: InteractControl
    
    
    """
    from numbers import Number
    label = ""
    default_value = 0
    
    # Checks for interact controls that are verbosely defined
    if isinstance(default, InteractControl):
        return default
    
    # Checks for labels and default values
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


# Aliases for backwards compatibility
slider=Slider
selector=Selector
input_box=InputBox
