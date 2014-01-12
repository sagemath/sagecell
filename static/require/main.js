{
    appDir: "/Users/grout/projects/ipython-upstream/IPython/html/static",
    baseUrl: ".",
    dir: "build",

/*    //Put in a mapping so that 'requireLib' in the
    //modules section below will refer to the require.js
    //contents.
    paths: {
        requireLib: 'require'
    },

    //Indicates the namespace to use for require/requirejs/define.
    namespace: "foo",
    modules: [
        {
            name: "foo",
            include: ["requireLib", "main"],
            //True tells the optimizer it is OK to create
            //a new file foo.js. Normally the optimizer
            //wants foo.js to exist in the source directory.
            create: true
        }
    ]
*/

optimize: 'none',
paths: {
    'underscore': 'components/underscore/underscore',
    'backbone': 'components/backbone/backbone',
    'requireLib': 'components/requirejs/require'
},

shim: {
    'underscore': {exports: '_'},
    'backbone': {exports: 'Backbone'}
},
modules: [ {name: "widgets",
	    create: true,
	    include: ["requireLib","notebook/js/widgetmanager", "notebook/js/widgets/init"],
	    insertRequire: ["notebook/js/widgets/init"],
	    override: {
		wrap: {
		    start: "(function(requirejs, require, define, IPython) {",
		    end: "})(sagecell.requirejs, sagecell.require, sagecell.define, IPython);"
		}
	    },
		
	   },
	   {name: "require",
	    create: true,
	    include: ["requireLib"],
	    override: {
	       wrap: {
	       start: "(function() {",
	       end: "sagecell.requirejs=requirejs; sagecell.require=require; sagecell.define=define;})();"
	       }
	    }
	   }

	 ],
}
