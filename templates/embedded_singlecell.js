
var singlecell = {};

singlecell.init = (function(callback) {
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
	document.getElementsByTagName("head")[0].appendChild(script);
    };

    singlecell.init_callback = callback

    // many stylesheets that have been smashed together into all.min.css
    $("head").append("<link rel='stylesheet' href='{{- url_for('static', filename='all.min.css', _external=True) -}}'></link>");
    $("head").append("<link rel='stylesheet' href='{{- url_for('static', filename='jqueryui/css/sage/jquery-ui-1.8.13.custom.css', _external=True) -}}'></link>");
    $("head").append("<link rel='stylesheet' href='{{- url_for('static', filename='colorpicker/css/colorpicker.css', _external=True) -}}'></link>");

    // Mathjax.  We need a separate script tag for mathjax since it later comes back and looks at the script tag.
    load({'text': 'MathJax.Hub.Config({  ' +
	  'extensions: ["jsMath2jax.js", "tex2jax.js"],' + 
	  'tex2jax: {' +
	  ' inlineMath: [ ["$","$"], ["\\\\(","\\\\)"] ],' +
	  ' displayMath: [ ["$$","$$"], ["\\\\[","\\\\]"] ],' +
	  ' processEscapes: true}' +
	  '});', 'type': 'text/x-mathjax-config'});
    load({'src': "{{- url_for('static',filename='mathjax/MathJax.js', _external=True, config='TeX-AMS-MML_HTMLorMML') -}}"});

    // many prerequisites that have been smashed together into all.min.js
    load({'src': "{{- url_for('static', filename='all.min.js', _external=True) -}}"});
});

var singlecell_dependencies_callback = function() {
    singlecell_dependencies=true;     
    if (singlecell.init_callback !== undefined) {
	singlecell.init_callback();
    }
};




singlecell.makeSinglecell = (function(args) {
    if (typeof args === "undefined") {
	args = {};
    }
    // Args:

    var inputDiv = args.inputDiv;
    var outputDiv = args.outputDiv;
    var hide = args.hide;
    // 'editor', 'files', 'evalButton', 'sageMode', 'output', 'computationID', 'messages'
    var code = args.code;
    var evalButtonText = args.evalButtonText;
    var editor = args.editor;
    
    // default arguments
    if (typeof inputDiv === "undefined") {
	throw "Must specify an inputDiv"
    }
    
    if (typeof outputDiv === "undefined") {
	outputDiv = inputDiv;
    }

    if (typeof hide === "undefined") {
	hide = [];
    }

    if (typeof editor === "undefined") {
	editor = true;
    }

    if (typeof code === "undefined") {
	code = $(inputDiv).text();
	// delete the text
	$(inputDiv).text("");
    }

    if (typeof evalButtonText === "undefined") {
	evalButtonText = "Evaluate";
    }
    
    var singlecellInfo = {"inputDiv": inputDiv, "outputDiv": outputDiv, "code": code, "editor": editor};
    var body = {% filter tojson %}{% include "singlecell.html" %}{% endfilter %};
    setTimeout(function() {
	// Wait for CodeMirror to load before using the $ function
	// Could we use MathJax Queues for this?
	// We have to do something special here since Codemirror is loaded dynamically,
	// so it may not be ready even though the page is loaded and ready.
	if (typeof singlecell_dependencies === "undefined") {
	    setTimeout(arguments.callee, 100);
	    return false;
	} else {
	    $(function() {
		$(inputDiv).html(body);
		$(inputDiv+" .singlecell_commands").text(code);
		if (inputDiv !== outputDiv) {
		    $(inputDiv+" .singlecell_output, .singlecell_messages").appendTo(outputDiv);
		}
		for (var i = 0, i_max = hide.length; i < i_max; i++) {
		    if (hide[i] === 'editor' || 
			hide[i] === 'editorToggle' || 
			hide[i] === 'files' || 
			hide[i] ==='evalButton' || 
			hide[i] ==='sageMode') {
			$(inputDiv+" .singlecell_"+hide[i]).css("display", "none");
		    } else if (hide[i] ==='output' || 
			       hide[i] ==='computationID' || 
			       hide[i] ==='messages') {
			$(outputDiv+" .singlecell_"+hide[i]).css("display", "none");
		    }
		}
		if (evalButtonText !== undefined) {
		    $(inputDiv+ " .singlecell_evalButton").val(evalButtonText);
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
    var editor = singlecellInfo.editor;
    var textArea = inputDiv.find(".singlecell_commands");
    var files = 0;

    if (singlecellInfo.code !== undefined) {
	textArea.val(singlecellInfo.code);
    }

    try {
	if (textArea.val().length == 0 && sessionStorage[inputDivName+"_editorValue"]) {
	    textArea.val(sessionStorage.getItem(inputDivName+"_editorValue"));
	}
	if (sessionStorage[inputDivName+"_sageModeCheck"]) {
	    inputDiv.find(".singlecell_sageModeCheck").attr("checked", sessionStorage.getItem(inputDivName+"_sageModeCheck")=="true");
	}
	inputDiv.find(".singlecell_sageModeCheck").change(function(e) {
	    sessionStorage.setItem(inputDivName+"_sageModeCheck",$(e.target).attr("checked"));
	});
    } catch(e) {}

    if (editor !== false) {
	editor = this.renderEditor(inputDiv);
    }

    $(document.body).append("<form class='singlecell_form' id='"+inputDivName+"_form'></form>");
    $("#"+inputDivName+"_form").attr({"action": $URL.evaluate,
				"enctype": "multipart/form-data",
				"method": "POST"
			       });

    inputDiv.find(".singlecell_editorToggle").click(function(){
	if (editor === false) {
	    editor = singlecell.renderEditor(inputDiv);
	} else {
	    editor = singlecell.removeEditor(editor);
	}
    });
    inputDiv.find(".singlecell_addFile").click(function(){
	inputDiv.find(".singlecell_fileUpload").append("<div class='singlecell_fileInput'><a class='singlecell_removeFile' href='#' style='text-decoration:none' onClick='$(this).parent().remove(); return false;'>[-]</a>&nbsp;&nbsp;&nbsp;<input type='file' id='"+inputDivName+"_file"+files+"' name='file'></div>");
	files++;
	return false;
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
	// TODO: actually make the JSON execute request message here.
	var session = new Session(outputDiv, ".singlecell_output", inputDiv.find(".singlecell_sageModeCheck").attr("checked"));
	inputDiv.find(".singlecell_computationID").append("<div>"+session.session_id+"</div>");
	$("#"+inputDivName+"_form").append("<input type='hidden' name='commands'>").children().last().val(JSON.stringify(textArea.val()));
	$("#"+inputDivName+"_form").append("<input name='session_id' value='"+session.session_id+"'>");
	$("#"+inputDivName+"_form").append("<input name='msg_id' value='"+uuid4()+"'>");
	inputDiv.find(".singlecell_sageModeCheck").clone().appendTo($("#"+inputDivName+"_form"));
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

singlecell.renderEditor = (function(inputDiv) {
    editor = CodeMirror.fromTextArea(inputDiv.find(".singlecell_commands").get(0), {
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
	    editor.save();
	    try {
		sessionStorage.removeItem(inputDivName+"_editorValue");
		sessionStorage.setItem(inputDivName+"_editorValue", inputDiv.find(".singlecell_commands").val());
	    } catch (e) {
		// if we can't store, don't do anything, e.g. if cookies are blocked
	    }
	})
    });
    return editor;
});

singlecell.removeEditor = (function(editor) {
    editor.toTextArea();
    return false;
});


// Make the script root available to jquery
$URL={'root': {{ request.url_root|tojson|safe }},
      'evaluate': {{url_for('evaluate',_external=True)|tojson|safe}},
      'output_poll': {{url_for('output_poll',_external=True)|tojson|safe}} +
          '?callback=?',
      'output_long_poll': {{url_for('output_long_poll',_external=True)|tojson|safe}}
     };
