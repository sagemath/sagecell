(function() {
// posEq convenience function from CodeMirror source
function posEq(a, b) {return a.line == b.line && a.ch == b.ch;}


window.cm_widget = {
    init: function(cm, node) {
        /*   
             var cm = CodeMirror.fromTextArea($("#code")[0],
             {mode: "python",
             lineNumbers:true,
             autofocus:true,
             extraKeys: {
             'Ctrl-,': false,
             'Ctrl-.': false
             }
             })
        */
        node.find("#insertinteger").click(function() {new IntegerWidget(cm)});
        node.find("#inserttable").click(function() {new TableWidget(cm)});
        node.find("#insertgraph").click(function() {new GraphWidget(cm)});
        $(cm.getWrapperElement()).keydown('ctrl+.', function(event) {new TableWidget(cm,undefined, {rows:2})});
        $(cm.getWrapperElement()).keydown('ctrl+,', function(event) {new TableWidget(cm,undefined, {columns:2})});
        
        // update the convenient display of text
        //var updateContents = function(cm) { $("#content").text(cm.getValue())};
        //updateContents(cm)
        //cm.on("change", updateContents);
        
        cm.on("cursorActivity", function(cm) {
            if (cm.widgetEnter) {
                // check to see if movement is purely navigational, or if it
                // doing something like extending selection
                var cursorHead = cm.getCursor('head');
                var cursorAnchor = cm.getCursor('anchor');
                if (posEq(cursorHead, cursorAnchor)) {
                    cm.widgetEnter();
                }
                cm.widgetEnter = undefined;
            }
        });
    },
    parseWidgets: function(cm) {
        var d = cm.getValue();
        var start_delimiter = '\u2af7';
        var end_delimiter = '\u2af8';
        var start = d.indexOf(start_delimiter)
        while (start>=0) {
            var end = d.indexOf(end_delimiter, start);
            cm.setSelection(cm.posFromIndex(start), cm.posFromIndex(end+1));
            msg = $.parseJSON(d.slice(start+1,end));
            widget = registry[msg.widget];
            if (widget) {
                var w = new widget(cm, msg);
                end = cm.indexFromPos(w.mark.find().to)
                // creating the widget might have altered the text
                d = cm.getValue()
            }
            start = d.indexOf(start_delimiter, end);
        }
        cm.refresh();
    }
}

var registry = {
    table: TableWidget
    ,integer: IntegerWidget
    ,graph: GraphWidget
};

if ( !Object.create ) {
    // shim for ie8, etc.
    Object.create = function ( o ) {
        function F() {}
        F.prototype = o;
        return new F();
    };
}

function Widget(cm, msg) {
    // the subclass must define this.domNode before calling this constructor
    // and this.type as a string for the widget registry
    var _this = this;
    this.cm = cm;
    if (typeof msg === "undefined") {
        cm.replaceSelection("\u2af7"+cm.getSelection()+"\u2af8");
    }
    var from = cm.getCursor(true);
    var to = cm.getCursor(false);
    this.mark = cm.markText(from, to, {replacedWith: this.domNode});
    if (this.enter) {
        CodeMirror.on(this.mark, "beforeCursorEnter", function(e) {
            // register the enter function 
            // the actual movement happens if the cursor movement was a plain navigation
            // but not if it was a backspace or selection extension, etc.
            var direction = posEq(_this.cm.getCursor(), _this.mark.find().from) ? 'left' : 'right';
            cm.widgetEnter = $.proxy(_this, 'enterIfDefined', direction);
        });
    }
    CodeMirror.on(this.mark, "clear", function(e) {
        // if we don't do this and do:

        // G = <integer widget>
        //
        // 3x3 table widget 

        // then backspace to get rid of table widget,
        // the integer widget disappears until we type on the first
        // line again.  Calling this refresh takes care of things.
        cm.refresh();
    });

    cm.setCursor(to);
    cm.refresh()
}

Widget.prototype.enterIfDefined = function(direction) {
    // check to make sure the mark still exists
    if (this.mark.find()) {
        this.enter(direction);
    }
}

Widget.prototype.range = function() {
    var find = this.mark.find();
    find.from.ch+=1;
    find.to.ch-=1;
    return find;
}
Widget.prototype.setText = function(text) {
    var r = this.range();
    this.cm.replaceRange(text, r.from, r.to);
    // call changed() when widget size changes
    // Likely, this happens a lot when the backing text is changed, so we
    // call it here too.
    this.mark.changed();
}
    Widget.prototype.getText = function() {
    var r = this.range();
    return this.cm.getRange(r.from, r.to);
}

    Widget.prototype.makeMessage = function(data) {
        return {widget: this.widget, data: data}
    }

function IntegerWidget(cm, msg) {
    this.value = 0;
    this.node = $(".widget-templates .integerwidget").clone();
    this.domNode = this.node[0];
    this.widget = "integer";
    _this = this
    Widget.apply(this, arguments);
    
    this.node.find('.inc').click($.proxy(this, 'changeValue', 1))
    this.node.find('.dec').click($.proxy(this, 'changeValue', -1))
    this.node.find('.value').change(function(e) {_this.setValue($(this).val())})

    this.node.keydown('left', function(event) {
        if ($(event.target).getCursorPosition()===0) {
            _this.exit('left');
        }
    });
    this.node.keydown('right', function(event) {
        var t = $(event.target);
        if (t.getCursorPosition()==t.val().length) {
            _this.exit('right');
        }
    });

    if (msg) {
        this.value = msg.data;
    } else {
        var t = this.getText();
        if (t !== "") {
            this.value = parseInt(t);
        }
    }
    // set text to the parsed or default value initially
    this.changeValue(0)

}

IntegerWidget.prototype = Object.create(Widget.prototype)
IntegerWidget.prototype.enter = function(direction) {
    var t = this.node.find('.value');
    t.focus();
    if (direction==='left') {
        t.setCursorPosition(0);
    } else {
        t.setCursorPosition(t.val().length)
    }
}

IntegerWidget.prototype.exit = function(direction) {
    var range = this.mark.find();
    this.cm.focus();
    if (direction==='left') {
        this.cm.setCursor(range.from)
    } else {
        this.cm.setCursor(range.to)
    }
}

IntegerWidget.prototype.changeValue = function(inc) {
    this.setValue(this.value+inc);
}
IntegerWidget.prototype.setValue = function(val) {
    this.value = parseInt(val);
    this.setText(JSON.stringify(this.makeMessage(this.value)));
    this.node.find('.value').val(this.value);
}

function GraphWidget(cm) {
    var _this = this
    this.node = $(".widget-templates .graphwidget").clone();
    this.domNode = this.node[0];
    this.widget = "graph";
    // If this is too big (bigger than codemirror), the scrollCursorIntoView function in CodeMirror completely freezes the browser.
    this.graph = new GraphEditor(this.domNode, {width:100, height:100})
    Widget.apply(this, arguments);

    this.graph.changed = function() {
        var u,v,i;
        var graph = {'widget': 'graph', data: {}};
        graph.data.vertices = _this.graph.nodes.length;
        graph.data.edges = [];
        for (i = 0; i < _this.graph.links.length; i++) {
            u = _this.graph.nodes.indexOf(_this.graph.links[i].source);
            v = _this.graph.nodes.indexOf(_this.graph.links[i].target);
            graph.data.edges.push([u,v]);
        }
        _this.setText(JSON.stringify(graph));
    }
    this.graph.changed();
}
GraphWidget.prototype = Object.create(Widget.prototype)


function TableWidget(cm, msg, options) {
    this.node = $(".widget-templates .tablewidget").clone();
    this.domNode = this.node[0];
    this.widget = "table"
    Widget.apply(this, [cm, msg]);
    _this = this;

    var t = this.node.find('table');

    t.change($.proxy(this, 'updateText'));
    t.keydown('ctrl+.', function(event) {_this.insertRow(event.target); _this.updateText(); event.target.focus(); return false;})
    t.keydown('ctrl+,', function(event) {_this.insertColumn(event.target); _this.updateText(); event.target.focus(); return false;})
    t.keydown('up', $.proxy(this, 'up'));
    t.keydown('down', $.proxy(this, 'down'));
    t.keydown('return', function(event) {
        var target = $(event.target);
        if (target.closest('tr').next().length > 0) {
            _this.down(event);
        } else if (target.closest('td').next().length > 0) {
            // wrap
            target.closest('table')
                .find('tr:eq(0) td:eq('+target.closest('td').next().index()+') input')
                .focus();
        } else {
            _this.exitRight();
        }
        return false;
    });
    t.keydown('left', $.proxy(this, 'left'));
    t.keydown('right', $.proxy(this, 'right'));

    // exit handlers
    t.find('input').first().keydown('shift+tab', $.proxy(this, 'exitLeft'));
    t.find('input').last().keydown('tab', $.proxy(this, 'exitRight'));

    this.updateText();
    var firstinput = t.find('input').first();
    if (typeof msg !== "undefined") {
        options = options || {};
        options.rows = msg.data.length;
        options.columns = msg.data[0].length;
    }
    if (options && options.rows !== undefined) {
        for (var i=1;i<options.rows;i++) {
            this.insertRow(firstinput);
        }
    }
    if (options && options.columns !== undefined) {
        for (var i=1; i<options.columns;i++) {
            this.insertColumn(firstinput);
        }
    }
    if (typeof msg !== "undefined") {
        // fill in values
        var vals = $.map( msg.data, function(n){
            return n;
        });
        t.find('input').each(function(index) {
            $(this).val(vals[index]);
        });
        this.updateText();
    }
    firstinput.focus();
}

TableWidget.prototype = Object.create(Widget.prototype)
TableWidget.prototype.enter = function(direction) {
    var inputs = this.node.find('table').find('input');
    if (direction==='left') {
        inputs.first().focus();
    } else {
        inputs.last().focus();
    }
}
    TableWidget.prototype.up = function(event) {
        var td = $(event.target).closest('td')
        var prevRow = $(td).closest('tr').prev();
        prevRow && prevRow.find('td:eq('+td.index()+') input').focus();
    }
    TableWidget.prototype.down = function(event) {
        var td = $(event.target).closest('td')
        var nextRow = $(td).closest('tr').next();
        nextRow && nextRow.find('td:eq('+td.index()+') input').focus();
    }
    TableWidget.prototype.left = function(event) {
        var t = $(event.target);
        var pos = t.getCursorPosition();
        if (pos===0) {
            var td = $(event.target).closest('td');
            var left = td.prev();
            if (left.length>0) {
                left.find('input').focus();
            } else {
                this.exitLeft();
            }
        }
    }

    TableWidget.prototype.right = function(event) {
        var t = $(event.target);
        var pos = t.getCursorPosition();
        if (pos===t.val().length) {
            var td = $(event.target).closest('td');
            var right = td.next();
            if (right.length>0) {
                right.find('input').focus();
            } else {
                this.exitRight();
            }
        }
    }

TableWidget.prototype.exitLeft = function() {
    this.cm.focus();
    this.cm.setCursor(this.mark.find().from);
    return false;
}

TableWidget.prototype.exitRight = function() {
    this.cm.focus();
    this.cm.setCursor(this.mark.find().to);
    return false;
}

TableWidget.prototype.insertRow = function(target) {
    var tr = $(target).closest('tr');
    var newtr = tr.clone();
    tr.after(newtr);
    // if last tr, we need to remove the event handler and add it to the new last input
    if (newtr.next('tr').length === 0) {
        tr.find('input').last().off('keydown');
        newtr.find('input').last().keydown('tab', $.proxy(this,'exitRight'))
    }
}

TableWidget.prototype.insertColumn = function(target) {
    var target = $(target).closest('td');
    
    var colIndex = target.index();
    var lastCol = target.closest('tr').find('td').get(-1) == target[0];
    var column = target.closest('table').find('tr').find('td:eq('+colIndex+')');
    column.each(function() {$(this).after($(this).clone())});
    // if last column, we need to remove the event handler and add it to the new last input
    if (lastCol) {
        var lastrow = target.closest('table').find('tr').last();
        lastrow.find('input').eq(-2).off('keydown');
        lastrow.find('input').last().keydown('tab', $.proxy(this,'exitRight'))
    }
}

TableWidget.prototype.updateText = function() {
    var matrix = [];
    this.node.find('tr').each(function() {
        var row = [];
        $(this).find('input').each(function() {row.push($(this).val())});
        matrix.push(row);
    });
    this.setText(JSON.stringify(this.makeMessage(matrix)));
}

// From http://stackoverflow.com/a/2897510/1200039
$.fn.getCursorPosition = function() {
    var input = this.get(0);
    if (!input) return; // No (input) element found
    if ('selectionStart' in input) {
        // Standard-compliant browsers
        return input.selectionStart;
    } else if (document.selection) {
        // IE
        input.focus();
        var sel = document.selection.createRange();
        var selLen = document.selection.createRange().text.length;
        sel.moveStart('character', -input.value.length);
        return sel.text.length - selLen;
    }
}

// from http://stackoverflow.com/q/499126/1200039
$.fn.setCursorPosition = function(pos) {
    if ($(this).get(0).setSelectionRange) {
        $(this).get(0).setSelectionRange(pos, pos);
    } else if ($(this).get(0).createTextRange) {
        var range = $(this).get(0).createTextRange();
        range.collapse(true);
        range.moveEnd('character', pos);
        range.moveStart('character', pos);
        range.select();
    }
}

function interpret(n) {
    if (n!== "" && !isNaN(n)) {
        n = +n; // convert n to number
    }
    return n;
}
/***********************************************************************/
/*
 * jQuery Hotkeys Plugin
 * Copyright 2010, John Resig
 * Dual licensed under the MIT or GPL Version 2 licenses.
 *
 * Based upon the plugin by Tzury Bar Yochay:
 * http://github.com/tzuryby/hotkeys
 *
 * Original idea by:
 * Binny V A, http://www.openjs.com/scripts/events/keyboard_shortcuts/
*/

(function(jQuery){
	
	jQuery.hotkeys = {
		version: "0.8",

		specialKeys: {
			8: "backspace", 9: "tab", 13: "return", 16: "shift", 17: "ctrl", 18: "alt", 19: "pause",
			20: "capslock", 27: "esc", 32: "space", 33: "pageup", 34: "pagedown", 35: "end", 36: "home",
			37: "left", 38: "up", 39: "right", 40: "down", 45: "insert", 46: "del", 
			96: "0", 97: "1", 98: "2", 99: "3", 100: "4", 101: "5", 102: "6", 103: "7",
			104: "8", 105: "9", 106: "*", 107: "+", 109: "-", 110: ".", 111 : "/", 
			112: "f1", 113: "f2", 114: "f3", 115: "f4", 116: "f5", 117: "f6", 118: "f7", 119: "f8", 
		    120: "f9", 121: "f10", 122: "f11", 123: "f12", 144: "numlock", 145: "scroll", 191: "/", 224: "meta"
		},
	
		shiftNums: {
			"`": "~", "1": "!", "2": "@", "3": "#", "4": "$", "5": "%", "6": "^", "7": "&", 
			"8": "*", "9": "(", "0": ")", "-": "_", "=": "+", ";": ": ", "'": "\"", ",": "<", 
			".": ">",  "/": "?",  "\\": "|"
		},
            exceptions: {
                186: 59, // ;
                187: 61, // =
                188: 44, // ,
                189: 45, // -
                190: 46, // .
                191: 47, // /
                192: 96, // `
                219: 91, // [
                220: 92, // \
                221: 93, // ]
                222: 39  // '
            }
	};

	function keyHandler( handleObj ) {
		// Only care when a possible input has been specified
		if ( typeof handleObj.data !== "string" ) {
			return;
		}

		var origHandler = handleObj.handler,
			keys = handleObj.data.toLowerCase().split(" ")
	    //textAcceptingInputTypes = ["text", "password", "number", "email", "url", "range", "date", "month", "week", "time", "datetime", "datetime-local", "search", "color"];

		handleObj.handler = function( event ) {
			// Don't fire in text-accepting inputs that we didn't directly bind to
			/*if ( this !== event.target && (/textarea|select/i.test( event.target.nodeName ) ||
				jQuery.inArray(event.target.type, textAcceptingInputTypes) > -1 ) ) {
				return;
			}
                        */

			// Keypress represents characters, not special keys
			var special = event.type !== "keypress" && jQuery.hotkeys.specialKeys[ event.which ],
		    character = String.fromCharCode( jQuery.hotkeys.exceptions[event.which] || event.which ).toLowerCase(),
				key, modif = "", possible = {};

			// check combinations (alt|ctrl|shift+anything)
			if ( event.altKey && special !== "alt" ) {
				modif += "alt+";
			}

			if ( event.ctrlKey && special !== "ctrl" ) {
				modif += "ctrl+";
			}
			
			// TODO: Need to make sure this works consistently across platforms
			if ( event.metaKey && !event.ctrlKey && special !== "meta" ) {
				modif += "meta+";
			}

			if ( event.shiftKey && special !== "shift" ) {
				modif += "shift+";
			}

			if ( special ) {
				possible[ modif + special ] = true;

			} else {
				possible[ modif + character ] = true;
				possible[ modif + jQuery.hotkeys.shiftNums[ character ] ] = true;

				// "$" can be triggered as "Shift+4" or "Shift+$" or just "$"
				if ( modif === "shift+" ) {
					possible[ jQuery.hotkeys.shiftNums[ character ] ] = true;
				}
			}
			for ( var i = 0, l = keys.length; i < l; i++ ) {
				if ( possible[ keys[i] ] ) {
                                    return origHandler.apply( this, arguments );
				}
			}
		};
	}

	jQuery.each([ "keydown", "keyup", "keypress" ], function() {
		jQuery.event.special[ this ] = { add: keyHandler };
	});

})( jQuery );
/************ END Jquery hotkeys plugin *******************/
})()

/* Modified from a d3.js example at http://bl.ocks.org/mbostock/929623 */

function GraphEditor(domNode, options) {
    var options = options || {};
    var width  = options.width || 300;
    var height = options.height || 300;

    var fill = d3.scale.category20();

    var force = d3.layout.force()
        .size([width, height])
        .nodes([{}]) // initialize with a single node
        .linkDistance(30)
        .charge(-60)
        .on("tick", tick);

    var svg = d3.select(domNode).append("svg")
        .attr("width", width)
        .attr("height", height)
        .on("mousemove", mousemove)
        .on("mousedown", mousedown);

    svg.append("rect")
        .attr("width", width)
        .attr("height", height);

    var nodes = force.nodes();
    var links = force.links();
    var obj = {nodes: nodes, links: links};
    var node = svg.selectAll(".node");
    var link = svg.selectAll(".link");

    var cursor = svg.append("circle")
        .attr("r", 30)
        .attr("transform", "translate(-100,-100)")
        .attr("class", "cursor");

    restart();

    function mousemove() {
        cursor.attr("transform", "translate(" + d3.mouse(this) + ")");
    }

    function mousedown() {
        d3.event.stopPropagation();
        var point = d3.mouse(this),
        node = {x: point[0], y: point[1]},
        n = nodes.push(node);

        // add links to any nearby nodes
        nodes.forEach(function(target) {
            var x = target.x - node.x,
            y = target.y - node.y,
            distance = Math.sqrt(x*x+y*y);
            
            if (distance>.1 && distance < 30) {
                links.push({source: node, target: target});
            }
        });
        obj.changed && obj.changed();
        restart();
    }

    function tick() {
        link.attr("x1", function(d) { return d.source.x; })
            .attr("y1", function(d) { return d.source.y; })
            .attr("x2", function(d) { return d.target.x; })
            .attr("y2", function(d) { return d.target.y; });

        node.attr("cx", function(d) { return d.x; })
            .attr("cy", function(d) { return d.y; });
    }

    function restart() {
        link = link.data(links);

        link.enter().insert("line", ".node")
            .attr("class", "link");

        node = node.data(nodes);

        node.enter().insert("circle", ".cursor")
            .attr("class", "node")
            .attr("r", 5)
            .call(force.drag);
        force.start();
    }
    return obj;
}
