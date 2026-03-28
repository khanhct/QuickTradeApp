import logging
from app.mt5 import mt5_module as mt5
logger = logging.getLogger(__name__)


def initialize() -> bool:
    """Initialize MT5 connection via local process. Must be called from the worker thread."""
    if not mt5.initialize():
        error = mt5.last_error()
        logger.error(f"MT5 initialize failed: {error}")
        return False

    info = mt5.terminal_info()
    if info:
        logger.info(f"MT5 connected: {info.name} build {info.build}")
    return True


def shutdown():
    """Shutdown MT5 connection."""
    mt5.shutdown()
    logger.info("MT5 connection closed")


def is_connected() -> bool:
    """Check if MT5 terminal is connected."""
    info = mt5.terminal_info()
    return info is not None and info.connected
