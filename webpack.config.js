const webpack = require("webpack");
const path = require("path");

module.exports = {
    entry: "./js/main.js",
    output: {
        filename: "./embedded_sagecell.js",
        path: path.resolve(__dirname, "build"),
    },
    // Enable sourcemaps for debugging webpack's output.
    devtool: "source-map",
    resolve: {
        extensions: ["", ".webpack.js", ".web.js", ".js"],
        modules: ["build/vendor", "node_modules"],
    },
    module: {
        rules: [
            {
                test: /\.m?js$/,
                exclude: /(node_modules|bower_components|JSmol.js)/,
                use: {
                    loader: "babel-loader",
                    options: {
                        presets: ["@babel/preset-env"],
                        plugins: ["@babel/plugin-transform-modules-amd"],
                    },
                },
            },
            // JSmol.js is not written in strict mode, so the babel-loader
            // will error if it is imported. Instead we directly load
            // it in an unprocessed form.
            { test: /JSmol.js$/, loader: "source-map-loader" },
            {
                test: /\.(html|css)$/i,
                use: "raw-loader",
            },
        ],
    },
    plugins: [
        new webpack.ProvidePlugin({
            jQuery: "jquery",
            $: "jquery",
            // Normally the following lines are used to make sure that jQuery
            // cannot "leak" into the outside environment. However, since
            // we *want* to initialize the global jQuery object, we omit them.
            // "window.jQuery": "jquery",
            // "window.$": "jquery",
        }),
        new webpack.optimize.LimitChunkCountPlugin({
            maxChunks: 1,
        }),
    ],
};
