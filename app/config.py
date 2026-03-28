import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.json"

DEFAULTS = {
    "sync_interval_ms": 30000,
    "default_sl_offset": 10.0,
    "default_lot_size": 0.01,
    "default_symbol": "XAUUSD",
    "symbols": ["XAUUSD"],
}


class Config:
    def __init__(self):
        self._data = dict(DEFAULTS)
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            self._data.update(user_config)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getattr__(self, name):
        if name.startswith("_"):
            return super().__getattribute__(name)
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"Config has no attribute '{name}'")


config = Config()
