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
