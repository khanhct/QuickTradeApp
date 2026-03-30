import logging
from concurrent.futures import Future
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QGroupBox, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, QTimer

from client_app.config import client_config
from client_app.api_client import ApiClient
from client_app.worker import ApiWorker
from app.core.sl_calculator import calculate_sl

logger = logging.getLogger(__name__)

_BTN_STYLE = (
    "QPushButton {{ background-color: {bg}; color: white; font-weight: bold; "
    "font-size: {fs}px; border-radius: 4px; }}"
    "QPushButton:hover {{ background-color: {hover}; }}"
    "QPushButton:pressed {{ background-color: {pressed}; }}"
)

SELL_MARKET_STYLE = _BTN_STYLE.format(bg="#f44336", hover="#d32f2f", pressed="#b71c1c", fs=14)
SELL_LIMIT_STYLE = _BTN_STYLE.format(bg="#f44336", hover="#d32f2f", pressed="#b71c1c", fs=12)
BUY_MARKET_STYLE = _BTN_STYLE.format(bg="#2196F3", hover="#1976D2", pressed="#0D47A1", fs=14)
BUY_LIMIT_STYLE = _BTN_STYLE.format(bg="#2196F3", hover="#1976D2", pressed="#0D47A1", fs=12)


class OrderPanel(QWidget):
    order_placed = pyqtSignal(str)

    def __init__(self, api: ApiClient, worker: ApiWorker, parent=None):
        super().__init__(parent)
        self._api = api
        self._worker = worker
        self._tick_future: Future | None = None
        self._order_future: Future | None = None
        self._setup_ui()
        self._start_price_sync()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(6)

        # === SELL panel ===
        sell_group = QGroupBox("SELL")
        sell_group.setStyleSheet(
            "QGroupBox { font-size: 16px; font-weight: bold; color: #f44336; "
            "border: 2px solid #f44336; border-radius: 6px; margin-top: 8px; padding-top: 12px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }"
        )
        sell_layout = QVBoxLayout(sell_group)
        sell_layout.addStretch()

        self._sell_market_btn = QPushButton("SELL MARKET")
        self._sell_market_btn.setMinimumSize(160, 45)
        self._sell_market_btn.setStyleSheet(SELL_MARKET_STYLE)
        self._sell_market_btn.clicked.connect(lambda: self._on_place_order("sell", is_market=True))
        sell_layout.addWidget(self._sell_market_btn)

        sell_layout.addSpacing(12)

        self._sell_limit_btn = QPushButton("SELL LIMIT")
        self._sell_limit_btn.setMinimumSize(160, 45)
        self._sell_limit_btn.setStyleSheet(SELL_LIMIT_STYLE)
        self._sell_limit_btn.clicked.connect(lambda: self._on_place_order("sell", is_market=False))
        sell_layout.addWidget(self._sell_limit_btn)

        sell_layout.addStretch()
        main_layout.addWidget(sell_group)

        # === Center inputs ===
        center_group = QGroupBox("Order Settings")
        center_layout = QGridLayout(center_group)
        row = 0

        center_layout.addWidget(QLabel("Symbol:"), row, 0)
        self._symbol_combo = QComboBox()
        self._symbol_combo.addItems(client_config.symbols)
        self._symbol_combo.setCurrentText(client_config.default_symbol)
        self._symbol_combo.setEditable(True)
        self._symbol_combo.currentTextChanged.connect(self._on_symbol_changed)
        center_layout.addWidget(self._symbol_combo, row, 1)

        row += 1
        center_layout.addWidget(QLabel("Lot:"), row, 0)
        self._lot_input = QLineEdit(str(client_config.default_lot_size))
        center_layout.addWidget(self._lot_input, row, 1)

        row += 1
        center_layout.addWidget(QLabel("Current Price:"), row, 0)
        self._current_price_label = QLabel("--")
        self._current_price_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        center_layout.addWidget(self._current_price_label, row, 1)

        row += 1
        center_layout.addWidget(QLabel("Entry Price:"), row, 0)
        self._price_input = QLineEdit()
        self._price_input.setPlaceholderText("Manual entry for limit orders")
        center_layout.addWidget(self._price_input, row, 1)

        row += 1
        center_layout.addWidget(QLabel("SL Offset:"), row, 0)
        self._sl_offset_input = QLineEdit(str(client_config.default_sl_offset))
        self._sl_offset_input.setToolTip("SL distance from entry price")
        center_layout.addWidget(self._sl_offset_input, row, 1)

        row += 1
        center_layout.addWidget(QLabel("Stop Loss:"), row, 0)
        self._sl_input = QLineEdit()
        self._sl_input.setPlaceholderText("Auto-calculated")
        center_layout.addWidget(self._sl_input, row, 1)

        row += 1
        center_layout.addWidget(QLabel("Take Profit:"), row, 0)
        self._tp_input = QLineEdit()
        self._tp_input.setPlaceholderText("Optional")
        center_layout.addWidget(self._tp_input, row, 1)

        row += 1
        self._spread_label = QLabel("Spread: --")
        self._spread_label.setStyleSheet("color: #666; font-style: italic;")
        center_layout.addWidget(self._spread_label, row, 0, 1, 2)

        main_layout.addWidget(center_group, stretch=1)

        # === BUY panel ===
        buy_group = QGroupBox("BUY")
        buy_group.setStyleSheet(
            "QGroupBox { font-size: 16px; font-weight: bold; color: #2196F3; "
            "border: 2px solid #2196F3; border-radius: 6px; margin-top: 8px; padding-top: 12px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }"
        )
        buy_layout = QVBoxLayout(buy_group)
        buy_layout.addStretch()

        self._buy_market_btn = QPushButton("BUY MARKET")
        self._buy_market_btn.setMinimumSize(160, 45)
        self._buy_market_btn.setStyleSheet(BUY_MARKET_STYLE)
        self._buy_market_btn.clicked.connect(lambda: self._on_place_order("buy", is_market=True))
        buy_layout.addWidget(self._buy_market_btn)

        buy_layout.addSpacing(12)

        self._buy_limit_btn = QPushButton("BUY LIMIT")
        self._buy_limit_btn.setMinimumSize(160, 45)
        self._buy_limit_btn.setStyleSheet(BUY_LIMIT_STYLE)
        self._buy_limit_btn.clicked.connect(lambda: self._on_place_order("buy", is_market=False))
        buy_layout.addWidget(self._buy_limit_btn)

        buy_layout.addStretch()
        main_layout.addWidget(buy_group)

    def _start_price_sync(self):
        self._price_timer = QTimer(self)
        self._price_timer.timeout.connect(self._on_price_tick)
        self._price_timer.start(1000)
        self._fetch_price()

    def _on_price_tick(self):
        self._check_tick_result()
        self._fetch_price()

    def _fetch_price(self):
        symbol = self._symbol_combo.currentText().strip()
        if not symbol:
            return
        if self._tick_future is not None and not self._tick_future.done():
            return
        self._tick_future = self._worker.submit(self._api.get_tick, symbol)

    def _check_tick_result(self):
        if self._tick_future is None or not self._tick_future.done():
            return
        future = self._tick_future
        self._tick_future = None
        try:
            tick = future.result()
            if tick is None:
                return
            spread = round(tick["ask"] - tick["bid"], 5)
            self._spread_label.setText(f"Spread: {spread}")
            self._current_price_label.setText(f"BID: {tick['bid']}  |  ASK: {tick['ask']}")
        except Exception:
            pass

    def _on_symbol_changed(self, symbol):
        self._price_input.clear()
        self._sl_input.clear()
        self._fetch_price()

    def _on_place_order(self, order_type: str, is_market: bool):
        if self._order_future is not None and not self._order_future.done():
            return

        try:
            symbol = self._symbol_combo.currentText().strip()
            if not symbol:
                return

            lot = float(self._lot_input.text())
            sl_text = self._sl_input.text().strip()
            sl = float(sl_text) if sl_text else None
            tp_text = self._tp_input.text().strip()
            tp = float(tp_text) if tp_text else None
            sl_offset = self.get_sl_offset()

            if is_market:
                self._order_future = self._worker.submit(
                    self._api.send_market_order, symbol, order_type, lot, sl, tp, sl_offset,
                )
                btn = self._buy_market_btn if order_type == "buy" else self._sell_market_btn
            else:
                price_text = self._price_input.text().strip()
                if not price_text:
                    QMessageBox.warning(self, "Error", "Entry price is required for limit orders")
                    return
                price = float(price_text)
                self._order_future = self._worker.submit(
                    self._api.send_limit_order, symbol, order_type, lot, price, sl, tp, sl_offset,
                )
                btn = self._buy_limit_btn if order_type == "buy" else self._sell_limit_btn

            btn.setEnabled(False)
            btn.setText("Sending...")
            self._start_order_poll()

        except ValueError as e:
            QMessageBox.warning(self, "Input Error", f"Invalid input: {e}")

    def _start_order_poll(self):
        self._order_poll_count = 0
        if not hasattr(self, '_order_poll'):
            self._order_poll = QTimer(self)
            self._order_poll.timeout.connect(self._check_order_result)
        self._order_poll.start(100)

    def _check_order_result(self):
        self._order_poll_count += 1
        if self._order_poll_count > 300:
            self._order_poll.stop()
            self.order_placed.emit("Order timeout: no response after 30s")
            self._reset_buttons()
            self._order_future = None
            return
        if self._order_future is None or not self._order_future.done():
            return
        self._order_poll.stop()
        future = self._order_future
        self._order_future = None

        try:
            result = future.result()
            if result.success:
                msg = f"Order placed! Ticket: {result.ticket}"
            else:
                msg = f"Order failed: {result.comment} (code: {result.retcode})"
            self.order_placed.emit(msg)
        except Exception as e:
            self.order_placed.emit(f"Order error: {e}")
        finally:
            self._reset_buttons()

    def _reset_buttons(self):
        for btn, text in [
            (self._buy_market_btn, "BUY MARKET"),
            (self._sell_market_btn, "SELL MARKET"),
            (self._buy_limit_btn, "BUY LIMIT"),
            (self._sell_limit_btn, "SELL LIMIT"),
        ]:
            btn.setEnabled(True)
            btn.setText(text)

    def get_sl_offset(self) -> float:
        text = self._sl_offset_input.text().strip()
        try:
            return float(text)
        except (ValueError, TypeError):
            return client_config.default_sl_offset

    def get_sl_value(self):
        text = self._sl_input.text().strip()
        return float(text) if text else None

    def get_tp_value(self):
        text = self._tp_input.text().strip()
        return float(text) if text else None
