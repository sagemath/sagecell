define([
    "jquery",
    "editor",
    "session",
    "utils",
    "text!cell_body.html",
    "text!all.min.css",
    // Unreferenced dependencies
    "domReady!",
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
    editor,
    Session,
    utils,
    cell_body,
    css
   ) {
"use strict";
var undefined;

sagecell.modes = {
    sage: "python",
    python: "python",
    html: "htmlmixed",
    r: "r"};

var style = document.createElement('style');
style.innerHTML = css.replace(/url\((?!data:)/g, 'url(' + utils.URLs.root + 'static/');
var fs = document.getElementsByTagName('script')[0];
fs.parentNode.insertBefore(style, fs);

if (window.MathJax === undefined) {
    var script = document.createElement("script");
    script.type = "text/x-mathjax-config";
    script.text = "MathJax.Hub.Config(" + JSON.stringify({
        "extensions": ["jsMath2jax.js", "tex2jax.js"],
        "tex2jax": {
            "inlineMath": [["$", "$"], ["\\(", "\\)"]],
            "displayMath": [["$$", "$$"], ["\\[", "\\]"]],
            "processEscapes": true,
            "processEnvironments": true
        },
        "TeX": {
            "extensions": ["color.js"]
        }
    }) + ");";
    fs.parentNode.insertBefore(script, fs);
    script = document.createElement("script");
    script.type = "text/javascript";
    script.src  = "https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML";
    fs.parentNode.insertBefore(script, fs);
}
// Preload images
new Image().src = utils.URLs.spinner;

sagecell.kernels = [];

function make(args, cellInfo, k) {
    if (args.inputLocation === undefined) {
        throw "Must specify an inputLocation!";
    }
    var input = $(args.inputLocation);
    if (input.length === 0) {
        return;
    }
    if (input.length > 1) {
        if (args.outputLocation !== undefined) {
            throw "inputLocation must be unique if outputLocation is specified";
        }
        cellInfo.array = [];
        if (args.linked) {
            args.autoeval = false;
            k = sagecell.kernels.push(null) - 1;
        }
        for (var i = 0, i_max = input.length; i < i_max; i++) {
            var args_i = $.extend({}, args);
            args_i.inputLocation = input[i];
            var cellInfo_i = {};
            make(args_i, cellInfo_i, k);
            cellInfo.array.push(cellInfo_i);
        }
        return;
    }
    if (input.hasClass("sagecell")) {
        // Do not process again the same locations.
        return;
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
        } else if (input.children("script").length > 0) {
            args.code = input.children("script").html();
        } else if (input.is("textarea")) {
            args.code = input.val();
        } else {
            args.code = input.text();
        }
        args.code = $.trim(args.code);
    }
    var defaults = {"editor": "codemirror",
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
        $.extend(cellInfo, defaults, args.template, args)
        if (args.template.hide !== undefined) {
            cellInfo.hide = $.merge(cellInfo.hide, args.template.hide);
        }
    } else {
        $.extend(cellInfo, defaults, args);
    }
    if ($.inArray(cellInfo.defaultLanguage, cellInfo.languages) === -1) {
        cellInfo.defaultLanguage = cellInfo.languages[0];
    }
    if (cellInfo.languages.length === 1) {
        cellInfo.hide.push("language");
    }
    if (cellInfo.linked) {
        cellInfo.hide.push("permalink");
    }

    var hide = cellInfo.hide;
    var output = $(cellInfo.outputLocation);

    if (input.is("textarea")) {
        var ta = input;
        input = $(document.createElement("div")).insertBefore(input);
        input.html(cell_body);
        ta.addClass("sagecell_commands");
        ta.attr({"autocapitalize": "off", "autocorrect": "off", "autocomplete": "off"});
        input.find(".sagecell_commands").replaceWith(ta);
        var id = "input_" + utils.uuid();
        input[0].id = id;
        if (input === output) {
            output = $(cellInfo.outputLocation = "#" + id);
        }
        cellInfo.inputLocation = "#" + id;
    } else {
        input.html(cell_body);
    }
    input.addClass("sagecell");
    output.addClass("sagecell");
    input.find(".sagecell_commands").val(cellInfo.code);
    if (input !== output) {
        input.find(".sagecell_output_elements").appendTo(output);
    }
    output.find(".sagecell_output_elements").hide();
    hide.push("files"); // TODO: Delete this line when this feature is implemented.
    if (cellInfo.mode === "debug") {
        console.info("Running SageMathCell in debug mode");
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
        output.addClass(out_class);
        for (var i = 0, i_max = hide.length; i < i_max; i++) {
            if (hide[i] in hideable["in"]) {
                input.find(".sagecell_"+hide[i]).css("display", "none");
                // TODO: make the advancedFrame an option to hide, then delete
                // this hideAdvanced hack
                if (hide[i] === 'files') {
                    hideAdvanced[hide[i]] = true;
                }
            } else if (hide[i] in hideable["out"]) {
                hidden_out.push("." + out_class + " .sagecell_" + hide[i]);
            }
        }
        var langOpts = input.find(".sagecell_language option");
        langOpts.not(function () {
            return $.inArray(this.value, cellInfo.languages) !== -1;
        }).css("display", "none");
        langOpts[0].parentNode.value = cellInfo.defaultLanguage;
        if (hideAdvanced.files) {
            input.find(".sagecell_advancedFrame").css("display", "none");
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
    input.find(".sagecell_evalButton").text(cellInfo.evalButtonText);
    init(cellInfo, k);
    _gaq.push(['sagecell._trackEvent', 'SageCell', 'Make',window.location.origin+window.location.pathname]);
}


var accepted_tos = localStorage.accepted_tos;
var deferred_eval = [];

function deferredEvaluation() {
    for (var i = 0; i < deferred_eval.length; i++) {
        deferred_eval[i][0](deferred_eval[i][1]);
    }
}

var last_session = {};
var ce = utils.createElement;

function init(cellInfo, k) {
    var input = $(cellInfo.inputLocation);
    var output = $(cellInfo.outputLocation);
    var langSelect = input.find(".sagecell_language select");
    //var files = [];
    var temp = editor.render(cellInfo.editor, input, cellInfo.collapse);
    var editorType = temp[0];
    var editorData = temp[1];
    editorData.k = k;
    input.find(".sagecell_advancedTitle").click(function () {
        input.find(".sagecell_advancedFields").slideToggle();
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
    var fileButton = input.find(".sagecell_addFile");
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
        input.find(".sagecell_clearFiles").before(input,
                document.createElement("br"));
    }
    function change() {
        var delButton = ce("span", {title: "Remove file"});
        $(delButton).addClass("sagecell_deleteButton");
        var fileList = input.find(".sagecell_fileList");
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
    input.find(".sagecell_clearFiles").click(function () {
        files = [];
        input.find(".sagecell_fileList").empty();
        return false;
    });
    */
    function startEvaluation(evt) {
        if (last_session[evt.data.id]) {
            if (!last_session[evt.data.id].linked) {
                last_session[evt.data.id].kernel.kill();
            }
            if (cellInfo.replaceOutput) {
                last_session[evt.data.id].destroy();
            }
        }
        if (editorType.lastIndexOf('codemirror',0) === 0 /* efficient .startswith('codemirror')*/ ) {
            editorData.save();
        }
        _gaq.push(['sagecell._trackEvent', 'SageCell', 'Execute',window.location.origin+window.location.pathname]);

        var code = input.find(".sagecell_commands").val();
        var language = langSelect[0].value;
        var session = new Session(output, language,
            cellInfo.interacts || [], k, cellInfo.linked || false);
        cellInfo.session = session;
        cellInfo.interacts = [];
        session.execute(code);
        last_session[evt.data.id] = session;
        output.find(".sagecell_output_elements").show();
    }
    cellInfo.submit = function (evt) {
        if (accepted_tos) {
            startEvaluation(evt);
            return false;
        }
        deferred_eval.push([startEvaluation, evt]);
        if (deferred_eval.length === 1) {
            utils.sendRequest("POST", utils.URLs.terms, {}, function (data) {
                if (data.length === 0) {
                    accepted_tos = true;
                    deferredEvaluation();
                } else {
                    var terms = $(document.createElement("div"));
                    terms.html(data);
                    terms.dialog({
                        "modal": true,
                        "height": 400,
                        "width": 600,
                        "appendTo": input,
                        "title": "Terms of Service",
                        "buttons": {
                            "Accept": function () {
                                $(this).dialog("close");
                                accepted_tos = true;
                                localStorage.accepted_tos = true;
                                deferredEvaluation();
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
    var button = input.find(".sagecell_evalButton").button();
    button.click({"id": utils.uuid()}, cellInfo.submit);
    if (cellInfo.code && cellInfo.autoeval) {
        button.click();
    }
    if (cellInfo.callback) {
        cellInfo.callback();
    }
    return cellInfo;
}

return {
    make: make,
    delete: function(cellInfo) {
        $(cellInfo.inputLocation).remove();
        $(cellInfo.outputLocation).remove();
    },
    moveInputForm: function(cellInfo) {
        var moved = ce("div", {id: "sagecell_moved"});
        moved.style.display = "none";
        $(document.body).append(moved);
        $(cellInfo.inputLocation).contents().appendTo($(moved));
    },
    restore: function(cellInfo) {
        var moved = $("#sagecell_moved");
        moved.contents().appendTo(cellInfo.inputLocation);
        moved.remove();
    }
};
});
