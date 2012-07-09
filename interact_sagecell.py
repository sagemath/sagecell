"""
Interacts

The camelcase controls (like Selector or ButtonBar) have experimental APIs and may change.  The stable API is still the backwards-compatible API.

Examples
--------


Radio button example::

    @interact
    def f(n = Selector(values=["Option1","Option2"], selector_type="radio", label=" ")):
        print n


Push button example::

    result = 0
    @interact
    def f(n = Button(text="Increment", default=0, value=1, width="10em", label=" ")):
        global result
        result = result + n
        print "Result: ", result


Button bar example::

    result = 0
    @interact
    def f(n = ButtonBar(values=[(1,"Increment"),(-1,"Decrement")], default=0, width="10em", label=" ")):
        global result
        result = result + n
        print "Result: ", result

Multislider example::

    sliders = 5
    interval = [(0,10)]*sliders
    default = [3]*sliders
    @interact
    def f(n = MultiSlider(sliders = sliders, interval = interval, default = default), c = (1,100)):
        print "Sum of cn for all n: %s"%float(sum(c * i for i in n))

Nested interacts::

    @interact
    def f(n=(0,10,1)):
        print n
        @interact
        def transformation(c=(0,n)):
            print c


Nested interacts where the number of controls is changed::

    @interact
    def f(n=(0,10)):
        @interact(controls=[('x%d'%i, (0,10)) for i in range(n)])
        def s(multiplier=2, **kwargs):
            print sum(kwargs.values())*multiplier


Recursively nested interact::

    c=1
    @interact
    def f(n=(0,10)):
        global c
        c+=1
        print 'f evaluated %d times'%c
        for i in range(n):
            interact(f)
"""

import uuid
import sys
from misc import session_metadata, decorator_defaults

__interacts={}

def update_interact(interact_id, control_vals):
    interact_info = __interacts[interact_id]
    kwargs = interact_info["state"].copy()
    controls = interact_info["controls"]
    for var,value in control_vals.items():
        c = controls[var]
        kwargs[var] = c.adapter(value, interact_info["globals"])
        if c.preserve_state:
            interact_info["state"][var]=kwargs[var]
    __interacts[interact_id]["function"](control_vals=kwargs)


def interact_func(session, pub_socket):
    """
    Create a function to be used as ``interact`` in the user namespace,
    with the correct session and socket objects.

    :arg IPython.zmq.session.Session session: an IPython session
    :arg zmq.Socket pub_socket: the \xd8MQ PUB socket used for the IOPUB stream
    :returns: the ``interact`` function
    :rtype: function
    """

    @decorator_defaults
    def interact(f, controls=[], update=None, layout=None):
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
            def f(name3, name4=control4, name5=control5, **kwargs):
                ...

        In each example, ``name1``, with no associated control,
        will default to a text box.

        :arg function f: the function to make into an interact
        :arg list controls: a list of tuples of the form ``("name",control)``
        :returns: the original function
        :rtype: function
        """

        if update is None: update = {}
        if layout is None: layout = {}

        if isinstance(controls,(list,tuple)):
            controls=list(controls)
            for i,name in enumerate(controls):
                if isinstance(name, str):
                    controls[i]=(name, None)
                elif not isinstance(name[0], str):
                    raise ValueError("interact control must have a string name, but %r isn't a string"%(name[0],))
        names = {c[0] for c in controls}

        import inspect
        (args, varargs, varkw, defaults) = inspect.getargspec(f)
        if len(names) != len(controls) or any(a in names for a in args):
            raise ValueError("duplicate argument in interact definition")
        if defaults is None:
            defaults=[]
        n=len(args)-len(defaults)
        controls = zip(args, [None] * n + list(defaults)) + controls
        names=[n for n,_ in controls]
        controls=[automatic_control(c, var=n) for n,c in controls]
        nameset = set(names)

        for n,c in zip(names, controls):
            # Check for update button controls
            if isinstance(c, UpdateButton):
                update[n] = c.boundVars()

        if update:
            # sanitize input
            for key,value in update.items():
                # note: we are modifying the dictionary below, so we want
                # to get all the items first
                if key not in nameset:
                    # Test if the updating variable is defined
                    raise ValueError("%s is not an interacted variable."%repr(change))
                # make the values unique, and make sure the control updates itself
                value = set(value)
                value.add(key)
                if "*" in value:
                    # include all controls
                    value = nameset
                elif value-nameset:
                    raise ValueError("Update variables %s are not interact variables."%repr(list(value-nameset)))
                update[key]=list(value)
        else:
            update = dict((n,[n]) for n in names)

        if isinstance(layout, (list, tuple)):
            layout = {'top_center': layout}

        if layout:
            # sanitize input
            layout_values = set(["top_left","top_right","top_center","right","left","bottom_left","bottom_right","bottom_center", "top", "bottom"])
            sanitized_layout = {}
            previous_vars = []

            for key,value in layout.items():
                error_vars = []

                if key in layout_values:
                    if key in ("top", "bottom"):
                        oldkey=key
                        key+="_center"
                        if key in layout:
                            raise ValueError("Cannot have both %s and %s specified"%(oldkey,key))
                else:
                    raise ValueError("%s is an incorrect layout key. Possible options are %s"%(repr(k), layout_values))
                if not isinstance(value[0], (list, tuple)):
                    value = [value]
            
                if ["*"] in value:
                    value = [[n] for n in names]
                elif set(flatten(value))-nameset:
                    raise ValueError("Layout variables %s are not interact variables."%repr(list(set(flatten(value))-nameset)))
                for varlist in value:
                    for var in varlist:
                        if var in previous_vars:
                            error_vars.append(var);
                    if error_vars:
                        raise ValueError("Layout variables %s are repeated in '%s'."%(repr(error_vars),key))
                    previous_vars.extend(varlist)
                sanitized_layout[key] = value
                layout = sanitized_layout
        else:
            layout["top_center"] = [[n] for n in names]

        interact_id=str(uuid.uuid4())
        msg = {"application/sage-interact": {"new_interact_id": interact_id,
                                             "controls": dict(zip(names, (control.message() for control in controls))),
                                             "layout": layout,
                                             "update": update},
               "text/plain": "Sage Interact"}
        sys._sage_.display_message(msg)
        sys._sage_.kernel_timeout = float("inf")
        def adapted_f(control_vals):
            with session_metadata({'interact_id': interact_id}):
                returned=f(**control_vals)
            return returned
        # update global __interacts
        __interacts[interact_id] = {"function": adapted_f,
                                  "controls": dict(zip(names, controls)),
                                  "state": dict(zip(names,[c.adapter(c.default, f.func_globals) for c in controls])),
                                  "globals": f.func_globals}
        adapted_f(__interacts[interact_id]["state"].copy())
        return f
    return interact

def safe_sage_eval(code, globs):
    """
    Evaluate an expression using sage_eval,
    returning an ``Exception`` object if an exception occurs

    :arg str code: the expression to evaluate
    :arg dict globs: the global dictionary in which to evaluate the expression
    :returns: the value of the expression. If an exception occurs, the
    ``Exception`` object is returned instead.
    """
    try:
        try:
            from sage.all import sage_eval
            return sage_eval(code, globs)
        except ImportError:
            return eval(code, globs)
    except Exception as e:
        return e

class InteractControl(object):
    """
    Base class for all interact controls.
    """

    preserve_state = True

    def __init__(self, *args, **kwargs):
        self.args=args
        self.kwargs=kwargs

    def adapter(self, v, globs):
        """
        Get the value of the interact in a form that can be passed to
        the inner function

        We pass in a global variable dictionary ``globs`` so that the
        arguments can be evaluated in context of the current global
        environment. This is necessary since the arguments are being evaluated
        in a totally different context from the rest of the function.

        :arg v: a value as passed from the client
        :dict globs: the global variables in which to evaluate things
        :returns: the interpretation of that value in the context of
            this control (by default, the value is not changed)
        """
        return v

    def message(self):
        """
        Get a control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        raise NotImplementedError

class Checkbox(InteractControl):
    """
    A checkbox control

    :arg bool default: ``True`` if the checkbox is checked by default
    :arg bool raw: ``True`` if the value should be treated as "unquoted"
        (raw), so it can be used in control structures. There are few
        conceivable situations in which raw should be set to ``False``,
        but it is available.
    :arg str label: the label of the control, ``""`` for no label, and
        a default value (None) of the control's variable.
    """
    def __init__(self, default=True, label=None, raw=True):
        self.default=default
        self.raw=raw
        self.label=label

    def message(self):
        """
        Get a checkbox control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        return {'control_type':'checkbox',
                'default':self.default,
                'raw':self.raw,
                'label':self.label}

class InputBox(InteractControl):
    """
    An input box control

    :arg default: default value of the input box.  If this is not a string, repr is
        called on it to get a string, which is then the default input.
    :arg int width: character width of the input box.
    :arg int height: character height of the input box. If this is greater than
        one, an HTML textarea will be rendered, while if it is less than one,
        an input box form element will be rendered.
    :arg str label: the label of the control, ``""`` for no label, and
        a default value (None) of the control's variable.
    :arg bool keypress: update the value of the interact when the user presses
        any key, rather than when the user presses Enter or unfocuses the textbox
    """
    def __init__(self, default=u"", label=None, width=0, height=1, keypress=True):
        if not isinstance(default, basestring):
            default = repr(default)
        self.default=default
        self.width=int(width)
        self.height=int(height)
        self.keypress = keypress
        self.label=label
        if self.height > 1:
            self.subtype = "textarea"
        else:
            self.subtype = "input"

    def message(self):
        """
        Get an input box control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        return {'control_type':'input_box',
                'subtype':self.subtype,
                'default':self.default,
                'width':self.width,
                'height':self.height,
                'evaluate': False,
                'keypress': self.keypress,
                'label':self.label}

class ExpressionBox(InputBox):
    """
    An ``InputBox`` whose value is the result of evaluating its contents with Sage
    :arg default: default value of the input box.  If this is not a string, repr is
        called on it to get a string, which is then the default input.
    :arg int width: character width of the input box.
    :arg int height: character height of the input box. If this is greater than
        one, an HTML textarea will be rendered, while if it is less than one,
        an input box form element will be rendered.
    :arg str label: the label of the control, ``""`` for no label, and
        a default value (None) of the control's variable.
    :arg adapter: a callable which will be passed the input before
        sending it into the function.  This might ensure that the
        input to the function is of a specific type, for example.  The
        function should take as input the value of the control and
        should return something that is then passed into the interact
        function as the value of the control.
    """
    def __init__(self, default=u"", label=None, width=0, height=1, adapter=None):
        super(ExpressionBox, self).__init__(default, label, width, height)
        if adapter is not None:
            self.adapter = lambda x, globs: adapter(safe_sage_eval(x, globs), globs)
        else:
            self.adapter = lambda x, globs: safe_sage_eval(x, globs)

    def message(self):
        """
        Get an input box control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        return {"control_type": "input_box",
                "subtype": self.subtype,
                "default": self.default,
                "width": self.width,
                "height": self.height,
                "evaluate": True,
                "keypress": False,
                "label": self.label}

class InputGrid(InteractControl):
    """
    An input grid control

    :arg int nrows: number of rows in the grid
    :arg int ncols: number of columns in the grid
    :arg default: default values of the control. A multi-dimensional
        list specifies the values of individual inputs; a single value
        sets the same value to all inputs
    :arg adapter: a callable which will be passed the input before
        sending it into the function.  This might ensure that the
        input to the function is of a specific type, for example.  The
        function should take as input a list of lists (the value
        of the control), as well as the globals.
    :arg int width: character width of each input box
    :arg str label: the label of the control, ``""`` for no label, and
        a default value (None) of the control's variable.
    :arg element_adapter: a callable which takes an element value and the globs
        and returns an adapter element.  A nested list of these adapted elements
        is what is given to the adapter function.
    :arg evaluate: whether or not the strings returned from the front end
        are first sage_eval'd (default: ``True``).
    """
    def __init__(self, nrows=1, ncols=1, default=u'0', adapter=None, width=0, label=None,
                 element_adapter=None, evaluate=True):
        self.nrows = int(nrows)
        self.ncols = int(ncols)
        self.width = int(width)
        self.label = label
        self.evaluate = evaluate
        if self.evaluate:
            if element_adapter is not None:
                self.element_adapter = lambda x,globs: element_adapter(safe_sage_eval(x,globs), globs)
            else:
                self.element_adapter = lambda x,globs: safe_sage_eval(x,globs)
        else:
            if element_adapter is not None:
                self.element_adapter = lambda x,globs: element_adapter(x,globs)
            else:
                self.element_adapter = lambda x,globs: x

        if adapter is None:
            self.adapter = lambda x,globs: [[self.element_adapter(i,globs) for i in xi] for xi in x]
        else:
            self.adapter = lambda x,globs: adapter([[self.element_adapter(i,globs) for i in xi] for xi in x],globs)

        def makestring(x):
            if isinstance(x, basestring):
                return x
            else:
                return repr(x)

        if not isinstance(default, list):
            self.default = [[makestring(default) for _ in range(self.ncols)] for _ in range(self.nrows)]
        # Allows 1-row input grids to use non-nested lists for default values
        elif not all(isinstance(entry, (list,tuple)) for entry in default):
            # the above test will exhaust an iterator...
            self.default = [[makestring(default[i * self.ncols + j]) for j in range(self.ncols)] for i in range(self.nrows)]
        else:
            self.default = [[makestring(default[r][c]) for c in range(self.ncols)] for r in range(self.nrows)]

    def message(self):
        """
        Get an input grid control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        return {'control_type': 'input_grid',
                'nrows': self.nrows,
                'ncols': self.ncols,
                'default': self.default,
                'width':self.width,
                'raw': True,
                'evaluate': self.evaluate,
                'label': self.label}

class Selector(InteractControl):
    """
    A selector interact control

    :arg int default: initially selected item in the list of values
    :arg list values: list of values from which the user can select. A value can
        also be represented as a tuple of the form ``(value, label)``, where the
        value is the name of the variable and the label is the text displayed to
        the user.
    :arg string selector_type: Type of selector. Currently supported options
        are "button" (Buttons), "radio" (Radio buttons), and "list"
        (Dropdown list), with "list" being the default. If "list" is used,
        ``ncols`` and ``nrows`` will be ignored. If "radio" is used, ``width``
        will be ignored.
    :arg int ncols: number of columns of selectable objects. If this is given,
        it must cleanly divide the number of objects, else this value will be
        set to the number of objects and ``nrows`` will be set to 1.
    :arg int nrows: number of rows of selectable objects. If this is given, it
        must cleanly divide the number of objects, else this value will be set
        to 1 and ``ncols`` will be set to the number of objects. If both
        ``ncols`` and ``nrows`` are given, ``nrows * ncols`` must equal the
        number of objects, else ``nrows`` will be set to 1 and ``ncols`` will
        be set to the number of objects.
    :arg string width: CSS width of each button. This should be specified in
        px or em.
    :arg str label: the label of the control, ``""`` for no label, and
        a default value (None) of the control's variable.
    """

    def __init__(self, values, default=None, selector_type="list", nrows=None, ncols=None, width="", label=None):
        self.values=values[:]
        self.selector_type=selector_type
        self.nrows=nrows
        self.ncols=ncols
        self.width=str(width)
        self.label=label

        if self.selector_type != "button" and self.selector_type != "radio":
            self.selector_type = "list"
        
        # Assign selector labels and values.
        self.value_labels=[str(v[1]) if isinstance(v,tuple) and
                           len(v)==2 else str(v) for v in values]
        self.values = [v[0] if isinstance(v,tuple) and
                       len(v)==2 else v for v in values]
        self.default = default_to_index(self.values, default)
        # If not using a dropdown list,
        # check/set rows and columns for layout.
        if self.selector_type != "list":
            if self.nrows is None and self.ncols is None:
                self.nrows = 1
                self.ncols = len(self.values)
            elif self.nrows is None:
                self.ncols = int(self.ncols)
                if self.ncols <= 0:
                    self.ncols = len(values)
                self.nrows = int(len(self.values) / self.ncols)
                if self.ncols * self.nrows < len(self.values):
                    self.nrows = 1
                    self.ncols = len(self.values)
            elif self.ncols is None:
                self.nrows = int(self.nrows)
                if self.nrows <= 0:
                    self.nrows = 1
                self.ncols = int(len(self.values) / self.nrows)
                if self.ncols * self.nrows < len(self.values):
                    self.nrows = 1
                    self.ncols = len(self.values)
            else:
                self.ncols = int(self.ncols)
                self.nrows = int(self.nrows)
                if self.ncols * self.nrows != len(self.values):
                    self.nrows = 1
                    self.ncols = len(self.values)

    def message(self):
        """
        Get a selector control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        return {'control_type': 'selector',
                'subtype': self.selector_type,
                'values': len(self.values),
                'value_labels': self.value_labels,
                'default': self.default,
                'nrows': int(self.nrows) if self.nrows is not None else None,
                'ncols': int(self.ncols) if self.ncols is not None else None,
                'raw': True,
                'width': self.width,
                'label':self.label}
                
    def adapter(self, v, globs):
        return self.values[int(v)]

class DiscreteSlider(InteractControl):
    """
    A discrete slider interact control.

    The slider value correlates with the index of an array of values.

    :arg int default: initial value (index) of the slider; if ``None``, the
        slider defaults to the 0th index.  The default will be the
        closest values to this parameter.
    :arg list values: list of values to which the slider position refers.
    :arg bool range_slider: toggles whether the slider should select
        one value (False, default) or a range of values (True).
    :arg bool display_value: toggles whether the slider value sould be displayed (default = True)
    :arg str label: the label of the control, ``""`` for no label, and
        a default value (None) of the control's variable.
    """

    def __init__(self, values=[0,1], default=None, range_slider=False, display_value=True, label=None):
        from types import GeneratorType

        if isinstance(values, GeneratorType):
            self.values = take(10000, values)
        else:
            self.values = values[:]

        if len(self.values) < 2:
            self.values = [0,1]

        self.range_slider = range_slider
        self.display_value = display_value
        
        if self.range_slider:
            self.subtype = "discrete_range"
            if default is None:
                self.default = (0,len(values)-1)
            else:
                self.default=tuple(default_to_index(self.values, d)
                                   for d in default)
        else:
            self.subtype = "discrete"
            self.default = default_to_index(self.values,
                                            default)

        self.label=label

    def message(self):
        """
        Get a discrete slider control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        return {'control_type':'slider',
                'subtype':self.subtype,
                'display_value':self.display_value,
                'default':self.default,
                'range':[0, len(self.values)-1],
                'values':[repr(i) for i in self.values],
                'step':1,
                'raw':True,
                'label':self.label}
    def adapter(self,v, globs):
        if self.range_slider:
            return tuple(self.values[int(i)] for i in v)
        else:
            return self.values[int(v)]

class ContinuousSlider(InteractControl):
    """
    A continuous slider interact control.

    The slider value moves between a range of numbers.

    :arg int default: initial value of the slider; if ``None``, the
        slider defaults to its minimum
    :arg tuple interval: range of the slider, in the form ``(min, max)``
    :arg int steps: number of steps the slider should have between min and max
    :arg Number stepsize: size of step for the slider. If both step and stepsize are specified, stepsize takes precedence so long as it is valid.
    :arg bool range_slider: toggles whether the slider should select one value (default = False) or a range of values (True).
    :arg bool display_value: toggles whether the slider value sould be displayed (default = True)
    :arg str label: the label of the control, ``""`` for no label, and
        a default value (None) of the control's variable.
    
    Note that while "number of steps" and/or "stepsize" can be specified for the slider, this is to enable snapping, rather than a restriction on the slider's values. The only restrictions placed on the values of the slider are the endpoints of its range.
    """

    def __init__(self, interval=(0,100), default=None, steps=250, stepsize=0, label=None, range_slider=False, display_value=True):
        self.range_slider = range_slider
        self.display_value = display_value
        self.interval = interval if interval[0] < interval[1] and len(interval) == 2 else (0,100)
        
        if self.range_slider:
            self.subtype = "continuous_range"
            self.default = default if default is not None and len(default) == 2 else (self.interval[0], self.interval[1])
            for i in range(2):
                if not (self.interval[0] <= self.default[i] <= self.interval[1]):
                    self.default[i] = self.interval[i]
            self.default_return = [float(i) for i in self.default]
        else:
            self.subtype = "continuous"
            self.default = default if default is not None and self.interval[0] <= default <= self.interval[1] else self.interval[0]
            self.default_return = float(self.default)

        self.steps = int(steps) if steps > 0 else 250
        self.stepsize = float(stepsize if stepsize > 0 and stepsize <= self.interval[1] - self.interval[0] else float(self.interval[1] - self.interval[0]) / self.steps)
        self.label = label

    def message(self):
        """
        Get a continuous slider control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        return {'control_type':'slider',
                'subtype':self.subtype,
                'display_value':self.display_value,
                'default':self.default_return,
                'step':self.stepsize,
                'range':[float(i) for i in self.interval],
                'raw':True,
                'label':self.label}

class MultiSlider(InteractControl):
    """
    A multiple-slider interact control.

    Defines a bank of vertical sliders (either discrete or continuous sliders, but not both in the same control).

    :arg string slider_type: type of sliders to generate. Currently, only "continuous" and "discrete" are valid, and other input defaults to "continuous."
    :arg int sliders: Number of sliders to generate
    :arg list default: Default value of each slider. The length of the list should be equivalent to the number of sliders, but if all sliders are to have the same default value, the list only needs to contain that one value.
    :arg list values: Values for each value slider in a multi-dimensional list for the form [[slider_1_val_1..slider_1_val_n], ... ,[slider_n_val_1, .. ,slider_n_val_n]]. The length of the first dimension of the list should be equivalent to the number of sliders, but if all sliders are to iterate through the same values, the list only needs to contain that one list of values.
    :arg list interval: Intervals for each continuous slider in a list of tuples of the form [(min_1, max_1), ... ,(min_n, max_n)]. This parameter cannot be set if value sliders are specified. The length of the first dimension of the list should be equivalent to the number of sliders, but if all sliders are to have the same interval, the list only needs to contain that one tuple.
    :arg list stepsize: List of numbers representing the stepsize for each continuous slider. The length of the list should be equivalent to the number of sliders, but if all sliders are to have the same stepsize, the list only needs to contain that one value.
    :arg list steps: List of numbers representing the number of steps for each continuous slider. Note that (as in the case of the regular continuous slider), specifying a valid stepsize will always take precedence over any specification of number of steps, valid or not. The length of this list should be equivalent to the number of sliders, but if all sliders are to have the same number of steps, the list only neesd to contain that one value.
    :arg bool display_values: toggles whether the slider values sould be displayed (default = True)
    :arg str label: the label of the control, ``""`` for no label, and
        a default value (None) of the control's variable.
    """

    def __init__(self, sliders=1, values=[[0,1]], interval=[(0,1)], slider_type="continuous",  default=[0], stepsize=[0], steps=[250], display_values=True, label=None):
        from types import GeneratorType

        self.slider_type = slider_type
        self.display_values = display_values

        self.sliders = int(sliders) if sliders > 0 else 1
        self.slider_range = range(self.sliders)
        
        if self.slider_type == "discrete":
            self.stepsize = 1

            if len(values) == self.sliders:
                self.values = values[:]
            elif len(values) == 1 and len(values[0]) >= 2:
                self.values = [values[0]] * self.sliders
            else:
                self.values = [[0,1]] * self.sliders

            self.values = [i if not isinstance(i, GeneratorType) else take(10000, i) for i in self.values]

            self.interval = [(0, len(self.values[i])-1) for i in self.slider_range]

            # TODO: make sure default specifies a value, not an index into self.values; use default_to_index
            if len(default) == self.sliders:
                self.default = [default_to_index(self.values, default[i]) for i in default]
            elif len(default) == 1:
                self.default = [default_to_index(self.values, default[0]) for i in self.slider_range]
            else:
                self.default = [0] * self.sliders

        else:
            self.slider_type = "continuous"

            if len(interval) == self.sliders:
                self.interval = interval[:]
            elif len(interval) == 1 and len(interval[0]) == 2:
                self.interval = [interval[0]] * self.sliders
            else:
                self.interval = [(0,1) for i in self.slider_range]

            for i in self.slider_range:
                if not len(self.interval[i]) == 2 or self.interval[i][0] > self.interval[i]:
                    self.interval[i] = (0,1)
                else:
                    self.interval[i] = [float(j) for j in self.interval[i]]

            if len(default) == self.sliders:
                self.default = [default[i] if default[i] > self.interval[i][0] and default[i] < self.interval[i][1] else self.interval[i][0] for i in self.slider_range]
            elif len(default) == 1:
                self.default = [default[0] if default[0] > self.interval[i][0] and default[0] < self.interval[i][1] else self.interval[i][0] for i in self.slider_range]
            else:
                self.default = [self.interval[i][0] for i in self.slider_range]

            self.default_return = [float(i) for i in self.default]

            if len(steps) == 1:
                self.steps = [steps[0]] * self.sliders if steps[0] > 0 else [250] * self.sliders
            else:
                self.steps = [int(i) if i > 0 else 250 for i in steps] if len(steps) == self.sliders else [250 for i in self.slider_range]

            if len(stepsize) == self.sliders:
                self.stepsize = [float(stepsize[i]) if stepsize[i] > 0 and stepsize[i] <= self.interval[i][1] - self.interval[i][0] else float(self.interval[i][1] - self.interval[i][0]) / self.steps[i] for i in self.slider_range]
            elif len(stepsize) == 1:
                self.stepsize = [float(stepsize[0]) if stepsize[0] > 0 and stepsize[0] <= self.interval[i][1] - self.interval[i][0] else float(self.interval[i][1] - self.interval[i][0]) / self.steps[i] for i in self.slider_range]
            else:
                self.stepsize = [float(self.interval[i][1] - self.interval[i][0]) / self.steps[i] for i in self.slider_range]

        self.label = label

    def message(self):
        """
        Get a multi_slider control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        return_message = {'control_type':'multi_slider',
                          'subtype':self.slider_type,
                          'display_values':self.display_values,
                          'sliders':self.sliders,
                          'range':self.interval,
                          'step':self.stepsize,
                          'raw':True,
                          'label':self.label}
        if self.slider_type == "discrete":
            return_message["values"] = [[repr(j) for j in self.values[i]] for i in self.slider_range]
            return_message["default"] = self.default
        else:
            return_message["default"] = self.default_return
        return return_message

    def adapter(self,v, globs):
        if self.slider_type == "discrete":
            return [self.values[i][v[i]] for i in self.slider_range]
        else:
            return v

class ColorSelector(InteractControl):
    """
    A color selector interact control

    :arg default: initial color (either as an html hex string or a Sage Color
        object, if sage is installed.
    :arg bool hide_input: Toggles whether the hex value of the color picker
        should be displayed in an input box beside the control.
    :arg bool sage_color: Toggles whether the return value should be a Sage
        Color object (True) or html hex string (False). If Sage is unavailable
        or if the user has deselected "sage mode" for the computation, this
        value will always end up False, regardless of whether the user specified
        otherwise in the interact.
    :arg str label: the label of the control, ``""`` for no label, and
        a default value (None) of the control's variable.
    """

    def __init__(self, default="#000000", hide_input=False, sage_color=True, label=None):
        self.sage_color = sage_color
        if self.sage_color:
            try:
                from sagenb.misc.misc import Color
                self.sage_mode = True;
            except:
                self.sage_mode = False;
        if self.sage_mode and self.sage_color:
            if isinstance(default, Color):
                self.default = default
            elif isinstance(default, str):
                self.default = Color(default)
            else:
                self.default = Color("#000000")
        else:
            self.default = default if isinstance(default,str) else "#000000"

        self.hide_input = hide_input
        self.label = label

    def message(self):
        """
        Get a color selector control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        self.return_value =  {'control_type':'color_selector',
                              'hide_input': self.hide_input,
                              'raw':False,
                              'label':self.label}

        if self.sage_mode and self.sage_color:
            self.return_value["default"] = self.default.html_color()
        else:
            self.return_value["default"] = self.default
        return self.return_value

    def adapter(self, v, globs):
        if self.sage_mode and self.sage_color:
            from sagenb.misc.misc import Color
            return Color(v)
        else:
            return v

class Button(InteractControl):
    """
    A button interact control
    
    :arg string text: button text
    :arg value: value of the button, when pressed.
    :arg default: default value that should be used if the button is not
        pushed. This **must** be specified.
    :arg string width: CSS width of the button. This should be specified in
        px or em.
    :arg str label: the label of the control, ``""`` for no label, and
        a default value (None) of the control's variable.
    """
    def __init__(self, default="", value = "", text="Button", width="", label=None):
        self.text = text
        self.width = width
        self.value = value
        self.default = False
        self.default_value = default
        self.label = label
        self.preserve_state = False

    def message(self):
        return {'control_type':'button',
                'width':self.width,
                'text':self.text,
                'raw': True,
                'label': self.label}

    def adapter(self, v, globs):
        if v:
            return self.value
        else:
            return self.default_value

class ButtonBar(InteractControl):
    """
    A button bar interact control
    
    :arg list values: list of values from which the user can select. A value can
        also be represented as a tuple of the form ``(value, label)``, where the
        value is the name of the variable and the label is the text displayed to
        the user.
    :arg default: default value that should be used if no button is pushed.
        This **must** be specified.
    :arg int ncols: number of columns of selectable buttons. If this is given,
        it must cleanly divide the number of buttons, else this value will be
        set to the number of buttons and ``nrows`` will be set to 1.
    :arg int nrows: number of rows of buttons. If this is given, it must cleanly
        divide the total number of objects, else this value will be set to 1 and
        ``ncols`` will be set to the number of buttosn. If both ``ncols`` and
        ``nrows`` are given, ``nrows * ncols`` must equal the number of buttons,
        else ``nrows`` will be set to 1 and ``ncols`` will be set to the number
        of objects.
    :arg string width: CSS width of each button. This should be specified in
        px or em.
    :arg str label: the label of the control, ``""`` for no label, and
        a default value (None) of the control's variable.
    """
    def __init__(self, values=[0], default="", nrows=None, ncols=None, width="", label=None):
        self.default = None
        self.default_value = default
        self.values = values[:]
        self.nrows = nrows
        self.ncols = ncols
        self.width = str(width)
        self.label = label
        self.preserve_state=False

        # Assign button labels and values.
        self.value_labels=[str(v[1]) if isinstance(v,tuple) and
                           len(v)==2 else str(v) for v in values]
        self.values = [v[0] if isinstance(v,tuple) and
                       len(v)==2 else v for v in values]

        # Check/set rows and columns for layout
        if self.nrows is None and self.ncols is None:
            self.nrows = 1
            self.ncols = len(self.values)
        elif self.nrows is None:
            self.ncols = int(self.ncols)
            if self.ncols <= 0:
                self.ncols = len(values)
            self.nrows = int(len(self.values) / self.ncols)
            if self.ncols * self.nrows < len(self.values):
                self.nrows = 1
                self.ncols = len(self.values)
        elif self.ncols is None:
            self.nrows = int(self.nrows)
            if self.nrows <= 0:
                self.nrows = 1
            self.ncols = int(len(self.values) / self.nrows)
            if self.ncols * self.nrows < len(self.values):
                self.nrows = 1
                self.ncols = len(self.values)
        else:
            self.ncols = int(self.ncols)
            self.nrows = int(self.nrows)
            if self.ncols * self.nrows != len(self.values):
                self.nrows = 1
                self.ncols = len(self.values)

    def message(self):
        """
        Get a button bar control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        return {'control_type': 'button_bar',
                'values': len(self.values),
                'value_labels': self.value_labels,
                'nrows': self.nrows,
                'ncols': self.ncols,
                'raw': True,
                'width': self.width,
                'label': self.label}

    def adapter(self,v, globs):
        if v is None:
            return self.default_value
        else:
            return self.values[int(v)]

class HtmlBox(InteractControl):
    """
    An html box interact control
    
    :arg string value: Html code to be inserted. This should be given in quotes.
    :arg str label: the label of the control, ``None`` for the control's
        variable, and ``""`` (default) for no label.
    """
    def __init__(self, value="", label=""):
        self.value = self.default = value;
        self.label = label;
    def message(self):
        """
        Get an html box control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        return {'control_type': 'html_box',
                'value': self.value,
                'label': self.label}

class UpdateButton(InteractControl):
    """
    An update button interact control
    
    :arg list update: List of vars (all of which should be quoted) that the
        update button updates when pressed.
    :arg string text: button text
    :arg value: value of the button, when pressed.
    :arg default: default value that should be used if the button is not
        pushed. This **must** be specified.
    :arg string width: CSS width of the button. This should be specified in
        px or em.
    :arg str label: the label of the control, ``None`` for the control's
        variable, and ``""`` (default) for no label.
    """
    def __init__(self, update=["*"], text="Update", value="", default="", width="", label=""):
        self.vars = update
        self.text = text
        self.width = width
        self.value = value
        self.default = False
        self.default_value = default
        self.label = label
        self.preserve_state = False

    def message(self):
        return {'control_type':'button',
                'width':self.width,
                'text':self.text,
                'raw': True,
                'label': self.label}

    def adapter(self, v, globs):
        if v:
            return self.value
        else:
            return self.default_value

    def boundVars(self):
        return self.vars


def automatic_control(control, var=None):
    """
    Guesses the desired interact control from the syntax of the parameter.
    
    :arg control: Parameter value.
    
    :returns: An InteractControl object.
    :rtype: InteractControl
    
    
    """
    from numbers import Number
    from types import GeneratorType
    label = None
    default_value = 0

    # For backwards compatibility, we check to see if
    # auto_update=False as passed in. If so, we set up an
    # UpdateButton.  This should be deprecated.

    if var=="auto_update" and control is False:
        return UpdateButton()
    
    # Checks for labels and control values
    for _ in range(2):
        if isinstance(control, tuple) and len(control) == 2 and isinstance(control[0], str):
            label, control = control
        if isinstance(control, tuple) and len(control) == 2 and isinstance(control[1], (tuple, list, GeneratorType)):
            # TODO: default_value isn't used effectively below in all instances 
            default_value, control = control

    # Checks for interact controls that are verbosely defined
    if isinstance(control, InteractControl):
        C = control
        if label:
            C.label = label
    elif isinstance(control, basestring):
        C = InputBox(default = control, label = label, evaluate=False)
    elif isinstance(control, bool):
        C = Checkbox(default = control, label = label, raw = True)
    elif isinstance(control, list):
        if len(control)==1:
            if isinstance(control[0], (list,tuple)) and len(control[0])==2:
                buttonvalue, buttontext=control[0]
            else:
                buttonvalue, buttontext=control[0],str(control[0])
            C = Button(value=buttonvalue, text=buttontext, default=buttonvalue, label=label)
        else:
            if len(control) <= 5:
                selectortype = "button"
            else:
                selectortype = "list"
            C = Selector(selector_type = selectortype, default = default_value, label = label, values = control)
    elif isinstance(control, GeneratorType):
        values=take(10000,control)
        C = DiscreteSlider(default = default_value, values = values, label = label)
    elif isinstance (control, tuple):
        if len(control) == 2:
            C = ContinuousSlider(default = default_value, interval = (control[0], control[1]), label = label)
        elif len(control) == 3:
            C = ContinuousSlider(default = default_value, interval = (control[0], control[1]), stepsize = control[2], label = label)
        else:
            values=list(control)
            C = DiscreteSlider(default = default_value, values = values, label = label)
    else:
        C = InputBox(default = control, label=label, evaluate=True)
        try:
            from sagenb.misc.misc import Color
            from sage.structure.all import is_Vector, is_Matrix
            from sage.all import parent
            if is_Matrix(control):
                nrows = control.nrows()
                ncols = control.ncols()
                default_value = control.list()
                default_value = [[default_value[j * ncols + i] for i in range(ncols)] for j in range(nrows)]
                C = InputGrid(nrows = nrows, ncols = ncols, label = label, 
                              default = default_value, adapter=lambda x, globs: parent(control)(x))
            elif is_Vector(control):
                default_value = [control.list()]
                nrows = 1
                ncols = len(control)
                C = InputGrid(nrows = nrows, ncols = ncols, label = label, 
                              default = default_value, adapter=lambda x, globs: parent(control)(x[0]))
            elif isinstance(control, Color):
                C = ColorSelector(default = control, label = label)
        except:
            pass
    
    return C

def take(n, iterable):
    """
    Return the first n elements of an iterator as a list.

    This is from the `Python itertools documentation <http://docs.python.org/library/itertools.html#recipes>`_.

    :arg int n: Number of elements through which v should be iterated.
    :arg iterable: An iterator.

    :returns: First n elements of iterable.
    :rtype: list
    """

    from itertools import islice
    return list(islice(iterable, n))

def flatten(listOfLists):
    """
    Flatten one level of nesting
    
    This is from the `Python itertools documentation <http://docs.python.org/library/itertools.html#recipes>`_.
    """
    from itertools import chain
    return chain.from_iterable(listOfLists)


def default_to_index(values, default):
    """
    From sage notebook's interact.py file
    """
    # determine the best choice of index into the list of values
    # for the user-selected default. 
    if default is None:
        index = 0
    else:
        try:
            i = values.index(default)
        except ValueError:
            # here no index matches -- which is best?
            try:
                v = [(abs(default - val), j) for j,val in enumerate(values)]
                m = min(v)
                i = m[1]
            except TypeError: # abs not defined on everything, so give up
                i = 0
        index = i
    return index

imports = {"Checkbox": Checkbox, "InputBox": InputBox,
           "ExpressionBox": ExpressionBox, "InputGrid": InputGrid,
           "Selector": Selector, "DiscreteSlider": DiscreteSlider,
           "ContinuousSlider": ContinuousSlider, "MultiSlider": MultiSlider,
           "ColorSelector": ColorSelector, "Selector": Selector,
           "Button": Button, "ButtonBar": ButtonBar, "HtmlBox": HtmlBox,
           "UpdateButton": UpdateButton}

