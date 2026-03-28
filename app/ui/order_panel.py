import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QGroupBox, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, QTimer, Qt
from app.config import config
from app.core.sl_calculator import calculate_sl
from app.mt5.worker import MT5Worker
from app.mt5 import trading

logger = logging.getLogger(__name__)

# Shared button style
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
    """Two-panel layout: SELL (left) | Shared inputs (center) | BUY (right)."""

    order_placed = pyqtSignal(str)

    def __init__(self, worker: MT5Worker, parent=None):
        super().__init__(parent)
        self._worker = worker
        self._setup_ui()
        self._start_price_sync()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(6)

        # === SELL panel (left) ===
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

        self._sell_limit_btn = QPushButton("SELL LIMIT")
        self._sell_limit_btn.setMinimumSize(160, 45)
        self._sell_limit_btn.setStyleSheet(SELL_LIMIT_STYLE)
        self._sell_limit_btn.clicked.connect(lambda: self._on_place_order("sell", is_market=False))
        sell_layout.addWidget(self._sell_limit_btn)

        sell_layout.addStretch()
        main_layout.addWidget(sell_group)

        # === Shared inputs (center) ===
        center_group = QGroupBox("Order Settings")
        center_layout = QGridLayout(center_group)
        row = 0

        # Symbol
        center_layout.addWidget(QLabel("Symbol:"), row, 0)
        self._symbol_combo = QComboBox()
        self._symbol_combo.addItems(config.symbols)
        self._symbol_combo.setCurrentText(config.default_symbol)
        self._symbol_combo.setEditable(True)
        self._symbol_combo.currentTextChanged.connect(self._on_symbol_changed)
        center_layout.addWidget(self._symbol_combo, row, 1)

        # Lot
        row += 1
        center_layout.addWidget(QLabel("Lot:"), row, 0)
        self._lot_input = QLineEdit(str(config.default_lot_size))
        center_layout.addWidget(self._lot_input, row, 1)

        # Entry price (auto-synced from MT5)
        row += 1
        center_layout.addWidget(QLabel("Entry Price:"), row, 0)
        self._price_input = QLineEdit()
        self._price_input.setPlaceholderText("Auto-synced from MT5")
        center_layout.addWidget(self._price_input, row, 1)

        # SL (auto-filled from entry price - default offset)
        row += 1
        center_layout.addWidget(QLabel("Stop Loss:"), row, 0)
        self._sl_input = QLineEdit()
        self._sl_input.setPlaceholderText("Auto-calculated")
        center_layout.addWidget(self._sl_input, row, 1)

        # TP
        row += 1
        center_layout.addWidget(QLabel("Take Profit:"), row, 0)
        self._tp_input = QLineEdit()
        self._tp_input.setPlaceholderText("Optional")
        center_layout.addWidget(self._tp_input, row, 1)

        # Spread display
        row += 1
        self._spread_label = QLabel("Spread: --")
        self._spread_label.setStyleSheet("color: #666; font-style: italic;")
        center_layout.addWidget(self._spread_label, row, 0, 1, 2)

        main_layout.addWidget(center_group, stretch=1)

        # === BUY panel (right) ===
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

        self._buy_limit_btn = QPushButton("BUY LIMIT")
        self._buy_limit_btn.setMinimumSize(160, 45)
        self._buy_limit_btn.setStyleSheet(BUY_LIMIT_STYLE)
        self._buy_limit_btn.clicked.connect(lambda: self._on_place_order("buy", is_market=False))
        buy_layout.addWidget(self._buy_limit_btn)

        buy_layout.addStretch()
        main_layout.addWidget(buy_group)

    def _start_price_sync(self):
        """Sync current price from MT5 every second."""
        self._price_timer = QTimer(self)
        self._price_timer.timeout.connect(self._fetch_price)
        self._price_timer.start(1000)
        self._fetch_price()

    def _fetch_price(self):
        symbol = self._symbol_combo.currentText().strip()
        if not symbol:
            return
        future = self._worker.submit(self._get_tick, symbol)
        future.add_done_callback(self._on_tick_received)

    @staticmethod
    def _get_tick(symbol):
        from app.mt5 import mt5_module as mt5
        return mt5.symbol_info_tick(symbol)

    def _on_tick_received(self, future):
        try:
            tick = future.result()
            if tick is None:
                return
            spread = round(tick.ask - tick.bid, 5)
            self._spread_label.setText(f"Spread: {spread}  |  BID: {tick.bid}  ASK: {tick.ask}")

            # Auto-fill entry price if user hasn't manually edited it
            if not self._price_input.hasFocus():
                mid = round((tick.ask + tick.bid) / 2, 5)
                self._price_input.setText(str(mid))

            # Auto-fill SL from entry price + default offset (if not focused)
            if not self._sl_input.hasFocus():
                price = float(self._price_input.text()) if self._price_input.text() else mid
                # Default to BUY SL (price - offset); user can edit before placing
                sl_value = calculate_sl("buy", price, config.default_sl_offset)
                self._sl_input.setText(str(sl_value))
        except Exception:
            pass

    def _on_symbol_changed(self, symbol):
        self._price_input.clear()
        self._fetch_price()

    def _on_place_order(self, order_type: str, is_market: bool):
        try:
            symbol = self._symbol_combo.currentText().strip()
            if not symbol:
                return

            lot = float(self._lot_input.text())
            sl_text = self._sl_input.text().strip()
            sl = float(sl_text) if sl_text else None
            tp_text = self._tp_input.text().strip()
            tp = float(tp_text) if tp_text else None

            if is_market:
                def _execute_market():
                    from app.mt5 import mt5_module as mt5
                    tick = mt5.symbol_info_tick(symbol)
                    if tick is None:
                        from app.models.trade import TradeResult
                        return TradeResult(success=False, comment=f"Cannot get tick for {symbol}")
                    price = tick.ask if order_type == "buy" else tick.bid
                    final_sl = sl if sl is not None else calculate_sl(order_type, price, config.default_sl_offset)
                    return trading.send_market_order(symbol, order_type, lot, final_sl, tp)

                future = self._worker.submit(_execute_market)
                future.add_done_callback(self._on_order_result)

                btn = self._buy_market_btn if order_type == "buy" else self._sell_market_btn
                btn.setEnabled(False)
                btn.setText("Sending...")
            else:
                price_text = self._price_input.text().strip()
                if not price_text:
                    QMessageBox.warning(self, "Error", "Entry price is required for limit orders")
                    return
                price = float(price_text)
                if sl is None:
                    sl = calculate_sl(order_type, price, config.default_sl_offset)

                future = self._worker.submit(
                    trading.send_limit_order, symbol, order_type, lot, price, sl, tp
                )
                future.add_done_callback(self._on_order_result)

                btn = self._buy_limit_btn if order_type == "buy" else self._sell_limit_btn
                btn.setEnabled(False)
                btn.setText("Sending...")

        except ValueError as e:
            QMessageBox.warning(self, "Input Error", f"Invalid input: {e}")

    def _on_order_result(self, future):
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
            for btn, text in [
                (self._buy_market_btn, "BUY MARKET"),
                (self._sell_market_btn, "SELL MARKET"),
                (self._buy_limit_btn, "BUY LIMIT"),
                (self._sell_limit_btn, "SELL LIMIT"),
            ]:
                btn.setEnabled(True)
                btn.setText(text)
