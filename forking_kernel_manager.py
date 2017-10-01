import errno, os, resource, signal, uuid
from multiprocessing import Pipe, Process

from log import kernel_logger

from ipykernel.kernelapp import IPKernelApp
from traitlets.config.loader import Config



class KernelError(Exception):
    """
    An error relating to starting up kernels
    """
    pass

class ForkingKernelManager(object):
    """Manager for multiple kernels and forking on the untrusted side."""
    
    def __init__(self, ip, update_function, tmp_dir):
        self.kernels = {}
        self.ip = ip
        self.update_function = update_function
        self.dir = tmp_dir
        try:
            os.makedirs(tmp_dir)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

    def fork_kernel(self, config, pipe, resource_limits):
        """The target for new processes in ForkingKernelManager.start_kernel.
       
        This method forks and initializes a new kernel, uses the update_function
        to update the kernel's namespace, sets resource limits for the kernel,
        and sends kernel connection information through the Pipe object.

        :arg traitlets.config.loader config: kernel configuration
        :arg multiprocessing.Pipe pipe: a pipe for sending kernel ip, session,
            and port information to the other side
        :arg dict resource_limits: a dictionary with keys resource.RLIMIT_*
            (see config_default documentation for explanation of valid options)
        """
        os.setpgrp()
        logger = kernel_logger.getChild(str(uuid.uuid4())[:4])
        logger.debug("kernel forked; now starting and configuring")
        try:
            ka = IPKernelApp.instance(config=config, ip=config["ip"])
            ka.log.propagate = True
            ka.log_level = logger.level
            from namespace import InstrumentedNamespace
            ka.user_ns = InstrumentedNamespace()
            ka.initialize([])
        except:
            logger.exception("Error initializing IPython kernel")
            # FIXME: What's the point in proceeding after?!
        try:
            if self.update_function is not None:
                self.update_function(ka)
        except:
            logger.exception("Error configuring up kernel")
        logger.debug("finished updating")
        for r, limit in resource_limits.iteritems():
            resource.setrlimit(getattr(resource, r), (limit, limit))
        pipe.send({
            "ip": ka.ip,
            "key": ka.session.key,
            "shell_port": ka.shell_port,
            "stdin_port": ka.stdin_port,
            "hb_port": ka.hb_port,
            "iopub_port": ka.iopub_port})
        pipe.close()
        # The following line will erase JSON connection file with ports and
        # other numbers. Since we do not reuse the kernels, we don't really need
        # these files. And new kernels set atexit hook to delete the file, but
        # it does not get called, perhaps because kernels are stopped by system
        # signals. The result is accumulation of files leading to disk quota
        # issues AND attempts to use stale files to connect to non-existing
        # kernels that eventually crash the server. TODO: figure out a better
        # fix, perhaps kernels have to be stopped in a more gentle fashion?
        ka.cleanup_connection_file()
        # In order to show the correct code line when a (deprecation) warning
        # is triggered, we change the main module name and save user code to
        # a file with the same name.
        import sys
        sys.argv = ['sagemathcell.py']
        old_execute = ka.kernel.do_execute
        import codecs
        
        def new_execute(code, *args, **kwds):
            with codecs.open('sagemathcell.py', 'w', encoding='utf-8') as f:
                f.write(code)
            return old_execute(code, *args, **kwds)
            
        ka.kernel.do_execute = new_execute
        ka.start()

    def start_kernel(self, kernel_id=None, config=None, resource_limits=None):
        """ A function for starting new kernels by forking.

        :arg str kernel_id: the id of the kernel to be started.
            If no id is passed, a uuid will be generated.
        :arg Ipython.config.loader config: kernel configuration.
        :arg dict resource_limits: a dict with keys resource.RLIMIT_*
            (see config_default documentation for explanation of valid options)
            and values of the limit for the given resource to be set in the
            kernel process
        :returns: kernel id and connection information which includes the
            kernel's ip, session key, and shell, heartbeat, stdin, and iopub
            port numbers
        :rtype: dict
        """
        kernel_logger.debug("start_kernel with config %s", config)
        if kernel_id is None:
            kernel_id = str(uuid.uuid4())
        if config is None:
            config = Config({"ip": self.ip})
        if resource_limits is None:
            resource_limits = {}
        config.HistoryManager.enabled = False

        dir = os.path.join(self.dir, kernel_id)
        try:
            os.mkdir(dir)
        except OSError:
            # TODO: take care of race conditions and other problems with us
            # using an 'unclean' directory
            pass
        currdir = os.getcwd()
        os.chdir(dir)

        p, q = Pipe()
        proc = Process(target=self.fork_kernel, args=(config, q, resource_limits))
        proc.start()
        os.chdir(currdir)
        # todo: yield back to the message processing while we wait
        for i in range(5):
            if p.poll(1):
                connection = p.recv()
                p.close()
                self.kernels[kernel_id] = (proc, connection)
                return {"kernel_id": kernel_id, "connection": connection}
            else:
                kernel_logger.info("Kernel %s did not start after %d seconds."
                                   % (kernel_id[:4], i))
        p.close()
        self.kill_process(proc)
        raise KernelError("Kernel start timeout.")

    def kill_process(self, proc):
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            # todo: yield back to message processing loop while we join
            proc.join(30)
        except Exception as e:
            # On Unix, we may get an ESRCH error if the process has already
            # terminated. Ignore it.
            from errno import ESRCH
            if e.errno !=  ESRCH:
                return False
        return True

    def kill_kernel(self, kernel_id):
        """ A function for ending running kernel processes.

        :arg str kernel_id: the id of the kernel to be killed
        :returns: whether or not the kernel process was successfully killed
        :rtype: bool
        """
        if kernel_id in self.kernels:
            proc = self.kernels[kernel_id][0]
            if self.kill_process(proc):
                del self.kernels[kernel_id]
                return True
        return False

    def interrupt_kernel(self, kernel_id):
        """ A function for interrupting running kernel processes.

        :arg str kernel_id: the id of the kernel to be interrupted
        :returns: whether or not the kernel process was successfully interrupted
        :rtype: bool
        """
        success = False

        if kernel_id in self.kernels:
            try:
                os.kill(self.kernels[kernel_id][0].pid, signal.SIGINT)
                success = True
            except:
                pass

        return success

    def restart_kernel(self, kernel_id):
        """ A function for restarting running kernel processes.

        :arg str kernel_id: the id of the kernel to be restarted
        :returns: kernel id and connection information which includes the kernel's ip, session key, and shell, heartbeat, stdin, and iopub port numbers for the restarted kernel
        :rtype: dict
        """
        ports = self.kernels[kernel_id][1]
        self.kill_kernel(kernel_id)
        return self.start_kernel(kernel_id, Config({"IPKernelApp": ports, "ip": self.ip}))

    def purge_kernels(self):
        return [id for id in self.kernels.keys() if not self.kill_kernel(id)]
