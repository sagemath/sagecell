define([
    "jquery",
    "utils"
], function(
    $,
    utils
) {
"use strict";
var undefined;

var ce = utils.createElement;

function InteractControl(dirty_update) {
    return function(control) {
        this.control = control;
        if (typeof dirty_update === "undefined") {
            this.dirty_update = !this.control.update;
        } else {
            this.dirty_update = dirty_update;
        }
        this.eventCount = this.ignoreNext = 0;
    }
}

var Button = InteractControl();

Button.prototype.rendered = function(id) {
    this.button = ce("button", {"id": id}, [this.control.text]);
    this.button.style.width = this.control.width;
    var that = this;
    $(this.button).click(function() {
        that.clicked = true;
        $(that.button).trigger("clickdone");
    });
    $(this.button).button();
    this.clicked = false;
    return this.button;
};

Button.prototype.changeHandlers = function() {
    return {"clickdone": this.button};
};

Button.prototype.json_value = function() {
    var c = this.clicked;
    this.clicked = false;
    return c;
};

Button.prototype.disable = function() {
    $(this.button).button("option", "disabled", true);
};

var ButtonBar = InteractControl();

ButtonBar.prototype.rendered = function(id) {
    var table = ce("table", {"style": "width: auto;"});
    var i = -1;
    this.buttons = $();
    var that = this;
    for (var row = 0; row < this.control.nrows; row++) {
        var tr = ce("tr");
        for (var col = 0; col < this.control.ncols; col++) {
            var button = ce("button", {}, [this.control.value_labels[++i]]);
            button.style.width = this.control.width;
            $(button).click(function(i) {
                return function(event) {
                    that.index = i;
                    $(event.target).trigger("clickdone");
                };
            }(i));
            this.buttons = this.buttons.add(button);
            tr.appendChild(ce("td", {}, [button]));
        }
        table.appendChild(tr);
    }
    this.buttons.first().attr("id", id);
    this.index = null;
    this.buttons.button();
    return table;
};

ButtonBar.prototype.changeHandlers = function() {
    return {"clickdone": this.buttons};
};

ButtonBar.prototype.json_value = function() {
    var i = this.index;
    this.index = null;
    return i;
};

ButtonBar.prototype.disable = function() {
    this.buttons.button("option", "disabled", true);
};

var Checkbox = InteractControl();

Checkbox.prototype.rendered = function(id) {
    this.input = ce("input", {"type": "checkbox", "id": id});
    this.input.checked = this.control["default"];
    return this.input;
};

Checkbox.prototype.changeHandlers = function() {
    return {"change": this.input};
};

Checkbox.prototype.json_value = function() {
    return this.input.checked;
};

Checkbox.prototype.update = function(value) {
    this.input.checked = value;
};

Checkbox.prototype.disable = function() {
    this.input.disabled = true;
};

var ColorSelector = InteractControl();

ColorSelector.prototype.rendered = function() {
    this.selector = ce("span", {"class": "sagecell_colorSelector"});
    var text = document.createTextNode(this.control["default"]);
    this.span = ce("span", {}, [this.selector]);
    if (!this.control.hide_input) {
        this.selector.style.marginRight = "10px";
        this.span.appendChild(text);
    }
    this.selector.style.backgroundColor = this.control["default"];
    var that = this;
    $(this.selector).ColorPicker({
        "color": this.control["default"],
        "onChange": this.change = function(hsb, hex, rgb, el) {
            text.nodeValue = that.color = that.selector.style.backgroundColor = "#" + hex;
        },
        "onHide": function() {
            $(that.span).change();
        }
    });
    return this.span;
};

ColorSelector.prototype.changeHandlers = function() {
    return {"change": this.span};
};

ColorSelector.prototype.json_value = function() {
    return this.color;
};

ColorSelector.prototype.update = function(value) {
    $(this.selector).ColorPickerSetColor(value);
    this.change(undefined, value.substr(1));
};

ColorSelector.prototype.disable = function() {
    $(this.span.firstChild).off("click");
    this.span.firstChild.style.cursor = "default";
};

var HtmlBox = InteractControl(false);

HtmlBox.prototype.rendered = function() {
    this.div = ce("div");
    this.value = this.control.value;
    $(this.div).html(this.control.value);
    return this.div;
};

HtmlBox.prototype.changeHandlers = function() {
    return {};
};

HtmlBox.prototype.json_value = function() {
    return this.value;
};

HtmlBox.prototype.update = function(value) {
    this.value = value;
    $(this.div).html(value);
};

var InputBox = InteractControl();

InputBox.prototype.rendered = function(id) {
    if (this.control.subtype === "textarea") {
        this.textbox = ce("textarea",
            {"rows": this.control.height, "cols": this.control.width});
    } else if (this.control.subtype === "input") {
        this.textbox = ce("input",
            /* Most of the time these will be Sage expressions, so turn all "helpful" features */
            {"size": this.control.width,  "autocapitalize": "off", "autocorrect": "off", "autocomplete": "off"});
    }
    this.textbox.value = this.control["default"];
    this.textbox.id = id;
    if (this.control.evaluate) {
        this.textbox.style.fontFamily = "monospace";
    }
    this.event = this.control.keypress ? "keyup" : "change";
    return this.textbox;
};

InputBox.prototype.changeHandlers = function() {
    var h = {};
    h[this.event] = this.textbox;
    return h;
};

InputBox.prototype.json_value = function() {
    return this.textbox.value;
};

InputBox.prototype.update = function(value) {
    this.textbox.value = value;
};

InputBox.prototype.disable = function() {
    this.textbox.disabled = true;
};

var InputGrid = InteractControl();

InputGrid.prototype.rendered = function(id) {
    this.textboxes = $();
    var table = ce("table", {"style": "width: auto; vertical-align: middle; display: inline-table;"});
    this.button = ce("button", {"style": "vertical-align: middle;"}, ["Submit"]);
    var div = ce("div", {}, [table, this.button]);
    for (var row = 0; row < this.control.nrows; row++) {
        var tr = ce("tr");
        for (var col = 0; col < this.control.ncols; col++) {
            var textbox = ce("input", {"value": this.control["default"][row][col],
                                       "size": this.control.width,
                                       "autocapitalize": "off", "autocorrect": "off", "autocomplete": "off"});
            if (this.control.evaluate) {
                textbox.style.fontFamily = "monospace";
            }
            this.textboxes = this.textboxes.add(textbox);
            tr.appendChild(ce("td", {}, [textbox]));
        }
        table.appendChild(tr);
    }
    this.textboxes.attr("id", id);
    return div;
};

InputGrid.prototype.changeHandlers = function() {
    return {"click": this.button};
};

InputGrid.prototype.json_value = function() {
    var value = [];
    for (var row = 0; row < this.control.nrows; row++) {
        var rowlist = [];
        for (var col = 0; col < this.control.ncols; col++) {
            rowlist.push(this.textboxes[row * this.control.ncols + col].value);
        }
        value.push(rowlist);
    }
    return value;
};

InputGrid.prototype.update = function(value, index) {
    if (index === undefined) {
        var i = -1;
        for (var row = 0; row < value.length; row++) {
            for (var col = 0; col < value[row].length; col++) {
                this.textboxes[++i].value = value[row][col];
            }
        }
    } else {
        this.textboxes[index[0] * this.control.ncols + index[1]].value = value;
    }
};

InputGrid.prototype.disable = function() {
    this.textboxes.prop("disabled", true);
};

var MultiSlider = InteractControl();

MultiSlider.prototype.rendered = function() {
    var div = ce("div");
    this.sliders = $();
    this.value_boxes = $();
    this.values = this.control["default"].slice();
    this.eventCount = 1;
    for (var i = 0; i < this.control.sliders; i++) {
        var column = ce("div");
        column.style.width = "50px";
        column.style.cssFloat = "left";
        column.style.textAlign = "center";
        var slider = ce("span", {"class": "sagecell_multiSliderControl"});
        slider.style.display = "block";
        slider.style.margin = "0.25em 0.5em 1em 0.8em";
        column.appendChild(slider);
        var that = this;
        if (this.control.subtype === "continuous") {
            var textbox = ce("input", {
                "class": "sagecell_interactValueBox",
                "type": "number", 
                "min": this.control.range[i][0],
                "max": this.control.range[i][1],
                "step": "any"
            });
            textbox.value = this.values[i].toString();
            textbox.size = textbox.value.length + 1;
            textbox.style.display = this.control.display_values ? "" : "none";
            $(textbox).change((function(i) {
                return function(event) {
                    var textbox = event.target;
                    var val = parseFloat(textbox.value);
                    if (that.control.range[i][0] <= val && val <= that.control.range[i][1]) {
                        that.values[i] = val;
                        $(that.sliders[i]).slider("option", "value", val);
                        textbox.value = val.toString();
                    } else {
                        textbox.value = that.values[i].toString();
                    }
                    textbox.size = textbox.value.length + 1;
                };
            }(i)));
            $(textbox).keyup(function(event) {
                event.target.size = event.target.value.length + 1;
            });
            that.value_boxes = that.value_boxes.add(textbox);
            column.appendChild(textbox);
        } else {
            var span = ce("span", {}, [this.control.values[i][this.values[i]].toString()]);
            span.style.fontFamily = "monospace";
            span.style.display = this.control.display_values ? "" : "none";
            that.value_boxes = that.value_boxes.add(span);
            column.appendChild(span);
        }
        var slide_handler = (function(i) {
            return function(event, ui) {
                that.values[i] = ui.value;
                var value_box = that.value_boxes[i];
                if (that.control.subtype === "continuous") {
                    value_box.value = ui.value.toString();
                    value_box.size = value_box.value.length + 1;
                    $(value_box).data("old_value", value_box.value);
                } else {
                    $(value_box).text(that.control.values[i][ui.value]);
                }
            };
        }(i));
        $(slider).slider({"orientation": "vertical",
                          "value": this.control["default"][i],
                          "min": this.control.range[i][0],
                          "max": this.control.range[i][1],
                          "step": this.control.step[i]});
        $(slider).on("slide", slide_handler);
        this.sliders = this.sliders.add(slider);
        div.appendChild(column);
    }
    return div;
};

MultiSlider.prototype.changeHandlers = function() {
    return {"slidechange": this.sliders};
};

MultiSlider.prototype.json_value = function() {
    return this.values.slice();
};

MultiSlider.prototype.update = function(value, index) {
    if (index === undefined) {
        this.ignoreNext = value.length;
        for (var i = 0; i < value.length; i++) {
            $(this.sliders[i]).slider("option", "value", value[i]);
            $(this.sliders[i]).trigger("slide", {"value": value[i]});
        }
    } else {
        $(this.sliders[index]).slider("option", "value", value);
        $(this.sliders[index]).trigger("slide", {"value": value});
    }
};

MultiSlider.prototype.disable = function() {
    this.sliders.slider("option", "disabled", true);
    this.value_boxes.prop("disabled", true);
};

var Selector = InteractControl();

Selector.prototype.rendered = function(id) {
    var that = this;
    if (this.control.subtype === "list") {
        var select = ce("select");
        for (var i = 0; i < this.control.values; i++) {
            select.appendChild(ce("option", {}, [this.control.value_labels[i]]));
        }
        this.value = select.selectedIndex = this.control["default"];
        $(select).change(function(event) {
            that.value = event.target.selectedIndex;
            $(event.target).trigger("changedone");
        });
        select.style.width = this.control.width;
        select.id = id;
        this.changing = select;
        return select;
    } else if (this.control.subtype === "radio" || this.control.subtype === "button") {
        this.changing = $();
        var table = ce("table", {"style": "width: auto;"});
        var i = -1;
        for (var row = 0; row < this.control.nrows; row++) {
            var tr = ce("tr");
            for (var col = 0; col < this.control.ncols; col++) {
                var radio_id = id + "_" + (++i);
                var option = ce("input", {"type": "radio", "name": id, "id": radio_id});
                if (i === this.control["default"]) {
                    option.checked = true;
                    this.value = i;
                }
                var label = ce("label", {"for": radio_id}, [this.control.value_labels[i]]);
                label.style.width = this.control.width;
                $(option).change(function(i) {
                    return function(event) {
                        that.value = i;
                        $(event.target).trigger("changedone");
                    };
                }(i));
                this.changing = this.changing.add(option);
                tr.appendChild(ce("td", {}, [option, label]));
            }
            table.appendChild(tr);
        }
        if (this.control.subtype === "button") {
            this.changing.button();
        }
        return table;
    }
};

Selector.prototype.changeHandlers = function() {
    return {"changedone": this.changing};
};

Selector.prototype.json_value = function() {
    return this.value;
};

Selector.prototype.update = function(value) {
    if (this.control.subtype === "list") {
        this.changing.selectedIndex = value;
    } else {
        this.changing[value].checked = true;
        this.changing.button("refresh");
    }
    this.value = value;
};

Selector.prototype.disable = function() {
    if (this.control.subtype === "list") {
        this.changing.disabled = true;
    } else if (this.control.subtype === "radio") {
        this.changing.prop("disabled", true);
    } else {
        this.changing.button("option", "disabled", true);
    }
};

var Slider = InteractControl();

Slider.prototype.rendered = function() {
    this.continuous = this.control.subtype === "continuous" ||
                      this.control.subtype === "continuous_range";
    this.range = this.control.subtype === "discrete_range" ||
                 this.control.subtype === "continuous_range";
    var cell1 = ce("div"), cell2 = ce("div");
    var container = ce("div", {"class": "sagecell_sliderContainer"}, [cell1, cell2]);
    this.value_boxes = $();
    this.eventCount = this.range ? 2 : 1;
    this.slider = ce("div", {"class": "sagecell_sliderControl"});
    cell1.appendChild(this.slider);
    var that = this;
    if (this.continuous) {
        if (this.range) {
            this.values = this.control["default"].slice();
            $(this.slider).slider({"min": this.control.range[0],
                                   "max": this.control.range[1],
                                   "step": this.control.step,
                                   "range": true,
                                   "values": this.values});
            var min_text = ce("input", {
                "class": "sagecell_interactValueBox",
                "type": "number",
                "value": this.values[0].toString(),
                "min": this.control.range[0],
                "max": this.control.range[1],
                "step": "any"
            });
            var max_text = min_text.cloneNode();
            max_text.value = this.values[1].toString();
            min_text.size = min_text.value.length;
            max_text.size = max_text.value.length;
            $(this.slider).on("slide", function(event, ui) {
                that.values = ui.values.slice()
                min_text.value = that.values[0].toString();
                max_text.value = that.values[1].toString();
                min_text.size = min_text.value.length;
                max_text.size = max_text.value.length;
            });
            $(min_text).change(function() {
                var val = parseFloat(min_text.value);
                if (that.control.range[0] <= val &&
                        val <= $(that.slider).slider("option", "values")[1]) {
                    that.values[0] = val;
                    $(that.slider).slider("option", "values", that.values);
                    min_text.value = val.toString();
                } else {
                    min_text.value = that.values[0].toString();
                }
                min_text.size = min_text.value.length + 1;
            });
            $(max_text).change(function() {
                var val = parseFloat(max_text.value);
                if ($(that.slider).slider("option", "values")[0] <= val &&
                        val <= that.control.range[1]) {
                    that.values[1] = val;
                    $(that.slider).slider("option", "values", that.values);
                    max_text.value = val.toString();
                } else {
                    max_text.value = that.values[1].toString();
                }
                max_text.size = max_text.value.length + 1;
            });
            $([min_text, max_text]).keyup(function(event) {
                event.target.size = event.target.value.length + 1;
            });
            $([min_text, max_text]).focus(function(event) {
                event.target.size = event.target.value.length + 1;
            });
            $([min_text, max_text]).blur(function(event) {
                event.target.size = event.target.value.length;
            });
            var div = ce("div", {}, [ "(", min_text, ",", max_text, ")"]);
            div.style.whiteSpace = "nowrap";
            this.value_boxes = $([min_text, max_text]);
            div.style.fontFamily = "monospace";
            cell2.appendChild(div);
        } else {
            this.value = this.control["default"];
            $(this.slider).slider({"min": this.control.range[0],
                                   "max": this.control.range[1],
                                   "step": this.control.step,
                                   "value": this.value});
            var textbox = ce("input", {
                "class": "sagecell_interactValueBox",
                "type": "number",
                "value": this.value.toString(),
                "min": this.control.range[0],
                "max": this.control.range[1],
                "step": "any"
            });
            textbox.size = textbox.value.length + 1;
            $(this.slider).on("slide", function(event, ui) {
                textbox.value = (that.value = ui.value).toString();
                textbox.size = textbox.value.length + 1;
            });
            $(textbox).change(function() {
                var val = parseFloat(textbox.value);
                if (that.control.range[0] <= val && val <= that.control.range[1]) {
                    that.value = val;
                    $(that.slider).slider("option", "value", that.value);
                    textbox.value = val.toString();
                } else {
                    textbox.value = that.value.toString();
                }
                textbox.size = textbox.value.length + 1;
            });
            $(textbox).keyup(function(event) {
                textbox.size = textbox.value.length + 1;
            });
            cell2.appendChild(textbox);
            this.value_boxes = $(textbox);
        }
    } else if (this.range) {
        this.values = this.control["default"].slice();
        $(this.slider).slider({"min": this.control.range[0],
                               "max": this.control.range[1],
                               "step": this.control.step,
                               "range": true,
                               "values": this.values});
        var div = ce("div", {}, ["(" + this.control.values[this.values[0]] +
                                   ", " + this.control.values[this.values[1]] + ")" ]);
        div.style.fontFamily = "monospace";
        div.style.whiteSpace = "nowrap";
        $(this.slider).on("slide", function(event, ui) {
            that.values = ui.values.slice()
            this.values = ui.values.slice();
            $(div).text("(" + that.control.values[that.values[0]] +
                         ", " + that.control.values[that.values[1]] + ")");
        });
        cell2.appendChild(div);
    } else {
        this.value = this.control["default"];
        $(this.slider).slider({"min": this.control.range[0],
                               "max": this.control.range[1],
                               "step": this.control.step,
                               "value": this.value});
        var div = ce("div", {}, [this.control.values[this.value].toString()]);
        div.style.fontFamily = "monospace";
        $(this.slider).on("slide", function(event, ui) {
            $(div).text(that.control.values[that.value = ui.value].toString());
        });
        cell2.appendChild(div);
    }
    return container;
};

Slider.prototype.changeHandlers = function() {
    return {"slidechange": this.slider};
};

Slider.prototype.json_value = function() {
    if (this.range) {
        return this.values.slice();
    } else {
        return this.value;
    }
};

Slider.prototype.update = function(value) {
    if (this.range) {
        value = value.slice();
    }
    $(this.slider).slider("option", (this.range ? "values" : "value"), value);
    var ui = {};
    ui[this.range ? "values" : "value"] = value;
    $(this.slider).trigger("slide", ui);
};

Slider.prototype.disable = function() {
    $(this.slider).slider("option", "disabled", true);
    $(this.value_boxes).prop("disabled", true);
};

return {
    button: Button,
    button_bar: ButtonBar,
    checkbox: Checkbox,
    color_selector: ColorSelector,
    html_box: HtmlBox,
    input_box: InputBox,
    input_grid: InputGrid,
    multi_slider: MultiSlider,
    selector: Selector,
    slider: Slider
};
});
