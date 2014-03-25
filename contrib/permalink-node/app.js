
/**
 * Module dependencies.
 */

var express = require('express');
var routes = require('./routes');
var http = require('http');
var path = require('path');
var helenus = require('helenus');
var config = require('./config');

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

    app.post('/', routes.set_permalink);
    app.post('/permalink', routes.set_permalink);
    app.get('/', routes.get_permalink);
    app.get('/permalink', routes.get_permalink);


    http.createServer(app).listen(app.get('port'), function(){
	console.log('Express server listening on port ' + app.get('port'));
    });
});
