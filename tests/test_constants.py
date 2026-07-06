"""Tests for the env-driven attestation allowlist parsing in constants.py.

The allowlists are parsed at import time, so each test sets the environment then
reloads the module. The autouse fixture reloads it again afterwards so a mutated
allowlist doesn't leak into other tests.
"""

import importlib

import pytest

import constants


@pytest.fixture(autouse=True)
def restore_constants():
    yield
    importlib.reload(constants)


def test_apple_allowlist_is_split_stripped_and_filtered(monkeypatch):
    monkeypatch.setenv("ALLOWED_APPLE_APP_IDS", " TEAM.a.b , , TEAM.c.d ")
    reloaded = importlib.reload(constants)
    assert reloaded.allowed_apple_app_ids == ["TEAM.a.b", "TEAM.c.d"]


def test_google_allowlist_is_split_stripped_and_filtered(monkeypatch):
    monkeypatch.setenv("ALLOWED_GOOGLE_PACKAGE_NAMES", "x.y , z.w")
    reloaded = importlib.reload(constants)
    assert reloaded.allowed_google_package_names == ["x.y", "z.w"]


def test_defaults_to_bcwallet_when_env_absent(monkeypatch):
    monkeypatch.delenv("ALLOWED_APPLE_APP_IDS", raising=False)
    monkeypatch.delenv("ALLOWED_GOOGLE_PACKAGE_NAMES", raising=False)
    reloaded = importlib.reload(constants)
    assert reloaded.allowed_apple_app_ids == ["L796QSLV3E.ca.bc.gov.BCWallet"]
    assert reloaded.allowed_google_package_names == ["ca.bc.gov.BCWallet"]
