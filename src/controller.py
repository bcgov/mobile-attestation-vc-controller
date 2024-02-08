import base64
import json
import secrets
import logging
from flask import Flask, request, make_response
from traction import get_connection, send_message, offer_attestation_credential
from apple import verify_attestation_statement
from goog import verify_integrity_token
import os
from dotenv import load_dotenv
from redis_config import redis_instance
from constants import auto_expire_nonce, app_id, app_vendor, AttestationMethod
from datetime import datetime

if os.getenv("FLASK_ENV") == "development":
    load_dotenv()

server = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handle_message(message, content):
    action = content.get("action")
    handler = {
        "request_nonce": handle_request_nonce,
        "challenge_response": handle_challenge_response,
    }.get(action, handle_default)

    return handler(message["connection_id"], content)


def report_failure(connection_id):
    message_templates_path = os.getenv("MESSAGE_TEMPLATES_PATH")
    with open(os.path.join(message_templates_path, "report_failure.json"), "r") as f:
        report_failure = json.load(f)

    json_str = json.dumps(report_failure)
    base64_str = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")

    logger.info(f"sending report failure message to {connection_id}")

    send_message(connection_id, base64_str)


def handle_request_nonce(connection_id, content):
    logger.info("handle_request_nonce")
    connection = get_connection(connection_id)
    logger.info(f"fetched connection, id = {connection_id}")

    if connection is None or connection["rfc23_state"] != "completed":
        logger.info(f"connection not completed, id = {connection_id}")
        return

    message_templates_path = os.getenv("MESSAGE_TEMPLATES_PATH")
    with open(
        os.path.join(message_templates_path, "request_attestation.json"), "r"
    ) as f:
        request_attestation = json.load(f)

    nonce = secrets.token_hex(16)
    # cache nonce with connection id as key, allow it to expire
    # after n seconds
    redis_instance.setex(connection_id, auto_expire_nonce, nonce)

    request_attestation["nonce"] = nonce
    json_str = json.dumps(request_attestation)
    base64_str = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")

    logger.info(f"sending request attestation message to {connection_id}")

    send_message(connection_id, base64_str)


def handle_challenge_response(connection_id, content):
    logger.info("handle_attestation_challenge")

    attestation_object = content.get("attestation_object")
    platform = content.get("platform")
    app_version = content.get("app_version")
    os_version_parts = content.get("os_version").split(" ")
    method = (
        AttestationMethod.AppleAppAttestation.value
        if platform == "apple"
        else AttestationMethod.GooglePlayIntegrity.value
    )
    is_valid_challenge = False

    # fetch nonce from cache using connection id as key
    nonce = redis_instance.get(connection_id)
    if not nonce:
        logger.info("No cached nonce")
        report_failure(connection_id)
        return

    message_templates_path = os.getenv("MESSAGE_TEMPLATES_PATH")
    with open(os.path.join(message_templates_path, "offer.json"), "r") as f:
        offer = json.load(f)

    offer["connection_id"] = connection_id
    offer["credential_preview"]["attributes"] = [
        {"name": "operating_system", "value": os_version_parts[0]},
        {"name": "operating_system_version", "value": os_version_parts[1]},
        {"name": "validation_method", "value": method},
        {"name": "app_id", "value": ".".join(app_id.split(".")[1:])},
        {"name": "app_vendor", "value": app_vendor},
        {"name": "issue_date_dateint", "value": datetime.now().strftime("%Y%m%d")},
        {"name": "app_version", "value": app_version},
    ]

    if platform == "apple":
        logger.info("testing apple challenge")
        key_id = content.get("key_id")
        is_valid_challenge = verify_attestation_statement(
            attestation_object, key_id, nonce
        )
    elif platform == "google":
        logger.info("testing google challenge")
        is_valid_challenge = verify_integrity_token(attestation_object, nonce)
    else:
        logger.info("unsupported platform")
        report_failure(connection_id)

    if is_valid_challenge:
        logger.info("valid challenge")
        offer_attestation_credential(offer)
    else:
        logger.info("invalid challenge")
        report_failure(connection_id)


def handle_default(connection_id, content):
    # Handle default case
    pass


def is_base64(s):
    try:
        # Attempt to decode the string as base64
        base64.b64decode(s)
        return True
    except Exception:
        # If an exception is raised, the string is not base64 encoded
        return False


def decode_base64_to_json(s):
    decoded = base64.b64decode(s)
    json_str = decoded.decode("utf-8")
    json_obj = json.loads(json_str)

    return json_obj


@server.route("/topic/ping/", methods=["POST"])
def ping():
    logger.info("Run POST /ping/")
    return make_response("", 204)


@server.route("/topic/basicmessages/", methods=["POST"])
def basicmessages():
    logger.info("Run POST /topic/basicmessages/")
    message = request.get_json()
    content = message["content"]

    if is_base64(content):
        decoded_content = decode_base64_to_json(content)
        if decoded_content["type"] == "attestation":
            handle_message(message, decoded_content)

    return make_response("", 204)


if __name__ == "__main__":
    server.run(debug=True, port=5501)
