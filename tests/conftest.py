import sys
from pathlib import Path

# Ensure the repository root is on sys.path so tests can import the `backend` package
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def pytest_configure(config):
    # Helpful debug output when tests start
    print(f"PYTEST: Added project root to sys.path: {ROOT}")
