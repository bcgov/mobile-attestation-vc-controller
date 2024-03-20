from enum import Enum


class AttestationMethod(Enum):
    AppleAppAttestation = "apple:app-attest"
    GooglePlayIntegrity = "google:play-integrity"


app_vendor = "Government of British Columbia"

# Apple App Attestation
app_id = "L796QSLV3E.ca.bc.gov.BCWallet"
rp_id_hash_end = 32
counter_start = 33
counter_end = 37
aaguid_start = 37
aaguid_end = 53
cred_id_start = 55

# Redis
auto_expire_nonce = 60 * 10  # 10 minutes

# Attestation cred def IDs
attestation_cred_def_ids = [
    "NXp6XcGeCR2MviWuY51Dva:3:CL:33557:bcwallet",
    "RycQpZ9b4NaXuT5ZGjXkUE:3:CL:120:bcwallet",
    "XqaRXJt4sXE6TRpfGpVbGw:3:CL:655:bcwallet",
]
