import os

from traction import create_schema, get_schema

schema_id = "%s:2:app_attestation:1.0" % os.environ.get("TRACTION_LEGACY_DID")

schemas = get_schema(schema_id)

if schemas.get("schema_ids"):
    print(f"Schema {schema_id} already exists")
    exit(0)

schema_name = "app_attestation"
schema_version = "1.0"
attributes = [
    "issue_date_dateint",
    "validation_method",
    "app_version",
    "app_vendor",
    "app_id",
    "operating_system",
    "operating_system_version",
]

created_schema = create_schema(schema_name, schema_version, attributes)

if created_schema:
    print(f"Schema {schema_id} created successfully")
    exit(0)
