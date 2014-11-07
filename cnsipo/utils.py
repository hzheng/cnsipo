# -*- coding: utf-8 -*-

"""
Universal utitlities
"""

__author__ = "Hui Zheng"
__copyright__ = "Copyright 2014 Hui Zheng"
__credits__ = ["Hui Zheng"]
__license__ = "MIT <http://www.opensource.org/licenses/mit-license.php>"
__version__ = "0.1"
__email__ = "xyzdll[AT]gmail[DOT]com"

import time
from functools import wraps
from contextlib import contextmanager
from Queue import Queue
from threading import Thread


def apply_function(f, *args, **kwargs):
    """ Apply a function or staticmethod/classmethod to the given arguments.
    """
    if callable(f):
        return f(*args, **kwargs)
    elif len(args) and hasattr(f, '__get__'):
        # support staticmethod/classmethod
        return f.__get__(None, args[0])(*args, **kwargs)
    else:
        assert False, "expected a function or staticmethod/classmethod"


def retry(forgivable_exceptions, forgive=lambda x: True,
          tries=5, delay=5, backoff=2, logger=None):
    """Retry decorator with exponential backoff.

    `forgivable_exceptions` is a type of Exception(or Exception tuple)
    `forgive` is a function which takes the caught exception as its argument,
    the meaning of its return value is as follows:
    a negative object(e.g. `False`, `None`) means the old exception will be
    rethrown, an `Exception` object means it will be thrown,
    otherwise the failed call is forgiven and will be retried.
    Furthermore, if the return value is a function, it will be invoked
    before the next try. This function takes the retried call's first
    argument(if any) as its argument(which is typically the calling object).

    Inspired by:
    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    """

    def decorator(f):

        if tries < 1:
            raise ValueError("tries must be at least 1")

        @wraps(f)
        def wrapper(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except forgivable_exceptions as e:
                    forgiven = apply_function(forgive, e) or e
                    if isinstance(forgiven, BaseException):
                        if logger:
                            logger.debug("just give up: {}".format(e))
                        raise forgiven

                    msg = "Error: {}. Retry in {} seconds...".format(
                        str(e), mdelay)
                    if logger:
                        logger.debug(msg)
                    else:
                        print msg
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
                    if callable(forgiven):
                        forgiven(args[0] if len(args) else None)
            return f(*args, **kwargs)  # last chance

        return wrapper

    return decorator


class JobQueue(object):
    """A threaded job queue
    """

    def __init__(self, threads):
        self._threads = threads
        self._thread_enabled = threads > 1
        self._queue = None

    def disable_thread(self):
        self._thread_enabled = False

    def start(self):
        if self._threads <= 1:
            return

        # calling start will automatically enable thread
        self._thread_enabled = True
        if self._queue:  # threads already created
            return

        queue = self._queue = Queue()

        def work():
            while True:
                func, args, kwargs = queue.get()
                try:
                    func(*args, **kwargs)
                finally:
                    queue.task_done()

        for _ in range(self._threads):
            t = Thread(target=work)
            t.daemon = True
            t.start()

    def finish(self):
        if self._queue:
            self._queue.join()

    def add_task(self, func, *args, **kwargs):
        if self._thread_enabled and self._queue:
            self._queue.put((func, args, kwargs))
        else:
            func(*args, **kwargs)


@contextmanager
def threaded(queue):
    """Wrap the block with the threaded queue
    """
    queue.start()
    try:
        yield
    finally:
        queue.finish()
