"""Entry point for the QuickTrade remote UI client."""
import sys
import logging

from PyQt6.QtWidgets import QApplication

from client_app.config import client_config
from client_app.api_client import ApiClient
from client_app.ui.main_window import MainWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    api = ApiClient(
        base_url=client_config.api_url,
        token=client_config.api_token,
    )

    logger.info(f"Connecting to API at {client_config.api_url}")

    qt_app = QApplication(sys.argv)
    qt_app.setStyle("Fusion")

    window = MainWindow(api)
    window.show()

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
