"""Compatibility entry point for the shared builder."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dashboard_shared.build import build

if __name__=="__main__":
    build()
