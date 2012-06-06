

$(function() {
    var base_url = "kernel";

    var test_kernel = new IPython.Kernel(base_url);

    test_kernel.start();

    console.log(test_kernel); // Successful startup

    var execute_reply_callback = function(msg) {
        console.log("exec_reply");
        console.log(msg);
    };
    var output_callback = function(msg) {
        console.log("output");
        console.log(msg);
    };
    var clear_output_callback = function(msg) {
        console.log("clear output");
        console.log(msg);
    };
    var callbacks = {
        "execute_reply": execute_reply_callback,
        "output": output_callback,
        "clear_output": clear_output_callback,
        "cell": 0
    };

    (function() {
        if (test_kernel.shell_channel === null || test_kernel.iopub_channel === null) {
            var fn = arguments.callee;
            var _this = this;
            setTimeout(function(){fn.call(_this);}, 200);
        } else {

            $("#evalbutton").on("click", function(event) {
                $("#message_output").empty();
                var code = $("#codebox").val();
                test_kernel.execute(code, callbacks);
            });

            $("#restartbutton").on("click", function(event) {
                alert("This doesn't do anything right now ....");
            });

        }
    })();

});