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





// Set up the editor and evaluate button
$(function() {
    editor=CodeMirror.fromTextArea(document.getElementById("commands"),{
	mode:"python",
	indentUnit:4,
	tabMode:"shift",
	lineNumbers:true,
	matchBrackets:true});
    editor.setValue("")
    editor.focus();
    
    $('#command_form').submit(function() {
	var session = new Session('#output');
	$('#computation_id').append('<div>'+session.session_id+'</div>');
	msg=session.sendMsg(editor.getValue());
	return false;
    });
});


// Create UUID4-compliant ID
// Taken from stackoverflow answer here: http://stackoverflow.com/questions/105034/how-to-create-a-guid-uuid-in-javascript
function uuid4() {
    uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx';
    return uuid.replace(/[xy]/g, function(c) {
	var r = Math.random()*16|0, v = c == 'x' ? r : (r&0x3|0x8);
	return v.toString(16);
    });
}

// makeClass - By John Resig (MIT Licensed)
// see http://ejohn.org/blog/simple-class-instantiation/
function makeClass(){
  return function(args){
    if ( this instanceof arguments.callee ) {
      if ( typeof this.init == "function" )
        this.init.apply( this, args.callee ? args : arguments );
    } else
      return new arguments.callee( arguments );
  };
}


/**************************************************************
* 
* Colorize Tracebacks
* 
**************************************************************/
colorCodes={"30":"black",
	    "31":"red",
	    "32":"green",
	    "33":"goldenrod",
	    "34":"blue",
	    "35":"purple",
	    "36":"darkcyan",
	    "37":"gray"};

function colorize(text) {
    text=text.split("\u001b[");
    result="";
    for(i in text) {
	if(text[i]=="")
	    continue;
	color=text[i].substr(0,text[i].indexOf("m")).split(";");
	if(color.length==2) {
	    result+="<span style=\"color:"+colorCodes[color[1]];
	    if(color[0]==1)
		result+="; font-weight:bold";
	    result+="\">"+text[i].substr(text[i].indexOf("m")+1)+"</span>";
	} else
	    result+=text[i].substr(text[i].indexOf("m")+1);
    }
    return result;
}

/**************************************************************
* 
* Session Class
* 
**************************************************************/

var Session = makeClass();
Session.prototype.init = function (output) {
    this.session_id = uuid4();
    this.sequence = 0;
    this.poll_interval = 400;
    $(output).append('<div id="session_'+this.session_id+'" class="session_container"><div id="session_'+this.session_id+'_title" class="session_title">Session '+this.session_id+'</div><div id="session_'+this.session_id+'_output" class="session_output"></div></div>');
    this.session_title=$('#session_'+this.session_id+'_title');
    this.session_output=$('#session_'+this.session_id+'_output');
    this.replace_output=false;
    this.lock_output=false;
    this.eventHandlers = {};
    this.interacts = {};
    this.setQuery();
}

// Manages where session output should be sent, whether it should replace existing content, and whether other function calls are allowed to modify it.
Session.prototype.setOutput = function(location, replace, lock) {
    if (! this.lock_output) {
	this.restoreOutput();
	this.session_output = $("#session_"+this.session_id+" "+location);
	if (replace) {
	    this.replace_output = true;
	}
	if (lock) {
	    this.lock_output = true;
	}
    }
}
Session.prototype.restoreOutput = function() {
    this.session_output=$("#session_"+this.session_id+" #session_"+this.session_id+"_output");
    this.replace_output = false;
    this.lock_output = false;
}

// Manages querying the webserver for messages
Session.prototype.setQuery = function() {
    this.queryID = setInterval($.proxy(this, 'get_output'), this.poll_interval);
}

Session.prototype.clearQuery = function() {
    clearInterval(this.queryID);
}

Session.prototype.updateQuery = function(new_interval) {
    this.poll_interval = new_interval;
    this.clearQuery();
    this.setQuery();
}

Session.prototype.sendMsg = function() {
    var code = arguments[0];
    var msg_id;
    if (arguments[1] == undefined){
	msg_id = uuid4();
    } else {
	msg_id = arguments[1];
    }
    var msg = {"parent_header": {},
		   "header": {"msg_id": msg_id,
			  "username": "",
			  "session": this.session_id},
		   "msg_type": "execute_request",
		   "content": {"code": code,
			   "silent": false,
			   "user_variables": [],
			   "user_expressions": {}}
	      };
    /* We need to make a proxy object; see
       http://api.jquery.com/bind/#comment-74776862 or
       http://bitstructures.com/2007/11/javascript-method-callbacks
       for why. If we don't do the proxy, then "this" in the
       send_computation_success function will *not* refer to the
       session object. */
    $.post($URL.evaluate, {message: JSON.stringify(msg)}, dataType="json")
	.success($.proxy( this, 'send_computation_success' ), "json")
	.error(function(jqXHR, textStatus, errorThrown) {
	    console.log(jqXHR); 
	    console.log(textStatus); 
	    console.log(errorThrown);
	});
}

Session.prototype.output = function(html) {
    if (this.replace_output) {
	this.session_output.html(html);
    } else {
	this.session_output.append(html);
    }
}

Session.prototype.send_computation_success = function(data, textStatus, jqXHR) {
    if (data.computation_id!==this.session_id) {
	alert("Session id returned and session id sent don't match up");
    }
    this.get_output();
}

Session.prototype.get_output = function() {
    // POSSIBLE TODO: Have a global object querying the server for a given computation. Right now, it's managed by the session object.
    $.getJSON($URL.output_poll, {computation_id: this.session_id, sequence: this.sequence}, $.proxy(this, 'get_output_success'));
}

Session.prototype.get_output_success = function(data, textStatus, jqXHR) {
    var id=this.session_id;

    if(data!==undefined && data.content!==undefined) {
        var content = data.content;
	for (var i = 0; i < content.length; i++) {
            var msg=content[i];
	    var parent_id=msg.parent_header.msg_id;
	    if (this.interacts[parent_id] == 1) {
		this.setOutput("#"+parent_id, true, false);
	    } else if (! this.lock_output) {
		this.restoreOutput();
	    }
            if(msg.sequence!==this.sequence) {
                //TODO: Make a big warning sign
                console.log('sequence is out of order; I think it should be '+this.sequence+', but server claims it is '+msg.sequence);
            }
            this.sequence+=1;
            // Handle each stream type.  This should probably be separated out into different functions.
	    switch(msg.msg_type) {
	    //TODO: if two stdout/stderr messages happen consecutively, consolidate them in the same pre
	    case 'stream':
		this.output("<pre class='"+msg.content.name+"'>"+msg.content.data+"</pre>");
		break;

	    case 'pyout':
                this.output("<pre class='pyout'>"+msg.content.data['text/plain']+"</pre>");
		break;

	    case 'display_data':
                if(msg.content.data['image/svg+xml']!==undefined) {
                    this.output('<object id="svgImage" type="image/svg+xml">'+msg.content.data['image/svg+xml']+'</object>');
                } else if(msg.content.data['text/html']!==undefined) {
		    this.output('<div>'+msg.content.data['text/html']+'</div>');
		}
		break;

	    case 'pyerr':
		this.output("<pre>"+colorize(msg.content.traceback.join("\n")
						     .replace(/&/g,"&amp;")
						     .replace(/</g,"&lt;")+"</pre>"));
		break;
	    case 'execute_reply':
		if(msg.content.status==="error") {
		    // copied from the pyerr case
		    this.output("<pre>"+colorize(msg.content.traceback.join("\n")
							.replace(/&/g,"&amp;")
							.replace(/</g,"&lt;")+"</pre>"));
		}
		this.updateQuery(2000);
		break;

	    case 'extension':
		var user_msg=msg.content;
		switch(user_msg.msg_type) {
		case "files":
		    var files=user_msg.content.files
		    var html="<div>\n";
		    for(var j=0; j<files.length; j++)
			//TODO: escape filenames and id
			html+="<a href=\"/files/"+id+"/"+files[j]+"\">"
			    +files[j]+"</a><br>\n";
		    this.output(html);
		    break;
		case "session_end":
		    this.output("<div class='done'>Session "+id+ " done</div>");
		    // Unbinds interact change handlers
		    for (var i in this.eventHandlers) {
			for (var j in this.eventHandlers[i]) {
			    $(i).die(this.eventHandlers[i][j]);
			}
		    }
		    this.clearQuery();
		    break;
		case "interact_start":
		    interact_id = uuid4();
		    var div_id = "interact-" + interact_id;
		    this.output("<div class='interact_container'><div class='interact' id='"+div_id+"'></div><div class='interact_output' id="+msg.header.msg_id+"></div></div>");
		    this.setOutput("#"+msg.header.msg_id, true, true);
		    this.interacts[msg.header.msg_id] = 1;
		    var interact = new InteractCell("#" + div_id, {
			'interact_id': interact_id,
			'layout': user_msg.content.layout,
			'controls': user_msg.content.controls,
			'function_code': user_msg.content.function_code,
			'msg_id': msg.header.msg_id,
			'session': this});
		    break;
		case "interact_end":
		    this.restoreOutput();
		    break;
		}
		break;
	    }

	    // Append the message to the div of messages
	    // use .text() so that strings are automatically escaped
	    $('#messages').append(document.createElement('div'))
		.children().last().text(JSON.stringify(msg));
        }
    }
}

/**************************************************************
* 
* InteractCell Class
* 
**************************************************************/


var InteractCell = makeClass();
InteractCell.prototype.init = function (selector, data) {
    this.element = $(selector);
    this.element.data("interact", this);
    this.interact_id = data.interact_id
    this.function_code = data.function_code;
    this.controls = data.controls;
    this.layout = data.layout;
    this.session = data.session;
    this.msg_id = data.msg_id;

    this.renderCanvas();
    this.bindChange(this);
}

InteractCell.prototype.bindChange = function(interact) {
    var id = ".urn_uuid_" + this.interact_id;
    var events = {};
    for (var i in this.controls) {
	switch(this.controls[i].control_type) {
	case "html":
	    break;
	case "input_box":
	    events["change"] = null;
	    break;
	case "selector":
	    events["change"] = null;
	    break;
	case "slider":
	    events["slidestop"] = null;
	    events["change"] = null;
	    break;
	}
    }
    this.session.eventHandlers[id] = [];
    for (var i in events) {
	this.session.eventHandlers[id].push(i);
	$(id).live(i, function(){
            var changes = interact.getChanges();
            var code = interact.function_code + "(";
            for (var i in changes) {
		if (interact.controls[i].raw) {
		    code = code + i + "=" + changes[i] + ",";
		} else {
		    code = code + i + "='" + changes[i].replace(/'/g, "\\'") + "',";
		}
            }
            code = code + ")";
	    interact.session.sendMsg(code, interact.msg_id);
	});
    }
}

InteractCell.prototype.getChanges = function() {
    id = "#urn_uuid_" + this.interact_id;
    var params = {};
    for (var i in this.controls){
	switch(this.controls[i].control_type) {
	case "html":
	   // for text box: this.params[i] = $(id + "-" + i).val();
	    break;
	case "input_box":
	    params[i] = $(id + "_" + i).val();
	    break;
	case "selector":
	    params[i] = $(id + "_" + i).val();
	    break;
	case "slider":
	    var input = $(id + "_" + i + "_value").val();
	    $(id + "_" + i).slider("option", "value", input);
	    params[i] = String(input);
	    break;
	}
    }
    return params;
}

InteractCell.prototype.renderCanvas = function() {
    // TODO: use this.layout to lay out the controls
    id = "urn_uuid_" + this.interact_id;
    for (var i in this.controls) {
	switch(this.controls[i].control_type) {
	case "html":
	    var html_code = this.controls[i].html;
	    html_code = html_code.replace("$"+i+"$", this.controls[i]["default"]);
	    html_code = html_code.replace("$id$", id);
	    this.element.append(html_code);
	    break;
	case "input_box":
	    var html_code = "<div class='interact_input_box'><table><tbody><tr><td class=" + id + " id='" + id + "_" + i + "_label' style='width:5em'>" + this.controls[i].label + "</td><td><input type='text' value =" + "'" + this.controls[i]["default"] +  "' class = " + id + " id = " + id + "_" + i + "></input></td></tr></tbody></table></div>";
	    this.element.append(html_code);
	    break;
	case "selector":
	    var html_selector = "<select class = " + id + " id = " + id + "_" + i + ">";
	    for (var j in this.controls[i].values) {
		if (j == this.controls[i]["default"]) {
		    html_selector = html_selector + "<option selected='selected' value'" + this.controls[i].values[j] + "'>" + this.controls[i].values[j] + "</option>";
		} else {
		    html_selector = html_selector + "<option value'" + this.controls[i].values[j] + "'>" + this.controls[i].values[j] + "</option>";
		}
	    }
	    html_selector = html_selector + "</select>";
	    var html_code = "<div class='interact_select'><table><tbody><tr><td class=" + id + " id='" + id + "_" + i + "_label' style='width:5em'>" + this.controls[i].label + "</td><td>" + html_selector + "</td></tr></tbody></table></div>";
	    this.element.append(html_code);
	    break;
	case "slider":
	    var html_code = "<div class='interact_slider'><table><tbody><tr><td class=" + id + " id='" + id + "_" + i + "_label' style='width:5em'>" + this.controls[i].label + "</td><td><div class=" + id + " id='" + id + "_" + i + "' style='width:15.0em;margin-right:1.0em;margin-left:1.0em'></div></td><td><input type='text' class=" + id + " id ='" + id + "_" + i + "_value' value='' style='border:none'></input></td></tr></tbody></table></div>";
	    this.element.append(html_code);
	    $("#" + id + "_" + i).slider({
		value:this.controls[i]["default"],
		min:this.controls[i]["range"][0],
		max:this.controls[i]["range"][1],
		step:this.controls[i]["step"],
		slide:function(event, ui){
		    $("#" + ui.handle.offsetParent.id + "_value").val(ui.value);
		}
	    });
	    $("#"+id+"_"+i+"_value").val($("#"+id+"_"+i).slider("value"));
	    break;
	}
    }
}
