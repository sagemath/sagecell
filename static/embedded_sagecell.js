// TODO: put this tracking code in a site-specific file.
// TODO: finish implementing our own stats service that handles,
//       the phone apps, for example.
var _gaq = _gaq || [];
_gaq.push(['sagecell._setAccount', 'UA-29124745-1']);
_gaq.push(['sagecell._setDomainName', 'sagemath.org']);
_gaq.push(['sagecell._trackPageview']);

(function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
})();

(function() {
"use strict";
var undefined;

// Make a global sagecell namespace for our functions
window.sagecell = window.sagecell || {};

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
    /* Read the Sage Cell server's  root url from one of the following locations:
         1. the variable sagecell.root
         2. a tag of the form <link property="sagecell-root" href="...">
         3. the root of the URL of the executing script */
    var el;
    if (sagecell.root) {
        sagecell.URLs.root = sagecell.root;
    } else if ((el = $("link[property=sagecell-root]")).length > 0) {
        sagecell.URLs.root = el.last().attr("href");
    } else {
        /* get the first part of the last script element's src that loaded something called 'embedded_sagecell.js'
           also, strip off the static/ part of the url if the src looked like 'static/embedded_sagecell.js'
           modified from MathJax source
           We could use the jquery reverse plugin at  http://www.mail-archive.com/discuss@jquery.com/msg04272.html 
           and the jquery .each() to get this as well, but this approach avoids creating a reversed list, etc. */
        var scripts = (document.documentElement || document).getElementsByTagName("script");
        var namePattern = /^.*?(?=(?:static\/)?embedded_sagecell.js)/;
        for (var i = scripts.length-1; i >= 0; i--) {
            var m = (scripts[i].src||"").match(namePattern);
            if (m) {
                var r = m[0];
                break;
            }
        }
        if (r === "" || r === "/") {
            r = window.location.protocol + "//" + window.location.host + "/";
        }
        sagecell.URLs.root = r;
    }
    if (sagecell.URLs.root.slice(-1) !== "/") {
        sagecell.URLs.root += "/";
    }
}());

sagecell.URLs.kernel = sagecell.URLs.root + "kernel";
sagecell.URLs.sockjs = sagecell.URLs.root + "sockjs";
sagecell.URLs.permalink = sagecell.URLs.root + "permalink";
sagecell.URLs.cell = sagecell.URLs.root + "sagecell.html";
sagecell.URLs.completion = sagecell.URLs.root + "complete";
sagecell.URLs.terms = sagecell.URLs.root + "tos.html";
sagecell.URLs.help = sagecell.URLs.root + "help.html"
sagecell.URLs.sage_logo = sagecell.URLs.root + "static/sagelogo.png";
sagecell.URLs.spinner = sagecell.URLs.root + "static/spinner.gif";
sagecell.modes = {"sage": "python", "python": "python",
                  "html": "htmlmixed", "r": "r"};
if (sagecell.loadMathJax === undefined) {
    sagecell.loadMathJax = true;
}
if (sagecell.log === undefined) {
    sagecell.log = (function (log) {
        return function (obj) {
            if (sagecell.debug) {
                log(obj);
            }
        };
    }(typeof console === "undefined" ? function() {} : $.proxy(console.log, console)));
}
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
                if (typeof children[i] == 'string') {
                    node.appendChild(document.createTextNode(children[i]));
                } else {
                    node.appendChild(children[i]);
                }
            }
        }
        return node;
    }
/* var p = proxy(['list', 'of', 'methods'])
     will save any method calls in the list.  At some later time, you can invoke
     each method on an object by doing p._run_callbacks(my_obj) */
    ,"proxy": function(methods) {
        var proxy = {_callbacks: []};
        $.each(methods, function(i,method) {
            proxy[method] = function() {
                proxy._callbacks.push([method, arguments]);
                console.log('stored proxy for '+method);
            }
        })
            proxy._run_callbacks = function(obj) {
                $.each(proxy._callbacks, function(i,cb) {
                    obj[cb[0]].apply(obj, cb[1]);
                })
                    }
        return proxy;
    }


//     throttle is from:
//     Underscore.js 1.4.3
//     http://underscorejs.org
//     (c) 2009-2012 Jeremy Ashkenas, DocumentCloud Inc.
//     Underscore may be freely distributed under the MIT license.
// Returns a function, that, when invoked, will only be triggered at most once
// during a given window of time.
    ,"throttle": function(func, wait) {
    var context, args, timeout, result;
    var previous = 0;
    var later = function() {
      previous = new Date;
      timeout = null;
      result = func.apply(context, args);
    };
    return function() {
      var now = new Date;
      var remaining = wait - (now - previous);
      context = this;
      args = arguments;
      if (remaining <= 0) {
        clearTimeout(timeout);
        timeout = null;
        previous = now;
        result = func.apply(context, args);
      } else if (!timeout) {
        timeout = setTimeout(later, remaining);
      }
      return result;
    };
  }

};

var ce = sagecell.util.createElement;
var deferred_eval = [];
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
    var stylesheets = [sagecell.URLs.root + "static/jquery-ui/css/sagecell/jquery-ui-1.10.2.custom.min.css",
                       sagecell.URLs.root + "static/colorpicker/css/colorpicker.css",
                       sagecell.URLs.root + "static/all.min.css"]
    for (var i = 0; i < stylesheets.length; i++) {
        document.head.appendChild(ce("link", {rel: "stylesheet", href: stylesheets[i]}));
    }

    if(window.MathJax === undefined && sagecell.loadMathJax) {
        // Mathjax.  We need a separate script tag for mathjax since it later
        // comes back and looks at the script tag.
        var mjConfig = {
            "extensions": ["jsMath2jax.js", "tex2jax.js"],
            "tex2jax": {
                "inlineMath": [["$", "$"], ["\\(", "\\)"]],
                "displayMath": [["$$", "$$"], ["\\[", "\\]"]],
                "processEscapes": true,
                "processEnvironments": true
            }
        };
        load({
            'text': 'MathJax.Hub.Config(' + JSON.stringify(mjConfig) + ');',
            'type': 'text/x-mathjax-config'
        });
        load({"src": "https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML"});
    }
    // Preload images
    new Image().src = sagecell.URLs.sage_logo;
    new Image().src = sagecell.URLs.spinner;
    sagecell.sendRequest("GET", sagecell.URLs.cell, {},
        function (data) {
            $(function () {
                sagecell.body = data;
                // many prerequisites that have been smashed together into all.min.js
                load({"src": sagecell.URLs.root + "static/all.min.js"})
            });
        }, undefined);
};

sagecell.sagecell_dependencies_callback = function () {
    sagecell.dependencies_loaded = true;
    if (sagecell.init_callback !== undefined) {
        sagecell.init_callback();
    }
};

sagecell.kernels = [];

sagecell.makeSagecell = function (args, k) {
    var defaults;
    var settings = {};
    if (args === undefined) {
        args = {};
    }
    if (args.inputLocation === undefined) {
        throw "Must specify an inputLocation!";
    }
    if (args.linked) {
        settings.autoeval = false;
    }
    setTimeout(function waitForLoad() {
        // Wait for dependencies to load before setting up the Sage cell
        // TODO: look into something like require.js?
        if (!sagecell.dependencies_loaded) {
            if (sagecell.dependencies_loaded === undefined) {
                sagecell.init(function () {
                    IPython.Kernel.prototype.kill = function () {
                        if (this.running) {
                            this.running = false;
                            sagecell.sendRequest("DELETE", this.kernel_url);
                        }
                    }
                    IPython.WidgetManager.prototype.display_view = function(msg, model) {
                        var session = this.comm_manager.kernel.session;
                        var block_id = msg.metadata.interact_id || null;
                        var view = this.create_view(model, {cell: session})
                        if (view === undefined) {
                            console.error("Could not find widget view for model", model);
                        }
                        session.output(view.$el, block_id);
                    }
                    IPython.WidgetManager.prototype.callbacks = function (view) {
                        // callback handlers specific a view
                        var callbacks = {};
                        if (view && view.options && view.options.cell) {
                            var session = view.options.cell;
                            // Create callback dict using what is known
                            callbacks = {
                                iopub : {
                                    output : $.proxy(session.handle_output, session),
                                    clear_output : null,

                                    // Special function only registered by widget messages.
                                    // Allows us to get the cell for a message so we know
                                    // where to add widgets if the code requires it.
                                    get_cell : function () {
                                        return session;
                                    },
                                }
                            };
                        }
                        return callbacks;
                    };
                    // override IPython notebookisms
                    IPython.WidgetManager.prototype._handle_new_view = function() {/*do nothing*/};
                });
            }
            setTimeout(waitForLoad, 100);
            return false;
        }
        // Wait for the page to load before trying to find various DOM elements
        $(function () {
            var input = $(args.inputLocation);
            if (input.length === 0) {
                return [];
            }
            if (input.length > 1 && args.outputLocation === undefined) {
                var r = [];
                if (args.linked) {
                    k = sagecell.kernels.push(null) - 1;
                }
                for (var i = 0, i_max = input.length; i < i_max; i++) {
                    var a = $.extend({}, args);
                    a.inputLocation = input[i];
                    r.push(sagecell.makeSagecell(a, k));
                }
                return r;
            }
            if (input.hasClass("sagecell")) {
                    return null;
            }
            if (k === undefined) {
                k = sagecell.kernels.push(null) - 1;
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
                args.code = $.trim(args.code);
            }
            defaults = {"editor": "codemirror",
                        "evalButtonText": "Evaluate",
                        "hide": ["messages"],
                        "mode": "normal",
                        "replaceOutput": true,
                        "languages": ["sage"]};
            // jQuery.extend() has issues with nested objects, so we manually merge
            // hide parameters.
            if (args.hide === undefined) {
                args.hide = defaults.hide;
            } else {
                args.hide = $.merge(args.hide, defaults.hide);
            }
        
            if (args.template !== undefined) {
                $.extend(settings, defaults, args.template, args)
                if (args.template.hide !== undefined) {
                    settings.hide = $.merge(settings.hide, args.template.hide);
                }
            } else {
                $.extend(settings, defaults, args);
            }
            if ($.inArray(settings.defaultLanguage, settings.languages) === -1) {
                settings.defaultLanguage = settings.languages[0];
            }
            if (settings.languages.length === 1) {
                settings.hide.push("language");
            }
            if (settings.linked) {
                settings.hide.push("permalink");
            }

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
            inputLocation.addClass("sagecell");
            outputLocation.addClass("sagecell");
            inputLocation.find(".sagecell_commands").val(settings.code);
            if (inputLocation !== outputLocation) {
                inputLocation.find(".sagecell_output_elements").appendTo(outputLocation);
            }
            outputLocation.find(".sagecell_output_elements").hide();
            hide.push("files"); // TODO: Delete this line when this feature is implemented.
            if (settings.mode === "debug") {
                sagecell.log("Running the Sage Cell in debug mode!");
            } else {
                var hideAdvanced = {};
                var hideable = {"in": {"editor": true,
                                       "files": true,
                                       "evalButton": true,
                                       "language": true},
                                "out": {"output": true,
                                        "messages": true,
                                        "sessionFiles": true,
                                        "permalink": true}};
                var hidden_out = [];
                var out_class = "output_" + IPython.utils.uuid();
                outputLocation.addClass(out_class);
                for (var i = 0, i_max = hide.length; i < i_max; i++) {
                    if (hide[i] in hideable["in"]) {
                        inputLocation.find(".sagecell_"+hide[i]).css("display", "none");
                        // TODO: make the advancedFrame an option to hide, then delete
                        // this hideAdvanced hack
                        if (hide[i] === 'files') {
                            hideAdvanced[hide[i]] = true;
                        }
                    } else if (hide[i] in hideable["out"]) {
                        hidden_out.push("." + out_class + " .sagecell_" + hide[i]);
                    }
                }
                var langOpts = inputLocation.find(".sagecell_language option");
                langOpts.not(function () {
                    return $.inArray(this.value, settings.languages) !== -1;
                }).css("display", "none");
                langOpts[0].parentNode.value = settings.defaultLanguage;
                if (hideAdvanced.files) {
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
            sagecell.initCell(settings, k);
            _gaq.push(['sagecell._trackEvent', 'SageCell', 'Make',window.location.origin+window.location.pathname]);

        });
    }, 0);
    return settings;
};


var isXDomain = sagecell.URLs.root !== window.location.protocol + "//" + window.location.host + "/";
var accepted_tos = localStorage.accepted_tos;

sagecell.initCell = (function (sagecellInfo, k) {
    var inputLocation = $(sagecellInfo.inputLocation);
    var outputLocation = $(sagecellInfo.outputLocation);
    var editor = sagecellInfo.editor;
    var replaceOutput = sagecellInfo.replaceOutput;
    var collapse = sagecellInfo.collapse;
    var textArea = inputLocation.find(".sagecell_commands");
    var langSelect = inputLocation.find(".sagecell_language select");
    //var files = [];
    var editorData, temp;
    temp = this.renderEditor(editor, inputLocation, collapse);
    editor = temp[0];
    editorData = temp[1];
    editorData.k = k;
    inputLocation.find(".sagecell_advancedTitle").click(function () {
        inputLocation.find(".sagecell_advancedFields").slideToggle();
        return false;
    });
    langSelect.change(function () {
        var mode = langSelect[0].value;
        editorData.setOption("mode", sagecell.modes[mode]);
    });
    /* Old files code
    function fileRemover(i, li) {
        return function () {
            delete files[i];
            li.parentNode.removeChild(li);
        }
    }
    var fileButton = inputLocation.find(".sagecell_addFile");
    var input = ce("input", {type: "file", multiple: "true", name: "file"});
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
        var delButton = ce("span", {title: "Remove file"});
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
        var newInput = ce("input", {type: "file", multiple: "true", name: "file"});
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
    */
    var startEvaluation = function (evt) {
        if (sagecell.last_session[evt.data.id]) {
            if (!sagecell.last_session[evt.data.id].linked) {
                sagecell.last_session[evt.data.id].kernel.kill();
            }
            if (replaceOutput) {
                sagecell.last_session[evt.data.id].destroy();
            }
        }
        if (editor.lastIndexOf('codemirror',0) === 0 /* efficient .startswith('codemirror')*/ ) {
            editorData.save();
        }
        _gaq.push(['sagecell._trackEvent', 'SageCell', 'Execute',window.location.origin+window.location.pathname]);

        var code = textArea.val();
        var language = langSelect[0].value;
        var session = new sagecell.Session(outputLocation, language,
            sagecellInfo.interacts || [], k, sagecellInfo.linked || false);
        sagecellInfo.session = session;
        sagecellInfo.interacts = [];
        session.execute(code);
        sagecell.last_session[evt.data.id] = session;
        outputLocation.find(".sagecell_output_elements").show();
    };
    sagecellInfo.submit = function (evt) {
        if (accepted_tos || sagecellInfo.requires_tos === false) {
            startEvaluation(evt);
            return false;
        }
        deferred_eval.push([startEvaluation, evt]);
        if (deferred_eval.length === 1) {
            sagecell.sendRequest("POST", sagecell.URLs.terms, {}, function (data) {
                if (data.length === 0) {
                    accepted_tos = true;
                    startEvaluation(evt);
                } else {
                    var terms = $(document.createElement("div"));
                    terms.html(data);
                    terms.dialog({
                        "modal": true,
                        "height": 400,
                        "width": 600,
                        "appendTo": inputLocation,
                        "title": "Terms of Service",
                        "buttons": {
                            "Accept": function () {
                                $(this).dialog("close");
                                accepted_tos = true;
                                localStorage.accepted_tos = true;
                                for (var i = 0; i < deferred_eval.length; i++) {
                                    deferred_eval[i][0](deferred_eval[i][1]);
                                }
                            },
                            "Cancel": function () {
                                $(this).dialog("close");
                            }
                        }
                    });
                }
            });
        }
        // return false to make *sure* any containing form doesn't submit
        return false;
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

sagecell.sendRequest = function (method, url, data, callback, files) {
    method = method.toUpperCase();
    var hasFiles = false;
    /* files code
    if (files === undefined) {
        files = [];
    }
    for (var i = 0; i < files.length; i++) {
        if (files[i]) {
            hasFiles = true;
            break;
        }
    }
    */
    var xhr = new XMLHttpRequest();
    var fd = undefined;
    if (method === "GET") {
        data.rand = Math.random().toString();
    }
    if (method === "POST" && accepted_tos) {
        data.accepted_tos = "true";
    }
    // Format parameters to send as a string or a FormData object
    if (window.FormData && method !== "GET") {
        fd = new FormData();
        for (var k in data) {
            if (data.hasOwnProperty(k)) {
                fd.append(k, data[k]);
            }
        }
        /* files code
        for (var i = 0; i < files.length; i++) {
            if (files[i]) {
                fd.append("file", files[i]);
            }
        }
        */
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
    if (window.FormData || !(isXDomain /*|| hasFiles*/)) {
        // If an XMLHttpRequest is possible, use it
        xhr.open(method, url, true);
        xhr.withCredentials = true;
        xhr.onreadystatechange = function () {
            if (xhr.readyState === 4 /* DONE */ && callback) {
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
        $.getJSON(url, callback);
    } else {
        // Use a form submission to send POST requests
        // Methods such as DELETE and OPTIONS will be sent as POST instead
        var iframe = document.createElement("iframe");
        iframe.name = IPython.utils.uuid();
        var form = ce("form", {method: "POST", action: url, target: iframe.name});
        if (data === undefined) {
            data = {};
        }
        data.method = method;
        for (var k in data) {
            if (data.hasOwnProperty(k)) {
                form.appendChild(sagecell.util.createElement("input",
                        {"name": k, "value": data[k]}));
            }
        }
        form.appendChild(ce("input", {name: "frame", value: "on"}));
        /* file code
        if (hasFiles) {
            form.setAttribute("enctype", "multipart/form-data");
            for (var i = 0; i < files.length; i++) {
                if (files[i]) {
                    form.appendChild(files[i]);
                }
            }
        }
        */
        form.style.display = iframe.style.display = "none";
        document.body.appendChild(iframe);
        document.body.appendChild(form);
        var listen = function (evt) {
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
    var moved = ce("div", {id: "sagecell_moved"});
    moved.style.display = "none";
    $(document.body).append(moved);
    $(sagecellInfo.inputLocation).contents().appendTo($(moved));
};

sagecell.restoreInputForm = function (sagecellInfo) {
    var moved = $("#sagecell_moved");
    moved.contents().appendTo(sagecellInfo.inputLocation);
    moved.remove();
};

var makeMsg = function (msg_type, content) {
    return {
        "header": {
            "msg_id": IPython.utils.uuid(),
            "session": IPython.utils.uuid(),
            "msg_type": msg_type,
            "username": ""
        },
        "content": content,
        "parent_header": {},
        "metadata": {}
    }
};

var callbacks = {};
var completerMsg = function (msg, callback) {
    var sendMsg = function () {
        callbacks[msg.header.msg_id] = callback;
        sagecell.completer.send(JSON.stringify(msg));
    };
    if (sagecell.completer === undefined) {
        sagecell.completer = new sagecell.MultiSockJS(null, "complete/shell");
        sagecell.completer.onmessage = function (event) {
            var data = JSON.parse(event.data);
            var cb = callbacks[data.parent_header.msg_id];
            delete callbacks[data.parent_header.msg_id];
            cb(data)
        }
        sagecell.completer.onopen = sendMsg;
    } else {
        sendMsg();
    }
};

var openedDialog = null;
var closeDialog = function () {
    if (openedDialog) {
        openedDialog.dialog("destroy");
        openedDialog = null;
    }
}

var showInfo = function (data, cm) {
    if (data.content) {
        data = data.content;
    }
    if (!data.found) {
        return;
    }
    var d;
    if (data.source === null) {
        var def;
        if (data.definition !== null) {
            def = ce("code");
            def.innerHTML = IPython.utils.fixConsole(data.definition);
        }
        d = ce("div", {}, [
            ce("div", {}, [ce("strong", {}, "File: "), ce("code", {}, data.file || data.namespace)]),
            ce("div", {}, [ce("strong", {}, "Type: "), ce("code", {}, data.base_class)])
        ]);
        if (def) {
            d.appendChild(ce("div", {}, [ce("strong", {}, "Definition: "), def]));
        }
        d.appendChild(ce("pre", {}, data.docstring));
    } else {
        d = ce("pre", {"class": "cm-s-default"});
        CodeMirror.runMode(data.source, "python", d);
    }
    closeDialog();
    openedDialog = $(d).dialog({
        "title": data.name,
        "width": 700,
        "height": 300,
        "position": {
            "my": "left top",
            "at": "left+5px bottom+5px",
            "of": cm.display.cursor.parentNode,
            "collision": "none"
        },
        "appendTo": $(cm.display.wrapper).parents(".sagecell").first(),
        "close": closeDialog
    });
    cm.focus();
}

var requestInfo = function (cm) {
    var cur = cm.getCursor();
    var line = cm.getLine(cur.line).substr(0, cur.ch);
    var detail = (cur.ch > 1 && line[cur.ch - 2] === "?") ? 1 : 0;
    var oname = line.match(/([a-z_][a-z_\d.]*)(\?\??|\()$/i);
    if (oname === null) {
        return;
    }
    var cb = function (data) {
        showInfo(data, cm);
    }
    var kernel = sagecell.kernels[cm.k];
    if (kernel && kernel.session.linked && kernel.shell_channel.send) {
        var msg = kernel._get_msg("object_info_request", {
            "oname": oname[1],
            "detail_level": detail
        })
        kernel.shell_channel.send(JSON.stringify(msg));
        kernel.set_callbacks_for_msg(msg.header.msg_id, {
            "object_info_reply": cb
        });
    } else {
        completerMsg(makeMsg("object_info_request", {
            "oname": oname[1],
            "detail_level": detail
        }), cb);
    }
}

sagecell.renderEditor = function (editor, inputLocation, collapse) {
    var commands = inputLocation.find(".sagecell_commands");
    var editorData;
    if (collapse !== undefined) {
        var header, code;
        var accordion = ce("div", {}, [
            header = ce("h3", {}, ["Code"]),
            code = document.createElement("div")
        ]);
        header.style.paddingLeft = "2.2em";
        $(accordion).insertBefore(commands);
        $(accordion).accordion({"active": (collapse ? false : header),
                                "collapsible": true,
                                "header": header});
    }
    commands.keypress(function (event) {
        if (event.which === 13 && event.shiftKey) {
            event.preventDefault();
        }
    });
    commands.keyup(function (event) {
        if (event.which === 13 && event.shiftKey) {
            inputLocation.find(".sagecell_evalButton").click();
        }
    });
    if (editor === "textarea") {
        editorData = {};
    } else if (editor === "textarea-readonly") {
        editorData = {}
        commands.attr("readonly", "readonly");
    } else {
        var readOnly = false;
        if (editor === "codemirror-readonly") {
            readOnly = true;
        } else {
            editor = "codemirror";
        }
        var langSelect = inputLocation.find(".sagecell_language select");
        var mode = langSelect[0].value;
        CodeMirror.commands.autocomplete = function (cm) {
            CodeMirror.showHint(cm, function (cm, callback) {
                var cur = cm.getCursor();
                var kernel = sagecell.kernels[cm.k];
                var cb = function (data) {
                    if (data.content) {
                        data = data.content;
                    }
                    if (data.matched_text.length === 0) {
                        data.matches = [];
                    }
                    callback({
                        "list": data.matches,
                        "from": CodeMirror.Pos(cur.line, cur.ch - data.matched_text.length),
                        "to": cur
                    });
                };
                var mode = langSelect[0].value;
                if ((mode === "sage" || mode === "python") && kernel &&
                    kernel.session.linked && kernel.shell_channel.send) {
                    kernel.complete(cm.getLine(cur.line), cur.ch, {"complete_reply": cb});
                } else {
                    completerMsg(makeMsg("complete_request", {
                        "text": "",
                        "line": cm.getLine(cur.line),
                        "cursor_pos": cur.ch,
                        "mode": mode
                    }), cb);
                }
            }, {"async": true});
        };
        var fullscreen = $(ce("button", {title: "Toggle full-screen editor", type: "button", class: "sagecell_fullScreen sagecell_icon-resize-full"}));
        var fullscreenToggle = function(editor) {
            editor.setOption("fullScreen", !editor.getOption("fullScreen"));
            fullscreen.toggleClass("sagecell_fullScreenEnabled");
            fullscreen.toggleClass("sagecell_icon-resize-full sagecell_icon-resize-small");
        }

        editorData = CodeMirror.fromTextArea(commands.get(0), {
            mode: sagecell.modes[mode],
            viewportMargin: Infinity,
            indentUnit: 4,
            lineNumbers: true,
            matchBrackets: true,
            readOnly: readOnly,
            foldGutter: true,
            gutters: ["CodeMirror-linenumbers", "CodeMirror-foldgutter"],
            extraKeys: {
                "Tab": function (editor) {
                    var cur = editor.getCursor();
                    var line = editor.getLine(cur.line).substr(0, cur.ch);
                    var mode = langSelect[0].value;
                    if ((mode === "sage" || mode === "python") && cur.ch > 0 &&
                        (line[cur.ch - 1] === "?" || line[cur.ch - 1] === "(")) {
                        requestInfo(editor);
                    } else if (line.match(/^ *$/)) {
                        CodeMirror.commands.indentMore(editor);
                    } else {
                        closeDialog();
                        CodeMirror.commands.autocomplete(editor);
                    }
                },
                "Shift-Tab": "indentLess",
                "Shift-Enter": closeDialog,
                "Esc": function(cm) {
                    if (openedDialog) {
                        closeDialog();
                    } else if (cm.getOption("fullScreen")) {
                        fullscreenToggle(cm);
                    }
                }
            }
        });
        editorData.on("keyup", function (editor, event) {
            editor.save();
            if (event.which === 13 && event.shiftKey) {
                inputLocation.find(".sagecell_evalButton").click();
                if (editor.getOption("fullScreen")) {
                    fullscreenToggle(editor);
                }
            }
        });
        $(accordion).on("accordionactivate", function () {
            editorData.refresh();
        });
        $(editorData.getWrapperElement()).prepend(fullscreen);
        fullscreen.click(function() {
            fullscreenToggle(editorData);
            editorData.focus();
        });
    }
    return [editor, editorData];
};

sagecell.templates = {
    "minimal": { // for an evaluate button and nothing else.
        "editor": "textarea-readonly",
        "hide": ["editor", "files", "permalink"],
    },
    "restricted": { // to display/evaluate code that can't be edited.
        "editor": "codemirror-readonly",
        "hide": ["files", "permalink"],
    }
};

sagecell.allLanguages = ["sage", "gap", "gp", "html", "maxima", "octave", "python", "r", "singular"]


// Purely for backwards compability
window.singlecell = window.sagecell;
window.singlecell.makeSinglecell = window.singlecell.makeSagecell;
})();
