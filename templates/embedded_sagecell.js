(function($) {
// Make a global sagecell namespace for our functions
window.sagecell = {};

if (!document.head) {
    document.head = document.getElementsByTagName("head")[0];
}

sagecell.init = function (callback) {
    if (sagecell.dependencies_loaded !== undefined)
        return;
    var load = function ( config ) {
        // We can't use the jquery .append to load javascript because then the script tag disappears.  At least mathjax depends on the script tag 
        // being around later to get the mathjax path.  See http://stackoverflow.com/questions/610995/jquery-cant-append-script-element.
        var script = document.createElement( 'script' );
        if (config.type!==undefined) {
            script.type = config.type;
        } else {
            script.type="text/javascript";
        }
        if (config.src!==undefined) { script.src = config.src; }
        if (config.text!==undefined) {script.text = config.text;}
        document.getElementsByTagName("head")[0].appendChild(script);
    };

    sagecell.init_callback = callback
    sagecell.dependencies_loaded = false;

    // many stylesheets that have been smashed together into all.min.css
    var stylesheets = [{{url_for(".static", filename="all.min.css", _external=True)|tojson|safe}},
                       {{url_for(".static", filename="jqueryui/css/sage/jquery-ui-1.8.17.custom.css", _external=True)|tojson|safe}},
                       {{url_for(".static", filename="colorpicker/css/colorpicker.css", _external=True)|tojson|safe}}];
    for (var i = 0; i < stylesheets.length; i++) {
        document.head.appendChild(sagecell.functions.createElement("link",
                {rel: "stylesheet", href: stylesheets[i]}));
    }

    // Mathjax.  We need a separate script tag for mathjax since it later comes back and looks at the script tag.
    load({'text': 'MathJax.Hub.Config({  \n\
          extensions: ["jsMath2jax.js", "tex2jax.js"],\n\
          tex2jax: {\n\
           inlineMath: [ ["$","$"], ["\\\\(","\\\\)"] ],\n\
           displayMath: [ ["$$","$$"], ["\\\\[","\\\\]"] ],\n\
           processEscapes: true,\n\
           processEnvironments: false}\n\
          });\n\
          // SVG backend does not work for IE version < 9, so switch if the default is SVG\n\
          //if (MathJax.Hub.Browser.isMSIE && (document.documentMode||0) < 9) {\n\
          //  MathJax.Hub.Register.StartupHook("End Config",function () {\n\
          //    var settings = MathJax.Hub.config.menuSettings;\n\
          //    if (!settings.renderer) {settings.renderer = "HTML-CSS"}\n\
          //  });\n\
          //}', 
          'type': 'text/x-mathjax-config'});
    load({'src': "{{- url_for('.static',filename='mathjax/MathJax.js', _external=True, config='TeX-AMS-MML_HTMLorMML') -}}"});

    // many prerequisites that have been smashed together into all.min.js
    load({'src': "{{- url_for('.static', filename='all.min.js', _external=True) -}}"});
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
                "hide": ["computationID", "messages", "sessionTitle", "sageMode"],
                "mode": "normal",
                "replaceOutput": true,
                "sageMode": true};

    // jQuery.extend() has issues with nested objects, so we manually merge
    // hide parameters.
    if (args.hide === undefined) {
        args.hide = defaults.hide;
    } else {
        args.hide = $.merge(args.hide, defaults.hide);
    }

    if (args.template !== undefined) {
        settings = $.extend({}, defaults, args.template, args)
        if (args.template.hide !== undefined) {
            settings.hide = $.merge(settings.hide, args.template.hide);
        }
    } else {
        settings = $.extend({}, defaults, args);
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

            inputLocation.addClass("sagecell");
            outputLocation.addClass("sagecell");
            inputLocation.html(body);
            inputLocation.find(".sagecell_commands").val(settings.code);
            if (inputLocation !== outputLocation) {
                inputLocation.find(".sagecell_output_elements").appendTo(outputLocation);
            }
            outputLocation.find(".sagecell_output_elements").hide();
            if (settings.mode === "debug") {
                console.warn("Running the Sage Cell in debug mode!");
            } else {
                var hideAdvanced = {};
                var hideable = {"in": {"computationID": true, "editor": true,
                                       "editorToggle": true,  "files": true,
                                       "evalButton": true,    "sageMode": true},
                                "out": {"output": true,       "messages": true,
                                        "sessionTitle": true, "sessionFiles": true,
                                        "permalinks": true}};
                var hidden_out = [];
                for (var i = 0, i_max = hide.length; i < i_max; i++) {
                    if (hide[i] in hideable["in"]) {
                        inputLocation.find(".sagecell_"+hide[i]).css("display", "none");
                        // TODO: make the advancedFrame an option to hide, then delete
                        // this hideAdvanced hack
                        if (hide[i] === 'files' || hide[i] === 'sageMode') {
                            hideAdvanced[hide[i]] = true;
                        }
                    } else if (hide[i] in hideable["out"]) {
                        hidden_out.push(settings.outputLocation + " .sagecell_" + hide[i]);
                    }
                }
                if (hideAdvanced.files && hideAdvanced.sageMode) {
                    inputLocation.find(".sagecell_advancedFrame").css("display", "none");
                }
                if (hidden_out.length > 0) {
                    var s = document.createElement("style");
                    var css = hidden_out.join(", ") + " {display: none;}";
                    s.setAttribute("type", "text/css");
                    if (s.styleSheet) {
                        s.styleSheet.cssText = css;
                    } else {
                        s.appendChild(document.createTextNode(css));
                    }
                    document.head.appendChild(s);
                }
            }
            if (evalButtonText !== undefined) {
                inputLocation.find(".sagecell_evalButton").text(evalButtonText);
            }
            sagecell.initCell(settings);
        });
    }, 100);
    return settings;
};

sagecell.initCell = (function(sagecellInfo) {
    var inputLocation = $(sagecellInfo.inputLocation);
    var outputLocation = $(sagecellInfo.outputLocation);
    var editor = sagecellInfo.editor;
    var replaceOutput = sagecellInfo.replaceOutput;
    var sageMode = inputLocation.find(".sagecell_sageModeCheck");
    var textArea = inputLocation.find(".sagecell_commands");
    var files = [];
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
    inputLocation.find(".sagecell_editorToggle").click(function () {
        temp = sagecell.toggleEditor(editor, editorData, inputLocation);
        editor = temp[0];
        editorData = temp[1];
        return false;
    });
    inputLocation.find(".sagecell_advancedTitle").click(function () {
        inputLocation.find(".sagecell_advancedFields").slideToggle();
        return false;
    });
    function fileRemover(i, li) {
        return function () {
            delete files[i];
            li.parentNode.removeChild(li);
        }
    }
    var fileButton = inputLocation.find(".sagecell_addFile");
    var input = sagecell.functions.createElement("input",
            {"type": "file", "multiple": "true", "name": "file"});
    if (navigator.userAgent.indexOf("MSIE") === -1) {
        // Create an off-screen file input box if not in Internet Explorer
        input.style.position = "absolute";
        input.style.top = "0px";
        input.style.left = "-9999px";
        fileButton.click(function () {
            input.click();
        });
        document.body.appendChild(input);
    } else {
        // Put the input box in the file upload box in Internet Explorer
        fileButton.remove();
        inputLocation.find(".sagecell_clearFiles").before(input,
                document.createElement("br"));
    }
    function change() {
        var delButton = sagecell.functions.createElement("span",
                {"title": "Remove file"});
        $(delButton).addClass("sagecell_deleteButton");
        var fileList = inputLocation.find(".sagecell_fileList");
        var li = document.createElement("li");
        li.appendChild(delButton.cloneNode(false));
        li.appendChild(document.createElement("span"));
        $(li.childNodes[1]).addClass("sagecell_fileName");
        if (input.files) {
            for (var i = 0; i < input.files.length; i++) {
                if (window.FormData) {
                    var f = li.cloneNode(true);
                    files.push(input.files[i]);
                    f.childNodes[1].appendChild(
                            document.createTextNode(input.files[i].name));
                    $(f.childNodes[0]).click(fileRemover(files.length - 1, f));
                    fileList.append(f);
                } else {
                    li.childNodes[1].appendChild(
                            document.createTextNode(input.files[i].name));
                    if (i < input.files.length - 1) {
                        li.childNodes[1].appendChild(document.createElement("br"));
                    }
                }
            }
            if (!window.FormData) {
                files.push(input);
                $(li.childNodes[0]).click(fileRemover(files.length - 1, li));
                if (input.files.length > 1) {
                    li.childNodes[0].setAttribute("title", "Remove files")
                }
                fileList.append(li);
            }
        } else {
            files.push(input);
            li.childNodes[1].appendChild(document.createTextNode(
                    input.value.substr(input.value.lastIndexOf("\\") + 1)));
            $(li.childNodes[0]).click(fileRemover(files.length - 1, li));
            fileList.append(li);
        }
        var newInput = sagecell.functions.createElement("input",
            {"type": "file", "multiple": "true", "name": "file"});
        if (navigator.userAgent.indexOf("MSIE") === -1) {
            newInput.style.position = "absolute";
            newInput.style.top = "0px";
            newInput.style.left = "-9999px";
        }
        $(newInput).change(change);
        input.parentNode.replaceChild(newInput, input);
        input = newInput;
    }
    $(input).change(change);
    inputLocation.find(".sagecell_clearFiles").click(function () {
        files = [];
        inputLocation.find(".sagecell_fileList").empty();
        return false;
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

        if (editorData.save !== undefined) {
            editorData.save();
        }
        var data = {"commands": JSON.stringify(textArea.val()),
                    "msg_id": sagecell.functions.uuid4()}
        if (inputLocation.find(".sagecell_sageModeCheck")[0].checked) {
            data["sage_mode"] = "on";
        }
        function callback(response) {
            response = JSON.parse(response);
            outputLocation.find(".sagecell_codeurl").attr("href", response.codeurl);
            outputLocation.find(".sagecell_zipurl").attr("href", response.zipurl);
            outputLocation.find(".sagecell_queryurl").attr("href", response.queryurl);
            new sagecell.Session(outputLocation, ".sagecell_output", response.session_id,
                    inputLocation.find(".sagecell_sageModeCheck").attr("checked"));
            outputLocation.find(".sagecell_computationID span").append(response.session_id);
            outputLocation.find(".sagecell_output_elements").show();
        }
        sagecell.sendRequest("POST", sagecell.$URL.evaluate, data, callback, files);
    };

    inputLocation.find(".sagecell_evalButton").click(sagecellInfo.submit);
    if (sagecellInfo.code && sagecellInfo.autoeval) {
        sagecellInfo.submit();
    }
    return sagecellInfo;
});

sagecell.sendRequest = function (method, url, data, callback, files) {
    method = method.toUpperCase();
    var hasFiles = false;
    if (files === undefined) {
        files = [];
    }
    for (var i = 0; i < files.length; i++) {
        if (files[i]) {
            hasFiles = true;
            break;
        }
    }
    var xhr = new XMLHttpRequest();
    var isXDomain = sagecell.$URL.root !== location.protocol + "//" + location.host + "/";
    var fd = undefined;
    if (method === "GET") {
        data.rand = Math.random().toString();
    }
    // Format parameters to send as a string or a FormData object
    if (window.FormData && method !== "GET") {
        fd = new FormData();
        for (var k in data) {
            if (data.hasOwnProperty(k)) {
                fd.append(k, data[k]);
            }
        }
        for (var i = 0; i < files.length; i++) {
            if (files[i]) {
                fd.append("file", files[i]);
            }
        }
    } else {
        fd = "";
        for (var k in data) {
            if (data.hasOwnProperty(k)) {
                fd += "&" + encodeURIComponent(k) + "=" + encodeURIComponent(data[k]);
            }
        }
        fd = fd.substr(1);
        if (fd.length > 0 && method === "GET") {
            url += "?" + fd;
            fd = undefined;
        }
    }
    if (window.FormData || !(isXDomain || hasFiles)) {
        // If an XMLHttpRequest is possible, use it
        xhr.open(method, url, true);
        xhr.onreadystatechange = function () {
            if (xhr.readyState === 4 /* DONE */) {
                callback(xhr.responseText);
            }
        };
        if (typeof fd === "string") {
            xhr.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
        }
        xhr.send(fd);
    } else if (method === "GET") {
        // Use JSONP to send cross-domain GET requests
        url += (url.indexOf("?") === -1 ? "?" : "&") + "callback=?";
        $.getJSON(url, data, callback);
    } else {
        // Use a form submission to send POST requests
        var iframe = document.createElement("iframe");
        iframe.name = sagecell.functions.uuid4();
        var form = sagecell.functions.createElement("form",
                {"method": method, "action": url, "target": iframe.name});
        for (var k in data) {
            if (data.hasOwnProperty(k)) {
                form.appendChild(sagecell.functions.createElement("input",
                        {"name": k, "value": data[k]}));
            }
        }
        form.appendChild(sagecell.functions.createElement("input",
                {"name": "frame", "value": "on"}));
        if (hasFiles) {
            form.setAttribute("enctype", "multipart/form-data");
            for (var i = 0; i < files.length; i++) {
                if (files[i]) {
                    form.appendChild(files[i]);
                }
            }
        }
        form.style.display = iframe.style.display = "none";
        document.body.appendChild(iframe);
        document.body.appendChild(form);
        function listen(evt) {
            if (evt.source === iframe.contentWindow &&
                evt.origin + "/" === sagecell.$URL.root) {
                if (window.removeEventListener) {
                    removeEventListener("message", listen);
                } else {
                    detachEvent("onmessage", listen);
                }
                callback(evt.data);
                document.body.removeChild(iframe);
            }
        }
        if (window.addEventListener) {
            window.addEventListener("message", listen);
        } else {
            window.attachEvent("onmessage", listen);
        }
        form.submit();
        document.body.removeChild(form);
    }
}

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
        "hide": ["editor", "editorToggle", "files", "permalinks"],
    },
    "restricted": { // to display/evaluate code that can't be edited.
        "editor": "codemirror-readonly",
        "hide": ["editorToggle", "files", "permalinks"],
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
    "createElement": function (type, attrs, children) {
        var node = document.createElement(type);
        for (var k in attrs) {
            if (attrs.hasOwnProperty(k)) {
                node.setAttribute(k, attrs[k]);
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
sagecell.$URL = {'root': {{request.url_root|tojson|safe}},
        'evaluate': {{url_for('evaluate',_external=True)|tojson|safe}},
        'powered_by_img': {{url_for('.static', filename='sagelogo.png', _external=True)|tojson|safe}},
        'spinner_img': {{url_for('.static', filename='spinner.gif', _external=True)|tojson|safe}},
        'output_poll': {{url_for('output_poll',_external=True)|tojson|safe}},
        'output_long_poll': {{url_for('output_long_poll',_external=True)|tojson|safe}}};

// Purely for backwards compability
window.singlecell = window.sagecell;
window.singlecell.makeSinglecell = window.singlecell.makeSagecell;
})(jQuery);
