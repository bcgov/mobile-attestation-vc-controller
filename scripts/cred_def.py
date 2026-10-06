import os
import re
import sys

sys.path.insert(0, "./src")

from traction import create_cred_def, get_cred_def

tag = "bcwallet"
revocation_registry_size = 0
schema_id = f"{os.environ.get('TRACTION_LEGACY_DID')}:2:app_attestation:1.0"
cred_def_id_regex = r"{}:3:CL:[0-9]+:{}".format(os.environ.get("TRACTION_LEGACY_DID"), tag)

cred_def_ids = get_cred_def(schema_id)
matches = [s for s in cred_def_ids.get("credential_definition_ids") if re.search(cred_def_id_regex, s)]

if len(matches) > 0:
    print(f"Credential defention {matches.pop()} already exists")
    exit(0)

response = create_cred_def(schema_id, tag, revocation_registry_size)


def created_cred_def_id(response):
    """Reads the cred def id from either the anoncreds or the legacy endorsement shape."""
    if not response:
        return None

    state = response.get("credential_definition_state") or {}
    if state.get("credential_definition_id"):
        return state["credential_definition_id"]

    txn = response.get("txn") or {}
    if txn.get("state") == "request_sent":
        return txn.get("meta_data", {}).get("context", {}).get("cred_def_id")

    return None


cred_def_id = created_cred_def_id(response)

if cred_def_id:
    print(f"Cred def ID {cred_def_id} created successfully")
    exit(0)
else:
    print(f"Error creating cred def: {response}")
    exit(1)
