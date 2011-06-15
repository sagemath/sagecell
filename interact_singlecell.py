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

    def adapted_f(**kwargs):
        MESSAGE.push_output_id(function_id)
        # remap parameters
        for k,v in kwargs.items():
            kwargs[k]=controls[args.index(k)].adapter(v)
        returned=f(**kwargs)
        MESSAGE.pop_output_id()
        return returned

    _INTERACTS[function_id]=adapted_f
    MESSAGE.message_queue.message('interact_prepare',
                                   {'interact_id':function_id,
                                    'controls':dict(zip(args,[c.message() for c in controls])),
                                    'layout':args})
    global __single_cell_timeout__
    __single_cell_timeout__=60
    adapted_f(**dict(zip(args,[c.default() for c in controls])))
    return f

class InteractControl:
    """
    Base class for all interact controls.
    """
    def __init__(self, *args, **kwargs):
        self.args=args
        self.kwargs=kwargs

    def adapter(self, v):
        return v

class Checkbox(InteractControl):
    """
    Defines a checkbox control.
    """
    def message(self):
        """
        :returns: Checkbox control configuration for an interact_prepare message.
        """
        return {'control_type':'checkbox',
                'default':self.kwargs.get('default',True),
                'raw':self.kwargs.get('raw',True),
                'label':self.kwargs.get('label',"")}
    def default(self):
        """
        :returns: Default value of control.
        :rtype: Dict
        """
        return self.kwargs.get('default',True)

class InputBox(InteractControl):
    """
    Defines an input box control.
    """
    def message(self):
        """
        :returns: Input box control configuration for an interact_prepare message.
        :rtype: Dict
        """
        return {'control_type':'input_box',
                'default':self.kwargs.get('default',""),
                'width':self.kwargs.get('width',""),
                'raw':self.kwargs.get('raw',False),
                'label':self.kwargs.get('label',"")}
    def default(self):
        """
        :returns: Default value of control.
        """
        return self.kwargs.get('default',None)

class InputGrid(InteractControl):
    """
    Defines an interact grid control.
    """
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.nrows = self.kwargs.get('nrows',1)
        self.ncols = self.kwargs.get('ncols',1)
        self.default_value = self.kwargs.get('default',0)
        if not isinstance(self.default_value, list):
            self.default_value = [[self.default_value for _ in range(self.ncols)] for _ in range(self.nrows)]

    def message(self):
        """
        :returns: Input grid control configuration for an interact_prepare message.
        :rtype: Dict
        """
        return {'control_type': 'input_grid',
                'nrows': self.nrows,
                'ncols': self.ncols,
                'default': self.default_value,
                'width':self.kwargs.get('width',""),
                'raw': self.kwargs.get('raw', True),
                'label': self.kwargs.get('label',"")}
    def default(self):
        """
        :returns: Default value of control.
        """
        return self.default_value

class Selector(InteractControl):
    """
    Defines a selector interact control.
    """
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.values = self.kwargs.get('values',[0])
        self.default_value = self.kwargs.get('default',0)
        self.ncols = self.kwargs.get('ncols',None)
        self.nrows = self.kwargs.get('nrows',None)
        self.buttons = self.kwargs.get('buttons',False)
        
        # Assign selector labels and values.
        if len(self.values) > 0 and isinstance(self.values[0], tuple) and len(self.values[0]) == 2:
            self.value_labels = [str(z[1]) if z[1] is not None else str(z[0]) for z in self.values]
            self.values = [z[0] for z in self.values]
        else:
            self.value_labels = [str(z) for z in self.values]
        
        # Ensure that default index is always in the correct range.
        if self.default_value < 0 or self.default_value >= len(self.values):
            self.default_value = 0

        # If using buttons rather than dropdown, check/set rows and columns for layout.
        if self.buttons:
            if self.nrows is None:
                if self.ncols is not None:
                    self.nrows = len(self.values) / self.ncols
                    if self.ncols * self.nrows < len(self.values):
                        self.nrows += 1
                else:
                    self.nrows = 1
            elif self.nrows <= 0:
                    self.nrows = 1

            if self.ncols is None:
                self.ncols = len(self.values) / self.nrows
                if self.ncols * self.nrows < len(self.values):
                    self.ncols += 1

    def message(self):
        """
        :returns: Selector control configuration for an interact_prepare message.
        :rtype: Dict
        """
        return {'control_type': 'selector',
                'values': range(len(self.values)),
                'value_labels': self.value_labels,
                'default': self.default_value,
                'buttons': self.buttons,
                'nrows': self.nrows,
                'ncols': self.ncols,
                'width': self.kwargs.get('width',""),
                'raw': self.kwargs.get('raw',True),
                'label':self.kwargs.get('label',"")}
    def default(self):
        """
        :returns: Default value of control.
        """
        return self.values[self.default_value]
                
    def adapter(self, v):
        return self.values[int(v)]

class Slider(InteractControl):
    """
    Defines a slider interact control.
    """
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.interval = self.kwargs.get('range',(0,100))
        self.default_value = self.kwargs.get('default',self.interval[0])
    def message(self):
        """
        :returns: Slider control configuration for an interact_prepare message.
        :rtype: Dict
        """
        return {'control_type':'slider',
                'default':int(self.default_value),
                'range':[int(i) for i in self.interval],
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
    elif isinstance(default, bool):
        C = checkbox(default = default, label = label, raw = True)
    elif isinstance(default, Number):
        C = input_box(default = default, label = label, raw = True)
    elif isinstance(default, list):
        C = selector(buttons = len(default) <= 5, default = default_value, label = label, values = default, raw = False)
    elif isinstance (default, tuple):
        if len(default) == 2:
            C = slider(default = default[0], range = (default[0], default[1]), label = label)
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
input_grid=InputGrid
checkbox=Checkbox
