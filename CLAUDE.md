# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Python desktop app for quick trading via MetaTrader 5 (MT5). PyQt6 GUI with a dedicated MT5 worker thread for non-blocking operations. Windows-only for real MT5; mock module for development on other platforms.

## Commands

```bash
# Install dependencies
uv sync

# Run the app
uv run tradingapp

# Build standalone .exe
uv sync --extra build
uv run python build_exe.py
```

## Architecture

**MT5 single-thread constraint**: All MT5 API calls must go through `MT5Worker` (`app/mt5/worker.py`) — MT5's Python API is blocking and requires all calls on the same thread that called `initialize()`.

- `worker.submit(fn)` → returns `Future` (for operations that need results: price ticks, order placement)
- `worker.fire_and_forget(fn)` → returns immediately (for bulk operations: set SL/TP, close positions)

**Platform abstraction**: `app/mt5/__init__.py` auto-selects real `MetaTrader5` on Windows or `app/mt5/mock.py` on other platforms. All modules import via `from app.mt5 import mt5_module as mt5`.

**UI polling pattern**: Since MT5 calls happen on a background thread, the UI uses `QTimer`-based polling to check `Future.done()` rather than callbacks — keeps everything on the Qt main thread.

**Config**: `config.json` at project root, loaded by `app/config.py` as singleton `config`. Access via `config.attribute_name`.

## Key Models (`app/models/trade.py`)

- `Position` / `PendingOrder` — represent MT5 open positions and pending orders
- `TradeRequest` — order parameters (symbol, type, lot, price, sl, tp)
- `TradeResult` — order execution result (success, ticket, retcode, comment)
