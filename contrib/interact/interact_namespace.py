class DictHook(dict):
    """
    Allows you to set custom hooks for dict methods.
 
    Examples::
 
        sage: from dicthook import DictHook
        sage: d=DictHook()
        sage: def printop(op, *args): print op, args
        sage: from functools import partial
        sage: d.sethook = partial(printop, 'set')
        sage: d.gethook = partial(printop, 'get')
        sage: d.delhook = partial(printop, 'del')
        sage: d['a']=4
        set ('a', 4)
        sage: d['a']
        get ('a',)
        4
        sage: del d['a']
        del ('a',)
        sage: d
        DictHook({})
 
    """
    def __init__(self, *args, **kwargs):
        dict.__init__(self,*args,**kwargs)
        self.sethook = None
        self.gethook = None
        self.delhook = None
 
    def __getitem__(self, key):
        val = dict.__getitem__(self, key)
        if self.gethook is not None:
            self.gethook(key)
        return val
 
    def __setitem__(self, key, val):
        if self.sethook is not None:
            self.sethook(key,val)
        dict.__setitem__(self, key, val)
 
    def __delitem__(self, key):
        if self.delhook is not None:
            self.delhook(key)
        dict.__delitem__(self, key)
 
    def __repr__(self):
        dictrepr = dict.__repr__(self)
        return '%s(%s)' % (type(self).__name__, dictrepr)

import symtable
def describe_symtable(st, recursive=True, indent=0):
    "from http://eli.thegreenplace.net/2010/09/18/python-internals-symbol-tables-part-1/"
    def print_d(s, *args):
        prefix = ' ' * indent
        print prefix + s, args

    assert isinstance(st, symtable.SymbolTable)
    print_d('Symtable: type=%s, id=%s, name=%s' % (
                st.get_type(), st.get_id(), st.get_name()))
    print_d('  nested:', st.is_nested())
    print_d('  has children:', st.has_children())
    print_d('  identifiers:', list(st.get_identifiers()))
    for i in st.get_symbols():
        describe_symbol(i, indent)

    if recursive:
        for child_st in st.get_children():
            describe_symtable(child_st, recursive, indent + 5)

from pprint import pprint
def describe_symbol(sym, indent=0):
    "from http://eli.thegreenplace.net/2010/09/18/python-internals-symbol-tables-part-1/"
    def print_d(s, *args):
        prefix = ' ' * indent
        print prefix + s, args

    assert type(sym) == symtable.Symbol
    print_d("Symbol:", sym.get_name())

    for prop in [
            'referenced', 'imported', 'parameter',
            'global', 'declared_global', 'local',
            'free', 'assigned', 'namespace']:
        if getattr(sym, 'is_' + prop)():
            print_d('    is', prop)

import collections
import itertools
class DictProxy(collections.MutableMapping):
    """
    Maintain a list of dictionaries.  Get happens in the first dictionary possible.  Set happens in the first dictionary that has the key
    otherwise in the first dictionary.  Del happens in the first dictionary that has the key.
    """
    def __init__(self, *args):
        self.d = args
    def __getitem__(self, name):
        for d in self.d:
            try:
                return d[name]
            except KeyError:
                continue
        raise KeyError
    def __setitem__(self, name, value):
        for d in self.d:
            if name in d:
                d[name]=value
                break
        else:
            self.d[0][name]=value
    def __delitem__(self, name):
        for d in self.d:
            try:
                del d[name]
                break
            except KeyError:
                continue
        else:
            raise KeyError
    def __contains__(self, name):
        print "Contains"
        for d in self.d:
            if name in d:
                return True
        else:
            print "did not find %s in any dict"%(name,)
            raise KeyError
    def __iter__(self):
        already = set()
        for i in itertools.chain(*self.d):
            if i not in already:
                already.add(i)
                yield i
    def __len__(self):
        return len([i for i in self])


def interactive(code, ns,debug=False):
    # set output region, send code string and identifier of the namespace
    if debug:
        st=symtable.symtable(code,'<string>', 'exec')
        describe_symtable(st)
        print set(i for i in st.get_identifiers() if i in ns)
    exec code in globals(), ns

def interactive_namespace(**kwargs):
    ns = DictHook(**kwargs)
    def f(k,v):
        print "Setting %s = %s"%(k,v)
    ns.sethook = f
    return ns

def slider(var, (beg,end)):
    try:
        var = float(var)
        html("""$("div").slider()""")
    except TypeError:
        varnamevar,ns = var
        val = ns[varname]
        html(slider_html_interactive(val, ns, varname))
def slider_html(
             
        

"""
ns = interactive_namespace(x=10, y='y variable')


"""

html("""<div id="asdf" style="max-width: 50%"></div><script>
(function() {
var elt = \$("#asdf")
var session = sagecell.findSession(elt);
elt.slider({
    change: function(event, ui) {
    session.send_message('custom_type', {'SLIDER': ui.value}, {"output": \$.proxy(session.handle_output, session),
        'custom_reply': console.log});
    }
    });
console.log(session);
})()</script>""")

@interact
def _(n=(0,1)):
    print n

def handler_wrapper(msg_type):
    import sys
    def register(f):
        def g(stream, ident, msg):
            return f(msg)
        sys._sage_.register_handler(msg_type, g)
    return register
        
        
@handler_wrapper("custom_type")
def update_interact_msg(msg):
    print msg['content']['SLIDER']
    return {'x': msg['content']['SLIDER']}


"""
http://localhost:8080/?z=eJx1U01vnDAQvfMrLKcVtkRJKqWX7W6UQ3uo1FNzTCPkwMBaMQbZhl204r93DJilVeODxXjevDdf2MGmmRUVZOkbGA0qc7KGpnPkQErVCMeo1CXl0dHVilFK94XsiSwOVNiipMS6QcGB1uL86SQLd9yRL3cf6cP-FmEPe5sb2bqHiJWdzp1sNOPkEvXCEFBe4fcHRm8mIj69WrAWUejxKeWgVFpKXTzNzwyD-NcI79QqWYBhl4jgyY9CV7Ajqwj0oF1COunVPGLhTS3oIqvRQHYW5511TZ25oYU4IZf46eePb99_xTsMTHuhOhjxlWIv2s7RHSabtqY5DyywoWyhIJsBSRDhySTpT1Aw0KoBefNG20ZBqppqxEI8ZJxvtDbOoICvI2d8f7v0EdvPo-hRagdG5C4qoCQZ0wd2l3zmfDdRtQbdREeTc87QZCcj2hb7VdtqKnfByrptjCN2sJPpIwxU0iI9KxdMcGBSzoCoExz-1F3k2kD8MeA6o0npZfjqsdcNC-TZkteaT0KWgIUiAFeS68fjvzXRzRixPT7Xri2Egyz0KUMZdk137hDazzH23GEx8ctzGP7LNo1LfMapvYcc5x4HFdkDy5sCa9F2UbrBncBZwInMO0JeVZO_bVxdS4Re0l3Xd_HnQinijvBf91oa_omdll6XdZ0sUn_dM45rEgY3h7PNrE7SHcO24t_gBAIEu8QbUix7Y41L8F_ThjPkxAsjklSqeRXKMu6rDwWKHt4rL4r-AKzraQ8=&lang=sage

TODO:

* register handler on js side (see Brian's pull request) for a display_data
  - gets list of outputs that depend on the given variable
  - sends requests for updates on those outputs
* implement the variable-changed message
* implement a namespace variable control like a slider

CONTROLS (including a "python control")

* message to create a control, along with the variables to listen for changes to
* in python:
   - create control object
   - create an update function
   - send the js control message

* in js:
   - create the control,
   - register for necessary messages

When a js control needs to notify a change in a variable:
   - send a message back to the python control to update the variable
   - upon return with status ok, trigger an event telling controls to update

When a js control receives a variable-change event:
   - ignore if it's an event we already took care of
   - sends a message to Sage to update the control

"""
sys._sage_.kernel_timeout = float("inf")
from uuid import uuid4
controls={}
namespaces = {}

def handler_wrapper(msg_type):
    import sys
    def register(f):
        def g(stream, ident, msg):
            return f(msg['content'])
        sys._sage_.register_handler(msg_type, g)
    return register

@handler_wrapper("variable_update")
def update_interact_msg(msg):
    return controls[msg['control_id']].variable_update(msg)

@handler_wrapper("control_update")
def update_interact_msg(msg):
    return controls[msg['control_id']].control_update(msg)

class InteractiveNamespace(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self,*args,**kwargs)
        self.id = 'namespace-'+unicode(uuid4())
        global namespaces
        namespaces[self.id] = self
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        sys._sage_.display_message({'text/plain': 'variable changed',
                                    'application/sage-interact-variable': {'namespace': self.id,
                                                                     'variable': key,
                                                                     'value': value}})
class slider(object):
    def __init__(self, var, ns, min, max, code=None):
        self.var = var
        self.ns = ns
        self.min = min
        self.max = max
        global controls
        self.id = 'control-'+unicode(uuid4())
        controls[self.id] = self
        self.code = code
        
    def create(self):
        sys._sage_.display_message({'text/plain': 'slider control, %s'%((self.var,self.min,self.max),), 
                                    'application/sage-interact-control': {'control_id': self.id,
                                                                     'control_type': 'slider',
                                                                     'variable': self.var,
                                                                     'namespace': self.ns.id,
                                                                     'range': map(float, (self.min, self.max))}})
        
    def variable_update(self, msg):
        if len(self.var)==1:
            self.ns[self.var[0]] = msg['value']

    def control_update(self, msg):
        if self.code is None and len(self.var)==1:
            return {'value': self.ns[self.var[0]]}
        else:
            return {'value': eval(self.code,globals(), self.ns)}

class input(object):
    def __init__(self, var, ns, code=None):
        self.var = var
        self.ns = ns
        global controls
        self.id = 'control-'+unicode(uuid4())
        controls[self.id] = self
        self.code = code
        
    def create(self):
        sys._sage_.display_message({'text/plain': 'slider control, %s'%((self.var),), 
                                    'application/sage-interact-control': {'control_id': self.id,
                                                                     'control_type': 'input',
                                                                     'variable': self.var,
                                                                     'namespace': self.ns.id}})
        
    def variable_update(self, msg):
        if len(self.var)==1:
            self.ns[self.var[0]] = int(msg['value'])

    def control_update(self, msg):
        if self.code is None and len(self.var)==1:
            return {'value': self.ns[self.var[0]]}
        else:
            return {'value': eval(self.code,globals(), self.ns)}


class pythoncode(object):
    def __init__(self, var, ns, code):
        self.var = var
        self.ns = ns
        global controls
        self.id = 'control-'+unicode(uuid4())
        controls[self.id] = self
        self.code = code
        
    def create(self):
        sys._sage_.display_message({'text/plain': 'python code control, %s'%((self.var),), 
                                    'application/sage-interact-control': {'control_id': self.id,
                                                                     'control_type': 'pythoncode',
                                                                     'variable': self.var,
                                                                     'namespace': self.ns.id}})
        
    def variable_update(self, msg):
        pass

    def control_update(self, msg):
        exec self.code in globals(),self.ns

ns = InteractiveNamespace(x=10,y=3)
A=slider('x', ns, 0, 2)
A.create()
B=slider('y', ns, 0, 2)
B.create()
C=slider('xy', ns, 0, 2, 'x-y')
C.create()
var('t')
E=pythoncode('x',ns,"""
print x
show(plot(sin(x*t), (t,-3,3),plot_points=3,figsize=2))
print 'hi'
""")
E.create()
D=input('xy',ns,'x')
D.create()
