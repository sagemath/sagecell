var singlecell = {};

singlecell.init = (function() {
    document.head || (document.head = document.getElementsByTagName('head')[0]);
    var scripts=[
	{%- for script in scripts -%}
	"{{- url_for('static',filename=script,_external=True) -}}",
	{%- endfor -%}];
    for(var i=0; i<scripts.length; i++) {
	var s=document.createElement("script");
	s.setAttribute("type","text/javascript");
	s.setAttribute("src",scripts[i]);
	document.head.appendChild(s);
    }
    var stylesheets=[
	{%- for stylesheet in stylesheets -%}
	"{{- url_for('static',filename=stylesheet,_external=True) -}}",
	{%- endfor -%}];
    for(var i=0; i<stylesheets.length; i++) {
	var s=document.createElement("link");
	s.setAttribute("rel","stylesheet");
	s.setAttribute("href",stylesheets[i]);
	document.head.appendChild(s);
    }
    return true;
})

singlecell.deleteSinglecell = (function(singlecellInfo) {
    $(singlecellInfo.inputDiv).remove();
    $(singlecellInfo.outputDiv).remove();
});

singlecell.makeSinglecell = (function(args) {
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
	// Wait for jQuery to load before using the $ function
	if (typeof jQuery === "undefined") {
	    setTimeout(arguments.callee, 100);
	    return false;
	} else {
	    $(function() {
		$.ajaxSetup({'dataType':'jsonp'});
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
/*
function handleEditorKeyEvent(editor,event) {
    if (event.which === 13 && event.shiftKey && event.type === "keypress") {
	inputDiv.find(".evalButton").click();
	event.stop();
	return true;
    }
    if (window.sessionStorage) {
	try {
	    sessionStorage.removeItem(inputDivID+"_editorValue");
	    sessionStorage.setItem(inputDivID+"_editorValue", editor.getValue());
	} catch (e) {
	    // if we can't store, we don't do anything
	    // for example, in chrome if we block cookies, we can't store.
	}
    }
}
*/
singlecell.initCell = (function(singlecellInfo) {
    var inputDivID = singlecellInfo.inputDiv.replace("\#","");
    var outputDivID = singlecellInfo.outputDiv.replace("\#","");
    var inputDiv = $(singlecellInfo.inputDiv);
    var outputDiv = $(singlecellInfo.outputDiv);

    var editor = CodeMirror.fromTextArea(inputDiv.find(".singlecell_commands").get(0),{
	mode:"python",
	indentUnit:4,
	tabMode:"shift",
	lineNumber:true,
	matchBrackets:true,
	/*onKeyEvent:handleEditorKeyEvent()*/
    });
    try {
	if (sessionStorage[inputDivID+"_editorValue"]) {
	    editor.setValue(sessionStorage.getItem(inputDivID+"_editorValue"));
	}
	if (sessionStorage[inputDivID+"_sageMode"]) {
	    inputDiv.find(".singlecell_sageMode").attr("checked", sessionStorage.getItem(inputDivID+"_sageMode")=="true");
	}
	inputDiv.find(".singlecell_sageMode").change(function(e) {
	    sessionStorage.setItem(inputDivID+"_sageMode",$(e.target).attr("checked"));
	});
    } catch(e) {}
    editor.focus();
    
    var files = 0;
    
    $(document.body).append("<form class='singlecell_form' id='"+inputDivID+"_form'></form>");
    $("#"+inputDivID+"_form").attr({"action": $URL.evaluate,
				"enctype": "multipart/form-data",
				"method": "POST"
			       });
    inputDiv.find(".singlecell_addFile").click(function(){
	inputDiv.find(".singlecell_fileUpload").append("<div class='singlecell_fileInput'><a class='singlecell_removeFile' href='#' style='text-decoration:none' onClick='$(this).parent().remove()'>[-]</a>&nbsp;&nbsp;&nbsp;<input type='file' id='"+inputDivID+"file"+files+"' name='file'></div>");
	files++;
    });
    inputDiv.find(".singlecell_clearFiles").click(function() {
	files = 0;
	$("#"+inputDivID+"_form").empty();
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
	$("#"+inputDivID+"_form").append("<input type='hidden' name='commands'>").children().last().val(editor.getValue());
	$("#"+inputDivID+"_form").append("<input name='session_id' value='"+session.session_id+"'>");
	$("#"+inputDivID+"_form").append("<input name='msg_id' value='"+uuid4()+"'>");
	inputDiv.find(".singlecell_sageMode").clone().appendTo($(inputDivID+"_form"));
	inputDiv.find(".singlecell_fileUpload .singlecell_fileInput").appendTo($(inputDivID+"_form"));
	$("#"+inputDivID+"_form").attr("target", "singlecell_serverResponse_"+session.session_id);
	inputDiv.append("<iframe style='display:none' name='singlecell_serverResponse_"+session.session_id+"' id='singlecell_serverResponse_"+session.session_id+"'></iframe>");
	$("#"+inputDivID+"_form").submit();
	$("#"+inputDivID+"_form").find(".singlecell_fileInput").appendTo(inputDiv.find(".singlecell_fileUpload"));
	$("#"+inputDivID+"_form").empty();
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
