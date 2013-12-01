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
"""
TODO for 3d graphics:

[ ] implement aspect ratio

[X] some z-fighting going on:  fixed in 99d8f2e7e9365088f1a031f289f75fd60791752a
sage: x, y = var('x y')
sage: W = plot3d(sin(pi*((x)^2+(y)^2))/2,(x,-1,1),(y,-1,1), frame=False, color='purple', opacity=0.8) 
sage: S = sphere((0,0,0),size=0.3, color='red', aspect_ratio=[1,1,1])
sage: threejs(W + S, figsize=8)

[X] the grid sometimes is too much---make it transparent -- fixed in 0c5fddfd08db2da3322242e130acd0fa52933a83

[ ] by default, make it shiny a bit

[ ] Figure out when to draw a point as a particle system, and when to draw as a small sphere.  A big particle is just a square, so it's not so pretty if you just have one point
sage: threejs(point3d((4,3,2),size=20,color='red',opacity=.5))

[ ] canvas2d lacks axis labels


"""

from uuid import uuid4
def uuid():
    return str(uuid4())

#######################################################
# Three.js based plotting
#######################################################

from comm import SageCellComm as Comm
#from uuid import uuid4 as uuid
noneint = lambda n : n if n is None else int(n)
class ThreeJS(object):
    def __init__(self, renderer=None, width=None, height=None,
                 frame=True, camera_distance=10.0, background=None, foreground=None, **ignored):
        """
        INPUT:

        - renderer -- None (automatic), 'canvas2d', or 'webgl'
        - width    -- None (automatic) or an integer
        - height   -- None (automatic) or an integer
        - frame    -- bool (default: True); draw a frame that includes every object.
        - camera_distance -- float (default: 10); default camera distance.
        - background -- None (transparent); otherwise a color such as 'black' or 'white'
        - foreground -- None (automatic = black if transparent; otherwise opposite of background);
           or a color; this is used for drawing the frame and axes labels.
        """
        self.id = uuid()
        self.comm = Comm(data={'renderer':renderer,
                                     'width':noneint(width),
                                     'height':noneint(height),
                                     'camera_distance':float(camera_distance),
                                     'background':background,
                                     'foreground':foreground
                                     }, target_name='threejs')
        self.comm.on_msg(self.on_msg)
        self._graphics = []

    def on_msg(self, msg):
        data = msg['content']['data']
        x,y = data['x'], data['y']
        print (x,y)
    def send(self, msg_type, data):
        d = {'msg_type': msg_type}
        d.update(data)
        self.comm.send(d)

    def lights(self, lights):
        self.send('lights', {'lights': [l.scenetree_json() for l in lights]})

    def add(self, graphics3d, **kwds):
        kwds = graphics3d._process_viewing_options(kwds)
        self._frame = kwds.get('frame',False)
        self._graphics.append(graphics3d)
        obj = graphics3d_to_jsonable(graphics3d)
        self.send('add', {'obj': obj,
                        'wireframe':jsonable(kwds.get('wireframe'))})
        self.set_frame(draw = self._frame)  # update the frame
    def render_scene(self, force=True):
        self.send('render', {'force':force})

    def add_text(self, pos, text, fontsize=18, fontface='Arial', sprite_alignment='topLeft'):
        self.send('add_text',
                   obj={'pos':[float(pos[0]), float(pos[1]), float(pos[2])],
                        'text':str(text),
                        'fontsize':int(fontsize),'fontface':str(fontface),
                        'sprite_alignment':str(sprite_alignment)})

    def animate(self, fps=None, stop=None, mouseover=True):
        self.send('animate', {'fps':noneint(fps), 'stop':stop, 'mouseover':mouseover})

    def set_frame(self, xmin=None, xmax=None, ymin=None, ymax=None, zmin=None, zmax=None, color=None, draw=True):
        if not self._graphics:
            xmin, xmax, ymin, ymax, zmin, zmax = -1,1,-1,1,-1,1
        else:
            b = self._graphics[0].bounding_box()
            xmin, xmax, ymin, ymax, zmin, zmax = b[0][0], b[1][0], b[0][1], b[1][1], b[0][2], b[1][2]
            for g in self._graphics[1:]:
                b = g.bounding_box()
                xmin, xmax, ymin, ymax, zmin, zmax = (
                      min(xmin,b[0][0]), max(b[1][0],xmax),
                      min(b[0][1],ymin), max(b[1][1],ymax),
                      min(b[0][2],zmin), max(b[1][2],zmax))

        self.send('set_frame', {
                      'xmin':float(xmin), 'xmax':float(xmax),
                      'ymin':float(ymin), 'ymax':float(ymax),
                      'zmin':float(zmin), 'zmax':float(zmax), 'color':color, 'draw':draw})


def show_3d_plot_using_threejs(g, **kwds):
    b = g.bounding_box()
    if 'camera_distance' not in kwds:
        kwds['camera_distance'] = 2 * max([abs(x) for x in list(b[0])+list(b[1])])
    import sage.plot.plot3d.light as light
    lights=kwds.pop('lights', light.DEFAULTS['sage'])
    t = ThreeJS(**kwds)
    t.lights(lights)
    t.set_frame(b[0][0],b[1][0],b[0][1],b[1][1],b[0][2],b[1][2],draw=False)
    t.add(g, **kwds)
    t.animate()
    return t


import sage.plot.plot3d.index_face_set
import sage.plot.plot3d.shapes
import sage.plot.plot3d.base
import sage.plot.plot3d.shapes2
from sage.structure.element import Element

def jsonable(x):
    if isinstance(x, Element):
        return float(x)
    return x

def graphics3d_to_jsonable(p):
    return p.scenetree_json()

def old_graphics3d_to_jsonable(p):

    obj_list = []

    def parse_obj(obj):
        model = []
        for item in obj.split("\n"):
            if "usemtl" in item:
                tmp = str(item.strip())
                tmp_list = {}
                try:
                    tmp_list = {"material_name":name,"face3":face3,"face4":face4,"face5":face5}
                    model.append(tmp_list)
                except (ValueError,UnboundLocalError):
                    pass
                face3 = []
                face4 = []
                face5 = []
                tmp_list = []
                name = tmp.split()[1]


            if "f" in item:
                tmp = str(item.strip())
                face_num = len(tmp.split())
                for t in tmp.split():
                    if(face_num ==4):
                        try:
                            face3.append(int(t))
                        except ValueError:
                            pass

                    elif(face_num ==6):
                        try:
                            face5.append(int(t))
                        except ValueError:
                            pass
                    else:
                        try:
                            face4.append(int(t))
                        except ValueError:
                            pass

        model.append({"material_name":name,"face3":face3,"face4":face4,"face5":face5})

        return model


    def parse_texture(p):
        texture_dict = []
        textures = p.texture_set()
        for item in range(0,len(textures)):
            texture_pop = textures.pop()
            string = str(texture_pop)
            item = string.split("(")[1]
            name = item.split(",")[0]
            color = texture_pop.color
            tmp_dict = {"name":name,"color":color}
            texture_dict.append(tmp_dict)

        return texture_dict

    def get_color(name,texture_set):
        for item in range(0,len(texture_set)):
            if(texture_set[item]["name"] == name):
                color = texture_set[item]["color"]
                color_list = [color[0],color[1],color[2]]
                break
            else:
                color_list = []
        return color_list

    def parse_mtl(p):
        mtl = p.mtl_str()
        all_material = []
        for item in mtl.split("\n"):
            if "newmtl" in item:
                tmp = str(item.strip())
                tmp_list = []
                try:
                    texture_set = parse_texture(p)
                    color = get_color(name,texture_set)
                except (ValueError,UnboundLocalError):
                    pass
                try:
                    tmp_list = {"name":name,"ambient":ambient, "specular":specular, "diffuse":diffuse, "illum":illum_list[0],
                               "shininess":shininess_list[0],"opacity":opacity_diffuse[3],"color":color}
                    all_material.append(tmp_list)
                except (ValueError,UnboundLocalError):
                    pass

                ambient = []
                specular = []
                diffuse = []
                illum_list = []
                shininess_list = []
                opacity_list = []
                opacity_diffuse = []
                tmp_list = []
                name = tmp.split()[1]

            if "Ka" in item:
                tmp = str(item.strip())
                for t in tmp.split():
                    try:
                        ambient.append(float(t))
                    except ValueError:
                        pass

            if "Ks" in item:
                tmp = str(item.strip())
                for t in tmp.split():
                    try:
                        specular.append(float(t))
                    except ValueError:
                        pass

            if "Kd" in item:
                tmp = str(item.strip())
                for t in tmp.split():
                    try:
                        diffuse.append(float(t))
                    except ValueError:
                        pass

            if "illum" in item:
                tmp = str(item.strip())
                for t in tmp.split():
                    try:
                        illum_list.append(float(t))
                    except ValueError:
                        pass



            if "Ns" in item:
                tmp = str(item.strip())
                for t in tmp.split():
                    try:
                        shininess_list.append(float(t))
                    except ValueError:
                        pass

            if "d" in item:
                tmp = str(item.strip())
                for t in tmp.split():
                    try:
                        opacity_diffuse.append(float(t))
                    except ValueError:
                        pass

        try:
            color = list(p.all[0].texture.color.rgb())
        except (ValueError, AttributeError):
            pass

        try:
            texture_set = parse_texture(p)
            color = get_color(name,texture_set)
        except (ValueError, AttributeError):
            color = []
            #pass

        tmp_list = {"name":name,"ambient":ambient, "specular":specular, "diffuse":diffuse, "illum":illum_list[0],
                   "shininess":shininess_list[0],"opacity":opacity_diffuse[3],"color":color}
        all_material.append(tmp_list)

        return all_material

    def convert_index_face_set(p):
        face_geometry = parse_obj(p.obj())
        material = parse_mtl(p)
        vertex_geometry = []
        obj  = p.obj()
        for item in obj.split("\n"):
            if "v" in item:
                tmp = str(item.strip())
                for t in tmp.split():
                    try:
                        vertex_geometry.append(float(t))
                    except ValueError:
                        pass
        myobj = {"face_geometry":face_geometry,"type":'index_face_set',"vertex_geometry":vertex_geometry,"material":material}
        for e in ['wireframe', 'mesh']:
            if p._extra_kwds is not None:
                v = p._extra_kwds.get(e, None)
                if v is not None:
                    myobj[e] = jsonable(v)
        obj_list.append(myobj)

    def convert_text3d(p):
        text3d_sub_obj = p.all[0]
        text_content = text3d_sub_obj.string
        color = "#" + text3d_sub_obj.get_texture().hex_rgb()

        # support for extra options not supported in sage
        extra_opts = p._extra_kwds
        fontsize = int(extra_opts.get('fontsize', 12))
        fontface = str(extra_opts.get('fontface', 'Arial'))
        constant_size = bool(extra_opts.get('constant_size', True))

        myobj = {"type":"text",
                 "text":text_content,
                 "pos":list(p.bounding_box()[0]),
                 "color":color,
                 'fontface':fontface,
                 'constant_size':constant_size,
                 'fontsize':fontsize}
        obj_list.append(myobj)

    def convert_line(p):
        obj_list.append({"type"       : "line",
                         "points"     : p.points,
                         "thickness"  : jsonable(p.thickness),
                         "color"      : "#" + p.get_texture().hex_rgb(),
                         "arrow_head" : bool(p.arrow_head)})

    def convert_point(p):
        obj_list.append({"type" : "point",
                         "loc"  : p.loc,
                         "size" : float(p.size),
                         "color" : "#" + p.get_texture().hex_rgb()})

    def convert_combination(p):
        for x in p.all:
            handler(x)(x)

    def convert_inner(p):
        if isinstance(p.all[0], sage.plot.plot3d.base.TransformGroup):
            convert_index_face_set(p)
        else:
            handler(p.all[0])(p)


    def handler(p):
        if isinstance(p, sage.plot.plot3d.index_face_set.IndexFaceSet):
            return convert_index_face_set
        elif isinstance(p, sage.plot.plot3d.shapes.Text):
            return convert_text3d
        elif isinstance(p, sage.plot.plot3d.base.TransformGroup):
            return convert_inner
        elif isinstance(p, sage.plot.plot3d.base.Graphics3dGroup):
            return convert_combination
        elif isinstance(p, sage.plot.plot3d.shapes2.Line):
            return convert_line
        elif isinstance(p, sage.plot.plot3d.shapes2.Point):
            return convert_point
        elif isinstance(p, sage.plot.plot3d.base.PrimitiveObject):
            return convert_index_face_set
        else:
            raise NotImplementedError("unhandled type ", type(p))


    handler(p)(p)

    return obj_list

###
# Interactive 2d Graphics
###

import os, matplotlib.figure

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

        from comm import SageCellComm as Comm
        self.comm = Comm(data={"filename": filename}, target_name='graphicswidget')
        import sys
        sys._sage_.sent_files[filename] = os.path.getmtime(filename)

        self.comm.on_msg(on_msg)



# Matplotlib's comm-based live plots.  See https://github.com/matplotlib/matplotlib/pull/2524
from matplotlib.backends.backend_webagg_core import (
    FigureManagerWebAgg, new_figure_manager_given_figure)
import json

from IPython.display import display,Javascript,HTML
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
        self.comm = Comm('matplotlib', data={'id': self.uuid})

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

