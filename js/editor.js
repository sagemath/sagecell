define([
    "jquery",
    "./sagecell",
    "./multisockjs",
    "./utils",
    "codemirror/lib/codemirror",
    // Unreferenced dependencies
    "codemirror/addon/display/autorefresh",
    "codemirror/addon/display/fullscreen",
    "codemirror/addon/edit/matchbrackets",
    "codemirror/addon/fold/foldcode",
    "codemirror/addon/fold/foldgutter",
    "codemirror/addon/fold/brace-fold",
    "codemirror/addon/fold/xml-fold",
    "codemirror/addon/fold/comment-fold",
    "codemirror/addon/fold/indent-fold",
    "codemirror/addon/hint/show-hint",
    "codemirror/addon/runmode/runmode",
    "codemirror/addon/runmode/colorize",
    "codemirror/mode/css/css",
    "codemirror/mode/htmlmixed/htmlmixed",
    "codemirror/mode/javascript/javascript",
    "codemirror/mode/python/python",
    "codemirror/mode/r/r",
    "codemirror/mode/xml/xml",
], function ($, sagecell, MultiSockJS, utils, CodeMirror) {
    "use strict";
    var undefined;

    var ce = utils.createElement;

    function makeMsg(msg_type, content) {
        return {
            header: {
                msg_id: utils.uuid(),
                session: utils.uuid(),
                msg_type: msg_type,
                username: "",
            },
            content: content,
            parent_header: {},
            metadata: {},
        };
    }

    var callbacks = {};

    function completerMsg(msg, callback) {
        function sendMsg() {
            callbacks[msg.header.msg_id] = callback;
            completer.send(JSON.stringify(msg));
        }
        if (completer === undefined) {
            var completer = new MultiSockJS(null, "complete");
            completer.onmessage = function (event) {
                var data = JSON.parse(event.data);
                var cb = callbacks[data.parent_header.msg_id];
                delete callbacks[data.parent_header.msg_id];
                cb(data);
            };
            completer.onopen = sendMsg;
        } else {
            sendMsg();
        }
    }

    var openedDialog = null;

    function closeDialog() {
        if (openedDialog) {
            openedDialog.dialog("destroy");
            openedDialog = null;
        }
    }

    function showInfo(msg, cm) {
        if (!msg.content.found) {
            return;
        }
        var d = ce("pre");
        d.innerHTML = utils.fixConsole(msg.content.data["text/plain"]);
        closeDialog();
        openedDialog = $(d).dialog({
            width: 700,
            height: 300,
            position: {
                my: "left top",
                at: "left+5px bottom+5px",
                of: cm.display.cursorDiv.parentNode,
                collision: "none",
            },
            appendTo: $(cm.display.wrapper).parents(".sagecell").first(),
            close: closeDialog,
        });
        cm.focus();
    }

    function requestInfo(cm) {
        var cur = cm.getCursor();
        var line = cm.getLine(cur.line).substr(0, cur.ch);
        var detail = cur.ch > 1 && line[cur.ch - 2] === "?" ? 1 : 0;
        var oname = line.match(/([a-z_][a-z_\d.]*)(\?\??|\()$/i);
        if (oname === null) {
            return;
        }
        var cb = function (data) {
            showInfo(data, cm);
        };
        var kernel = sagecell.kernels[cm.k];
        if (kernel && kernel.session.linked && kernel.shell_channel.send) {
            var msg = kernel._get_msg("object_info_request", {
                oname: oname[1],
                detail_level: detail,
            });
            kernel.shell_channel.send(JSON.stringify(msg));
            kernel.set_callbacks_for_msg(msg.header.msg_id, {
                inspect_request: cb,
            });
        } else {
            completerMsg(
                makeMsg("object_info_request", {
                    oname: oname[1],
                    detail_level: detail,
                }),
                cb
            );
        }
    }

    function render(editorType, inputLocation, collapse) {
        var commands = inputLocation.find(".sagecell_commands");
        var editorData;
        if (collapse !== undefined) {
            var header, code;
            var accordion = ce("div", {}, [
                (header = ce("h3", {}, ["Code"])),
                (code = document.createElement("div")),
            ]);
            header.style.paddingLeft = "2.2em";
            $(accordion).insertBefore(commands);
            $(accordion).accordion({
                active: collapse ? false : header,
                collapsible: true,
                header: header,
            });
        }
        commands.on("keypress", function (event) {
            if (event.which === 13 && event.shiftKey) {
                event.preventDefault();
            }
        });
        commands.on("keyup", function (event) {
            if (event.which === 13 && event.shiftKey) {
                inputLocation.find(".sagecell_evalButton").click();
            }
        });
        if (editorType === "textarea") {
            editorData = {};
        } else if (editorType === "textarea-readonly") {
            editorData = {};
            commands.attr("readonly", "readonly");
        } else {
            var readOnly = false;
            if (editorType === "codemirror-readonly") {
                readOnly = true;
            } else {
                editorType = "codemirror";
            }
            var langSelect = inputLocation.find(".sagecell_language select");
            var mode = langSelect[0].value;
            CodeMirror.commands.autocomplete = function (cm) {
                CodeMirror.showHint(
                    cm,
                    function (cm, callback) {
                        var cur = cm.getCursor();
                        var kernel = sagecell.kernels[cm.k];
                        var cb = function (data) {
                            if (data.content) {
                                data = data.content;
                            }
                            callback({
                                list: data.matches,
                                from: CodeMirror.Pos(
                                    cur.line,
                                    data.cursor_start
                                ),
                                to: cur,
                            });
                        };
                        var mode = langSelect[0].value;
                        if (
                            (mode === "sage" || mode === "python") &&
                            kernel &&
                            kernel.session.linked &&
                            kernel.shell_channel.send
                        ) {
                            kernel.complete(cm.getLine(cur.line), cur.ch, {
                                complete_reply: cb,
                            });
                        } else {
                            completerMsg(
                                makeMsg("complete_request", {
                                    text: "",
                                    line: cm.getLine(cur.line),
                                    cursor_pos: cur.ch,
                                    mode: mode,
                                }),
                                cb
                            );
                        }
                    },
                    { async: true }
                );
            };
            var fullscreen = $(
                ce("button", {
                    title: "Toggle full-screen editor (F11)",
                    type: "button",
                    class: "sagecell_fullScreen sagecell_icon-resize-full",
                })
            );
            var fullscreenToggle = function (cm) {
                cm.setOption("fullScreen", !cm.getOption("fullScreen"));
                fullscreen.toggleClass("sagecell_fullScreenEnabled");
                fullscreen.toggleClass(
                    "sagecell_icon-resize-full sagecell_icon-resize-small"
                );
            };

            editorData = CodeMirror.fromTextArea(commands.get(0), {
                autoRefresh: true,
                mode: sagecell.modes[mode],
                viewportMargin: Infinity,
                indentUnit: 4,
                lineNumbers: true,
                matchBrackets: true,
                readOnly: readOnly,
                foldGutter: true,
                gutters: ["CodeMirror-linenumbers", "CodeMirror-foldgutter"],
                extraKeys: {
                    Tab: function (cm) {
                        var cur = cm.getCursor();
                        var line = cm.getLine(cur.line).substr(0, cur.ch);
                        var mode = langSelect[0].value;
                        if (
                            (mode === "sage" || mode === "python") &&
                            cur.ch > 0 &&
                            (line[cur.ch - 1] === "?" ||
                                line[cur.ch - 1] === "(")
                        ) {
                            requestInfo(cm);
                        } else if (line.match(/^ *$/)) {
                            CodeMirror.commands.indentMore(cm);
                        } else {
                            closeDialog();
                            CodeMirror.commands.autocomplete(cm);
                        }
                    },
                    "Shift-Tab": "indentLess",
                    "Shift-Enter": closeDialog,
                    F11: function (cm) {
                        fullscreenToggle(cm);
                    },
                    Esc: function (cm) {
                        if (openedDialog) {
                            closeDialog();
                        } else if (cm.getOption("fullScreen")) {
                            fullscreenToggle(cm);
                        }
                    },
                },
            });
            editorData.on("keyup", function (cm, event) {
                cm.save();
                if (event.which === 13 && event.shiftKey) {
                    inputLocation.find(".sagecell_evalButton").click();
                    if (cm.getOption("fullScreen")) {
                        fullscreenToggle(cm);
                    }
                }
            });
            $(accordion).on("accordionactivate", function () {
                editorData.refresh();
            });
            $(editorData.getWrapperElement()).prepend(fullscreen);
            fullscreen.on("click", function () {
                fullscreenToggle(editorData);
                editorData.focus();
            });
        }
        return [editorType, editorData];
    }

    return {
        render: render,
    };
});
