// From sagenb/sagenb/data/sage/js/async_lib.js

function generic_callback(status, response_text) {
    /* do nothing */
}

function async_request(url, callback, postvars) {
    var settings = {
        url : url,
        async : true,
        cache : false,
        dataType: "json"
    };

    if ($.isFunction(callback)) {
        settings.error = function (jqXHR, textStatus, errorThrown) {
            callback("failure", errorThrown);
        };
        settings.success = function (data, textStatus, jqXHR) {
            callback("success", data, jqXHR);
        };
    }

    if (postvars) {
        settings.type = "POST";
        settings.data = postvars;
    } else {
        settings.type = "GET";
    }

    $.ajax(settings);
}


$(function() {
    // This variable is closed over in scope so it doesn't pollute the global scope
    var sequence=0;
    // Attach a javascript function to the form submit. This function
    // makes an AJAX call to evaluate the contents of the text box.
    var msg = {"parent_header": {},
	       "header": {"msg_id": uuid4(),
			  "username": "",
			  "session": uuid4()},
	       "msg_type": "execute_request",
	       "content": {"code": editor.getValue(),
			   "silent": False,
			   "user_variables": [],
			   "user_expressions": {}}
	      }
    $('#command_form').submit(function () {
        $.getJSON($URL.evaluate, {message: msg}, send_computation_success);
	console.log(editor.getValue());
        return false;
    });

function send_computation_success(data, textStatus, jqXHR) {
    $("#computation_id").text(data.computation_id);
    // start long-polling to get the output
    // TODO: look at maybe using something like https://github.com/RobertFischer/JQuery-PeriodicalUpdater/
    get_output(data.computation_id);
}

function get_output(id) {
    $.getJSON($URL.output_poll, {computation_id: id, sequence: sequence},
              function(data, textStatus, jqXHR) {
                  get_output_success(data, textStatus, jqXHR, id);});
}

function get_output_success(data, textStatus, jqXHR, id) {
    var done=false;

    if(data!==undefined && data.content!==undefined) {
        var content = data.content;
	for (var i = 0; i < content.length; i++) {
            msg=content[i];
            if(msg.sequence!==sequence) {
                //TODO: Make a big warning sign
                console.log('sequence is out of order; I think it should be '+sequence+', but server claims it is '+msg.sequence);
            }
            sequence+=1;
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
		$('#output').append("<pre>"+colorize(msg.content.traceback.join("\n").replace(/</g,"&lt;"))+"</pre>");
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
		case "comp_end":
		    sequence=0;
		    done=true;
		    break;
		case "interact_start":
		    var div_id = "interact" + Math.floor(Math.random()*100000);
		    console.log(id); // Computation ID
		    $('#output').append("<div id='"+div_id+"'></div>");
		    var interact = new InteractCell("#" + div_id);
		    interact.set_layout(user_msg.content.layout);
		    interact.set_controls(user_msg.content.controls);
		    interact.set_function(user_msg.content.function_code);
		    interact.renderCanvas(id);
		    $(function(){
			$("#urn_uuid_" + id).change(function(){
			    // Right now, only notifies (via console) of interact changes
			    console.log($("#urn_uuid_" + id).val());
			});
		    });
		    break;
		case "interact_end":
		    $('#output').append("<div>END OF DIV</div>");
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

});

function InteractCell(selector) {
    this.element = $(selector);
    this.element.data("interact", this);

    this.function_code = "";
    this.controls = {};
    this.layout = {};
}

InteractCell.prototype.renderCanvas = function(id) {
    for (var i in this.controls) {
	switch(this.controls[i].control_type) {
	case "input_box":
	    this.element.append("<input type='text' value =" + "'" + this.controls[i].default +  "' name = '" + i + "' id = 'urn_uuid_" + id  + "'></input>");
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


function get_output_long_poll(id) {
    $.getJSON($URL.output_long_poll, {computation_id: id, timeout: 2},
              function(data, textStatus, jqXHR) {
                  get_output_success(data, textStatus, jqXHR, id);});
}

function get_output_long_poll_success(data, textStatus, jqXHR, id) {
    //alert(data);
    if(data.output==undefined) {
        get_output(id);
    }
    $('#output').text(data.output)
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