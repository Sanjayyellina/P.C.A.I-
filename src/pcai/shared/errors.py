"""Typed P.C.A.I. domain errors."""

from __future__ import annotations


class PcaiError(Exception):
    """Base exception for safe, machine-readable P.C.A.I. failures."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message


class InvalidImageError(PcaiError):
    """Raised when image bytes or decoded image structure are invalid."""


class UnsupportedImageError(PcaiError):
    """Raised when a valid image falls outside the supported envelope."""
