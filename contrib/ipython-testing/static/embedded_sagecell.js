(function() {
"use strict";

// Make a global sagecell namespace for our functions
window.sagecell = {};

if (!document.head) {
    document.head = document.getElementsByTagName("head")[0];
}

var $ = jQuery.noConflict(true);
if (jQuery === undefined) {
    window.$ = jQuery = $;
}
sagecell.jQuery = $;

sagecell.URLs = {};

(function () {
    // Read root url from the script tag loading this file
    var r = $("script").last().attr("src").match(/^.*(?=embedded_sagecell.js)/)[0];
    var s = "static/";
    if (r.substring(r.length - s.length) === s) {
        r = r.substring(0, r.length - s.length);
    }
    if (r === "" || r === "/") {
        r = window.location.protocol + "//" + window.location.host + "/";
    }
    sagecell.URLs.root = r;
}());

sagecell.URLs.kernel = sagecell.URLs.root + "kernel";
sagecell.URLs.sockjs = sagecell.URLs.root + "sockjs";
sagecell.URLs.permalink = sagecell.URLs.root + "permalink";
sagecell.URLs.sage_logo = sagecell.URLs.root + "static/sagelogo.png";
sagecell.URLs.spinner = sagecell.URLs.root + "static/spinner.gif";

sagecell.init = function (callback) {
    if (sagecell.dependencies_loaded !== undefined) {
        return;
    }
    var load = function ( config ) {
        // We can't use the jquery .append to load javascript because then the script tag disappears.  At least mathjax depends on the script tag 
        // being around later to get the mathjax path.  See http://stackoverflow.com/questions/610995/jquery-cant-append-script-element.
        var script = document.createElement("script");
        if (config.type !== undefined) {
            script.type = config.type;
        }
        if (config.src !== undefined) {
            script.src = config.src;
        }
        if (config.text !== undefined) {
            script.text = config.text;
        }
        document.head.appendChild(script);
    };

    sagecell.init_callback = callback
    sagecell.dependencies_loaded = false;
    sagecell.last_session = {};

    // many stylesheets that have been smashed together into all.min.css
    var stylesheets = [sagecell.URLs.root + "static/jquery-ui/css/sagecell/jquery-ui-1.8.21.custom.css",
                       sagecell.URLs.root + "static/colorpicker/css/colorpicker.css",
                       sagecell.URLs.root + "static/all.min.css"]
    for (var i = 0; i < stylesheets.length; i++) {
        document.head.appendChild(sagecell.util.createElement("link",
                {"rel": "stylesheet", "href": stylesheets[i]}));
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
    load({"src": sagecell.URLs.root + "static/mathjax/MathJax.js?config=TeX-AMS-MML_HTMLorMML"});
    sagecell.sendRequest("GET", sagecell.URLs.root + "sagecell.html", {},
        function (data) {
            $(function () {
                sagecell.body = data;
                // many prerequisites that have been smashed together into all.min.js
                load({"src": sagecell.URLs.root + "static/all.min.js"})
            });
        }, undefined, "text/html");
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
        } else if ($(args.inputLocation).children("script").length > 0) {
            args.code = $(args.inputLocation).children("script").html();
        } else if ($(args.inputLocation).is("textarea")) {
            args.code = $(args.inputLocation).val();
        } else {
            args.code = $(args.inputLocation).text();
        }
    }
    defaults = {"editor": "codemirror",
                "evalButtonText": "Evaluate",
                "hide": ["computationID", "messages", "sageMode"],
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
        $(function () {
            var hide = settings.hide;
            var inputLocation = $(settings.inputLocation);
            var outputLocation = $(settings.outputLocation);
            var evalButtonText = settings.evalButtonText;

            if (inputLocation.is("textarea")) {
                var ta = inputLocation;
                inputLocation = $(document.createElement("div")).insertBefore(inputLocation);
                inputLocation.html(sagecell.body);
                ta.addClass("sagecell_commands");
                ta.attr({"autocapitalize": "off", "autocorrect": "off", "autocomplete": "off"});
                inputLocation.find(".sagecell_commands").replaceWith(ta);
                var id = "input_" + IPython.utils.uuid();
                inputLocation[0].id = id;
                if (settings.outputLocation === settings.inputLocation) {
                    outputLocation = $(settings.outputLocation = "#" + id);
                }
                settings.inputLocation = "#" + id;
            } else {
                inputLocation.html(sagecell.body);
            }
            var id = IPython.utils.uuid();
            inputLocation.find(".sagecell_editorToggle label").attr("for", id);
            inputLocation.find(".sagecell_editorToggle input").attr("id", id);
            inputLocation.addClass("sagecell");
            outputLocation.addClass("sagecell");
            inputLocation.find(".sagecell_commands").val(settings.code);
            if (inputLocation !== outputLocation) {
                inputLocation.find(".sagecell_output_elements").appendTo(outputLocation);
            }
            outputLocation.find(".sagecell_output_elements").hide();
            hide.push("files", "sageMode"); // TODO: Delete this line when these features are implemented.
            if (settings.mode === "debug") {
                console.warn("Running the Sage Cell in debug mode!");
            } else {
                var hideAdvanced = {};
                var hideable = {"in": {"computationID": true, "editor": true,
                                       "editorToggle": true,  "files": true,
                                       "evalButton": true,    "sageMode": true},
                                "out": {"output": true,       "messages": true,
                                        "sessionFiles": true, "permalink": true}};
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
    var collapse = sagecellInfo.collapse;
    var sageMode = inputLocation.find(".sagecell_sageModeCheck");
    var textArea = inputLocation.find(".sagecell_commands");
    var files = [];
    var editorData, temp;
    if (! sagecellInfo.sageMode) {
        sageMode.attr("checked", false);
    }
    temp = this.renderEditor(editor, inputLocation, collapse);
    editor = temp[0];
    editorData = temp[1];
    inputLocation.find(".sagecell_editorToggle input").change(function () {
        temp = sagecell.toggleEditor(editor, editorData, inputLocation);
        editor = temp[0];
        editorData = temp[1];
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
    var input = sagecell.util.createElement("input",
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
        var delButton = sagecell.util.createElement("span",
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
        var newInput = sagecell.util.createElement("input",
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
    sagecellInfo.submit = function (evt) {
        if (replaceOutput && sagecell.last_session[evt.data.id]) {
            $(sagecell.last_session[evt.data.id].session_container).remove();
        }
        var session = new sagecell.Session(outputLocation);
        session.execute(textArea.val());
        sagecell.last_session[evt.data.id] = session;
        // TODO: kill the kernel when a computation with no interacts finishes,
        //       and also when a new computation begins from the same cell
        outputLocation.find(".sagecell_output_elements").show();
    };
    var button = inputLocation.find(".sagecell_evalButton").button();
    button.click({"id": IPython.utils.uuid()}, sagecellInfo.submit);
    if (sagecellInfo.code && sagecellInfo.autoeval) {
        button.click();
    }
    if (sagecellInfo.callback) {
        sagecellInfo.callback();
    }
    return sagecellInfo;
});

sagecell.sendRequest = function (method, url, data, callback, files, accept) {
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
    var isXDomain = sagecell.URLs.root !== window.location.protocol + "//" + window.location.host + "/";
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
        xhr.setRequestHeader("Accept", accept || "application/json");
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
        iframe.name = IPython.utils.uuid();
        var form = sagecell.util.createElement("form",
                {"method": method, "action": url, "target": iframe.name});
        for (var k in data) {
            if (data.hasOwnProperty(k)) {
                form.appendChild(sagecell.util.createElement("input",
                        {"name": k, "value": data[k]}));
            }
        }
        form.appendChild(sagecell.util.createElement("input",
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
        listen = function (evt) {
            if (evt.source === iframe.contentWindow &&
                evt.origin + "/" === sagecell.URLs.root) {
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
    var moved = sagecell.util.createElement("div", {"id": "sagecell_moved"});
    moved.style.display = "none";
    $(document.body).append(moved);
    $(sagecellInfo.inputLocation).contents().appendTo($(moved));
};

sagecell.restoreInputForm = function (sagecellInfo) {
    var moved = $("#sagecell_moved");
    moved.contents().appendTo(sagecellInfo.inputLocation);
    moved.remove();
};

sagecell.renderEditor = function (editor, inputLocation, collapse) {
    var commands = inputLocation.find(".sagecell_commands");
    var editorData;
    if (collapse !== undefined) {
        var header, code;
        var accordion = sagecell.util.createElement("div", {}, [
            header = sagecell.util.createElement("h3", {}, [
                document.createTextNode("Code")
            ]),
            code = document.createElement("div")
        ]);
        header.style.paddingLeft = "2.2em";
        $(accordion).insertBefore(commands);
        $(code).append(commands, inputLocation.find(".sagecell_editorToggle"));
        $(accordion).accordion({"active": (collapse ? false : header),
                                "collapsible": true,
                                "header": header});
    }
    if (editor === "textarea") {
        editorData = editor;
    } else if (editor === "textarea-readonly") {
        editorData = editor;
        commands.attr("readonly", "readonly");
    } else {
        var readOnly = false;
        if (editor === "codemirror-readonly") {
            readOnly = true;
        } else {
            editor = "codemirror";
        }
        editorData = CodeMirror.fromTextArea(
            commands.get(0),
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
            }});
        $(accordion).on("accordionchange", function () {
            editorData.refresh();
        });
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
        "hide": ["editor", "editorToggle", "files", "permalink"],
    },
    "restricted": { // to display/evaluate code that can't be edited.
        "editor": "codemirror-readonly",
        "hide": ["editorToggle", "files", "permalink"],
    }
};

// Various utility functions for the Single Cell Server
sagecell.util = {
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

// Purely for backwards compability
window.singlecell = window.sagecell;
window.singlecell.makeSinglecell = window.singlecell.makeSagecell;
})();
