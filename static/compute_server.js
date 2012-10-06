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

/**************************************************************
* 
* Session Class
* 
**************************************************************/

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
       sagecell.log('time since '+t+': '+(new_t-old_t));
       return new_t-old_t;
   };
};

sagecell.Session = function (outputDiv, language) {
    this.timer = sagecell.simpletimer();
    this.outputDiv = outputDiv;
    this.language = language;
    this.last_requests = {};
    this.sessionContinue = true;
    // Set this object because we aren't loading the full IPython JavaScript library
    IPython.notification_widget = {"set_message": sagecell.log};
    $.post = function (url, callback) {
        sagecell.sendRequest("POST", url, {}, function (data) {
            callback(JSON.parse(data));
        });
    }
    this.executed = false;
    this.opened = false;
    this.deferred_code = [];
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
    var old_ws = window.WebSocket, old_log = console.log;
    window.WebSocket = sagecell.MultiSockJS;
    console.log = sagecell.log;
    this.kernel = new IPython.Kernel(sagecell.URLs.kernel);
    window.WebSocket = old_ws;

    var that = this;
    this.kernel._kernel_started = function (json) {
        sagecell.log('kernel start callback: '+that.timer()+' ms.');
        this.base_url = this.base_url.substr(sagecell.URLs.root.length);
        this._kernel_started = IPython.Kernel.prototype._kernel_started;
        this._kernel_started(json);
        sagecell.log('kernel ipython startup: '+that.timer()+' ms.');
        this.shell_channel.onopen = function () {
            console.log = old_log;
            sagecell.log('kernel channel opened: '+that.timer()+' ms.');
            that.opened = true;
            while (that.deferred_code.length > 0) {
                that.execute(that.deferred_code.shift());
            }
        }
        this.iopub_channel.onopen = undefined;
    }
    this.kernel.start(IPython.utils.uuid());
    this.output_blocks = {};
    var ce = sagecell.util.createElement;
    this.outputDiv.find(".sagecell_output").prepend(
        this.session_container = ce("div", {"class": "sagecell_sessionContainer"}, [
                ce("div", {"class": "sagecell_permalink"}, [
                    ce("a", {"class": "sagecell_permalink_zip"}, [document.createTextNode("Permalink")]),
                    document.createTextNode(", "),
                    ce("a", {"class": "sagecell_permalink_query"}, [document.createTextNode("Shortened Temporary Link")])
                ]),
            this.output_blocks[null] = ce("div", {"class": "sagecell_sessionOutput sagecell_active"}, [
                this.spinner = ce("img", {"src": sagecell.URLs.spinner,
                        "alt": "Loading", "class": "sagecell_spinner"})
            ]),
            ce("div", {"class": "sagecell_poweredBy"}, [
                document.createTextNode("Powered by "),
                ce("a", {"href": "http://www.sagemath.org"}, [
                    ce("img", {"src": sagecell.URLs.sage_logo, "alt": "Sage"})
                ])
            ]),
            this.session_files = ce("div", {"class": "sagecell_sessionFiles"})
        ]));
    $([IPython.events]).on("status_busy.Kernel", function (e) {
        if (e.kernel.kernel_id === that.kernel.kernel_id) {
            that.spinner.style.display = "";
        }
    });
    $([IPython.events]).on("status_idle.Kernel", function (e) {
        if (e.kernel.kernel_id === that.kernel.kernel_id) {
            that.spinner.style.display = "none";
        }
    });
    $([IPython.events]).on("status_dead.Kernel", function (e) {
        if (e.kernel.kernel_id === that.kernel.kernel_id) {
            for (var i = 0; i < that.interacts.length; i++) {
                that.interacts[i].disable();
            }
            $(that.output_blocks[null]).removeClass("sagecell_active");
        }
    });
    this.replace_output = {};
    this.lock_output = false;
    this.files = {};
    this.eventHandlers = {};
};

sagecell.Session.prototype.execute = function (code) {
    if (this.opened) {
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
        var callbacks = {"output": $.proxy(this.handle_output, this),
                         "execute_reply": $.proxy(this.handle_execute_reply, this)};
        this.set_last_request(null, this.kernel.execute(code, callbacks, {"silent": false,
                "user_expressions": {"_sagecell_files": "sys._sage_.new_files()"}}));
    } else {
        this.deferred_code.push(code);
    }
    if (!this.executed) {
        this.executed = true;
        var that = this;
        sagecell.log('sending permalink request post: '+that.timer()+' ms.');
        sagecell.sendRequest("POST", sagecell.URLs.permalink,
            {"message": JSON.stringify({"header": {"msg_type": "execute_request"},
                                        "metadata": {},
                                        "content": {"code": code}})},
            function (data) {
                sagecell.log('POST permalink request walltime: '+that.timer() + " ms");
                that.outputDiv.find("div.sagecell_permalink a.sagecell_permalink_query")
                    .attr("href", sagecell.URLs.root + "?q=" +
                    JSON.parse(data).query + "&lang=" + that.language);
                that.outputDiv.find("div.sagecell_permalink a.sagecell_permalink_zip")
                    .attr("href", sagecell.URLs.root + "?z=" +
                    JSON.parse(data).zip + "&lang=" + that.language);
            });
    }
};

sagecell.Session.prototype.set_last_request = function (interact_id, msg_id) {
    this.kernel.set_callbacks_for_msg(this.last_requests[interact_id]);
    this.last_requests[interact_id] = msg_id;
};

sagecell.Session.prototype.appendMsg = function(msg, text) {
    // Append the message to the div of messages
    // Use $.text() so that strings are automatically escaped
    this.outputDiv.find(".sagecell_messages").append(document.createElement('div')).children().last().text(text+JSON.stringify(msg));
};

sagecell.Session.prototype.output = function(html, block_id, create) {
    // create===false means just pass back the last child of the output_block
    // if we aren't replacing the output block
    if (create === undefined) {
        create = true;
    }
    var output_block=$(this.output_blocks[block_id]);
    if (block_id !== undefined && block_id !== null && this.replace_output[block_id]) {
        output_block.empty();
        this.replace_output[block_id]=false;
        create=true;
    }
    var out;
    if (create) {
        out = output_block.append(html).children().last();
    } else {
        out = output_block.children().last();
    }
    return out;
};

sagecell.Session.prototype.handle_execute_reply = function(msg) {
    
    sagecell.log('reply walltime: '+this.timer() + " ms");
    if(msg.status==="error") {
        this.output('<pre class="sagecell_pyerr"></pre>',null)
            .html(IPython.utils.fixConsole(msg.traceback.join("\n")));
    } 
    var payload = msg.payload[0];
    if (payload && payload.new_files){
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
        var filepath=sagecell.URLs.root+this.kernel.kernel_url+'/files/';
        for (j in this.files) {
            //TODO: escape filenames and id
            html+='<a href="'+filepath+j+'?q='+this.files[j]+'" target="_blank">'+j+'</a> [Updated '+this.files[j]+' time(s)]<br>\n';
        }
        html+="</div>";
        output_block.html(html).effect("pulsate", {times:1}, 500);
    }
}
    
sagecell.Session.prototype.handle_output = function (msg_type, content, metadata) {
    var block_id = metadata.interact_id || null;
    // Handle each stream type.  This should probably be separated out into different functions.
    switch (msg_type) {
    case "stream":
        var new_pre = !$(this.output_blocks[block_id]).children().last().hasClass("sagecell_" + content.name);
        var out = this.output("<pre class='sagecell_" + content.name + "'></pre>", block_id, new_pre);
        out.text(out.text() + content.data);
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
        var filepath=sagecell.URLs.root+this.kernel.kernel_url+'/files/';
        if (content.data["application/sage-interact"]) {
            this.interacts.push(new sagecell.InteractCell(this, content.data["application/sage-interact"], block_id));
        } else if (content.data["text/html"]) {
            var html = content.data['text/html'].replace(/cell:\/\//gi, filepath);
            this.output("<div></div>", block_id).html(html);
        } else if (content.data["text/image-filename"]) {
            this.output("<img src='"+filepath+content.data["text/image-filename"]+"'/>", block_id);
        } else if (content.data["image/png"]) {
            this.output("<img src='data:image/png;base64,"+content.data["image/png"]+"'/>", block_id);
        } else if(content.data['application/x-jmol']) {
            sagecell.log('making jmol applet');
            jmolSetDocument(false);
            this.output(jmolApplet(500, 'set defaultdirectory "'+filepath+content.data['application/x-jmol']+'";\n script SCRIPT;\n'),block_id);            
        } else if (content.data["text/plain"]) {
            this.output("<pre></pre>", block_id).text(content.data["text/plain"]);
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

/**************************************************************
* 
* InteractCell Class
* 
**************************************************************/

sagecell.InteractCell = function (session, data, parent_block) {
    this.interact_id = data.new_interact_id;
    this.function_code = data.function_code;
    this.controls = {};
    this.session = session;
    this.update = data.update;
    this.layout = data.layout;
    this.msg_id = data.msg_id;

    var controls = data.controls;
    for (var name in controls) {
        if (controls.hasOwnProperty(name)) {
            this.controls[name] = new sagecell.InteractData.control_types[controls[name].control_type](controls[name]);
        }
    }
    this.renderCanvas(parent_block);
    this.bindChange();
}

sagecell.InteractCell.prototype.bindChange = function () {
    var that = this;
    var handler = function (event, ui) {
        $(that.rows[event.data.name]).addClass("sagecell_dirtyControl");
        if (that.update[event.data.name]) {
            var code = "sys._sage_.update_interact(" + JSON.stringify(that.interact_id) + ",{";
            var kwargs = [];
            for (var name in that.controls) {
                if (that.controls.hasOwnProperty(name) &&
                        that.update[event.data.name].indexOf(name) !== -1) {
                    kwargs.push(JSON.stringify(name) + ":" + that.controls[name].py_value(ui));
                    $(that.rows[name]).removeClass("sagecell_dirtyControl");
                }
            }
            code += kwargs.join(",") + "})";
            that.session.replace_output[that.interact_id] = true;
            that.session.execute(code);
        }
    };
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
};

sagecell.InteractCell.prototype.renderCanvas = function (parent_block) {
    /*

      The template is:
      <td>{{label}}</td><td>{{control html code}}</td>

      if the control has a label. If not, then the template is:

      <td colspan='2'>{{control html code}}</td>

     */
    var cells = {};
    var ce = sagecell.util.createElement;
    var locs = [["top_left",    "top_center",    "top_right"   ],
                ["left",        null,            "right"       ],
                ["bottom_left", "bottom_center", "bottom_right"]];
    var table = ce("table", {"class": "sagecell_interactContainer"});
    for (var row = 0; row < 3; row++) {
        var tr = ce("tr");
        for (var col = 0; col < 3; col++) {
            var td;
            if (locs[row][col]) {
                td = ce("td", {"class": "sagecell_interactContainer"});
                cells[locs[row][col]] = td;
            } else {
                td = ce("td", {"class": "sagecell_interactOutput"});
                this.session.output_blocks[this.interact_id] = td;
            }
            tr.appendChild(td);
        }
        table.appendChild(tr);
    }
    this.rows = {};
    for (var loc in this.layout) {
        if (this.layout.hasOwnProperty(loc)) {
            var table2 = ce("table", {"class": "sagecell_interactControls"});
            for (var i = 0; i < this.layout[loc].length; i++) {
                var tr = ce("tr");
                var row = this.layout[loc][i];
                for (var j = 0; j < row.length; j++) {
                     var varname = this.layout[loc][i][j];
                     var varcontrol = this.controls[varname];
                    var id = this.interact_id + "_" + varname;
                    var right = ce("td", {"class": "sagecell_interactcontrolcell"}, [
                        varcontrol.rendered(id)
                    ]);
                    if (varcontrol.control.label !== "") {
                        var left = ce("td", {"class": "sagecell_interactcontrollabelcell"}, [
                            ce("label", {"for": id, "title": varname}, [
                                document.createTextNode(varcontrol.control.label || varname)
                            ])
                        ]);
                        tr.appendChild(left);
                        this.rows[varname] = [left, right];                                
                    } else {
                        right.setAttribute("colspan", "2");
                        this.rows[varname] = [right];
                    }
                    tr.appendChild(right);
                }
                table2.appendChild(tr);
            }
            cells[loc].appendChild(table2);
        }
    }
    this.session.output(table, parent_block);
}

sagecell.InteractCell.prototype.disable = function () {
    for (var name in this.controls) {
        if (this.controls.hasOwnProperty(name)) {
            this.controls[name].disable();
        }
    }
}

sagecell.InteractData = {};

sagecell.InteractData.InteractControl = function () {
    return function (control) {
        this.control = control;
    }
}

sagecell.InteractData.Button = sagecell.InteractData.InteractControl();

sagecell.InteractData.Button.prototype.rendered = function() {
    this.button = sagecell.util.createElement("button", {}, [
        document.createTextNode(this.control.text)
    ]);
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

sagecell.InteractData.Button.prototype.py_value = function () {
    var c = this.clicked;
    this.clicked = false;
    return c ? "True" : "False";
}

sagecell.InteractData.Button.prototype.disable = function () {
    $(this.button).button("option", "disabled", true);
}

sagecell.InteractData.ButtonBar = sagecell.InteractData.InteractControl();

sagecell.InteractData.ButtonBar.prototype.rendered = function () {
    var ce = sagecell.util.createElement;
    var table = ce("table", {"style": "width: auto;"});
    var i = -1;
    this.buttons = $();
    var that = this;
    for (var row = 0; row < this.control.nrows; row++) {
        var tr = ce("tr");
        for (var col = 0; col < this.control.ncols; col++) {
            var button = ce("button", {}, [
                document.createTextNode(this.control.value_labels[++i])
            ]);
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
    this.index = null;
    this.buttons.button();
    return table;
}

sagecell.InteractData.ButtonBar.prototype.changeHandlers = function () {
    return {"clickdone": this.buttons};
}

sagecell.InteractData.ButtonBar.prototype.py_value = function () {
    var i = this.index;
    this.index = null;
    return i !== null ? i : "None";
}

sagecell.InteractData.ButtonBar.prototype.disable = function () {
    this.buttons.button("option", "disabled", true);
}

sagecell.InteractData.Checkbox = sagecell.InteractData.InteractControl();

sagecell.InteractData.Checkbox.prototype.rendered = function () {
    this.input = sagecell.util.createElement("input", {"type": "checkbox"});
    this.input.checked = this.control["default"];
    return this.input;
}

sagecell.InteractData.Checkbox.prototype.changeHandlers = function () {
    return {"change": this.input};
}

sagecell.InteractData.Checkbox.prototype.py_value = function () {
    return this.input.checked ? "True" : "False";
}

sagecell.InteractData.Checkbox.prototype.disable = function () {
    this.input.disabled = true;
}

sagecell.InteractData.ColorSelector = sagecell.InteractData.InteractControl();

sagecell.InteractData.ColorSelector.prototype.rendered = function () {
    var selector = sagecell.util.createElement("span", {"class": "sagecell_colorSelector"});
    var text = document.createTextNode(this.control["default"]);
    this.span = sagecell.util.createElement("span", {}, [selector]);
    if (!this.control.hide_input) {
        selector.style.marginRight = "10px";
        this.span.appendChild(text);
    }
    selector.style.backgroundColor = this.control["default"];
    var that = this;
    $(selector).ColorPicker({
        "color": this.control["default"],
        "onChange": function (hsb, hex, rgb, el) {
            text.nodeValue = that.color = selector.style.backgroundColor = "#" + hex;
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

sagecell.InteractData.ColorSelector.prototype.py_value = function() {
    return JSON.stringify(this.color);
}

sagecell.InteractData.ColorSelector.prototype.disable = function () {
    $(this.span.firstChild).off("click");
    this.span.firstChild.style.cursor = "default";
}

sagecell.InteractData.HtmlBox = sagecell.InteractData.InteractControl();

sagecell.InteractData.HtmlBox.prototype.rendered = function () {
    this.div = document.createElement("div");
    $(this.div).html(this.control.value);
    return this.div;
}

sagecell.InteractData.HtmlBox.prototype.changeHandlers = function() {
    return {};
}

sagecell.InteractData.HtmlBox.prototype.py_value = function() {
    return "None";
}

sagecell.InteractData.HtmlBox.prototype.disable = function () {}

sagecell.InteractData.InputBox = sagecell.InteractData.InteractControl();

sagecell.InteractData.InputBox.prototype.rendered = function () {
    if (this.control.subtype === "textarea") {
        this.textbox = sagecell.util.createElement("textarea",
            {"rows": this.control.height, "cols": this.control.width});
    } else if (this.control.subtype === "input") {
        this.textbox = sagecell.util.createElement("input",
            /* Most of the time these will be Sage expressions, so turn all "helpful" features */
            {"size": this.control.width,  "autocapitalize": "off", "autocorrect": "off", "autocomplete": "off"});
    }
    this.textbox.value = this.control["default"];
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

sagecell.InteractData.InputBox.prototype.py_value = function () {
    return "u" + JSON.stringify(this.textbox.value);
}

sagecell.InteractData.InputBox.prototype.disable = function () {
    this.textbox.disabled = true;
}

sagecell.InteractData.InputGrid = sagecell.InteractData.InteractControl();

sagecell.InteractData.InputGrid.prototype.rendered = function () {
    this.textboxes = $();
    var ce = sagecell.util.createElement;
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
    return table;
}

sagecell.InteractData.InputGrid.prototype.changeHandlers = function () {
    return {"change": this.textboxes};
}

sagecell.InteractData.InputGrid.prototype.py_value = function () {
    var string = "[";
    for (var row = 0; row < this.control.nrows; row++) {
        string += "[";
        for (var col = 0; col < this.control.ncols; col++) {
            string += "u" + JSON.stringify(this.textboxes[row * this.control.ncols + col].value) + ","
        }
        string += "],";
    }
    return string + "]";
}

sagecell.InteractData.InputGrid.prototype.disable = function () {
    this.textboxes.attr("disabled", true);
}

sagecell.InteractData.MultiSlider = sagecell.InteractData.InteractControl();

sagecell.InteractData.MultiSlider.prototype.rendered = function () {
    var ce = sagecell.util.createElement;
    var div = ce("div");
    this.sliders = $();
    this.value_boxes = $();
    this.values = this.control["default"].slice();
    for (var i = 0; i < this.control.sliders; i++) {
        var column = ce("div");
        column.style.width = "50px";
        column.style.cssFloat = "left";
        column.style.textAlign = "center";
        var slider = ce("span", {"class": "sagecell_multiSliderControl"});
        slider.style.display = "block";
        slider.style.margin = "1em 0.5em 1em 0.8em";
        column.appendChild(slider);
        var that = this;
        if (this.control.subtype === "continuous") {
            var textbox = ce("input", {"class": "sagecell_interactValueBox", "type": "number", 
                                       "min": this.control.range[i][0], "max": this.control.range[i][1]});
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
            var span = ce("span", {},
                    [document.createTextNode(this.values[i].toString())]);
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
                          "step": this.control.step[i],
                          "slide": slide_handler});
        this.sliders = this.sliders.add(slider);
        div.appendChild(column);
    }
    return div;
}

sagecell.InteractData.MultiSlider.prototype.changeHandlers = function() {
    return {"slidechange": this.sliders};
}

sagecell.InteractData.MultiSlider.prototype.py_value = function () {
    return JSON.stringify(this.values);
}

sagecell.InteractData.MultiSlider.prototype.disable = function () {
    this.sliders.slider("option", "disabled", true);
    this.value_boxes.attr("disabled", true);
}

sagecell.InteractData.Selector = sagecell.InteractData.InteractControl();

sagecell.InteractData.Selector.prototype.rendered = function (control_id) {
    var ce = sagecell.util.createElement;
    var that = this;
    if (this.control.subtype === "list") {
        var select = ce("select");
        for (var i = 0; i < this.control.values; i++) {
            select.appendChild(ce("option", {}, [
                document.createTextNode(this.control.value_labels[i])
            ]));
        }
        this.value = select.selectedIndex = this.control["default"];
        $(select).change(function (event) {
            that.value = event.target.selectedIndex;
            $(event.target).trigger("changedone");
        });
        select.style.width = this.control.width;
        this.changing = select;
        return select;
    } else if (this.control.subtype === "radio" || this.control.subtype === "button") {
        this.changing = $();
        var table = ce("table", {"style": "width: auto;"});
        var i = -1;
        for (var row = 0; row < this.control.nrows; row++) {
            var tr = ce("tr");
            for (var col = 0; col < this.control.ncols; col++) {
                var id = control_id + "_" + (++i);
                var option = ce("input", {"type": "radio", "name": control_id, "id": id});
                if (i === this.control["default"]) {
                    option.checked = true;
                    this.value = i;
                }
                var label = ce("label", {"for": id}, [
                    document.createTextNode(this.control.value_labels[i])
                ]);
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

sagecell.InteractData.Selector.prototype.py_value = function () {
    return JSON.stringify(this.value);
}

sagecell.InteractData.Selector.prototype.disable = function () {
    if (this.control.subtype === "list") {
        this.changing.disabled = true;
    } else if (this.control.subtype === "radio") {
        this.changing.attr("disabled", true);
    } else {
        this.changing.button("option", "disabled", true);
    }   
}

sagecell.InteractData.Slider = sagecell.InteractData.InteractControl();

sagecell.InteractData.Slider.prototype.rendered = function () {
    var ce = sagecell.util.createElement;
    this.continuous = this.control.subtype === "continuous" ||
                      this.control.subtype === "continuous_range";
    this.range = this.control.subtype === "discrete_range" ||
                 this.control.subtype === "continuous_range";
    var container = ce("span");
    this.value_boxes = $();
    container.style.whitespace = "nowrap";
    this.slider = ce("span", {"class": "sagecell_sliderControl"});
    container.appendChild(this.slider);
    var that = this;
    if (this.continuous) {
        if (this.range) {
            this.values = this.control["default"].slice();
            $(this.slider).slider({"min": this.control.range[0],
                                   "max": this.control.range[1],
                                   "step": this.control.step,
                                   "range": true,
                                   "values": this.values,});
            var min_text = ce("input", {"class": "sagecell_interactValueBox", "type": "number",
                                        "value": this.values[0].toString(), "min": this.control.range[0],
                                        "max": this.control.range[1], "step": this.control.step});
            var max_text = ce("input", {"class": "sagecell_interactValueBox", "type": "number",
                                        "value": this.values[1].toString(), "min": this.control.range[0],
                                        "max": this.control.range[1], "step": this.control.step});
            min_text.size = min_text.value.length;
            max_text.size = max_text.value.length;
            min_text.style.marginTop = max_text.style.marginTop = "3px";
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
            var span = ce("span", {}, [
                document.createTextNode("("),
                min_text,
                document.createTextNode(", "),
                max_text,
                document.createTextNode(")")
            ]);
            this.value_boxes = $([min_text, max_text]);
            span.style.fontFamily = "monospace";
            container.appendChild(span);
        } else {
            this.value = this.control["default"];
            $(this.slider).slider({"min": this.control.range[0],
                                   "max": this.control.range[1],
                                   "step": this.control.step,
                                   "value": this.value});
            var textbox = ce("input", {"class": "sagecell_interactValueBox", "type": "number",
                                       "value": this.value.toString(), "min": this.control.range[0],
                                       "max": this.control.range[1], "step": this.control.step});
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
            container.appendChild(textbox);
            this.value_boxes = $(textbox);
        }
    } else if (this.range) {
        this.values = this.control["default"].slice();
        $(this.slider).slider({"min": this.control.range[0],
                               "max": this.control.range[1],
                               "step": this.control.step,
                               "range": true,
                               "values": this.values});
        var span = ce("span", {}, [
            document.createTextNode("(" + this.control.values[this.values[0]] +
                    ", " + this.control.values[this.values[1]] + ")")
        ]);
        span.style.fontFamily = "monospace";
        $(this.slider).on("slide", function (event, ui) {
            that.values = ui.values.slice()
            this.values = ui.values.slice();
            $(span).text("(" + that.control.values[that.values[0]] +
                         ", " + that.control.values[that.values[1]] + ")");
        });
        container.appendChild(span);
    } else {
        this.value = this.control["default"];
        $(this.slider).slider({"min": this.control.range[0],
                               "max": this.control.range[1],
                               "step": this.control.step,
                               "value": this.value});
        var span = ce("span", {}, [
            document.createTextNode(this.control.values[this.value].toString())
        ]);
        span.style.fontFamily = "monospace";
        $(this.slider).on("slide", function (event, ui) {
            $(span).text(that.control.values[that.value = ui.value].toString());
        });
        container.appendChild(span);
    }
    return container;
}

sagecell.InteractData.Slider.prototype.changeHandlers = function() {
    return {"slidechange": this.slider};
}

sagecell.InteractData.Slider.prototype.py_value = function () {
    if (this.range) {
            return "(" + JSON.stringify(this.values[0]) + "," +
                         JSON.stringify(this.values[1]) + ")";
    } else {
        return JSON.stringify(this.value);
    }
}

sagecell.InteractData.Slider.prototype.disable = function () {
    $(this.slider).slider("option", "disabled", true);
    this.value_boxes.attr("disabled", true);
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

sagecell.MultiSockJS = function (url) {
    sagecell.log("Starting sockjs connection to "+url+": "+(new Date()).getTime());
    if (!sagecell.MultiSockJS.channels) {
        sagecell.MultiSockJS.channels = {};
        sagecell.MultiSockJS.opened = false;
        sagecell.MultiSockJS.to_init = [];
        sagecell.MultiSockJS.sockjs = new SockJS(sagecell.URLs.sockjs);
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
    this.prefix = url.match(/^\w+:\/\/.*?\/kernel\/(.*)$/)[1];
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
