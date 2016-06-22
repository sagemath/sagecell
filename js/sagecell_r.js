require([
    "jquery",
    "services/kernels/kernel",
    "editor",
    "session",
    "utils",
    // Unreferenced dependencies
    "jquery-ui",
    "jquery-ui-tp",
    "colorpicker",
    "canvas3d_lib",
    "three",
    "OrbitControls",
    "Detector",
    "JSmol",
    "3d"
], function(
    $,
    Kernel,
    editor,
    Session,
    utils
   ) {
"use strict";
var undefined;

sagecell.modes = {"sage": "python", "python": "python",
                  "html": "htmlmixed", "r": "r"};
if (sagecell.loadMathJax === undefined) {
    sagecell.loadMathJax = true;
}

var ce = utils.createElement;
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

    document.head.appendChild(ce("link", {rel: "stylesheet", href: utils.URLs.root + "static/all.min.css"}));

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
    new Image().src = utils.URLs.sage_logo;
    new Image().src = utils.URLs.spinner;
    utils.sendRequest("GET", utils.URLs.cell, {},
        function (data) {
            $(function () {
                sagecell.body = data;
                sagecell.dependencies_loaded = true;
                if (callback !== undefined) {
                    callback();
                };
            });
        }, undefined);
};

sagecell.kernels = [];

sagecell.makeSagecell = function (args, k) {
    var defaults;
    var settings = {};
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
                    Kernel.Kernel.prototype.kill = function () {
                        if (this.running) {
                            this.running = false;
                            utils.sendRequest("DELETE", this.kernel_url);
                        }
                    }
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
                var id = "input_" + utils.uuid();
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
                console.info("Running the Sage Cell in debug mode!");
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
                var out_class = "output_" + utils.uuid();
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


var accepted_tos = localStorage.accepted_tos;

sagecell.initCell = (function (sagecellInfo, k) {
    var inputLocation = $(sagecellInfo.inputLocation);
    var outputLocation = $(sagecellInfo.outputLocation);
    var editorType = sagecellInfo.editor;
    var replaceOutput = sagecellInfo.replaceOutput;
    var collapse = sagecellInfo.collapse;
    var textArea = inputLocation.find(".sagecell_commands");
    var langSelect = inputLocation.find(".sagecell_language select");
    //var files = [];
    var editorData, temp;
    temp = editor.render(editorType, inputLocation, collapse);
    editorType = temp[0];
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
        if (editorType.lastIndexOf('codemirror',0) === 0 /* efficient .startswith('codemirror')*/ ) {
            editorData.save();
        }
        _gaq.push(['sagecell._trackEvent', 'SageCell', 'Execute',window.location.origin+window.location.pathname]);

        var code = textArea.val();
        var language = langSelect[0].value;
        var session = new Session(outputLocation, language,
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
            utils.sendRequest("POST", utils.URLs.terms, {}, function (data) {
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
    button.click({"id": utils.uuid()}, sagecellInfo.submit);
    if (sagecellInfo.code && sagecellInfo.autoeval) {
        button.click();
    }
    if (sagecellInfo.callback) {
        sagecellInfo.callback();
    }
    return sagecellInfo;
});

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
});
