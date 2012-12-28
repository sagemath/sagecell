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
        self.ns = InteractiveNamespace()
        # TODO: the argument names of f should be added to self.ns, along with default values
        self.var = self.ns.keys()

    def create(self):
        # TODO: make controls with the same namespace, using the existing automatic rules
        # TODO: lay these out according to whatever layout is specified, or the automatic layout rules

        # output region is an output_region control that depends on all of the function inputs
        sys._sage_.display_message({'text/plain': 'python code control, %s'%((self.var),), 
                                    'application/sage-interact-control': {'control_id': self.id,
                                                                     'control_type': 'output_region',
                                                                     'variable': self.var,
                                                                     'namespace': self.ns.id}})
    def control_update(self, msg):
        # run the function with the appropriate arguments
        self.fn(**ns)

"""
Point2d:
http://aleph.sagemath.org/?z=eJytV01v4zYQPce_gmukELVQZMdpD3XWBbLJHrZAi0WxPaWBoUi0zY1MCiKVRDX83_tGH5RkZzc5VAdbIoczj28eh6QpTbg00VoswweRK5EurdwKXVi2YKtUR5aPpVqN_RHeE-5trM3MfDLJo6dwLe2muA9jvZ18i4xW6xzDJuQrFmk6kcqKPIrt2VYYajSTWCuby3vX416WKoJRFsUizErPH9ETp5Ex7IuGzeyGX9NQnfrzEcOTiBVbLqWSdrnkRqSrgD1G-XmAn1nAlGnM6DFFJnLeuAkYGfuhG-t3dugIyQnmTX9HHbO6YzbsUAbNyjhUcS4iKypMfRAdyYk0WRqVy4YUvvOseLYTtEnlzZk3u6nn7AVu9I8eL8qyVMaRlVpV1J852uOaMjjdec37Uib4rIDL5G0BXkfQ-rZlJmgGWcV18sYJvO4fpMvoPiXfty5LQZeXu_8rkBNhy5EyoGm_9112WyjLIkvaNAdsa9b9XDcjt0VqpRGW7xzoOZne0oTOvbveDLr2mXe3D1jD6KJJVBe_pfoH4XNhi1wh5VUUN5GOOQSuIx33ze72o43dpjwfj8ejDybOZWZ_G6GHxQI6b5d2WFiZhrXUP6ViK5S9HI0mkwrA3yoRuYl1LsJvhp2HP4cXbRcVD9SOwll8M6HO1203j302m05_PZtNz2fsd5GLbcmuzOZBqMgE7EbHBYW6TnWRsM8qDo9Dsm1UsnvBVrkQacmw2KjgFFYkrIrK7EawPz5_ZVgzQhlRufirosywiK0KFdNKCmAX2YA9bYRiUj3qB5HgS6Yp0yqtIsDveg2ICYss22pj0RMLpAEOkyKXag1_a_kIB09SJfqJ6RWj0hrChhi1m1xbmxKvbVhOL4gTSeuzXZXSintkHTUiYFG-Bg9NfQ6QagONXTq7LBePUhdUkaZda4ok5f0grWvWH6DEE7uB5WXT1W0CqkjTtrWO2DgLqfSUfIDOry339V-jxRciEzAFTo4DUw8Sj2pIFC4qMtgZ42R95hD7rXkTHYZ2I03bSlDQhL9KMa5drhjvnH8ATx0k-EpFlH-tJ84bAlyg71EyZFE_XfZW4tvIAl1MpEZU6N61cXu4usAoJy2-Kq1BR1XnzOWqIr8vkiot-Kket5g_NxtGs8WasNks-wv-yOaggSP8qw7DDIrXtE00taOnSsZR0aKA3ac6fsA21dc_rcVBguktJCox9UrbVYPBjgpPIdjJQFAs-DiRj-OA7WQyZ-Q-7LbBvd-L9ZLXMDaG7zZCrjcWm9r5dJo9e1QDErvpfd_rHGWFGrJnZnQqE7iN4gd0ZVGSIDHo-wWm-8MowAHkpw6n75NGhEq-aj6E8sLII3QH4F7DtoX-pELXtAcNvmElwlSv-e0QQtAPHgyh1Ci4f-d3RafeoPpVR6ASQveFpMye4Knlzqp27AISeKL0E33Bohbv5b62JAG49BpQ5E5P3sGOjKlVQ2gUY7su30cCqE-McwAKM20kYQxTsbJVO3ZkJPis32d1th86H9dCG8_ZKSn7ueQDnJtIJcBVGwWDOfjEeO2lXa8DRpM8Wq9pVnzHmhRQGZsfSBQHhSI3mjK81Y809_r7CpY74MUkApoS_veBi0fO52734TVvAc3Xf-EgZSo_tVHjgsDv31A_esv9SA6o5-1hK3CnKnfweW39k3L6hMGevVssDoafDKrCUDbDgxSYG0jlwDduFC3YOXsB99y91TSffEccPTRH4uj6_EZlmOd4CHOZC-whcOkWVbWd0LLaChuRwN3i6va7xiY0NrK0SYEnTz94reVJJT5oc1BZPNINTojt4HoXaU7eHjTh1SvkuH_WaLuFsG8_9m2Z2UM9TjzuBtiEN7fu_nD3ww2oEdnl6MOkPafi0BoSRUgO9069wPvn1PPpMlld0loPOJL92eaQPy_Op0G5uPBHGY5slnnP3uhqYVAqcWn0qIgqnLim9fIYXTX7Fq6NrX3pjT46-_LA_mPP_hoQ2sssOSZjXFRH1z0b0Mc9i_uvWdABvIW0-Ak-S_x6P_HnoATWVFv-_N5Ixcv3FoLhNji7CC78YCXXRv4rFhcB2SwrKg2-II6MZg4JUY2AdjDn0Gz0E-JSrJvFl9JutLrWCe4VFbKbDtl_aK31JQ==&lang=sage
"""
