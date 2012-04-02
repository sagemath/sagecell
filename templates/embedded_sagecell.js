(function($) {
// Make a global sagecell namespace for our functions
window.sagecell = {};

if (!document.head) {
    document.head = document.getElementsByTagName("head")[0];
}

sagecell.init = function (callback) {
    if (sagecell.dependencies_loaded !== undefined)
        return;
    sagecell.init_callback = callback
    sagecell.dependencies_loaded = false;

    // many stylesheets that have been smashed together into all.min.css
    var stylesheets = [{{url_for("static", filename="all.min.css", _external=True)|tojson|safe}},
                       {{url_for("static", filename="jqueryui/css/sage/jquery-ui-1.8.17.custom.css", _external=True)|tojson|safe}},
                       {{url_for("static", filename="colorpicker/css/colorpicker.css", _external=True)|tojson|safe}}];
    for (var i = 0; i < stylesheets.length; i++) {
        document.head.appendChild(sagecell.functions.createElement("link",
                {rel: "stylesheet", href: stylesheets[i]}));
    }

    // Mathjax.  We need a separate script tag for mathjax since it later comes back and looks at the script tag.
    document.head.appendChild(sagecell.functions.createElement("script",
        {"type": "text/x-mathjax-config"},
        [document.createTextNode('MathJax.Hub.Config({ \
             extensions: ["jsMath2jax.js", "tex2jax.js"], \
             tex2jax: {inlineMath: [ ["$","$"], ["\\\\(","\\\\)"] ], \
                       displayMath: [ ["$$","$$"], ["\\\\[","\\\\]"] ], \
             }); \
             // SVG backend does not work for IE version < 9, so switch if the default is SVG \
             // if (MathJax.Hub.Browser.isMSIE && (document.documentMode||0) < 9) { \
             //     MathJax.Hub.Register.StartupHook("End Config",function () { \
             //         var settings = MathJax.Hub.config.menuSettings; \
             //         if (!settings.renderer) {settings.renderer = "HTML-CSS"} \
             //     }); \
             // }')]));
    // many prerequisites that have been smashed together into all.min.js
    document.head.appendChild(sagecell.functions.createElement("script",
        {"src": {{url_for('static', filename='all.min.js', _external=True)|tojson|safe}}}));
};

sagecell.sagecell_dependencies_callback = function () {
    sagecell.dependencies_loaded = true;
    if (sagecell.init_callback !== undefined) {
        sagecell.init_callback();
    }
};

sagecell.makeSagecell = function (args) {
    var defaults;
    var settings = {};
    if (args === undefined) {
        args = {};
    }
    if (args.inputLocation === undefined) {
        throw "Must specify an inputLocation!";
    }
    if (args.outputLocation === undefined) {
        args.outputLocation = args.inputLocation;
    }
    if (args.code === undefined) {
        if (args.codeLocation !== undefined) {
            args.code = $(args.codeLocation).html();
        } else {
            args.code = $(args.inputLocation).children("script").html();
        }
    }
    defaults = {"editor": "codemirror",
                "evalButtonText": "Evaluate",
                "hide": [],
                "replaceOutput": true,
                "sageMode": true};
    if (args.template !== undefined) {
        settings = $.extend(settings, defaults, args.template, args)
        if (args.template.hide !== undefined) {
            settings.hide.concat(args.template.hide);
        }
    } else {
        settings = $.extend(settings, defaults, args);
    }
    setTimeout(function waitForLoad() {
        // Wait for CodeMirror to load before using the $ function
        // Could we use MathJax Queues for this?
        // We have to do something special here since Codemirror is loaded dynamically,
        // so it may not be ready even though the page is loaded and ready.
        if (!sagecell.dependencies_loaded) {
            if (sagecell.dependencies_loaded === undefined) {
                sagecell.init();
            }
            setTimeout(waitForLoad, 100);
            return false;
        }
        var body = {% filter tojson %}{% include "sagecell.html" %}{% endfilter %};
        $(function() {
            var hide = settings.hide;
            var inputLocation = $(settings.inputLocation);
            var outputLocation = $(settings.outputLocation);
            var evalButtonText = settings.evalButtonText;

            inputLocation.html(body);
            inputLocation.find(".sagecell_commands").val(settings.code);
            if (inputLocation !== outputLocation) {
                inputLocation.find(".sagecell_output, .sagecell_messages")
                        .appendTo(outputLocation);
            }
            var hideAdvanced = {};
            var hideable = {"in": {"computationID": true, "editor": true,
                                   "editorToggle": true,  "files": true,
                                   "evalButton": true,    "sageMode": true},
                            "out": {"output": true,       "messages": true,
                                    "sessionTitle": true, "done": true,
                                    "sessionFiles": true, "sessionFilesTitle": true}};
            var hidden_out = [];
            for (var i = 0, i_max = hide.length; i < i_max; i++) {
                if (hideable["in"][hide[i]]) {
                    inputLocation.find(".sagecell_"+hide[i]).css("display", "none");
                    // TODO: make the advancedFrame an option to hide, then delete
                    // this hideAdvanced hack
                    if (hide[i] === 'files' || hide[i] === 'sageMode') {
                        hideAdvanced[hide[i]] = true;
                    }
                } else if (hideable["out"][hide[i]]) {
                    hidden_out.push(settings.outputLocation + " .sagecell_" + hide[i]);
                }
            }
            if (hideAdvanced.files && hideAdvanced.sageMode) {
                inputLocation.find(".sagecell_advancedFrame").css("display", "none");
            }
            if (hidden_out.length > 0) {
                document.head.appendChild(sagecell.functions.createElement("style", {},
                        [document.createTextNode(hidden_out.join(", ") +
                         " {display: none;}")]));
            }
            if (evalButtonText !== undefined) {
                inputLocation.find(".sagecell_evalButton").val(evalButtonText);
            }
            sagecell.initCell(settings);
	        });
    }, 100);
    return settings;
};

sagecell.initCell = (function(sagecellInfo) {
//Strips all special characters
    var inputLocationName = sagecellInfo.inputLocation.replace(/[\!\"\#\$\%\&\'\(\)\*\+\,\.\/\:\;\\<\=\>\?\@\[\\\]\^\`\{\|\}\~\s]/gmi, "");
    var inputLocation = $(sagecellInfo.inputLocation);
    var outputLocation = $(sagecellInfo.outputLocation);
    var editor = sagecellInfo.editor;
    var replaceOutput = sagecellInfo.replaceOutput;
    var sageMode = inputLocation.find(".sagecell_sageModeCheck");
    var textArea = inputLocation.find(".sagecell_commands");
    var files = 0;
    var editorData, temp;

    if (sagecellInfo.code !== undefined) {
        textArea.val(sagecellInfo.code);
    }
    if (! sagecellInfo.sageMode) {
        sageMode.attr("checked", false);
    }

    /* Saving the state and restoring it seems more confusing than necessary for new users.
       There also seems to be a bug; if the sage mode checkbox is unchecked, it seems that it defaults to that
       from then on.
    try {
        if (textArea.val().length == 0 && sessionStorage[inputLocationName+"_editorValue"]!== undefined) {
            textArea.val(sessionStorage.getItem(inputLocationName+"_editorValue"));
        }
        if (sessionStorage[inputLocationName+"_sageModeCheck"]!==undefined) {
            sageMode.attr("checked", sessionStorage.getItem(inputLocationName+"_sageModeCheck")===true);
        }
        sageMode.change(function(e) {
            sessionStorage.setItem(inputLocationName+"_sageModeCheck",$(e.target).attr("checked")==="checked");
        });
    } catch(e) {}
    */

    temp = this.renderEditor(editor, inputLocation);
    editor = temp[0];
    editorData = temp[1];

    this.submitForm = sagecell.functions.createElement("form",
            {"action": $URL.evaluate, "enctype": "multipart/form-data",
             "method": "POST"});
    this.submitForm.id = inputLocationName + "_form";
    document.body.appendChild(this.submitForm);

    inputLocation.find(".sagecell_editorToggle").click(function(){
        temp = sagecell.toggleEditor(editor, editorData, inputLocation);
        editor = temp[0];
        editorData = temp[1];
        return false;
    });

    inputLocation.find(".sagecell_advancedTitle").click(function() {
        inputLocation.find('.sagecell_advancedFields').slideToggle();
        return false;
    });

    inputLocation.find(".sagecell_addFile").click(function(){
        inputLocation.find(".sagecell_fileUpload").append("<div class='sagecell_fileInput'><a class='sagecell_removeFile' href='#' style='text-decoration:none' onClick='jQuery(this).parent().remove(); return false;'>[-]</a>&nbsp;&nbsp;&nbsp;<input type='file' id='"+inputLocationName+"_file"+files+"' name='file'></div>");
        files++;
        return false;
    });
    inputLocation.find(".sagecell_clearFiles").click(function() {
        files = 0;
        $("#"+inputLocationName+"_form").empty();
        inputLocation.find(".sagecell_fileUpload").empty();
        return false;
    });

    $(".sagecell_sageMode").find("label").live("click",function(e) {
        var location = $(this).parent().find("input");
        location.attr("checked", !location.attr("checked"));
    });
    
    $(".sagecell_selectorButton").live("hover", function (e) {
        $(e.target).addClass("ui-state-hover");
    });
    $(".sagecell_selectorButton").live("focus", function (e) {
        $(e.target).addClass("ui-state-focus");
    });
    $(".sagecell_selectorButton").live("blur", function (e) {
        $(e.target).removeClass("ui-state-focus");
    });

    sagecellInfo.submit = function() {
        // TODO: actually make the JSON execute request message here.
        if (replaceOutput) {
            outputLocation.find(".sagecell_output").empty();
        }
        var session = new sagecell.Session(outputLocation, ".sagecell_output", inputLocation.find(".sagecell_sageModeCheck").attr("checked"));
        inputLocation.find(".sagecell_computationID").append("<div>"+session.session_id+"</div>");
        if (editorData.save !== undefined) {editorData.save();}
        $("#"+inputLocationName+"_form").append("<input type='hidden' name='commands'>").children().last().val(JSON.stringify(textArea.val()));
        $("#"+inputLocationName+"_form").append("<input name='session_id' value='"+session.session_id+"'>");
        $("#"+inputLocationName+"_form").append("<input name='msg_id' value='"+sagecell.functions.uuid4()+"'>");
        inputLocation.find(".sagecell_sageModeCheck").clone().appendTo($("#"+inputLocationName+"_form"));
        inputLocation.find(".sagecell_fileInput").appendTo($("#"+inputLocationName+"_form"));
        $("#"+inputLocationName+"_form").attr("target", "sagecell_serverResponse_"+session.session_id);
        inputLocation.append("<iframe style='display:none' name='sagecell_serverResponse_"+session.session_id+"' id='sagecell_serverResponse_"+session.session_id+"'></iframe>");
        $("#"+inputLocationName+"_form").submit();
        $("#"+inputLocationName+"_form").find(".sagecell_fileInput").appendTo(inputLocation.find(".sagecell_fileUpload"));
        $("#"+inputLocationName+"_form").empty();
        $("#sagecell_serverResponse_"+session.session_id).load(function(event) {
            // if the hosts are the same, communication between frames
            // is allowed
            // Instead of using a try/except block, we use an if to work 
            // around a bug in Webkit documented at
            // http://code.google.com/p/chromium/issues/detail?id=17325
            if ($URL.root === (location.protocol+'//'+location.host+'/')) {
                var server_response = $("#sagecell_serverResponse_"+session.session_id).contents().find("body").html();
                if (server_response !== "") {
                    if (server_response.indexOf("Permalink")>=0) {
                        session.output(server_response+"<br/>");
                    } else {
                        session.output(server_response);
                        session.clearQuery();
                    }
                }
            }
            $("#sagecell_serverResponse_"+session.session_id).unbind();
        });
        return false;
    };

    inputLocation.find(".sagecell_evalButton").click(sagecellInfo.submit);
    if (sagecellInfo.code && sagecellInfo.autoeval) {
        sagecellInfo.submit();
    }
    return sagecellInfo;
});

sagecell.deleteSagecell = function (sagecellInfo) {
    $(sagecellInfo.inputLocation).remove();
    $(sagecellInfo.outputLocation).remove();
};

sagecell.moveInputForm = function (sagecellInfo) {
    var moved = sagecell.functions.createElement("div", {"id": "sagecell_moved"});
    moved.style.display = "none";
    $(document.body).append(moved);
    $(sagecellInfo.inputLocation).contents().appendTo($(moved));
};

sagecell.restoreInputForm = function (sagecellInfo) {
    var moved = $("#sagecell_moved");
    moved.contents().appendTo(sagecellInfo.inputLocation);
    moved.remove();
};

sagecell.renderEditor = function (editor, inputLocation) {
    var editorData;

    if (editor === "textarea") {
        editorData = editor;
    } else if (editor === "textarea-readonly") {
        editorData = editor;
        inputLocation.find(".sagecell_commands").attr("readonly", "readonly");
    } else {
        var readOnly = false;
        if (editor == "codemirror-readonly") {
            readOnly = true;
        } else {
            editor = "codemirror";
        }
        editorData = CodeMirror.fromTextArea(
            inputLocation.find(".sagecell_commands").get(0),
            {mode: "python",
             indentUnit: 4,
             tabMode: "shift",
             lineNumbers: true,
             matchBrackets: true,
             readOnly: readOnly,
             extraKeys: {'Shift-Enter': function (editor) {
                 editor.save();
                 inputLocation.find(".sagecell_evalButton").click();
             }},
             onKeyEvent: function (editor, event) {
                 editor.save();
                /* Saving state and restoring it seems more confusing for new users, so we're commenting it out for now.
                try {
                    sessionStorage.removeItem(inputLocationName+"_editorValue");
                    sessionStorage.setItem(inputLocationName+"_editorValue", inputLocation.find(".sagecell_commands").val());
                } catch (e) {
                    // if we can't store, don't do anything, e.g. if cookies are blocked
                }
                */
            }});
    }
    return [editor, editorData];
};

sagecell.toggleEditor = function (editor, editorData, inputLocation) {
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
};

sagecell.templates = {
    "minimal": { // for an evaluate button and nothing else.
        "editor": "textarea-readonly",
        "hide": ["computationID", "editor", "editorToggle", "files",
                 "messages", "sageMode", "sessionTitle", "done",
                 "sessionFilesTitle"],
        "replaceOutput": true
    },
    "restricted": { // to display/evaluate code that can't be edited.
        "editor": "codemirror-readonly",
        "hide": ["computationID", "editorToggle", "files", "messages",
                 "sageMode", "sessionTitle", "done", "sessionFilesTitle"],
        "replaceOutput": true
    }
};

// Various utility functions for the Single Cell Server
sagecell.functions = {
    // Create UUID4-compliant ID (based on stackoverflow answer)
    //http://stackoverflow.com/questions/105034/how-to-create-a-guid-uuid-in-javascript
    "uuid4": function() {
        var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx';
        return uuid.replace(/[xy]/g, function(c) {
            var r = Math.random()*16|0, v = c == 'x' ? r : (r&0x3|0x8);
            return v.toString(16);
        });
    },

    // MIT-licensed by John Resig
    // http://ejohn.org/blog/simple-class-instantiation/)
    "makeClass": function() {
        return function(args){
            if ( this instanceof arguments.callee ) {
                if ( typeof this.init == "function" )
                    this.init.apply( this, args.callee ? args : arguments );
            } else
                return new arguments.callee( arguments );
        };
    },

    // Colorize tracebacks
    "colorizeTB": (function(){
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
            for (var i = 0, i_max = text.length; i < i_max; i++) {
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
    })(),
    "createElement": function (type, args, children) {
        var node = document.createElement(type);
        for (var k in args) {
            if (args.hasOwnProperty(k)) {
                node.setAttribute(k, args[k]);
            }
        }
        if (children) {
            for (var i = 0; i < children.length; i++) {
                node.appendChild(children[i]);
            }
        }
        return node;
    }
};

// Make the script root available to jquery
$URL={'root': {{request.url_root|tojson|safe}},
      'evaluate': {{url_for('evaluate',_external=True)|tojson|safe}},
      'powered_by_img': {{url_for('static', filename = 'sagelogo.png', _external=True)|tojson|safe}},
      'output_poll': {{url_for('output_poll',_external=True)|tojson|safe}} +
          '?callback=?',
      'output_long_poll': {{url_for('output_long_poll',_external=True)|tojson|safe}}};

// Purely for backwards compability
window.singlecell = window.sagecell;
window.singlecell.makeSinglecell = window.singlecell.makeSagecell;
})(jQuery);
