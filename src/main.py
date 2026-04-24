"""Entry point."""
from __future__ import annotations

import sys

from .app import App
from .config import load_config


def main() -> int:
    cfg = load_config()
    app = App(cfg)
    try:
        app.run()
    except KeyboardInterrupt:
        app._shutdown()  # type: ignore[attr-defined]
    return 0


if __name__ == "__main__":
    sys.exit(main())
