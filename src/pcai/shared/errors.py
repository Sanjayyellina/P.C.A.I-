"""
P.C.A.I. shared errors.

Mission
-------
Expose stable machine-readable failure codes and safe user-facing messages.
"""

from __future__ import annotations


class PcaiError(Exception):
    """Base exception for safe, typed P.C.A.I. failures."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message


class InvalidImageError(PcaiError):
    """Raised when captured bytes cannot form an approved image observation."""
