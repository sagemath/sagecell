# Draft

This is being edited a lot right now.

# Interact Classes

Classes provide a great way to have both a small self-contained namespace and chunks of code.  A class decorator sets up the necessary infrastructure to make the variables interactive.
```python
var('t')
@interact('x,y')
class F(object):
    x,y=(1,2)
    def right_panel(self):
        plot(self.x*sin(self.y*t), (t,-3,3))
        slider(self.interactive.x)
    @depends('x,y')
    def left_panel(self):
        interactive_point((self.interactive.x, self.interactive.y)) # a small div that picks 2d coordinates
f=F()
table([[f.right_panel, f.left_panel]])
```
This is expanded into:
```python
from collections import namedtuple
interactive_variable = namedtuple("interactive", "object_id, name, value")
class InteractiveVariable(object):
    def __init__(self, obj):
        self.obj = obj
    def __getattr__(self, name):
        return interactive_variable(object_id=self.obj.object_id, name=name, value=getattr(self.obj, name))
from uuid import uuid4
class F(object):
    x = 1
    y = 2
    _interactive_vars = set(['x','y'])
    
    def __init__(self):
        self.right_panel.__dict__['vars'] = ('x','y')
        self.left_panel.__dict__['vars'] = ('x','y')
        self.object_id = uuid4()
        self.interactive = InteractiveVariable(self)

    def __setattr__(self, name, value):
        super(F, self).__setattr__(name, value)
        if name in self._interactive_vars:
            print "Variable update: %s %s updated to %s"%(self.object_id, name, value)
        
    def _update_right_panel(self):
        print 'in right panel'
    def _update_left_panel(self):
        print 'in left panel'
    def right_panel(self):
        output_id = uuid4()
        # push default output id
        iopub_message({'dependent_variables': self.right_panel.vars,
                       'update_function': (self.object_id, '_update_right_panel')})
        self._update_right_panel()
        # pop default output_id
    def left_panel(self):
        output_id = uuid4()
        # push default output id
        iopub_message({'dependent_variables': self.right_panel.vars,
                       'update_function': (self.object_id, '_update_left_panel')})
        self._update_left_panel()
        # pop default output_id
```

* the class decorator:
   - analyzes each function to determine which attributes (or maybe just dynamic attributes) it references (we could also have a method decorator to explicitly indicate dependencies).  These attribute names are stored as a set in an attribute of the method.
   - sets up an `interactive` attribute that can be used to retrieve specs for interactive variables (for controls that both display and can set the variables).  Basically, `self.interactive.x` returns the object id, the attribute name, and the current value.  This is so controls can send appropriate update messages, as well as use the value directly.
   - adds a lazy attribute that calculates a unique object id, specific to the object instance
   - sets up the following behaviors for methods and interactive variables
* when a method of `f` is called:
  - an output id is generated
  - an update function is registered (actually the same function), with the output id as a key
  - a context is set up to send a message to the frontend with the new output area id and also the list of dependent variable (encoded as `(instance id, attribute name)`), then send an output end message afterwards.  The method is called inside of this context.
* when a dynamic attribute of the class is updated:
  - send the frontend a variable-changed message with the variable id.  This might be in response to a message the frontend already sent about changing the variable

On the frontend:
* when a variable-changed message is received that was not instigated by a control on the frontend
   - look up the outputs that depend on the variable ids and request updates for those outputs
* when a control on the frontend is changed
   - send a message back to the server with the variable ids and new values, ignoring any response variable-change messages (we already know the variables were changed)
   - request updates for any output region that was affected

In fact, the current `@interact` can be reimplemented as such a class, so that 
```python
@interact
def f(a=(0,1), b=x^2*y):
    print a*b
```
gets transformed to something like
```python
@interact('a,b')
class G(object):
    a=0
    b=x^2*y
    def controls(self):
        slider(self.interactive.a, (0,1))
        expressionbox(self.interactive.b,x^2*y)
    def output(self):
        print self.a*self.b
g=G()
table([[g.controls],[g.output]])
```

# Global scope

One problem with the class-based approach is that interactive parts aren't fine-grained enough.  Often we just have one particular thing or control that needs to be interactive.  Also, it would be quite a bit simpler if we could just have interactive global variables.

Here's one way to do it:

* Declare a namespace interactive (basically, a dict with messages on key updates)
* Any code can be executed as a string, like:
```python
N = InteractiveNamespace(x=3)
interactive("plot(c*x^2,(x,-3,3))", N)
```
Internally, this determines makes a proxy global namespace, where `N` overshadows any global variables (basically, we're creating our own scoping here).  The code is executed as `exec(code, ChainDict(N,globals()))`.  The only problem here is that `ChainDict(N,globals())` *must* be a dictionary (not just a `collections.MutableMapping`) in Python less than 3.3 (sometimes dictionary-specific methods are used to access the keys).  For example, this does not work if ChainDict is not a dictionary with all of the items in the dictionary:

```python
def fff():
    print y
```
where `y` is in the global namespace.  So...ChainDict has to populate itself with values from globals().  But then it's not up to date with the globals(), so the `y` above is never updated.

In Python 3.3, `exec(code, g)` lets `g` be an arbitrary python object, so the scheme works well.

The alternative is to instrument the entire global dictionary, but that seems like a huge overkill.

## Previous text
Using something like https://gist.github.com/4326157 as the globals dictionary, it is possible to send notifications any time a global variable is assigned, accessed, or deleted.  When a variable is declared as `interactive`, add it to the list of watched variables.  Keep track of things that depend on the variable, and when a message comes through that it has been updated, then update the things depending on the variable.

Example syntax:
```python
# registers namespace
N = InteractiveNamespace(x=3)
interactive("plot(c*x^2,(x,-3,3))", N)
```
where interactive is basically
```python
def interactive(code, ns):
    #find symbols
    st=symtable.symtable(code,'<string>', 'exec')
    set(st.get_identifiers)
    # set output region, send code string and identifier of the namespace
    exec code in globals(), ns
```

# Stop reading

Okay, you can stop reading.  Below is basically a scratchpad for other ideas.

## Principles of design

* Updates should be done via a pull model rather than a push model.  In other words, an update is only done if the user/client requests it.
  - the front end should know what variables each output area depends on
  - the front end only needs to request updates for output regions that are in view
  - somewhere on the server, there should be some sort of dictionary mapping output regions to functions
  - if a client goes down or something, no big deal---they just won't request updates



## Issues

* We cannot tell if a mutable value is changed, only if a new value is assigned to a variable name.  For example, we can tell if `x=[1,2,3]` is done, but we can't tell when `x[2]=100` is done.  If we insisted that `x` was our own subclass of list (for example, if we cast `x` to that upon update), then we could be notified of changes in elements of `x`.
* Because the `locals()` dict is not live, in the sense that changing a local variable will not trigger a dictionary access, this logic doesn't work on local variables.  In Python 2.x, you can add an `exec ""` to the beginning of a function to force locals to go through the dictionary, but that won't work in Python 3.x.  See http://stackoverflow.com/questions/8028708/dynamically-set-local-variable-in-python, for example.

## Example syntax

## A control directly representing a variable

```python
c=1
Slider('c')
```
produces a slider that represents the value of `c`.  The slider's javascript view registers to receive updates about the variable `c`.  The Slider representation also registers on the python side for a message to be sent when `c` is updated.

## An expression involving an interactive variable

Make an `interactive` object that has a custom attribute accessor so that `interactive.c` will register to get notifications for updates to the global variable `c`.  Then the above example could be done as:
```python
c=1
Slider(interactive.c)
```

### Strings

If you have an expression which depends on `c`, or a list of expressions that should be updated when `c` is changed, you could do something like
```python
interactive('plot(c*x, (x,-3,3))')
```
(internally, this would be compiled to an AST and tagged with the variables used so that anytime a variable was updated, the expression was reevaluated)

### Functions

You could use an explicit function to encapsulate an update block, reminiscent of the current interact system:
```python
@depends('c')
def _(c):
    g=plot(c*x^2, (x,-3,3))
    g+=plot(sin(x), (x,-3,3))
    g.show()
```
or even just
```python
@interact
def _(c=interactive.c):
    ...
```

### Cell magics

You could also use a cell magic:
```
%%interact
g=plot(interactive.c*x^2, (x,-3,3))
g+=plot(sin(x), (x,-3,3))
g.show()
```
and the cell would be reevaluated whenever an interactive variable inside of it changed (we could get at this via inspecting the code with an AST transformer, then setting some flag if we found an interactive object).

### AST transform
You could even *always* do an AST transform looking for interactive variables, rather than just when the cell magic is specified.  The convention would be that a cell is rerun anytime an interactive variable is updated.

You'd have to be careful to be aware of side effects.  For example, if you had 
```python
l.append(interactive.c)
```
You'd also have to be aware that cells that used results of interactive computations without themselves being interactive wouldn't be updated, unless of course you used interactive.* in the affected cell.

Having an always-on AST transformer provides nice convenience for interactive objects, but could mess up things if you want something that has a more restricted scope, like the `@interact` function scoping above.  On the other hand, you could determine if the interact control was being used in the global namespace or in a function scope or in a class scope, and just rerun the code associated with the cell, function, or class, as appropriate.  That might be getting too magic now, though.

# Overall thoughts

## Global scope
It seems that having a function that takes a code string (and a corresponding cell magic) might be the way to go: 

* the `interactive("code")` function reruns the code string if any variable in it is changed.  Arguments can restrict which variables we look at, how often it can be rerun, etc.
* the `%%interact` cell magic just wraps the cell in `interactive()`, passing magic arguments to the interactive function
* the function and magic could take a special namespace name instead of using the global namespace.

## Smaller scope

Sometimes we want to restrict the namespace; we don't want to pollute the global namespace with our interactive variables.  We have three scoping mechanisms within python: module, class, and function.  Additionally, we could explicitly use a dictionary for a namespace (i.e., set this when execing the string of code).

### Exec dictionaries

We could explicitly specify a dictionary (with event hooks, like above) to use for the globals/locals when doing `interactive()`.

### Sage interacts
The current Sage interacts provide a nice way to have limited scope.  With Sage interacts, 
```python
@interact
def f(n=(0,1)):
    print n
```
defines some controls for manipulating `n`, and every time `n` is updated by changing the control, the function is rerun with the new `n` value.  A disadvantage of this approach is that there is a definite input and definite output region---it's not easy to mix the two (to have an interactive graph, for example).

### Traits

I'm not an expert on Traits, but the system basically uses the class scope to restrict dynamic variables and the class special functions to create an event system for changes in class variables.