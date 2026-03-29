import logging
from concurrent.futures import Future
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from app.mt5.worker import MT5Worker
from app.mt5 import positions as positions_mod
from app.config import config

logger = logging.getLogger(__name__)

_POLL_INTERVAL_MS = 100  # check future every 100ms


def _fetch_all():
    """Fetch both open positions and pending orders from MT5."""
    positions = positions_mod.get_positions()
    orders = positions_mod.get_orders()
    return positions, orders


class SyncManager(QObject):
    """Manages periodic sync of positions and pending orders from MT5."""

    positions_updated = pyqtSignal(list)  # list[Position]
    orders_updated = pyqtSignal(list)     # list[PendingOrder]
    sync_error = pyqtSignal(str)

    def __init__(self, worker: MT5Worker, parent=None):
        super().__init__(parent)
        self._worker = worker
        self._pending_future: Future | None = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.sync_now)
        self._timer.setInterval(config.sync_interval_ms)

        # Poll timer to check future result on main thread
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._check_result)
        self._poll_timer.setInterval(_POLL_INTERVAL_MS)

    def start(self):
        """Start periodic sync."""
        self.sync_now()
        self._timer.start()
        logger.info(f"Sync started, interval={config.sync_interval_ms}ms")

    def stop(self):
        self._timer.stop()
        self._poll_timer.stop()

    def sync_now(self):
        """Trigger an immediate sync."""
        if self._pending_future is not None and not self._pending_future.done():
            logger.debug("Sync skipped — previous sync still pending")
            return
        logger.info("Sync: submitting fetch_all to worker...")
        self._pending_future = self._worker.submit(_fetch_all)
        self._poll_timer.start()

    def _check_result(self):
        """Poll future on main thread — avoids cross-thread signal issues."""
        if self._pending_future is None or not self._pending_future.done():
            return

        self._poll_timer.stop()
        future = self._pending_future
        self._pending_future = None

        try:
            positions, orders = future.result()
            logger.info(f"Sync complete: {len(positions)} positions, {len(orders)} pending orders")
            self.positions_updated.emit(positions)
            self.orders_updated.emit(orders)
        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            self.sync_error.emit(str(e))
