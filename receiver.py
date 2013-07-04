from untrusted_kernel_manager import UntrustedMultiKernelManager
import zmq
from zmq import ssh
import sys
from misc import Timer

class Receiver(object):
    def __init__(self, filename, ip):
        self.context = zmq.Context()
        self.dealer = self.context.socket(zmq.DEALER)
        self.port = self.dealer.bind_to_random_port("tcp://%s" % ip)
        print self.port
        sys.stdout.flush()
        self.sage_mode = self.setup_sage()
        print self.sage_mode
        sys.stdout.flush()
        self.km = UntrustedMultiKernelManager(filename, ip,
                update_function=self.update_dict_with_sage)
        self.filename = filename
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
            logging.debug("Start %s"%(msg_type,))
            handler = getattr(self, msg_type)
            response = handler(msg["content"])
            logging.debug("Finished handler %s: %s"%(msg_type, self.timer))

            self.dealer.send(source, zmq.SNDMORE)
            self.dealer.send_pyobj(response)

    def _form_message(self, content, error=False):
        return {"content": content,
                "type": "error" if error else "success"}

    def setup_sage(self):
        try:
            import sage
            import sage.all
            sage.misc.misc.EMBEDDED_MODE = {'frontend': 'sagecell'}
            import StringIO
            # The first plot takes about 2 seconds to generate (presumably
            # because lots of things, like matplotlib, are imported).  We plot
            # something here so that worker processes don't have this overhead
            try:
                sage.all.plot(lambda x: x, (0,1)).save(StringIO.StringIO())
            except Exception as e:
                logging.debug('plotting exception: %s'%e)
            self.sage_dict = {'sage': sage}
            sage_code = """
from sage.all import *
from sage.calculus.predefined import x
from sage.misc.html import html
from sage.server.support import help
from sagenb.misc.support import automatic_names
"""
            exec sage_code in self.sage_dict
            return True
        except ImportError as e:
            self.sage_dict = {}
            return False

    def update_dict_with_sage(self, ka):
        import misc
        class TempClass(object):
            pass
        _sage_ = TempClass()
        _sage_.display_message = misc.display_message
        _sage_.kernel_timeout = 0.0
        _sage_.sent_files = {}
        def new_files(root='./'):
            import os
            import sys
            new_files = []
            for top,dirs,files in os.walk(root):
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
                md = kernel._make_metadata(parent['metadata'])
                content = parent['content']
                # Set the parent message of the display hook and out streams.
                kernel.shell.displayhook.set_parent(parent)
                kernel.shell.display_pub.set_parent(parent)
                kernel.shell.data_pub.set_parent(parent)
                sys.stdout.set_parent(parent)
                sys.stderr.set_parent(parent)
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
                    reply_content[u'user_variables'] = \
                                 kernel.shell.user_variables(content.get(u'user_variables', []))
                    reply_content[u'user_expressions'] = \
                                 kernel.shell.user_expressions(content.get(u'user_expressions', {}))
                else:
                    # If there was an error, don't even try to compute variables or
                    # expressions
                    reply_content[u'user_variables'] = {}
                    reply_content[u'user_expressions'] = {}

                if kernel._execute_sleep:
                    import time
                    time.sleep(kernel._execute_sleep)

                from IPython.utils.jsonutil import json_clean
                reply_content = json_clean(reply_content)

                md['status'] = reply_content['status']
                if reply_content['status'] == 'error' and \
                                reply_content['ename'] == 'UnmetDependency':
                        md['dependencies_met'] = False
                reply_msg = kernel.session.send(stream, key+u'_reply',
                                              reply_content, parent, metadata=md,
                                              ident=ident)
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

        sys._sage_ = _sage_
        # maybe should use prepare_user_module from IPython's interactive shell
        from namespace import InstrumentedNamespace
        logging.debug('namespace check:')
        logging.debug(ka.kernel.shell.user_global_ns is ka.kernel.shell.user_ns)
        user_ns = InstrumentedNamespace(ka.kernel.shell.user_module.__dict__)
        ka.kernel.shell.user_module.__dict__ = user_ns
        ka.kernel.shell.user_ns = ka.kernel.shell.Completer.namespace = user_ns
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
            ka.kernel.shell.extension_manager.load_extension('sage.misc.sage_extension')
            ka.kernel.shell.extension_manager.load_extension('stringdecorators')
            user_ns.update(self.sage_dict)
            sage_code = """
# Ensure unique random state after forking
set_random_seed()
"""
            exec sage_code in user_ns
        def getsource(obj, is_binary):
            # modified from sage.misc.sagedoc.my_getsource
            from sage.misc.sagedoc import sageinspect, format_src
            try:
                s = sageinspect.sage_getsource(obj, is_binary)
                return format_src(str(s))
            except Exception, msg:
                print 'Error getting source:', msg
                return None
        from IPython.core import oinspect
        oinspect.getsource = getsource
        import interact_sagecell
        import interact_compatibility
        # overwrite Sage's interact command with our own
        user_ns["interact"] = interact_sagecell.interact_func(ka.session, ka.iopub_socket)
        user_ns.update(interact_sagecell.imports)
        user_ns.update(interact_compatibility.imports)
        sys._sage_.update_interact = interact_sagecell.update_interact

    """
    Message Handlers
    """
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
            return self._form_message({}, error=True)

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
    filename = sys.argv[2]
    comp_id = sys.argv[3]
    import logging
    import uuid
    logging.basicConfig(filename=filename,format=comp_id[:4]+': %(asctime)s %(message)s',level=logging.DEBUG)
    logging.debug('started')
    ip = sys.argv[1]
    receiver = Receiver(filename, ip)
    receiver.start()
    logging.debug('ended')
