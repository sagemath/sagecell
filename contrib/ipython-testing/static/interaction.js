$(function() {
    "use strict";
    function cursor_line(text, idx) {
        text = text.split("\n");
        while (text[0].length < idx) {
            idx -= text.shift().length + 1;
        }
        return [idx, text[0]];
    }

    function should_complete(textbox) {
        if (!textbox.jquery) {
            textbox = $(textbox);
        }
        if (!(textbox[0].selectionStart !== undefined &&
            textbox[0].selectionStart === textbox[0].selectionEnd)) {
            return false;
        }
        var line = cursor_line(textbox.val(), textbox[0].selectionStart);
        return !line[1].substring(0,line[0]).match(/^\s*$/);
    }

    function left_part_at_end(text, target) {
        for (var i = target.length; i >= 1; i--) {
            if (target.substr(0, i) === text.substr(text.length - i, i)) {
                break;
            }
        }
        return target.substr(0, i);
    }

    function fill_completion(completion, textbox) {
        var start = textbox.selectionStart;
        var part = left_part_at_end(textbox.value.substring(0, start), completion);
        textbox.value = textbox.value.substring(0, start) + completion.substr(part.length) + textbox.value.substring(start);
        textbox.selectionStart = start + completion.length - part.length;
        textbox.focus();
    }

    function show_completions(completions, dest, textbox) {
        var span = document.createElement("span");
        for (var i = 0; i < completions.length; i++) {
            var item = document.createElement("span");
            item.appendChild(document.createTextNode(completions[i]));
            item.style.cursor = "pointer";
            if (i > 0) {
                item.style.marginLeft = "1em";
            }
            item.addEventListener("click", function (i) {
                return function () {
                    fill_completion(completions[i], textbox);
                    dest.style.display = "none";
                }
            }(i));
            span.appendChild(item);
        }
        if (dest.hasChildNodes()) {
            dest.removeChild(dest.firstChild);
        }
        dest.appendChild(span);
        dest.style.display = "inherit";
    }

    var base_url = "kernel";
    var test_kernel = new IPython.Kernel(base_url);
    test_kernel.start();
    console.log(test_kernel); // Successful startup
    var output_callback = function (type, msg) {
        var text;
        if (type === "stream") {
            text = msg.data;
        } else if (type === "pyout") {
            text = msg.data["text/plain"];
        } else if (type === "pyerr") {
            text = msg.traceback.join("\n");
        }
        var output = document.getElementById("output");
        var span = document.createElement("span");
        if (type !== "pyerr") {
            $(span).text(text);
        } else {
            $(span).html(IPython.utils.fixConsole(text));
        }
        $("#output").append(span);
    };
    var callbacks = {"output": output_callback};

    (function f() {
        if (test_kernel.shell_channel === null || test_kernel.iopub_channel === null) {
            var _this = this;
            setTimeout(function(){f.call(_this);}, 200);
        } else {
            var codebox = $("#codebox");
            codebox.keydown(function (event) {
                if (event.keyCode === 9) {
                    event.preventDefault();
                }
            });
            var completions = [];
            codebox.keypress(function (event) {
                if (event.keyCode === 9 && codebox[0].selectionStart !== undefined) {
                    event.preventDefault();
                    var lines = codebox.val().split("\n");
                    var line = cursor_line(codebox.val(), codebox[0].selectionStart);
                    if (should_complete(codebox)) {
                        test_kernel.complete(line[1], line[0], {"complete_reply": function (content) {
                            completions = content.matches;
                            if (completions.length > 1) {
                                show_completions(completions, document.getElementById("completion"), codebox[0]);
                            } else if (completions.length === 1) {
                                fill_completion(completions[0], codebox[0]);
                                document.getElementById("completion").style.display = "none";
                            } else {
                                document.getElementById("completion").style.display = "none";
                            }
                        }});
                    } else if (codebox[0].selectionStart === codebox[0].selectionEnd) {
                        codebox.val(codebox.val().substring(0, codebox[0].selectionBegin) + "\t" +
                                codebox.val().substring(codebox[0].selectionEnd, codebox.val().length));
                    }
                } else if (event.keyCode === 8 || String.fromCharCode(event.charCode).match(/\w/) && 
                    !(event.ctrlKey || event.altKey || event.metaKey || (event.shiftKey && event.keyCode === 8))) {
                    var comp = document.getElementById("completion");
                    if (comp.style.display !== "none") {
                        var new_completions = [];
                        var new_val = codebox.val().substring(0, codebox[0].selectionStart);
                        if (event.keyCode !== 8) {
                            new_val += String.fromCharCode(event.charCode);
                        } else {
                            new_val = new_val.substring(0, new_val.length - 1);
                        }
                        for (var i = 0; i < completions.length; i++) {
                            var part = left_part_at_end(new_val, completions[i]);
                            if (part.length > 0) {
                                new_completions.push(completions[i]);
                            }
                        }
                        if (new_completions.length > 0) {
                            show_completions(new_completions, comp, codebox[0]);
                        } else {
                            comp.style.display = "none";
                        }
                    } else {
                        comp.style.display = "none";
                    }
                } else {
                    document.getElementById("completion").style.display = "none"
                }
            });
            $("#codebox").on("click focus blur", function () {
                document.getElementById("completion").style.display = "none"
            });
            $("#evalbutton").on("click", function(event) {
                $("#message_output").empty();
                $("#output").empty();
                var code = $("#codebox").val();
                test_kernel.execute(code, callbacks);
            });

        }
    })();

});
