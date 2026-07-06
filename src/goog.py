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


# should eventually confirm nonce matches here
# Returns the matched package name on success, else None.
def isValidVerdict(verdict, nonce):
    try:
        logger.debug(f"Evaluating Play Integrity verdict: {verdict}")
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
            failures.append(f"requestPackageName {request_package_name} not in allowlist")
        if package_name not in allowed_google_package_names:
            failures.append(f"packageName {package_name} not in allowlist")
        if not set(valid_device_verdicts).issubset(device_verdicts):
            failures.append(f"device integrity {device_verdicts} missing {valid_device_verdicts}")
        if not (app_verdict == PLAY_RECOGNIZED or allow_test_builds):
            failures.append(f"app recognition verdict {app_verdict} is not {PLAY_RECOGNIZED}")

        if failures:
            logger.warning(f"Play Integrity verdict rejected: {'; '.join(failures)}")
            return None

        return package_name
    except Exception as e:
        logger.error(f"Error evaluating verdict: {e}")
        return None


# decrypt the integrity token on google's servers
# Returns the matched package name on success, else None. Each allowed package
# is a distinct Play Integrity app, so the token must be decoded against the
# package that issued it; try each allowed package until one validates.
def verify_integrity_token(token, nonce):
    path = os.getenv("GOOGLE_AUTH_JSON_PATH")
    creds = service_account.Credentials.from_service_account_file(path, scopes=[integrity_scope])
    service = build("playintegrity", "v1", credentials=creds)
    body = {"integrityToken": token}
    instance = service.v1()

    for package_name in allowed_google_package_names:
        try:
            verdict = instance.decodeIntegrityToken(packageName=package_name, body=body).execute()
            matched = isValidVerdict(verdict, nonce)
            if matched:
                return matched
        except Exception as e:
            logger.error(f"Error verifying integrity token for {package_name}: {e}")

    logger.warning(
        "Play Integrity token did not validate against any allowed package: %s",
        allowed_google_package_names,
    )
    return None


def main():
    pass


if __name__ == "__main__":
    main()
