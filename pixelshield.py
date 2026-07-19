#!/usr/bin/env python3
"""
PixelShield – Main Entry Point
Run with:
    python pixelshield.py [command] [options]
Or after installation:
    pixelshield [command] [options]
"""

import sys
import os

# Allow running from project root without installation.
sys.path.insert(0, os.path.dirname(__file__))

from cli.app import app

if __name__ == "__main__":
    app()
