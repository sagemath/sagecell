# myextension.py

import re
import json
import ast
import logging

def tabletransform(m):
    matrix = [map(ast.literal_eval, row) for row in m['data']]
    return "matrix(QQ,%r)"%(matrix,)

def integertransform(m):
    return repr(int(m['data']))

def graphtransform(m):
    vertices = m['data']['vertices']
    edges = m['data']['edges']
    data = {i:[] for i in range(vertices)}
    for u,v in edges:
        data[u].append(v)
    return "Graph(%r)"%(data,)

widgets = {'table': tabletransform, 'integer': integertransform, 'graph': graphtransform}


def widget_handler(match):
    msg = json.loads(match.group(1))
    f = widgets.get(msg['widget'], None)
    if f is not None:
        s = f(msg)
        return s
    else:
        return u''

def widget_transformer(line, line_number):
    start=u'\u2af7'
    end=u'\u2af8'
    s = re.sub(start+'(.*?)'+end,widget_handler, line)
    return s

def load_ipython_extension(ipython):
    # The `ipython` argument is the currently active `InteractiveShell`
    # instance, which can be used in any way. This allows you to register
    # new magics or aliases, for example.
    ipython.input_splitter.transforms.insert(0,widget_transformer)

def unload_ipython_extension(ipython):
    # If you want your extension to be unloadable, put that logic here.
    pass

