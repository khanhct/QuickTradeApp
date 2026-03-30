import logging
from concurrent.futures import Future
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSplitter
from PyQt6.QtCore import Qt, QTimer

from client_app.api_client import ApiClient
from client_app.worker import ApiWorker
from client_app.config import client_config
from client_app.ui.order_panel import OrderPanel
from client_app.ui.positions_panel import PositionsPanel
from client_app.ui.status_bar import StatusBar

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.setWindowTitle("MT5 Quick Trading (Remote)")
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)

        self._api = api
        self._worker = ApiWorker()
        self._worker.start()

        self._sync_future: Future | None = None

        self._setup_ui()
        self._start_sync()
        self._connect_signals()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self._order_panel = OrderPanel(self._api, self._worker)
        self._positions_panel = PositionsPanel(self._api, self._worker)

        splitter.addWidget(self._order_panel)
        splitter.addWidget(self._positions_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

        self._status_bar = StatusBar()
        layout.addWidget(self._status_bar)

    def _connect_signals(self):
        self._positions_panel.request_sync.connect(self._sync_now)
        self._order_panel.order_placed.connect(self._on_order_placed)
        self._order_panel._symbol_combo.currentTextChanged.connect(
            self._positions_panel.set_symbol
        )
        self._positions_panel.set_symbol(self._order_panel._symbol_combo.currentText())
        self._positions_panel._get_sl_value = self._order_panel.get_sl_value
        self._positions_panel._get_tp_value = self._order_panel.get_tp_value

    def _start_sync(self):
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._check_sync_result)
        self._poll_timer.setInterval(100)

    def _sync_now(self):
        if self._sync_future is not None and not self._sync_future.done():
            return

        def _fetch():
            positions = self._api.get_positions()
            orders = self._api.get_orders()
            return positions, orders

        self._sync_future = self._worker.submit(_fetch)
        self._poll_timer.start()

    def _check_sync_result(self):
        if self._sync_future is None or not self._sync_future.done():
            return
        self._poll_timer.stop()
        future = self._sync_future
        self._sync_future = None

        try:
            positions, orders = future.result()
            self._positions_panel.update_positions(positions)
            self._positions_panel.update_orders(orders)
            self._status_bar.set_sync_time()
            self._status_bar.set_connected(True)
            self._status_bar.set_position_count(len(positions) + len(orders))
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self._status_bar.set_connected(False)

    def _on_order_placed(self, msg):
        logger.info(msg)
        self._sync_now()

    def closeEvent(self, event):
        self._poll_timer.stop()
        self._worker.stop()
        super().closeEvent(event)
