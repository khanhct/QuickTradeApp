"""Background worker for API calls — keeps UI responsive."""
import queue
import threading
import logging
from concurrent.futures import Future

logger = logging.getLogger(__name__)


class ApiWorker:
    """Single-threaded worker that serializes API calls in background."""

    def __init__(self):
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True, name="ApiWorker")
        self._running = False

    def start(self):
        self._running = True
        self._thread.start()

    def stop(self):
        self._running = False
        self._queue.put(None)
        self._thread.join(timeout=5)

    def submit(self, fn, *args, **kwargs) -> Future:
        future = Future()
        self._queue.put((fn, args, kwargs, future))
        return future

    def fire_and_forget(self, fn, *args, **kwargs):
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
                logger.exception(f"ApiWorker error in {fn.__name__}: {e}")
                if future is not None:
                    future.set_exception(e)
