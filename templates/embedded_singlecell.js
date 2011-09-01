
(function($) {
// Make a global singlecell namespace for our functions
window.singlecell = {};

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

singlecell.singlecell_dependencies_callback = (function() {
    window.singlecell_dependencies=true;
    if (singlecell.init_callback !== undefined) {
	singlecell.init_callback();
    }
});


singlecell.makeSinglecell = (function(args) {
    if (typeof args === "undefined") {
	args = {};
    }

    // Args:
    var template = args.template;
    var inputLocation = args.inputLocation;
    var outputLocation = args.outputLocation;
    var code = args.code;
    var evalButtonText = args.evalButtonText;
    var hide = args.hide;
    var editor = args.editor;
    var sageMode = args.sageMode;
    var replaceOutput = args.replaceOutput;

    if (typeof template !== "undefined") {
	if (typeof evalButtonText === "undefined") {
	    evalButtonText = template.evalButtonText;
	}
	if (typeof editor === "undefined") {
	    editor = template.editor;
	}
	if (typeof hide === "undefined") {
	    hide = template.hide;
	} else {
	    for (var i = 0, i_max = template.hide.length; i < i_max; i++) {
		hide.push(template.hide[i]);
	    }
	}
	if (typeof sageMode === "undefined") {
	    sageMode = template.sageMode;
	}
	if (typeof replaceOutput === "undefined") {
	    replaceOutput = template.replaceOutput;
	}
    }

    // default arguments
    if (typeof inputLocation === "undefined") {
	throw "Must specify an inputLocation"
    }
    
    if (typeof outputLocation === "undefined") {
	outputLocation = inputLocation;
    }

    if (typeof hide === "undefined") {
	hide = [];
    }

    if (typeof editor === "undefined") {
	editor = "codemirror";
    }

    if (typeof code === "undefined") {
	code = $(inputLocation).text();
	// delete the text
	$(inputLocation).text("");
    }

    if (typeof evalButtonText === "undefined") {
	evalButtonText = "Evaluate";
    }
    
    if (typeof sageMode === "undefined") {
	sageMode = true;
    }

    if (typeof replaceOutput === "undefined") {
	replaceOutput = false;
    }

    var singlecellInfo = {"inputLocation": inputLocation,
			  "outputLocation": outputLocation,
			  "code": code,
			  "editor": editor,
			  "replaceOutput": replaceOutput,
			  "sageMode": sageMode};

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
		$(inputLocation).html(body);
		$(inputLocation+" .singlecell_commands").text(code);
		if (inputLocation !== outputLocation) {
		    $(inputLocation+" .singlecell_output, .singlecell_messages").appendTo(outputLocation);
		}
		for (var i = 0, i_max = hide.length; i < i_max; i++) {
		    if (hide[i] === 'editor' || 
			hide[i] === 'editorToggle' || 
			hide[i] === 'files' || 
			hide[i] ==='evalButton' || 
			hide[i] ==='sageMode') {
			$(inputLocation+" .singlecell_"+hide[i]).css("display", "none");
		    } else if (hide[i] ==='output' || 
			       hide[i] ==='computationID' || 
			       hide[i] ==='messages') {
			$(outputLocation+" .singlecell_"+hide[i]).css("display", "none");
		    }
		}
		if (evalButtonText !== undefined) {
		    $(inputLocation+ " .singlecell_evalButton").val(evalButtonText);
		}
		singlecell.initCell(singlecellInfo);
	    });
	}
    }, 100);
    return singlecellInfo;
});

singlecell.initCell = (function(singlecellInfo) {
//Strips all special characters
    var inputLocationName = singlecellInfo.inputLocation.replace(/[\!\"\#\$\%\&\'\(\)\*\+\,\.\/\:\;\\<\=\>\?\@\[\\\]\^\`\{\|\}\~\s]/gmi, "");
    var inputLocation = $(singlecellInfo.inputLocation);
    var outputLocation = $(singlecellInfo.outputLocation);
    var editor = singlecellInfo.editor;
    var replaceOutput = singlecellInfo.replaceOutput;
    var sageMode = inputLocation.find(".singlecell_sageModeCheck");
    var textArea = inputLocation.find(".singlecell_commands");
    var files = 0;
    var editorData, temp;

    if (singlecellInfo.code !== undefined) {
	textArea.val(singlecellInfo.code);
    }

    if (! singlecellInfo.sageMode) {
	sageMode.attr("checked", false);
    }

    try {
	if (textArea.val().length == 0 && sessionStorage[inputLocationName+"_editorValue"]) {
	    textArea.val(sessionStorage.getItem(inputLocationName+"_editorValue"));
	}
	if (sessionStorage[inputLocationName+"_sageModeCheck"]) {
	    sageMode.attr("checked", sessionStorage.getItem(inputLocationName+"_sageModeCheck")=="true");
	}
	sageMode.change(function(e) {
	    sessionStorage.setItem(inputLocationName+"_sageModeCheck",$(e.target).attr("checked"));
	});
    } catch(e) {}

    temp = this.renderEditor(editor, inputLocation);
    editor = temp[0];
    editorData = temp[1];

    $(document.body).append("<form class='singlecell_form' id='"+inputLocationName+"_form'></form>");
    $("#"+inputLocationName+"_form").attr({"action": $URL.evaluate,
				"enctype": "multipart/form-data",
				"method": "POST"
			       });

    inputLocation.find(".singlecell_editorToggle").click(function(){
	temp = singlecell.toggleEditor(editor, editorData, inputLocation);
	editor = temp[0];
	editorData = temp[1];
	return false;
    });
    inputLocation.find(".singlecell_addFile").click(function(){
	inputLocation.find(".singlecell_fileUpload").append("<div class='singlecell_fileInput'><a class='singlecell_removeFile' href='#' style='text-decoration:none' onClick='$(this).parent().remove(); return false;'>[-]</a>&nbsp;&nbsp;&nbsp;<input type='file' id='"+inputLocationName+"_file"+files+"' name='file'></div>");
	files++;
	return false;
    });
    inputLocation.find(".singlecell_clearFiles").click(function() {
	files = 0;
	$("#"+inputLocationName+"_form").empty();
	inputLocation.find(".singlecell_fileUpload").empty();
	return false;
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
    
    inputLocation.find(".singlecell_evalButton").click(function() {
	// TODO: actually make the JSON execute request message here.

	if (replaceOutput) {
	    inputLocation.find(".singlecell_output").empty();
	}

	var session = new Session(outputLocation, ".singlecell_output", inputLocation.find(".singlecell_sageModeCheck").attr("checked"));
	inputLocation.find(".singlecell_computationID").append("<div>"+session.session_id+"</div>");
	$("#"+inputLocationName+"_form").append("<input type='hidden' name='commands'>").children().last().val(JSON.stringify(textArea.val()));
	$("#"+inputLocationName+"_form").append("<input name='session_id' value='"+session.session_id+"'>");
	$("#"+inputLocationName+"_form").append("<input name='msg_id' value='"+uuid4()+"'>");
	inputLocation.find(".singlecell_sageModeCheck").clone().appendTo($("#"+inputLocationName+"_form"));
	inputLocation.find(".singlecell_fileInput").appendTo($("#"+inputLocationName+"_form"));
	$("#"+inputLocationName+"_form").attr("target", "singlecell_serverResponse_"+session.session_id);
	inputLocation.append("<iframe style='display:none' name='singlecell_serverResponse_"+session.session_id+"' id='singlecell_serverResponse_"+session.session_id+"'></iframe>");
	$("#"+inputLocationName+"_form").submit();
	$("#"+inputLocationName+"_form").find(".singlecell_fileInput").appendTo(inputLocation.find(".singlecell_fileUpload"));
	$("#"+inputLocationName+"_form").empty();
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
    $(singlecellInfo.inputLocation).remove();
    $(singlecellInfo.outputLocation).remove();
});

singlecell.moveInputForm = (function(singlecellInfo) {
    $(document.body).append("<div id='singlecell_moved' style='display:none'></div>");
    $(singlecellInfo.inputLocation).contents().appendTo("#singlecell_moved");
});

singlecell.restoreInputForm = (function(singlecellInfo) {
    $("#singlecell_moved").contents().appendTo(singlecellInfo.inputLocation);
    $("#singlecell_moved").remove();
});

singlecell.renderEditor = (function(editor, inputLocation) {
    var editorData;

    if (editor === "textarea") {
	editorData = editor;
    } else if (editor === "textarea-readonly") {
	editorData = editor;
	inputLocation.find(".singlecell_commands").attr("readonly", "readonly");
    } else {
	var readOnly = false;
	if (editor == "codemirror-readonly") {
	    readOnly = true;
	} else {
	    editor = "codemirror";
	}

	editorData = CodeMirror.fromTextArea(inputLocation.find(".singlecell_commands").get(0), {
	    mode:"python",
	    indentUnit:4,
	    tabMode:"shift",
	    lineNumbers:true,
	    matchBrackets:true,
	    readOnly: readOnly,
	    onKeyEvent: (function(editor, event){
		if (event.which === 13 && event.shiftKey && event.type === "keypress") {
		    inputLocation.find(".singlecell_evalButton").click();
		    event.stop();
		    return true;
		}
		editor.save();
		try {
		    sessionStorage.removeItem(inputLocationName+"_editorValue");
		    sessionStorage.setItem(inputLocationName+"_editorValue", inputLocation.find(".singlecell_commands").val());
		} catch (e) {
		    // if we can't store, don't do anything, e.g. if cookies are blocked
		}
	    })
	});
    }

    return [editor, editorData];
});

singlecell.toggleEditor = (function(editor, editorData, inputLocation) {
    var editable = ["textarea", "codemirror"];
    var temp;

    if ($.inArray(editor, editable) !== -1) {
	if (editor === "codemirror") {
	    editorData.toTextArea();
	    editor = editorData = "textarea";
	} else {
	    editor = "codemirror";
	    temp = this.renderEditor(editor, inputLocation);
	    editorData = temp[1];
	}
    } else {
	if (editor === "codemirror-readonly") {
	    editorData.toTextArea();
	    editor = "textarea-readonly";
	    temp = this.renderEditor(editor, inputLocation);
	    editorData = temp[1];
	} else {
	    editor = "codemirror-readonly";
	    temp = this.renderEditor(editor, inputLocation);
	    editorData = temp[1];
	}
    }

    return [editor, editorData];
});

singlecell.templates = {
    "minimal": { // for an evaluate button and nothing else.
	"editor": "textarea-readonly",
	"hide": ["computationID", "editor", "editorToggle", "files",
		 "messages", "sageMode"],
	"replaceOutput": true
    },
    "restricted": { // to display/evaluate code that can't be edited.
	"editor": "codemirror-readonly",
	"hide": ["computationID", "editorToggle", "files", "messages",
		 "sageMode"],
	"replaceOutput": true
    }
};


// Make the script root available to jquery
$URL={'root': {{ request.url_root|tojson|safe }},
      'evaluate': {{url_for('evaluate',_external=True)|tojson|safe}},
      'output_poll': {{url_for('output_poll',_external=True)|tojson|safe}} +
          '?callback=?',
      'output_long_poll': {{url_for('output_long_poll',_external=True)|tojson|safe}}
     };
})(jQuery);
