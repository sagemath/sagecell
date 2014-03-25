
/*
 * GET home page.
 */

var zlib = require('zlib');
var async = require('async');

exports.set_permalink = function(req, res){
    var retval = {query: null, zip: null}
    if (req.body.code === undefined) {
	res.send(400);
	return;
    }
    var code = req.body.code;
    var language = req.body.language || "sage";
    var interacts = req.body.interacts || "";
    actions = {
	zip: async.apply(async.waterfall, 
			 [async.apply(zlib.deflate, code),
			 function(b, cb) {cb(null, b.toString('base64'))}]),
	// TODO: do real query method
	query: function(callback) {callback(null, 'FAKEQUERY');}
    }
    if (req.body.interacts) {
	actions.interacts = async.apply(async.waterfall, 
					[async.apply(zlib.deflate, code),
					 function(b, cb) {cb(null, b.toString('base64'))}]);
    }
    async.parallel(actions,
	function(err, results) {
	    if (err) {return next(err);}
	    if (req.body.n) {
		results.n = parseInt(req.body.n);
	    }
	    if (req.body.frame === undefined) {
		res.set("Access-Control-Allow-Origin", req.get("Origin") || "*");
		res.set("Access-Control-Allow-Credentials", "true");
	    } else {
		results = '<script>parent.postMessage('+JSON.stringify(results)+',"*");</script>';
	    }
	    res.send(results);
	}
    );
};

exports.get_permalink = function(req, res) {
    async.series([
	function(cb) {
	    var results = '"Looked up"'+req.query.q;
	    // TODO actually look up results in database
	    cb(null, results);
	}], function(err, results) {
	    res.set("Access-Control-Allow-Origin", req.get("Origin") || "*");
	    res.set("Access-Control-Allow-Credentials", "true");
	    res.jsonp(results);
	})
}
