"""Pytest configuration for construct_impl tests."""
import sys
from pathlib import Path

# Add src to the FRONT of path to prioritize it
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) in sys.path:
    sys.path.remove(str(src_path))
sys.path.insert(0, str(src_path))
