function handleKeyPress(event) {
    if(event.which==9) {
        event.preventDefault();
        var box=event.target;
        var i=box.value.lastIndexOf("\n",box.selectionStart-1);
        if(!box.value.substring(i,box.selectionStart).match(/^\s*$/)) {
            $.getJSON("/complete",{code:box.value, pos:box.selectionStart},showCompletions);
	}
        else {
            // Insert a tab at the current position and reset the cursor position
            var start=box.selectionStart;
            box.value=box.value.substring(0,start)+"\t"+box.value.substring(start);
            box.selectionStart=box.selectionEnd=start+1;
        }
    } else if(event.which==13 && event.shiftKey) {
        event.preventDefault();
        $("#evalButton").submit();
    }
}

function showCompletions(data,textStatus,jqXHR) {
    $("#completion").text(data.completions.join(", "));
}

function setUpHandler() {
    if($("#commands").length)
        $("#commands").keydown(handleKeyPress);
}

$(document).ready(setUpHandler);
