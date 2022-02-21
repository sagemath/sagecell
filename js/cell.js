import $ from "jquery";
import sagecell from "./sagecell";
import editor from "./editor";
import Session from "./session";
import utils from "./utils";
import domReady from "requirejs-domready";
import { initializeURLs, URLs } from "./urls";
import { _gaq } from "./gaq";

// Imports for side-effects only
import "webpack-jquery-ui";
import "jsmol";
import "colorpicker";

// The contents of these files is imported as strings
//import css from "all.min.css";
import cell_body from "./cell_body.html";

import {css} from "./css"

const cell = (function () {
    "use strict";
    var undefined;

    sagecell.modes = {
        sage: "python",
        python: "python",
        html: "htmlmixed",
        r: "r",
    };

    domReady(function () {
        initializeURLs();

        var style = document.createElement("style");
        style.innerHTML = css.replace(
            /url\((?!data:)/g,
            "url(" + URLs.root + "static/"
        );
        var fs = document.getElementsByTagName("script")[0];
        fs.parentNode.insertBefore(style, fs);

        if (window.MathJax === undefined) {
            // MathJax 3
            var script = document.createElement("script");
            script.type = "text/javascript";
            script.text = `window.MathJax = {
        tex: {
          inlineMath: [["$", "$"], ["\\\\(", "\\\\)"]],
          displayMath: [["$$", "$$"], ["\\\\[", "\\\\]"]],
          processEscapes: true,
          processEnvironments: true,
        },
        options: {
          renderActions: { /* remove when dropping MathJax2 compatibility */
            find_script_mathtex: [10, function (doc) {
              for (const node of document.querySelectorAll('script[type^="math/tex"]')) {
                const display = !!node.type.match(/; *mode=display/);
                const math = new doc.options.MathItem(node.textContent, doc.inputJax[0], display);
                const text = document.createTextNode('');
                node.parentNode.replaceChild(text, node);
                math.start = {node: text, delim: '', n: 0};
                math.end = {node: text, delim: '', n: 0};
                doc.math.push(math);
              }
            }, '']
          }
        }
    };`;
            fs.parentNode.insertBefore(script, fs);
            script = document.createElement("script");
            script.type = "text/javascript";
            script.src =
                "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml-full.js";
            fs.parentNode.insertBefore(script, fs);
        }

        // Preload images
        new Image().src = URLs.spinner;
    });

    sagecell.kernels = [];

    function make(args, cellInfo, k) {
        if (args.inputLocation === undefined) {
            throw "Must specify an inputLocation!";
        }
        // Cannot be run before the dom is ready since this function
        // searches the dom for sagecell elements to replace.
        domReady(function () {
            var input = $(args.inputLocation);
            if (input.length === 0) {
                return;
            }
            if (input.length > 1) {
                if (args.outputLocation !== undefined) {
                    throw "inputLocation must be unique if outputLocation is specified";
                }
                cellInfo.array = [];
                if (args.linked && k === undefined) {
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
            var defaults = {
                editor: "codemirror",
                evalButtonText: "Evaluate",
                hide: ["messages"],
                mode: "normal",
                replaceOutput: true,
                languages: ["sage"],
            };
            $.extend(cellInfo, defaults, args.template, args);
            // Since hide is an array, it is not actually merged as intended
            var hide = (cellInfo.hide = $.merge([], defaults.hide));
            if (
                args.template !== undefined &&
                args.template.hide !== undefined
            ) {
                $.merge(hide, args.template.hide);
            }
            if (args.hide !== undefined) {
                $.merge(hide, args.hide);
            }
            if (
                $.inArray(cellInfo.defaultLanguage, cellInfo.languages) === -1
            ) {
                cellInfo.defaultLanguage = cellInfo.languages[0];
            }
            if (cellInfo.languages.length === 1) {
                hide.push("language");
            }
            if (cellInfo.linked) {
                hide.push("permalink");
            }

            var output = $(cellInfo.outputLocation);

            if (input.is("textarea")) {
                var ta = input;
                input = $(document.createElement("div")).insertBefore(input);
                input.html(cell_body);
                ta.addClass("sagecell_commands");
                ta.attr({
                    autocapitalize: "off",
                    autocorrect: "off",
                    autocomplete: "off",
                });
                input.find(".sagecell_commands").replaceWith(ta);
                var id = "input_" + utils.uuid();
                input[0].id = id;
                if (input === output) {
                    output = $((cellInfo.outputLocation = "#" + id));
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
                var hideable = {
                    in: {
                        editor: true,
                        files: true,
                        evalButton: true,
                        language: true,
                    },
                    out: {
                        output: true,
                        messages: true,
                        sessionFiles: true,
                        permalink: true,
                    },
                };
                var hidden_out = [];
                var out_class = "output_" + utils.uuid();
                output.addClass(out_class);
                for (var i = 0, i_max = hide.length; i < i_max; i++) {
                    if (hide[i] in hideable["in"]) {
                        input
                            .find(".sagecell_" + hide[i])
                            .css("display", "none");
                        // TODO: make the advancedFrame an option to hide, then delete
                        // this hideAdvanced hack
                        if (hide[i] === "files") {
                            hideAdvanced[hide[i]] = true;
                        }
                    } else if (hide[i] in hideable["out"]) {
                        hidden_out.push(
                            "." + out_class + " .sagecell_" + hide[i]
                        );
                    }
                }
                var langOpts = input.find(".sagecell_language option");
                langOpts
                    .not(function () {
                        return $.inArray(this.value, cellInfo.languages) !== -1;
                    })
                    .css("display", "none");
                langOpts[0].parentNode.value = cellInfo.defaultLanguage;
                if (hideAdvanced.files) {
                    input
                        .find(".sagecell_advancedFrame")
                        .css("display", "none");
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
            if (hide.indexOf("fullScreen") != -1) {
                input.find(".sagecell_fullScreen").css("display", "none");
            }
            _gaq.push([
                "sagecell._trackEvent",
                "SageCell",
                "Make",
                window.location.origin + window.location.pathname,
            ]);
        });
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
        cellInfo.editorData = editorData;
        editorData.k = k;
        input.find(".sagecell_advancedTitle").on("click", function () {
            input.find(".sagecell_advancedFields").slideToggle();
            return false;
        });
        langSelect.on("change", function () {
            var mode = langSelect[0].value;
            editorData.setOption("mode", sagecell.modes[mode]);
        });
        function startEvaluation(evt) {
            if (last_session[evt.data.id]) {
                if (!last_session[evt.data.id].linked) {
                    last_session[evt.data.id].kernel.kill();
                }
                if (cellInfo.replaceOutput) {
                    last_session[evt.data.id].destroy();
                }
            }
            if (
                editorType.lastIndexOf("codemirror", 0) ===
                0 /* efficient .startswith('codemirror')*/
            ) {
                editorData.save();
            }
            _gaq.push([
                "sagecell._trackEvent",
                "SageCell",
                "Execute",
                window.location.origin + window.location.pathname,
            ]);

            var code = input.find(".sagecell_commands").val();
            var language = langSelect[0].value;
            var session = new Session(
                output,
                language,
                cellInfo.interacts || [],
                k,
                cellInfo.linked || false
            );
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
                utils.sendRequest("POST", URLs.terms, {}, function (data) {
                    if (data.length === 0) {
                        accepted_tos = true;
                        deferredEvaluation();
                    } else {
                        var terms = $(document.createElement("div"));
                        terms.html(data);
                        terms.dialog({
                            modal: true,
                            height: 400,
                            width: 600,
                            appendTo: input,
                            title: "Terms of Service",
                            buttons: {
                                Accept: function () {
                                    $(this).dialog("close");
                                    accepted_tos = true;
                                    localStorage.accepted_tos = true;
                                    deferredEvaluation();
                                },
                                Cancel: function () {
                                    $(this).dialog("close");
                                },
                            },
                        });
                    }
                });
            }
            // return false to make *sure* any containing form doesn't submit
            return false;
        };
        var button = input.find(".sagecell_evalButton").button();
        button.on("click", { id: utils.uuid() }, cellInfo.submit);
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
        delete: function (cellInfo) {
            $(cellInfo.inputLocation).remove();
            $(cellInfo.outputLocation).remove();
        },
        moveInputForm: function (cellInfo) {
            var moved = ce("div", { id: "sagecell_moved" });
            moved.style.display = "none";
            $(document.body).append(moved);
            $(cellInfo.inputLocation).contents().appendTo($(moved));
        },
        restore: function (cellInfo) {
            var moved = $("#sagecell_moved");
            moved.contents().appendTo(cellInfo.inputLocation);
            moved.remove();
        },
    };
})();

export default cell;
