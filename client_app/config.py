import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "client_config.json"

DEFAULTS = {
    "api_url": "http://localhost:8000",
    "api_token": "changeme-secret-token",
    "sync_interval_ms": 1000,
    "default_sl_offset": 10.0,
    "default_lot_size": 0.1,
    "default_symbol": "XAUUSD",
    "symbols": ["XAUUSD"],
}


class ClientConfig:
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
        raise AttributeError(f"ClientConfig has no attribute '{name}'")


client_config = ClientConfig()
