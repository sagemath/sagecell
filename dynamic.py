
#TODO: Need some way of having controls without output and without
#having a 'dirty' indicator.  Just javascript controls.  This should
#be an argument to interact, like @interact(output=False) or something

# also, need an easy way to make controls read-only (especially if
# they are just displaying a value)

def _dynamic(var, control=None):
    if control is None:
        control = sys._sage_.namespace.get(var,'')

    # Workaround for not having the nonlocal statement in python 2.x
    old_value = [sys._sage_.namespace.get(var,None)]

    @interact(layout=[[(var,12)]], output=False)
    def f(self, x=(var,control)):
        if x is not old_value[0]:
            # avoid infinite recursion: if control is already set,
            # leave it alone
            sys._sage_.namespace[var]=x
        old_value[0] = x

    def g(var,y):
        f.x = y
    sys._sage_.namespace.on(var,'change', g)

    if var in sys._sage_.namespace:
        g(var, sys._sage_.namespace[var])

def dynamic(*args, **kwds):
    """
    Make variables in the global namespace dynamically linked to a control from the
    interact label (see the documentation for interact).

    EXAMPLES:

    Make a control linked to a variable that doesn't yet exist::

         dynamic('newname')

    Make a slider and a selector, linked to t and x::

         dynamic(t=(1..10), x=[1,2,3,4])
         t = 5          # this changes the control
    """
    for var in args:
        if not isinstance(var, str):
            i = id(var)
            for k,v in sys._sage_.namespace.iteritems():
                if id(v) == i:
                    _dynamic(k)
            return
        else:
            _dynamic(var)

    for var, control in kwds.iteritems():
        _dynamic(var, control)


def dynamicexpression(v, vars):
    """
    sage: t=5
    sage: dynamic(t)
    sage: dynamicexpression('2*t','t')
    """
    # control
    @interact(output=False, readonly=True)
    def f(t=(0,2)):
        pass

    # update function
    def g(var,val):
        f.t = eval(v)

    for vv in vars:
        sys._sage_.namespace.on(vv,'change',g)

