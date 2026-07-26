"""
P.C.A.I. shared identifier value objects.

Identifiers are immutable domain values. Raw strings should not cross stable
Cell boundaries without validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class _UuidIdentifier:
    """Base class for validated UUID-backed identifiers."""

    value: str

    def __post_init__(self) -> None:
        try:
            UUID(self.value)
        except ValueError as error:
            raise ValueError(f"Invalid UUID identifier: {self.value}") from error

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class FrameId(_UuidIdentifier):
    """Unique identifier for one captured frame."""


@dataclass(frozen=True, slots=True)
class ObservationId(_UuidIdentifier):
    """Unique identifier for one immutable observation record."""
