import requests
import json
import os
from urllib.parse import urljoin
from dotenv import load_dotenv
import logging
import jwt
import datetime

if os.getenv("FLASK_ENV") == "development":
    load_dotenv()

bearer_token = None
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def is_token_expired(token):
    try:
        # Bypass signature verification since we only need to check the
        # expiration claim and this is our token (we trust it).
        decoded = jwt.decode(token, options={"verify_signature": False})

        # Extract the expiration claim, and check if the token is expired.
        exp_timestamp = decoded.get("exp")
        if exp_timestamp:
            exp = datetime.datetime.fromtimestamp(exp_timestamp, datetime.timezone.utc)
            if exp < datetime.datetime.now(datetime.timezone.utc):
                return True
            else:
                return False
        else:
            return True
    except Exception as e:
        # Handle potential exceptions
        print(f"An error occurred: {e}")


def fetch_bearer_token():
    global bearer_token

    if bearer_token and not is_token_expired(bearer_token):
        logger.info("Found existing unexpired bearer token, returning it")
        return bearer_token

    base_url = os.environ.get("TRACTION_BASE_URL")
    tenant_id = os.environ.get("TRACTION_TENANT_ID")
    api_key = os.environ.get("TRACTION_TENANT_API_KEY")
    endpoint = f"multitenancy/tenant/{tenant_id}/token"
    url = urljoin(base_url, endpoint)
    headers = {"Content-Type": "application/json", "accept": "application/json"}
    data = {"api_key": api_key}

    logger.info(f"Requesting bearer token for walletId {tenant_id}")

    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        logger.info("Token fetched successfully")
        response_data = json.loads(response.text)

        bearer_token = response_data["token"]
        if bearer_token is None:
            logger.error("Token doesn't exist in response data")

        return bearer_token
    else:
        logger.error(f"Error fetching token: {response.status_code}")
        logger.error(f"Text content for error: {response.text}")


def get_connection(conn_id):
    base_url = os.environ.get("TRACTION_BASE_URL")
    endpoint = f"/connections/{conn_id}"
    url = urljoin(base_url, endpoint)

    token = fetch_bearer_token()

    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    logger.info(f"Fetching connection {conn_id}")

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        logger.info("Connection fetched successfully")
        return json.loads(response.text)
    else:
        logger.error(f"Error fetching connection message: {response.status_code}")
        logger.error(f"Text content for error: {response.text}")

    return None


def send_drpc_response(conn_id, thread_id, response):
    endpoint = f"/drpc/{conn_id}/response"
    message = {"response": response, "thread_id": thread_id}
    print(f"Sending response to {conn_id}, message = {message}")

    send_generic_message(conn_id, endpoint, message)


def send_drpc_request(conn_id, request):
    endpoint = f"/drpc/{conn_id}/request"
    message = {
        "request": request,
    }
    send_generic_message(conn_id, endpoint, message)


def send_generic_message(conn_id, endpoint, message):
    base_url = os.environ.get("TRACTION_BASE_URL")
    url = urljoin(base_url, endpoint)

    token = fetch_bearer_token()

    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    logger.info(f"Sending message to {conn_id}, message = {endpoint}")

    response = requests.post(url, headers=headers, data=json.dumps(message))

    if response.status_code == 200:
        logger.info("Message sent successfully")
    else:
        logger.error(f"Error sending message: {response.status_code} {response.text}")


def offer_attestation_credential(offer):
    logger.info("issue_attestation_credential")

    base_url = os.environ.get("TRACTION_BASE_URL")
    endpoint = "/issue-credential/send-offer"
    url = urljoin(base_url, endpoint)

    token = fetch_bearer_token()

    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    logger.info(f"Sending offer to {offer['connection_id']}, offer = {offer}")

    response = requests.post(url, headers=headers, data=json.dumps(offer))

    if response.status_code == 200:
        logger.info("Offer sent successfully")
    else:
        logger.error(f"Error sending offer: {response.status_code}")
        logger.error(f"Text content for error: {response.text}")


def get_schema(schema_id):
    logger.info("get_schema")

    base_url = os.environ.get("TRACTION_BASE_URL")
    endpoint = "/schemas/created"
    url = urljoin(base_url, endpoint)

    token = fetch_bearer_token()

    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    response = requests.get(url, headers=headers, params={"schema_id": schema_id})

    if response.status_code == 200:
        logger.info("Schema queried successfully")
    else:
        logger.error(f"Error querying schema: {response.status_code}")
        logger.error(f"Text content for error: {response.text}")

    return response.json()


def get_cred_def(schema_id):
    logger.info("get_cred_def")

    base_url = os.environ.get("TRACTION_BASE_URL")
    endpoint = "/credential-definitions/created"
    url = urljoin(base_url, endpoint)

    token = fetch_bearer_token()

    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    response = requests.get(url, headers=headers, params={"schema_id": schema_id})

    if response.status_code == 200:
        logger.info("Cred def queried successfully")
    else:
        logger.error(f"Error querying cred def: {response.status_code}")
        logger.error(f"Text content for error: {response.text}")

    return response.json()


def create_schema(schema_name, schema_version, attributes):
    logger.info("create_schema")

    base_url = os.environ.get("TRACTION_BASE_URL")
    endpoint = "/schemas"
    url = urljoin(base_url, endpoint)

    token = fetch_bearer_token()

    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    schema = {
        "schema_name": schema_name,
        "schema_version": schema_version,
        "attributes": attributes,
    }

    response = requests.post(url, headers=headers, data=json.dumps(schema))

    if response.status_code == 200:
        logger.info("Schema created successfully")
    else:
        logger.error(f"Error creating schema: {response.status_code}")
        logger.error(f"Text content for error: {response.text}")

    return response.json()


def create_cred_def(schema_id, tag, revocation_registry_size=0):
    logger.info("create_cred_def")

    base_url = os.environ.get("TRACTION_BASE_URL")
    endpoint = "/credential-definitions"
    url = urljoin(base_url, endpoint)

    token = fetch_bearer_token()

    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    payload = {
        "schema_id": schema_id,
        "tag": tag,
        "support_revocation": revocation_registry_size > 0,
    }

    if revocation_registry_size > 0:
        payload["revocation_registry_size"] = revocation_registry_size

    # print(payload)
    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        logger.info("Request sent successfully")
        return response.json()
    else:
        logger.error(f"Error creating request: {response.status_code}")
        logger.error(f"Text content for error: {response.text}")

    return None


def create_presentation_request(presentation_data):
    logger.info("create_presentation_request")

    base_url = os.environ.get("TRACTION_BASE_URL")
    endpoint = "/present-proof-2.0/create-request"
    url = urljoin(base_url, endpoint)

    token = fetch_bearer_token()

    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    logger.info(f"Creating presentation request = {presentation_data}")

    response = requests.post(url, headers=headers, data=json.dumps(presentation_data))

    if response.status_code == 200:
        logger.info("Request creation successfully")
        return response.json()
    else:
        logger.error(f"Error creating request: {response.status_code}")
        logger.error(f"Text content for error: {response.text}")


def send_presentation_request(request):
    logger.info("send_presentation_request")

    base_url = os.environ.get("TRACTION_BASE_URL")
    endpoint = "/present-proof-2.0/send-request"
    url = urljoin(base_url, endpoint)

    token = fetch_bearer_token()

    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    logger.info(f"Sending presentation request = {request}")

    response = requests.post(url, headers=headers, data=json.dumps(request))

    if response.status_code == 200:
        logger.info("Request sent successfully")
        return response.json()
    else:
        logger.error(f"Error sending request: {response.status_code}")
        logger.error(f"Text content for error: {response.text}")
