"""Unit tests for the deterministic helpers and failure paths in apple.py.

The challenge_response_apple.json fixture only carries placeholder base64, so a
full happy-path App Attest verification can't be reproduced offline. These tests
cover the pure crypto helpers and the early rejection/decoding paths instead.
"""

import hashlib

import apple


def test_create_app_id_hash_matches_sha256():
    app_id = "L796QSLV3E.ca.bc.gov.BCWallet"
    expected = hashlib.sha256(app_id.encode("utf-8")).hexdigest()
    assert apple.create_app_id_hash(app_id) == expected


def test_create_composite_nonce_matches_sha256():
    buffer = b"authdata-plus-client-data-hash"
    expected = hashlib.sha256(buffer).hexdigest()
    assert apple.create_composite_nonce(buffer) == expected


def test_create_authdata_with_nonce_hash_appends_nonce_digest():
    attestation_object = {"authData": b"AUTHDATA"}
    nonce = "challenge-nonce"
    result = apple.create_authdata_with_nonce_hash(attestation_object, nonce)
    expected = b"AUTHDATA" + hashlib.sha256(nonce.encode("utf-8")).digest()
    assert result == expected


def test_decode_invalid_attestation_object_returns_none():
    assert apple.decode_apple_attestation_object("%%% not base64 %%%") is None


def test_verify_attestation_statement_rejects_undecodable_object():
    # Undecodable attestation object -> verification fails closed.
    assert apple.verify_attestation_statement("%%% not base64 %%%", "key-id", "nonce") is False
