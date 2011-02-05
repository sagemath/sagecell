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


$(function() {
    // Attach a javascript function to the form submit. This function
    // makes an AJAX call to evaluate the contents of the text box.
    $('#command_form').submit(function () {
	$.getJSON($EVALUATE_URL, {commands: $('#commands').val()}, send_computation_success);
	return false;
    });
});

function send_computation_success(data, textStatus, jqXHR) {
    $("#computation_id").text(data.computation_id);
    // start long-polling to get the output
    // TODO: look at maybe using something like https://github.com/RobertFischer/JQuery-PeriodicalUpdater/
    get_output(data.computation_id);
}

function get_output(id) {
    $.getJSON($OUTPUT_URL, {computation_id: id, timeout: 2},
	      function(data, textStatus, jqXHR) {
		  get_output_success(data, textStatus, jqXHR, id);});
}

function get_output_success(data, textStatus, jqXHR, id) {
    //alert(data);
    if(data.output==undefined) {
	get_output(id);
    }
    $('#output').text(data.output)
}


