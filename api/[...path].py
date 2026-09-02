"""Vercel's catch-all Python Function for the existing Flask API."""
from pathlib import Path
import sys


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

# Import the one existing application; this module deliberately adds no routes.
from app import app  # noqa: E402,F401
