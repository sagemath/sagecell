define(["jquery", "./utils"], function ($, utils) {
    "use strict";

    var interact_control_throttle = 100;

    function InteractControl() {
        return function (session, control_id) {
            this.session = session;
            this.control_id = control_id;
        };
    }

    /* 
// To implement a new control, do something like the following.  
// See below for examples.  The Checkbox control is particularly simple.

MyControl = InteractControl();
MyControl.prototype.create = function(data, block_id) {
    // The create message is in `data`, while the block id to use for `this.session.output` is in block_id.  
    // This method creates the control and registers any change handlers.
    // Change handlers should send a `variable_update` message back to the server.  This message is handled 
    // by the control's python variable_update method.
};

MyControl.prototype.update = function(namespace, variable, control_id) {
    // If a variable in the namespace is updated (i.e., the client receives a variable update message),
    // this method is called.  The namespace is the UUID of the namespace, the variable is the variable name as a string, 
    // and the control_id is the UUID of the control.  This method should send a message and register a handler for the reply
    // from the control's python update_control method. The reply handler should then update the control appropriately.
};
*/

    var Slider = InteractControl();
    Slider.prototype.create = function (data, block_id) {
        var that = this;
        this.control = this.session.output(
            utils.createElement("div", { id: data.control_id }),
            block_id
        );
        this.control.slider({
            disabled: !data.enabled,
            min: data.min,
            max: data.max,
            step: data.step,
            slide: utils.throttle(function (event, ui) {
                if (!event.originalEvent) {
                    return;
                }
                that.session.send_message(
                    "variable_update",
                    { control_id: data.control_id, value: ui.value },
                    {
                        iopub: {
                            output: $.proxy(
                                that.session.handle_output,
                                that.session
                            ),
                        },
                    }
                );
            }, interact_control_throttle),
        });
    };

    Slider.prototype.update = function (namespace, variable, control_id) {
        var that = this;
        if (this.control_id !== control_id) {
            this.session.send_message(
                "control_update",
                {
                    control_id: this.control_id,
                    namespace: namespace,
                    variable: variable,
                },
                {
                    iopub: {
                        output: $.proxy(
                            this.session.handle_output,
                            this.session
                        ),
                    },
                    shell: {
                        control_update_reply: function (content, metadata) {
                            if (content.status === "ok") {
                                that.control.slider(
                                    "value",
                                    content.result.value
                                );
                            }
                        },
                    },
                }
            );
        }
    };

    var ExpressionBox = InteractControl();
    ExpressionBox.prototype.create = function (data, block_id) {
        var that = this;
        this.control = this.session.output(
            utils.createElement("input", {
                id: data.control_id,
                type: "textbox",
            }),
            block_id
        );
        this.control.change(function (event) {
            if (!event.originalEvent) {
                return;
            }
            that.session.send_message(
                "variable_update",
                { control_id: data.control_id, value: $(this).val() },
                {
                    iopub: {
                        output: $.proxy(
                            that.session.handle_output,
                            that.session
                        ),
                    },
                }
            );
        });
    };

    ExpressionBox.prototype.update = function (
        namespace,
        variable,
        control_id
    ) {
        var that = this;
        this.session.send_message(
            "control_update",
            {
                control_id: this.control_id,
                namespace: namespace,
                variable: variable,
            },
            {
                iopub: {
                    output: $.proxy(this.session.handle_output, this.session),
                },
                shell: {
                    control_update_reply: function (content, metadata) {
                        if (content.status === "ok") {
                            that.control.val(content.result.value);
                        }
                    },
                },
            }
        );
    };

    var Checkbox = InteractControl();
    Checkbox.prototype.create = function (data, block_id) {
        var that = this;
        this.control = this.session.output(
            utils.createElement("input", {
                id: data.control_id,
                type: "checkbox",
            }),
            block_id
        );
        this.control.change(function (event) {
            if (!event.originalEvent) {
                return;
            }
            that.session.send_message(
                "variable_update",
                { control_id: data.control_id, value: $(this).prop("checked") },
                {
                    iopub: {
                        output: $.proxy(
                            that.session.handle_output,
                            that.session
                        ),
                    },
                }
            );
        });
    };

    Checkbox.prototype.update = function (namespace, variable, control_id) {
        var that = this;
        this.session.send_message(
            "control_update",
            {
                control_id: this.control_id,
                namespace: namespace,
                variable: variable,
            },
            {
                iopub: {
                    output: $.proxy(this.session.handle_output, this.session),
                },
                shell: {
                    control_update_reply: function (content, metadata) {
                        if (content.status === "ok") {
                            that.control.prop("checked", content.result.value);
                        }
                    },
                },
            }
        );
    };

    var OutputRegion = InteractControl();
    OutputRegion.prototype.create = function (data, block_id) {
        var that = this;
        this.control = this.session.output(
            utils.createElement("div", { id: data.control_id }),
            block_id
        );
        this.session.output_blocks[this.control_id] = this.control;
        this.message_number = 1;
    };

    OutputRegion.prototype.update = function (namespace, variable, control_id) {
        var that = this;
        this.message_number += 1;
        var msg_number = this.message_number;
        this.session.send_message(
            "control_update",
            {
                control_id: this.control_id,
                namespace: namespace,
                variable: variable,
            },
            {
                iopub: {
                    output: function (msg) {
                        if (msg_number === that.message_number) {
                            $.proxy(that.session.handle_output, that.session)(
                                msg,
                                that.control_id
                            );
                        }
                    },
                },
            }
        );
    };

    return {
        Slider: Slider,
        ExpressionBox: ExpressionBox,
        Checkbox: Checkbox,
        OutputRegion: OutputRegion,
    };
});
