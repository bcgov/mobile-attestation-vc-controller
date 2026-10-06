"""Sends an attestation proof request to a wallet over an existing connection.

Useful for exercising the attestation flow end to end without depending on another
verifier: the wallet receives this request, sees it can't satisfy it, obtains an
attestation credential from this controller, and presents it back.

The restrictions are built from TRACTION_LEGACY_DID and ATTESTATION_CRED_DEF_IDS so the
proof always asks for a credential this tenant can actually issue.

Usage:
    python scripts/send_proof.py <connection_id> [--format anoncreds|indy]
"""

import argparse
import json
import os
import sys

sys.path.insert(0, "./src")

from dotenv import load_dotenv  # noqa: E402

# constants reads the environment at import time, so .env has to be loaded first.
if os.getenv("FLASK_ENV") == "development":
    load_dotenv(os.path.join("src", ".env"))

from constants import attestation_cred_def_ids  # noqa: E402
from traction import create_presentation_request, send_presentation_request  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("connection_id", help="connection to send the request over")
parser.add_argument("--format", default="anoncreds", choices=["anoncreds", "indy"])
args = parser.parse_args()

did = os.environ.get("TRACTION_LEGACY_DID")
if not did:
    sys.exit("TRACTION_LEGACY_DID is not set (is FLASK_ENV=development?)")

cred_def_id = next((c for c in attestation_cred_def_ids if did in c), None)
if not cred_def_id:
    sys.exit(f"No cred def in ATTESTATION_CRED_DEF_IDS is issued by {did}")

with open(os.path.join("./fixtures/", "request_attest_verif.json"), "r") as f:
    fixture = json.load(f)

# The fixture carries one format block; reuse its attribute list but point the
# restrictions at this tenant's own schema and cred def.
template = next(iter(fixture["presentation_request"].values()))
template["requested_attributes"]["attestationInfo"]["restrictions"] = [
    {"schema_id": f"{did}:2:app_attestation:1.0", "issuer_did": did},
    {"cred_def_id": cred_def_id},
]

proof_request = {
    "comment": fixture.get("comment", ""),
    "trace": fixture.get("trace", False),
    "presentation_request": {args.format: template},
}

print(f"Requesting {cred_def_id} over connection {args.connection_id}")

create_presentation_response = create_presentation_request(proof_request)
if not create_presentation_response:
    sys.exit("Could not create the presentation request")

payload = {
    "connection_id": args.connection_id,
    "presentation_request": {
        **create_presentation_response["by_format"]["pres_request"],
    },
}

send_presentation_response = send_presentation_request(payload)
if not send_presentation_response:
    sys.exit("Could not send the presentation request")

# A successful send reports a state of "request-sent"
print(f"Send presentation status = {send_presentation_response['state']}")
