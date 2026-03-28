import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from app.mt5.worker import MT5Worker
from app.mt5 import connection
from app.core.sync import SyncManager
from app.ui.order_panel import OrderPanel
from app.ui.positions_panel import PositionsPanel
from app.ui.status_bar import StatusBar

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MT5 Quick Trading")
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)

        # Create MT5 worker
        self._worker = MT5Worker()

        # Create sync manager
        self._sync_manager = SyncManager(self._worker, self)

        # Setup UI
        self._setup_ui()
        self._connect_signals()

        # Start worker and initialize MT5
        self._worker.start()
        self._init_mt5()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Splitter for order panel (top) and positions (bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)

        self._order_panel = OrderPanel(self._worker)
        self._positions_panel = PositionsPanel(self._worker)

        splitter.addWidget(self._order_panel)
        splitter.addWidget(self._positions_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

        # Status bar
        self._status_bar = StatusBar()
        layout.addWidget(self._status_bar)

    def _connect_signals(self):
        # Sync updates
        self._sync_manager.positions_updated.connect(self._on_positions_updated)
        self._sync_manager.sync_error.connect(self._on_sync_error)

        # Position panel requests sync after bulk actions
        self._positions_panel.request_sync.connect(self._sync_manager.sync_now)

        # Order placed feedback
        self._order_panel.order_placed.connect(self._on_order_placed)

        # Symbol from OrderPanel drives PositionsPanel filter
        self._order_panel._symbol_combo.currentTextChanged.connect(
            self._positions_panel.set_symbol
        )
        # Set initial symbol
        self._positions_panel.set_symbol(self._order_panel._symbol_combo.currentText())

        # PositionsPanel reads SL/TP values from OrderPanel
        self._positions_panel._get_sl_value = self._order_panel.get_sl_value
        self._positions_panel._get_tp_value = self._order_panel.get_tp_value

        # Worker errors
        self._worker.error_occurred.connect(self._on_worker_error)

    def _init_mt5(self):
        """Initialize MT5 connection on the worker thread."""
        future = self._worker.submit(connection.initialize)
        future.add_done_callback(self._on_mt5_init_complete)

    def _on_mt5_init_complete(self, future):
        """Callback from worker thread — schedule UI work on main thread."""
        try:
            success = future.result()
        except Exception as e:
            logger.error(f"MT5 init error: {e}")
            success = False
        # QTimer.singleShot with 0ms runs on the main event loop thread
        QTimer.singleShot(0, lambda: self._handle_mt5_init(success))

    def _handle_mt5_init(self, success: bool):
        self._status_bar.set_connected(success)
        if success:
            logger.info("MT5 initialized, starting sync")
            self._sync_manager.start()
        else:
            logger.error("MT5 initialization failed")

    def _on_positions_updated(self, positions):
        self._positions_panel.update_positions(positions)
        self._status_bar.set_position_count(len(positions))
        self._status_bar.set_sync_time()
        self._status_bar.set_connected(True)

    def _on_sync_error(self, error_msg):
        logger.error(f"Sync error: {error_msg}")
        self._status_bar.set_connected(False)

    def _on_order_placed(self, msg):
        logger.info(msg)
        # Trigger sync to refresh positions after order
        self._sync_manager.sync_now()

    def _on_worker_error(self, task_name, error_msg):
        logger.error(f"Worker error in {task_name}: {error_msg}")

    def closeEvent(self, event):
        """Clean shutdown."""
        self._sync_manager.stop()
        self._worker.submit(connection.shutdown)
        self._worker.stop()
        super().closeEvent(event)
