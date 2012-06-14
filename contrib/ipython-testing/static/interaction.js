$(function() {
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

    (function() {
        var listener = null;
        if (test_kernel.shell_channel === null || test_kernel.iopub_channel === null) {
            var fn = arguments.callee;
            var _this = this;
            setTimeout(function(){fn.call(_this);}, 200);
        } else {
            var codebox = $("#codebox");
            codebox.keydown(function (event) {
                if (event.which === 9) {
                    event.preventDefault();
                }
            });
            codebox.keypress(function (event) {
                if (event.keyCode === 9 && codebox[0].selectionStart !== undefined) {
                    event.preventDefault();
                    var lines = codebox.val().split("\n");
                    var line = cursor_line(codebox.val(), codebox.selectionStart);
                    if (should_complete(codebox)) {
                        if (listener !== null) {
                            codebox.unbind("keypress", listener);
                        }
                        test_kernel.complete(line[1], line[0], {"complete_reply": function (content) {
                            if (content.matches.length > 1) {
                                $("#completion").text(content.matches.join("   "));
                                $("#completion").css("display", "inherit");
                                if (listener !== null) {
                                    codebox.unbind("keypress", listener);
                                }
                                listener = function (event) {
                                    if (String.fromCharCode(event.charCode).match(/\W/)) {
                                        return;
                                    }
                                    var matched = content.matches, new_matched = [];
                                    for (var i = 0; i < matched.length; i++) {
                                        if (left_part_at_end(codebox.val().substring(0, codebox[0].selectionStart) +
                                                String.fromCharCode(event.charCode), matched[i])) {
                                            new_matched.push(matched[i]);
                                        }
                                    }
                                    $("#completion").text(new_matched.join("   "));
                                }
                                codebox.bind("keypress", listener)
                            } else if (content.matches.length === 1) {
                                var matched = content.matches[0];
                                var val = codebox.val().substring(0, codebox[0].selectionEnd);
                                var part = left_part_at_end(val, matched);
                                if (part.length) {
                                    codebox.val(val.substring(0, codebox[0].selectionEnd) +
                                            matched.substring(part.length, matched.length) +
                                            val.substring(codebox[0].selectionEnd, val.length));
                                }
                                $("#completion").css("display", "none");
                                if (listener !== null) {
                                    codebox.unbind("keypress", listener);
                                }   
                            } else {
                                $("#completion").css("display", "none");
                            }
                        }});
                    } else if (codebox[0].selectionStart === codebox[0].selectionEnd) {
                        codebox.val(codebox.val().substring(0, codebox[0].selectionBegin) + "\t" +
                                codebox.val().substring(codebox[0].selectionEnd, codebox.val().length));
                    }
                } else if (event.keyCode === 8 || String.fromCharCode(event.charCode).match(/\W/)) {
                    $("#completion").css("display", "none");
                }
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
