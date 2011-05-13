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
    // This variable is closed over in scope so it doesn't pollute the global scope
    var sequence=0;
    // Attach a javascript function to the form submit. This function
    // makes an AJAX call to evaluate the contents of the text box.
    $('#command_form').submit(function () {
        $.getJSON($URL.evaluate, {commands: $('#commands').val()}, send_computation_success);
        return false;
    });

function send_computation_success(data, textStatus, jqXHR) {
    $("#computation_id").text(data.computation_id);
    // start long-polling to get the output
    // TODO: look at maybe using something like https://github.com/RobertFischer/JQuery-PeriodicalUpdater/
    get_output(data.computation_id);
}

function get_output(id) {
    $.getJSON($URL.output_poll, {computation_id: id, sequence: sequence},
              function(data, textStatus, jqXHR) {
                  get_output_success(data, textStatus, jqXHR, id);});
}

function get_output_success(data, textStatus, jqXHR, id) {
    var done=false;

    if(data!==undefined && data.content!==undefined) {
        var content = data.content;
        for (var i = 0; i < content.length; i++) {
            msg=content[i];
            if(msg.sequence!==sequence) {
                //TODO: Make a big warning sign
                console.log('sequence is out of order; I think it should be '+sequence+', but server claims it is '+msg.sequence);
            }
            sequence+=1;
            if(msg.msg_type==='execute_reply' ||(msg.msg_type==='status' && msg.content.execution_state==='idle')) {
                done=true;
                sequence=0;
            }
            // Handle each stream type.  This should probably be separated out into different functions.
            if(msg.msg_type==='stream'){

                switch(msg.content.name) {
                case 'stdout':
                    $('#output').append("<pre class='stdout'>"+msg.content.data+"</pre>");
                    break;

                case 'stderr':
                    $('#output').append("<pre class='stderr'>"+msg.content.data+"</pre>");
                    break;

               
                }
            } else if(msg.msg_type==='pyout') {
                $('#output').append("<pre class='pyout'>"+msg.content.data['text/plain']+"</pre>")
            } else if(msg.msg_type==='display_data') {
                if(msg.content.data['image/svg+xml']!==undefined) {
                    $('#output').append('<object id="svgImage" type="image/svg+xml">'+msg.content.data['image/svg+xml']+'</object>');
                } else if(msg.content.data['text/html']!==undefined) {
		    $('#output').append('<div>'+msg.content.data['text/html']+'</div>');
		}
            } else if(msg.msg_type==='files') {
		var html="<div>\n";
		for(var j in msg.content.files)
		    html+="<a href=\"/files/"+id+"/"+msg.content.files[j]+"\">"+
		          msg.content.files[j]+"</a><br>\n";
		$('#output').append(html);
	    }
	    
	    // Append the message to the div of messages
	    $('#messages').append(document.createElement('div'))
		.children().last().text(JSON.stringify(msg));
            //TODO: handle all the types of messages intelligently
        }
    }
/*
    for(d in data.output) {
            if(d!="closed")
                streams.push(data.output[d]);
    }
    streams.sort(sortstream);
    //$('#output').empty();
    for(i in streams)
        if(streams[i].type=='text')
            $('#output').append("<pre>"+streams[i].content+"</pre>");
        else if(streams[i].type=='image')
            for(j in streams[i].files)
                $('#output').append("<img src='/files/"+id+"/"+streams[i].files[j]+"'/><br/>");
        else if(streams[i].type=='files') {
            var toAppend="<div>";
            for(j in streams[i].files)
                toAppend+="<a href='/files/"+id+"/"+streams[i].files[j]+"'>"+
                    streams[i].files[j]+"</a><br/>";
            $('#output').append(toAppend+"</div>");
        }
        else if(streams[i].type=='error')
            $('#output').append("<pre class='error'>"+streams[i].ename+"<br/>"+streams[i].evalue+"</pre>")
          if(data.output && !data.output.closed)
              $('#output').append("&hellip;")
*/
    if(!done) {
        // poll again after a bit
        setTimeout(function() {get_output(id);}, 2000);
    }
}

});

function get_output_long_poll(id) {
    $.getJSON($URL.output_long_poll, {computation_id: id, timeout: 2},
              function(data, textStatus, jqXHR) {
                  get_output_success(data, textStatus, jqXHR, id);});
}

function get_output_long_poll_success(data, textStatus, jqXHR, id) {
    //alert(data);
    if(data.output==undefined) {
        get_output(id);
    }
    $('#output').text(data.output)
}


