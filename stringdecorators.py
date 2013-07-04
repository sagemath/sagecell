# myextension.py
from IPython.core.inputtransformer import CoroutineInputTransformer
import token

def string_decorator_defaults(func):
    def my_wrap(*args,**kwds):
        if len(kwds)==0 and len(args)==1 and isinstance(args[0],basestring):
            # call without parentheses
            return func(*args)
        else:
            return lambda f: func(f, *args, **kwds)
    return my_wrap

@CoroutineInputTransformer.wrap
def stringdecorator(end_on_blank_line=False):
    """Captures & transforms cell magics.
    
    After a cell magic is started, this stores up any lines it gets until it is
    reset (sent None).
    """
    line = ''
    from tokenize import generate_tokens
    while True:
        line = (yield line)
        if (not line) or (not line.startswith('%')):
            continue
        g = generate_tokens(iter([line]).next)
        code,value,start,end,_ = g.next()
        if not (code==token.OP and value == '%'):
            continue
        code,value,start,end,_ = g.next()
        cell_decorator=False
        if code==token.OP and value == '%':
            cell_decorator=True
            code,value,start,end,_ = g.next()
        if not (code==token.NAME):
            continue
        func_start=start[1]
        func_end=end[1]
        # the last question: is there an open paren?
        code,value,start,end,_ = g.next()
        if (code==token.OP and value=='('):
            #find closing paren; that will be func_end
            parens=1
            while parens>0 and code!=token.ENDMARKER:
                code,value,start,end,_ = g.next()
                if code==token.OP:
                    if value=='(':
                        parens+=1
                    elif value==')':
                        parens-=1
            if parens>0:
                # couldn't find a matching closing paren
                continue
            func_end = end[1]
        decorator = line[func_start:func_end]
        string = line[func_end:].strip()
        if len(string)==0 or cell_decorator:
            body = []
            if len(string)>0: body.append(string)
            line = (yield None)
            while (line is not None) and ((line.strip() != '')
                                          or not end_on_blank_line):
                body.append(line)
                line = (yield None)
            string = '\n'.join(body)
        line = "%s(%r)"%(decorator,string)

def load_ipython_extension(ipython):
    # The `ipython` argument is the currently active `InteractiveShell`
    # instance, which can be used in any way. This allows you to register
    # new magics or aliases, for example.
    ipython.input_splitter.physical_line_transforms.append(stringdecorator(end_on_blank_line=True))
    ipython.input_transformer_manager.physical_line_transforms.append(stringdecorator(end_on_blank_line=False))

def unload_ipython_extension(ipython):
    # If you want your extension to be unloadable, put that logic here.
    pass

