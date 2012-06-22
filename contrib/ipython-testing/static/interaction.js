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
        if (!(textbox.selectionStart !== undefined &&
            textbox.selectionStart === textbox.selectionEnd)) {
            return false;
        }
        var line = cursor_line(textbox.value, textbox.selectionStart);
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

    function update_interact(interact_id, ui) {
        var python_string = "sys._interacts[\"" + interact_id + "\"](";
        var controls = interacts[interact_id].controls;
        var control_args = [];
        for (var c in controls) {
            if (controls.hasOwnProperty(c)) {
                control_args.push(c + "=" + controls[c].evaluator(controls[c].arg, ui));
            }
        }
        python_string += control_args.join(",") + ")";
        should_empty[interact_id] = true;
        test_kernel.set_callbacks_for_msg(last_request[interact_id], {});
        last_request[interact_id] = test_kernel.execute(python_string, {"output": output_callback});
    }

    var interact_evaluators = {
        "input": function (input) {
            return "u" + JSON.stringify(input.value);
        },
        "slider": function (slider, ui) {
            return ui && ui.handle.parentNode === slider ? ui.value : $(slider).slider("option", "value");
        }
    };

    var base_url = "kernel";
    var test_kernel = new IPython.Kernel(base_url);
    var interacts = {undefined: {"output": document.getElementById("output")}};
    var should_empty = {};
    var last_request = {};
    test_kernel.start();
    console.log(test_kernel); // Successful startup
    var output_callback = function (type, content) {
        var output = interacts[content.interact_id].output;
        if (should_empty[content.interact_id]) {
            $(output).empty();
            should_empty[content.interact_id] = false;
        }
        var text;
        if (type === "stream" || type === "pyout" || type === "pyerr") {
            var text;
            if (type === "stream") {
                output.appendChild(document.createTextNode(content.data));
            } else if (type === "pyout") {
                output.appendChild(document.createTextNode(content.data["text/plain"]));
            } else if (type === "pyerr") {
                output.innerHTML += IPython.utils.fixConsole(content.traceback.join("\n"));
            }
            output.normalize();
        } else if (type === "extension" && content.msg_type === "interact_prepare") {
            var interact = document.createElement("div");
            var control_table = document.createElement("table");
            var controls = content.content.controls;
            var control_info = {};
            for (var i = 0; i < controls.length; i++) {
                var name = controls[i][0];
                var control_dict = controls[i][1];
                var row = document.createElement("tr");
                var name_col = document.createElement("td");
                var label = control_dict.label !== null ? control_dict.label : name;
                name_col.appendChild(document.createTextNode(label));
                var control_col = document.createElement("td");
                var control, events;
                if (control_dict.control_type === "input_box") {
                    control = document.createElement("input");
                    control.value = control_dict.default;
                    control_col.appendChild(control);
                    events = "keyup";
                    control_info[name] = {"evaluator": interact_evaluators.input, "arg": control};
                } else if (control_dict.control_type === "slider") {
                    control = document.createElement("div");
                    control.style.width = "300px";
                    control.style.marginLeft = "30px";
                    control.style.display = "inline-block";
                    control.style.marginRight = "20px";
                    $(control).slider({"min": control_dict.min,
                                       "max": control_dict.max,
                                       "step": control_dict.step,
                                       "value": control_dict.default});
                    var value = document.createElement("span");
                    value.appendChild(document.createTextNode(control_dict.default.toString()));
                    control_col.appendChild(control);
                    control_col.appendChild(value);
                    (function (textNode) {
                        $(control).on("slide", function (event, ui) {
                            textNode.nodeValue = ui.value.toString();
                        });
                    }(value.firstChild));
                    events = "slidechange";
                    control_info[name] = {"evaluator": interact_evaluators.slider, "arg": control};
                }
                $(control).on(events, function (event, ui) {
                    update_interact(content.content.new_interact_id, ui);
                });
                row.appendChild(name_col);
                row.appendChild(control_col);
                control_table.appendChild(row);
            }
            var interact_output = document.createElement("div");
            interact_output.style.marginLeft = "2em";
            interact.appendChild(control_table);
            interact.appendChild(interact_output);
            interacts[content.content.new_interact_id] = {"output": interact_output, "controls": control_info};
            output.appendChild(interact);
        }       
    };

    (function f() {
        if (test_kernel.shell_channel === null || test_kernel.iopub_channel === null) {
            var _this = this;
            setTimeout(function(){f.call(_this);}, 200);
        } else {
            var codebox = $("#codebox");
            codebox.keydown(function (event) {
                if (event.keyCode === 900) {
                    event.preventDefault();
                }
            });
            var completions = [];
            codebox.keypress(function (event) {
                if (event.keyCode === 9 && codebox[0].selectionStart !== undefined) {
                    event.preventDefault();
                    var lines = codebox.val().split("\n");
                    var line = cursor_line(codebox.val(), codebox[0].selectionStart);
                    if (should_complete(codebox[0])) {
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
                        var i = codebox[0].selectionStart;
                        codebox.val(codebox.val().substring(0, codebox[0].selectionStart) + "\t" +
                                codebox.val().substring(codebox[0].selectionEnd, codebox.val().length));
                        codebox[0].selectionStart = codebox[0].selectionEnd = i + 1;
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
                } else if (event.keyCode === 13 && event.shiftKey) {
                    event.preventDefault();
                    document.getElementById("completion").style.display = "none";
                    $("#evalbutton").click();
                } else {
                    document.getElementById("completion").style.display = "none"
                }
            });
            $("#codebox").on("click focus", function () {
                document.getElementById("completion").style.display = "none"
            });
            $("#evalbutton").on("click", function(event) {
                should_empty[undefined] = true;
                var code = $("#codebox").val();
                should_empty[undefined] = true;
                test_kernel.set_callbacks_for_msg(last_request[undefined], {});
                last_request[undefined] = test_kernel.execute(code, {"output": output_callback});
            });

        }
    })();

});
