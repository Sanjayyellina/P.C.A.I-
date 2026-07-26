"""
P.C.A.I. hashing utilities.

Mission
-------
Provide deterministic content hashing for immutable evidence references.
"""

from __future__ import annotations

import hashlib


def sha256_hex(content: bytes) -> str:
    """Return the lowercase SHA-256 digest for *content*."""

    return hashlib.sha256(content).hexdigest()
