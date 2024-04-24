import json
import secrets
import logging
import random
from flask import Flask, request, make_response
from traction import (
    send_drpc_response,
    send_drpc_request,
    offer_attestation_credential,
)
from apple import verify_attestation_statement
from goog import verify_integrity_token
import os
from dotenv import load_dotenv
from redis_config import redis_instance
from constants import (
    auto_expire_nonce,
    app_id,
    app_vendor,
    AttestationMethod,
    attestation_cred_def_ids,
)
from datetime import datetime

if os.getenv("FLASK_ENV") == "development":
    load_dotenv()

server = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handle_drpc_request(drpc_request, connection_id):
    handler = {
        "request_nonce": handle_drpc_request_nonce,
    }.get(drpc_request["method"], handle_drpc_default)

    return handler(drpc_request, connection_id)


def handle_drpc_default(drpc_request, connection_id):
    return {
        "jsonrpc": "2.0",
        "error": {"code": -32601, "message": "method not found"},
        "id": drpc_request["id"],
    }


def handle_drpc_request_nonce(drpc_request, connection_id):
    nonce = secrets.token_hex(16)
    request_attestation = {
        "jsonrpc": "2.0",
        "method": "request_attestation",
        "params": {"nonce": nonce},
        "id": random.randint(0, 1000000),
    }
    # cache nonce with connection id as key, allow it to expire
    # after n seconds
    redis_instance.setex(connection_id, auto_expire_nonce, nonce)

    send_drpc_request(connection_id, request_attestation)

    return {}


def handle_drpc_challenge_response(drpc_response, connection_id):
    logger.info("handle_attestation_challenge")
    attestation_resp = drpc_response.get("result")
    if not attestation_resp:
        report_failure(connection_id)
        return
    attestation_object = attestation_resp.get("attestation_object")
    platform = attestation_resp.get("platform")
    app_version = attestation_resp.get("app_version")
    os_version = attestation_resp.get("os_version")
    if None in [attestation_object, platform, app_version, os_version]:
        report_failure(connection_id)
        return
    os_version_parts = os_version.split(" ")
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

    did = os.getenv("TRACTION_LEGACY_DID")

    def pred(cred_def):
        return did in cred_def

    # find the cred def id that contains the current traction issuer did
    cred_def_id = next(filter(pred, attestation_cred_def_ids), None)
    if cred_def_id is None:
        logger.info("No matching cred def id")
        report_failure(connection_id)
        return

    offer["cred_def_id"] = cred_def_id
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
        key_id = attestation_resp.get("key_id")
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


def report_failure(connection_id):
    pass  # Will implement as DRPC once BC Wallet is capable of handling


@server.route("/topic/ping/", methods=["POST", "GET"])
def ping():
    if request.method == "POST":
        logger.info("Run POST /ping/")
    elif request.method == "GET":
        logger.info("Run GET /ping/")
    return make_response("", 204)


@server.route("/topic/drpc_request/", methods=["POST"])
def drpc_request():
    logger.info("Run POST /topic/drpc_request/")
    message = request.get_json()
    connection_id = message["connection_id"]
    thread_id = message["thread_id"]
    req = message["request"]
    drpc_request = req["request"]
    drpc_response = handle_drpc_request(drpc_request, connection_id)

    send_drpc_response(connection_id, thread_id, drpc_response)

    return make_response("", 204)


@server.route("/topic/drpc_response/", methods=["POST"])
def drpc_response():
    logger.info("Run POST /topic/drpc_response/")
    message = request.get_json()
    connection_id = message["connection_id"]
    print(message)
    req = message["response"]["request"]
    if req["method"] == "request_attestation":
        resp = message["response"]["response"]
        handle_drpc_challenge_response(resp, connection_id)
    return make_response("", 204)


if __name__ == "__main__":
    server.run(debug=True, port=5501, host="0.0.0.0")
