"""Unit tests for deterministic content hashing."""

from pcai.shared.hashing import sha256_hex


def test_sha256_hex_matches_known_digest() -> None:
    assert sha256_hex(b"pcai") == "71dd6c904f0575b9e75edd4373e5aad5cf986ca481119ec2fea3d2a30393bade"
