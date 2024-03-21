import os
import logging
from googleapiclient.discovery import build
from google.oauth2 import service_account
from dotenv import load_dotenv

dev_mode = os.getenv("FLASK_ENV") == "development"
allow_test_builds = os.getenv("ALLOW_TEST_BUILDS") == "true"

if dev_mode:
    load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
path = os.getenv("GOOGLE_AUTH_JSON_PATH")
creds = service_account.Credentials.from_service_account_file(
    path, scopes=["https://www.googleapis.com/auth/playintegrity"]
)


# should eventually confirm nonce matches here
def isValidVerdict(verdict, nonce):
    try:
        print(verdict)
        valid_device_verdicts = ["MEETS_DEVICE_INTEGRITY"]
        verdict_nonce = verdict["tokenPayloadExternal"]["requestDetails"]["nonce"]
        request_package_name = verdict["tokenPayloadExternal"]["requestDetails"][
            "requestPackageName"
        ]
        package_name = verdict["tokenPayloadExternal"]["appIntegrity"]["packageName"]
        app_verdict = verdict["tokenPayloadExternal"]["appIntegrity"][
            "appRecognitionVerdict"
        ]
        device_verdicts = verdict["tokenPayloadExternal"]["deviceIntegrity"][
            "deviceRecognitionVerdict"
        ]

        if (
            verdict_nonce == nonce
            and request_package_name == "ca.bc.gov.BCWallet"
            and package_name == "ca.bc.gov.BCWallet"
            and set(valid_device_verdicts).issubset(device_verdicts)
            and (app_verdict == "PLAY_RECOGNIZED" or allow_test_builds)
        ):
            return True
        else:
            return False
    except Exception as e:
        print(e)
        logger.info("Error evaluating verdict:", e)
        return False


# decrypt the integrity token on google's servers
def verify_integrity_token(token, nonce):
    try:
        service = build("playintegrity", "v1", credentials=creds)
        body = {"integrityToken": token}
        instance = service.v1()
        verdict = instance.decodeIntegrityToken(
            packageName="ca.bc.gov.BCWallet", body=body
        ).execute()

        if isValidVerdict(verdict, nonce):
            return True
        else:
            return False
    except Exception as e:
        logger.info("Error verifying integrity token:", e)
        return False


def main():
    pass


if __name__ == "__main__":
    main()
