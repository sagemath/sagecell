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
function initPage() {
    var editor=CodeMirror.fromTextArea($("#commands")[0],{
	mode:"python",
	indentUnit:4,
	tabMode:"shift",
	lineNumbers:true,
	matchBrackets:true,
	onKeyEvent:handleKeyEvent});
    try {
	if(sessionStorage.editor_value) {
	    editor.setValue(sessionStorage.getItem('editor_value'));
	}
	if(sessionStorage.sage_mode) {
	    $('#sage_mode').attr('checked',sessionStorage.getItem('sage_mode')=='true');
	}
    } catch(e) {}
    editor.focus();
    
    var files = 0

    $('#sage_mode').change(function(e) {
	try {
	    sessionStorage.setItem('sage_mode',$(e.target).attr('checked'));
	} catch(e) {};
    });

    $(document.body).append('<form id="sc_form"></form>');
    $('#sc_form').attr('action',$URL.evaluate);
    $('#sc_form').attr('enctype','multipart/form-data');
    $('#sc_form').attr('method','POST');
    $('#singlecell #add_file').click(function(){$('.file_current').click()});
    $('.file_current').live('change',function(e) {
	files++;
	var v=e.target.value;
	if(v) {
	    $('#file_upload').append(v+'<br>');
	} else {
	    $('#file_upload').text(files+' files to be uploaded<br>')
	}
	$('#sc_form').append('<input type="file" id="file'+files+' name="file'+files+'>');
	$('.file_current').removeClass('file_current');
	$('#file'+files).addClass('file_current');
    })

    $('#singlecell #clear_files').click(function(){
	files = 0;
	$('#sc_form').empty();
	$('#file_upload').empty();
	$('#sc_form').html('<input type="file" id="file0" name="file" class="file_current"><br><span id="upload_values"></span>');
    });

    $('#singlecell #clear_files').click();

    $('#singlecell #eval_button').click(function() {
	var session = new Session("#output", $("#sage_mode").attr("checked"));
	$('#computation_id').append('<div>'+session.session_id+'</div>');
	$('#singlecell #session_id').val(session.session_id);
	$('#singlecell #msg_id').val(uuid4());
	$('#sc_form #upload_values').empty()
	$('#sc_form #upload_values').append('<input type="hidden" name="commands">').children().last().val(editor.getValue());
	$('#singlecell #session_id,#msg_id,#sage_mode').each(function(i) {
	    $(this).clone().appendTo($("#sc_form #upload_values"));
	});
	$('#sc_form').attr("target", "upload_target_"+session.session_id);
	$('#singlecell').append("<iframe style='display:none' name = 'upload_target_"+session.session_id+"' id='upload_target_"+session.session_id+"'></iframe>");
	$('#sc_form').submit();
	$("#upload_target_"+session.session_id).load($.proxy(function(event){
	    try {
		var server_response = $("#upload_target_"+session.session_id).contents().find('body').html();
		if (server_response !== "") {
		    session.session_output.append(server_response);
		    session.clearQuery();
		}
	    } catch(e) {}
	    $("#upload_target_"+session.session_id).unbind();
	    $("#singlecell #clear_files").click();	    
	}),session);
	return false;
    });
}

// Create UUID4-compliant ID
// Taken from stackoverflow answer here: http://stackoverflow.com/questions/105034/how-to-create-a-guid-uuid-in-javascript
function uuid4() {
    var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx';
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

colorize = (function(){
    var color_codes = {"30":"black",
		       "31":"red",
		       "32":"green",
		       "33":"goldenrod",
		       "34":"blue",
		       "35":"purple",
		       "36":"darkcyan",
		       "37":"gray"};
    return function(text) {
	var color, result = "";
	text=text.split("\u001b[");
	for(i in text) {
	    if(text[i]=="")
		continue;
	    color=text[i].substr(0,text[i].indexOf("m")).split(";");
	    if(color.length==2) {
		result+="<span style=\"color:"+color_codes[color[1]];
		if(color[0]==1)
		    result+="; font-weight:bold";
		result+="\">"+text[i].substr(text[i].indexOf("m")+1)+"</span>";
	    } else
		result+=text[i].substr(text[i].indexOf("m")+1);
	}
	return result;
    }
})();

function handleKeyEvent(editor, event) {
    if(event.which==13 && event.shiftKey && event.type=="keypress") {
	$('#singlecell #eval_button').click()
	event.stop()
	return true;
    }
    if(window.sessionStorage) {
	try {
	    sessionStorage.removeItem('editor_value');
	    sessionStorage.setItem('editor_value',editor.getValue());
	} catch (e) {
	    // if we can't store, we don't do anything
	    // for example, in chrome if we block cookies, we can't store, it seems.
	};
    }
    return false;
}

/**************************************************************
* 
* Session Class
* 
**************************************************************/

var Session = makeClass();
Session.prototype.init = function (output, sage_mode) {
    this.session_id = uuid4();
    this.sage_mode = sage_mode;
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
    var code = arguments[0], msg, msg_id;

    if (arguments[1] == undefined){
	msg_id = uuid4();
    } else {
	msg_id = arguments[1];
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
    $('#messages').append(document.createElement('div'))
	.children().last().text("*******SEND: "+JSON.stringify(msg));

    /* We need to make a proxy object; see
       http://api.jquery.com/bind/#comment-74776862 or
       http://bitstructures.com/2007/11/javascript-method-callbacks
       for why. If we don't do the proxy, then "this" in the
       send_computation_success function will *not* refer to the
       session object. */
    $.post($URL.evaluate, {message: JSON.stringify(msg)}, function(){})
	.success($.proxy( this, 'send_computation_success' ))
	.error(function(jqXHR, textStatus, errorThrown) {
	    console.log(jqXHR); 
	    console.log(textStatus); 
	    console.log(errorThrown);
	});
}

Session.prototype.output = function(html) {
    if (this.replace_output) {
	return this.session_output.html(html).children().last();
    } else {
	return this.session_output.append(html).children().last();
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
	for (var i = 0, i_max = content.length; i < i_max; i++) {
            var msg = content[i];
	    var parent_id = msg.parent_header.msg_id;
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
		this.output("<pre class='"+msg.content.name+"'></pre>").text(msg.content.data);
		break;

	    case 'pyout':
                this.output("<pre class='pyout'></pre>").append(msg.content.data['text/plain']);
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
		    this.output("<pre></pre>").html(colorize(msg.content.traceback.join("\n").replace(/&/g,"&amp;").replace(/</g,"&lt;")));
		}
		this.updateQuery(2000);
		break;

	    case 'extension':
		var user_msg=msg.content;
		switch(user_msg.msg_type) {
		case "files":
		    var files = user_msg.content.files;
		    var html="<div>\n";
		    for(var j = 0, j_max = files.length; j < j_max; j++)
			//TODO: escape filenames and id
			html+='<a href="'+$URL['root']+'/files/'+id+'/'+files[j]+'" target="_blank">'+files[j]+'</a><br>\n';
		    html+="</div>";
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
		    var interact_id = uuid4();
		    var div_id = "interact-" + interact_id;
		    this.output("<div class='interact_container'><div class='interact' id='"+div_id+"'></div><div class='interact_output' id="+msg.header.msg_id+"></div></div>");
		    this.setOutput("#"+msg.header.msg_id, true, true);
		    this.interacts[msg.header.msg_id] = 1;
		    new InteractCell("#" + div_id, {
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
	case "checkbox":
	    events["change"] = null;
	case "input_box":
	    events["change"] = null;
	    break;
	case "input_grid":
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
    var id = "#urn_uuid_" + this.interact_id;
    var params = {};
    for (var name in this.controls){
	switch(this.controls[name].control_type) {
	case "html":
	    // for text box: this.params[name] = $(id + "-" + name).val();
	    break;
	case "checkbox":
	    if ($(id + "_" + name).attr("checked") == true) {
		params[name] = "True";
	    } else {
		params[name] = "False";
	    }
	    break;
	case "input_box":
	    params[name] = $(id + "_" + name).val();
	    break;
	case "input_grid":
	    var values = "[";
	    for (var j = 0, j_max = this.controls[name].nrows; j < j_max; j ++) {
		values += "[";
		for (var k = 0, k_max = this.controls[name].ncols; k < k_max; k ++) {
		    values += $(id + "_" + name + "_" + j + "_" + k).val() + ", ";
		}
		values += "],";
	    }
	    values += "]"
	    params[name] = values;
	    break;
	case "selector":
	    params[name] = String($(id + "_" + name).val());
	    break;
	case "slider":
	    var input = $(id + "_" + name + "_value").val();
	    $(id + "_" + name).slider("option", "value", input);
	    params[name] = String(input);
	    break;
	}
    }
    return params;
}

InteractCell.prototype.renderCanvas = (function() {
    var addRow=function(table, labeltext, name, controlHTML, id) {
	var row=document.createElement("tr");
	var c_td=document.createElement("td");
	if(labeltext) {
	    var l_td=document.createElement("td");
	    var label=document.createElement("label");
	    label.setAttribute('for',id);
	    label.setAttribute('title',name);
	    label.appendChild(document.createTextNode(labeltext));
	    l_td.appendChild(label);
	    row.appendChild(l_td);
	} else {
	    console.log("#3")
	    c_td.setAttribute("colspan",2);
	}
	c_td.innerHTML=controlHTML;
	row.appendChild(c_td);
	table.appendChild(row);
    }
    var select_labels={};
    return function() {
	// TODO: use this.layout to lay out the controls
	var id = "urn_uuid_" + this.interact_id;
	var table = document.createElement("table");
	for (var name in this.controls) {
	    // We assume layout is a list of variables, in order
	    var control_id = id + '_' + name;
	    var label = escape(this.controls[name].label || name);
	    var type=this.controls[name].control_type;
	    switch(type) {
	    case "html":
		addRow(table, null, null, html_code.replace(new RegExp('$'+name+'$','g'),this.controls[name]["default"])
		       .replace(/\$id\$/g,id));
		break;
	    case "checkbox":
		addRow(table, label, name, '<input type="checkbox" id="'+control_id+'" class="'+id+' checkbox_control" checked="'+this.controls[name]['default']+'">',control_id);
		break;
	    case "input_box":
		addRow(table, label, name, '<input type="text" id="'+control_id+'" class="'+id+' '+' input_box__control" value="'+this.controls[name]['default']+'">',control_id);
		break;
	    case "input_grid":
		var default_values = this.controls[name].default;
		var width = this.controls[name].width;
		var inner_table = "<table><tbody>";
		for (var r = 0, r_max = this.controls[name].nrows; r < r_max; r ++) {
		    inner_table += "<tr>";
		    for (var c = 0, c_max = this.controls[name].ncols; c < c_max; c ++) {
			inner_table += '<td><input type="text" class="'+id+' input_grid_item" id = "'+control_id+'_'+r+'_'+c+'" title="'+name+'['+r+']['+c+']" value="'+default_values[r][c]+'" size="'+width+'"></td>';
		    }
		    inner_table += "</tr>";
		}
		inner_table += "</tbody></table>";
		addRow(table, label, name, inner_table, control_id+'_0_0');
		break;
	    case "selector":
		if (this.controls[name].buttons) {
		    var nrows = this.controls[name].nrows,
		    ncols = this.controls[name].ncols,
		    values = this.controls[name].values,
		    value_labels = this.controls[name].value_labels,
		    default_index = this.controls[name]["default"];
		    var inner_table = "<table><tbody>";
		    for (var r = 0, i = 0; r < nrows; r ++) {
			inner_table += "<tr>";
			for (var c = 0; c < ncols; c ++, i ++) {
			    inner_table += '<td><input type="button" style="width:'+this.controls[name].width+'" class="'+control_id+' selector_button" id="'+control_id+'_'+i+'" value="'+escape(value_labels[i])+'"></td>';
			    $('#'+control_id+'_'+i).live('click', (function(i,control_id){return function(e) {
				if(!$(e.target).hasClass('selected_button')) {
				    $('.'+control_id).filter('.selected_button').removeClass('selected_button');
				    $(e.target).addClass('selected_button');
				    $('#'+control_id).val(values[i]).change();
				    select_labels[control_id].setAttribute('for',e.target.id);
				}
			    }}(i,control_id)));
			}
			inner_table += "</tr>";
		    }
		    inner_table += "</tbody></table>";
		    var html_code = inner_table + '<input type="hidden" id="'+control_id+'" class="'+id+'" value="'+values[default_index]+'"></div>';
		    var default_id=control_id+'_'+default_index
		    addRow(table,label,name,html_code,control_id+'_'+default_index);
		    $(table).find('#'+default_id).addClass('selected_button');
		    select_labels[control_id]=$(table).find('label[for="'+default_id+'"]')[0];
		} else {
		    var html_code = '<select class="' + id + '" id = "' + control_id + '">';
		    var values=this.controls[name].values
		    for (var i=0; i<values.length; i++) {
			html_code += '<option value="' + values[i] + '">' + escape(this.controls[name].value_labels[i]) + "</option>";
		    }
		    html_code = html_code + "</select>";
		    addRow(table,label,name,html_code,control_id);
		}
		break;
	    case "slider":
		var html_code = '<span style="whitespace:nowrap"><span class="' + id + ' slider_control" id="' + control_id + '"></span><input type="text" class="' + id + '" id ="' + control_id + '_value" style="border:none"></span>';
		addRow(table,label,name,html_code,control_id);
		$(table).find("#" + control_id).slider({
		    value:this.controls[name]["default"],
		    min:this.controls[name]["range"][0],
		    max:this.controls[name]["range"][1],
		    step:this.controls[name]["step"],
		    slide:function(event, ui){
			$("#" + ui.handle.offsetParent.id + "_value").val(ui.value);
		    }
		});
		$(table).find("#"+control_id+"_value").val(this.controls[name]["default"]);
		break;
	    }
	}
	this.element[0].appendChild(table);
    }
})();

InteractCell.prototype.locateButtonIndex = function(n, ncols) {
    var location = {};
    location.button = n;
    location.row = Math.floor(n / ncols) - 1;
    if (location.row < 0) {
	location.row = 0;
    }
    location.col = location.button - (location.row * ncols) - 1;
    return location;
}

var escape = function(s) {
    return $('<div></div>').text(s).html();
}