import sys
import os
import re

sys.path.insert(0, "./src")

from traction import get_cred_def, create_cred_def

tag = "bcwallet"
revocation_registry_size = 0
schema_id = f"{os.environ.get('TRACTION_LEGACY_DID')}:2:app_attestation:1.0"
cred_def_id_regex = r"{}:3:CL:[0-9]+:{}".format(
    os.environ.get("TRACTION_LEGACY_DID"), tag
)

cred_def_ids = get_cred_def(schema_id)
matches = [
    s
    for s in cred_def_ids.get("credential_definition_ids")
    if re.search(cred_def_id_regex, s)
]

if len(matches) > 0:
    print(f"Credential defention {matches.pop()} already exists")
    exit(0)

response = create_cred_def(schema_id, tag, revocation_registry_size)

if (
    response is not None
    and response.get("txn") is not None
    and response.get("txn").get("state") == "request_sent"
):
    cred_def_id = response.get("txn").get("meta_data").get("context").get("cred_def_id")
    print(f"Cred def ID {cred_def_id} created successfully")
    exit(0)
else:
    print(f"Error creating cred def: {response}")
    exit(1)
