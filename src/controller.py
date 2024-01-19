import base64
import json
import secrets
from flask import Flask, request, make_response
from traction import get_connection, send_message, offer_attestation_credential
from apple import verify_attestation_statement
from goog import verify_integrity_token
import os
from dotenv import load_dotenv
from redis_config import redis_instance
from constants import auto_expire_nonce

load_dotenv()

server = Flask(__name__)

def handle_message(message, content):
    action = content.get('action')
    handler = {
        'request_nonce': handle_request_nonce,
        'challenge_response': handle_challenge_response,
    }.get(action, handle_default)

    return handler(message['connection_id'], content)

def handle_request_nonce(connection_id, content):
    print("handle_request_nonce")
    connection = get_connection(connection_id)
    print(f"fetched connection = {connection}")
    if connection['rfc23_state'] != 'completed':
        print("connection is not completed")
        return

    message_templates_path = os.getenv("MESSAGE_TEMPLATES_PATH")
    with open(os.path.join(message_templates_path, 'request_attestation.json'), 'r') as f:
        request_attestation = json.load(f)

    nonce = secrets.token_hex(16)
    # cache nonce with connection id as key, allow it to expire
    # after n seconds
    redis_instance.setex(connection_id, auto_expire_nonce, nonce)

    request_attestation['nonce'] = nonce
    json_str = json.dumps(request_attestation)
    base64_str = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

    print(f"sending request attestation message to {connection_id}")

    send_message(connection_id, base64_str)

def handle_challenge_response(connection_id, content):
    print("handle_attestation_challenge")

    platform = content.get('platform')

    # fetch nonce from cache using connection id as key
    nonce = redis_instance.get(connection_id)
    if not nonce:
        print('No cached nonce')
        return

    if platform == 'apple':
        is_valid_challenge = verify_attestation_statement(content, nonce)
        if is_valid_challenge:
            print("valid apple challenge")
            offer_attestation_credential(connection_id)
        else:
            print("invalid apple challenge")
    elif platform == 'google':
        token = content.get('attestation_object')
        is_valid_challenge = verify_integrity_token(token, nonce)
        if is_valid_challenge:
            print("valid google integrity verdict")
            offer_attestation_credential(connection_id)
        else:
            print("invalid google integrity verdict")
    else:
        print("unsupported platform")


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
    json_str = decoded.decode('utf-8')
    json_obj = json.loads(json_str)

    return json_obj

@server.route('/topic/ping/', methods=['POST'])
def ping():
    print("Run POST /ping/")
    return make_response('', 204)

@server.route('/topic/basicmessages/', methods=['POST'])
def basicmessages():
    print("Run POST /topic/basicmessages/")
    message = request.get_json()
    content = message['content']

    if is_base64(content):
        decoded_content = decode_base64_to_json(content)
        if decoded_content['type'] == 'attestation':
            handle_message(message, decoded_content)

    return make_response('', 204)


if __name__ == '__main__':
    server.run(debug=True)
