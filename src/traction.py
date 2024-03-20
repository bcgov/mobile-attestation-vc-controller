import requests
import json
import os
from urllib.parse import urljoin
from dotenv import load_dotenv
import logging

if os.getenv("FLASK_ENV") == "development":
    load_dotenv()

bearer_token = None
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_bearer_token():
    global bearer_token

    if bearer_token:
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
        return bearer_token
    else:
        logger.info(f"Error fetcing token: {response.status_code}")


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
        logger.info("Conneciton fetched successfully")
        return json.loads(response.text)
    else:
        logger.info(f"Error fetcing conneciton message: {response.status_code}")

    return None

def send_drpc_response(conn_id, thread_id, response):
    endpoint = f"/drpc/{conn_id}/response"
    message = {
        "response": response,
        "thread_id": thread_id
    }
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
        logger.info(f"Error sending message: {response.status_code} {response.text}")


def send_message(conn_id, content):
    base_url = os.environ.get("TRACTION_BASE_URL")
    endpoint = f"/connections/{conn_id}/send-message"
    url = urljoin(base_url, endpoint)

    token = fetch_bearer_token()

    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    data = {"content": content}

    logger.info(f"Sending message to {conn_id}, message = {content}")

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        logger.info("Message sent successfully")
    else:
        logger.info(f"Error sending message: {response.status_code}")


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
        logger.info(f"Error sending offer: {response.status_code}")


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
        logger.info(f"Error quering schema: {response.status_code}")

    return response.json()


def get_cred_def(schema_id):
    logger.info("get_schema")

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
        logger.info("Schema queried successfully")
    else:
        logger.info(f"Error quering schema: {response.status_code}")

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
        logger.info(f"Error creating schema: {response.status_code}")

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
        logger.info(f"Error creating request: {response.status_code}")

    return None
