
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

    app.post('/', express.bodyParser(), set_permalink);
    app.get('/', get_permalink);
    app.post('/permalink', express.bodyParser(), set_permalink);
    app.get('/permalink', get_permalink);

    http.createServer(app).listen(app.get('port'), function(){
	console.log('Express server listening on port ' + app.get('port'));
    });
});

function set_permalink(req, res, next){
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

function get_permalink (req, res, next) {
    async.waterfall([async.apply(retrieve_permalink,req.query.q)], 
                    function(err, results) {
                        if(err===1) {
                            res.status(404).send("ID not found in permalink database");
                        }
                        if(err) {return next(err);}
	                res.set("Access-Control-Allow-Origin", req.get("Origin") || "*");
	                res.set("Access-Control-Allow-Credentials", "true");
	                res.jsonp(results);
	            })
}


function store_permalink(code, language, interacts, cb) {
    // calls cb(err, ident)
    var count = 0;
    var ident = null;
    async.whilst(
        function () { return (ident === null) && (count < 3); },
        function (callback) {
            count++;
            async.waterfall([
                async.apply(random_string, 5+count),
                function(id, cb) {
                    console.log(count, id);
                    insert_permalink(id, code, language, interacts,
                                     function(err, success) {
                                         // error handling if err is not null
                                         if (err) {
                                             console.log('error inserting permalink',err, success);
                                             return callback(err);
                                         }
                                         if (success) {ident = id;}
                                         callback();
                                     });
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
    // calls cb(err, success), where success is true
    // if insert was successful, false otherwise
    // (probably because the record exists already)

    var query = 'INSERT INTO cellserver.permalinks (ident, code, language, interacts, created, last_access) VALUES (?, ?, ?, ?, dateof(now()), dateof(now())) IF NOT EXISTS;';
    var params = [ident, code, language, interacts];
    pool.cql(query, params, function(err, results) {
        if (err || results.length<1) {return cb(err, false);}
        var success = results[0].get('[applied]').value;
        cb(err, success);
    });
}

function retrieve_permalink(ident, cb) {
/*
- select on ident; return error if ident is not found
- update last_access record
- update permalink_count record
- return code, language, interacts fields

- returns err===1 if there are no results
*/
    var query = 'SELECT ident, code, language, interacts FROM cellserver.permalinks WHERE ident=?;';
    var params = [ident];
    pool.cql(query, params, function(err, results) {
        if(err) {return cb(err, results);}
        if (results.length<1) {return cb(1, results);}
        var row = results[0];
        var code = row.get('code').value || '';
        var language = row.get('language').value || '';
        var interacts = row.get('interacts').value || '';
        cb(err, {code:code, language:language, interacts:interacts});
    });
}


function random_string(ident_len, cb) {
    var valid_chars = "abcdefghijklmnopqrstuwxyz";
    var num_valid = valid_chars.length;
    var value = new Array(ident_len);
    async.waterfall([
        // pseudoRandom because we don't want to error out
        // just give us non-crypto random bytes, please
        async.apply(crypto.pseudoRandomBytes, ident_len),
        function (randbytes, cb) {
            // construct id
            for (var i = 0; i<ident_len; i++) {
                value[i] = valid_chars[randbytes[i] % num_valid]
            }
            cb(null, value.join(''));
        }], cb);
}
