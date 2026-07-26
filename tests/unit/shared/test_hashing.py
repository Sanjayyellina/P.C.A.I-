"""Unit tests for deterministic content hashing."""

from pcai.shared.hashing import sha256_hex


def test_sha256_hex_matches_known_digest() -> None:
    assert sha256_hex(b"pcai") == "37837c04cdce9a716e7465e2ddab048538527a94f3f2b9ab27c6600c7eb94dd3"
