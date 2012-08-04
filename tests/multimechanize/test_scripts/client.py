import urllib2
import websocket
import json
import uuid

root = "http://localhost:8888"

class SageCellSession(object):
    def __init__(self):
        f = urllib2.urlopen("%s/kernel" % (root,), "")
        data = json.loads(f.read())
        f.close()
        self.kernel_id = data["kernel_id"]
        self.ws_url = data["ws_url"]
        self.iopub = websocket.create_connection("%skernel/%s/iopub" % (self.ws_url, self.kernel_id))
        self.shell = websocket.create_connection("%skernel/%s/shell" % (self.ws_url, self.kernel_id))
        self.session_id = str(uuid.uuid4())

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, etype, value, traceback):
        self.close()

    def execute(self, code):
        content = {"code": code,
                   "silent": False,
                   "user_variables": [],
                   "user_expressions": {"_sagecell_files": "sys._sage_.new_files()"},
                   "allow_stdin": False}
        self.send_msg("execute_request", content)

    def update_interact(self, interact_id, values):
        self.execute("sys._sage_.update_interact(%r, %r)" % (interact_id, values))

    def send_msg(self, msg_type, content):
        msg = {"header": {"msg_id": str(uuid.uuid4()),
                          "username": "username",
                          "session": self.session_id,
                          "msg_type": msg_type
                         },
               "metadata": {},
               "content": content,
               "parent_header":{}
              }
        self.shell.send(json.dumps(msg))

    def close(self):
        self.iopub.close()
        self.shell.close()

    def iopub_recv(self):
        return json.loads(self.iopub.recv())

    def shell_recv(self):
        return json.loads(self.shell.recv())

def load_root():
    resources = ["/", "/static/root.css", "/static/jquery.min.js",
                 "/static/embedded_sagecell.js",
                 "/static/jquery-ui/css/sagecell/jquery-ui-1.8.21.custom.css",
                 "/static/colorpicker/css/colorpicker.css",
                 "/static/all.min.css", "/static/mathjax/MathJax.js",
                 "/static/sagelogo.png", "/static/spinner.gif",
                 "/sagecell.html", "/static/all.min.js",
                 "/static/mathjax/config/TeX-AMS-MML_HTMLorMML.js",
                 "/static/mathjax/images/MenuArrow-15.png",
                 "/static/jquery-ui/css/sagecell/images/ui-bg_highlight-hard_60_99bbff_1x100.png",
                 "/static/mathjax/extensions/jsMath2jax.js",
                 "/static/jquery-ui/css/sagecell/images/ui-bg_highlight-hard_90_99bbff_1x100.png"]
    for r in resources:
        f = urllib2.urlopen(root + r)
        assert f.code == 200, "Bad response: HTTP %d" % (f.code,)
