import logging
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from app.mt5.worker import MT5Worker
from app.mt5 import positions as positions_mod
from app.models.trade import Position
from app.config import config

logger = logging.getLogger(__name__)


class SyncManager(QObject):
    """Manages periodic position sync from MT5."""

    positions_updated = pyqtSignal(list)  # list[Position]
    sync_error = pyqtSignal(str)

    def __init__(self, worker: MT5Worker, parent=None):
        super().__init__(parent)
        self._worker = worker
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.sync_now)
        self._timer.setInterval(config.sync_interval_ms)

    def start(self):
        """Start periodic sync."""
        self.sync_now()
        self._timer.start()
        logger.info(f"Sync started, interval={config.sync_interval_ms}ms")

    def stop(self):
        self._timer.stop()

    def sync_now(self):
        """Trigger an immediate sync."""
        future = self._worker.submit(positions_mod.get_positions)
        future.add_done_callback(self._on_sync_complete)

    def _on_sync_complete(self, future):
        try:
            positions = future.result()
            self.positions_updated.emit(positions)
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self.sync_error.emit(str(e))
