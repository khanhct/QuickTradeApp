from datetime import datetime
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt


class StatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        self._connection_label = QLabel("● Disconnected")
        self._connection_label.setStyleSheet("color: red; font-weight: bold;")

        self._sync_label = QLabel("Last sync: --")
        self._positions_label = QLabel("Positions: 0")

        layout.addWidget(self._connection_label)
        layout.addStretch()
        layout.addWidget(self._positions_label)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self._sync_label)

    def set_connected(self, connected: bool):
        if connected:
            self._connection_label.setText("● Connected")
            self._connection_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self._connection_label.setText("● Disconnected")
            self._connection_label.setStyleSheet("color: red; font-weight: bold;")

    def set_sync_time(self):
        now = datetime.now().strftime("%H:%M:%S")
        self._sync_label.setText(f"Last sync: {now}")

    def set_position_count(self, count: int):
        self._positions_label.setText(f"Positions: {count}")
