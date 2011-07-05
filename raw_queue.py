"""
Subclasses the multiprocessing queue to provide "safe" get and put methods that operate on bytes, rather than pickling objects
"""
from multiprocessing.queues import _multiprocessing, Queue, Pipe, Lock, os, sys, BoundedSemaphore, register_after_fork, threading, collections

__all__ = ['RawQueue']


class _RawQueue(Queue):
    """
    RawQueue makes a single change to Queue: instead of using the underlying ``send`` and ``recv`` functions of the pipe, it uses ``send_bytes`` and ``recv_bytes`` to provide a "safe" transport mechanism
    """
    def __init__(self, maxsize=0):
        """
        Override the __init__ function so that *our* _after_fork function gets registered, rather than Queue's.
        """
        if maxsize <= 0:
            maxsize = _multiprocessing.SemLock.SEM_VALUE_MAX
        self._maxsize = maxsize
        self._reader, self._writer = Pipe(duplex=False)
        self._rlock = Lock()
        self._opid = os.getpid()
        if sys.platform == 'win32':
            self._wlock = None
        else:
            self._wlock = Lock()
        self._sem = BoundedSemaphore(maxsize)

        self._after_fork()

        if sys.platform != 'win32':
            # this is the only line that is changed from Queue, to
            # call *our* _after_fork
            register_after_fork(self, _RawQueue._after_fork)


    def _after_fork(self):
        """
        Override the default :meth:`multiprocessing.Queue._after_fork` method
        to use the ``send_bytes`` and ``recv_bytes`` methods.
        """
        self._notempty = threading.Condition(threading.Lock())
        self._buffer = collections.deque()
        self._thread = None
        self._jointhread = None
        self._joincancelled = False
        self._closed = False
        self._close = None
        # the following two lines are the only changes from Queue, 
        # make the functions the *_bytes ones
        self._send = self._writer.send_bytes
        self._recv = self._reader.recv_bytes
        self._poll = self._reader.poll

def RawQueue(maxsize=0):
    '''
    Returns a queue object
    '''
    return _RawQueue(maxsize)

