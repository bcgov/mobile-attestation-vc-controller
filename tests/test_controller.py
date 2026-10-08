"""Tests for issuance protocol selection and offer shaping in controller.py.

`build_offer` is a pure function over the offer template, so the v1 and v2 shapes
can be compared directly without a Traction instance.
"""

import copy

import pytest

import controller

CRED_DEF_ID = "NXp6XcGeCR2MviWuY51Dva:3:CL:33557:bcwallet_dev_v2"


@pytest.fixture
def offer_template():
    return copy.deepcopy(
        {
            "auto_issue": True,
            # Stale value so the tests prove build_offer replaces or drops it.
            "cred_def_id": "stale:3:CL:0:template",
            "credential_preview": {
                "@type": "issue-credential/1.0/credential-preview",
                "attributes": [],
            },
            "comment": "",
        }
    )


def test_v1_offer_keeps_cred_def_id_at_top_level(offer_template):
    offer = controller.build_offer(offer_template, CRED_DEF_ID, "v1")
    assert offer["cred_def_id"] == CRED_DEF_ID
    assert "filter" not in offer
    assert offer["credential_preview"]["@type"] == "issue-credential/1.0/credential-preview"


def test_v2_offer_moves_cred_def_id_into_anoncreds_filter(offer_template):
    offer = controller.build_offer(offer_template, CRED_DEF_ID, "v2")
    assert offer["filter"] == {"anoncreds": {"cred_def_id": CRED_DEF_ID}}
    assert "cred_def_id" not in offer
    assert offer["credential_preview"]["@type"] == "issue-credential/2.0/credential-preview"


def test_unsupported_protocol_is_rejected():
    rv = controller.validate_and_offer(
        ("attestation-object", None),
        "nonce",
        "google",
        "1.0.0-1",
        "Android 14",
        "connection-id",
        "v3",
    )
    assert rv == 32608


def test_each_supported_protocol_maps_to_an_endpoint():
    # A protocol the controller accepts but traction.py can't route would 500 at
    # issuance time rather than being rejected up front.
    assert set(controller.supported_credential_protocols) == set(
        controller.offer_attestation_credential.__globals__["issue_credential_endpoints"]
    )
