"""
pytest conftest – ensures the PixelShield project root is on sys.path
so that `from core.xxx import ...` works from any test file.
"""

import sys
from pathlib import Path

# Add the PixelShield project root to the Python path.
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
