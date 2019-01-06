define([
    "jquery",
    "base/js/namespace",
    "base/js/events",
    "services/kernels/kernel",
    "interact_cell",
    "interact_controls",
    "multisockjs",
    "utils",
    "widgets"
], function(
    $,
    IPython,
    events,
    Kernel,
    InteractCell,
    interact_controls,
    MultiSockJS,
    utils,
    widgets
) {
"use strict";
var undefined;

Kernel.Kernel.prototype.kill = function () {
    if (this.running) {
        this.running = false;
        utils.sendRequest("DELETE", this.kernel_url);
    }
};

var ce = utils.createElement;

var interacts = {};

var stop = function(event) {
    event.stopPropagation();
}
var close = null;

var jmolCounter = 0;

function Session(outputDiv, language, interact_vals, k, linked) {
    this.timer = utils.simpleTimer();
    this.outputDiv = outputDiv;
    this.outputDiv[0].sagecell_session = this;
    this.language = language;
    this.interact_vals = interact_vals;
    this.linked = linked;
    this.last_requests = {};
    this.sessionContinue = true;
    this.namespaces = {};


    // Set this object because we aren't loading the full IPython JavaScript library
    IPython.notification_widget = {"set_message": console.debug};

    this.interacts = [];
    if (window.addEventListener) {
        // Prevent Esc key from closing WebSockets and XMLHttpRequests in Firefox
        window.addEventListener("keydown", function(event) {
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
    var that = this;
    if (linked && sagecell.kernels[k]) {
        this.kernel = sagecell.kernels[k];
    } else {
        var old_ws = window.WebSocket;
        // sometimes (IE8) window.console is not defined (until the console is opened)
        var old_console = window.console;
        var old_log = window.console && console.log;
        window.WebSocket = MultiSockJS;
        window.console = window.console || {};
        this.kernel = sagecell.kernels[k] = new Kernel.Kernel(utils.URLs.kernel);
        this.kernel.comm_manager.register_target('threejs', utils.always_new(widgets.ThreeJS(this)));
        this.kernel.comm_manager.register_target('graphicswidget', utils.always_new(widgets.Graphics(this)));
        this.kernel.comm_manager.register_target('matplotlib', utils.always_new(widgets.MPL(this)));

        this.kernel.session = this;
        this.kernel.opened = false;
        this.kernel.deferred_code = [];
        window.WebSocket = old_ws;

        this.kernel.post = function(url, callback) {
            utils.sendRequest("POST", url, {}, function(data) { callback(JSON.parse(data)); });
        }

    // Copied from Jupyter notebook and slightly modified to add deferred code execution
    this.kernel._ws_opened = function(evt) {
        /**
         * Handle a websocket entering the open state,
         * signaling that the kernel is connected when websocket is open.
         *
         * @function _ws_opened
         */
        if (this.is_connected()) {
            // ADDED BLOCK START
            this.opened = true;
            while (this.deferred_code.length > 0) {
                this.session.execute(this.deferred_code.shift());
            }
            // ADDED BLOCK END
            // all events ready, trigger started event.
            this._kernel_connected();
        }
    };

        this.kernel.start({CellSessionID: utils.cellSessionID(), timeout: linked ? 'inf' : 0, accepted_tos : "true"});
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
                    "src": utils.URLs.spinner,
                    "alt": "Loading",
                    "class": "sagecell_spinner"
                })
            ]),
            ce("div", {"class": "sagecell_poweredBy"}, [
                ce("a", {"href": utils.URLs.help, "target": "_blank"},
                    ["Help"]),
                " | Powered by ",
                ce("a", {"href": "http://www.sagemath.org", "target": "_blank"},
                    ["SageMath"]),
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
    this.updateLinks = function(new_vals) {
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
            console.debug('sending permalink request post:', that.timer());
            var args = {
                "code": that.rawcode,
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
            utils.sendRequest("POST", utils.URLs.permalink, args, function(data) {
                data = JSON.parse(data);
                console.debug('POST permalink request:', that.timer());
                if (data.n !== n) {
                    return;
                }
                pl_qlink.href = links.query = utils.URLs.root + "?q=" + data.query;
                links.zip = utils.URLs.root + "?z=" + data.zip + "&lang=" + that.language;
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
    pl_button.addEventListener("click", function() {
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
    events.on("kernel_busy.Kernel", function(evt, data) {
        console.debug("kernel_busy.Kernel for", data.kernel.id);
        if (data.kernel.id === that.kernel.id) {
            that.spinner.style.display = "";
        }
    });
    pl_chkbox.addEventListener("change", function() {
        that.updateLinks(false);
    });
    events.on("kernel_idle.Kernel", function(evt, data) {
        console.debug("kernel_idle.Kernel for", data.kernel.id);
        if (data.kernel.id !== that.kernel.id) {
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
            that.interacts[j].state(that.interact_vals[i].state, (function(interact, val) {
                return function() {
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
    var killkernel = function(evt, data) {
        console.debug("killkernel for", data.kernel.id);
        if (data.kernel.id === that.kernel.id) {
            that.spinner.style.display = "none";
            for (var i = 0; i < that.interacts.length; i++) {
                that.interacts[i].disable();
            }
            $(that.output_block).removeClass("sagecell_active");
            data.kernel.shell_channel = {};
            data.kernel.iopub_channel = {};
            sagecell.kernels[k] = null;
        }
    }
    events.on("kernel_dead.Kernel", killkernel);
    events.on("kernel_disconnected.Kernel", killkernel);
    this.lock_output = false;
    this.files = {};
    this.eventHandlers = {};
};

Session.prototype.send_message = function() {
    this.kernel.send_shell_message.apply(this.kernel, arguments);
};

Session.prototype.execute = function(code) {
    if (this.kernel.opened) {
        console.debug('opened and executing in kernel:', this.timer());
        var pre;
        //TODO: do this wrapping of code on the server, not in javascript
        //Maybe the system can be sent in metadata in the execute_request message
        this.rawcode = code;
        if (this.language === "python") {
            pre = "exec ";
        } else if (this.language === "html") {
            pre = "html";
        } else if (this.language !== "sage") {
            pre = "print " + this.language + ".eval";
        }
        if (this.language === "r") {
            code = "options(bitmapType='cairo')\n" + code + "\ngraphics.off()";
        }
        if (pre) {
            code = pre + '("""' + code.replace(/"/g, '\\"') + '""").strip()'
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

Session.prototype.set_last_request = function(interact_id, msg_id) {
    this.kernel.set_callbacks_for_msg(this.last_requests[interact_id]);
    this.last_requests[interact_id] = msg_id;
};

Session.prototype.appendMsg = function(msg, text) {
    // Append the message to the div of messages
    // Use $.text() so that strings are automatically escaped
    $(ce('div')).text(text+JSON.stringify(msg)).prependTo(this.outputDiv.find(".sagecell_messages"));
};

Session.prototype.clear = function(block_id, changed) {
    var output_block = $(block_id === null ? this.output_block : interacts[block_id].output_block);
    if (output_block.length===0) {return;}
    output_block[0].style.minHeight = output_block.height() + "px";
    setTimeout(function() {
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

Session.prototype.output = function(html, block_id) {
    // Return a DOM element for new content. The html is appended to the html
    // block and the newly appended content element is returned.
    var output_block = $(block_id === null ?
        this.output_block : interacts[block_id].output_block);
    if (output_block.length !== 0) {
        return $(html).appendTo(output_block);
    }
};

Session.prototype.handle_message_reply = function(msg) {
};

Session.prototype.handle_execute_reply = function(msg) {
    console.debug("handle_execute_reply:", this.timer());
    /* This would give two error messages (since a pyerr should have already come)
      if(msg.status==="error") {
        this.output('<pre class="sagecell_pyerr"></pre>',null)
            .html(utils.fixConsole(msg.traceback.join("\n")));
    }
    */
    // TODO: handle payloads with a payload callback, instead of in the execute_reply
    // That would be much less brittle
    var payload = msg.content.payload[0];
    if (!payload) {
        return;
    }
    if (payload.new_files && payload.new_files.length > 0) {
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
    if (payload.data && payload.data['text/plain']) {
        this.output('<pre class="sagecell_payload"></pre>', null).html(
            utils.fixConsole(payload.data['text/plain']));
    }
}

Session.prototype.handle_output = function(msg, default_block_id) {
    console.debug("handle_output");
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
        var block = $(block_id === null ? this.output_block : interacts[block_id].output_block);
        var last = block.children().last();
        var last_output = (last.length === 0 ? undefined : last);
        if (last_output && last_output.hasClass("sagecell_" + content.name)) {
            last_output.text(last_output.text() + content.text);
        } else {
            var html = ce('pre', {class: 'sagecell_' + content.name},
                             [content.text]);
            this.output(html, block_id);
        }
        break;
    case "error":
        if (content.traceback.join) {
            this.output('<pre class="sagecell_pyerr"></pre>', block_id)
                .html(utils.fixConsole(content.traceback.join("\n")));
        }
        break;
    case "display_data":
    case "execute_result":
        var filepath = this.kernel.kernel_url + '/files/';
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
    console.debug('handled output:', this.timer());
    this.appendMsg(content, "Accepted: ");
    // need to mathjax the entire output, since output_block could just be part of the output
    var output = this.outputDiv.find(".sagecell_output").get(0);
    MathJax.Hub.Queue(["Typeset",MathJax.Hub, output]);
    MathJax.Hub.Queue([function() {$(output).find(".math").removeClass('math');}]);
};

// dispatch table on mime type
Session.prototype.display_handlers = {
    'application/sage-interact': function(data, block_id) {
        this.interacts.push(interacts[data.new_interact_id] = new InteractCell(this, data, block_id));
    },
    'application/sage-interact-update': function(data) {
        interacts[data.interact_id].updateControl(data);
    },
    'application/sage-interact-new-control': function(data) {
        interacts[data.interact_id].newControl(data);
    },
    'application/sage-interact-del-control': function(data) {
        interacts[data.interact_id].delControl(data);
    },
    'application/sage-interact-bookmark': function(data) {
        interacts[data.interact_id].createBookmark(data.name, data.values);
    },
    'application/sage-interact-control': function(data, block_id) {
        var that = this;
        var control_class = interact_controls[data.control_type];
        if (control_class === undefined) {return false;}
        var control = new control_class(this, data.control_id);
        control.create(data, block_id);
        $.each(data.variable, function(index, value) {
            that.register_control(data.namespace, value, control);

        });
        control.update(data.namespace, data.variable);
    },
    'application/sage-interact-variable': function(data) {
        this.update_variable(data.namespace, data.variable, data.control);
    },
    'application/sage-clear': function(data, block_id) {
        this.clear(block_id, data.changed);
    },
    'text/html': function(data, block_id, filepath) {
        this.output("<div></div>", block_id).html(data.replace(/cell:\/\//gi, filepath));
    },
    'application/javascript': function(data) {
        eval(data);
    },
    'text/image-filename': function(data, block_id, filepath) {
        this.output("<img src='" + filepath + data + "'/>", block_id);
    },
    'image/png': function(data, block_id) {
        this.output("<img src='data:image/png;base64," + data + "'/>", block_id);
    },
    'application/x-jmol': function(data, block_id, filepath) {
        Jmol.setDocument(false);
        var info = {
            height: 500,
            width: 500,
            color: "white",
            j2sPath: utils.URLs.root + "static/jsmol/j2s",
            serverURL: utils.URLs.root + "static/jsmol/php/jsmol.php",
            coverImage: filepath + data + "/preview.png",
            deferUncover: true,
            disableInitialConsole: true,
            script: "set defaultdirectory '" + filepath + data + "/scene.zip';\n script SCRIPT;\n",
            menuFile: utils.URLs.root + "static/SageMenu.mnu"
        };
        this.output(Jmol.getAppletHtml("scJmol" + jmolCounter++, info), block_id);
    },
    "application/x-canvas3d": function(data, block_id, filepath) {
        var div = this.output(document.createElement("div"), block_id);
        var old_cw = [window.hasOwnProperty("cell_writer"), window.cell_writer],
            old_tr = [window.hasOwnProperty("translations"), window.translations];
        window.cell_writer = {"write": function(html) {
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
};

Session.prototype.register_control = function(namespace, variable, control) {
    if (this.namespaces[namespace] === undefined) {
        this.namespaces[namespace] = {};
    }
    if (this.namespaces[namespace][variable] === undefined) {
        this.namespaces[namespace][variable] = []
    }
    this.namespaces[namespace][variable].push(control);
};

Session.prototype.get_variable_controls = function(namespace, variable) {
    var notify = {};
    if (this.namespaces[namespace] && this.namespaces[namespace][variable]) {
        $.each(this.namespaces[namespace][variable], function(index, control) {
            notify[control.control_id] = control;
        });
    }
    return notify;
};

Session.prototype.update_variable = function(namespace, variable, control_id) {
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

Session.prototype.destroy = function() {
    this.clear(null);
    $(this.session_container).remove();
};

return Session;
});
