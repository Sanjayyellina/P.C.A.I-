"""Deterministic hashing utilities."""

from __future__ import annotations

import hashlib


def sha256_hex(content: bytes) -> str:
    """Return a lowercase SHA-256 hexadecimal digest."""
    return hashlib.sha256(content).hexdigest()
