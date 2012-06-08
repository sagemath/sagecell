$(function() {
var canvas = $('#mycanvas');
var divnum = 0;
var celltemplate = {
    hide: ['messages', 'sagemode', 'files', 'computationID', 'permalink']
};
canvas.click(function(e) {
    if (e.target !== this) {
        return;
    }
    var id = 'cell'+divnum;
    var newcell = $('<div class="cell clearfix" id="'+id+'">print ' + divnum + '</div>').appendTo(canvas).offset({
        top: e.offsetY,
        left: e.offsetX
    });
    sagecell.makeSagecell({
        inputLocation: newcell,
        template: celltemplate
    });
    divnum += 1;

});

})
