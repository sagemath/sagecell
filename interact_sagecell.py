#########################################################################################
#       Copyright (C) 2013 Jason Grout, Ira Hanson, Alex Kramer                         #
#                                                                                       #
#  Distributed under the terms of the GNU General Public License (GPL), version 2+      #
#                                                                                       #
#                  http://www.gnu.org/licenses/                                         #
#########################################################################################

# the only reason this file is distributed under GPLv2+ is because it
# imports functions from Sage GPLv2+ code.  The actual code in this
# file is under the modified BSD license, which means that if the Sage
# imports are replaced with BSD-compatible functions, this file can be
# distributed under the modified BSD license.

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
    def f(n=(0,10,1)):
        @interact(controls=[('x%d'%i, (0,10)) for i in range(n)])
        def s(multiplier=2, **kwargs):
            print sum(kwargs.values())*multiplier


Recursively nested interact::

    c=1
    @interact
    def f(n=(0,10,1)):
        global c
        c+=1
        print 'f evaluated %d times'%c
        for i in range(n):
            interact(f)
"""

import uuid
import sys
import json
from misc import session_metadata, decorator_defaults

__interacts={}

def update_interact(interact_id, name=None, value=None, do_update=True):
    interact_info = __interacts[interact_id]
    controls = interact_info["controls"]
    proxy = interact_info["proxy"]
    if name is not None:
        controls[name].value = value
        if name not in proxy._changed:
            proxy._changed.append(str(name))
    if do_update and (name is None or controls[name].update):
        kwargs = {n: c.adapter(c.value) for n, c in controls.iteritems()}
        interact_info["function"](control_vals=kwargs)
        for c in controls.itervalues():
            c.reset()
        proxy._changed = []

def update_interact_msg(stream, ident, msg):
    content = msg["content"]
    interact_id = content["interact_id"]
    for name in content["values"]:
        if name in __interacts[interact_id]["controls"]:
            update_interact(interact_id, name, content["values"][name], not content["update_last"])
    if content["update_last"]:
        update_interact(interact_id)

class InteractProxy(object):
    def __init__(self, interact_id, function):
        self.__interact_id = interact_id
        self.__interact = globals()["__interacts"][self.__interact_id]
        self.__function = function
        self._changed = self.__interact["controls"].keys()

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super(InteractProxy, self).__setattr__(name, value)
            return
        if name not in self.__interact["controls"]:
            control = automatic_control(value, var=name)
            self.__interact["controls"][name] = control
            control.globals = self.__function.func_globals
            msg = control.message()
            msg["label"] = control.label if control.label is not None else name
            msg["update"] = control.update = not any(
                isinstance(c, UpdateButton) for c in self.__interact["controls"].itervalues()
            )
            sys._sage_.display_message({
                "application/sage-interact-new-control": {
                    "interact_id": self.__interact_id,
                    "name": name,
                    "control": msg
                },
                "text/plain": "New interact control %s" % (name,)
            })
            if name not in self._changed:
                self._changed.append(name)
            return
        if isinstance(self.__interact["controls"][name].value, list):
            for i,v in enumerate(value):
                getattr(self, name)[i]=v
            return
        self.__interact["controls"][name].value = value
        self.__send_update(name)
    def __dir__(self):
        items = self.__interact["controls"].keys()
        for a in self.__dict__:
            if a.startswith("_") and not a.startswith("_InteractProxy__"):
                items.append(a)
        items.append("_update")
        items.sort()
        return items

    def __getattr__(self, name):
        if name not in self.__interact["controls"]:
            raise AttributeError("Interact has no control '%s'" % (name,))
        if isinstance(self.__interact["controls"][name].value, list):
            return InteractProxy.ListProxy(self, name)
        return self.__interact["controls"][name].value

    def __delattr__(self, name):
        del self.__interact["controls"][name]
        sys._sage_.display_message({
            "application/sage-interact-del-control": {
                "interact_id": self.__interact_id,
                "name": name
            },
            "text/plain": "Deleting interact control %s" % (name,)
        })
        if name not in self._changed:
            self._changed.append(name)

    def __call__(self, *args, **kwargs):
        return self.__function(*args, **kwargs)

    def __send_update(self, name, items={}):
        msg = {
            "application/sage-interact-update": {
                "interact_id": self.__interact_id,
                "control": name,
                "value": self.__interact["controls"][name].value
            },
            "text/plain": "Sage Interact Update"
        }
        msg["application/sage-interact-update"].update(items)
        sys._sage_.display_message(msg)
        if name not in self._changed:
            self._changed.append(name)

    def _update(self):
        update_interact(self.__interact_id)

    def _state(self, state=None):
        if state is None:
            return {k:v.value for k,v in self.__interact["controls"].items()}
        else:
            for k,v in state.items():
                setattr(self, k, v)

    def _bookmark(self, name, state=None):
        if state is None:
            state = self._state()
        else:
            state = {n: self.__interact["controls"][n].constrain(v) for n, v in state.iteritems()}
        msg = {
            "application/sage-interact-bookmark": {
                "interact_id": self.__interact_id,
                "name": name,
                "values": state
            },
            "text/plain": "Creating bookmark %s" % (name,)
        }
        sys._sage_.display_message(msg)

    def _set_bookmarks(self, bookmarks):
        if isinstance(bookmarks, basestring):
            bookmarks = json.loads(bookmarks)
            for name, state in bookmarks:
                self._bookmark(name, state)

    class ListProxy(object):
        def __init__(self, iproxy, name, index=[]):
            self.iproxy = iproxy
            self.name = name
            self.control = self.iproxy._InteractProxy__interact["controls"][self.name]
            self.list = self.control.value
            self.index = index[:]
            for i in self.index:
                self.list = self.list[i]

        def __getitem__(self, index):
            if isinstance(self.list[index], list):
                return InteractProxy.ListProxy(self.iproxy, self.name, self.index + [int(index)])
            return self.list[index]

        def __setitem__(self, index, value):
            if isinstance(index, slice):
                raise TypeError("object does not support slice assignment")
            if isinstance(self.list[index], list):
                for i,v in enumerate(value):
                    self[index][i] = v
                return
            index = int(index)
            self.list[index] = self.control.constrain_elem(value, index)
            self.iproxy._InteractProxy__send_update(self.name, {
                "value": self.list[index],
                "index": self.index + [index]
            })
            if self.name not in self.iproxy._changed:
                self.iproxy._changed.append(self.name)

        def __len__(self):
            return len(self.list)

        def __repr__(self):
            return "[%s]" % (", ".join(repr(e) for e in self.list),)

import sys
try:
    sys._sage_.register_handler("sagenb.interact.update_interact", update_interact_msg)
except AttributeError:
    pass

@decorator_defaults
def interact(f, controls=[], update=None, layout=None, locations=None,
             output=True, readonly=False, automatic_labels=True):
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

    If ``output=False``, then changed controls will not be
    highlighted.

    :arg function f: the function to make into an interact
    :arg list controls: a list of tuples of the form ``("name",control)``
    :arg boolean output: whether any output should be shown
    :returns: the original function
    :rtype: function
    """
    if isinstance(f, InteractProxy):
        f = f._InteractProxy__function
    update = set(update) if update is not None else set()
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
    if args is None:
        args = []
    if defaults is None:
        defaults = []
    if len(args) > len(defaults):
        pass_proxy = True
        args = args[1:]
    else:
        pass_proxy = False
    if len(names) != len(controls) or any(a in names for a in args):
        raise ValueError("duplicate argument in interact definition")
    n=len(args)-len(defaults)
    controls = zip(args, [None] * n + list(defaults)) + controls
    names = [c[0] for c in controls]
    controls = {n: automatic_control(c, var=n) for n, c in controls}
    nameset = set(names)

    for n, c in controls.iteritems():
        if n.startswith("_"):
            raise ValueError("invalid control name: %s" % (n,))
        if isinstance(c, UpdateButton):
            update.add(n)
    if len(update) == 0:
        update = names
    for n in update:
        controls[n].update = True

    if isinstance(layout, dict):
        rows = []
        rows.extend(layout.get("top", []))
        for pos, ctrls in layout.iteritems():
            if pos not in ("bottom", "top"):
                rows.extend(ctrls)
        if output:
            rows.append([("_output",1)])
        rows.extend(layout.get("bottom", []))
        layout = rows
    elif layout is None:
        layout = []

    if locations is True:
        locations="" # empty prefix
    if isinstance(locations, basestring):
        prefix = '#'+locations
        locations = {name: prefix+name for name in names+["_output","_bookmarks"]}

    placed = set()
    if locations:
        placed.update(locations.keys())
    if layout:
        for r in layout:
            for i, c in enumerate(r):
                if not isinstance(c, (list, tuple)):
                    c = (c, 1)
                r[i] = c = (c[0], int(c[1]))
                if c[0] is not None:
                    if c[0] in placed:
                        raise ValueError("duplicate item %s in layout" % (c[0],))
                    placed.add(c[0])
    layout.extend([(n, 1)] for n in names if n not in placed)
    if output and "_output" not in placed:
        layout.append([("_output", 1)])

    interact_id=str(uuid.uuid4())
    msgs = {n: c.message() for n, c in controls.iteritems()}
    for n, m in msgs.iteritems():
        if controls[n].label is not None:
            m["label"] = controls[n].label
        elif automatic_labels:
            m["label"] = n
        else:
            m["label"]= ""
        m["update"] = controls[n].update
    msg = {
        "application/sage-interact": {
            "new_interact_id": interact_id,
            "controls": msgs,
            "layout": layout,
            "locations": locations,
            "readonly": readonly,
        },
        "text/plain": "Sage Interact"
    }
    sys._sage_.display_message(msg)
    sys._sage_.reset_kernel_timeout(float('inf'))
    def adapted_f(control_vals):
        args = [__interacts[interact_id]["proxy"]] if pass_proxy else []
        with session_metadata({'interact_id': interact_id}):
            sys._sage_.clear(__interacts[interact_id]["proxy"]._changed)
            try:
                returned = f(*args, **control_vals)
            except:
                print "Interact state: %r" % (__interacts[interact_id]["proxy"]._state())
                raise
        return returned
    # update global __interacts
    __interacts[interact_id] = {
        "function": adapted_f,
        "controls": controls,
        "update": update
    }
    for n, c in controls.iteritems():
        c.globals = f.func_globals
    proxy = InteractProxy(interact_id, f)
    __interacts[interact_id]["proxy"] = proxy
    update_interact(interact_id)
    return proxy

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

    :arg default: the default value for the control
    :arg function adapter: a function that will be called on the value every
        time the interact is evaluated. This function should take one argument
        (the value) and return a value that will be passed to the function.
    """
    
    def __init__(self, default, label, adapter=None):
        self.value = default
        self.label = label
        self.update = False
        self.adapter = adapter if adapter is not None else lambda value: value

    def __setattr__(self, name, value):
        super(InteractControl, self).__setattr__(name, self.constrain(value) if name == "value" else value)

    def message(self):
        """
        Get a control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        raise NotImplementedError

    def constrain(self, value):
        """
        A function that is called on each value to which the control is set.
        This is called once, whenever the value is set, and may be overriden
        by a decendant of this class.
        
        :arg value: the value to constrain
        :returns: the constrained value to be stored
        """
        return value

    def reset(self):
        """
        This method is called after every interact update.
        """
        pass

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
        self.raw=raw
        super(Checkbox, self).__init__(default, label)

    def message(self):
        """
        Get a checkbox control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        return {
            'control_type':'checkbox',
            'default':self.value,
            'raw':self.raw
        }

    def constrain(self, value):
        return bool(value)

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
    def __init__(self, default=u"", label=None, width=0, height=1, keypress=False, adapter=None):
        super(InputBox, self).__init__(default, label, adapter)
        self.width=int(width)
        self.height=int(height)
        self.keypress = keypress
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
                'default':self.value,
                'width':self.width,
                'height':self.height,
                'evaluate': False,
                'keypress': self.keypress}

    def constrain(self, value):
        if isinstance(value, str):
            return value.decode("utf-8")
        if isinstance(value, unicode):
            return value
        return unicode(repr(value))

class ExpressionBox(InputBox):
    """
    An ``InputBox`` whose value is the result of evaluating its contents with Sage
    :arg default: default value of the input box.  If this is not a string, repr is
        called on it to get a string, which is then the default input.
    :arg int width: character width of the input box.
    :arg int height: character height of the input box. If this is greater than
        one, an HTML textarea will be rendered, while if it is less than one,x
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
    def __init__(self, default=u"0", label=None, width=0, height=1, adapter=None):
        if adapter is not None:
            full_adapter = lambda x: adapter(safe_sage_eval(x, self.globals))
        else:
            full_adapter = lambda x: safe_sage_eval(x, self.globals)
        super(ExpressionBox, self).__init__(default, label, width, height, adapter=full_adapter)

    def message(self):
        """
        Get an input box control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        return {"control_type": "input_box",
                "subtype": self.subtype,
                "default": self.value,
                "width": self.width,
                "height": self.height,
                "evaluate": True,
                "keypress": False}

class InputGrid(InteractControl):
    """
    An input grid control

    :arg int nrows: number of rows in the grid
    :arg int ncols: number of columns in the grid
    :arg default: default values of the control. A multi-dimensional
        list specifies the values of individual inputs; a single value
        sets the same value to all inputs
    :arg int width: character width of each input box
    :arg str label: the label of the control, ``""`` for no label, and
        a default value (None) of the control's variable.
    :arg evaluate: whether or not the strings returned from the front end
        are first sage_eval'd (default: ``True``).
    :arg adapter: a callable which will be passed the input before
        sending it into the function.  This might ensure that the
        input to the function is of a specific type, for example.  The
        function should take as input a list of lists (the value
        of the control).
    :arg element_adapter: a callable which takes an element value
        and returns an adapted value.  A nested list of these adapted elements
        is what is given to the main adapter function.
    """
    def __init__(self, nrows=1, ncols=1, default=u'0', width=5, label=None,
                 evaluate=True, adapter=None, element_adapter=None):
        self.nrows = int(nrows)
        self.ncols = int(ncols)
        self.width = int(width)
        self.evaluate = evaluate
        if self.evaluate:
            if element_adapter is not None:
                self.element_adapter = lambda x: element_adapter(safe_sage_eval(x, self.globals))
            else:
                self.element_adapter = lambda x: safe_sage_eval(x, self.globals)
        else:
            if element_adapter is not None:
                self.element_adapter = element_adapter
            else:
                self.element_adapter = lambda value: value
        if adapter is None:
            full_adapter = lambda x: [[self.element_adapter(i) for i in xi] for xi in x]
        else:
            full_adapter = lambda x: adapter([[self.element_adapter(i) for i in xi] for xi in x])
        super(InputGrid, self).__init__(default, label, full_adapter)

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
                'default': self.value,
                'width':self.width,
                'raw': True,
                'evaluate': self.evaluate}

    def constrain(self, value):
        from types import GeneratorType
        if isinstance(value, GeneratorType):
            return [[self.constrain_elem(value.next()) for _ in xrange(self.ncols)] for _ in xrange(self.nrows)]
        elif not isinstance(value, (list, tuple)):
            return [[self.constrain_elem(value) for _ in xrange(self.ncols)] for _ in xrange(self.nrows)]
        elif not all(isinstance(entry, (list, tuple)) for entry in value):
            return [[self.constrain_elem(value[i * self.ncols + j]) for j in xrange(self.ncols)] for i in xrange(self.nrows)]
        return [[self.constrain_elem(v) for v in row] for row in value]

    def constrain_elem(self, value, i=None):
        return unicode(value if isinstance(value, basestring) else repr(value))

class Selector(InteractControl):
    """
    A selector interact control

    :arg list values: list of values from which the user can select. A value can
        also be represented as a tuple of the form ``(value, label)``, where the
        value is the name of the variable and the label is the text displayed to
        the user.
    :arg int default: initially selected item in the list of values
    :arg string selector_type: Type of selector. Currently supported options
        are "button" (Buttons), "radio" (Radio buttons), and "list"
        (Dropdown list), with "list" being the default. If "list" is used,
        ``ncols`` and ``nrows`` will be ignored. If "radio" is used, ``width``
        will be ignored.
    :arg int nrows: number of rows of selectable objects. If this is given, it
        must cleanly divide the number of objects, else this value will be set
        to 1 and ``ncols`` will be set to the number of objects. If both
        ``ncols`` and ``nrows`` are given, ``nrows * ncols`` must equal the
        number of objects, else ``nrows`` will be set to 1 and ``ncols`` will
        be set to the number of objects.
    :arg int ncols: number of columns of selectable objects. If this is given,
        it must cleanly divide the number of objects, else this value will be
        set to the number of objects and ``nrows`` will be set to 1.
    :arg string width: CSS width of each button. This should be specified in
        px or em.
    :arg str label: the label of the control, ``""`` for no label, and
        a default value (None) of the control's variable.
    """

    def __init__(self, values, default=None, selector_type="list", nrows=None, ncols=None, width="", label=None):
        self.selector_type=selector_type
        self.nrows=nrows
        self.ncols=ncols
        self.width=str(width)
        if self.selector_type != "button" and self.selector_type != "radio":
            self.selector_type = "list"
        if len(values) == 0:
            raise ValueError("values list cannot be empty")
        # Assign selector labels and values.
        if all(isinstance(v, tuple) and len(v) == 2 for v in values):
            self.values = [v[0] for v in values]
            self.value_labels = [unicode(v[1]) for v in values]
        else:
            self.values = values[:]
            self.value_labels = [unicode(v) for v in self.values]
        default = 0 if default is None else self.values.index(default)
        super(Selector, self).__init__(default, label, self.values.__getitem__)
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
                'default': self.value,
                'nrows': int(self.nrows) if self.nrows is not None else None,
                'ncols': int(self.ncols) if self.ncols is not None else None,
                'raw': True,
                'width': self.width}

    def constrain(self, value):
        return int(constrain_to_range(value, 0, len(self.values) - 1))

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
            raise ValueError("discrete slider must have at least 2 values")
        self.range_slider = range_slider
        if self.range_slider:
            default = (0, len(self.values) - 1) if default is None else \
                [closest_index(self.values, default[i]) for i in (0, 1)]
        else:
            default = closest_index(self.values, default)
        super(DiscreteSlider, self).__init__(default, label, \
            lambda v: tuple(self.values[i] for i in v) if self.range_slider else self.values[v])
        self.display_value = display_value

    def message(self):
        """
        Get a discrete slider control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        return {'control_type':'slider',
                'subtype': 'discrete_range' if self.range_slider else 'discrete',
                'display_value':self.display_value,
                'default': self.value,
                'range':[0, len(self.values)-1],
                'values':[repr(i) for i in self.values],
                'step':1,
                'raw':True}

    def constrain(self, value):
        if self.range_slider:
            return tuple(sorted(int(constrain_to_range(value[i], 0, len(self.values) - 1)) for i in (0, 1)))
        return int(constrain_to_range(value, 0, len(self.values) - 1))

class ContinuousSlider(InteractControl):
    """
    A continuous slider interact control.

    The slider value moves between a range of numbers.

    :arg tuple interval: range of the slider, in the form ``(min, max)``
    :arg int default: initial value of the slider; if ``None``, the
        slider defaults to its minimum
    :arg int steps: number of steps the slider should have between min and max
    :arg Number stepsize: size of step for the slider. If both step and stepsize are specified, stepsize takes precedence so long as it is valid.
    :arg str label: the label of the control, ``""`` for no label, and
        a default value (None) of the control's variable.
    :arg bool range_slider: toggles whether the slider should select one value (default = False) or a range of values (True).
    :arg bool display_value: toggles whether the slider value sould be displayed (default = True)
    
    Note that while "number of steps" and/or "stepsize" can be specified for the slider, this is to enable snapping, rather than a restriction on the slider's values. The only restrictions placed on the values of the slider are the endpoints of its range.
    """

    def __init__(self, interval=(0,100), default=None, steps=250, stepsize=0, label=None, range_slider=False, display_value=True, adapter=None):
        self.range_slider = range_slider
        self.display_value = display_value
        if len(interval) != 2 or interval[0] == interval[1]:
            raise ValueError("invalid interval: %r" % (interval,))
        self.interval = tuple(sorted((float(interval[0]), float(interval[1]))))
        super(ContinuousSlider, self).__init__(default, label, adapter)
        self.steps = int(steps) if steps > 0 else 250
        self.stepsize = float(stepsize if stepsize > 0 and stepsize <= self.interval[1] - self.interval[0] else float(self.interval[1] - self.interval[0]) / self.steps)

    def message(self):
        """
        Get a continuous slider control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        return {'control_type':'slider',
                'subtype': 'continuous_range' if self.range_slider else 'continuous',
                'display_value':self.display_value,
                'default':self.value,
                'step':self.stepsize,
                'range':[float(i) for i in self.interval],
                'raw':True}

    def constrain(self, value):
        if self.range_slider:
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return tuple(sorted(float(constrain_to_range(value[i], self.interval[0], self.interval[1])) for i in (0, 1)))
            return self.interval
        return float(constrain_to_range(value, self.interval[0], self.interval[1]))

class MultiSlider(InteractControl):
    """
    A multiple-slider interact control.

    Defines a bank of vertical sliders (either discrete or continuous sliders, but not both in the same control).

    :arg int sliders: Number of sliders to generate
    :arg list values: Values for each value slider in a multi-dimensional list for the form [[slider_1_val_1..slider_1_val_n], ... ,[slider_n_val_1, .. ,slider_n_val_n]]. The length of the first dimension of the list should be equivalent to the number of sliders, but if all sliders are to contain the same values, the outer list only needs to contain that one list of values.
    :arg list interval: Intervals for each continuous slider in a list of tuples of the form [(min_1, max_1), ... ,(min_n, max_n)]. This parameter cannot be set if value sliders are specified. The length of the first dimension of the list should be equivalent to the number of sliders, but if all sliders are to have the same interval, the list only needs to contain that one tuple.
    :arg string slider_type: type of sliders to generate. Currently, only "continuous" and "discrete" are valid, and other input defaults to "continuous."
    :arg list default: Default value of each slider. The length of the list should be equivalent to the number of sliders, but if all sliders are to have the same default value, the list only needs to contain that one value.
    :arg list stepsize: List of numbers representing the stepsize for each continuous slider. The length of the list should be equivalent to the number of sliders, but if all sliders are to have the same stepsize, the list only needs to contain that one value.
    :arg list steps: List of numbers representing the number of steps for each continuous slider. Note that (as in the case of the regular continuous slider), specifying a valid stepsize will always take precedence over any specification of number of steps, valid or not. The length of this list should be equivalent to the number of sliders, but if all sliders are to have the same number of steps, the list only neesd to contain that one value.
    :arg bool display_values: toggles whether the slider values sould be displayed (default = True)
    :arg str label: the label of the control, ``""`` for no label, and
        a default value (None) of the control's variable.
    """

    def __init__(self, sliders=1, values=[[0,1]], interval=[(0,1)], slider_type="continuous",  default=None, stepsize=[0], steps=[250], display_values=True, label=None):
        from types import GeneratorType
        self.number = int(sliders)
        self.slider_type = slider_type
        self.display_values = display_values
        if not isinstance(default, (list, tuple)):
            default = [default]
        if len(default) == 1:
            default *= self.number
        if self.slider_type == "discrete":
            self.stepsize = 1
            if len(values) == self.number:
                self.values = values[:]
                for i, v in enumerate(self.values):
                    if isinstance(v, GeneratorType):
                        self.values[i] = take(10000, i)
            elif len(values) == 1 and len(values[0]) >= 2:
                self.values = [values[0][:]] * self.number
            else:
                self.values = [[0,1]] * self.number
            self.interval = [(0, len(self.values[i]) - 1) for i in xrange(self.number)]
            default = [closest_index(self.values[i], d) for i, d in enumerate(default)]
            super(MultiSlider, self).__init__(default, label, lambda v: [self.values[i][v[i]] for i in xrange(self.number)])
        else:
            self.slider_type = "continuous"
            if len(interval) == self.number:
                self.interval = list(interval)
                for i, ival in enumerate(self.interval):
                    if len(ival) != 2 or ival[0] == ival[1]:
                        raise ValueError("invalid interval: %r" % (ival,))
                    self.interval[i] = tuple(sorted([float(ival[0]), float(ival[1])]))
            elif len(interval) == 1 and len(interval[0]) == 2 and interval[0][0] != interval[0][1]:
                self.interval = [tuple(sorted([float(interval[0][0]), float(interval[0][1])]))] * self.number
            else:
                self.interval = [(0, 1)] * self.number
            super(MultiSlider, self).__init__(default, label)
            if len(steps) == 1:
                self.steps = [steps[0]] * self.number if steps[0] > 0 else [250] * self.number
            else:
                self.steps = [int(i) if i > 0 else 250 for i in steps] if len(steps) == self.number else [250 for _ in self.interval]
            if len(stepsize) == self.number:
                self.stepsize = [float(stepsize[i]) if stepsize[i] > 0 and stepsize[i] <= self.interval[i][1] - self.interval[i][0] else float(self.interval[i][1] - self.interval[i][0]) / self.steps[i] for i in xrange(self.number)]
            elif len(stepsize) == 1:
                self.stepsize = [float(stepsize[0]) if stepsize[0] > 0 and stepsize[0] <= self.interval[i][1] - self.interval[i][0] else float(self.interval[i][1] - self.interval[i][0]) / self.steps[i] for i in xrange(self.number)]
            else:
                self.stepsize = [float(self.interval[i][1] - self.interval[i][0]) / self.steps[i] for i in self.number]

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
                          'sliders': self.number,
                          'raw':True,
                          'default':self.value,
                          'range': self.interval,
                          'step': self.stepsize}
        if self.slider_type == "discrete":
            return_message["values"] = [[repr(v) for v in val] for val in self.values]
        return return_message

    def constrain(self, value):
        if isinstance(value, (list, tuple)) and len(value) == self.number:
            return [self.constrain_elem(v, i) for i, v in enumerate(value)]
        else:
            return [self.constrain_elem(value, i) for i in xrange(self.number)]

    def constrain_elem(self, value, index):
        if self.slider_type == "discrete":
            return int(constrain_to_range(value, 0, len(self.values[index]) - 1))
        else:
            return float(constrain_to_range(value, self.interval[index][0], self.interval[index][1]))

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
        try:
            from sagenb.misc.misc import Color
            self.Color = Color
        except ImportError:
            self.Color = None
        self.sage_color = self.Color and sage_color
        super(ColorSelector, self).__init__(default, label, self.Color if sage_color else None)
        self.hide_input = hide_input

    def constrain(self, value):
        if self.Color:
            return self.Color(value).html_color()
        if isinstance(value, basestring):
            return value
        return "#000000"

    def message(self):
        """
        Get a color selector control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        return {
            "control_type": "color_selector",
            "default": self.value,
            "hide_input": self.hide_input,
            "raw": False
        }

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

    def __init__(self, default="", value ="", text="Button", width="", label=None):
        super(Button, self).__init__(False, label, lambda v: self.clicked_value if v else self.default_value)
        self.text = text
        self.width = width
        self.default_value = default
        self.clicked_value = value

    def message(self):
        return {'control_type':'button',
                'width':self.width,
                'text':self.text,
                'raw': True,}

    def constrain(self, value):
        return bool(value)

    def reset(self):
        self.value = False

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
        super(ButtonBar, self).__init__(None, label, lambda v: self.default_value if v is None else self.values[int(v)])
        self.default_value = default
        self.values = values[:]
        self.nrows = nrows
        self.ncols = ncols
        self.width = str(width)

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
                'width': self.width,}

    def constrain(self, value):
        return None if value is None else constrain_to_range(int(value), 0, len(self.values) - 1)

    def reset(self):
        self.value = None

class HtmlBox(InteractControl):
    """
    An html box interact control
    
    :arg string value: Html code to be inserted. This should be given in quotes.
    :arg str label: the label of the control, ``None`` for the control's
        variable, and ``""`` (default) for no label.
    """
    def __init__(self, value="", label=""):
        super(HtmlBox, self).__init__(value, label)

    def message(self):
        """
        Get an html box control configuration message for an
        ``interact_prepare`` message

        :returns: configuration message
        :rtype: dict
        """
        return {'control_type': 'html_box',
                'value': self.value,}

    def constrain(self, value):
        return unicode(value)

class UpdateButton(Button):
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

    def __init__(self, text="Update", value="", default="", width="", label=""):
        super(UpdateButton, self).__init__(default, value, text, width, label)

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
    default_value = None

    # For backwards compatibility, we check to see if
    # auto_update=False as passed in. If so, we set up an
    # UpdateButton.  This should be deprecated.

    if var=="auto_update" and control is False:
        return UpdateButton()
    
    # Checks for labels and control values
    for _ in range(2):
        if isinstance(control, tuple) and len(control) == 2 and isinstance(control[0], basestring):
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
        C = InputBox(default = control, label = label)
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
            from sage.arith.srange import srange
            C = DiscreteSlider(default=default_value, values=srange(control[0], control[1], control[2], include_endpoint=True), label=label)
        else:
            values=list(control)
            C = DiscreteSlider(default = default_value, values = values, label = label)
    else:
        C = ExpressionBox(default = control, label=label)
        try:
            from sagenb.misc.misc import Color
            from sage.structure.element import is_Vector, is_Matrix
            from sage.all import parent
            if is_Matrix(control):
                nrows = control.nrows()
                ncols = control.ncols()
                default_value = control.list()
                default_value = [[default_value[j * ncols + i] for i in range(ncols)] for j in range(nrows)]
                C = InputGrid(nrows = nrows, ncols = ncols, label = label, 
                              default = default_value, adapter=parent(control))
            elif is_Vector(control):
                default_value = [control.list()]
                nrows = 1
                ncols = len(control)
                C = InputGrid(nrows = nrows, ncols = ncols, label = label, 
                              default = default_value, adapter=lambda x: parent(control)(x[0]))
            elif isinstance(control, Color):
                C = ColorSelector(default = control, label = label)
        except:
            pass
    
    return C

def closest_index(values, value):
    if value == None:
        return 0
    try:
        return values.index(value)
    except ValueError:
        try:
            return min(xrange(len(values)), key=lambda i: abs(value - values[i]))
        except TypeError:
            return 0

def constrain_to_range(v, rmin, rmax):
    if v is None or v < rmin:
        return rmin
    if v > rmax:
        return rmax
    return v

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

imports = {"interact": interact,
           "Checkbox": Checkbox,
           "InputBox": InputBox,
           "ExpressionBox": ExpressionBox,
           "InputGrid": InputGrid,
           "Selector": Selector,
           "DiscreteSlider": DiscreteSlider,
           "ContinuousSlider": ContinuousSlider,
           "MultiSlider": MultiSlider,
           "ColorSelector": ColorSelector,
           "Selector": Selector,
           "Button": Button,
           "ButtonBar": ButtonBar,
           "HtmlBox": HtmlBox,
           "UpdateButton": UpdateButton}
