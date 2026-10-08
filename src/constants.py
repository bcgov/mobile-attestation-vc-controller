import os
from enum import Enum


class AttestationMethod(Enum):
    AppleAppAttestation = "apple:app-attest"
    GooglePlayIntegrity = "google:play-integrity"


app_vendor = "Government of British Columbia"


def _csv_env(name, default):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# Apple App Attestation
# "<TeamID>.<bundle id>" for each app allowed to attest against this deployment.
allowed_apple_app_ids = _csv_env("ALLOWED_APPLE_APP_IDS", "L796QSLV3E.ca.bc.gov.BCWallet")
rp_id_hash_end = 32
counter_start = 33
counter_end = 37
aaguid_start = 37
aaguid_end = 53
cred_id_start = 55

# Google Play Integrity
integrity_scope = "https://www.googleapis.com/auth/playintegrity"
allowed_google_package_names = _csv_env("ALLOWED_GOOGLE_PACKAGE_NAMES", "ca.bc.gov.BCWallet")
PLAY_RECOGNIZED = "PLAY_RECOGNIZED"

# Credential issuance protocol used when a client doesn't ask for one.
# "v1" is issue-credential/1.0; "v2" is issue-credential/2.0 with an anoncreds filter.
supported_credential_protocols = ("v1", "v2")
default_credential_protocol = os.getenv("DEFAULT_CREDENTIAL_PROTOCOL", "v1")

# Redis
auto_expire_nonce = 60 * 10  # 10 minutes

# Attestation cred def IDs. The one whose issuer DID matches TRACTION_LEGACY_DID is
# used; override to point at a cred def in your own tenant.
attestation_cred_def_ids = _csv_env(
    "ATTESTATION_CRED_DEF_IDS",
    "NXp6XcGeCR2MviWuY51Dva:3:CL:33557:bcwallet_dev_v2,"
    "RycQpZ9b4NaXuT5ZGjXkUE:3:CL:120:bcwallet_test_v2,"
    "XqaRXJt4sXE6TRpfGpVbGw:3:CL:655:bcwallet",
)
