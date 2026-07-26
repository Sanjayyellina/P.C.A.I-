"""
P.C.A.I. shared identifiers.

Mission
-------
Provide explicit immutable identifier types so domain boundaries never rely on
anonymous strings.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FrameId:
    """Stable identifier for one captured frame."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("frame identifier must not be empty")

    def __str__(self) -> str:
        return self.value
