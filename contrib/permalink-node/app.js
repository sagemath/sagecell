
/**
 * Module dependencies.
 */

var express = require('express');
var http = require('http');
var path = require('path');
var helenus = require('helenus');
var config = require('./config');
var zlib = require('zlib');
var async = require('async');
var crypto = require('crypto');

var app = express();
var pool = new helenus.ConnectionPool(config.cassandra_config);

pool.connect(function(err){
    if(err){
	throw(err);
    }
    // all environments
    app.set('port', process.env.PORT || 3000);
    app.use(express.logger('dev'));
    app.use(express.json());
    app.use(express.urlencoded());
    app.use(express.methodOverride());
    app.use(app.router);

    // development only
    if ('development' == app.get('env')) {
	app.use(express.errorHandler());
    }

    app.post('/', set_permalink);
    app.get('/', get_permalink);
    app.post('/permalink', set_permalink);
    app.get('/permalink', get_permalink);

    http.createServer(app).listen(app.get('port'), function(){
	console.log('Express server listening on port ' + app.get('port'));
    });
});

function set_permalink(req, res){
    var retval = {query: null, zip: null}
    if (req.body.code === undefined) {
	res.send(400);
	return;
    }
    var code = req.body.code || "";
    var language = req.body.language || "sage";
    var interacts = req.body.interacts || "";
    var query_ident = null;
    actions = {
	zip: async.apply(async.waterfall, 
			 [async.apply(zlib.deflate, code),
			 function(b, cb) {cb(null, b.toString('base64'))}]),
	query: async.apply(store_permalink, code, language, interacts)
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

function get_permalink (req, res) {
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

function retrieve_permalink(ident, cb) {
/*
- select on ident; return error if ident is not found
- update last_access record
- update permalink_count record
- return code, language, interacts fields
*/

}

function store_permalink(code, language, interacts, cb) {
    // calls cb(err, ident)
    var count = 0;
    debugger;
    var ident = null;
    async.whilst(
        function () { return (ident === null) && (count < 3); },
        function (callback) {
            count++;
            async.waterfall([
                async.apply(random_string, count),
                function(id, cb) {
                    console.log(count, id);
                    insert_permalink(id, code, language, interacts, function(err, results) {
                        console.log(err, results[0].get('ident'));
                        if (err || !results[0].get('[applied]')) {
                            // continue
                            callback();
                        } else {
                            // break
                            ident = id;
                            callback();
                        }
                    })
                }
            ]);
        },
        function (err) {
            if (ident===null) {
                cb(true, null)
            } else {
                cb(null, ident);
            }
        }
    );
}

function insert_permalink(ident, code, language, interacts, cb) {
    var query = 'INSERT INTO cellserver.permalinks (ident, code, language, interacts, created, last_access) VALUES (?, ?, ?, ?, dateof(now()), dateof(now())) IF NOT EXISTS;';
    var params = [ident, code, language, interacts];
    pool.cql(query, params, cb);
}

function random_string(ident_len, cb) {
    var valid_chars = "012345679";//"abcdefghijklmnopqrstuwxyz";
    var num_valid = valid_chars.length;
    var value = new Array(ident_len);
    async.waterfall([
        // pseudoRandom because we don't want to error out---just give us non-crypto random bytes, please
        async.apply(crypto.pseudoRandomBytes, ident_len),
        function (randbytes, cb) {
            // construct id
            for (var i = 0; i<ident_len; i++) {
                value[i] = valid_chars[randbytes[i] % num_valid]
            }
            cb(null, value.join(''));
        }], cb);
}

