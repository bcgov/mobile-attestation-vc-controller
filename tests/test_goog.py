"""Unit tests for the Play Integrity verdict evaluation in goog.py.

isValidVerdict is a pure function over the decoded verdict dict, so it can be
exercised directly against the sample_google_verdict.json fixture.
"""

import pytest

import goog


@pytest.fixture
def nonce(google_verdict):
    return google_verdict["tokenPayloadExternal"]["requestDetails"]["nonce"]


@pytest.fixture(autouse=True)
def allowlist(monkeypatch):
    # Pin the allowlist/test-build flag so tests don't depend on the environment.
    # The fixture's app is ca.bc.gov.BCWallet with an UNRECOGNIZED_VERSION verdict,
    # so allow_test_builds must be True for the happy path.
    monkeypatch.setattr(goog, "allowed_google_package_names", ["ca.bc.gov.BCWallet"])
    monkeypatch.setattr(goog, "allow_test_builds", True)


def test_valid_verdict_returns_package_name(google_verdict, nonce):
    assert goog.isValidVerdict(google_verdict, nonce) == "ca.bc.gov.BCWallet"


def test_nonce_mismatch_rejected(google_verdict):
    assert goog.isValidVerdict(google_verdict, "not-the-nonce") is None


def test_package_not_in_allowlist_rejected(google_verdict, nonce, monkeypatch):
    monkeypatch.setattr(goog, "allowed_google_package_names", ["ca.bc.gov.SomethingElse"])
    assert goog.isValidVerdict(google_verdict, nonce) is None


def test_unrecognized_app_rejected_when_test_builds_disabled(google_verdict, nonce, monkeypatch):
    # Fixture's appRecognitionVerdict is UNRECOGNIZED_VERSION.
    monkeypatch.setattr(goog, "allow_test_builds", False)
    assert goog.isValidVerdict(google_verdict, nonce) is None


def test_play_recognized_app_passes_without_test_builds(google_verdict, nonce, monkeypatch):
    monkeypatch.setattr(goog, "allow_test_builds", False)
    google_verdict["tokenPayloadExternal"]["appIntegrity"]["appRecognitionVerdict"] = goog.PLAY_RECOGNIZED
    assert goog.isValidVerdict(google_verdict, nonce) == "ca.bc.gov.BCWallet"


def test_missing_device_integrity_rejected(google_verdict, nonce):
    google_verdict["tokenPayloadExternal"]["deviceIntegrity"]["deviceRecognitionVerdict"] = []
    assert goog.isValidVerdict(google_verdict, nonce) is None


def test_request_package_name_mismatch_rejected(google_verdict, nonce):
    google_verdict["tokenPayloadExternal"]["requestDetails"]["requestPackageName"] = "ca.bc.gov.Other"
    assert goog.isValidVerdict(google_verdict, nonce) is None


def test_malformed_verdict_returns_none(nonce):
    assert goog.isValidVerdict({"unexpected": "shape"}, nonce) is None
