###############################################################################
# Copyright (c) 2013, William Stein
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are those
# of the authors and should not be interpreted as representing official policies,
# either expressed or implied, of the FreeBSD Project.
###############################################################################

import os
import sys
from uuid import uuid4

from comm import create_comm
import matplotlib.figure


def uuid():
    return str(uuid4())


def sagecell_comm(*args, **kwargs):
    sys._sage_.reset_kernel_timeout(float('inf'))
    return create_comm(*args, **kwargs)

###
# Interactive 2d Graphics
###

STORED_INTERACTIVE_GRAPHICS = [];
class InteractiveGraphics(object):
    def __init__(self, g, events=None, renderer="sage"):
        self._g = g
        if events is None:
            events = {}
        self._events = events
        self.renderer=renderer

    def figure(self, **kwds):
        if isinstance(self._g, matplotlib.figure.Figure):
            return self._g

        options = dict()
        options.update(self._g.SHOW_OPTIONS)
        options.update(self._g._extra_kwds)
        options.update(kwds)
        options.pop('dpi'); options.pop('transparent'); options.pop('fig_tight')
        fig = self._g.matplotlib(**options)

        return fig

    def save(self, filename, **kwds):
        if isinstance(self._g, matplotlib.figure.Figure):
            self._g.savefig(filename)
        else:
            # When fig_tight=True (the default), the margins are very slightly different.
            # I don't know how to properly account for this yet (or even if it is possible),
            # since it only happens at figsize time -- do "a=plot(sin); a.save??".
            # So for interactive graphics, we just set this to false no matter what.
            kwds['fig_tight'] = False
            self._g.save(filename, **kwds)

    def show(self, **kwds):
        STORED_INTERACTIVE_GRAPHICS.append(self);
        if self.renderer=="sage":
            return self.show_sage(**kwds)
        elif self.renderer=="matplotlib":
            return self.show_matplotlib(**kwds)

    def show_matplotlib(self, **kwds):
        self.fig = self.figure(**kwds)
        CommFigure(self.fig)
        for k,v in self._events.items():
            self.fig.canvas.mpl_connect(k,v)

    def show_sage(self, **kwds):
        fig = self.figure(**kwds)
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        canvas = FigureCanvasAgg(fig)
        fig.set_canvas(canvas)
        fig.tight_layout()  # critical, since sage does this -- if not, coords all wrong
        ax = fig.axes[0]
        # upper left data coordinates
        xmin, ymax = ax.transData.inverted().transform( fig.transFigure.transform((0,1)) )
        # lower right data coordinates
        xmax, ymin = ax.transData.inverted().transform( fig.transFigure.transform((1,0)) )

        def to_data_coords(p):
            # 0<=x,y<=1
            return ((xmax-xmin)*p[0] + xmin, (ymax-ymin)*(1-p[1]) + ymin)
        def on_msg(msg):
            data = msg['content']['data']
            x,y = data['x'], data['y']
            eventType = data['eventType']
            if eventType in self._events:
                self._events[eventType](to_data_coords([x,y]))
        file_id = uuid()
        if kwds.get('svg',False):
            filename = '%s.svg'%file_id
            del kwds['svg']
        else:
            filename = '%s.png'%file_id

        fig.savefig(filename)
        self.comm = sagecell_comm(data={"filename": filename}, target_name='graphicswidget')
        sys._sage_.sent_files[filename] = os.path.getmtime(filename)
        self.comm.on_msg(on_msg)


# Matplotlib's comm-based live plots.  See https://github.com/matplotlib/matplotlib/pull/2524
from matplotlib.backends.backend_webagg_core import (
    new_figure_manager_given_figure)
import json

from base64 import b64encode

class CommFigure(object):
    def __init__(self, figure):
        self.figure = figure
        self.manager = new_figure_manager_given_figure(id(figure), figure)
        self.comm = CommSocket(self.manager)
        self.comm.open()


class CommSocket(object):
    """
    A websocket for interactive communication between the plot in
    the browser and the server.

    In addition to the methods required by tornado, it is required to
    have two callback methods:

        - ``send_json(json_content)`` is called by matplotlib when
          it needs to send json to the browser.  `json_content` is
          a JSON tree (Python dictionary), and it is the responsibility
          of this implementation to encode it as a string to send over
          the socket.

        - ``send_binary(blob)`` is called to send binary image data
          to the browser.
    """
    supports_binary = False

    def __init__(self, manager):
        self.manager = manager
        self.uuid = uuid()
        #display(HTML("<div id='%s'></div>"%self.uuid))
        self.comm = sagecell_comm('matplotlib', data={'id': self.uuid})

    def open(self):
        # Register the websocket with the FigureManager.
        self.manager.add_web_socket(self)
        self.comm.on_msg(self.on_message)

    def on_close(self):
        # When the socket is closed, deregister the websocket with
        # the FigureManager.

        self.manager.remove_web_socket(self)
        self.comm.close()

    def send_json(self, content):
        self.comm.send({'data': json.dumps(content)})

    def send_binary(self, blob):
        data_uri = "data:image/png;base64,{0}".format(b64encode(blob))
        self.comm.send({'data': data_uri})

    def on_message(self, message):
        # The 'supports_binary' message is relevant to the
        # websocket itself.  The other messages get passed along
        # to matplotlib as-is.

        # Every message has a "type" and a "figure_id".
        message = json.loads(message['content']['data'])
        if message['type'] == 'supports_binary':
            self.supports_binary = message['value']
        else:
            self.manager.handle_json(message)

