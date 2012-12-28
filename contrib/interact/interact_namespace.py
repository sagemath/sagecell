'''
Use:

sys._sage_.kernel_timeout = float("inf")

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

'''

from uuid import uuid4
import symtable
import re
import tokenize
from keyword import iskeyword
from collections import namedtuple

VariableUpdate = namedtuple('VariableUpdate', ['value', 'control'])

controls={}
namespaces = {}
identifier_regexp = re.compile('^'+tokenize.Name+'$')

def is_identifier(s):
    return (not iskeyword(s)) and (identifier_regexp.match(s) is not None)


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
        if isinstance(value, VariableUpdate):
            control = value.control
            value = value.value
        else:
            control = None
        dict.__setitem__(self, key, value)
        # we don't send the value because it may not be jsonalizable
        sys._sage_.display_message({'text/plain': 'variable changed',
                                    'application/sage-interact-variable': {'namespace': self.id,
                                                                           'variable': key,
                                                                           'control': control}})
    def multiset(self, d, control=None):
        for k,v in d.iteritems():
            dict.__setitem__(self, k, v)
        # we don't send the value because it may not be jsonalizable
        sys._sage_.display_message({'text/plain': 'variable changed',
                                    'application/sage-interact-variable': {'namespace': self.id,
                                                                           'variable': d.keys(),
                                                                           'control': control}})
class Control(object):
    def __init__(self):
        self.id = 'control-'+unicode(uuid4())
        global controls
        controls[self.id] = self

    def create(self):
        pass
    def variable_update(self, msg):
        pass
    def control_update(self, msg):
        pass

class Slider(Control):
    def __init__(self, var, ns, min, max):
        super(Slider, self).__init__()
        self.ns = ns
        self.min = min
        self.max = max

    def create(self):
        sys._sage_.display_message({'text/plain': 'slider',
                                    'application/sage-interact-control': {'control_id': self.id,
                                                                     'control_type': 'slider',
                                                                     'variable': self.var if isinstance(self.var, list) else [self.var],
                                                                     'namespace': self.ns.id,
                                                                     'enabled': self.enabled,
                                                                     'min': float(self.min),
                                                                     'max': float(self.max) }})

class ExpressionSlider(Slider):
    def __init__(self, expr, ns, *args, **kwargs):
        super(ExpressionSlider, self).__init__(expr, ns, *args, **kwargs)
        self.enabled = False
        # find the variables in the expression
        self.var = [v for v in symtable.symtable(expr, '<string>', 'exec').get_identifiers() if v in ns]
        self.code = compile(expr, '<string>', 'eval')

    def control_update(self, msg):
        return {'value': float(eval(self.code, globals(), self.ns))}

class VariableSlider(Slider):
    def __init__(self, var, *args, **kwargs):
        super(VariableSlider, self).__init__(var, *args, **kwargs)
        self.enabled = True
        self.var = var
    def variable_update(self, msg):
        self.ns[self.var] = VariableUpdate(value=msg['value'], control=self.id)
    def control_update(self, msg):
        return {'value': float(self.ns[self.var])}


def slider(var, ns, min, max):
    if is_identifier(var):
        return VariableSlider(var, ns, min, max)
    else:
        return ExpressionSlider(var, ns, min, max)

class ExpressionBox(Control):
    def __init__(self, var, ns):
        super(ExpressionBox, self).__init__()
        self.var = var
        self.ns = ns
    def create(self):
        sys._sage_.display_message({'text/plain': 'Expression box',
                                    'application/sage-interact-control': {'control_id': self.id,
                                                                     'control_type': 'expression_box',
                                                                     'variable': [self.var],
                                                                     'namespace': self.ns.id}})
    def variable_update(self, msg):
        self.ns[self.var] = sage_eval(msg['value'], locals=self.ns)
    def control_update(self, msg):
        return {'value': unicode(self.ns[self.var])}

class PythonCode(Control):
    def __init__(self, code, ns):
        super(PythonCode, self).__init__()
        self.var = [v for v in symtable.symtable(code, '<string>', 'exec').get_identifiers() if v in ns]
        self.ns = ns
        self.code = compile(code, '<string>', 'exec')

    def create(self):
        sys._sage_.display_message({'text/plain': 'output_region',
                                    'application/sage-interact-control': {'control_id': self.id,
                                                                     'control_type': 'output_region',
                                                                     'variable': self.var,
                                                                     'namespace': self.ns.id}})
    def control_update(self, msg):
        exec(self.code, globals(), self.ns)

class InteractFunction(Control):
    def __init__(self, f):
        super(InteractFunction, self).__init__()
        self.fn = f
        # get arguments; these should be added to the namespace with their default values
        self.ns = InteractiveNamespace()
        self.var = self.ns.keys()
        
    def create(self):
        # make controls with the same namespace

        # output region
        sys._sage_.display_message({'text/plain': 'python code control, %s'%((self.var),), 
                                    'application/sage-interact-control': {'control_id': self.id,
                                                                     'control_type': 'output_region',
                                                                     'variable': self.var,
                                                                     'namespace': self.ns.id}})
    def control_update(self, msg):
        self.fn(**ns)
