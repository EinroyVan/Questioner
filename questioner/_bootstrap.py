"""Ensure imports resolve to this source tree, not a stale site-packages install."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ROOT_TEXT = str(PROJECT_ROOT)


def ensure_local_package() -> Path:
    """Prepend project root to sys.path and drop cached questioner modules."""
    if _ROOT_TEXT in sys.path:
        sys.path.remove(_ROOT_TEXT)
    sys.path.insert(0, _ROOT_TEXT)

    stale = [
        name
        for name in list(sys.modules)
        if name == "questioner" or name.startswith("questioner.")
    ]
    for name in stale:
        del sys.modules[name]

    return PROJECT_ROOT
