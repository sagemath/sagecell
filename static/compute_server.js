// From sagenb/sagenb/data/sage/js/async_lib.js

function generic_callback(status, response_text) {
    /* do nothing */
}

function async_request(url, callback, postvars) {
    var settings = {
        url : url,
        async : true,
        cache : false,
        dataType: "json"
    };

    if ($.isFunction(callback)) {
        settings.error = function (jqXHR, textStatus, errorThrown) {
            callback("failure", errorThrown);
        };
        settings.success = function (data, textStatus, jqXHR) {
            callback("success", data, jqXHR);
        };
    }

    if (postvars) {
        settings.type = "POST";
        settings.data = postvars;
    } else {
        settings.type = "GET";
    }

    $.ajax(settings);
}


function send_computation_error(jqXHR, textStatus, errorThrown) {
    alert(textStatus);
}

function send_computation_success(data, textStatus, jqXHR) {
    $("#computation_id").text(data.computation_id);
    // start long-polling to get the output
    poll_for_output(data.computation_id);
}

function get_output(id) {
    $.getJSON($OUTPUT_URL, {computation_id: id, timeout: 5},
	      function(data, textStatus, jqXHR) {
		  get_output_success(data, textStatus, jqXHR, id);});
}

function get_output_success(data, textStatus, jqXHR, id) {
    alert(data);
    get_output(id);
}

$(function() {
    $('#command_form').submit(function () {
	$.getJSON($EVALUATE_URL, {commands: $('#commands').val()}, send_computation_success);
	return false;
    });
});

