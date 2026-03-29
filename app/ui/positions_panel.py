import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QGroupBox, QHeaderView,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from app.mt5.worker import MT5Worker
from app.mt5 import positions as positions_mod
from app.models.trade import Position, PendingOrder

logger = logging.getLogger(__name__)


class PositionsPanel(QWidget):
    """Displays open positions and pending orders filtered by symbol."""

    request_sync = pyqtSignal()

    def __init__(self, worker: MT5Worker, parent=None):
        super().__init__(parent)
        self._worker = worker
        self._positions: list[Position] = []
        self._orders: list[PendingOrder] = []
        self._current_symbol = ""
        self._get_sl_value = None  # callback set by MainWindow
        self._get_tp_value = None  # callback set by MainWindow
        self._setup_ui()

    def _setup_ui(self):
        group = QGroupBox("Open Positions & Pending Orders")
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(group)

        layout = QVBoxLayout(group)

        # Action bar
        action_layout = QHBoxLayout()

        # Sync button
        self._sync_btn = QPushButton("Sync")
        self._sync_btn.setStyleSheet(
            "QPushButton { background-color: #607D8B; color: white; font-weight: bold; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #455A64; }"
        )
        self._sync_btn.clicked.connect(self._on_manual_sync)
        action_layout.addWidget(self._sync_btn)

        action_layout.addStretch()

        # Set SL from input
        self._set_sl_btn = QPushButton("Set SL")
        self._set_sl_btn.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #d32f2f; }"
        )
        self._set_sl_btn.clicked.connect(self._on_set_sl)
        action_layout.addWidget(self._set_sl_btn)

        # Set TP from input
        self._set_tp_btn = QPushButton("Set Target")
        self._set_tp_btn.setStyleSheet(
            "QPushButton { background-color: #9C27B0; color: white; font-weight: bold; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #7B1FA2; }"
        )
        self._set_tp_btn.clicked.connect(self._on_set_tp)
        action_layout.addWidget(self._set_tp_btn)

        # Set SL to Entry button
        self._sl_entry_btn = QPushButton("SL Entry")
        self._sl_entry_btn.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; font-weight: bold; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #F57C00; }"
        )
        self._sl_entry_btn.clicked.connect(self._on_set_sl_to_entry)
        action_layout.addWidget(self._sl_entry_btn)

        # Close Positions button
        self._close_pos_btn = QPushButton("Close Position")
        self._close_pos_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #388E3C; }"
        )
        self._close_pos_btn.clicked.connect(self._on_close_positions)
        action_layout.addWidget(self._close_pos_btn)

        # Cancel Pending button
        self._cancel_pending_btn = QPushButton("Close Pending")
        self._cancel_pending_btn.setStyleSheet(
            "QPushButton { background-color: #795548; color: white; font-weight: bold; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #5D4037; }"
        )
        self._cancel_pending_btn.clicked.connect(self._on_cancel_pending)
        action_layout.addWidget(self._cancel_pending_btn)

        layout.addLayout(action_layout)

        # Status label
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self._status_label)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(9)
        self._table.setHorizontalHeaderLabels([
            "Ticket", "Symbol", "Type", "Volume", "Price",
            "SL", "TP", "Profit", "Status"
        ])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(0, 80)
        self._table.setColumnWidth(1, 80)
        self._table.setColumnWidth(2, 80)
        self._table.setColumnWidth(3, 60)
        self._table.setColumnWidth(8, 70)
        layout.addWidget(self._table)

    def set_symbol(self, symbol: str):
        """Called from MainWindow when OrderPanel symbol changes."""
        self._current_symbol = symbol
        self._refresh_table()
        self.request_sync.emit()

    def update_positions(self, positions: list[Position]):
        """Called when sync completes with new position data."""
        logger.info(f"PositionsPanel.update_positions: received {len(positions)} positions, "
                     f"filter_symbol={self._current_symbol!r}")
        self._positions = positions
        self._refresh_table()

    def update_orders(self, orders: list[PendingOrder]):
        """Called when sync completes with new pending orders."""
        logger.info(f"PositionsPanel.update_orders: received {len(orders)} orders, "
                     f"filter_symbol={self._current_symbol!r}")
        self._orders = orders
        self._refresh_table()

    def _filter_by_symbol(self, items):
        if not self._current_symbol:
            return list(items)
        return [x for x in items if x.symbol == self._current_symbol]

    def _get_filtered_positions(self) -> list[Position]:
        return self._filter_by_symbol(self._positions)

    def _get_filtered_orders(self) -> list[PendingOrder]:
        return self._filter_by_symbol(self._orders)

    def _refresh_table(self):
        filtered_pos = self._get_filtered_positions()
        filtered_ord = self._get_filtered_orders()
        total = len(filtered_pos) + len(filtered_ord)
        self._table.setRowCount(total)

        row = 0

        # Open positions
        for pos in filtered_pos:
            self._table.setItem(row, 0, QTableWidgetItem(str(pos.ticket)))
            self._table.setItem(row, 1, QTableWidgetItem(pos.symbol))

            type_item = QTableWidgetItem(pos.type_str)
            type_item.setForeground(
                Qt.GlobalColor.blue if pos.type == 0 else Qt.GlobalColor.red
            )
            self._table.setItem(row, 2, type_item)

            self._table.setItem(row, 3, QTableWidgetItem(str(pos.volume)))
            self._table.setItem(row, 4, QTableWidgetItem(str(pos.price_open)))
            self._table.setItem(row, 5, QTableWidgetItem(str(pos.sl)))
            self._table.setItem(row, 6, QTableWidgetItem(str(pos.tp)))

            profit_item = QTableWidgetItem(f"{pos.profit:.2f}")
            profit_item.setForeground(
                Qt.GlobalColor.darkGreen if pos.profit >= 0 else Qt.GlobalColor.red
            )
            self._table.setItem(row, 7, profit_item)

            status_item = QTableWidgetItem("Open")
            status_item.setForeground(Qt.GlobalColor.darkGreen)
            self._table.setItem(row, 8, status_item)
            row += 1

        # Pending orders
        for order in filtered_ord:
            self._table.setItem(row, 0, QTableWidgetItem(str(order.ticket)))
            self._table.setItem(row, 1, QTableWidgetItem(order.symbol))

            type_item = QTableWidgetItem(order.type_str)
            type_item.setForeground(
                Qt.GlobalColor.blue if order.is_buy else Qt.GlobalColor.red
            )
            self._table.setItem(row, 2, type_item)

            self._table.setItem(row, 3, QTableWidgetItem(str(order.volume)))
            self._table.setItem(row, 4, QTableWidgetItem(str(order.price_open)))
            self._table.setItem(row, 5, QTableWidgetItem(str(order.sl)))
            self._table.setItem(row, 6, QTableWidgetItem(str(order.tp)))
            self._table.setItem(row, 7, QTableWidgetItem("--"))

            status_item = QTableWidgetItem("Pending")
            status_item.setForeground(QColor("#FF9800"))
            self._table.setItem(row, 8, status_item)

            # Dim the row background to distinguish from open positions
            for col in range(self._table.columnCount()):
                item = self._table.item(row, col)
                if item:
                    item.setBackground(QColor("#FFF8E1"))
            row += 1

    def _on_manual_sync(self):
        """Manual sync triggered by Sync button."""
        self._sync_btn.setEnabled(False)
        self._sync_btn.setText("Syncing...")
        self._status_label.setText("Syncing from MT5...")
        self.request_sync.emit()
        QTimer.singleShot(2000, lambda: (
            self._sync_btn.setEnabled(True),
            self._sync_btn.setText("Sync"),
        ))

    def _on_set_sl(self):
        """Fire-and-forget: set SL for all filtered positions from SL input."""
        if not self._get_sl_value:
            return
        sl = self._get_sl_value()
        if sl is None:
            self._status_label.setText("Stop Loss field is empty")
            return

        filtered = self._get_filtered_positions()
        if not filtered:
            self._status_label.setText("No positions to modify")
            return

        self._status_label.setText(f"Setting SL={sl} for {len(filtered)} positions...")
        for pos in filtered:
            self._worker.fire_and_forget(positions_mod.modify_sl, pos.ticket, sl)
        QTimer.singleShot(1000, self.request_sync.emit)

    def _on_set_tp(self):
        """Fire-and-forget: set TP for all filtered positions from TP input."""
        if not self._get_tp_value:
            return
        tp = self._get_tp_value()
        if tp is None:
            self._status_label.setText("Take Profit field is empty")
            return

        filtered = self._get_filtered_positions()
        if not filtered:
            self._status_label.setText("No positions to modify")
            return

        self._status_label.setText(f"Setting TP={tp} for {len(filtered)} positions...")
        for pos in filtered:
            self._worker.fire_and_forget(positions_mod.modify_tp, pos.ticket, tp)
        QTimer.singleShot(1000, self.request_sync.emit)

    def _on_set_sl_to_entry(self):
        """Fire-and-forget: set SL to entry price for all filtered positions."""
        filtered = self._get_filtered_positions()
        if not filtered:
            self._status_label.setText("No positions to modify")
            return

        count = len(filtered)
        self._status_label.setText(f"Setting SL → Entry for {count} positions...")

        for pos in filtered:
            self._worker.fire_and_forget(
                positions_mod.modify_sl, pos.ticket, pos.price_open
            )

        QTimer.singleShot(1000, self.request_sync.emit)

    def _on_close_positions(self):
        """Fire-and-forget: close all filtered open positions."""
        filtered_pos = self._get_filtered_positions()

        if not filtered_pos:
            self._status_label.setText("No positions to close")
            return

        self._status_label.setText(f"Closing {len(filtered_pos)} positions ({self._current_symbol})...")

        for pos in filtered_pos:
            self._worker.fire_and_forget(positions_mod.close_position, pos.ticket)

        QTimer.singleShot(1000, self.request_sync.emit)

    def _on_cancel_pending(self):
        """Fire-and-forget: cancel all filtered pending orders."""
        filtered_ord = self._get_filtered_orders()

        if not filtered_ord:
            self._status_label.setText("No pending orders to cancel")
            return

        self._status_label.setText(f"Cancelling {len(filtered_ord)} pending orders ({self._current_symbol})...")

        for order in filtered_ord:
            self._worker.fire_and_forget(positions_mod.cancel_order, order.ticket)

        QTimer.singleShot(1000, self.request_sync.emit)
