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



// Initialize jmol
// TODO: move to a better place
jmolInitialize('/static/jmol');
// TODO: setting the menu doesn't appear to work
//jmolSetCallback("menuFile","/static/jmol/appletweb/SageMenu.mnu");


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

/**************************************************************
* 
* Session Class
* 
**************************************************************/

var Session = makeClass();
Session.prototype.init = function (outputDiv, output, sage_mode) {
    this.outputDiv = outputDiv;
    this.session_id = uuid4();
    this.sage_mode = sage_mode;
    this.sequence = 0;
    this.poll_interval = 400;
    this.lastMessage = null;
    this.sessionContinue = true;
    this.outputDiv.find(output).append('<div id="session_'+this.session_id+'" class="singlecell_sessionContainer"><div id="session_'+this.session_id+'_title" class="singlecell_sessionTitle">Session '+this.session_id+'</div><div id="output_'+this.session_id+'" class="singlecell_sessionOutput"></div></div>');
    this.session_title=$('#session_'+this.session_id+'_title');
    this.replace_output=false;
    this.lock_output=false;
    this.eventHandlers = {};
    this.interacts = {};
    this.setQuery();
}

// Manages querying the webserver for messages
Session.prototype.setQuery = function() {
    this.clearQuery();
    this.queryID = setTimeout($.proxy(this, 'get_output'), this.poll_interval);
}

Session.prototype.clearQuery = function() {
    clearTimeout(this.queryID);
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
    this.lastMessage = msg_id;
    this.appendMsg(msg, "*******SEND: ");
    /* We need to make a proxy object; see
       http://api.jquery.com/bind/#comment-74776862 or
       http://bitstructures.com/2007/11/javascript-method-callbacks
       for why. If we don't do the proxy, then "this" in the
       send_computation_success function will *not* refer to the
       session object. */
    $.post($URL.evaluate, {message: JSON.stringify(msg)}, function(){})
	.success($.proxy( this, 'send_computation_success' ))
	.error(function(jqXHR, textStatus, errorThrown) {
	    console.warn(jqXHR); 
	    console.warn(textStatus); 
	    console.warn(errorThrown);
	});
}

Session.prototype.appendMsg = function(msg, text) {
    // Append the message to the div of messages
    // Use $.text() so that strings are automatically escaped
    this.outputDiv.find(".singlecell_messages").append(document.createElement('div')).children().last().text(text+JSON.stringify(msg));
}

Session.prototype.output = function(html, block_id) {
    var output_block=$("#output_"+(block_id || this.session_id));
    if (this.replace_output) {
	output_block.empty();
	this.replace_output=false;
    }
    return output_block.append(html).children().last();
}

Session.prototype.write = function(html) {
    this.output(html);
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
	    var output_block = msg.output_block;
            if(msg.sequence!==this.sequence) {
                //TODO: Make a big warning sign
                console.warn('sequence is out of order; I think it should be '+this.sequence+', but server claims it is '+msg.sequence);
            }
            this.sequence+=1;
	    if (parent_id !== undefined && parent_id !== this.lastMessage && this.lastMessage !== null) {
		// If another message has been sent to the server since the parent of this one, don't format it for output but log that it was received.
		// This solves a problem associated with updating complex interacts quicker than the server can reply where output would be printed multiple times.
		this.appendMsg(msg, "Rejected: ");
		continue;
	    }
            // Handle each stream type.  This should probably be separated out into different functions.
	    switch(msg.msg_type) {
		//TODO: if two stdout/stderr messages happen consecutively, consolidate them in the same pre
	    case 'stream':
		this.output("<pre class='singlecell_"+msg.content.name+"'></pre>",output_block).text(msg.content.data);
		break;

	    case 'pyout':
                this.output("<pre class='singlecell_pyout'></pre>",output_block).append(msg.content.data['text/plain']);
		break;

	    case 'display_data':
		var filepath=$URL['root']+'files/'+id+'/';
                if(msg.content.data['image/svg+xml']!==undefined) {
                    this.output('<embed  class="singlecell_svgImage" type="image/svg+xml">'+msg.content.data['image/svg+xml']+'</embed>',output_block);
		}
                if(msg.content.data['text/html']!==undefined) {
		    this.output('<div>'+msg.content.data['text/html']+'</div>',output_block);
		}
		if(msg.content.data['text/filename']!==undefined) {
		    this.output('<img src="'+filepath+msg.content.data['text/filename']+'" />');
		}
		if(msg.content.data['image/png']!==undefined) {
		    console.log('making png img with data in src');
		    this.output('<img src="'+msg.content.data['image/png']+'" />');
		}
		if(msg.content.data['application/x-jmol']!==undefined) {
		    console.log('making jmol applet');
		    console.log(this);
		    jmolSetDocument(this);
		    jmolApplet(500, 'set defaultdirectory "'+filepath+msg.content.data['application/x-jmol']+'";\n script SCRIPT;\n');
		}
		
		break;

	    case 'pyerr':
		this.output("<pre>"+colorize(msg.content.traceback.join("\n")
					     .replace(/&/g,"&amp;")
					     .replace(/</g,"&lt;")+"</pre>"),output_block);
		break;
	    case 'execute_reply':
		if(msg.content.status==="error") {
		    // copied from the pyerr case
		    this.output("<pre></pre>",output_block).html(colorize(msg.content.traceback.join("\n").replace(/&/g,"&amp;").replace(/</g,"&lt;")));
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
			html+='<a href="'+$URL['root']+'files/'+id+'/'+files[j]+'" target="_blank">'+files[j]+'</a><br>\n';
		    html+="</div>";
		    this.output(html,output_block);
		    break;
		case "session_end":
		    this.output("<div class='singlecell_done'>Session "+id+ " done</div>",output_block);
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
		    var div_id = "interact-" + interact_id;
		    this.output("<div class='singlecell_interactContainer'><div class='singlecell_interact' id='"+div_id+"'></div><div class='singlecell_interactOutput' id='output_"+interact_id+"'></div></div>",output_block);
		    this.interacts[interact_id] = 1;
		    new InteractCell("#" + div_id, {
			'interact_id': interact_id,
			'layout': user_msg.content.layout,
			'controls': user_msg.content.controls,
			'session': this});
		    break;
		}
		break;
	    }
	    
	    this.appendMsg(msg, "Accepted: ");
        }
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
	var control_type = this.controls[i].control_type;
	var subtype = this.controls[i].subtype;
	switch(control_type) {
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
	case "multi_slider":
	    events["slidestop"] = null;
	    if (subtype === "continuous") {
		events["change"] = null;
	    }
	    break;
	case "slider":
	    events["slidestop"] = null;
	    switch (subtype) {
	    case "continuous": // Fall-through here by design
	    case "continuous_range":
		events["change"] = null;
		break;
	    }
	case "color_selector":
	    events["change"] = null;
	    break;
	case "button":
	    events["change"] = null;
	    break;
	case "button_bar":
	    events["change"] = null;
	}
    }
    this.session.eventHandlers[id] = [];
    for (var i in events) {
	this.session.eventHandlers[id].push(i);
	$(id).live(i, function(){
            var changes = interact.getChanges();
	    var code = "_get_interact_function('"+interact.interact_id+"')(";
            for (var i in changes) {
		if (interact.controls[i].raw) {
		    code = code + i + "=" + changes[i] + ",";
		} else {
		    code = code + i + "='" + changes[i].replace(/'/g, "\\'") + "',";
		}
            }
            code = code + ")";
	    interact.session.sendMsg(code, interact.msg_id);
	    interact.session.replace_output=true;
	    return false;
	});
    }
}

InteractCell.prototype.getChanges = function() {
    var id = "#urn_uuid_" + this.interact_id;
    var params = {};
    for (var name in this.controls){
	var control_type=this.controls[name].control_type;
	var subtype=this.controls[name].subtype;
	switch(control_type) {
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
	case "multi_slider":
	    var sliders = this.controls[name]["sliders"];
	    var slider_values = [];
	    switch(subtype) {
	    case "continuous":
		for (i = 0; i < sliders; i ++) {
		    var input = $(id + "_" + name + "_" + i + "_value").val();
		    $(id + "_" + name + "_" + i).slider("option", "value", input);
		    slider_values.push(input);
		}
		break;
	    case "discrete":
		for (i = 0; i < sliders; i ++) {
		    slider_values.push($(id + "_" + name + "_" + i + "_index").val());
		}
		break;
	    }
	    params[name] = "["+ String(slider_values) +"]";
	    break;
	case "slider":
	    switch(subtype) {
	    case "continuous":
		var input = $(id + "_" + name + "_value").val();
		$(id + "_" + name).slider("option", "value", input);
		params[name] = String(input);
		break;
	    case "continuous_range":
		var input = String("["+$(id + "_" + name + "_value").val()+"]");
		$(id + "_" + name).slider("option","values",JSON.parse(input));
		params[name] = input;
		break;
	    case "discrete":
		params[name] = String($(id + "_" + name + "_index").val());
		break;
	    case "discrete_range":
		params[name] = String("["+$(id + "_" + name + "_index").val()+"]");
		break;
	    }
	    break;
	case "color_selector":
	    params[name] = $(id + "_" + name + "_value").val();
	    break;
	case "button":
	    params[name] = $(id + "_" + name + "_value").val();
	    $(id + "_" + name + "_value").val("false");
	    break;
	case "button_bar":
	    params[name] = $(id + "_" + name + "_value").val();
	    $(id + "_" + name + "_value").val("None");
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
	    if(id) {
		label.setAttribute('for',id);
	    }
	    label.setAttribute('title',name);
	    label.appendChild(document.createTextNode(labeltext));
	    l_td.appendChild(label);
	    row.appendChild(l_td);
	} else {
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
	    var subtype=this.controls[name].subtype;
	    switch(type) {
	    case "html":
		addRow(table, null, null, html_code.replace(new RegExp('$'+name+'$','g'),this.controls[name]["default"])
		       .replace(/\$id\$/g,id));
		break;
	    case "checkbox":
		addRow(table, label, name, '<input type="checkbox" id="'+control_id+'" class="'+id+' checkbox_control" checked="'+this.controls[name]['default']+'">',control_id);
		break;
	    case "input_box":
		addRow(table, label, name, '<input type="text" id="'+control_id+'" class="'+id+'" size='+this.controls[name]["width"]+' value="'+this.controls[name]['default']+'">',control_id);
		break;
	    case "input_grid":
		var default_values = this.controls[name]["default"];
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
		var nrows = this.controls[name].nrows,
		ncols = this.controls[name].ncols,
		values = this.controls[name].values,
		value_labels = this.controls[name].value_labels,
		default_index = this.controls[name]["default"];

		switch(subtype) {
		case "list":
		    var html_code = '<select class="' + id + '" id = "' + control_id + '">';
		    for (var i=0; i<values.length; i++) {
			html_code += '<option value="' + values[i] + '">' + escape(value_labels[i]) + "</option>";
		    }
		    html_code = html_code + "</select>";
		    addRow(table,label,name,html_code,control_id);
		    break;
		case "radio":
		    var default_id = control_id+"_"+default_index,
		    inner_table = "<table><tbody>",
		    html_code;

		    for (var r = 0, i = 0; r < nrows; r ++) {
			inner_table += "<tr>";
			for (var c = 0; c < ncols; c ++, i ++) {
			    inner_table += '<td><input class="'+control_id+'" id="'+control_id+'_'+i+'" type="radio" name="'+control_id+'" value='+i+' />'+escape(value_labels[i])+'</td>';
			    $("#"+control_id+"_"+i).live("mousedown", (function(i,control_id){return function(e) {
				if (!$(e.target).attr("checked")) {
				    $("#"+control_id).val(values[i]).change();
				}
			    }}(i,control_id)));
			}
			inner_table += "</tr>";
		    }
		    inner_table += "</tbody></table>";
		    html_code = inner_table + '<input type="hidden" id ="'+control_id+'" class="'+id+'" value="'+values[default_index]+'"></div';
		    addRow(table,label,name,html_code,control_id);
		    $(table).find("#"+default_id).attr("checked","checked");
		break;
		case "button":
		    var inner_table = "<table><tbody>";
		    for (var r = 0, i = 0; r < nrows; r ++) {
			inner_table += "<tr>";
			for (var c = 0; c < ncols; c ++, i ++) {
			    inner_table += '<td><button class="'+control_id+' singlecell_button ui-widget ui-state-default ui-corner-all" id="'+control_id+'_'+i+'"><span>'+escape(value_labels[i])+'</span></button></td>';
			    $('#'+control_id+'_'+i).live('mouseenter', (function(i,control_id) {return function(e) {
				$('#'+control_id+'_'+i).addClass('ui-state-hover');
			    }}(i,control_id)));
			    $('#'+control_id+'_'+i).live('mouseleave', (function(i,control_id) {return function(e) {
				$('#'+control_id+'_'+i).removeClass('ui-state-hover');
			    }}(i,control_id)));
			    $('#'+control_id+'_'+i).live('click', (function(i,control_id) {return function(e) {
				if(!$('#'+control_id+'_'+i).hasClass('ui-state-active')) {
				    $('.'+control_id).filter('.ui-state-active').removeClass('ui-state-active');
				    $('#'+control_id+'_'+i).addClass('ui-state-active');
				    $('#'+control_id+'_value').val(values[i]).change();
				    select_labels[control_id].setAttribute('for',e.target.id);
				}
			    }}(i,control_id)));
				
			}
			inner_table += "</tr>";
		    }
		    inner_table += "</tbody></table>";
		    var html_code = inner_table + '<input type="hidden" id="'+control_id+'_value" class="'+id+'" value="'+values[default_index]+'"></div>';
		    var default_id=control_id+'_'+default_index
		    addRow(table,label,name,html_code,control_id+'_'+default_index);
		    $(table).find("."+control_id).css("width",this.controls[name].width);
		    $(table).find('#'+default_id).addClass('ui-state-active');
		    select_labels[control_id]=$(table).find('label[for="'+default_id+'"]')[0];
		    $(table).find('label:last').click((function(control_id){return function() {
			$('.'+control_id+' .ui-state-active').focus();
		    }})(control_id))

		    break;
		case "radio":
		    
		    break;
		}

		break;
	    case "multi_slider":
		var sliders = this.controls[name]["sliders"];
		var slider_values = this.controls[name]["values"];
		var slider_config = {};

		var html_code = '<div class="' + id + ' singlecell_multiSliderContainer"><span style="whitespace:nowrap">';

		for (var i = 0; i < sliders; i++) {
		    html_code = html_code +
			'<span class="singlecell_multiSliderControl" id = "' + control_id + '_' + i +'"></span>'+
			'<input type="text" class="' + control_id + '_value' + '" id ="' + control_id + '_' + i + '_value" style="border:none;" size="4">'+
			'<input class="' + control_id + '_index' + '" id ="' + control_id + '_' + i + '_index" style="display:none"></input>';
		}
		html_code = html_code + '</span></div>';
		addRow(table,label,name,html_code,null);

		switch(subtype) {
		case "continuous":
		    for (var i = 0; i < sliders; i ++) {
			$(table).find("#" + control_id + "_" + i + "_value").val(this.controls[name]["default"][i]);
			$(table).find("#" + control_id + "_" + i + "_value").addClass(id);
			slider_config = {
			    orientation:"vertical",
			    value: this.controls[name]["default"][i],
			    min: this.controls[name]["range"][i][0],
			    max: this.controls[name]["range"][i][1],
			    step: this.controls[name]["step"][i],
			    slide: function(event,ui) {
				$(table).find("#" + ui.handle.offsetParent.id + "_value").val(ui.value);
			    }
			};

			$(table).find("#" + control_id + "_" + i).slider(slider_config);
		    }
		    break;

		case "discrete":
		    $(table).find("."+control_id+"_value").attr("readonly","readonly");
		    for (var i = 0; i < sliders; i++) {
			var i_temp = i;
			$(table).find("#" + control_id + "_" + i + "_value").val(slider_values[i][this.controls[name]["default"][i]]);
			$(table).find("#" + control_id + "_" + i + "_index").val(this.controls[name]["default"][i]);

			slider_config = {
			    orientation:"vertical",
			    value: this.controls[name]["default"][i],
			    min: this.controls[name]["range"][i][0],
			    max: this.controls[name]["range"][i][1],
			    step: this.controls[name]["step"][i],
			    slide: function(event,ui) {
				$(table).find("#" + ui.handle.offsetParent.id + "_value").val(slider_values[i_temp][ui.value]);
				$(table).find("#" + ui.handle.offsetParent.id + "_index").val(ui.value);
			    }
			};
			$(table).find("#" + control_id + "_" + i).slider(slider_config);
		    }
		    break;
		}
		
	    	break;
	    case "slider":
		var html_code = '<span style="whitespace:nowrap"><span class="' + id + ' singlecell_sliderControl" id="' + control_id + '"></span><input type="text" class="' + id + '" id ="' + control_id + '_value" style="border:none"><input type="text" class="' + id +'" id ="' + control_id + '_index" style="display:none"></span>';
		var slider_config = {
		    min:this.controls[name]["range"][0],
		    max:this.controls[name]["range"][1],
		    step:this.controls[name]["step"]
		}
		var default_value = this.controls[name]["default"]

		addRow(table,label,name,html_code,null);
		switch(subtype) {
		case "discrete":
		    var values = this.controls[name].values;
		    $(table).find("#"+control_id+"_value").val(values[default_value]);
		    $(table).find("#"+control_id+"_index").val(default_value);

		    $(table).find("#"+control_id+"_value").attr("readonly", "readonly");

		    slider_config["slide"] = function(event,ui) {
			$("#" + ui.handle.offsetParent.id + "_value").val(values[ui.value]);
			$("#" + ui.handle.offsetParent.id + "_index").val(ui.value);
		    }
		    slider_config["value"] = default_value;
		    break;
		case "discrete_range":
		    var values = this.controls[name].values;
		    $(table).find("#"+control_id+"_value").val([values[default_value[0]], values[default_value[1]]]);
		    $(table).find("#"+control_id+"_index").val(default_value);

		    $(table).find("#"+control_id+"_value").attr("readonly", "readonly");

		    slider_config["range"] = true;
		    slider_config["slide"] = function(event,ui) {
			$("#" + ui.handle.offsetParent.id + "_value").val([values[ui.values[0]], values[ui.values[1]]]);
			$("#" + ui.handle.offsetParent.id + "_index").val(ui.values);
		    }
		    slider_config["values"] = default_value;
		    break;
		case "continuous":
		    $(table).find("#"+control_id+"_value").val(default_value);

		    slider_config["slide"] = function(event,ui) {
			$("#" + ui.handle.offsetParent.id + "_value").val(ui.value);
		    }
		    slider_config["value"] = default_value;
		    break;
		case "continuous_range":
		    $(table).find("#"+control_id+"_value").val(default_value);

		    slider_config["range"] = true;
		    slider_config["slide"] = function(event,ui) {
			$("#" + ui.handle.offsetParent.id + "_value").val(ui.values);
		    }
		    slider_config["values"] = default_value;
		    break;
		}

		$(table).find("#" + control_id).slider(slider_config);

		$(table).find('label:last').click((function(control_id){return function() {
		    $('#'+control_id+' .ui-slider-handle').focus();
		};})(control_id))
		break;
	    case "color_selector":
		var default_value = this.controls[name]["default"];
		addRow(table, label, name, '<input type="text" class="singlecell_colorSelector" id='+control_id+'><input type="text" id="'+control_id+'_value" style="border:none" class="'+id+'" value='+this.controls[name]["default"]+'>',control_id);
		$(table).find("#"+control_id).css({"backgroundColor": default_value});
		$(table).find("#"+control_id).ColorPicker({
		    color: default_value,
		    onSubmit: function(hsb, hex, rgb, el) {
			$("#"+control_id+"_value").val("#"+hex);
			$(el).ColorPickerHide();
			$("#"+control_id+"_value").trigger("change");
		    },
		    onChange: function(hsb, hex, rgb, el) {
			$("#"+control_id).css({"backgroundColor": "#"+hex, "color": "#"+hex});
			$("#"+control_id+"_value").val("#"+hex);
		    }
		});
		break;
	    case "button":
		html_code = '<button class="singlecell_button ui-widget ui-state-default ui-corner-all" id="'+control_id+'_button"><span>'+this.controls[name]["text"]+'</span></button><input type="hidden" id="'+control_id+'_value" class="'+id+'" value="false">';
		addRow(table, label, name, html_code, control_id);

		$(table).find("#"+control_id+"_button").css("width",this.controls[name].width);

		$("#"+control_id+"_button").live("mouseenter", (function(control_id) {return function(e) {
		    $("#"+control_id+"_button").addClass("ui-state-hover");
		}}(control_id)));
		$("#"+control_id+"_button").live("mouseleave", (function(control_id) {return function(e) {
		    $("#"+control_id+"_button").removeClass("ui-state-hover");
		}}(control_id)));
		$("#"+control_id+"_button").live("mousedown", (function(control_id) {return function(e) {
		    $("#"+control_id+"_button").addClass("ui-state-active");
		}}(control_id)));
		$("#"+control_id+"_button").live("mouseup", (function(control_id) {return function(e) {
		    $("#"+control_id+"_button").removeClass("ui-state-active");
		    $("#"+control_id+"_value").val("true").change();
		}}(control_id)));
		break;
	    case "button_bar":
		var nrows = this.controls[name].nrows,
		ncols = this.controls[name].ncols,
		value_labels = this.controls[name].value_labels,
		values = this.controls[name].values;

		var inner_table = "<table><tbody>";
		for (var r = 0, i = 0; r < nrows; r++) {
		    inner_table += "<tr>";
		    for (var c = 0; c < ncols; c ++, i++) {
			inner_table += '<td><button class="'+control_id+' singlecell_button ui-widget ui-state-default ui-corner-all" id="'+control_id+'_'+i+'"<span>'+escape(value_labels[i])+'</span></button></td>';
			$("#"+control_id+"_"+i).live("mouseenter", (function(i,control_id) {return function(e) {
			    $("#"+control_id+"_"+i).addClass("ui-state-hover");
			}}(i,control_id)));
			$("#"+control_id+"_"+i).live("mouseleave", (function(i,control_id) {return function(e) {
			    $("#"+control_id+"_"+i).removeClass("ui-state-hover");
			}}(i,control_id)));
			$("#"+control_id+"_"+i).live("mousedown", (function(i,control_id) {return function(e) {
			    $("#"+control_id+"_"+i).addClass("ui-state-active");
			}}(i,control_id)));
			$("#"+control_id+"_"+i).live("mouseup", (function(i,control_id) {return function(e) {
			    $("#"+control_id+"_"+i).removeClass("ui-state-active");
			    $("#"+control_id+"_value").val(values[i]).change();
			}}(i,control_id)));
		    }
		    inner_table += "</tr>";
		}
		inner_table +="</tbody></table>";
		var html_code = inner_table + "<input type='hidden' id='"+control_id+"_value' class='"+id+"' value='None'>";
		addRow(table, label, name, html_code, control_id);

		$(table).find("."+control_id).css("width",this.controls[name].width);

		break;
	    }
	}
	this.element[0].appendChild(table);
    }
})();

var escape = function(s) {
    return $('<div></div>').text(s).html();
}