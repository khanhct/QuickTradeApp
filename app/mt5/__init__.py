"""MT5 module - uses real MetaTrader5 on Windows, mock on other platforms."""
import sys

if sys.platform == "win32":
    try:
        import MetaTrader5  # noqa: F401
        USE_MOCK = False
    except ImportError:
        USE_MOCK = True
else:
    USE_MOCK = True

if USE_MOCK:
    from app.mt5 import mock as mt5_module
    import logging
    logging.getLogger(__name__).warning("Using MOCK MT5 module (not on Windows or MT5 not installed)")
else:
    import MetaTrader5 as mt5_module

# Re-export so other modules can do: from app.mt5 import mt5_module
