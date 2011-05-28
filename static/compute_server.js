// From sagenb/sagenb/data/sage/js/async_lib.js

function generic_callback(status, response_text) {
    /* do nothing */
}

/* TODO:
   Make session object so that each time eval is pressed, a new session object is created which tracks its own sequence, request, id, session, etc.
*/

$(function() {
    $('#command_form').submit(function() {
	var session = new Session(editor.getValue());
	session.sendMsg();
	return false;
    });
});

function Session(input) {
    this.input = input;
    this.session_id = uuid4();
    this.sequence = 0;
}

Session.prototype.sendMsg = function() {
    var msg = {"parent_header": {},
		   "header": {"msg_id": uuid4(),
			  "username": "",
			  "session": this.session_id},
		   "msg_type": "execute_request",
		   "content": {"code": this.input,
			   "silent": false,
			   "user_variables": [],
			   "user_expressions": {}}
	      };
    return false;
}

Session.prototype.send_computation_success = function(data, textStatus, jqXHR) {
    $("#computation_id").text(data.computation_id);
    this.get_output(data.computation_id);
}

Session.prototype.get_output = function(id) {
    $.getJSON($URL.output_poll, {computation_id: id, sequence: this.sequence},
              function(data, textStatus, jqXHR) {
                  this.get_output_success(data, textStatus, jqXHR, id);});
}

Session.prototype.get_output_success = function(data, textStatus, jqXHR, id) {
    var done = false;

    if(data!==undefined && data.content!==undefined) {
        var content = data.content;
	for (var i = 0; i < content.length; i++) {
            msg=content[i];
            if(msg.sequence!==this.sequence) {
                //TODO: Make a big warning sign
                console.log('sequence is out of order; I think it should be '+sequence+', but server claims it is '+msg.sequence);
            }
            this.sequence+=1;
            // Handle each stream type.  This should probably be separated out into different functions.
	    switch(msg.msg_type) {
	    case 'stream': 
                $('#output').append("<pre class='"+msg.content.name+"'>"+msg.content.data+"</pre>");
		break;

	    case 'pyout':
                $('#output').append("<pre class='pyout'>"+msg.content.data['text/plain']+"</pre>");
		break;

	    case 'display_data':
                if(msg.content.data['image/svg+xml']!==undefined) {
                    $('#output').append('<object id="svgImage" type="image/svg+xml">'+msg.content.data['image/svg+xml']+'</object>');
                } else if(msg.content.data['text/html']!==undefined) {
		    $('#output').append('<div>'+msg.content.data['text/html']+'</div>');
		}
		break;

	    case 'pyerr':
		$('#output').append("<pre>"+colorize(msg.content.traceback.join("\n")
						     .replace(/&/g,"&amp;")
						     .replace(/</g,"&lt;")+"</pre>"));
		break;
	    case 'execute_reply':
		if(msg.content.status==="error") {
		    // copied from the pyerr case
		    $('#output').append("<pre>"+colorize(msg.content.traceback.join("\n")
							 .replace(/&/g,"&amp;")
							 .replace(/</g,"&lt;")+"</pre>"));
		}
		done=true;
		break;

	    case 'extension':
		var user_msg=msg.content;
		switch(user_msg.msg_type) {
		case "files":
		    var html="<div>\n";
		    for(var j=0; j<user_msg.files.length; j++)
			//TODO: escape filenames and id
			html+="<a href=\"/files/"+id+"/"+user_msg.files[j]+"\">"
			    +user_msg.files[j]+"</a><br>\n";
		    $('#output').append(html);
		    break;
		case "session_end":
		    $('#output').append("<div class='done'>Session Done</div>");
		    sequence=0;
		    done=true;
		    break;
		case "interact_start":
		    var div_id = "interact-" + id;
		    console.log(id); // Computation ID
		    $('#output').append("<div id='"+div_id+"'></div>");
		    var interact = new InteractCell("#" + div_id);
		    interact.set_layout(user_msg.content.layout);
		    interact.set_controls(user_msg.content.controls);
		    interact.set_function(user_msg.content.function_code);
		    interact.renderCanvas(id);
		    $(function(){
			$(".urn_uuid_" + id).change(function(){
			    var changes = interact.getChanges(id);
			    var code = interact.function_code + "(";
			    for (var i in changes) {
				code = code + i + "='" +  changes[i] + "',";
			    }
			    code = code + ")";
			    var msg = {"parent_header": {},
				       "header": {"msg_id": uuid4(),
						  "username": "",
						  "session": id},
				       "msg_type": "execute_request",
				       "content": {"code": code,
						   "silent": false,
						   "user_variables": [],
						   "user_expressions": {}}
				      }
			    $.post($URL.evaluate, {message: JSON.stringify(msg)}, send_computation_success, "json");
			});
		    });
		    break;
		case "interact_end":
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
    if(!done) {
        // poll again after a bit
        setTimeout(function() {get_output(id);}, 2000);
    }
}

function InteractCell(selector) {
    this.element = $(selector);
    this.element.data("interact", this);

    this.function_code = "";
    this.controls = {};
    this.layout = {};
}

InteractCell.prototype.getChanges = function(id) {
    id = "#urn_uuid_" + id;
    this.params = {};
    for (var i in this.controls){
	switch(this.controls[i].control_type) {
	case "html":
	   // for text box: this.params[i] = $(id + "-" + i).val();
	    break;
	case "input_box":
	    this.params[i] = $(id + "-" + i).val();
	    break;
	}
    }
    return this.params;
}

InteractCell.prototype.renderCanvas = function(id) {
    id = "urn_uuid_" + id;
    for (var i in this.controls) {
	switch(this.controls[i].control_type) {
	case "html":
	    var html_code = this.controls[i].html;
	    html_code = html_code.replace("$"+i+"$", this.controls[i].default);
	    html_code = html_code.replace("$id$", id);
	    this.element.append(html_code);
	    break;
	case "input_box":
	    this.element.append("<input type='text' value =" + "'" + this.controls[i].default +  "' class = " + id + " id = " + id + "-" + i + "></input>");
	    break;
	}
    }
}

InteractCell.prototype.set_layout = function (new_layout) {
    this.layout = new_layout;
}

InteractCell.prototype.set_controls = function (new_controls) {
    this.controls = new_controls;
}

InteractCell.prototype.set_function = function (new_function) {
    this.function_code = new_function
}


// Create UUID4-compliant ID
// Taken from stackoverflow answer here: http://stackoverflow.com/questions/105034/how-to-create-a-guid-uuid-in-javascript
function uuid4() {
    uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx';
    return uuid.replace(/[xy]/g, function(c) {
	var r = Math.random()*16|0, v = c == 'x' ? r : (r&0x3|0x8);
	return v.toString(16);
    });
}

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

$(document).ready(function(){
    editor=CodeMirror.fromTextArea(document.getElementById("commands"),{
	mode:"python",
	indentUnit:4,
	tabMode:"shift",
	lineNumbers:true,
	onKeyEvent:handleKeyEvent});
    editor.setValue("")
    editor.focus();
});