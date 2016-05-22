import sys, time

from log import receiver_logger

from ipykernel.jsonutil import json_clean
import zmq

from misc import Timer, sage_json
from untrusted_kernel_manager import UntrustedMultiKernelManager


class Receiver(object):
    
    def __init__(self, ip, tmp_dir):
        self.context = zmq.Context()
        self.dealer = self.context.socket(zmq.DEALER)
        self.port = self.dealer.bind_to_random_port("tcp://%s" % ip)
        print(self.port)
        sys.stdout.flush()
        self.sage_mode = self.setup_sage()
        print(self.sage_mode)
        sys.stdout.flush()
        self.km = UntrustedMultiKernelManager(ip,
                update_function=self.update_dict_with_sage, tmp_dir=tmp_dir)
        self.timer = Timer("", reset=True)

    def start(self):
        self.listen = True
        while self.listen:
            source = self.dealer.recv()
            msg = self.dealer.recv_pyobj()

            msg_type = "invalid_message"
            if msg.get("type") is not None:
                msgtype = msg["type"]
                if hasattr(self, msgtype):
                    msg_type = msgtype

            if msg.get("content") is None:
                msg["content"] = {}

            self.timer()
            logger.debug("Start handler %s" % msg_type)
            handler = getattr(self, msg_type)
            response = handler(msg["content"])
            logger.debug("Finished handler %s: %s"%(msg_type, self.timer))

            self.dealer.send(source, zmq.SNDMORE)
            self.dealer.send_pyobj(response)

    def _form_message(self, content, error=False):
        return {"content": content,
                "type": "error" if error else "success"}

    def setup_sage(self):
        try:
            import sage
            import sage.all

            # override matplotlib and pylab show functions
            # TODO: use something like IPython's inline backend
            from uuid import uuid4
            import os
            def mp_show(savefig):
                filename="%s.png"%uuid4()
                savefig(filename)
                msg={'text/image-filename': filename}
                sys._sage_.sent_files[filename] = os.path.getmtime(filename)
                sys._sage_.display_message(msg)
            from functools import partial
            import pylab
            import matplotlib.pyplot
            pylab.show = partial(mp_show, savefig=pylab.savefig)
            matplotlib.pyplot.show = partial(mp_show, savefig=matplotlib.pyplot.savefig)

            import StringIO
            # The first plot takes about 2 seconds to generate (presumably
            # because lots of things, like matplotlib, are imported).  We plot
            # something here so that worker processes don't have this overhead
            try:
                sage.all.plot(lambda x: x, (0,1)).save(StringIO.StringIO())
            except Exception as e:
                logger.debug('plotting exception: %s'%e)
            self.sage_dict = {'sage': sage}
            return True
        except ImportError as e:
            print(e)
            self.sage_dict = {}
            return False

    def update_dict_with_sage(self, ka):
        import misc
        class TempClass(object):
            pass
        _sage_ = TempClass()
        _sage_.display_message = misc.display_message
        _sage_.stream_message = misc.stream_message
        _sage_.reset_kernel_timeout = misc.reset_kernel_timeout
        _sage_.javascript = misc.javascript
        _sage_.sent_files = {}
        import graphics
        _sage_.threejs = graphics.show_3d_plot_using_threejs
        _sage_.InteractiveGraphics = graphics.InteractiveGraphics
        def new_files(root='./'):
            import os
            import sys
            new_files = []
            for top,dirs,files in os.walk(root):
                for dir in dirs:
                    if dir.endswith(".jmol"):
                        dirs.remove(dir)
                for nm in files:
                    path = os.path.join(top,nm)
                    if path.startswith('./'):
                        path = path[2:]
                    mtime = os.stat(path).st_mtime
                    if path not in sys._sage_.sent_files or sys._sage_.sent_files[path] < mtime:
                        new_files.append(path)
                        sys._sage_.sent_files[path] = mtime
            ip = user_ns['get_ipython']()
            ip.payload_manager.write_payload({"new_files": new_files})
            return ''
        _sage_.new_files = new_files

        def handler_wrapper(key, handler):
            """
            On the one hand, it makes a lot of sense to just call
            run_cell with store_history=False and silent=True.  Then
            the message will be transformed, all of the necessary
            error handling will be put in place, etc.  However, it
            adds quite a bit of overhead, with the pre_run_code bit,
            the user_variables bit, etc.  Also, if the user has handed
            you a function, you actually want to call that function,
            instead of whatever has that name currently (i.e., you
            want to use the actual function and closure, not just
            convert things back to strings again).  Even building up
            an AST right away calls the function name rather than the
            actual function. (what I wouldn't give for Lisp macros
            right now! :).

            On the other hand, if we just literally store the function
            and call the function, then it's hard to run in the user
            namespace.  How do you exec in a namespace, but use an
            actual function object rather than trying to find the
            string.  Oh, I guess you can just assign the function to
            some storage dictionary and use *that* string, and hope
            the user doesn't change that dictionary.  In a sense,
            that's doing a gensym.

            The last is probably the best approach.  Use that and
            run_code, though we should time things to see how much
            overhead is introduced, or at least provide an option for
            running a minimal version of the code.

            Pursuant to this, we should probably remove the ident and
            stream options, and just provide the actual message to the
            handler.  The handler can return a content and metadata
            dictionary that will automatically be sent in a
            key+'_reply' message, or raise an error that will be sent
            in that status message.

            So, still to do: either make the execute_request handler a
            subcase of this, or abstract out some of the things done
            in the handler into maybe a context manager so that the
            things like sending a kernel busy message are shared.

            Discuss namespaces and things for message ids.  I think
            it's fine to request that a module that is adding handler
            functions use a message type that reflects the module
            name, or in some way reflects the project (e.g.,
            'sagenb.interact.update')

            Also, should these requests be broadcast out to other
            clients?  I think not, but double-check this.

            Provide an option to just run the code with minimal
            changes (i.e., no input splitting).  This provides fast
            execution.
            """
            kernel = ka.kernel
            from functools import wraps
            @wraps(handler)
            def f(stream, ident, parent, *args, **kwargs):
                kernel._publish_status(u'busy', parent)
                md = kernel.init_metadata(parent)
                content = parent['content']
                # Set the parent message of the display hook and out streams.
                kernel.shell.set_parent(parent)
                reply_content = {}
                try:
                    reply_content[u'result'] = handler(stream, ident, parent, *args, **kwargs)
                except:
                    status = u'error'
                    etype, evalue, tb = sys.exc_info()
                    import traceback
                    tb_list = traceback.format_exception(etype, evalue, tb)
                    reply_content.update(kernel.shell._showtraceback(etype, evalue, tb_list))
                else:
                    status = u'ok'
                reply_content[u'status'] = status
                sys.stdout.flush()
                sys.stderr.flush()

                # this should be refactored probably to use existing IPython code
                if reply_content['status'] == 'ok':
                    reply_content[u'user_expressions'] = \
                                 kernel.shell.user_expressions(content.get(u'user_expressions', {}))
                else:
                    # If there was an error, don't even try to compute
                    # expressions
                    reply_content[u'user_expressions'] = {}

                # Payloads should be retrieved regardless of outcome, so we can both
                # recover partial output (that could have been generated early in a
                # block, before an error) and clear the payload system always.
                reply_content[u'payload'] = kernel.shell.payload_manager.read_payload()
                # Be agressive about clearing the payload because we don't want
                # it to sit in memory until the next execute_request comes in.
                kernel.shell.payload_manager.clear_payload()

                # Flush output before sending the reply.
                sys.stdout.flush()
                sys.stderr.flush()
                # FIXME: on rare occasions, the flush doesn't seem to make it to the
                # clients... This seems to mitigate the problem, but we definitely need
                # to better understand what's going on.
                if kernel._execute_sleep:
                    time.sleep(kernel._execute_sleep)

                reply_content = json_clean(reply_content)
                md['status'] = reply_content['status']
                if (reply_content['status'] == 'error' and
                    reply_content['ename'] == 'UnmetDependency'):
                        md['dependencies_met'] = False
                md = kernel.finish_metadata(parent, md, reply_content)
                reply_msg = kernel.session.send(stream, key + u'_reply',
                    reply_content, parent, metadata=md, ident=ident)
                kernel.log.debug("%s", reply_msg)
                kernel._publish_status(u'idle', parent)
            return f
            
        def register_handler(key, handler):
            msg_types = set([ 'execute_request', 'complete_request',
                          'object_info_request', 'history_request',
                          'connect_request', 'shutdown_request',
                          'apply_request',
                          ])

            if key not in msg_types:
                ka.kernel.shell_handlers[key] = handler_wrapper(key, handler)
                
        _sage_.register_handler = register_handler
        
        def send_message(stream, msg_type, content, parent, **kwargs):
            ka.kernel.session.send(stream, msg_type, content=content, parent=parent, **kwargs)
        _sage_.send_message = send_message

        # Enable Sage types to be sent via session messages
        from zmq.utils import jsonapi
        ka.kernel.session.pack = lambda x: jsonapi.dumps(x, default=sage_json)

        sys._sage_ = _sage_
        user_ns = ka.kernel.shell.user_module.__dict__
        #ka.kernel.shell.user_ns = ka.kernel.shell.Completer.namespace = user_ns
        sys._sage_.namespace = user_ns
        # TODO: maybe we don't want to cut down the flush interval?
        sys.stdout.flush_interval = sys.stderr.flush_interval = 0.0
        def clear(changed=None):
            sys._sage_.display_message({
                "application/sage-clear": {"changed": changed},
                "text/plain": "Clear display"
            })
        sys._sage_.clear = clear
        if self.sage_mode:
            ka.kernel.shell.extension_manager.load_extension('sage.repl.ipython_extension')
            user_ns.update(self.sage_dict)
            sage_code = """
# Ensure unique random state after forking
set_random_seed()
from sage.repl.rich_output import get_display_manager
from backend_cell import BackendCell
get_display_manager().switch_backend(BackendCell(), shell=get_ipython())
# Make R interface pickup the new working directory
r = R()
"""
            exec(sage_code, user_ns)
            
        from IPython.core import oinspect
        from sage.misc.sagedoc import my_getsource
        oinspect.getsource = my_getsource
        
        import interact_sagecell
        import interact_compatibility
        import dynamic
        import exercise
        # overwrite Sage's interact command with our own
        user_ns.update(interact_sagecell.imports)
        user_ns.update(interact_compatibility.imports)
        user_ns.update(dynamic.imports)
        user_ns.update(exercise.imports)
        user_ns['threejs'] = sys._sage_.threejs
        sys._sage_.update_interact = interact_sagecell.update_interact

    # Message Handlers
    
    def invalid_message(self, msg_content):
        """Handler for unsupported messages."""
        return self._form_message({"status": "Invalid message!"}, error = True)

    def start_kernel(self, msg_content):
        """Handler for start_kernel messages."""
        resource_limits = msg_content.get("resource_limits")
        try:
            reply_content = self.km.start_kernel(resource_limits=resource_limits)
            return self._form_message(reply_content)
        except Exception as e:
            logger.exception("Error starting kernel")
            return self._form_message(str(e), error=True)

    def kill_kernel(self, msg_content):
        """Handler for kill_kernel messages."""
        kernel_id = msg_content["kernel_id"]
        success = self.km.kill_kernel(kernel_id)

        reply_content = {"status": "Kernel %s killed!"%(kernel_id)}
        if not success:
            reply_content["status"] = "Could not kill kernel %s!"%(kernel_id)

        return self._form_message(reply_content, error=(not success))
    
    def purge_kernels(self, msg_content):
        """Handler for purge_kernels messages."""
        failures = self.km.purge_kernels()
        reply_content = {"status": "All kernels killed!"}
        success = (len(failures) == 0)
        if not success:
            reply_content["status"] = "Could not kill kernels %s!"%(failures)
        return self._form_message(reply_content, error=(not success))

    def restart_kernel(self, content):
        """Handler for restart_kernel messages."""
        kernel_id = content["kernel_id"]
        return self._form_message(self.km.restart_kernel(kernel_id))

    def interrupt_kernel(self, msg_content):
        """Handler for interrupt_kernel messages."""
        kernel_id = msg_content["kernel_id"]

        reply_content = {"status": "Kernel %s interrupted!"%(kernel_id)}
        success = self.km.interrupt_kernel(kernel_id)
        if not success:
            reply_content["status"] = "Could not interrupt kernel %s!"%(kernel_id)
        return self._form_message(reply_content, error=(not success))

    def remove_computer(self, msg_content):
        """Handler for remove_computer messages."""
        self.listen = False
        return self.purge_kernels(msg_content)


if __name__ == '__main__':
    ip = sys.argv[1]
    comp_id = sys.argv[2]
    tmp_dir = sys.argv[3]
    logger = receiver_logger.getChild(comp_id[:4])
    logger.debug('started')
    receiver = Receiver(ip, tmp_dir)
    receiver.start()
    logger.debug('ended')
