import queue
import logging
import threading

from concurrent.futures import ThreadPoolExecutor

DEFAULT_MAX_WORKER = 30
DEFAULT_THREAD_PREFIX = 'ThreadManager'
QUEUE_EXIT_SIGNAL = object()


class ThreadManager:
    """
    ThreadManager control thread safe exit and max thread number
    """
    def __init__(self, _queue: queue.Queue = None, max_workers=DEFAULT_MAX_WORKER,
                 thread_name_prefix=DEFAULT_THREAD_PREFIX):
        self._pool = ThreadPoolExecutor(max_workers, thread_name_prefix=thread_name_prefix)
        self._shutdown = False
        self._queue = _queue

    def submit(self, func, *args, **kwargs):
        """
        create a new thread to run `func`
        :param func:
        :param args:
        :param kwargs:
        :return:
        """
        curr_thread = threading.enumerate()
        logging.info('ThreadManager current thread: {} {}'.format(len(curr_thread), curr_thread))
        try:
            self._pool.submit(func, *args, **kwargs)
        except Exception as e:
            raise e

    def shutdown(self, wait=False):
        """
        shutdown notify thread quit
        :param wait: Whether to wait to release all resources
        :return:
        """
        if self._queue is not None:
            self._queue.put(QUEUE_EXIT_SIGNAL)
        self._shutdown = True
        self._pool.shutdown(wait)

    def has_shutdown(self):
        """
        this is a judge condition for `while not` instead of `while True`
        ensure thread could exit when has_shutdown() is True
        :return:
        """
        return self._shutdown
