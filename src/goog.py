import logging
import os

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

from constants import PLAY_RECOGNIZED, allowed_google_package_names, integrity_scope

dev_mode = os.getenv("FLASK_ENV") == "development"
allow_test_builds = os.getenv("ALLOW_TEST_BUILDS") == "true"

if dev_mode:
    load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Returns the package name that attested, or None if the verdict is not acceptable.
def isValidVerdict(verdict, nonce):
    try:
        valid_device_verdicts = ["MEETS_DEVICE_INTEGRITY"]
        verdict_nonce = verdict["tokenPayloadExternal"]["requestDetails"]["nonce"]
        request_package_name = verdict["tokenPayloadExternal"]["requestDetails"]["requestPackageName"]
        package_name = verdict["tokenPayloadExternal"]["appIntegrity"]["packageName"]
        app_verdict = verdict["tokenPayloadExternal"]["appIntegrity"]["appRecognitionVerdict"]
        device_verdicts = verdict["tokenPayloadExternal"]["deviceIntegrity"]["deviceRecognitionVerdict"]

        failures = []
        if verdict_nonce != nonce:
            failures.append("nonce mismatch")
        if request_package_name not in allowed_google_package_names:
            failures.append(f"requestPackageName {request_package_name} not allowed")
        if package_name not in allowed_google_package_names:
            failures.append(f"packageName {package_name} not allowed")
        if not set(valid_device_verdicts).issubset(device_verdicts):
            failures.append(f"device integrity {device_verdicts} insufficient")
        if not (app_verdict == PLAY_RECOGNIZED or allow_test_builds):
            failures.append(f"app recognition verdict is {app_verdict}")

        if failures:
            logger.warning(f"Verdict rejected: {'; '.join(failures)}")
            return None

        return package_name
    except Exception as e:
        logger.error(f"Error evaluating verdict: {e}")
        return None


def decode_order(preferred_package):
    """Allowed packages, with the client's hint first.

    The hint is only an ordering nudge and is ignored unless it is already allowed, so
    a client can never make us call decodeIntegrityToken for an unrelated package.
    """
    if preferred_package not in allowed_google_package_names:
        return allowed_google_package_names

    return [preferred_package] + [p for p in allowed_google_package_names if p != preferred_package]


# Decrypt the integrity token on google's servers. decodeIntegrityToken needs the
# package name up front and the token can't be read before decoding, so each allowed
# package is tried in turn. Returns the package name that attested, or None.
def verify_integrity_token(token, nonce, preferred_package=None):
    try:
        path = os.getenv("GOOGLE_AUTH_JSON_PATH")
        creds = service_account.Credentials.from_service_account_file(path, scopes=[integrity_scope])
        service = build("playintegrity", "v1", credentials=creds)
        body = {"integrityToken": token}
        instance = service.v1()
    except Exception as e:
        logger.error(f"Error building play integrity client: {e}")
        return None

    for package_name in decode_order(preferred_package):
        try:
            verdict = instance.decodeIntegrityToken(packageName=package_name, body=body).execute()
        except Exception as e:
            logger.info(f"Could not decode token as {package_name}: {e}")
            continue

        matched = isValidVerdict(verdict, nonce)
        if matched:
            return matched

    logger.warning(f"Token did not validate against any allowed package {allowed_google_package_names}")
    return None


def main():
    pass


if __name__ == "__main__":
    main()
