"""Build script to create standalone .exe using PyInstaller.
Run on Windows: uv run python build_exe.py
"""
import subprocess
import sys


def main():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "QuickTradeApp",
        "--add-data", "config.json;.",
        "--hidden-import", "MetaTrader5",
        "run.py",
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("\nBuild complete! Exe at: dist/QuickTradeApp.exe")


if __name__ == "__main__":
    main()
