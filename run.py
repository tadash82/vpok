#!/usr/bin/env python3
"""Entry point do Video Poker Clássico."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from videopoker.ui.app import App


def main() -> int:
    app = App()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
