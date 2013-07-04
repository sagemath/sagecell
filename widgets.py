# myextension.py

import re
import json
import ast
import logging
from uuid import uuid4
from sage.all import matrix, QQ, Graph

class WidgetTransform(object):
    def __init__(self, mesg):
        self.mesg = mesg
    def object(self):
        return self._object

class TableTransform(WidgetTransform):
    def __init__(self, mesg):
        super(TableTransform, self).__init__(mesg)
        data = [map(ast.literal_eval, row) for row in mesg['data']]
        self._object = matrix(QQ, data)

class IntegerTransform(WidgetTransform):
    def __init__(self, mesg):
        self._object = int(mesg['data'])

class GraphTransform(WidgetTransform):
    def __init__(self, mesg):
        vertices = mesg['data']['vertices']
        edges = mesg['data']['edges']
        data = {i:[] for i in range(vertices)}
        for u,v in edges:
            data[u].append(v)
        self._object = Graph(data)

widgets = {'table': TableTransform, 'integer': IntegerTransform, 'graph': GraphTransform}

import sys
sys._sage_.widgets={}
def widget_handler(match):
    msg = json.loads(match.group(1))
    f = widgets.get(msg['widget'], None)
    if f is not None:
        i = str(uuid4())
        sys._sage_.widgets[i] = f(msg)
        s = "sys._sage_.widgets[%r].object()"%i
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

