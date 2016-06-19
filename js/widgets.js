define([
    "jquery",
    "utils",
    "mpl" // Creates global namespace
], function(
    $,
    utils
   ) {
"use strict";
var undefined;

return {
    Graphics: function(session) {
        return function(comm, msg) {
            var callbacks = {iopub : {output: $.proxy(session.handle_output, session)}};
            var filename = msg.content.data.filename;
            var filepath=session.kernel.kernel_url+'/files/';
            var img =utils.createElement("img", {src: filepath+filename});
            var block_id = msg.metadata.interact_id || null;

            session.output(img, block_id);
            // Handle clicks inside the image
            $(img).click(function(e) {
                var offset = $(this).offset();
                var x = (e.pageX - offset.left) / img.clientWidth;
                var y = (e.pageY - offset.top) / img.clientHeight;
                comm.send({x:x, y:y, eventType:'click'}, callbacks);
            });
            // Handle mousemove inside the image
            $(img).mousemove(function(e) {
                var offset = $(this).offset();
                var x = (e.pageX - offset.left) / img.clientWidth;
                var y = (e.pageY - offset.top) / img.clientHeight;
                comm.send({x:x, y:y, eventType:'mousemove'}, callbacks);
            });

            // For messages from Python to javascript; we don't use this in this example
            //comm.on_msg(function(msg) {console.log(msg)});
        };
    },
    ThreeJS: function(session) {
        return function(comm, msg) {
            var that = this;
            var callbacks = {iopub : {output: $.proxy(session.handle_output, session)}};
            var div = utils.createElement("div", {style: "border: 2px solid blue;margin:0;padding:0;"});
            var block_id = msg.metadata.interact_id || null;

            $(div).salvus_threejs(msg.content.data)

            that.obj = utils.proxy(['add_3dgraphics_obj', 'render_scene', 'set_frame', 'animate']);
            run_when_defined({fn: function() {return $(div).data('salvus-threejs')},
                                cb: function(result) {that.obj._run_callbacks(result);
                                                    that.obj = result;},
                                err: function(err) {comm.close(); console.log(err);}})

            session.output(div, block_id);

            comm.on_msg(function(msg) {
                var data = msg.content.data;
                var type = data.msg_type;
                delete data.msg_type;
                if(type==='add') {
                    that.obj.add_3dgraphics_obj(data);
                } else if (type==='render') {
                    that.obj.render_scene(data);
                } else if (type==='set_frame') {
                    that.obj.set_frame(data);
                }  else if (type==='animate') {
                    that.obj.animate(data);
                } else if (type==='lights') {
                    that.obj.add_lights(data);
                }
            });
        };
    },
    MPL: function(session) {
        var callbacks = {iopub : {output: $.proxy(session.handle_output, session)}};
        var comm_websocket = function(comm) {
            var ws = {};
            // MPL assumes we have a websocket that is not open yet
            // so we run the onopen handler after they have a chance
            // to set it.
            ws.onopen = function() {};
            setTimeout(ws.onopen(), 0);
            ws.close = function() {comm.close()};
            ws.send = function(m) {
                comm.send(m, callbacks); 
                console.log('sending',m);
            };
            comm.on_msg(function(msg) {
                console.log('receiving', msg);
                ws.onmessage(msg['content']['data'])
            });
            return ws;
        }
        return function(comm, msg) {
            var id = msg.content.data.id;
            var div = utils.createElement("div", {style: "border: 2px solid blue;margin:0;padding:0;"});
            var block_id = msg.metadata.interact_id || null;
            session.output(div, block_id);
            var c = comm_websocket(comm)
            var m = new mpl.figure(id, c,
                                   function() {console.log('download')}, div);
        };
    }
};
});
