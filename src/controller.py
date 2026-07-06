import json
import logging
import os
import random
import secrets
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, make_response, request

from apple import verify_attestation_statement
from constants import (
    AttestationMethod,
    app_vendor,
    attestation_cred_def_ids,
    auto_expire_nonce,
)
from goog import verify_integrity_token
from redis_config import redis_instance
from traction import (
    offer_attestation_credential,
    send_drpc_request,
    send_drpc_response,
)

if os.getenv("FLASK_ENV") == "development":
    load_dotenv()

server = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Agents/mediators poll /topic/ping/ constantly; log only the first ping per
# method so the signal isn't drowned out in the logs.
_ping_logged = {"GET": False, "POST": False}

error_codes = {
    32601: "method not found",
    32602: "invalid params",
    32603: "nonce not found",
    32604: "cred def id not found",
    32605: "unsupported platform",
    32606: "invalid challenge",
    32607: "unable to cache nonce",
}


def handle_drpc_request(drpc_request, connection_id):
    handler = {
        "request_nonce": handle_drpc_request_nonce_v1,
        "request_nonce_v2": handle_drpc_request_nonce_v2,
        "request_attestation_v2": handle_drpc_request_attestation_v2,
    }.get(drpc_request["method"], handle_drpc_default)

    return handler(drpc_request, connection_id)


def handle_drpc_response(drpc_response, connection_id):
    handler = {
        "request_attestation_v1": handle_drpc_request_attestation_v1,
    }.get(drpc_response["request"]["method"], handle_drpc_default)

    return handler(drpc_response, connection_id)


def handle_drpc_default(drpc_request, connection_id):
    return {
        "jsonrpc": "2.0",
        "error": {
            "code": 32601,
            "message": f"{error_codes.get(32601, 'Unknown error')}",
        },
        "id": drpc_request.get("id", random.randint(0, 1000000)),
    }


def handle_drpc_request_nonce_v1(drpc_request, connection_id):
    logger.info("handle_drpc_request_nonce_v1")

    nonce = secrets.token_hex(16)
    request_attestation = {
        "jsonrpc": "2.0",
        "method": "request_attestation_v1",
        "params": {"nonce": nonce},
        "id": random.randint(0, 1000000),
    }

    # Cache nonce with connection id as key, allow it to expire
    # after `auto_expire_nonce` seconds
    redis_instance.setex(connection_id, auto_expire_nonce, nonce)

    # The response to a request for a nonce is a request for
    # attestation. This is fixed in v2 of the protocol.
    send_drpc_request(connection_id, request_attestation)

    return {}  # return empty response


def handle_drpc_request_nonce_v2(drpc_request, connection_id):
    logger.info("handle_drpc_request_nonce_v2")

    try:
        drpc_request_id = drpc_request.get("id", random.randint(0, 1000000))
        nonce = secrets.token_hex(16)

        # Cache nonce with connection id as key, allow it to expire
        # after `auto_expire_nonce` seconds
        redis_instance.setex(connection_id, auto_expire_nonce, nonce)
    except Exception as e:
        logger.info(f"Unable to cache nonce for connection id: {connection_id}, {e}")
        return report_failure(drpc_request_id, 32607)

    response = {
        "jsonrpc": "2.0",
        "result": {"status": "success", "nonce": nonce},
        "id": drpc_request_id,
    }

    return response


def handle_drpc_request_attestation_v1(drpc_response, connection_id):
    logger.info("handle_drpc_request_attestation_v1")

    result = drpc_response.get("response").get("result")
    if not result:
        logger.warning("Unable to get result from drpc response, aborting")
        return

    attestation_object = result.get("attestation_object")
    platform = result.get("platform")
    app_version = result.get("app_version")
    os_version = result.get("os_version")
    key_id = result.get("key_id", None)

    # fetch nonce from cache using connection id as key
    nonce = redis_instance.get(connection_id)
    if not nonce:
        logger.warning(f"No cached nonce for connection {connection_id}, aborting")
        return

    if None in [attestation_object, nonce, platform, app_version, os_version]:
        logger.warning("Attestation parameters missing, aborting")
        return

    if platform == "apple" and key_id is None:
        logger.warning("Key id missing for apple attestation, aborting")
        return

    try:
        return validate_and_offer(
            (attestation_object, key_id),
            nonce,
            platform,
            app_version,
            os_version,
            connection_id,
        )
    except Exception as e:
        logger.info(f"Error processing attestation {str(e)}")


def handle_drpc_request_attestation_v2(drpc_request, connection_id):
    logger.info("handle_drpc_request_attestation_v2")

    attestation_params = drpc_request.get("params")
    drpc_request_id = drpc_request.get("id", random.randint(0, 1000000))

    if not attestation_params:
        return report_failure(drpc_request_id, 32602)

    attestation_object = attestation_params.get("attestation_object")
    platform = attestation_params.get("platform")
    app_version = attestation_params.get("app_version")
    os_version = attestation_params.get("os_version")
    key_id = attestation_params.get("key_id", None)
    drpc_request_id = drpc_request.get("id", random.randint(0, 1000000))

    # fetch nonce from cache using connection id as key
    nonce = redis_instance.get(connection_id)
    if not nonce:
        logger.info("No cached nonce")
        return report_failure(drpc_request_id, 32603)

    if None in [attestation_object, nonce, platform, app_version, os_version]:
        logger.info("Attestation paremeters missing")
        return report_failure(drpc_request_id, 32602)

    if platform == "apple" and key_id is None:
        logger.info("Key id missing for apple attestation")
        return report_failure(drpc_request_id, 32602)

    try:
        rv = validate_and_offer(
            (attestation_object, key_id),
            nonce,
            platform,
            app_version,
            os_version,
            connection_id,
        )

        if rv is not None:
            return report_failure(drpc_request_id, rv)

        response = {
            "jsonrpc": "2.0",
            "result": {"status": "success"},
            "id": drpc_request_id,
        }

        return response

    except Exception as e:
        logger.info(f"Error processing attestation: {e}")
        return report_failure(drpc_request_id, 32606)


# TODO(jl): Break into seporate validate and offer functions.
def validate_and_offer(attestation_data, nonce, platform, app_version, os_version, connection_id):
    attestation_object, key_id = attestation_data
    os_version_parts = os_version.split(" ")
    method = (
        AttestationMethod.AppleAppAttestation.value
        if platform == "apple"
        else AttestationMethod.GooglePlayIntegrity.value
    )

    message_templates_path = os.getenv("MESSAGE_TEMPLATES_PATH")
    with open(os.path.join(message_templates_path, "offer.json"), "r") as f:
        offer = json.load(f)

    did = os.getenv("TRACTION_LEGACY_DID")

    def pred(cred_def):
        return did in cred_def

    # find the cred def id that contains the current
    # traction issuer did
    cred_def_id = next(filter(pred, attestation_cred_def_ids), None)
    if cred_def_id is None:
        logger.info("No matching cred def id")
        return 32604

    offer["filter"]["anoncreds"]["cred_def_id"] = cred_def_id
    offer["connection_id"] = connection_id

    # The verifiers return the actual attesting bundle on success (None on
    # failure), so the issued cred reflects the real bundle, not a constant.
    if platform == "apple":
        logger.info("testing apple challenge")
        matched_app_id = verify_attestation_statement(attestation_object, key_id, nonce)
        # strip the Apple Team ID prefix to get the bundle id
        attestation_app_id = ".".join(matched_app_id.split(".")[1:]) if matched_app_id else None
    elif platform == "google":
        logger.info("testing google challenge")
        attestation_app_id = verify_integrity_token(attestation_object, nonce)
    else:
        logger.info("unsupported platform")
        return 32605

    if not attestation_app_id:
        logger.info("invalid challenge")
        return 32606

    logger.info("valid challenge")
    offer["credential_preview"]["attributes"] = [
        {"name": "operating_system", "value": os_version_parts[0]},
        {"name": "operating_system_version", "value": os_version_parts[1]},
        {"name": "validation_method", "value": method},
        {"name": "app_id", "value": attestation_app_id},
        {"name": "app_vendor", "value": app_vendor},
        {"name": "issue_date_dateint", "value": datetime.now().strftime("%Y%m%d")},
        {"name": "app_version", "value": app_version},
    ]
    offer_attestation_credential(offer)

    return None


def report_failure(drpc_request_id, code):
    return {
        "jsonrpc": "2.0",
        "error": {"code": code, "message": f"{error_codes.get(code, 'Unknown error')}"},
        "id": drpc_request_id,
    }


@server.route("/topic/ping/", methods=["POST", "GET"])
def ping():
    if not _ping_logged.get(request.method, True):
        logger.info(f"Run {request.method} /ping/ (further pings suppressed)")
        _ping_logged[request.method] = True
    return make_response("", 204)


@server.route("/topic/issue_credential_v2_0/", methods=["POST"])
def issue_credential():
    logger.info("Run POST /topic/issue_credential_v2_0")

    connection_id = request.get_json().get("connection_id")
    state = request.get_json().get("state")

    logger.info(f"Credential for connection id {connection_id}, state {state}")

    return make_response("", 204)


# These are incoming requests a.k.a RPC calls to us from other agents.
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


# These are incoming responses a.k.a responses to RPC calls we made
# to other agents.
@server.route("/topic/drpc_response/", methods=["POST"])
def drpc_response():
    logger.info("Run POST /topic/drpc_response/")

    message = request.get_json()
    connection_id = message["connection_id"]
    drpc_response = message["response"]

    handle_drpc_response(drpc_response, connection_id)

    return make_response("", 204)


if __name__ == "__main__":
    server.run(debug=True, port=5501, host="0.0.0.0")
