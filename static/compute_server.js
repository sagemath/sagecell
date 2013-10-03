// Options to document the functions:
// YUIDocs
// Sphinx: http://docs.cubicweb.org/annexes/docstrings-conventions.html#
// jsdoc->sphinx: http://code.google.com/p/jsdoc-toolkit-rst-template/
// recommendation to use jsdoc http://groups.google.com/group/sphinx-dev/browse_thread/thread/defa96cdc0dfc584
// sphinx javascript domain: http://sphinx.pocoo.org/domains.html#the-javascript-domain

// TODO from Crockford's book:

//  * Make objects *not* use this, but rather make them an associative
//    array that contains functions which access variables inside of a
//    closure. Then we don't have to do any $.proxy stuff; things will
//    just work. See chapter 5. However, see
//    http://bonsaiden.github.com/JavaScript-Garden/#function.constructors,
//    which argues that it is more inefficient to make objects out of
//    closures instead of using the prototype property and "new"

(function($) {
"use strict";
var undefined;
var ce = sagecell.util.createElement;
var throttle = sagecell.util.throttle;
var interacts = {};

sagecell.simpletimer = function () {
    var t = (new Date()).getTime();
   //var a = 0;
   sagecell.log('starting timer from '+t);
   return function(reset) {
       reset = reset || false;
       var old_t = t;
       var new_t = (new Date()).getTime();
       if (reset) {
           t = new_t;
       }
       //a+=1;
       //sagecell.log('time since '+t+': '+(new_t-old_t));
       return new_t-old_t;
   };
};

    sagecell.findSession = function(node) {
        if (node instanceof jQuery) {
            node = node[0]
        }
        while(!node.sagecell_session) {
            node = node.parentNode
        }
        if (node) {
            return node.sagecell_session;
        } else {
            return undefined;
        }
    }

var stop = function (event) {
    event.stopPropagation();
}
var close = null;

sagecell.Session = function (outputDiv, language, interact_vals, k, linked) {
    this.timer = sagecell.simpletimer();
    this.outputDiv = outputDiv;
    this.outputDiv[0].sagecell_session = this;
    this.language = language;
    this.interact_vals = interact_vals;
    this.linked = linked;
    this.last_requests = {};
    this.sessionContinue = true;
    this.namespaces = {};
    // Set this object because we aren't loading the full IPython JavaScript library
    IPython.notification_widget = {"set_message": sagecell.log};
    $.post = function (url, callback) {
        sagecell.sendRequest("POST", url, {}, function (data) {
            callback(JSON.parse(data));
        });
    }
    this.interacts = [];
    if (window.addEventListener) {
        // Prevent Esc key from closing WebSockets and XMLHttpRequests in Firefox
        window.addEventListener("keydown", function (event) {
            if (event.keyCode === 27) {
                event.preventDefault();
            }
        });
    }
    /* Always use sockjs, until we can get websockets working reliably.
     * Right now, if we have a very short computation (like 1+1), there is some sort of 
     * race condition where the iopub handler does not get established before 
     * the kernel is closed down.  This only manifests itself on a remote server, since presumably
     * if you are running on a local server, the connection is established too quickly.
     *
     * Also, there are some bugs in, for example, Firefox and other issues that we don't want to have
     * to work around, that sockjs already worked around.
     */
    /* 
    // When we restore the websocket, things are messed up if window.WebSocket was undefined and window.MozWebSocket was.
    var old_ws = window.WebSocket || window.MozWebSocket;
    if (!old_ws) {
        window.WebSocket = sagecell.MultiSockJS;
    }
    this.kernel = new IPython.Kernel(sagecell.URLs.kernel);
    window.WebSocket = old_ws;
    */
    var that = this;
    if (linked && sagecell.kernels[k]) {
        this.kernel = sagecell.kernels[k];
    } else {
        var old_ws = window.WebSocket;
        // sometimes (IE8) window.console is not defined (until the console is opened)
        var old_console = window.console;
        var old_log = window.console && console.log;
        window.WebSocket = sagecell.MultiSockJS;
        window.console = window.console || {};
        console.log = sagecell.log;
        this.kernel = sagecell.kernels[k] = new IPython.Kernel(sagecell.URLs.kernel);
        this.kernel.session = this;
        this.kernel.opened = false;
        this.kernel.deferred_code = [];
        window.WebSocket = old_ws;
        this.kernel.start_channels = function() {
            // wrap the IPython start_channels function, since it
            // assumes that this.kernel_url is a relative url when it
            // constructs the websocket URL
            var absolute_kernel = this.kernel_url;
            this.kernel_url = absolute_kernel.substr(sagecell.URLs.root.length);
            $.proxy(IPython.Kernel.prototype.start_channels, this)();
            this.kernel_url = absolute_kernel;
        }

    /**
     * Handle a websocket entering the open state
     * sends session and cookie authentication info as first message.
     * Once all sockets are open, signal the Kernel.status_started event.
     * @method _ws_opened
     */
    this.kernel._ws_opened = function (evt) {
        // send the session id so the Session object Python-side
        // has the same identity
        //evt.target.send(this.session_id + ':' + document.cookie);
        var channels = [this.shell_channel, this.iopub_channel, this.stdin_channel];
        for (var i=0; i < channels.length; i++) {
            // if any channel is not ready, don't trigger event.
            if ( !channels[i].readyState ) return;
        }
        // all events ready, trigger started event.
        $([IPython.events]).trigger('status_started.Kernel', {kernel: this});
    };



        this.kernel._kernel_started = function (json) {
            sagecell.log('kernel start callback: '+that.timer()+' ms.');
            this._kernel_started = IPython.Kernel.prototype._kernel_started;
            this._kernel_started(json);
            sagecell.log('kernel ipython startup: '+that.timer()+' ms.');
            this.shell_channel.onopen = function () {
                console.log = old_log;
                console = old_console;
                sagecell.log('kernel channel opened: '+that.timer()+' ms.');
                that.kernel.opened = true;
                while (that.kernel.deferred_code.length > 0) {
                    that.execute(that.kernel.deferred_code.shift());
                }
            }
            this.iopub_channel.onopen = undefined;
        }
        this.kernel.start = function(notebook_id, timeout) {
            // Override the IPython start kernel function since we want to send extra data, like a default timeout
            var that = this;
            if (!this.running) {
                timeout = timeout || 0;
                var qs = $.param({notebook:notebook_id, timeout: timeout});
                console.log(qs);
                var url = this.base_url + '?' + qs;
                $.post(url,
                       $.proxy(that._kernel_started,that),
                       'json'
                      );
            }

        }

        this.kernel.start(IPython.utils.uuid(), linked ? 'inf' : 0);
    }
    var pl_button, pl_box, pl_zlink, pl_qlink, pl_qrcode, pl_chkbox;
    this.outputDiv.find(".sagecell_output").prepend(
        this.session_container = ce("div", {"class": "sagecell_sessionContainer"}, [
            ce("div", {"class": "sagecell_permalink"}, [
                pl_button = ce("button", {}, ["Share"]),
                pl_box = ce("div", {"class": "sagecell_permalink_result"}, [
                    ce("div", {}, [pl_zlink = ce("a", {
                        "title": "Link that will work on any Sage Cell server"
                    }, ["Permalink"])]),
                    ce("div", {}, [pl_qlink = ce("a", {
                        "title": "Shortened link that will only work on this server"
                    }, ["Short temporary link"])]),
                    ce("div", {}, [ce("a", {}, [
                        pl_qrcode = ce("img", {
                            "title": "QR code that will only work on this server",
                            "alt": ""
                        })
                    ])]),
                    this.interact_pl = ce("label", {}, [
                        "Share interact state",
                        pl_chkbox = ce("input", {"type": "checkbox"})
                    ])
                ])
            ]),
            this.output_block = ce("div", {"class": "sagecell_sessionOutput sagecell_active"}, [
                this.spinner = ce("img", {
                    "src": sagecell.URLs.spinner,
                    "alt": "Loading",
                    "class": "sagecell_spinner"
                })
            ]),
            ce("div", {"class": "sagecell_poweredBy"}, [
                "Powered by ",
                ce("a", {"href": "http://www.sagemath.org"}, [
                    ce("img", {"src": sagecell.URLs.sage_logo, "alt": "Sage"})
                ])
            ]),
            this.session_files = ce("div", {"class": "sagecell_sessionFiles"})
        ])
    );
    pl_box.style.display = this.interact_pl.style.display = "none";
    var pl_hidden = true;
    var hide_box = function hide_box() {
        pl_box.style.display = "none";
        window.removeEventListener("mousedown", hide_box);
        pl_hidden = true;
        close = null;
    };
    var n = 0;
    var code_links = {}, interact_links = {};
    var that = this;
    var qr_prefix = "https://chart.googleapis.com/chart?cht=qr&chs=200x200&chl="
    this.updateLinks = function (new_vals) {
        if (new_vals) {
            interact_links = {};
        }
        if (pl_hidden) {
            return;
        }
        var links = (pl_chkbox.checked ? interact_links : code_links);
        if (links.zip === undefined) {
            pl_zlink.removeAttribute("href");
            pl_qlink.removeAttribute("href");
            pl_qrcode.parentNode.removeAttribute("href");
            pl_qrcode.removeAttribute("src");
            sagecell.log('sending permalink request post: '+that.timer()+' ms');
            var args = {
                "code": that.code,
                "language": that.language,
                "n": ++n
            };
            if (pl_chkbox.checked) {
                var list = [];
                for (var i = 0; i < that.interacts.length; i++) {
                    if (that.interacts[i].parent_block === null) {
                        var interact = that.interacts[i];
                        var dict = {
                            "state": interact.state(),
                            "bookmarks": []
                        }
                        for (var j = 0; j < interact.bookmarks.childNodes.length; j++) {
                            var b = interact.bookmarks.childNodes[j];
                            if (b.firstChild.firstChild.hasChildNodes()) {
                                dict.bookmarks.push({
                                    "name": b.firstChild.firstChild.firstChild.nodeValue,
                                    "state": $(b).data("values")
                                });
                            }
                        }
                        list.push(dict);
                    }
                }
                args.interacts = JSON.stringify(list);
            }
            sagecell.sendRequest("POST", sagecell.URLs.permalink, args, function (data) {
                data = JSON.parse(data);
                sagecell.log('POST permalink request walltime: '+that.timer() + " ms");
                if (data.n !== n) {
                    return;
                }
                pl_qlink.href = links.query = sagecell.URLs.root + "?q=" + data.query;
                links.zip = sagecell.URLs.root + "?z=" + data.zip + "&lang=" + that.language;
                if (data.interacts) {
                    links.zip += "&interacts=" + data.interacts;
                }
                pl_zlink.href = links.zip;
                pl_qrcode.parentNode.href = links.query;
                pl_qrcode.src = qr_prefix + links.query;
            });
        } else {
            pl_qlink.href = pl_qrcode.parentNode.href = links.query;
            pl_zlink.href = links.zip;
            pl_qrcode.src = qr_prefix + links.query;
        }
    };
    pl_button.addEventListener("click", function () {
        if (pl_hidden) {
            pl_hidden = false;
            that.updateLinks(false);
            pl_box.style.display = "block";
            if (close) {
                close();
            }
            close = hide_box;
            window.addEventListener("mousedown", hide_box);
        } else {
            hide_box();
        }
    });
    pl_button.addEventListener("mousedown", stop);
    pl_box.addEventListener("mousedown", stop);
    $([IPython.events]).on("status_busy.Kernel", function (evt, data) {
        if (data.kernel.kernel_id === that.kernel.kernel_id) {
            that.spinner.style.display = "";
        }
    });
    pl_chkbox.addEventListener("change", function () {
        that.updateLinks(false);
    });
    $([IPython.events]).on("status_idle.Kernel", function (evt, data) {
        if (data.kernel.kernel_id !== that.kernel.kernel_id) {
            return;
        }
        that.spinner.style.display = "none";
        for (var i = 0, j = 0; i < that.interact_vals.length; i++) {
            while (that.interacts[j] && that.interacts[j].parent_block !== null) {
                j++;
            }
            if (j === that.interacts.length) {
                break;
            }
            that.interacts[j].state(that.interact_vals[i].state, (function (interact, val) {
                return function () {
                    interact.clearBookmarks();
                    for (var i = 0; i < val.bookmarks.length; i++) {
                        interact.createBookmark(val.bookmarks[i].name, val.bookmarks[i].state);
                    }
                };
            })(that.interacts[j], that.interact_vals[i]));
            j++;
        }
        that.interact_vals = [];
    });
    $([IPython.events]).on("status_dead.Kernel", function (evt, data) {
        if (data.kernel.kernel_id === that.kernel.kernel_id) {
            for (var i = 0; i < that.interacts.length; i++) {
                that.interacts[i].disable();
            }
            $(that.output_block).removeClass("sagecell_active");
            data.kernel.shell_channel = {};
            data.kernel.iopub_channel = {};
            sagecell.kernels[k] = null;
        }
    });
    this.lock_output = false;
    this.files = {};
    this.eventHandlers = {};
};

// metadata is optional
sagecell.Session.prototype.send_message = function(msg_type, content, callbacks, metadata) {
    var msg = this.kernel._get_msg(msg_type, content);
    msg['metadata'] = metadata || {};
    this.kernel.shell_channel.send(JSON.stringify(msg));
    this.kernel.set_callbacks_for_msg(msg.header.msg_id, callbacks);
}

sagecell.Session.prototype.execute = function (code) {
    if (this.kernel.opened) {
        sagecell.log('opened and executing in kernel: '+this.timer()+' ms');
        var pre;
        if (this.language === "python") {
            pre = "exec ";
        } else if (this.language === "html") {
            pre = "html";
        } else if (this.language !== "sage") {
            pre = "print " + this.language + ".eval";
        }
        if (pre) {
            code = pre + '("""' + code.replace(/"/g, '\\"') + '""")'
        }
        if (this.language === "html") {
            code += "\nNone";
        }
        this.code = code;
        var callbacks = {iopub: {"output": $.proxy(this.handle_output, this)},
                         shell: {"reply": $.proxy(this.handle_execute_reply, this)}};
        this.set_last_request(null, this.kernel.execute(code, callbacks, {
            "silent": false,
            "user_expressions": {"_sagecell_files": "sys._sage_.new_files()"},
        }));
    } else {
        this.kernel.deferred_code.push(code);
    }
};

sagecell.Session.prototype.set_last_request = function (interact_id, msg_id) {
    this.kernel.set_callbacks_for_msg(this.last_requests[interact_id]);
    this.last_requests[interact_id] = msg_id;
};

sagecell.Session.prototype.appendMsg = function(msg, text) {
    // Append the message to the div of messages
    // Use $.text() so that strings are automatically escaped
    $(ce('div')).text(text+JSON.stringify(msg)).prependTo(this.outputDiv.find(".sagecell_messages"));
};

sagecell.Session.prototype.last_output = function(block_id) {
    var block = $(block_id === null ? this.output_block : interacts[block_id].output_block);
    var last = block.children().last();
    return (last.length === 0 ? undefined : last);
}

sagecell.Session.prototype.clear = function (block_id, changed) {
    var output_block = $(block_id === null ? this.output_block : interacts[block_id].output_block);
    if (output_block.length===0) {return;}
    output_block[0].style.minHeight = output_block.height() + "px";
    setTimeout(function () {
        output_block.animate({"min-height": "0px"}, "slow");
    }, 3000);
    output_block.empty();
    if (changed) {
        for (var i = 0; i < changed.length; i++) {
            $(interacts[block_id].cells[changed[i]]).removeClass("sagecell_dirtyControl");
        }
    }
    for (var i = 0; i < this.interacts.length; i++) {
        if (this.interacts[i].parent_block === block_id) {
            this.clear(this.interacts[i].interact_id);
            delete interacts[this.interacts[i].interact_id];
            this.interacts.splice(i--, 1);
        }
    }
};

sagecell.Session.prototype.output = function(html, block_id) {
    // Return a DOM element for new content.  The html is appended to the html block, and then the last child of the output region is returned.
    var output_block=$(block_id === null ? this.output_block : interacts[block_id].output_block);
    if (output_block.length===0) {return;}
    return output_block.append(html).children().last();
};

sagecell.Session.prototype.handle_message_reply = function(msg) {
}


sagecell.Session.prototype.handle_execute_reply = function(msg) {
    sagecell.log('reply walltime: '+this.timer() + " ms");
    /* This would give two error messages (since a pyerr should have already come)
      if(msg.status==="error") {
        this.output('<pre class="sagecell_pyerr"></pre>',null)
            .html(IPython.utils.fixConsole(msg.traceback.join("\n")));
    } 
    */
    // TODO: handle payloads with a payload callback, instead of in the execute_reply
    // That would be much less brittle
    var payload = msg.content.payload[0];
    if (payload && payload.new_files && payload.new_files.length>0){
        var files = payload.new_files;
        var output_block = this.outputDiv.find("div.sagecell_sessionFiles");
        var html="<div>\n";
        for(var j = 0, j_max = files.length; j < j_max; j++) {
            if (this.files[files[j]] !== undefined) {
                this.files[files[j]]++;
            } else {
                this.files[files[j]] = 0;
            }
        }
        var filepath=this.kernel.kernel_url+'/files/';
        for (j in this.files) {
            //TODO: escape filenames and id
            html+='<a href="'+filepath+j+'?q='+this.files[j]+'" target="_blank">'+j+'</a> [Updated '+this.files[j]+' time(s)]<br>\n';
        }
        html+="</div>";
        output_block.html(html).effect("pulsate", {times:1}, 500);
    }
}
    
sagecell.Session.prototype.handle_output = function (msg, default_block_id) {
    var msg_type = msg.header.msg_type;
    var content = msg.content;
    var metadata = msg.metadata;
    var block_id = metadata.interact_id || default_block_id || null;
    if (block_id !== null && !interacts.hasOwnProperty(block_id)) {
        return;
    }
    // Handle each stream type.  This should probably be separated out into different functions.
    switch (msg_type) {
    case "stream":
        // First, see if we should consolidate this output with the previous output <pre>
        // this reaches into the inner workings of output
        var last_output = this.last_output(block_id);
        if (last_output && last_output.hasClass("sagecell_" + content.name)) {
            // passing in an empty html string will actually return the last child of the output region
            var html = "";
        } else {
            var html = "<pre class='sagecell_" + content.name + "'></pre>";
        }
        var out = this.output(html, block_id);
        if (out) {out.text(out.text() + content.data);}
        break;

    case "pyout":
        this.output('<pre class="sagecell_pyout"></pre>', block_id)
            .text(content.data["text/plain"]);
        break;

    case "pyerr":
        if (content.traceback.join) {
            this.output('<pre class="sagecell_pyerr"></pre>', block_id)
                .html(IPython.utils.fixConsole(content.traceback.join("\n")));
        }
        break;

    case "display_data":
        var filepath=this.kernel.kernel_url+'/files/';
        // find any key of content that is in the display_handlers array and execute that handler
        // if none found, do the text/plain 
        var already_handled = false;
        for (var key in content.data) {
            if (content.data.hasOwnProperty(key) && this.display_handlers[key]) {
                // return false if the mime type wasn't handled after all
                already_handled = false !== $.proxy(this.display_handlers[key], this)(content.data[key], block_id, filepath);
                // we only use one mime type
                break;
            }
        }
        if (!already_handled && content.data['text/plain']) {
            // we are *always* supposed to have a text/plain attribute
            this.output("<pre></pre>", block_id).text(content.data['text/plain']);
        }
        break;
    }
    sagecell.log('handled output: '+this.timer()+' ms');
    this.appendMsg(content, "Accepted: ");
    // need to mathjax the entire output, since output_block could just be part of the output
    var output = this.outputDiv.find(".sagecell_output").get(0);
    MathJax.Hub.Queue(["Typeset",MathJax.Hub, output]);
    MathJax.Hub.Queue([function () {$(output).find(".math").removeClass('math');}]);
};

// dispatch table on mime type
sagecell.Session.prototype.display_handlers = {
    'application/sage-interact': function (data, block_id) {
        this.interacts.push(interacts[data.new_interact_id] = new sagecell.InteractCell(this, data, block_id));
    },
    'application/sage-interact-update': function (data) {
        interacts[data.interact_id].updateControl(data);
    },
    'application/sage-interact-new-control': function (data) {
        interacts[data.interact_id].newControl(data);
    },
    'application/sage-interact-del-control': function (data) {
        interacts[data.interact_id].delControl(data);
    },
    'application/sage-interact-bookmark': function (data) {
        interacts[data.interact_id].createBookmark(data.name, data.values);
    },
    'application/sage-clear': function (data, block_id) {
        this.clear(block_id, data.changed);
    }
    ,'text/html': function(data, block_id, filepath) {this.output("<div></div>", block_id).html(data.replace(/cell:\/\//gi, filepath)); }
    ,'text/image-filename': function(data, block_id, filepath) {this.output("<img src='"+filepath+data+"'/>", block_id);}
    ,'image/png': function(data, block_id, filepath) {this.output("<img src='data:image/png;base64,"+data+"'/>", block_id);}
    ,'application/x-jmol': function(data, block_id, filepath) {
        jmolSetDocument(false);
        this.output(jmolApplet(500, 'set defaultdirectory "'+filepath+data+'";\n script SCRIPT;\n'),block_id); }
    ,"application/x-canvas3d": function (data, block_id, filepath) {
        var div = this.output(document.createElement("div"), block_id);
        var old_cw = [window.hasOwnProperty("cell_writer"), window.cell_writer],
            old_tr = [window.hasOwnProperty("translations"), window.translations];
        window.cell_writer = {"write": function (html) {
            div.html(html);
        }};
        var text = "Sorry, but you need a browser that supports the &lt;canvas&gt; tag.";
        window.translations = {};
        window.translations[text] = text;
        canvas3d.viewer(filepath + data);
        if (old_cw[0]) {
            window.cell_writer = old_cw[1];
        } else {
            delete window.cell_writer;
        }
        if (old_tr[0]) {
            window.translations = old_tr[1];
        } else {
            delete window.translations;
        }
    }
    ,'application/sage-interact-control': function(data, block_id, filepath) {
        var that=this;
        var control_class = sagecell.interact_controls[data.control_type];
        if ( control_class === undefined) {return false;}
        var control = new control_class(this, data.control_id);
        control.create(data, block_id);
        $.each(data.variable, function(index, value) {that.register_control(data.namespace, value, control);});
        control.update(data.namespace, data.variable);
    }
    ,'application/sage-interact-variable': function(data, block_id, filepath) {this.update_variable(data.namespace, data.variable, data.control);}
}

sagecell.Session.prototype.register_control = function(namespace, variable, control) {
    if (this.namespaces[namespace] === undefined) {
        this.namespaces[namespace] = {};
    }
    if (this.namespaces[namespace][variable] === undefined) {
        this.namespaces[namespace][variable] = []
    }
    this.namespaces[namespace][variable].push(control);
}

sagecell.Session.prototype.get_variable_controls = function(namespace, variable) {
    var notify = {};
    if (this.namespaces[namespace] && this.namespaces[namespace][variable]) {
        $.each(this.namespaces[namespace][variable], function(index, control) {
            notify[control.control_id] = control;
        });
    }
    return notify;
}

sagecell.Session.prototype.update_variable = function(namespace, variable, control_id) {
    var that = this;
    var notify;
    if ($.isArray(variable)) {
        notify = {};
        $.each(variable, function(index, v) {$.extend(notify, that.get_variable_controls(namespace, v))});
    } else {
        notify = this.get_variable_controls(namespace, variable);
    }
    $.each(notify, function(k,v) {$.proxy(v.update, v)(namespace, variable, control_id);});
};

sagecell.Session.prototype.destroy = function () {
    this.clear(null);
    $(this.session_container).remove();
}

sagecell.InteractControls = {'throttle': 100};

sagecell.InteractControls.InteractControl = function () {
    return function (session, control_id) {
        this.session = session;
        this.control_id = control_id;
    }
}

/* 
// To implement a new control, do something like the following.  
// See below for examples.  The Checkbox control is particularly simple.

sagecell.InteractControls.MyControl = sagecell.InteractControls.InteractControl();
sagecell.InteractControls.MyControl.prototype.create = function (data, block_id) {
    // The create message is in `data`, while the block id to use for `this.session.output` is in block_id.  
    // This method creates the control and registers any change handlers.
    // Change handlers should send a `variable_update` message back to the server.  This message is handled 
    // by the control's python variable_update method.
}

sagecell.InteractControls.Checkbox.prototype.update = function (namespace, variable, control_id) {
    // If a variable in the namespace is updated (i.e., the client receives a variable update message),
    // this method is called.  The namespace is the UUID of the namespace, the variable is the variable name as a string, 
    // and the control_id is the UUID of the control.  This method should send a message and register a handler for the reply
    // from the control's python update_control method. The reply handler should then update the control appropriately.
}
*/

sagecell.InteractControls.Slider = sagecell.InteractControls.InteractControl();
sagecell.InteractControls.Slider.prototype.create = function (data, block_id) {
    var that = this;
    this.control = this.session.output(ce("div", {id: data.control_id}), block_id);
    this.control.slider({
        disabled: !data.enabled,
        min: data.min,
        max: data.max,
        step: data.step,
        slide: throttle(function(event, ui) {
            if (! event.originalEvent) {return;}
            that.session.send_message('variable_update', {control_id: data.control_id, value: ui.value}, 
                                      {iopub: {"output": $.proxy(that.session.handle_output, that.session)}});
        }, sagecell.InteractControls.throttle)
    });
}

sagecell.InteractControls.Slider.prototype.update = function (namespace, variable, control_id) {
    var that = this;
    if (this.control_id !== control_id) {
        this.session.send_message('control_update', {control_id: this.control_id, namespace: namespace, variable: variable},
                                  {iopub: {"output": $.proxy(this.session.handle_output, this.session)}, 
                                   shell: {"control_update_reply": function(content, metadata) {
                                       if (content.status === 'ok') {
                                           that.control.slider('value', content.result.value);
                                       }
                                   }}});
    }
}


sagecell.InteractControls.ExpressionBox = sagecell.InteractControls.InteractControl();
sagecell.InteractControls.ExpressionBox.prototype.create = function (data, block_id) {
    var that = this;
    this.control = this.session.output(ce("input", {id: data.control_id, type: 'textbox'}), block_id);
    this.control.change(function(event) {
        if (! event.originalEvent) {return;}
        that.session.send_message('variable_update', {control_id: data.control_id, value: $(this).val()}, 
                                  {iopub: {"output": $.proxy(that.session.handle_output, that.session)}});
    });
}

sagecell.InteractControls.ExpressionBox.prototype.update = function (namespace, variable, control_id) {
    var that = this;
    this.session.send_message('control_update', {control_id: this.control_id, namespace: namespace, variable: variable},
                              {iopub: {"output": $.proxy(this.session.handle_output, this.session)}, 
                               shell: {"control_update_reply": function(content, metadata) {
                                   if (content.status === 'ok') {
                                       that.control.val(content.result.value);
                                   }
                               }}});
}

sagecell.InteractControls.Checkbox = sagecell.InteractControls.InteractControl();
sagecell.InteractControls.Checkbox.prototype.create = function (data, block_id) {
    var that = this;
    this.control = this.session.output(ce("input", {id: data.control_id, type: 'checkbox'}), block_id);
    this.control.change(function(event) {
        if (! event.originalEvent) {return;}
        that.session.send_message('variable_update', {control_id: data.control_id, value: $(this).prop("checked")}, 
                                  {iopub: {"output": $.proxy(that.session.handle_output, that.session)}});
    });
}

sagecell.InteractControls.Checkbox.prototype.update = function (namespace, variable, control_id) {
    var that = this;
    this.session.send_message('control_update', {control_id: this.control_id, namespace: namespace, variable: variable},
                              {iopub: {"output": $.proxy(this.session.handle_output, this.session)}, 
                               shell: {"control_update_reply": function(content, metadata) {
                                   if (content.status === 'ok') {
                                       that.control.prop('checked', content.result.value);
                                   }
                               }}});
}


sagecell.InteractControls.OutputRegion = sagecell.InteractControls.InteractControl();
sagecell.InteractControls.OutputRegion.prototype.create = function (data, block_id) {
    var that = this;
    this.control = this.session.output(ce("div", {id: data.control_id}), block_id);
    this.session.output_blocks[this.control_id] = this.control;
    this.message_number = 1;
}

sagecell.InteractControls.OutputRegion.prototype.update = function (namespace, variable, control_id) {
    var that = this;
    this.message_number += 1;
    var msg_number = this.message_number;
    this.session.send_message('control_update', {control_id: this.control_id, namespace: namespace, variable: variable},
                              {iopub: {"output": function(msg) {
                                  if (msg_number === that.message_number) {
                                      $.proxy(that.session.handle_output, that.session)(msg, that.control_id);
                                  }
                              }}});
}

sagecell.interact_controls = {
    'Slider': sagecell.InteractControls.Slider,
    'ExpressionBox': sagecell.InteractControls.ExpressionBox,
    'Checkbox': sagecell.InteractControls.Checkbox,
    'OutputRegion': sagecell.InteractControls.OutputRegion

}

/**********************************************
    OLD Interacts
**********************************************/



sagecell.InteractCell = function (session, data, parent_block) {
    this.interact_id = data.new_interact_id;
    this.function_code = data.function_code;
    this.controls = {};
    this.session = session;
    this.parent_block = parent_block;
    this.layout = data.layout;
    this.locations = data.locations;
    this.msg_id = data.msg_id;
    this.changed = [];

    var controls = data.controls;
    for (var name in controls) {
        if (controls.hasOwnProperty(name)) {
            this.controls[name] = new sagecell.InteractData.control_types[controls[name].control_type](controls[name]);
        }
    }
    this.session.interact_pl.style.display = "block";
    this.renderCanvas(parent_block);
    this.bindChange();
    if (data.readonly) {this.disable();}
}

sagecell.InteractCell.prototype.newControl = function (data) {
    this.controls[data.name] = new sagecell.InteractData.control_types[data.control.control_type](data.control);
    this.placeControl(data.name);
    this.bindChange(data.name);
    if (this.output_block && this.controls[data.name].dirty_update) {
        $(this.cells[data.name]).addClass("sagecell_dirtyControl");
    }
    if (this.parent_block === null) {
        this.session.updateLinks(true);
    }
}

sagecell.InteractCell.prototype.delControl = function (data) {
    delete this.controls[data.name];
    var tr = this.cells[data.name].parentNode;
    tr.parentNode.removeChild(tr);
    delete this.cells[data.name];
    if (this.parent_block === null) {
        this.session.updateLinks(true);
    }
}

sagecell.InteractCell.prototype.bindChange = function (cname) {
    var that = this;
    var handler = function (event, ui) {
        if (that.controls[event.data.name].ignoreNext > 0) {
            that.controls[event.data.name].ignoreNext--;
            return;
        }
        if (that.changed.indexOf(event.data.name) === -1) {
            that.changed.push(event.data.name);
        }
        var msg_dict = {
            "interact_id": that.interact_id,
            "values": {},
            "update_last": false,
            "user_expressions": {"_sagecell_files": "sys._sage_.new_files()"}
        };
        msg_dict.values[event.data.name] = that.controls[event.data.name].json_value(ui);
        if (that.controls[event.data.name].dirty_update) {
            $(that.cells[event.data.name]).addClass("sagecell_dirtyControl");
        }
        var callbacks = {
            iopub: {"output": $.proxy(that.session.handle_output, that.session)},
            shell: {"reply": $.proxy(that.session.handle_execute_reply, that.session)}
        };
        that.session.send_message('sagenb.interact.update_interact', msg_dict, callbacks);
        if (this.parent_block === null) {
            that.session.updateLinks(true);
        }
    };
    if (cname === undefined) {
        for (var name in this.controls) {
            if (this.controls.hasOwnProperty(name)) {
                var events = this.controls[name].changeHandlers();
                for (var e in events) {
                    if (events.hasOwnProperty(e)) {
                        $(events[e]).on(e, {"name": name}, handler);
                    }
                }
            }
        }
    } else {
        var events = this.controls[cname].changeHandlers();
        for (var e in events) {
            if (events.hasOwnProperty(e)) {
                $(events[e]).on(e, {"name": cname}, handler);
            }
        }
    }
};

sagecell.InteractCell.prototype.placeControl = function (name) {
    var control = this.controls[name];
    var id = this.interact_id + "_" + name;
    var div = this.cells[name];
    if (div === undefined) {
        var rdiv = ce("div");
        div = this.cells[name] = ce("div", {"class": "sagecell_interactControlCell"});
        div.style.width = "90%";
        rdiv.appendChild(div);
        if (this.output_block) {
            var outRow = this.output_block.parentNode.parentNode 
            outRow.parentNode.insertBefore(rdiv, outRow);
        } else {
            $(this.container).append(rdiv);
        }
    }
    if (control.control.label.length > 0) {
        div.appendChild(ce("label", {
            "class": "sagecell_interactControlLabel",
            "for": id,
            "title": name
        }, [control.control.label]));
    }
    div.appendChild(ce("div", {"class": "sagecell_interactControl"}, [
        control.rendered(id)
    ]))
}

var textboxItem = function (defaultVal, callback) {
    var input = ce("input", {
        "value": defaultVal,
        "placeholder": "Bookmark name"
    });
    input.addEventListener("keydown", stop);
    input.addEventListener("keypress", function (event) {
        if (event.keyCode === 13) {
            callback();
            event.preventDefault();
        }
        event.stopPropagation();
    });
    var div = ce("div", {
        "title": "Add bookmark",
        "tabindex": "0",
        "role": "button"
    });
    div.addEventListener("click", callback);
    return ce("li", {"class": "ui-state-disabled"}, [ce("a", {}, [input, div])]);
};

var selectAll = function (txt) {
    txt.selectionStart = 0;
    txt.selectionEnd = txt.value.length;
    txt.selectionDirection = "forward";
};

sagecell.InteractCell.prototype.renderCanvas = function (parent_block) {
    this.cells = {}
    this.container = ce("div", {"class": "sagecell_interactContainer"});
    if (this.layout && this.layout.length>0) {
        for (var row = 0; row < this.layout.length; row++) {
            var rdiv = ce("div");
            var total = 0;
            for (var col = 0; col < this.layout[row].length; col++) {
                total += this.layout[row][col][1];
            }
            for (var col =  0; col < this.layout[row].length; col++) {
                var cdiv = ce("div", {"class": "sagecell_interactControlCell"});
                cdiv.style.width = 100 * this.layout[row][col][1] / total + "%";
                if (this.layout[row][col] !== undefined) {
                    this.cells[this.layout[row][col][0]] = cdiv;
                    if (this.layout[row][col][0] === "_output") {
                        this.output_block = ce("div", {"class": "sagecell_interactOutput"});
                        cdiv.appendChild(this.output_block);
                    }
                }
                rdiv.appendChild(cdiv);
            }
            this.container.appendChild(rdiv);
        }
    }
    if (this.locations) {
        for (var name in this.locations) {
            if (this.locations.hasOwnProperty(name)) {
                this.cells[name] = $("body").find(this.locations[name]).slice(0,1).empty()[0];
                if (name==="_output") {
                    this.output_block = this.cells[name];
                    $(this.output_block).addClass("sagecell_interactOutput");
                } else if (name==="_bookmarks") {
                    this.bookmark_container = this.cells[name];
                }
            }
        }
    }
    for (var name in this.controls) {
        if (this.controls.hasOwnProperty(name)) {
            this.placeControl(name);
        }
    }
    var menuBar = ce("div", {"class": "sagecell_bookmarks"});
    var expText = ce("input", {
        "title": "Pass this string to the interact proxy\u2019s _set_bookmarks method.",
        "readonly": ""
    });
    var expButton = ce("div", {
        "title": "Export bookmarks",
        "tabindex": "0",
        "role": "button"
    });
    expText.style.display = "none";
    expText.addEventListener("focus", function (event) {
        selectAll(expText);
    });
    var starButton = ce("div", {
        "title": "Bookmarks",
        "tabindex": "0",
        "role": "button"
    });
    this.set_export = function () {
        var b = [];
        for (var i = 0; i < this.bookmarks.childNodes.length; i++) {
            var li = this.bookmarks.childNodes[i];
            var node = li.firstChild.firstChild.firstChild;
            if (node !== null) {
                b.push([node.nodeValue, $(li).data("values")]);
            }
        }
        expText.value = JSON.stringify(JSON.stringify(b));
    };
    var list = ce("ul", {"class": "sagecell_bookmarks_list"});
    var that = this;
    menuBar.addEventListener("mousedown", stop);
    expButton.addEventListener("click", function () {
        expText.style.display = "";
        expText.focus();
        selectAll(expText);
        $(expButton).removeClass("sagecell_export");
    });
    menuBar.appendChild(expButton);
    menuBar.appendChild(expText);
    menuBar.appendChild(starButton);
    this.bookmark_container = this.bookmark_container || this.container;
    this.bookmark_container.appendChild(menuBar)
    this.bookmarks = list;
    list.addEventListener("mousedown", stop, true);
    this.set_export();
    var visible = false;
    var tb;
    var hide_box = function hide_box() {
        list.parentNode.removeChild(list);
        list.removeChild(tb);
        $(expButton).removeClass("sagecell_export");
        expText.style.display = "none";
        window.removeEventListener("mousedown", hide_box);
        visible = false;
        close = null;
    };
    $(list).menu({
        "select": function (event, ui) {
            that.state(ui.item.data("values"));
            hide_box();
        }
    });
    var handler = function (event) {
        if (visible) {
            return;
        }
        (function addTextbox() {
            var n = 1;
            while (true) {
                for (var i = 0; i < list.childNodes.length; i++) {
                    if (list.childNodes[i].firstChild.firstChild.firstChild.nodeValue === "Bookmark " + n) {
                        break;
                    }
                }
                if (i === list.childNodes.length) {
                    break;
                }
                n++;
            }
            tb = textboxItem("Bookmark " + n, function () {
                list.removeChild(tb);
                that.createBookmark(tb.firstChild.firstChild.value);
                addTextbox();
            });
            list.appendChild(tb);
            $(list).menu("refresh");
            setTimeout(function () {
                var input = list.lastChild.firstChild.firstChild;
                input.selectionStart = 0;
                input.selectionEnd = input.value.length;
                input.selectionDirection = "forward";
                input.focus();
            }, 0);
        })();
        visible = true;
        that.session.outputDiv.append(list);
        if (close) {
            close();
        }
        close = hide_box;
        $(list).position({
            "my": "right top",
            "at": "right bottom+5px",
            "of": starButton
        });
        $(expButton).addClass("sagecell_export");
        expButton.style.display = "inline-block";
        window.addEventListener("mousedown", hide_box);
        event.stopPropagation();
    };
    starButton.addEventListener("mousedown", handler);
    this.disable_bookmarks = function () {
        starButton.removeEventListener("mousedown", handler);
        starButton.setAttribute("aria-disabled", "true");
        starButton.removeAttribute("tabindex");
    }
    if (this.layout && this.layout.length > 0) {
        this.session.output(this.container, parent_block);
    }
}

sagecell.InteractCell.prototype.updateControl = function (data) {
    if (this.controls[data.control].update) {
        this.controls[data.control].ignoreNext = this.controls[data.control].eventCount;
        this.controls[data.control].update(data.value, data.index);
        if (this.output_block && this.controls[data.control].dirty_update) {
            $(this.cells[data.control]).addClass("sagecell_dirtyControl");
        }
        if (this.parent_block === null) {
            this.session.updateLinks(true);
        }
    }
}

sagecell.InteractCell.prototype.state = function (vals, callback) {
    if (vals === undefined) {
        vals = {};
        for (var n in this.controls) {
            if (this.controls.hasOwnProperty(n) && this.controls[n].update) {
                vals[n] = this.controls[n].json_value();
            }
        }
        return vals;
    } else {
        for (var n in vals) {
            if (vals.hasOwnProperty(n) && this.controls.hasOwnProperty(n)) {
                this.controls[n].ignoreNext = this.controls[n].eventCount;
                this.controls[n].update(vals[n]);
            }
        }
        var msg_dict = {
            "interact_id": this.interact_id,
            "values": vals,
            "update_last": true
        };
        var callbacks = {
            iopub: {"output": $.proxy(this.session.handle_output, this.session)},
            shell: {"sagenb.interact.update_interact_reply": callback || $.proxy(this.session.handle_message_reply, this.session)}
        };
        this.session.send_message('sagenb.interact.update_interact', msg_dict, callbacks);
    }
}

sagecell.InteractCell.prototype.createBookmark = function (name, vals) {
    if (vals === undefined) {
        vals = this.state();
    }
    var del = ce("div", {
        "title": "Delete bookmark",
        "tabindex": "0",
        "role": "button"
    });
    var entry = ce("li", {}, [ce("a", {}, [ce("div", {}, [name]), del])]);
    var that = this;
    var i = this.bookmarks.childNodes.length;
    del.addEventListener("click", function (event) {
        that.bookmarks.removeChild(entry);
        if (that.parent_block === null) {
            that.session.updateLinks(true);
        }
        that.set_export();
        event.stopPropagation();
    });
    $(entry).data({"values": vals});
    var tbEntry;
    if (this.bookmarks.hasChildNodes() &&
        !this.bookmarks.lastChild.firstChild.firstChild.hasChildNodes()) {
        tbEntry = this.bookmarks.removeChild(this.bookmarks.lastChild);
    }
    this.bookmarks.appendChild(entry);
    if (tbEntry) {
        this.bookmarks.appendChild(tbEntry);
    }
    $(this.bookmarks).menu("refresh");
    if (this.parent_block === null) {
        this.session.updateLinks(true);
    }
    this.set_export();
};

sagecell.InteractCell.prototype.clearBookmarks = function () {
    var tbEntry;
    if (this.bookmarks.hasChildNodes() &&
        !this.bookmarks.lastChild.firstChild.firstChild.hasChildNodes()) {
        tbEntry = this.bookmarks.removeChild(this.bookmarks.lastChild);
    }
    while (this.bookmarks.hasChildNodes()) {
        this.bookmarks.removeChild(this.bookmarks.firstChild);
    }
    if (tbEntry) {
        this.bookmarks.appendChild(tbEntry);
    }
}

sagecell.InteractCell.prototype.disable = function () {
    this.disable_bookmarks();
    for (var name in this.controls) {
        if (this.controls.hasOwnProperty(name) && this.controls[name].disable) {
            this.controls[name].disable();
        }
    }
}

sagecell.InteractData = {};

sagecell.InteractData.InteractControl = function (dirty_update) {
    return function (control) {
        this.control = control;
        if (typeof dirty_update === "undefined") {
            this.dirty_update = !this.control.update;
        } else {
            this.dirty_update = dirty_update;
        }
        this.eventCount = this.ignoreNext = 0;
    }
}

sagecell.InteractData.Button = sagecell.InteractData.InteractControl();

sagecell.InteractData.Button.prototype.rendered = function(id) {
    this.button = ce("button", {"id": id}, [this.control.text]);
    this.button.style.width = this.control.width;
    var that = this;
    $(this.button).click(function () {
        that.clicked = true;
        $(that.button).trigger("clickdone");
    });
    $(this.button).button();
    this.clicked = false;
    return this.button;
}

sagecell.InteractData.Button.prototype.changeHandlers = function () {
    return {"clickdone": this.button};
};

sagecell.InteractData.Button.prototype.json_value = function () {
    var c = this.clicked;
    this.clicked = false;
    return c;
}

sagecell.InteractData.Button.prototype.disable = function () {
    $(this.button).button("option", "disabled", true);
}

sagecell.InteractData.ButtonBar = sagecell.InteractData.InteractControl();

sagecell.InteractData.ButtonBar.prototype.rendered = function (id) {
    var table = ce("table", {"style": "width: auto;"});
    var i = -1;
    this.buttons = $();
    var that = this;
    for (var row = 0; row < this.control.nrows; row++) {
        var tr = ce("tr");
        for (var col = 0; col < this.control.ncols; col++) {
            var button = ce("button", {}, [this.control.value_labels[++i]]);
            button.style.width = this.control.width;
            $(button).click(function (i) {
                return function (event) {
                    that.index = i;
                    $(event.target).trigger("clickdone");
                };
            }(i));
            this.buttons = this.buttons.add(button);
            tr.appendChild(ce("td", {}, [button]));
        }
        table.appendChild(tr);
    }
    this.buttons.first().attr("id", id);
    this.index = null;
    this.buttons.button();
    return table;
}

sagecell.InteractData.ButtonBar.prototype.changeHandlers = function () {
    return {"clickdone": this.buttons};
}

sagecell.InteractData.ButtonBar.prototype.json_value = function () {
    var i = this.index;
    this.index = null;
    return i;
}

sagecell.InteractData.ButtonBar.prototype.disable = function () {
    this.buttons.button("option", "disabled", true);
}

sagecell.InteractData.Checkbox = sagecell.InteractData.InteractControl();

sagecell.InteractData.Checkbox.prototype.rendered = function (id) {
    this.input = ce("input", {"type": "checkbox", "id": id});
    this.input.checked = this.control["default"];
    return this.input;
}

sagecell.InteractData.Checkbox.prototype.changeHandlers = function () {
    return {"change": this.input};
}

sagecell.InteractData.Checkbox.prototype.json_value = function () {
    return this.input.checked;
}

sagecell.InteractData.Checkbox.prototype.update = function (value) {
    this.input.checked = value;
}

sagecell.InteractData.Checkbox.prototype.disable = function () {
    this.input.disabled = true;
}

sagecell.InteractData.ColorSelector = sagecell.InteractData.InteractControl();

sagecell.InteractData.ColorSelector.prototype.rendered = function () {
    this.selector = ce("span", {"class": "sagecell_colorSelector"});
    var text = document.createTextNode(this.control["default"]);
    this.span = ce("span", {}, [this.selector]);
    if (!this.control.hide_input) {
        this.selector.style.marginRight = "10px";
        this.span.appendChild(text);
    }
    this.selector.style.backgroundColor = this.control["default"];
    var that = this;
    $(this.selector).ColorPicker({
        "color": this.control["default"],
        "onChange": this.change = function (hsb, hex, rgb, el) {
            text.nodeValue = that.color = that.selector.style.backgroundColor = "#" + hex;
        },
        "onHide": function () {
            $(that.span).change();
        }
    });
    return this.span;
}

sagecell.InteractData.ColorSelector.prototype.changeHandlers = function() {
    return {"change": this.span};
}

sagecell.InteractData.ColorSelector.prototype.json_value = function() {
    return this.color;
}

sagecell.InteractData.ColorSelector.prototype.update = function (value) {
    $(this.selector).ColorPickerSetColor(value);
    this.change(undefined, value.substr(1));
}

sagecell.InteractData.ColorSelector.prototype.disable = function () {
    $(this.span.firstChild).off("click");
    this.span.firstChild.style.cursor = "default";
}

sagecell.InteractData.HtmlBox = sagecell.InteractData.InteractControl(false);

sagecell.InteractData.HtmlBox.prototype.rendered = function () {
    this.div = ce("div");
    this.value = this.control.value;
    $(this.div).html(this.control.value);
    return this.div;
}

sagecell.InteractData.HtmlBox.prototype.changeHandlers = function() {
    return {};
}

sagecell.InteractData.HtmlBox.prototype.json_value = function() {
    return this.value;
}

sagecell.InteractData.HtmlBox.prototype.update = function (value) {
    this.value = value;
    $(this.div).html(value);
}

sagecell.InteractData.InputBox = sagecell.InteractData.InteractControl();

sagecell.InteractData.InputBox.prototype.rendered = function (id) {
    if (this.control.subtype === "textarea") {
        this.textbox = ce("textarea",
            {"rows": this.control.height, "cols": this.control.width});
    } else if (this.control.subtype === "input") {
        this.textbox = ce("input",
            /* Most of the time these will be Sage expressions, so turn all "helpful" features */
            {"size": this.control.width,  "autocapitalize": "off", "autocorrect": "off", "autocomplete": "off"});
    }
    this.textbox.value = this.control["default"];
    this.textbox.id = id;
    if (this.control.evaluate) {
        this.textbox.style.fontFamily = "monospace";
    }
    this.event = this.control.keypress ? "keyup" : "change";
    return this.textbox;
}

sagecell.InteractData.InputBox.prototype.changeHandlers = function() {
    var h = {};
    h[this.event] = this.textbox;
    return h;
}

sagecell.InteractData.InputBox.prototype.json_value = function () {
    return this.textbox.value;
}

sagecell.InteractData.InputBox.prototype.update = function (value) {
    this.textbox.value = value;
}

sagecell.InteractData.InputBox.prototype.disable = function () {
    this.textbox.disabled = true;
}

sagecell.InteractData.InputGrid = sagecell.InteractData.InteractControl();

sagecell.InteractData.InputGrid.prototype.rendered = function (id) {
    this.textboxes = $();
    var table = ce("table", {"style": "width: auto;"});
    for (var row = 0; row < this.control.nrows; row++) {
        var tr = ce("tr");
        for (var col = 0; col < this.control.ncols; col++) {
            var textbox = ce("input", {"value": this.control["default"][row][col],
                                       "size": this.control.width,
                                       "autocapitalize": "off", "autocorrect": "off", "autocomplete": "off"});
            if (this.control.evaluate) {
                textbox.style.fontFamily = "monospace";
            }
            this.textboxes = this.textboxes.add(textbox);
            tr.appendChild(ce("td", {}, [textbox]));
        }
        table.appendChild(tr);
    }
    this.textboxes.attr("id", id);
    return table;
}

sagecell.InteractData.InputGrid.prototype.changeHandlers = function () {
    return {"change": this.textboxes};
}

sagecell.InteractData.InputGrid.prototype.json_value = function () {
    var value = [];
    for (var row = 0; row < this.control.nrows; row++) {
        var rowlist = [];
        for (var col = 0; col < this.control.ncols; col++) {
            rowlist.push(this.textboxes[row * this.control.ncols + col].value);
        }
        value.push(rowlist);
    }
    return value;
}

sagecell.InteractData.InputGrid.prototype.update = function (value, index) {
    if (index === undefined) {
        var i = -1;
        for (var row = 0; row < value.length; row++) {
            for (var col = 0; col < value[row].length; col++) {
                this.textboxes[++i].value = value[row][col];
            }
        }
    } else {
        this.textboxes[index[0] * this.control.ncols + index[1]].value = value;
    }
};

sagecell.InteractData.InputGrid.prototype.disable = function () {
    this.textboxes.prop("disabled", true);
}

sagecell.InteractData.MultiSlider = sagecell.InteractData.InteractControl();

sagecell.InteractData.MultiSlider.prototype.rendered = function () {
    var div = ce("div");
    this.sliders = $();
    this.value_boxes = $();
    this.values = this.control["default"].slice();
    this.eventCount = 1;
    for (var i = 0; i < this.control.sliders; i++) {
        var column = ce("div");
        column.style.width = "50px";
        column.style.cssFloat = "left";
        column.style.textAlign = "center";
        var slider = ce("span", {"class": "sagecell_multiSliderControl"});
        slider.style.display = "block";
        slider.style.margin = "0.25em 0.5em 1em 0.8em";
        column.appendChild(slider);
        var that = this;
        if (this.control.subtype === "continuous") {
            var textbox = ce("input", {
                "class": "sagecell_interactValueBox",
                "type": "number", 
                "min": this.control.range[i][0],
                "max": this.control.range[i][1],
                "step": "any"
            });
            textbox.value = this.values[i].toString();
            textbox.size = textbox.value.length + 1;
            textbox.style.display = this.control.display_values ? "" : "none";
            $(textbox).change((function (i) {
                return function (event) {
                    var textbox = event.target;
                    var val = parseFloat(textbox.value);
                    if (that.control.range[i][0] <= val && val <= that.control.range[i][1]) {
                        that.values[i] = val;
                        $(that.sliders[i]).slider("option", "value", val);
                        textbox.value = val.toString();
                    } else {
                        textbox.value = that.values[i].toString();
                    }
                    textbox.size = textbox.value.length + 1;
                };
            }(i)));
            $(textbox).keyup(function (event) {
                event.target.size = event.target.value.length + 1;
            });
            that.value_boxes = that.value_boxes.add(textbox);
            column.appendChild(textbox);
        } else {
            var span = ce("span", {}, [this.control.values[i][this.values[i]].toString()]);
            span.style.fontFamily = "monospace";
            span.style.display = this.control.display_values ? "" : "none";
            that.value_boxes = that.value_boxes.add(span);
            column.appendChild(span);
        }
        var slide_handler = (function (i) {
            return function (event, ui) {
                that.values[i] = ui.value;
                var value_box = that.value_boxes[i];
                if (that.control.subtype === "continuous") {
                    value_box.value = ui.value.toString();
                    value_box.size = value_box.value.length + 1;
                    $(value_box).data("old_value", value_box.value);
                } else {
                    $(value_box).text(that.control.values[i][ui.value]);
                }
            };
        }(i));
        $(slider).slider({"orientation": "vertical",
                          "value": this.control["default"][i],
                          "min": this.control.range[i][0],
                          "max": this.control.range[i][1],
                          "step": this.control.step[i]});
        $(slider).on("slide", slide_handler);
        this.sliders = this.sliders.add(slider);
        div.appendChild(column);
    }
    return div;
}

sagecell.InteractData.MultiSlider.prototype.changeHandlers = function() {
    return {"slidechange": this.sliders};
}

sagecell.InteractData.MultiSlider.prototype.json_value = function () {
    return this.values.slice();
};

sagecell.InteractData.MultiSlider.prototype.update = function (value, index) {
    if (index === undefined) {
        this.ignoreNext = value.length;
        for (var i = 0; i < value.length; i++) {
            $(this.sliders[i]).slider("option", "value", value[i]);
            $(this.sliders[i]).trigger("slide", {"value": value[i]});
        }
    } else {
        $(this.sliders[index]).slider("option", "value", value);
        $(this.sliders[index]).trigger("slide", {"value": value});
    }
};

sagecell.InteractData.MultiSlider.prototype.disable = function () {
    this.sliders.slider("option", "disabled", true);
    this.value_boxes.prop("disabled", true);
}

sagecell.InteractData.Selector = sagecell.InteractData.InteractControl();

sagecell.InteractData.Selector.prototype.rendered = function (id) {
    var that = this;
    if (this.control.subtype === "list") {
        var select = ce("select");
        for (var i = 0; i < this.control.values; i++) {
            select.appendChild(ce("option", {}, [this.control.value_labels[i]]));
        }
        this.value = select.selectedIndex = this.control["default"];
        $(select).change(function (event) {
            that.value = event.target.selectedIndex;
            $(event.target).trigger("changedone");
        });
        select.style.width = this.control.width;
        select.id = id;
        this.changing = select;
        return select;
    } else if (this.control.subtype === "radio" || this.control.subtype === "button") {
        this.changing = $();
        var table = ce("table", {"style": "width: auto;"});
        var i = -1;
        for (var row = 0; row < this.control.nrows; row++) {
            var tr = ce("tr");
            for (var col = 0; col < this.control.ncols; col++) {
                var radio_id = id + "_" + (++i);
                var option = ce("input", {"type": "radio", "name": id, "id": radio_id});
                if (i === this.control["default"]) {
                    option.checked = true;
                    this.value = i;
                }
                var label = ce("label", {"for": radio_id}, [this.control.value_labels[i]]);
                label.style.width = this.control.width;
                $(option).change(function (i) {
                    return function (event) {
                        that.value = i;
                        $(event.target).trigger("changedone");
                    };
                }(i));
                this.changing = this.changing.add(option);
                tr.appendChild(ce("td", {}, [option, label]));
            }
            table.appendChild(tr);
        }
        if (this.control.subtype === "button") {
            this.changing.button();
        }
        return table;
    }
}

sagecell.InteractData.Selector.prototype.changeHandlers = function () {
    return {"changedone": this.changing};
}

sagecell.InteractData.Selector.prototype.json_value = function () {
    return this.value;
}

sagecell.InteractData.Selector.prototype.update = function (value) {
    if (this.control.subtype === "list") {
        this.changing.selectedIndex = value;
    } else {
        this.changing[value].checked = true;
        this.changing.button("refresh");
    }
    this.value = value;
}

sagecell.InteractData.Selector.prototype.disable = function () {
    if (this.control.subtype === "list") {
        this.changing.disabled = true;
    } else if (this.control.subtype === "radio") {
        this.changing.prop("disabled", true);
    } else {
        this.changing.button("option", "disabled", true);
    }
}

sagecell.InteractData.Slider = sagecell.InteractData.InteractControl();

sagecell.InteractData.Slider.prototype.rendered = function () {
    this.continuous = this.control.subtype === "continuous" ||
                      this.control.subtype === "continuous_range";
    this.range = this.control.subtype === "discrete_range" ||
                 this.control.subtype === "continuous_range";
    var cell1 = ce("div"), cell2 = ce("div");
    var container = ce("div", {"class": "sagecell_sliderContainer"}, [cell1, cell2]);
    this.value_boxes = $();
    this.eventCount = this.range ? 2 : 1;
    this.slider = ce("div", {"class": "sagecell_sliderControl"});
    cell1.appendChild(this.slider);
    var that = this;
    if (this.continuous) {
        if (this.range) {
            this.values = this.control["default"].slice();
            $(this.slider).slider({"min": this.control.range[0],
                                   "max": this.control.range[1],
                                   "step": this.control.step,
                                   "range": true,
                                   "values": this.values});
            var min_text = ce("input", {
                "class": "sagecell_interactValueBox",
                "type": "number",
                "value": this.values[0].toString(),
                "min": this.control.range[0],
                "max": this.control.range[1],
                "step": "any"
            });
            var max_text = min_text.cloneNode();
            max_text.value = this.values[1].toString();
            min_text.size = min_text.value.length;
            max_text.size = max_text.value.length;
            $(this.slider).on("slide", function (event, ui) {
                that.values = ui.values.slice()
                min_text.value = that.values[0].toString();
                max_text.value = that.values[1].toString();
                min_text.size = min_text.value.length;
                max_text.size = max_text.value.length;
            });
            $(min_text).change(function () {
                var val = parseFloat(min_text.value);
                if (that.control.range[0] <= val &&
                        val <= $(that.slider).slider("option", "values")[1]) {
                    that.values[0] = val;
                    $(that.slider).slider("option", "values", that.values);
                    min_text.value = val.toString();
                } else {
                    min_text.value = that.values[0].toString();
                }
                min_text.size = min_text.value.length + 1;
            });
            $(max_text).change(function () {
                var val = parseFloat(max_text.value);
                if ($(that.slider).slider("option", "values")[0] <= val &&
                        val <= that.control.range[1]) {
                    that.values[1] = val;
                    $(that.slider).slider("option", "values", that.values);
                    max_text.value = val.toString();
                } else {
                    max_text.value = that.values[1].toString();
                }
                max_text.size = max_text.value.length + 1;
            });
            $([min_text, max_text]).keyup(function (event) {
                event.target.size = event.target.value.length + 1;
            });
            $([min_text, max_text]).focus(function (event) {
                event.target.size = event.target.value.length + 1;
            });
            $([min_text, max_text]).blur(function (event) {
                event.target.size = event.target.value.length;
            });
            var div = ce("div", {}, [ "(", min_text, ",", max_text, ")"]);
            div.style.whiteSpace = "nowrap";
            this.value_boxes = $([min_text, max_text]);
            div.style.fontFamily = "monospace";
            cell2.appendChild(div);
        } else {
            this.value = this.control["default"];
            $(this.slider).slider({"min": this.control.range[0],
                                   "max": this.control.range[1],
                                   "step": this.control.step,
                                   "value": this.value});
            var textbox = ce("input", {
                "class": "sagecell_interactValueBox",
                "type": "number",
                "value": this.value.toString(),
                "min": this.control.range[0],
                "max": this.control.range[1],
                "step": "any"
            });
            textbox.size = textbox.value.length + 1;
            $(this.slider).on("slide", function (event, ui) {
                textbox.value = (that.value = ui.value).toString();
                textbox.size = textbox.value.length + 1;
            });
            $(textbox).change(function () {
                var val = parseFloat(textbox.value);
                if (that.control.range[0] <= val && val <= that.control.range[1]) {
                    that.value = val;
                    $(that.slider).slider("option", "value", that.value);
                    textbox.value = val.toString();
                } else {
                    textbox.value = that.value.toString();
                }
                textbox.size = textbox.value.length + 1;
            });
            $(textbox).keyup(function (event) {
                textbox.size = textbox.value.length + 1;
            });
            cell2.appendChild(textbox);
            this.value_boxes = $(textbox);
        }
    } else if (this.range) {
        this.values = this.control["default"].slice();
        $(this.slider).slider({"min": this.control.range[0],
                               "max": this.control.range[1],
                               "step": this.control.step,
                               "range": true,
                               "values": this.values});
        var div = ce("div", {}, ["(" + this.control.values[this.values[0]] +
                                   ", " + this.control.values[this.values[1]] + ")" ]);
        div.style.fontFamily = "monospace";
        div.style.whiteSpace = "nowrap";
        $(this.slider).on("slide", function (event, ui) {
            that.values = ui.values.slice()
            this.values = ui.values.slice();
            $(div).text("(" + that.control.values[that.values[0]] +
                         ", " + that.control.values[that.values[1]] + ")");
        });
        cell2.appendChild(div);
    } else {
        this.value = this.control["default"];
        $(this.slider).slider({"min": this.control.range[0],
                               "max": this.control.range[1],
                               "step": this.control.step,
                               "value": this.value});
        var div = ce("div", {}, [this.control.values[this.value].toString()]);
        div.style.fontFamily = "monospace";
        $(this.slider).on("slide", function (event, ui) {
            $(div).text(that.control.values[that.value = ui.value].toString());
        });
        cell2.appendChild(div);
    }
    return container;
}

sagecell.InteractData.Slider.prototype.changeHandlers = function() {
    return {"slidechange": this.slider};
}

sagecell.InteractData.Slider.prototype.json_value = function () {
    if (this.range) {
        return this.values.slice();
    } else {
        return this.value;
    }
};

sagecell.InteractData.Slider.prototype.update = function (value) {
    if (this.range) {
        value = value.slice();
    }
    $(this.slider).slider("option", (this.range ? "values" : "value"), value);
    var ui = {};
    ui[this.range ? "values" : "value"] = value;
    $(this.slider).trigger("slide", ui);
}

sagecell.InteractData.Slider.prototype.disable = function () {
    $(this.slider).slider("option", "disabled", true);
    $(this.value_boxes).prop("disabled", true);
}

sagecell.InteractData.control_types = {
    "button": sagecell.InteractData.Button,
    "button_bar": sagecell.InteractData.ButtonBar,
    "checkbox": sagecell.InteractData.Checkbox,
    "color_selector": sagecell.InteractData.ColorSelector,
    "html_box": sagecell.InteractData.HtmlBox,
    "input_box": sagecell.InteractData.InputBox,
    "input_grid": sagecell.InteractData.InputGrid,
    "multi_slider": sagecell.InteractData.MultiSlider,
    "selector": sagecell.InteractData.Selector,
    "slider": sagecell.InteractData.Slider
};

sagecell.MultiSockJS = function (url, prefix) {
    sagecell.log("Starting sockjs connection to "+url+": "+(new Date()).getTime());
    if (!sagecell.MultiSockJS.channels) {
        sagecell.MultiSockJS.channels = {};
        sagecell.MultiSockJS.opened = false;
        sagecell.MultiSockJS.to_init = [];
        sagecell.MultiSockJS.sockjs = new SockJS(sagecell.URLs.sockjs, null, sagecell.sockjs_options || {});
        sagecell.MultiSockJS.sockjs.onopen = function (e) {
            sagecell.MultiSockJS.opened = true;
            while (sagecell.MultiSockJS.to_init.length > 0) {
                sagecell.MultiSockJS.to_init.shift().init_socket(e);
            }
        }
        sagecell.MultiSockJS.sockjs.onmessage = function (e) {
            var i = e.data.indexOf(",");
            var prefix = e.data.substring(0, i);
            e.data = e.data.substring(i + 1);
            if (sagecell.MultiSockJS.channels[prefix].onmessage) {
                sagecell.MultiSockJS.channels[prefix].onmessage(e);
            }
        }
        sagecell.MultiSockJS.sockjs.onclose = function (e) {
            for (var prefix in sagecell.MultiSockJS.channels) {
                if (sagecell.MultiSockJS.channels[prefix].onclose) {
                    sagecell.MultiSockJS.channels[prefix].onclose(e);
                }
            }
        }
    }
    this.prefix = url ? url.match(/^\w+:\/\/.*?\/kernel\/(.*)$/)[1] : prefix;
    sagecell.MultiSockJS.channels[this.prefix] = this;
    this.init_socket();
}

sagecell.MultiSockJS.prototype.init_socket = function (e) {
    if (sagecell.MultiSockJS.opened) {
        var that = this;
        // Run the onopen function after the current thread has finished,
        // so that onopen has a chance to be set.
        setTimeout(function () {
            if (that.onopen) {
                that.onopen(e);
            }
        }, 0);
    } else {
        sagecell.MultiSockJS.to_init.push(this);
    }
}

sagecell.MultiSockJS.prototype.send = function (msg) {
    sagecell.MultiSockJS.sockjs.send(this.prefix + "," + msg);
}

sagecell.MultiSockJS.prototype.close = function () {
    delete sagecell.MultiSockJS.channels[this.prefix];
}

// Initialize jmol
// TODO: move to a better place
jmolInitialize(sagecell.URLs.root + 'static/jmol');
jmolSetCallback("menuFile", sagecell.URLs.root + "static/jmol/appletweb/SageMenu.mnu");

})(sagecell.jQuery);
