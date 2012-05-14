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


jQuery.noConflict();

(function($) {


/**************************************************************
* 
* Session Class
* 
**************************************************************/

sagecell.Session = (sagecell.functions.makeClass());
sagecell.Session.prototype.init = function (outputDiv, output, session_id, sage_mode) {
    this.outputDiv = outputDiv;
    this.session_id = session_id;
    this.sage_mode = sage_mode;
    this.sequence = 0;
    this.polling_times = {'active': 250, 'inactive': 2000};
    this.poll_interval = this.polling_times.active;
    this.last_update = (new Date).getTime();
    this.lastMessage = {};
    this.sessionContinue = true;
    this.outputDiv.find(output).prepend('<div id="session_'+this.session_id+'" class="sagecell_sessionContainer"><div id="session_'+this.session_id+'_title" class="sagecell_sessionTitle">Session '+this.session_id+'</div><div id="output_'+this.session_id+'" class="sagecell_sessionOutput sagecell_active"></div><div id="output_files_'+this.session_id+'" class="sagecell_sessionFiles"></div></div>');
    var output = $(document.getElementById("output_" + this.session_id))
    output.after(sagecell.functions.createElement("div", {"class": "sagecell_poweredBy"}, [
            document.createTextNode("Powered by "),
            sagecell.functions.createElement("a", {"href": "http://www.sagemath.org"}, [
                sagecell.functions.createElement("img",
                    {"src": sagecell.$URL.powered_by_img, "alt": "Sage"})])]));
    this.spinner = sagecell.functions.createElement("img",
            {"src": sagecell.$URL.spinner_img, "alt": "Loading",
             "class": "sagecell_spinner"});
    output.append(this.spinner);
    this.session_title=$('#session_'+this.session_id+'_title');
    this.replace_output={};
    this.lock_output=false;
    this.files = {};
    this.eventHandlers = {};
    this.interacts = {};
    this.setQuery();
}

// Manages querying the webserver for messages
sagecell.Session.prototype.setQuery = function() {
    this.clearQuery();
    var now =  (new Date).getTime();
    var delta = now-this.last_update;
    if (delta < this.poll_interval) {
        this.queryID = setTimeout($.proxy(this, 'get_output'), this.poll_interval-delta);
    } else {
        this.queryID = setTimeout($.proxy(this, 'get_output'), 0);
    }
}

sagecell.Session.prototype.clearQuery = function() {
    clearTimeout(this.queryID);
}

sagecell.Session.prototype.updateQuery = function(new_interval) {
    this.poll_interval = new_interval;
    this.clearQuery();
    this.setQuery();
}

sagecell.Session.prototype.sendMsg = function() {
    var code = arguments[0];
    var msg, msg_id, interact_id;

    if (!this.sessionContinue) {
        return false;
    }

    if (arguments[1] === undefined){
        msg_id = sagecell.functions.uuid4();
    } else {
        msg_id = arguments[1];
    }

    if (arguments[2] !== undefined) {
        interact_id = arguments[2];
    }

    msg = {"parent_header": {},
           "header": {"msg_id": msg_id,
                      //"username": "",
                      "session": this.session_id},
           "msg_type": "execute_request",
           "content": {"code": code,
                       //"silent": false,
                       "sage_mode": this.sage_mode,
                       //"user_variables": [],
                       //"user_expressions": {}
                      }
          };

    this.lastMessage[interact_id] = msg_id;

    this.appendMsg(msg, "*******SEND: ");
    /* We need to make a proxy object; see
       http://api.jquery.com/bind/#comment-74776862 or
       http://bitstructures.com/2007/11/javascript-method-callbacks
       for why. If we don't do the proxy, then "this" in the
       send_computation_success function will *not* refer to the
       session object. */
    sagecell.sendRequest("POST", sagecell.$URL.evaluate,
            {"message": JSON.stringify(msg)},
            $.proxy(this.send_computation_success, this));
    // Pretend like we just got an update, so that we don't request a new update
    // immediately (since it will probably take a little bit of time for the server
    // to get the request and respond)
    this.last_update=(new Date).getTime();
    this.updateQuery(this.polling_times.active);
}

sagecell.Session.prototype.appendMsg = function(msg, text) {
    // Append the message to the div of messages
    // Use $.text() so that strings are automatically escaped
    this.outputDiv.find(".sagecell_messages").append(document.createElement('div')).children().last().text(text+JSON.stringify(msg));
}

sagecell.Session.prototype.output_id = function(block_id) {
    return "output_"+(block_id || this.session_id);
}

sagecell.Session.prototype.output = function(html, block_id, create) {
    // create===false means just pass back the last child of the output_block
    // if we aren't replacing the output block
    if (typeof(create)==="undefined") {
        create=true;
    }
    var output_block=$("#"+this.output_id(block_id));
    if (typeof(block_id) !=="undefined" && block_id !== null &&
        this.replace_output[block_id]) {
        output_block.empty();
        this.replace_output[block_id]=false;
        create=true;
    }
    if (create) {
        out = output_block.append(html).children().last();
    } else {
        out = output_block.children().last();
    }
    return out;
}

sagecell.Session.prototype.write = function(html) {
    this.output(html);
}

sagecell.Session.prototype.send_computation_success = function(data) {
    if (JSON.parse(data).computation_id !== this.session_id) {
        alert("Session id returned and session id sent don't match up");
    }
    this.setQuery();
}

sagecell.Session.prototype.get_output = function() {
    this.last_update = (new Date).getTime();
    sagecell.sendRequest("GET", sagecell.$URL.output_poll,
            {"computation_id": this.session_id, "sequence": this.sequence},
            $.proxy(this, "get_output_success"));
}

sagecell.Session.prototype.get_output_success = function(data) {
    var id=this.session_id;
    data = JSON.parse(data);
    if(typeof(data) !== "undefined" && data.content !== undefined) {
        var content = data.content;
        for (var i = 0, i_max = content.length; i < i_max; i++) {
            var msg = content[i];
            var parent_id = msg.parent_header.msg_id;
            var output_block = msg.output_block;

            if (msg.sequence !== this.sequence) {
                // If the sequence number is off (typically because of delays
                // in receiving messages, log that it was received but don't
                // output it. Instead, wait to output until the server catches
                // up; this should prevent multiple outputs from appearing.
                this.appendMsg(msg, "Rejected Sequence: ");
                console.warn('Sequence is out of order; client thinks it should be '+this.sequence+', but server claims it is '+msg.sequence);
                continue;
            }
            this.sequence += 1;
            if (typeof(parent_id) !== "undefined" && !$.isEmptyObject(this.lastMessage) && parent_id !== this.lastMessage[output_block] 
                && output_block !== null && output_block !== undefined) {
                // If another message has been sent to the server since the parent of this one, don't format it for output but log that it was received.
                // This solves a problem associated with updating complex interacts quicker than the server can reply where output would be printed multiple times.
                this.appendMsg(msg, "Rejected: ");
                continue;
            }

            // Handle each stream type.  This should probably be separated out into different functions.
            switch(msg.msg_type) {
            case 'stream':
                var new_pre = !$('#'+this.output_id(output_block)).children().last().hasClass("sagecell_"+msg.content.name);
                var out=this.output("<pre class='sagecell_"+msg.content.name+"'></pre>",output_block,new_pre);
                out.text(out.text()+msg.content.data);
                break;

            case 'pyout':
                this.output("<pre class='sagecell_pyout'></pre>",output_block).text(msg.content.data['text/plain']);
                break;

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

            case 'pyerr':
                this.output("<pre></pre>",output_block)
                    .html(sagecell.functions.colorizeTB(msg.content.traceback
                                                        .replace(/&/g,"&amp;")
                                                        .replace(/</g,"&lt;")));
                break;
            case 'execute_reply':
                this.spinner.style.display = "none";
                if(msg.content.status==="error") {
                    // copied from the pyerr case
                    this.output("<pre></pre>",output_block)
                        .html(sagecell.functions.colorizeTB(msg.content.traceback
                                                            .replace(/&/g,"&amp;")
                                                            .replace(/</g,"&lt;")));
                }
                this.updateQuery(this.polling_times.inactive);
                break;

            case 'extension':
                var user_msg=msg.content;
                switch(user_msg.msg_type) {
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
                    break;
                case "interact_prepare":
                    var interact_id = user_msg.content.interact_id;
                    var div_id = "interact_" + interact_id;
                    this.output("<table class='sagecell_interactContainer' id='"+div_id+"'>"+
                                "<tr><td class='sagecell_interactContainer_top_left'></td><td class='sagecell_interactContainer_top_center'></td><td class='sagecell_interactContainer_top_right'></td></tr>"+
                                "<tr><td class='sagecell_interactContainer_left'></td><td class='sagecell_interactOutput'><div id='output_"+interact_id+"'></div></td><td class='sagecell_interactContainer_right'></tr>"+
                                "<tr><td class='sagecell_interactContainer_bottom_left'></td><td class='sagecell_interactContainer_bottom_center'></td><td class='sagecell_interactContainer_bottom_right'></td></tr></table>", output_block);

                    this.interacts[interact_id] = 1;
                    new sagecell.InteractCell("#" + div_id, {
                        'interact_id': interact_id,
                        'layout': user_msg.content.layout,
                        'controls': user_msg.content.controls,
                        'update': user_msg.content.update,
                        'session': this});
                    break;
                }
                break;
            }
            
            this.appendMsg(msg, "Accepted: ");
        }
        // need to mathjax the entire output, since output_block could just be part of the output
        // TODO: this is really too much, as it typesets *all* of the session outputs
        // TODO: the session object really should have it's own output DOM element
        var output = this.outputDiv.find(".sagecell_output").get(0);
        MathJax.Hub.Queue(["Typeset",MathJax.Hub, output]);
        MathJax.Hub.Queue([function () {$(output).find(".math").removeClass('math');}]);
    }
    if (this.sessionContinue) {
        this.setQuery();
    }
}

/**************************************************************
* 
* InteractCell Class
* 
**************************************************************/

sagecell.InteractCell = (sagecell.functions.makeClass());
sagecell.InteractCell.prototype.init = function (selector, data) {
    this.element = $(selector);
    this.interact_id = data.interact_id
    this.function_code = data.function_code;
    this.controls = {};
    this.update = data.update;
    this.layout = data.layout;
    this.session = data.session;
    this.msg_id = data.msg_id;

    var controls = data.controls;
    var args = {
        "control": "",
        "interact_id": this.interact_id,
        "name": "",
        "session_id": this.session.session_id
    };

    for (i in controls) {
        args["control"] = controls[i];
        args["name"] = i;
        var control_type = controls[i]["control_type"];

        if (control_type === "button") {
            this.controls[i] = new sagecell.InteractData.Button(args);
        } else if (control_type === "button_bar") {
            this.controls[i] = new sagecell.InteractData.ButtonBar(args);
        } else if (control_type === "checkbox") {
            this.controls[i] = new sagecell.InteractData.Checkbox(args);
        } else if (control_type === "color_selector") {
            this.controls[i] = new sagecell.InteractData.ColorSelector(args);
        } else if (control_type === "html_box") {
            this.controls[i] = new sagecell.InteractData.HtmlBox(args);
        } else if (control_type === "input_box") {
            this.controls[i] = new sagecell.InteractData.InputBox(args);
        } else if (control_type === "input_grid") {
            this.controls[i] = new sagecell.InteractData.InputGrid(args);
        } else if (control_type === "multi_slider") {
            this.controls[i] = new sagecell.InteractData.MultiSlider(args);
        } else if (control_type === "selector") {
            this.controls[i] = new sagecell.InteractData.Selector(args);
        } else if (control_type === "slider") {
            this.controls[i] = new sagecell.InteractData.Slider(args);
        }
    }

    this.renderCanvas();
    this.bindChange(this);
}

sagecell.InteractCell.prototype.bindChange = function(interact) {
    var id = ".urn_uuid_" + this.interact_id;
    var elements = this.controls;
    var events = {};

    for (var i in elements) {
        var handlers = this.controls[i].changeHandlers();
        for (var j = 0, j_max = handlers.length; j < j_max; j ++) {
            if (events[handlers[j]] === undefined) {
                events[handlers[j]] = [i];
            } else {
                events[handlers[j]].push(i);
            }
        }
    }

    this.session.eventHandlers[id] = {};
    for (var i in events) {
        this.session.eventHandlers[id][i] = events[i];
        $(id).live(i, function(e){
            if (!interact.session.sessionContinue) {
                // If the session ended, don't try to send more messages
                return false;
            }
            var parentSpan = $(e.target).parentsUntil("span[class^='sagecell_var_']");
            if (parentSpan.length === 0) {
                parentSpan = $(e.target).parent();
            } else {
                parentSpan = parentSpan.parent();
            }
            var changedControl = parentSpan.attr("class").replace("sagecell_var_",""); // Get changed variable name

            if (interact.update[changedControl] !== undefined) {
                var changes = interact.getChanges(interact.update, changedControl, interact.interact_id);
                var code = "_update_interact('"+interact.interact_id+"',control_vals=dict(";

                for (j in changes) {
                    if (interact.controls[j]["control"]["raw"]) {
                        code += j + "=" +  changes[j] + ",";
                    } else {
                        code += j + "='" + changes[j].replace(/'/g, "\\'") + "',";
                    }
                }
                code += "))";
                interact.session.spinner.style.display = "";
                interact.session.sendMsg(code, interact.msg_id, interact.interact_id);
                interact.session.replace_output[interact.interact_id]=true;
            } else {
                parentSpan.parent().addClass("sagecell_dirtyControl");
            }
            return false;
        });
    }
}

sagecell.InteractCell.prototype.getChanges = function(interact_update, changed_control, interact_id) {
    var params = {};
    var controls = interact_update[changed_control];
    var interact_location = $("#interact_"+interact_id);

    for (var i = 0, i_max = controls.length; i < i_max; i++) {
        params[controls[i]] = this.controls[controls[i]].changes();
        interact_location
            .find("span[class^='sagecell_var_"+controls[i]+"']")
            .parent()
            .removeClass("sagecell_dirtyControl");
    }

    return params;
}

sagecell.InteractCell.prototype.renderCanvas = (function() {
    /*

      The template is:
      <td>{{label}}</td><td>{{control html code}}</td>

      if the control has a label. If not, then the template is:

      <td colspan='2'>{{control html code}}</td>

     */
    var addControl=function(labeltext, name, controlHtml, id) {
        var html_code = "";

        if (labeltext) {
            html_code += "<td><label ";
            if (id) {
                html_code += "for='"+id+"' ";
            }
            html_code += " title='"+name+"'>"+labeltext+"</label></td><td>";
        } else {
            html_code += "<td colspan='2'>";
        }

        html_code += controlHtml;
        html_code += "</td>";
        return html_code;
    }
    var select_labels={};
    return function() {
        var container = $("table#interact_"+this.interact_id);
        var id = "urn_uuid_" + this.interact_id;

        for (var i in this.layout) {
            var layout_location = this.layout[i]
            var section = container.find("td.sagecell_interactContainer_"+i);
            section.html("<table class='sagecell_interactControls'></table>");

            var control_location = section.find(".sagecell_interactControls");
            
            for (var j = 0, j_max = layout_location.length; j < j_max; j++) {

                var row = layout_location[j];
                var row_html = "<tr>";
                var name = row;

                var control_html = function(info,name) {
                    var label = info.controls[name]["control"].label;
                    if (label === null) {
                        label = name;
                    }
                    var control_id = id + "_" + name;
                    return addControl(label, name, info.controls[name].html(), control_id);
                };

                if (typeof(row)==="object") {
                    for (var c = 0, c_max = row.length; c < c_max; c++) {
                        name = row[c];
                        row_html += control_html(this,name);
                    }
                } else {
                    row_html += control_html(this,name);
                }

        
                row_html += "</tr>";
                control_location.append(row_html);
                this.controls[name].finishRender(control_location);
            }
        }
    }
})();


sagecell.InteractData = {};

sagecell.InteractData.Button = sagecell.functions.makeClass();
sagecell.InteractData.Button.prototype.init = function(args) {
    this.control = args["control"];
    this.interact_id = args["interact_id"];
    this.location = "*";
    this.name = args["name"];
    this.session_id = args["session_id"];
    
    this.control_class = "urn_uuid_"+this.interact_id;
    this.control_id = this.control_class + "_" + this.name;
}

sagecell.InteractData.Button.prototype.changeHandlers = function() {
    return ["change"];
};

sagecell.InteractData.Button.prototype.changes = function() {
    var control_out = $(this.location).find("#"+this.control_id+"_value")
    var value = control_out.val();
    control_out.val("false");
    return value;
}

sagecell.InteractData.Button.prototype.html = function() {
    return "<span class='sagecell_var_"+this.name+"'>"+
        "<button class='sagecell_button ui-widget ui-state-default ui-corner-all' id='"+this.control_id+"_button'>"+
        "<span>"+this.control["text"]+"</span></button><input type='hidden' class='"+this.control_class+"' id='"+this.control_id+"_value' value='false'></span>";
}

sagecell.InteractData.Button.prototype.finishRender = function(location) {
    this.location = location;
    $(this.location)
        .delegate("#"+this.control_id+"_button", {
            "mouseenter": function(e) {
                $(this).addClass("ui-state-hover");
            },
            "mouseleave": function(e) {
                $(this).removeClass("ui-state-hover");
            },
            "mousedown": function(e) {
                $(this).addClass("ui-state-active");
            },
            "mouseup": (function(control_id) {
                return function(e) {
                    $(this).removeClass("ui-state-active");
                    $(this).parent().find("#"+control_id+"_value").val("true").change();
                }
            }(control_id = this.control_id)),
            "click": function(e) {
                e.preventDefault();
            }
        })
        .css("width", this.control["width"]);
}


sagecell.InteractData.ButtonBar = sagecell.functions.makeClass();
sagecell.InteractData.ButtonBar.prototype.init = function(args) {
    this.control = args["control"];
    this.interact_id = args["interact_id"];
    this.location = "*";
    this.name = args["name"];
    this.session_id = args["session_id"];
    
    this.control_class = "urn_uuid_"+this.interact_id;
    this.control_id = this.control_class + "_" + this.name;
}

sagecell.InteractData.ButtonBar.prototype.changeHandlers = function() {
    return ["change"];
}

sagecell.InteractData.ButtonBar.prototype.changes = function() {
    var control_out = $(this.location).find("#"+this.control_id+"_value")
    var value = control_out.val();
    control_out.val("false");
    return value;
}

sagecell.InteractData.ButtonBar.prototype.html = function() {
    var nrows = this.control["nrows"],
    ncols = this.control["ncols"],
    value_labels = this.control["value_labels"],
    html_code = "<span class='sagecell_var_"+this.name+"'>",
    inner_table = "<table><tbody>";

    for (var r = 0, i = 0; r < nrows; r ++) {
        inner_table += "<tr>";
        for (var c = 0; c < ncols; c ++, i++) {
            inner_table += "<td><button class='"+this.control_id+
                " sagecell_button ui-widget ui-state-default ui-corner-all'"+
                " id='"+this.control_id+"_"+i+"'><span>"+value_labels[i]+
                "</span></button></td>";
        }
        inner_table += "</tr>";
    }
    
    inner_table += "</tbody></table>";

    html_code += inner_table + "<input type='hidden' id='"+this.control_id+
        "_value' class='"+this.control_class+"' value='None'></span>";

    return html_code;
}

sagecell.InteractData.ButtonBar.prototype.finishRender = function(location) {
    this.location = location;
    $(this.location).find("."+this.control_id)
        .css("width", this.control["width"]);
    for (var i = 0, i_max = this.control["values"]; i < i_max; i ++) {
        $(this.location)
            .delegate("#"+this.control_id+"_"+i, {
                "mouseenter": function(e) {
                    $(this).addClass("ui-state-hover");
                },
                "mouseleave": function(e) {
                    $(this).removeClass("ui-state-hover");
                },
                "mousedown": function(e) {
                    $(this).addClass("ui-state-active");
                },
                "mouseup": (function(location, control_id, i) {
                    return function(e) {
                        $(this).removeClass("ui-state-active");
                        $(location).find("#"+control_id+"_value").val(i)
                            .change();
                    }
                }(location = this.location, control_id = this.control_id, i)),
                "click": function(e) {
                    e.preventDefault();
                }
            });
    }
}


sagecell.InteractData.Checkbox = sagecell.functions.makeClass();
sagecell.InteractData.Checkbox.prototype.init = function(args) {
    this.control = args["control"];
    this.interact_id = args["interact_id"];
    this.location = "*";
    this.name = args["name"];
    this.session_id = args["session_id"];
    
    this.control_class = "urn_uuid_"+this.interact_id;
    this.control_id = this.control_class + "_" + this.name;
}

sagecell.InteractData.Checkbox.prototype.changeHandlers = function() {
    return ["change"];
}

sagecell.InteractData.Checkbox.prototype.changes = function() {
    var value = $(this.location).find("#"+this.control_id).prop("checked");
    if (value === true) {
        return "True";
    } else {
        return "False";
    }
}

sagecell.InteractData.Checkbox.prototype.html = function() {
    var html="<span class='sagecell_var_"+this.name+"'>"+
        "<input type='checkbox' class='"+this.control_class+"' id='"+
        this.control_id+"'"
    if(this.control["default"]) {
        html += " checked ";
    }
    html +="></span>";
    return html
}

sagecell.InteractData.Checkbox.prototype.finishRender = function(location) {
    this.location = location;
}


sagecell.InteractData.ColorSelector = sagecell.functions.makeClass();
sagecell.InteractData.ColorSelector.prototype.init = function(args) {
    this.control = args["control"];
    this.interact_id = args["interact_id"];
    this.location = "*";
    this.name = args["name"];
    this.session_id = args["session_id"];
    
    this.control_class = "urn_uuid_"+this.interact_id;
    this.control_id = this.control_class + "_" + this.name;
}

sagecell.InteractData.ColorSelector.prototype.changeHandlers = function() {
    return ["change"];
}

sagecell.InteractData.ColorSelector.prototype.changes = function() {
    return $(this.location).find("#"+this.control_id+"_value").val();
}

sagecell.InteractData.ColorSelector.prototype.html = function() {
    return "<span class='sagecell_var_"+this.name+"'><input type='text' class='sagecell_colorSelector' id='"+
        this.control_id+"'><input type='text' class='"+this.control_class+" sagecell_interactValueBox' id='"+
        this.control_id+"_value' style='border:none' value='"+this.control["default"]+"' readonly='readonly'><span>";
}

sagecell.InteractData.ColorSelector.prototype.finishRender = function(location) {
    this.location = location;
    var default_value = this.control["default"],
    control_out = $(this.location);

    if (this.control["hide_input"]) {
        control_out.find("#"+this.control_id+"_value").css("display", "none");
    }

    $(this.location).find("#"+this.control_id)
        .css("backgroundColor", default_value)
        .ColorPicker({
            color: default_value,
            onHide: (function(location, control_id) {
                return function(hsb, hex, rgb, el) {
                    $(location).find("#"+control_id+"_value").change();
                }
            }(location = this.location, control_id = this.control_id)),
            onSubmit: (function(location, control_id) {
                return function(hsb, hex, rgb, el) {
                    $(el).ColorPickerHide();
                    $(location).find("#"+control_id+"_value")
                        .val("#"+hex).change();
                }
            }(location = this.location, control_id = this.control_id)),
            onChange: (function(location, control_id) {
                return function(hsb, hex, rgb, el) {
                    $(location).find("#"+control_id).css({
                        "backgroundColor": "#"+hex,
                        "color": "#"+hex
                    });
                    $(location).find("#"+control_id+"_value").val("#"+hex);
                }
            }(location = this.location, control_id = this.control_id))
        });
}


sagecell.InteractData.HtmlBox = sagecell.functions.makeClass();
sagecell.InteractData.HtmlBox.prototype.init = function(args) {
    this.control = args["control"];
    this.interact_id = args["interact_id"];
    this.location = "*";
    this.name = args["name"];
    this.session_id = args["session_id"];
    
    this.control_class = "urn_uuid_"+this.interact_id;
    this.control_id = this.control_class + "_" + this.name;
}

sagecell.InteractData.HtmlBox.prototype.changeHandlers = function() {
    return [];
}

sagecell.InteractData.HtmlBox.prototype.changes = function() {
    return $(this.location).find("#"+this.control_id).html();
}

sagecell.InteractData.HtmlBox.prototype.html = function() {
    var html = this.control["value"].replace(/cell:\/\//gi, 
            sagecell.$URL.root + "files/" + this.session_id + '/');
    return "<span class='sagecell_var_"+this.name+"'><div class='"+this.control_class+"' id='"+this.control_id+"'>"+html+"</div></span>";
}

sagecell.InteractData.HtmlBox.prototype.finishRender = function(location) {
    this.location = location;
}


sagecell.InteractData.InputBox = sagecell.functions.makeClass();
sagecell.InteractData.InputBox.prototype.init = function(args) {
    this.control = args["control"];
    this.interact_id = args["interact_id"];
    this.location = "*";
    this.name = args["name"];
    this.session_id = args["session_id"];
    
    this.control_class = "urn_uuid_"+this.interact_id;
    this.control_id = this.control_class + "_" + this.name;
}

sagecell.InteractData.InputBox.prototype.changeHandlers = function() {
    return ["change"];
}

sagecell.InteractData.InputBox.prototype.changes = function() {
    var value = $(this.location).find("#"+this.control_id).val(),
    subtype = this.control["subtype"];

    if (subtype === "textarea") {
        return JSON.stringify(value);
    } else {
        return value;
    }
}

sagecell.InteractData.InputBox.prototype.html = function() {
    var subtype = this.control["subtype"];

    if (subtype === "textarea") {
        return "<span class='sagecell_var_"+this.name+"'><textarea class='"+
            this.control_class+"' id='"+this.control_id+"' rows='"+
            this.control["height"]+"' cols='"+this.control["width"]+
            "'>"+this.control["default"]+"</textarea></span>";
    } else if (subtype === "input") {
        return "<span class='sagecell_var_"+this.name+"'><input type='text' class='"+
            this.control_class+"' id='"+this.control_id+"' size="+
            this.control["width"]+" value='"+
            this.control["default"].replace(/'/g, "&#039;") + "'></span>";
    }
}

sagecell.InteractData.InputBox.prototype.finishRender = function(location) {
    this.location = location;
}


sagecell.InteractData.InputGrid = sagecell.functions.makeClass();
sagecell.InteractData.InputGrid.prototype.init = function(args) {
    this.control = args["control"];
    this.interact_id = args["interact_id"];
    this.location = "*";
    this.name = args["name"];
    this.session_id = args["session_id"];
    
    this.control_class = "urn_uuid_"+this.interact_id;
    this.control_id = this.control_class + "_" + this.name;
}

sagecell.InteractData.InputGrid.prototype.changeHandlers = function() {
    return ["change"];
}

sagecell.InteractData.InputGrid.prototype.changes = function() {
    var control_out = $(this.location);
    var row = [];
    var values = "[";

    for (var i = 0, i_max = this.control["nrows"]; i < i_max; i ++) {
        values += "[";
        row = [];
        for (var j =0, j_max = this.control["ncols"]; j < j_max; j ++) {
            row.push("'"+control_out.find("#"+this.control_id + "_" + i + "_" + j).val().replace(/'/g, "\\'")+"'");
        }
        values+=row.join(',');
        values += "],";
    }
    values += "]";

    return values;
}

sagecell.InteractData.InputGrid.prototype.html = function() {
    var default_values = this.control["default"],
    width = this.control["width"],
    html_code = "<span class='sagecell_var_"+this.name+"'><table><tbody>";

    for (var r = 0, r_max = this.control["nrows"]; r < r_max; r ++) {
        html_code += "<tr>";
        for (var c = 0, c_max = this.control["ncols"]; c < c_max; c ++) {
            html_code += "<td><input type='text' class='"+this.control_class+
                "' id='"+this.control_id+"_"+r+"_"+c+"' title='"+this.name+
                "["+r+"]["+c+"]' value='"+default_values[r][c]+"' size='"+
                width+"'></td>";
        }
        html_code += "</tr>"
    }

    html_code += "</tbody></table></span>";
    return html_code;
}

sagecell.InteractData.InputGrid.prototype.finishRender = function(location) {
    this.location = location;
}


sagecell.InteractData.MultiSlider = sagecell.functions.makeClass();
sagecell.InteractData.MultiSlider.prototype.init = function(args) {
    this.control = args["control"];
    this.interact_id = args["interact_id"];
    this.location = "*";
    this.name = args["name"];
    this.session_id = args["session_id"];
    
    this.control_class = "urn_uuid_"+this.interact_id;
    this.control_id = this.control_class + "_" + this.name;
}

sagecell.InteractData.MultiSlider.prototype.changeHandlers = function() {
    var handlers = ["slidestop"];
    if (this.control["subtype"] === "continuous") {
        handlers.push("change");
    }
    return handlers;
}

sagecell.InteractData.MultiSlider.prototype.changes = function() {
    var sliders = this.control["sliders"],
    control_out = $(this.location),
    input, slider_values = [];

    if (this.control["subtype"] === "continuous") {
        for (var i = 0; i < sliders; i ++) {
            input = control_out.find("#"+this.control_id + "_" + i + "_value")
                .val();
            control_out.find("#" + this.control_id + "_" + i)
                .slider("option", "value", input);
            slider_values.push(input);
        }
    } else {
        for (var i = 0; i < sliders; i ++) {
            slider_values.push(
                control_out.find("#" + this.control_id + "_" + i + "_index").val()
            );
        }
    }
    return "[" + String(slider_values) + "]";
}

sagecell.InteractData.MultiSlider.prototype.html = function() {
    var sliders = this.control["sliders"],
    html_code = "<span class='sagecell_var_"+this.name+"'><div class='" + this.control_class +
        " sagecell_multiSliderContainer'><span style='whitespace:nowrap'>";

    for (var i = 0; i < sliders; i ++) {
        html_code = html_code +
            "<span class='sagecell_multiSliderControl' id='"+this.control_id+"_"+i+"'></span>"+
            "<input type='text' class='"+this.control_id+" sagecell_interactValueBox' id='"+this.control_id+"_"+i+"_value' style='border:none'>"+
            "<input type='text' class='"+this.control_id+"' id='"+this.control_id+"_"+i+"_index' style='display:none'>";
    }
    html_code = html_code + "</span></div></span>";
    
    return html_code;
}

sagecell.InteractData.MultiSlider.prototype.finishRender = function(location) {
    this.location = location;

    var sliders = this.control["sliders"],
    slider_values = this.control["values"],
    slider_config = {},
    control_out = $(this.location),
    default_value;
    
    if (this.control["subtype"] === "continuous") {
        for (var i = 0; i < sliders; i ++) {
            var default_value = this.control["default"][i];

            control_out.find("#"+this.control_id+"_"+i+"_value")
                .val(default_value)
                .addClass(this.control_class)
                .attr("size", String(default_value).length)
                .css("display", (this.control["display_values"] ? "" : "none"));

            slider_config = {
                orientation: "vertical",
                value: this.control["default"][i],
                min: this.control["range"][i][0],
                max: this.control["range"][i][1],
                step: this.control["step"][i],
                slide: function(event,ui) {
                    var value_box = control_out.find("#"+ui.handle.offsetParent.id+"_value");
                    value_box.attr("size", String(ui.value).length)
                        .val(ui.value);
                }
            };

            control_out.find("#"+this.control_id+"_"+i).slider(slider_config);
        }
    } else {
        control_out.find("."+this.control_id+"_value").attr("readonly","readonly");
        for (var i = 0; i < sliders; i ++) {
            default_value = slider_values[i][this.control["default"][i]];
            control_out.find("#"+this.control_id+"_"+i+"_value")
                .val(default_value)
                .attr("size", String(default_value).length)
                .css("display", (this.control["display_values"] ? "" : "none"));
            control_out.find("#"+this.control_id+"_"+i+"_index").val(this.control["default"][i]);

            slider_config = {
                orientation: "vertical",
                value: this.control["default"][i],
                min: this.control["range"][i][0],
                max: this.control["range"][i][1],
                step: this.control["step"][i],
                slide: (function(control_out, i) {
                    return function(event,ui) {
                        var value_box = control_out.find("#"+ui.handle.offsetParent.id+"_value");
                        var value = slider_values[i][ui.value];
                        value_box.attr("size", String(value).length)
                            .val(slider_values[i][ui.value]);
                        control_out.find("#"+ui.handle.offsetParent.id+"_index").val(ui.value);
                    }
                }(control_out, i))
            }

            control_out.find("#"+this.control_id+"_"+i).slider(slider_config);
        }
    }
}


sagecell.InteractData.Selector = sagecell.functions.makeClass();
sagecell.InteractData.Selector.prototype.init = function(args) {
    this.control = args["control"];
    this.interact_id = args["interact_id"];
    this.location = "*";
    this.name = args["name"];
    this.session_id = args["session_id"];
    
    this.control_class = "urn_uuid_"+this.interact_id;
    this.control_id = this.control_class + "_" + this.name;
}

sagecell.InteractData.Selector.prototype.changeHandlers = function() {
    return ["change"];
}

sagecell.InteractData.Selector.prototype.changes = function() {
    return String($(this.location).find("#"+this.control_id).val());
}

sagecell.InteractData.Selector.prototype.html = function() {
    var nrows = this.control["nrows"],
    ncols = this.control["ncols"],
    values = this.control["values"],
    value_labels = this.control["value_labels"],
    default_index = this.control["default"],
    subtype = this.control["subtype"],
    html_code = "<span class='sagecell_var_"+this.name+"'>",
    inner_table;

    if (subtype === "list") {
        html_code += "<select class='"+this.control_class+"' id='"+this.control_id+"'>";
        for (var i = 0; i < values; i ++) {
            html_code += "<option value='"+i+"'><div>"+value_labels[i]+"</div></option>";
        }
        html_code += "</select>";

    } else if (subtype === "radio") {
        inner_table = "<table><tbody>";

        for (var r = 0, i = 0; r < nrows; r ++) {
            inner_table += "<tr>";
            for (var c = 0; c < ncols; c ++, i ++) {
                inner_table += "<td><input class='"+this.control_id+"' id='"+this.control_id+"_"+i+"' type='radio' name='"+this.control_id+"' value="+i+">"+value_labels[i]+"</td>";
            }
            inner_table += "</tr>";
        }
        inner_table += "</tbody></table>";

        html_code += inner_table + "<input type='hidden' class='"+this.control_class+"' id='"+this.control_id+"' + value='"+default_index+"'>";

    } else if (subtype === "button") {
        inner_table = "<table><tbody>";

        for (var r = 0, i = 0; r < nrows; r ++) {
            inner_table += "<tr>";
            for (var c = 0; c < ncols; c ++, i ++) {
                inner_table += "<td><button class='"+this.control_id+" sagecell_button ui-widget ui-state-default ui-corner-all' id='"+this.control_id+"_"+i+"'><span><div>"+value_labels[i]+"</div></span></button></td>";
            }
            inner_table += "</tr>";
        }
        inner_table += "</tbody></table>";
        
        html_code += inner_table + "<input type='hidden' class='"+this.control_class+"' id='"+this.control_id+"' + value='"+default_index+"'></div>";

    }
    html_code += "</span>";
    return html_code;
}

sagecell.InteractData.Selector.prototype.finishRender = function(location) {
    this.location = location;

    var subtype = this.control["subtype"],
    control_out = $(this.location),
    default_id = this.control_id+"_"+this.control["default"];

    if (subtype === "list") {
        $(control_out.find("#"+this.control_id).children()[this.control["default"]])
            .attr("selected","selected");
    } else if (subtype === "radio") {
        control_out.find("#"+default_id).attr("checked","checked");
        control_out.delegate("."+this.control_id, "mousedown", (function(control_out, control_id){
            return function(e) {
                var etarget = $(e.target);
                if (! etarget.prop("checked")) {
                    control_out.find("#"+control_id).val(etarget.val()).change();
                }
            }
        }(control_out, control_id = this.control_id)));
    } else if (subtype === "button") {
        control_out.find("#"+default_id).addClass("ui-state-active");
        control_out.find("."+this.control_id).css("width",this.control["width"]);
        for (var i = 0, i_max = this.control["nrows"] * this.control["ncols"];
             i < i_max; i ++) {
            control_out.delegate("#"+this.control_id+"_"+i, {
                "mouseenter": function(e) {
                    $(this).addClass("ui-state-hover");
                },
                "mouseleave": function(e) {
                    $(this).removeClass("ui-state-hover");
                },
                "mousedown": function(e) {
                    control_out.find(".ui-state-active").removeClass("ui-state-active");
                    $(this).addClass("ui-state-active");
                },
                "mouseup": (function(control_out,i,control_id) {
                    return function(e) {
                        if (control_out.find("#"+control_id).val() !== ""+i) {
                            control_out.find("#"+control_id).val(i).change();
                        }
                    }
                }(control_out, i, control_id=this.control_id)),
                "click": function(e) {
                    e.preventDefault();
                }
            });
        }
    }
}


sagecell.InteractData.Slider = sagecell.functions.makeClass();
sagecell.InteractData.Slider.prototype.init = function(args) {
    this.control = args["control"];
    this.interact_id = args["interact_id"];
    this.location = "*";
    this.name = args["name"];
    this.session_id = args["session_id"];
    
    this.control_class = "urn_uuid_"+this.interact_id;
    this.control_id = this.control_class + "_" + this.name;
}

sagecell.InteractData.Slider.prototype.changeHandlers = function() {
    var handlers = ["slidestop"];
    if (this.control["subtype"] === "continuous" || this.control["subtype"] === "continuous_range") {
        handlers.push("change");
    }
    return handlers;
}

sagecell.InteractData.Slider.prototype.changes = function() {
    var subtype = this.control["subtype"],
    control_out = $(this.location),
    slider, max, min, val, input, box;

    if (subtype === "continuous") {
        slider = control_out.find("#"+this.control_id);
        box = control_out.find("#"+this.control_id+"_value");
        max = slider.slider("option","max");
        min = slider.slider("option","min");
        val = slider.slider("option","value");
        input = box.val();

        if (isNaN(input) || input === "") {
            input = val;
        } else if (input < min) {
            input = min;
        } else if (input > max) {
            input = max;
        }

        box.val(input);
        return String(input);
    } else if (subtype === "continuous_range") {
        input = String("["+control_out.find("#"+this.control_id+"_value").val()+"]");
        control_out.find("#"+this.control_id).slider("option","values",JSON.parse(input));
        return input;
    } else if (subtype === "discrete") {
        return String(control_out.find("#"+this.control_id+"_index").val());
    } else if (subtype === "discrete_range") {
        return String("["+control_out.find("#"+this.control_id+"_index").val()+"]");
    }
}

sagecell.InteractData.Slider.prototype.html = function() {
    return "<span class='sagecell_var_"+this.name+"' style='whitespace:nowrap'>"+
        "<span class='" + this.control_class + " sagecell_sliderControl' id='" + this.control_id + "'></span>"+
        "<input type='text' class='" + this.control_class + " sagecell_interactValueBox' id='" + this.control_id + "_value' style='border:none'>"+
        "<input type='text' class='" + this.control_class +"' id='" + this.control_id + "_index' style='display:none'></span>";
}

sagecell.InteractData.Slider.prototype.finishRender = function(location) {
    this.location = location;

    var slider_config = {
        min:this.control["range"][0],
        max:this.control["range"][1],
        step:this.control["step"]
    },
    default_value = this.control["default"],
    subtype = this.control["subtype"],
    control_out = $(this.location);

    if (!this.control["display_value"]) {
        control_out.find("#"+this.control_id+"_value").css("display","none");
    }
    
    if (subtype === "continuous") {
        control_out.find("#"+this.control_id+"_value")
            .val(default_value)
            .attr("size", String(default_value).length);
        slider_config["slide"] = function(event, ui) {
            var value_box = control_out.find("#"+ui.handle.offsetParent.id+"_value");
            value_box.attr("size", String(ui.value).length)
                .val(ui.value);
        }
        slider_config["value"] = default_value;
    } else if (subtype === "continuous_range") {
        control_out.find("#"+this.control_id+"_value")
            .val(default_value)
            .attr("size", String(default_value).length);
        slider_config["range"] = true;
        slider_config["slide"] = function(event, ui) {
            var value_box = control_out.find("#"+ui.handle.offsetParent.id+"_value");
            value_box.attr("size", String(ui.values).length)
                .val(ui.values);
        }
        slider_config["values"] = default_value;
    } else if (subtype === "discrete") {
        var values = this.control["values"];
        control_out.find("#"+this.control_id+"_value")
            .attr({"readonly": "readonly",
                   "size": String(values[default_value]).size})
            .val(values[default_value]);
        control_out.find("#"+this.control_id+"_index").val(default_value);
        slider_config["slide"] = function(event,ui) {
            var value_box = control_out.find("#"+ui.handle.offsetParent.id+"_value");
            value_box.attr("size", String(values[ui.value]).length)
                .val(values[ui.value]);
            control_out.find("#" + ui.handle.offsetParent.id + "_index").val(ui.value);
        }
        slider_config["value"] = default_value;
    } else if (subtype === "discrete_range") {
        var values = this.control["values"];
        control_out.find("#"+this.control_id+"_value")
            .attr({"readonly": "readonly",
                   "size": String([values[default_value[0]],
                                   values[default_value[1]]]).length})
            .val([values[default_value[0]], values[default_value[1]]]);
        control_out.find("#"+this.control_id+"_index").val(default_value);
        slider_config["range"] = true;
        slider_config["slide"] = function(event,ui) {
            var value_box = control_out.find("#"+ui.handle.offsetParent.id+"_value");
            value_box.attr("size", String([values[ui.values[0]],values[ui.values[1]]]).length)
                .val([values[ui.values[0]], values[ui.values[1]]]);
            control_out.find("#" + ui.handle.offsetParent.id + "_index").val(ui.values);
        }
        slider_config["values"] = default_value;
    }
    control_out.find("#"+this.control_id).slider(slider_config);
}

// Initialize jmol
// TODO: move to a better place
jmolInitialize(sagecell.$URL.root + '/static/jmol');
jmolSetCallback("menuFile", sagecell.$URL.root + "/static/jmol/appletweb/SageMenu.mnu");

})(jQuery);
