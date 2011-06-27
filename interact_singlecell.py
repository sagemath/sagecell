_INTERACTS={}

__single_cell_timeout__=0

from functools import wraps

def decorator_defaults(func):
    """
    This function allows a decorator to have default arguments.

    Normally, a decorator can be called with or without arguments.
    However, the two cases call for different types of return values.
    If a decorator is called with no parentheses, it should be run
    directly on the function.  However, if a decorator is called with
    parentheses (i.e., arguments), then it should return a function
    that is then in turn called with the defined function as an
    argument.

    This decorator allows us to have these default arguments without
    worrying about the return type.

    EXAMPLES::
    
        sage: from sage.misc.decorators import decorator_defaults
        sage: @decorator_defaults
        ... def my_decorator(f,*args,**kwds):
        ...     print kwds
        ...     print args
        ...     print f.__name__
        ...       
        sage: @my_decorator
        ... def my_fun(a,b):
        ...     return a,b
        ...  
        {}
        ()
        my_fun
        sage: @my_decorator(3,4,c=1,d=2)
        ... def my_fun(a,b):
        ...     return a,b
        ...   
        {'c': 1, 'd': 2}
        (3, 4)
        my_fun
    """
    from inspect import isfunction
    @wraps(func)
    def my_wrap(*args,**kwargs):
        if len(kwargs)==0 and len(args)==1 and isfunction(args[0]):
            # call without parentheses
            return func(*args)
        else:
            def _(f):
                return func(f, *args, **kwargs)
            return _
    return my_wrap

@decorator_defaults
def interact(f, controls=[]):
    """
    A decorator that creates an interact.

    Each control can be given as an :class:`.InteractControl` object
    or a value, defined in :func:`.automatic_control`, that will be
    interpreted as the parameters for some control.

    The decorator can be used in several ways::

        @interact([name1, (name2, control2), (name3, control3)])
        def f(**kwargs):
            ...

        @interact
        def f(name1, name2=control2, name3=control3):
            ...


    The two ways can also be combined::

        @interact([name1, (name2, control2)])
        def f(name3, name4=control4, name5=control5):
            ...

    In each example, ``name1``, with no associated control,
    will default to a text box.
    """
    global _INTERACTS

    if isinstance(controls,(list,tuple)):
        controls=list(controls)
        for i,name in enumerate(controls):
            if isinstance(name, str):
                controls[i]=(name, None)
            elif not isinstance(name[0], str):
                raise ValueError("interact control must have a string name, but %s isn't a string"%(name[0],))

    import inspect
    (args, varargs, varkw, defaults) = inspect.getargspec(f)
    if defaults is None:
        defaults=[]
    n=len(args)-len(defaults)
    
    controls=zip(args,[None]*n+list(defaults))+controls

    names=[n for n,_ in controls]
    controls=[automatic_control(c) for _,c in controls]

    from sys import _sage_messages as MESSAGE, maxint
    from random import randrange

    # UUID would be better, but we can't use it because of a
    # bug in Python 2.6 on Mac OS X (http://bugs.python.org/issue8621)
    function_id=str(randrange(maxint))

    def adapted_f(**kwargs):
        MESSAGE.push_output_id(function_id)
        # remap parameters
        for k,v in kwargs.items():
            kwargs[k]=controls[names.index(k)].adapter(v)
        returned=f(**kwargs)
        MESSAGE.pop_output_id()
        return returned

    _INTERACTS[function_id]=adapted_f
    MESSAGE.message_queue.message('interact_prepare',
                                  {'interact_id':function_id,
                                   'controls':dict(zip(names,[c.message() for c in controls])),
                                   'layout':names})
    global __single_cell_timeout__
    __single_cell_timeout__=60
    adapted_f(**dict(zip(names,[c.default() for c in controls])))
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
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.raw = self.kwargs.get('raw',False);
        self.default_value = self.default_return_value = self.kwargs.get('default',"")
        if self.raw:
            self.default_return_value = repr(self.default_value)
    def message(self):
        """
        :returns: Input box control configuration for an interact_prepare message.
        :rtype: Dict
        """
        return {'control_type':'input_box',
                'default':self.default_return_value,
                'width':int(self.kwargs.get('width',0)),
                'raw':self.kwargs.get('raw',False),
                'label':self.kwargs.get('label',"")}
    def default(self):
        """
        :returns: Default value of control.
        """
        return self.default_value

class InputGrid(InteractControl):
    """
    Defines an interact grid control.
    """
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.nrows = self.kwargs.get('nrows',1)
        self.ncols = self.kwargs.get('ncols',1)
        self.default_value = self.kwargs.get('default',0)
        self.raw = self.kwargs.get('raw', True);

        if not isinstance(self.default_value, list):
            self.default_value = self.default_return_value = [[self.default_value for _ in range(self.ncols)] for _ in range(self.nrows)]

        if self.raw:
            self.default_return_value = [[repr(j) for j in i] for i in self.default_value]

    def message(self):
        """
        :returns: Input grid control configuration for an interact_prepare message.
        :rtype: Dict
        """
        return {'control_type': 'input_grid',
                'nrows': int(self.nrows),
                'ncols': int(self.ncols),
                'default': self.default_return_value,
                'width':int(self.kwargs.get('width',0)),
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
        return self.default_value
    def adapter(self, v):
        return self.values[int(v)]

class ContinuousSlider(InteractControl):
    """
    Defines a continues slider interact control.
    """
    def __init__(self, *args, **kwargs):
        self.default_steps = 250
        self.kwargs = kwargs
        self.interval = self.kwargs.get('range',(0,100))
        self.default_value = self.kwargs.get('default',self.interval[0])
        self.steps = self.kwargs.get('steps',self.default_steps)
        self.stepsize = self.kwargs.get('stepsize',0)
        
        if self.default_value > self.interval[1] or self.default_value < self.interval[0]:
            self.default_value = self.interval[0]

        if self.stepsize <= 0:
            if self.steps <= 0:
                self.stepsize = float(self.interval[1] - self.interval[0]) / self.default_steps
            else:
                self.stepsize = float(self.interval[1] - self.interval[0]) / self.steps

    def message(self):
        """
        :returns: Continuous slider control configuration for an interact_prepare message.
        "rtype: Dict
        """
        return {'control_type':'slider',
                'subtype':'continuous',
                'default':float(self.default_value),
                'range':[float(i) for i in self.interval],
                'step':float(self.stepsize),
                'raw':self.kwargs.get('raw',True),
                'label':self.kwargs.get('label',"")}
    def default(self):
        """
        :returns: Default value of control
        """
        return self.default_value

class Slider(InteractControl):
    """
    Defines a slider interact control.
    """
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.values = self.kwargs.get('values',[0,1])
        self.default_value = int(self.kwargs.get('default',0))
        
        if len(self.values) < 2:
            self.values = [0,1]

        if self.default_value > len(self.values):
            self.default_value = 0

    def message(self):
        """
        :returns: Slider control configuration for an interact_prepare message.
        :rtype: Dict
        """
        return {'control_type':'slider',
                'subtype':'value',
                'default':self.default_value,
                'range':[0,len(self.values) - 1],
                'values':[repr(i) for i in self.values],
                'range':[0, len(self.values) - 1],
                'step':int(self.kwargs.get('step',1)),
                'raw':self.kwargs.get('raw',True),
                'label':self.kwargs.get('label',"")}
    def default(self):
        """
        :returns: Default value of control.
        """
        return self.default_value

    def adapter(self, v):
        return self.values[int(v)]

def automatic_control(control):
    """
    Guesses the desired interact control from the syntax of the parameter.
    
    :arg control: Parameter value.
    
    :returns: An InteractControl object.
    :rtype: InteractControl
    
    
    """
    from numbers import Number
    from types import GeneratorType
    label = ""
    default_value = 0
    
    # Checks for interact controls that are verbosely defined
    if isinstance(control, InteractControl):
        return control
    
    # Checks for labels and control values
    for _ in range(2):
        if isinstance(control, tuple) and len(control) == 2 and isinstance(control[0], str):
            label, control = control
        if isinstance(control, tuple) and len(control) == 2 and isinstance(control[1], (tuple, list, GeneratorType)):
            default_value, control = control

    if isinstance(control, str):
        C = input_box(default = control, label = label)
    elif isinstance(control, bool):
        C = checkbox(default = control, label = label, raw = True)
    elif isinstance(control, Number):
        C = input_box(default = control, label = label, raw = True)
    elif isinstance(control, list):
        C = selector(buttons = len(control) <= 5, default = default_value, label = label, values = control, raw = False)
    elif isinstance(control, GeneratorType):
        C = slider(default = default_value, values = list_of_first_n(control,10000), label = label)
    elif isinstance (control, tuple):
        if len(control) == 2:
#            control = [float(i) for i in control]
            C = continuous_slider(default = default_value, range = (control[0], control[1]), label = label)
        elif len(control) == 3:
#            control = [float(i) for i in control]
            C = continuous_slider(default = default_value, range = (control[0], control[1]), stepsize = control[2], label = label)
        else:
            C = slider(default = default_value, values = list(control), label = label)
    else:
        C = input_box(default = control, label=label, raw = True)
    
    return C

def list_of_first_n(v,n):
    """
    Given an iterator v, return the first n elements it produces as a list.
    """
    if not hasattr(v, "next"):
        v = v.__iter__()
    w = []
    while n > 0:
        try:
            w.append(v.next())
        except StopIteration:
            return w
        n -= 1
    return w


# Aliases for backwards compatibility
slider=Slider
selector=Selector
input_box=InputBox
input_grid=InputGrid
checkbox=Checkbox
continuous_slider=ContinuousSlider
