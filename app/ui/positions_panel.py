import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QGroupBox, QHeaderView,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from app.mt5.worker import MT5Worker
from app.mt5 import positions as positions_mod
from app.models.trade import Position

logger = logging.getLogger(__name__)


class PositionsPanel(QWidget):
    """Displays open positions filtered by the symbol selected in OrderPanel."""

    request_sync = pyqtSignal()

    def __init__(self, worker: MT5Worker, parent=None):
        super().__init__(parent)
        self._worker = worker
        self._positions: list[Position] = []
        self._current_symbol = ""
        self._setup_ui()

    def _setup_ui(self):
        group = QGroupBox("Open Positions")
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(group)

        layout = QVBoxLayout(group)

        # Action bar
        action_layout = QHBoxLayout()
        action_layout.addStretch()

        # Set SL to Entry button
        self._sl_entry_btn = QPushButton("Set SL → Entry")
        self._sl_entry_btn.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; font-weight: bold; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #F57C00; }"
        )
        self._sl_entry_btn.clicked.connect(self._on_set_sl_to_entry)
        action_layout.addWidget(self._sl_entry_btn)

        # Quick Take Profit button
        self._quick_tp_btn = QPushButton("Quick TP (Close All)")
        self._quick_tp_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #388E3C; }"
        )
        self._quick_tp_btn.clicked.connect(self._on_quick_tp)
        action_layout.addWidget(self._quick_tp_btn)

        layout.addLayout(action_layout)

        # Status label
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self._status_label)

        # Positions table
        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels([
            "Ticket", "Symbol", "Type", "Volume", "Open Price",
            "SL", "TP", "Profit"
        ])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Ticket, Type, Volume smaller; Open Price, SL, TP, Profit wider
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # Ticket
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Symbol
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # Volume
        self._table.setColumnWidth(0, 80)   # Ticket
        self._table.setColumnWidth(1, 80)   # Symbol
        self._table.setColumnWidth(2, 50)   # Type
        self._table.setColumnWidth(3, 60)   # Volume
        layout.addWidget(self._table)

    def set_symbol(self, symbol: str):
        """Called from MainWindow when OrderPanel symbol changes."""
        self._current_symbol = symbol
        self._refresh_table()

    def update_positions(self, positions: list[Position]):
        """Called when sync completes with new position data."""
        self._positions = positions
        self._refresh_table()

    def _get_filtered_positions(self) -> list[Position]:
        if not self._current_symbol:
            return self._positions
        return [p for p in self._positions if p.symbol == self._current_symbol]

    def _refresh_table(self):
        filtered = self._get_filtered_positions()
        self._table.setRowCount(len(filtered))

        for row, pos in enumerate(filtered):
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

    def _on_set_sl_to_entry(self):
        """Fire-and-forget: set SL to entry price for all filtered positions."""
        filtered = self._get_filtered_positions()
        if not filtered:
            self._status_label.setText("No positions to modify")
            return

        count = len(filtered)
        self._status_label.setText(f"Setting SL → Entry for {count} positions ({self._current_symbol})...")

        for pos in filtered:
            self._worker.fire_and_forget(
                positions_mod.modify_sl, pos.ticket, pos.price_open
            )

        QTimer.singleShot(1000, self.request_sync.emit)

    def _on_quick_tp(self):
        """Fire-and-forget: close all filtered positions."""
        filtered = self._get_filtered_positions()
        if not filtered:
            self._status_label.setText("No positions to close")
            return

        count = len(filtered)
        self._status_label.setText(f"Closing {count} positions ({self._current_symbol})...")

        for pos in filtered:
            self._worker.fire_and_forget(
                positions_mod.close_position, pos.ticket
            )

        QTimer.singleShot(1000, self.request_sync.emit)
