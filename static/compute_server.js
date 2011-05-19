function add_args() {
    var args=Array.prototype.slice.call(arguments);
    var f=args.shift();
    return function() {
	var args2=Array.prototype.slice.call(arguments);
	return f.apply(null,args2.concat(args));
    };
}

sequences={};

function send_computation_success(data, textStatus, jqXHR, n) {
    $("#cid"+n).text(data.computation_id);
    // start long-polling to get the output
    // TODO: look at maybe using something like https://github.com/RobertFischer/JQuery-PeriodicalUpdater/
    sequences[data.computation_id]=0;
    get_output(data.computation_id, n);
}

function get_output(id, n) {
    $.getJSON($URL.output_poll, {computation_id: id, sequence: sequences[0]},
	      add_args(get_output_success,id,n));
}

function get_output_success(data, textStatus, jqXHR, id, n) {
    var done=false;
    if(data!==undefined && data.content!==undefined) {
        var content = data.content;
	var output = $("#output"+n);
        for (var i = 0; i < content.length; i++) {
            msg=content[i];
            if(msg.sequence!==sequences[id]) {
                //TODO: Make a big warning sign
                console.log('sequence is out of order; I think it should be '+sequences[id]+', but server claims it is '+msg.sequence);
            }
            sequences[id]+=1;
            // Handle each stream type.  This should probably be separated out into different functions.
	    switch(msg.msg_type) {
	    case 'stream': 
                output.append("<pre class='"+msg.content.name+"'>"+msg.content.data+"</pre>");
		break;

	    case 'pyout':
                output.append("<pre class='pyout'>"+msg.content.data['text/plain']+"</pre>");
		break;

	    case 'display_data':
                if(msg.content.data['image/svg+xml']!==undefined) {
                    output.append('<object id="svgImage" type="image/svg+xml">'+msg.content.data['image/svg+xml']+'</object>');
                } else if(msg.content.data['text/html']!==undefined) {
		    output.append('<div>'+msg.content.data['text/html']+'</div>');
		}
		break;

	    case 'pyerr':
		output.append("<pre>"+colorize(msg.content.traceback.join("\n").replace(/</g,"&lt;"))+"</pre>");
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
		    output.append(html);
		    break;
		case "comp_end":
		    sequence=0;
		    done=true;
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
        setTimeout(function() {get_output(id,n);}, 2000);
    }
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
    for(var i=0; i<=text.length; i++) {
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

editors=[]

function makeSingleCellBlock(span) {
    var n=editors.length;
    span.append("<textarea id=\"text"+n+"\"></textarea>"+
		"<p id=\"completions"+n+"\"></p>"+
		"Computation ID: <span id=\"cid"+n+"\"></span><br>"+
		"<input type=\"button\" value=\"Evaluate\" id=\"eval"+n+"\"><br>"+
		"<span id=\"output"+n+"\"></span><hr>");
    editors.push(CodeMirror.fromTextArea($("#text"+n)[0], {
	mode:"python",
	indentUnit:4,
	tabMode:"shift",
	lineNumbers:true,
	onKeyEvent:add_args(handleKeyEvent,n)}))
    editors[n].setValue("");
    editors[n].focus();
    $("#eval"+n).click(function(){
	$.getJSON($URL.evaluate, {commands: editors[n].getValue()},
		  add_args(send_computation_success,n));
    });
}

function add_cell() {
    var n=editors.length;
    $("#cell"+(n-1)).after("<span id=\"cell"+n+"\"></span>");
    makeSingleCellBlock($("#cell"+n));
}

$(document).ready(function(){
    makeSingleCellBlock($("#cell0"));
    $("#add_cell").click(add_cell);
});