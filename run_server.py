"""Entry point for the QuickTrade API server."""
import logging
import uvicorn

from app.config import config
from app.mt5.worker import MT5Worker
from app.mt5 import connection
from app.api.server import app, set_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    # Start MT5 worker
    worker = MT5Worker()
    worker.start()

    # Initialize MT5 on the worker thread
    future = worker.submit(connection.initialize)
    success = future.result(timeout=10)
    if not success:
        logger.error("MT5 initialization failed. Server will start but trading will not work.")

    # Register worker with FastAPI app
    set_worker(worker)

    port = config.get("api_port", 8000)
    logger.info(f"Starting QuickTrade API server on port {port}")
    logger.info(f"API docs available at http://localhost:{port}/docs")

    try:
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    finally:
        worker.submit(connection.shutdown)
        worker.stop()


if __name__ == "__main__":
    main()
