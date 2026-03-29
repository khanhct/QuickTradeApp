import sys
import logging
from PyQt6.QtWidgets import QApplication
from app.ui.main_window import MainWindow


class ColorFormatter(logging.Formatter):
    """Colorized console log formatter."""
    RESET = "\033[0m"
    COLORS = {
        logging.DEBUG:    "\033[90m",       # gray
        logging.INFO:     "\033[37m",       # white
        logging.WARNING:  "\033[33;1m",     # bold yellow
        logging.ERROR:    "\033[31;1m",     # bold red
        logging.CRITICAL: "\033[41;97;1m",  # white on red bg
    }

    def __init__(self):
        super().__init__("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        msg = super().format(record)
        return f"{color}{msg}{self.RESET}"


handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter())
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
