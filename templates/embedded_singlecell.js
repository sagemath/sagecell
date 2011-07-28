var singlecell = {};

singlecell.init = (function() {
    var load = function ( config ) {
	// We can't use the jquery .append to load javascript because then the script tag disappears.  At least mathjax depends on the script tag 
	// being around later to get the mathjax path.  See http://stackoverflow.com/questions/610995/jquery-cant-append-script-element.
        var script = document.createElement( 'script' );
	if (config.type!==undefined) {
	    script.type = config.type
	} else {
	    script.type="text/javascript"
	}
	if (config.src!==undefined) { script.src = config.src; }
	if (config.text!==undefined) {script.text = config.text;}

	document.head.appendChild(script);
    };

    load({'text': 'MathJax.Hub.Config({  extensions: ["jsMath2jax.js"]});', 
	  'type': 'text/x-mathjax-config'});
    var scripts=[
	{%- for (script,params) in scripts -%}
	"{{- url_for('static',filename=script,_external=True, **params) -}}",
	{%- endfor -%}]
    for(var i = 0; i < scripts.length; i++) {
	console.log('got '+scripts[i]);
	load({'src': scripts[i]});
    }

    var stylesheets=[
	{%- for stylesheet in stylesheets -%}
	"{{- url_for('static',filename=stylesheet,_external=True) -}}",
	{%- endfor -%}];
    for(var i = 0; i < stylesheets.length; i++) {
	$("head").append("<link rel='stylesheet' href='"+stylesheets[i]+"'></script>");
    }
});

singlecell.makeSinglecell = (function(args) {
    if (typeof args === "undefined") {
	args = {};
    }
    var inputDiv = args.inputDiv,
    outputDiv = args.outputDiv,
    files = args.files,
    messages = args.messages,
    computationID = args.computationID;

    if (typeof inputDiv === "undefined") {
	inputDiv = "#singlecell";
    }
    
    if (typeof outputDiv === "undefined") {
	outputDiv = inputDiv;
    }

    if (typeof files !== "boolean") {
	files = true;
    }
    if (typeof messages !== "boolean") {
	messages = true;
    }
    if (typeof computationID !== "boolean") {
	computationID = true;
    }
    
    var singlecellInfo = {"inputDiv": inputDiv, "outputDiv": outputDiv};
    var body = {% filter tojson %}{% include "singlecell.html" %}{% endfilter %};
    setTimeout(function() {
	// Wait for CodeMirror to load before using the $ function
	if (typeof CodeMirror === "undefined") {
	    setTimeout(arguments.callee, 100);
	    return false;
	} else {
	    $(function() {
		$(inputDiv).html(body);
		if (inputDiv !== outputDiv) {
		    $(inputDiv+" .singlecell_output, .singlecell_messages").appendTo(outputDiv);
		}
		if (messages === false) {
		    $(outputDiv+" .singlecell_messages").css("display","none");
		}
		if (computationID === false) {
		    $(inputDiv+" .singlecell_computationID").css("display","none");
		}
		if (files === false) {
		    $(inputDiv+" .singlecell_files").css("display","none");
		}
		singlecell.initCell(singlecellInfo);
	    });
	}
    }, 100);
    return singlecellInfo;
});

singlecell.initCell = (function(singlecellInfo) {
//Strips all special characters
    var inputDivName = singlecellInfo.inputDiv.replace(/[\!\"\#\$\%\&\'\(\)\*\+\,\.\/\:\;\\<\=\>\?\@\[\\\]\^\`\{\|\}\~\s]/gmi, "");
    var inputDiv = $(singlecellInfo.inputDiv);
    var outputDiv = $(singlecellInfo.outputDiv);

    var editor = CodeMirror.fromTextArea(inputDiv.find(".singlecell_commands").get(0),{
	mode:"python",
	indentUnit:4,
	tabMode:"shift",
	lineNumbers:true,
	matchBrackets:true,
	onKeyEvent: (function(editor, event){
	    if (event.which === 13 && event.shiftKey && event.type === "keypress") {
		inputDiv.find(".singlecell_evalButton").click();
		event.stop();
		return true;
	    }
	    try {
		sessionStorage.removeItem(inputDivName+"_editorValue");
		sessionStorage.setItem(inputDivName+"_editorValue", editor.getValue());
	    } catch (e) {
		// if we can't store, don't do anything, e.g. if cookies are blocked
	    }
	})
    });
    try {
	if (sessionStorage[inputDivName+"_editorValue"]) {
	    editor.setValue(sessionStorage.getItem(inputDivName+"_editorValue"));
	}
	if (sessionStorage[inputDivName+"_sageMode"]) {
	    inputDiv.find(".singlecell_sageMode").attr("checked", sessionStorage.getItem(inputDivName+"_sageMode")=="true");
	}
	inputDiv.find(".singlecell_sageMode").change(function(e) {
	    sessionStorage.setItem(inputDivName+"_sageMode",$(e.target).attr("checked"));
	});
    } catch(e) {}
    editor.focus();
    
    var files = 0;
    
    $(document.body).append("<form class='singlecell_form' id='"+inputDivName+"_form'></form>");
    $("#"+inputDivName+"_form").attr({"action": $URL.evaluate,
				"enctype": "multipart/form-data",
				"method": "POST"
			       });
    inputDiv.find(".singlecell_addFile").click(function(){
	inputDiv.find(".singlecell_fileUpload").append("<div class='singlecell_fileInput'><a class='singlecell_removeFile' href='#' style='text-decoration:none' onClick='$(this).parent().remove()'>[-]</a>&nbsp;&nbsp;&nbsp;<input type='file' id='"+inputDivName+"_file"+files+"' name='file'></div>");
	files++;
    });
    inputDiv.find(".singlecell_clearFiles").click(function() {
	files = 0;
	$("#"+inputDivName+"_form").empty();
	inputDiv.find(".singlecell_fileUpload").empty();
    });
    
    $(".singlecell_selectorButton").live("hover",function(e) {
	$(e.target).toggleClass("ui-state-hover");
    });
    $(".singlecell_selectorButton").live("focus",function(e) {
	$(e.target).toggleClass("ui-state-focus");
    });
    $(".singlecell_selectorButton").live("blur",function(e) {
	$(e.target).removeClass("ui-state-focus");
    });
    
    inputDiv.find(".singlecell_evalButton").click(function() {
	var session = new Session(outputDiv, ".singlecell_output", inputDiv.find(".singlecell_sageMode").attr("checked"));
	inputDiv.find(".singlecell_computationID").append("<div>"+session.session_id+"</div>");
	$("#"+inputDivName+"_form").append("<input type='hidden' name='commands'>").children().last().val(editor.getValue());
	$("#"+inputDivName+"_form").append("<input name='session_id' value='"+session.session_id+"'>");
	$("#"+inputDivName+"_form").append("<input name='msg_id' value='"+uuid4()+"'>");
	inputDiv.find(".singlecell_sageMode").clone().appendTo($("#"+inputDivName+"_form"));
	inputDiv.find(".singlecell_fileInput").appendTo($("#"+inputDivName+"_form"));
	$("#"+inputDivName+"_form").attr("target", "singlecell_serverResponse_"+session.session_id);
	inputDiv.append("<iframe style='display:none' name='singlecell_serverResponse_"+session.session_id+"' id='singlecell_serverResponse_"+session.session_id+"'></iframe>");
	$("#"+inputDivName+"_form").submit();
	$("#"+inputDivName+"_form").find(".singlecell_fileInput").appendTo(inputDiv.find(".singlecell_fileUpload"));
	$("#"+inputDivName+"_form").empty();
	$("#singlecell_serverResponse_"+session.session_id).load($.proxy(function(event) {
	    // if the hosts are the same, communication between frames
	    // is allowed
	    // Instead of using a try/except block, we use an if to work 
	    // around a bug in Webkit documented at
	    // http://code.google.com/p/chromium/issues/detail?id=17325
	    if ($URL.root === (location.protocol+'//'+location.host+'/')) {
		var server_response = $("#singlecell_serverResponse_"+session.session_id).contents().find("body").html();
		if (server_response !== "") {
		    session.output(server_response);
		    session.clearQuery();
		}
	    }
	    $("#singlecell_serverResponse_"+session.session_id).unbind();
	}), session);
	return false;
    });
    return singlecellInfo;
});

singlecell.deleteSinglecell = (function(singlecellInfo) {
    $(singlecellInfo.inputDiv).remove();
    $(singlecellInfo.outputDiv).remove();
});

singlecell.moveInputForm = (function(singlecellInfo) {
    $(document.body).append("<div id='singlecell_moved' style='display:none'></div>");
    $(singlecellInfo.inputDiv).contents().appendTo("#singlecell_moved");
});

singlecell.restoreInputForm = (function(singlecellInfo) {
    $("#singlecell_moved").contents().appendTo(singlecellInfo.inputDiv);
    $("#singlecell_moved").remove();
});

// Make the script root available to jquery
$URL={'root': {{ request.url_root|tojson|safe }},
      'evaluate': {{url_for('evaluate',_external=True)|tojson|safe}},
      'output_poll': {{url_for('output_poll',_external=True)|tojson|safe}} +
          '?callback=?',
      'output_long_poll': {{url_for('output_long_poll',_external=True)|tojson|safe}}
     };
