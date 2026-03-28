import queue
import threading
import logging
from concurrent.futures import Future
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class MT5Worker(QObject):
    """Single-threaded worker that serializes all MT5 API calls.
    MT5 requires all calls to happen on the same thread that called initialize().
    """

    result_ready = pyqtSignal(str, object)  # (task_name, result)
    error_occurred = pyqtSignal(str, str)  # (task_name, error_message)

    def __init__(self):
        super().__init__()
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True, name="MT5Worker")
        self._running = False

    def start(self):
        self._running = True
        self._thread.start()

    def stop(self):
        self._running = False
        self._queue.put(None)
        self._thread.join(timeout=5)

    def submit(self, fn, *args, **kwargs) -> Future:
        """Submit a task and get a Future back."""
        future = Future()
        self._queue.put((fn, args, kwargs, future))
        return future

    def fire_and_forget(self, fn, *args, **kwargs):
        """Submit a task without waiting for result."""
        self._queue.put((fn, args, kwargs, None))

    def _run(self):
        while self._running:
            try:
                item = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if item is None:
                break

            fn, args, kwargs, future = item
            try:
                result = fn(*args, **kwargs)
                if future is not None:
                    future.set_result(result)
            except Exception as e:
                logger.exception(f"MT5 worker error in {fn.__name__}: {e}")
                if future is not None:
                    future.set_exception(e)
                self.error_occurred.emit(
                    getattr(fn, "__name__", str(fn)), str(e)
                )
