function handleKeyEvent(editor, event, n) {
    if(event.which==9 && !event.shiftKey) {
	var cursor=editor.getCursor();
	if(!editor.getLine(cursor.line).substring(0,cursor.ch).match(/^\s*$/)) {
            $.getJSON("/complete",{
		code: editor.getValue(),
		pos: editor.getRange({line:0, ch:0}, cursor).length
	    },add_args(showCompletions,n));
	    event.stop();
	    return true;
	}
    } else if(event.which==13 && event.shiftKey && event.type=="keypress") {
        $("#eval"+n).click();
	event.stop();
	return true;
    }
    return false;
}

function showCompletions(data,textStatus,jqXHR,n) {
    $("#completions"+n).text(data.completions.join(", "));
}