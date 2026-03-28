# QuickTradeApp

A Python desktop application for quick trading via MetaTrader 5. Built with PyQt6 for a responsive UI and a dedicated MT5 worker thread for non-blocking operations.

## Features

- **Auto-sync positions** from MT5 on startup and every 30s (configurable)
- **Quick order entry** with SELL/BUY panels for Market and Limit orders
- **Auto Stop Loss** calculated from a configurable offset when SL is not specified (BUY: price - offset, SELL: price + offset)
- **Live price sync** into the Entry Price field, updated every second from MT5
- **Set SL** for all open positions of a pair from the Stop Loss input value
- **Set Target** for all open positions of a pair from the Take Profit input value
- **Set SL to Entry** sets stop loss to the entry price for all positions of a pair
- **Quick Take Profit** closes all open positions for a pair instantly
- All bulk actions use **fire-and-forget async** pattern for maximum speed

## UI Layout

```
+----------------+--------------------+----------------+
|                |   Order Settings   |                |
|  SELL MARKET   |   Symbol / Lot     |  BUY MARKET    |
|  SELL LIMIT    |   Entry Price      |  BUY LIMIT     |
|                |   SL / TP          |                |
|                |   Spread/BID/ASK   |                |
+----------------+--------------------+----------------+
|            Open Positions                            |
|  [Set SL] [Set Target] [Set SL→Entry] [Quick TP]    |
|  Ticket | Symbol | Type | Vol | Price | SL | TP | PL |
+------------------------------------------------------+
|  Status: Connected | Positions: 5 | Last sync: 12:00 |
+------------------------------------------------------+
```

## Requirements

- **Windows** (MetaTrader 5 only runs on Windows)
- **MetaTrader 5** terminal running locally
- Python 3.11+

## Setup & Run

```bash
# Install uv (if not installed)
pip install uv

# Install dependencies
uv sync

# Run the app
uv run tradingapp
```

## Configuration

Edit `config.json` to customize:

```json
{
    "sync_interval_ms": 30000,
    "default_sl_offset": 10.0,
    "default_lot_size": 0.01,
    "default_symbol": "XAUUSD",
    "symbols": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
}
```

| Setting | Description | Default |
|---|---|---|
| `sync_interval_ms` | Position sync interval in milliseconds | 30000 (30s) |
| `default_sl_offset` | Auto SL offset in points | 10.0 |
| `default_lot_size` | Default lot size for orders | 0.01 |
| `default_symbol` | Default selected symbol | XAUUSD |
| `symbols` | Available symbols in dropdown | XAUUSD, EURUSD, GBPUSD, USDJPY |

## Build Standalone .exe

```bash
# Install build dependencies
uv sync --extra build

# Build exe
uv run python build_exe.py
```

Output: `dist/QuickTradeApp.exe` - single file, no Python installation required.

## Architecture

```
app/
  config.py          # Config loader (config.json)
  models/trade.py    # Dataclasses: Position, TradeRequest, TradeResult
  mt5/
    worker.py        # Single-thread MT5 worker with task queue
    connection.py    # MT5 init/shutdown
    positions.py     # Get positions, modify SL/TP, close
    trading.py       # Market & Limit order execution
    mock.py          # Mock MT5 for development on non-Windows
  core/
    sync.py          # QTimer-driven periodic position sync
    sl_calculator.py # SL offset calculation
  ui/
    main_window.py   # Main window layout
    order_panel.py   # SELL/BUY panels + order settings
    positions_panel.py # Positions table + bulk action buttons
    status_bar.py    # Connection & sync status
```

**Key design**: All MT5 API calls go through a single dedicated worker thread (`worker.py`) since MT5's Python API is blocking and not thread-safe. The worker uses a FIFO queue with two modes:
- `submit(fn)` - returns a `Future` (for sync, order placement)
- `fire_and_forget(fn)` - returns immediately (for bulk SL/TP/close operations)

## License

MIT
