"""Build script to create standalone .exe using PyInstaller.
Run on Windows: uv run python build_exe.py
"""
import subprocess
import sys
import importlib.util
from pathlib import Path


def find_mt5_binary():
    """Find the MetaTrader5 .pyd binary to bundle."""
    spec = importlib.util.find_spec("MetaTrader5")
    if spec is None or spec.origin is None:
        return None
    pkg_dir = Path(spec.origin).parent
    pyd_files = list(pkg_dir.glob("*.pyd"))
    return pyd_files


def main():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "QuickTradeApp",
        "--add-data", "config.json;.",
        "--hidden-import", "MetaTrader5",
        "--hidden-import", "MetaTrader5._core",
    ]

    # Bundle MT5 .pyd native binary
    pyd_files = find_mt5_binary()
    if pyd_files:
        for pyd in pyd_files:
            cmd.extend(["--add-binary", f"{pyd};MetaTrader5"])
            print(f"Bundling MT5 binary: {pyd}")
    else:
        print("WARNING: MetaTrader5 .pyd not found — exe may not connect to MT5")

    # Collect entire MetaTrader5 package to be safe
    cmd.extend(["--collect-all", "MetaTrader5"])

    cmd.append("run.py")

    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("\nBuild complete! Exe at: dist/QuickTradeApp.exe")


if __name__ == "__main__":
    main()
