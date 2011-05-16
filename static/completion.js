function handleKeyEvent(editor, event) {
    if(event.which==9 && !event.shiftKey) {
	var cursor=editor.getCursor();
	if(!editor.getLine(cursor.line).substring(0,cursor.ch).match(/^\s*$/)) {
            $.getJSON("/complete",{
		code: editor.getValue(),
		pos: editor.getRange({line:0, ch:0}, cursor).length
	    },showCompletions);
	    event.stop();
	    return true;
	}
    } else if(event.which==13 && event.shiftKey && event.type=="keypress") {
        $("#evalButton").submit();
	event.stop();
	return true;
    }
    return false;
}

function showCompletions(data,textStatus,jqXHR) {
    $("#completion").text(data.completions.join(", "));
}

function setUpHandler() {
    if($("#commands").length)
        $("#commands").keydown(handleKeyPress);
}