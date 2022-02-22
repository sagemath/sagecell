import $ from "jquery";
import InteractData from "./interact_data";
import utils from "./utils";

import "base/js/events";

var ce = utils.createElement;

var stop = function (event) {
    event.stopPropagation();
};
var close = null;

function InteractCell(session, data, parent_block) {
    this.interact_id = data.new_interact_id;
    this.function_code = data.function_code;
    this.controls = {};
    this.session = session;
    this.parent_block = parent_block;
    this.layout = data.layout;
    this.locations = data.locations;
    this.msg_id = data.msg_id;
    this.changed = [];

    var controls = data.controls;
    for (var name in controls) {
        if (controls.hasOwnProperty(name)) {
            this.controls[name] = new InteractData[controls[name].control_type](
                controls[name]
            );
        }
    }
    this.session.interact_pl.style.display = "block";
    this.renderCanvas(parent_block);
    this.bindChange();
    if (data.readonly) {
        this.disable();
    }
}

InteractCell.prototype.newControl = function (data) {
    this.controls[data.name] = new InteractData[data.control.control_type](
        data.control
    );
    this.placeControl(data.name);
    this.bindChange(data.name);
    if (this.output_block && this.controls[data.name].dirty_update) {
        $(this.cells[data.name]).addClass("sagecell_dirtyControl");
    }
    if (this.parent_block === null) {
        this.session.updateLinks(true);
    }
};

InteractCell.prototype.delControl = function (data) {
    delete this.controls[data.name];
    var tr = this.cells[data.name].parentNode;
    tr.parentNode.removeChild(tr);
    delete this.cells[data.name];
    if (this.parent_block === null) {
        this.session.updateLinks(true);
    }
};

InteractCell.prototype.bindChange = function (cname) {
    var that = this;
    var handler = function (event, ui) {
        if (that.controls[event.data.name].ignoreNext > 0) {
            that.controls[event.data.name].ignoreNext--;
            return;
        }
        if (that.changed.indexOf(event.data.name) === -1) {
            that.changed.push(event.data.name);
        }
        var msg_dict = {
            interact_id: that.interact_id,
            values: {},
            update_last: false,
            user_expressions: { _sagecell_files: "sys._sage_.new_files()" },
        };
        msg_dict.values[event.data.name] =
            that.controls[event.data.name].json_value(ui);
        if (that.controls[event.data.name].dirty_update) {
            $(that.cells[event.data.name]).addClass("sagecell_dirtyControl");
        }
        var callbacks = {
            iopub: {
                output: $.proxy(that.session.handle_output, that.session),
            },
            shell: {
                reply: $.proxy(that.session.handle_execute_reply, that.session),
            },
        };
        that.session.send_message(
            "sagenb.interact.update_interact",
            msg_dict,
            callbacks
        );
        if (this.parent_block === null) {
            that.session.updateLinks(true);
        }
    };
    if (cname === undefined) {
        for (var name in this.controls) {
            if (this.controls.hasOwnProperty(name)) {
                var events = this.controls[name].changeHandlers();
                for (var e in events) {
                    if (events.hasOwnProperty(e)) {
                        $(events[e]).on(e, { name: name }, handler);
                    }
                }
            }
        }
    } else {
        var events = this.controls[cname].changeHandlers();
        for (var e in events) {
            if (events.hasOwnProperty(e)) {
                $(events[e]).on(e, { name: cname }, handler);
            }
        }
    }
};

InteractCell.prototype.placeControl = function (name) {
    var control = this.controls[name];
    var id = this.interact_id + "_" + name;
    var div = this.cells[name];
    if (div === undefined) {
        var rdiv = ce("div");
        div = this.cells[name] = ce("div", {
            class: "sagecell_interactControlCell",
        });
        div.style.width = "90%";
        rdiv.appendChild(div);
        if (this.output_block) {
            var outRow = this.output_block.parentNode.parentNode;
            outRow.parentNode.insertBefore(rdiv, outRow);
        } else {
            $(this.container).append(rdiv);
        }
    }
    if (control.control.label.length > 0) {
        div.appendChild(
            ce(
                "label",
                {
                    class: "sagecell_interactControlLabel",
                    for: id,
                    title: name,
                },
                [control.control.label]
            )
        );
    }
    div.appendChild(
        ce("div", { class: "sagecell_interactControl" }, [control.rendered(id)])
    );
};

var textboxItem = function (defaultVal, callback) {
    var input = ce("input", {
        value: defaultVal,
        placeholder: "Bookmark name",
    });
    input.addEventListener("keydown", stop);
    input.addEventListener("keypress", function (event) {
        if (event.keyCode === 13) {
            callback();
            event.preventDefault();
        }
        event.stopPropagation();
    });
    var div = ce("div", {
        title: "Add bookmark",
        tabindex: "0",
        role: "button",
    });
    div.addEventListener("click", callback);
    return ce("li", { class: "ui-state-disabled" }, [
        ce("a", {}, [input, div]),
    ]);
};

var selectAll = function (txt) {
    txt.selectionStart = 0;
    txt.selectionEnd = txt.value.length;
    txt.selectionDirection = "forward";
};

InteractCell.prototype.renderCanvas = function (parent_block) {
    this.cells = {};
    this.container = ce("div", { class: "sagecell_interactContainer" });
    if (this.layout && this.layout.length > 0) {
        for (var row = 0; row < this.layout.length; row++) {
            var rdiv = ce("div");
            var total = 0;
            for (var col = 0; col < this.layout[row].length; col++) {
                total += this.layout[row][col][1];
            }
            for (var col = 0; col < this.layout[row].length; col++) {
                var cdiv = ce("div", {
                    class: "sagecell_interactControlCell",
                });
                cdiv.style.width =
                    (100 * this.layout[row][col][1]) / total + "%";
                if (this.layout[row][col] !== undefined) {
                    this.cells[this.layout[row][col][0]] = cdiv;
                    if (this.layout[row][col][0] === "_output") {
                        this.output_block = ce("div", {
                            class: "sagecell_interactOutput",
                        });
                        cdiv.appendChild(this.output_block);
                    }
                }
                rdiv.appendChild(cdiv);
            }
            this.container.appendChild(rdiv);
        }
    }
    if (this.locations) {
        for (var name in this.locations) {
            if (this.locations.hasOwnProperty(name)) {
                this.cells[name] = $("body")
                    .find(this.locations[name])
                    .slice(0, 1)
                    .empty()[0];
                if (name === "_output") {
                    this.output_block = this.cells[name];
                    $(this.output_block).addClass("sagecell_interactOutput");
                } else if (name === "_bookmarks") {
                    this.bookmark_container = this.cells[name];
                }
            }
        }
    }
    for (var name in this.controls) {
        if (this.controls.hasOwnProperty(name)) {
            this.placeControl(name);
        }
    }
    var menuBar = ce("div", { class: "sagecell_bookmarks" });
    var expText = ce("input", {
        title: "Pass this string to the interact proxy\u2019s _set_bookmarks method.",
        readonly: "",
    });
    var expButton = ce("div", {
        title: "Export bookmarks",
        tabindex: "0",
        role: "button",
    });
    expText.style.display = "none";
    expText.addEventListener("focus", function (event) {
        selectAll(expText);
    });
    var starButton = ce("div", {
        title: "Bookmarks",
        tabindex: "0",
        role: "button",
    });
    this.set_export = function () {
        var b = [];
        for (var i = 0; i < this.bookmarks.childNodes.length; i++) {
            var li = this.bookmarks.childNodes[i];
            var node = li.firstChild.firstChild.firstChild;
            if (node !== null) {
                b.push([node.nodeValue, $(li).data("values")]);
            }
        }
        expText.value = JSON.stringify(JSON.stringify(b));
    };
    var list = ce("ul", { class: "sagecell_bookmarks_list" });
    var that = this;
    menuBar.addEventListener("mousedown", stop);
    expButton.addEventListener("click", function () {
        expText.style.display = "";
        expText.focus();
        selectAll(expText);
        $(expButton).removeClass("sagecell_export");
    });
    menuBar.appendChild(expButton);
    menuBar.appendChild(expText);
    menuBar.appendChild(starButton);
    this.bookmark_container = this.bookmark_container || this.container;
    this.bookmark_container.appendChild(menuBar);
    this.bookmarks = list;
    list.addEventListener("mousedown", stop, true);
    this.set_export();
    var visible = false;
    var tb;
    var hide_box = function hide_box() {
        list.parentNode.removeChild(list);
        list.removeChild(tb);
        $(expButton).removeClass("sagecell_export");
        expText.style.display = "none";
        window.removeEventListener("mousedown", hide_box);
        visible = false;
        close = null;
    };
    $(list).menu({
        select: function (event, ui) {
            that.state(ui.item.data("values"));
            hide_box();
        },
    });
    var handler = function (event) {
        if (visible) {
            return;
        }
        (function addTextbox() {
            var n = 1;
            while (true) {
                for (var i = 0; i < list.childNodes.length; i++) {
                    if (
                        list.childNodes[i].firstChild.firstChild.firstChild
                            .nodeValue ===
                        "Bookmark " + n
                    ) {
                        break;
                    }
                }
                if (i === list.childNodes.length) {
                    break;
                }
                n++;
            }
            tb = textboxItem("Bookmark " + n, function () {
                list.removeChild(tb);
                that.createBookmark(tb.firstChild.firstChild.value);
                addTextbox();
            });
            list.appendChild(tb);
            $(list).menu("refresh");
            setTimeout(function () {
                var input = list.lastChild.firstChild.firstChild;
                input.selectionStart = 0;
                input.selectionEnd = input.value.length;
                input.selectionDirection = "forward";
                input.focus();
            }, 0);
        })();
        visible = true;
        that.session.outputDiv.append(list);
        if (close) {
            close();
        }
        close = hide_box;
        $(list).position({
            my: "right top",
            at: "right bottom+5px",
            of: starButton,
        });
        $(expButton).addClass("sagecell_export");
        expButton.style.display = "inline-block";
        window.addEventListener("mousedown", hide_box);
        event.stopPropagation();
    };
    starButton.addEventListener("mousedown", handler);
    this.disable_bookmarks = function () {
        starButton.removeEventListener("mousedown", handler);
        starButton.setAttribute("aria-disabled", "true");
        starButton.removeAttribute("tabindex");
    };
    if (this.layout && this.layout.length > 0) {
        this.session.output(this.container, parent_block);
    }
};

InteractCell.prototype.updateControl = function (data) {
    if (this.controls[data.control].update) {
        this.controls[data.control].ignoreNext =
            this.controls[data.control].eventCount;
        this.controls[data.control].update(data.value, data.index);
        if (this.output_block && this.controls[data.control].dirty_update) {
            $(this.cells[data.control]).addClass("sagecell_dirtyControl");
        }
        if (this.parent_block === null) {
            this.session.updateLinks(true);
        }
    }
};

InteractCell.prototype.state = function (vals, callback) {
    if (vals === undefined) {
        vals = {};
        for (var n in this.controls) {
            if (this.controls.hasOwnProperty(n) && this.controls[n].update) {
                vals[n] = this.controls[n].json_value();
            }
        }
        return vals;
    } else {
        for (var n in vals) {
            if (vals.hasOwnProperty(n) && this.controls.hasOwnProperty(n)) {
                this.controls[n].ignoreNext = this.controls[n].eventCount;
                this.controls[n].update(vals[n]);
            }
        }
        var msg_dict = {
            interact_id: this.interact_id,
            values: vals,
            update_last: true,
        };
        var callbacks = {
            iopub: {
                output: $.proxy(this.session.handle_output, this.session),
            },
            shell: {
                "sagenb.interact.update_interact_reply":
                    callback ||
                    $.proxy(this.session.handle_message_reply, this.session),
            },
        };
        this.session.send_message(
            "sagenb.interact.update_interact",
            msg_dict,
            callbacks
        );
    }
};

InteractCell.prototype.createBookmark = function (name, vals) {
    if (vals === undefined) {
        vals = this.state();
    }
    var del = ce("div", {
        title: "Delete bookmark",
        tabindex: "0",
        role: "button",
    });
    var entry = ce("li", {}, [ce("a", {}, [ce("div", {}, [name]), del])]);
    var that = this;
    del.addEventListener("click", function (event) {
        that.bookmarks.removeChild(entry);
        if (that.parent_block === null) {
            that.session.updateLinks(true);
        }
        that.set_export();
        event.stopPropagation();
    });
    $(entry).data({ values: vals });
    var tbEntry;
    if (
        this.bookmarks.hasChildNodes() &&
        !this.bookmarks.lastChild.firstChild.firstChild.hasChildNodes()
    ) {
        tbEntry = this.bookmarks.removeChild(this.bookmarks.lastChild);
    }
    this.bookmarks.appendChild(entry);
    if (tbEntry) {
        this.bookmarks.appendChild(tbEntry);
    }
    $(this.bookmarks).menu("refresh");
    if (this.parent_block === null) {
        this.session.updateLinks(true);
    }
    this.set_export();
};

InteractCell.prototype.clearBookmarks = function () {
    var tbEntry;
    if (
        this.bookmarks.hasChildNodes() &&
        !this.bookmarks.lastChild.firstChild.firstChild.hasChildNodes()
    ) {
        tbEntry = this.bookmarks.removeChild(this.bookmarks.lastChild);
    }
    while (this.bookmarks.hasChildNodes()) {
        this.bookmarks.removeChild(this.bookmarks.firstChild);
    }
    if (tbEntry) {
        this.bookmarks.appendChild(tbEntry);
    }
};

InteractCell.prototype.disable = function () {
    this.disable_bookmarks();
    for (var name in this.controls) {
        if (this.controls.hasOwnProperty(name) && this.controls[name].disable) {
            this.controls[name].disable();
        }
    }
};

export default InteractCell;
export { InteractCell };
