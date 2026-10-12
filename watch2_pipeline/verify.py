"""Compatibility entry point for shared verification."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1]/"dashboard_shared/verify.py"),run_name="__main__")
