/**
 * Script to download all required vendor javascript files.
 */

import fs from "fs";
import path from "path";
import fetch from "node-fetch";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const TARGET_DIR = path.resolve(__dirname, "build/vendor");

const URLS = {
    "base/js/utils.js":
        "https://raw.githubusercontent.com/jupyter/notebook/master/notebook/static/base/js/utils.js",
    "base/js/namespace.js":
        "https://raw.githubusercontent.com/jupyter/notebook/master/notebook/static/base/js/namespace.js",
    "base/js/events.js":
        "https://raw.githubusercontent.com/jupyter/notebook/master/notebook/static/base/js/events.js",
    "services/kernels/kernel.js":
        "https://raw.githubusercontent.com/jupyter/notebook/master/notebook/static/services/kernels/kernel.js",
    "services/kernels/comm.js":
        "https://raw.githubusercontent.com/jupyter/notebook/master/notebook/static/services/kernels/comm.js",
    "services/kernels/serialize.js":
        "https://raw.githubusercontent.com/jupyter/notebook/master/notebook/static/services/kernels/serialize.js",
    "mpl.js":
        "https://raw.githubusercontent.com/matplotlib/matplotlib/main/lib/matplotlib/backends/web_backend/js/mpl.js",
    "colorpicker.js":
        "https://raw.githubusercontent.com/thorst/jQuery-ColorPicker/master/colorpicker.js",
    "colorpicker.css":
        "https://raw.githubusercontent.com/thorst/jQuery-ColorPicker/master/colorpicker.css",
};

async function fetchFile(fileName, url) {
    const resp = await fetch(url);
    const body = await resp.text();

    const fullPath = `${TARGET_DIR}/${fileName}`;
    const base = path.dirname(fullPath);
    fs.mkdirSync(base, { recursive: true });

    const stream = fs.createWriteStream(fullPath);
    stream.once("open", function (fd) {
        stream.write(body);
        stream.end();
        console.log(`Downloaded ${fileName}`);
    });
}

// Ensure the target directory has been created
fs.mkdirSync(TARGET_DIR, { recursive: true });

for (const [fileName, url] of Object.entries(URLS)) {
    fetchFile(fileName, url);
}
