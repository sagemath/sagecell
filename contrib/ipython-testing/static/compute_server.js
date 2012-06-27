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

/**************************************************************
* 
* Session Class
* 
**************************************************************/

sagecell.Session = function (outputDiv, hide) {
    this.outputDiv = outputDiv;
    this.last_requests = {};
    this.sessionContinue = true;
    // Set this object because we aren't loading the full IPython JavaScript library
    IPython.notification_widget = {"set_message": console.log};
    this.opened = false;
    this.deferred_code = [];
    this.kernel = new IPython.Kernel(sagecell.$URL.kernel);
    var that = this;
    this.kernel._kernel_started = function (json) {
        this._kernel_started = IPython.Kernel.prototype._kernel_started;
        this._kernel_started(json);
        this.shell_channel.onopen = function () {
            that.opened = true;
            while (that.deferred_code.length > 0) {
                that.execute(that.deferred_code.shift());
            }
        };
        this.iopub_channel.onopen = undefined;
    };
    this.kernel.start(IPython.utils.uuid());
    this.output_blocks = {};
    var ce = sagecell.util.createElement;
    this.outputDiv.find(".sagecell_output").prepend(
        this.session_container = ce("div", {"class": "sagecell_sessionContainer"}, [
            this.output_blocks[null] = ce("div", {"class": "sagecell_sessionOutput sagecell_active"}, [
                this.spinner = ce("img", {"src": sagecell.$URL.spinner_img,
                        "alt": "Loading", "class": "sagecell_spinner"})
            ]),
            ce("div", {"class": "sagecell_poweredBy"}, [
                document.createTextNode("Powered by "),
                ce("a", {"href": "http://www.sagemath.org"}, [
                    ce("img", {"src": sagecell.$URL.powered_by_img, "alt": "Sage"})
                ]),
            ]),
            this.session_files = ce("div", {"class": "sagecell_sessionFiles"})
        ]));
    if (hide) {
        $(this.session_container).hide();
    }
    this.open_count = 1;
    this.replace_output = {};
    this.lock_output = false;
    this.files = {};
    this.eventHandlers = {};
};

sagecell.Session.prototype.execute = function (code) {
    if (this.opened) {
        var callbacks = {"execute_reply": $.proxy(this.handle_execute_reply, this),
                         "output": $.proxy(this.handle_output, this)};
        this.set_last_request(null, this.kernel.execute(code, callbacks, {"silent": false}));
    } else {
        this.deferred_code.push(code);
    }
};

sagecell.Session.prototype.set_last_request = function (interact_id, msg_id) {
    this.kernel.set_callbacks_for_msg(this.last_requests[interact_id],
        {"execute_reply": $.proxy(this.handle_execute_reply, this)});
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

sagecell.Session.prototype.handle_output = function (msg_type, content) {
    var block_id = content.interact_id || null;
    // Handle each stream type.  This should probably be separated out into different functions.
    switch(msg_type) {
    case 'stream':
        var new_pre = !$(this.output_blocks[block_id]).children().last().hasClass("sagecell_" + content.name);
        var out = this.output("<pre class='sagecell_" + content.name + "'></pre>", block_id, new_pre);
        out.text(out.text() + content.data);
        break;

    case 'pyout':
        this.output("<pre class='sagecell_pyout'></pre>", block_id).text(content.data['text/plain']);
        break;
/*
    case 'display_data':
        var filepath=sagecell.$URL.root+'files/'+id+'/', html;

        if(msg.content.data['image/svg+xml']!==undefined) {
            this.output('<embed  class="sagecell_svgImage" type="image/svg+xml">'+msg.content.data['image/svg+xml']+'</embed>',output_block);
        }
        if(msg.content.data['text/html']!==undefined) {
            html = msg.content.data['text/html'].replace(/cell:\/\//gi, filepath);
            this.output('<div>'+html+'</div>',output_block);
        }
        if(msg.content.data['text/filename']!==undefined) {
            this.output('<img src="'+filepath+msg.content.data['text/filename']+'" />',output_block);
        }
        if(msg.content.data['image/png']!==undefined) {
            //console.log('making png img with data in src');
            this.output('<img src="'+msg.content.data['image/png']+'" />',output_block);
        }
        if(msg.content.data['application/x-jmol']!==undefined) {
            //console.log('making jmol applet');
            jmolSetDocument(false);
            this.output(jmolApplet(500, 'set defaultdirectory "'+filepath+msg.content.data['application/x-jmol']+'";\n script SCRIPT;\n'),output_block);
        }
        
        break;
*/
    case 'pyerr':
        this.output("<pre></pre>", block_id)
            .html(IPython.utils.fixConsole(content.traceback.join("\n")));
        break;
    case 'extension':
        switch(content.msg_type) { /*
        case "files":
            output_block = "files_"+this.session_id;
            this.replace_output[output_block] = true;
            var files = user_msg.content.files;
            var html="<div>\n";
            for(var j = 0, j_max = files.length; j < j_max; j++) {
                if (this.files[files[j]] !== undefined) {
                    this.files[files[j]]++;
                } else {
                    this.files[files[j]] = 0;
                }
            }
            for (j in this.files) {
                //TODO: escape filenames and id
                html+='<a href="'+sagecell.$URL.root+'files/'+id+'/'+j+'" target="_blank">'+j+'</a> [Updated '+this.files[j]+' time(s)]<br>\n';
            }
            html+="</div>";
            this.output(html,output_block).effect("pulsate", {times:1}, 500);
            break;
        case "session_end":
            $(document.getElementById("output_" + this.session_id)).removeClass("sagecell_active");
            // Unbinds interact change handlers
            for (var i in this.eventHandlers) {
                for (var j in this.eventHandlers[i]) {
                    $(i).die(this.eventHandlers[i][j]);
                }
            }
            this.clearQuery();
            this.sessionContinue = false;
            break; */
        case "interact_prepare":
            new sagecell.InteractCell(this, content.content, block_id);
            break;
        }
        break;
    }

    this.appendMsg(content, "Accepted: ");
    // need to mathjax the entire output, since output_block could just be part of the output
    // TODO: this is really too much, as it typesets *all* of the session outputs
    // TODO: the session object really should have it's own output DOM element
    var output = this.outputDiv.find(".sagecell_output").get(0);
    MathJax.Hub.Queue(["Typeset",MathJax.Hub, output]);
    MathJax.Hub.Queue([function () {$(output).find(".math").removeClass('math');}]);
};

sagecell.Session.prototype.handle_execute_reply = function (content) {
    if (--this.open_count === 0) {
        this.spinner.style.display = "none";
    }
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
        var code = "sys._update_interact(" + JSON.stringify(that.interact_id) + ", {";
        var kwargs = []
        for (var name in that.controls) {
            if (that.controls.hasOwnProperty(name)) {
                kwargs.push(JSON.stringify(name) + ":" + that.controls[name].py_value(ui));
            }
        }
        code += kwargs.join(",") + "})";
        that.session.spinner.style.display = "";
        that.session.open_count++;
        that.session.replace_output[that.interact_id] = true;
        that.session.execute(code);
    };
    for (var name in this.controls) {
        if (this.controls.hasOwnProperty(name)) {
            var events = this.controls[name].changeHandlers();
            for (var e in events) {
                if (events.hasOwnProperty(e)) {
                    $(events[e]).on(e, handler);
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
    for (var loc in this.layout) {
        if (this.layout.hasOwnProperty(loc)) {
            var table2 = ce("table", {"class": "sagecell_interactControls"});
            for (var i = 0; i < this.layout[loc].length; i++) {
                var tr = ce("tr");
                var id = this.interact_id + "_" + cells[loc][i];
                var right = ce("td", {}, [
                    this.controls[this.layout[loc][i]].rendered(id)
                ]);
                if (this.controls[this.layout[loc][i]].control.label) {
                    var left = ce("td", {}, [
                        ce("label", {"for": id, "title": this.layout[loc][i]}, [
                            document.createTextNode(this.controls[this.layout[loc][i]].control.label)
                        ])
                    ]);
                    tr.appendChild(left);
                } else {
                    right.setAttribute("colspan", "2");
                }
                tr.appendChild(right);
                table2.appendChild(tr);
            }
            cells[loc].appendChild(table2);
        }
    }
    this.session.output(table, parent_block);
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
    $(this.button).button();
    return this.button;
}

sagecell.InteractData.Button.prototype.changeHandlers = function () {
    return {"click": this.button};
};

sagecell.InteractData.Button.prototype.py_value = function () {
    return "None";
}

sagecell.InteractData.ButtonBar = sagecell.InteractData.InteractControl();

sagecell.InteractData.ButtonBar.prototype.rendered = function (control_id) {
    var ce = sagecell.util.createElement;
    var name = "interact_" + control_id;
    var table = ce("table");
    var i = -1;
    this.radios = $();
    var that = this;
    for (var row = 0; row < this.control.nrows; row++) {
        var tr = ce("tr");
        for (var col = 0; col < this.control.ncols; col++) {
            var id = name + "_" + ++i;
            var radio = ce("input", {"type": "radio", "name": name, "id": id});
            var label = ce("label", {"for": id}, [
                document.createTextNode(this.control.value_labels[i])
            ]);
            $(radio).data("index", i);
            this.radios = this.radios.add(radio);
            tr.appendChild(ce("td", {}, [radio, label]));
        }
        table.appendChild(tr);
    }
    this.radios.button();
    this.radios.off("change");
    return table;
}

sagecell.InteractData.ButtonBar.prototype.changeHandlers = function () {
    return {"change": this.radios};
}

sagecell.InteractData.ButtonBar.prototype.py_value = function () {
    return this.radios.filter(":checked").data("index");
}

sagecell.InteractData.Checkbox = sagecell.InteractData.InteractControl();

sagecell.InteractData.Checkbox.prototype.rendered = function () {
    this.input = sagecell.util.createElement("input", {"type": "checkbox"});
    this.input.checked = this.control.default;
    return this.input;
}

sagecell.InteractData.Checkbox.prototype.changeHandlers = function () {
    return {"change": this.input};
}

sagecell.InteractData.Checkbox.prototype.py_value = function () {
    return this.input.checked ? "True" : "False";
}

sagecell.InteractData.ColorSelector = sagecell.InteractData.InteractControl();

sagecell.InteractData.ColorSelector.prototype.rendered = function () {
    var selector = sagecell.util.createElement("span", {"class": "sagecell_colorSelector"});
    var text = document.createTextNode(this.control.default);
    this.span = sagecell.util.createElement("span", {}, [selector]);
    if (!this.control.hide_input) {
        selector.style.marginRight = "10px";
        this.span.appendChild(text);
    }
    selector.style.backgroundColor = this.control.default;
    var that = this;
    $(selector).ColorPicker({
        "color": this.control.default,
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

sagecell.InteractData.HtmlBox = sagecell.InteractData.InteractControl();

sagecell.InteractData.HtmlBox.prototype.rendered = function () {
    // TODO: replace "cell:" URIs in HTML with URLs for uploaded files
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

sagecell.InteractData.InputBox = sagecell.InteractData.InteractControl();

sagecell.InteractData.InputBox.prototype.rendered = function () {
    if (this.control.subtype === "textarea") {
        this.textbox = sagecell.util.createElement("textarea",
            {"rows": this.control.height, "cols": this.control.width});
    } else if (this.control.subtype === "input") {
        this.textbox = sagecell.util.createElement("input",
            {"size": this.control.width});
    }
    this.textbox.value = this.control.default;
    return this.textbox;
}

sagecell.InteractData.InputBox.prototype.changeHandlers = function() {
    return {"change": this.textbox};
}

sagecell.InteractData.InputBox.prototype.py_value = function () {
    return "u" + JSON.stringify(this.textbox.value);
}

sagecell.InteractData.InputGrid = sagecell.InteractData.InteractControl();

sagecell.InteractData.InputGrid.prototype.rendered = function () {
    this.textboxes = $();
    var ce = sagecell.util.createElement;
    var table = ce("table");
    for (var row = 0; row < this.control.nrows; row++) {
        var tr = ce("tr");
        for (var col = 0; col < this.control.ncols; col++) {
            var textbox = ce("input", {"value": this.control.default[row][col],
                                       "size": this.control.width});
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

sagecell.InteractData.MultiSlider = sagecell.InteractData.InteractControl();

sagecell.InteractData.MultiSlider.prototype.rendered = function () {
    var ce = sagecell.util.createElement;
    var div = ce("div");
    this.sliders = $();
    this.value_boxes = $();
    this.values = this.control.default.slice();
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
            var textbox = ce("input", {"class": "sagecell_interactValueBox"});
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
                          "value": this.control.default[i],
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
        select.selectedIndex = this.control.default;
        $(select).change(function (event) {
            that.value = event.target.selectedIndex;
            $(event.target).trigger("changedone");
        });
        this.changing = select;
        return select;
    } else if (this.control.subtype === "radio" || this.control.subtype === "button") {
        this.changing = $();
        var table = ce("table");
        var i = -1;
        for (var row = 0; row < this.control.nrows; row++) {
            var tr = ce("tr");
            for (var col = 0; col < this.control.ncols; col++) {
                var id = control_id + "_" + ++i;
                var option = ce("input", {"type": "radio", "name": control_id, "id": id});
                if (i === this.control.default) {
                    option.checked = true;
                }
                var label = ce("label", {"for": id}, [
                    document.createTextNode(this.control.value_labels[i])
                ]);
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

sagecell.InteractData.Slider = sagecell.InteractData.InteractControl();

sagecell.InteractData.Slider.prototype.rendered = function () {
    var ce = sagecell.util.createElement;
    this.continuous = this.control.subtype === "continuous" ||
                      this.control.subtype === "continuous_range";
    this.range = this.control.subtype === "discrete_range" ||
                 this.control.subtype === "continuous_range";
    var container = ce("span");
    container.style.whitespace = "nowrap";
    this.slider = ce("span", {"class": "sagecell_sliderControl"});
    container.appendChild(this.slider);
    var that = this;
    if (this.continuous) {
        if (this.range) {
            this.values = this.control.default.slice();
            $(this.slider).slider({"min": this.control.range[0],
                                   "max": this.control.range[1],
                                   "step": this.control.step,
                                   "range": true,
                                   "values": this.values,});
            var min_text = ce("input", {"class": "sagecell_interactValueBox",
                                        "value": this.values[0].toString()});
            var max_text = ce("input", {"class": "sagecell_interactValueBox",
                                        "value": this.values[1].toString()});
            min_text.size = min_text.value.length + 1;
            max_text.size = max_text.value.length + 1;
            min_text.style.marginTop = max_text.style.marginTop = "3px";
            $(this.slider).on("slide", function (event, ui) {
                that.values = ui.values.slice()
                min_text.value = that.values[0].toString();
                max_text.value = that.values[1].toString();
                min_text.size = min_text.value.length + 1;
                max_text.size = max_text.value.length + 1;
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
            var span = ce("span", {}, [
                document.createTextNode("("),
                min_text,
                document.createTextNode(", "),
                max_text,
                document.createTextNode(")")
            ]);
            span.style.fontFamily = "monospace";
            container.appendChild(span);
        } else {
            this.value = this.control.default;
            $(this.slider).slider({"min": this.control.range[0],
                                   "max": this.control.range[1],
                                   "step": this.control.step,
                                   "value": this.value});
            var textbox = ce("input", {"class": "sagecell_interactValueBox",
                                       "value": this.value.toString()});
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
        }
    } else if (this.range) {
        this.values = this.control.default.slice();
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
        this.value = this.control.default;
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

/* This function is copied from IPython's kernel.js
 * (https://github.com/ipython/ipython/blob/master/IPython/frontend/html/notebook/static/js/kernel.js)
 * and modified to allow messages of type 'extension'.
 */
IPython.Kernel.prototype._handle_iopub_reply = function (e) {
    var reply = $.parseJSON(e.data);
    var content = reply.content;
    var msg_type = reply.header.msg_type;
    var callbacks = this.get_callbacks_for_msg(reply.parent_header.msg_id);
    if (msg_type !== 'status' && callbacks === undefined) {
        // Message not from one of this notebook's cells and there are no
        // callbacks to handle it.
        return;
    }
    var output_types = ['stream','display_data','pyout','pyerr','extension'];
    if (output_types.indexOf(msg_type) >= 0) {
        var cb = callbacks['output'];
        if (cb !== undefined) {
            cb(msg_type, content);
        }
    } else if (msg_type === 'status') {
        if (content.execution_state === 'busy') {
            $([IPython.events]).trigger('status_busy.Kernel');
        } else if (content.execution_state === 'idle') {
            $([IPython.events]).trigger('status_idle.Kernel');
        } else if (content.execution_state === 'dead') {
            this.stop_channels();
            $([IPython.events]).trigger('status_dead.Kernel');
        };
    } else if (msg_type === 'clear_output') {
        var cb = callbacks['clear_output'];
        if (cb !== undefined) {
            cb(content);
        }
    };
};




// Initialize jmol
// TODO: move to a better place
jmolInitialize(sagecell.$URL.root + '/static/jmol');
jmolSetCallback("menuFile", sagecell.$URL.root + "/static/jmol/appletweb/SageMenu.mnu");

})(sagecell.jQuery);
