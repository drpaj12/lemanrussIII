"""Shared test helpers: Odin III availability (modelled on loki's tests/helpers.py)."""

from __future__ import annotations

import importlib


def odin_available() -> bool:
    """True when the odin3 module imports and the shared library loads."""
    try:
        mod = importlib.import_module("odin3")
        mod.Odin3()
    except Exception:
        return False
    return True
