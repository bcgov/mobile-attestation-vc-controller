import requests
import json
import os
from urllib.parse import urljoin
from dotenv import load_dotenv

if os.getenv("FLASK_ENV") == "development":
    load_dotenv()

bearer_token = None


def fetch_bearer_token():
    global bearer_token

    if bearer_token:
        return bearer_token

    base_url = os.environ.get("TRACTION_BASE_URL")
    wallet_id = os.environ.get("TRACTION_WALLET_ID")
    wallet_key = os.environ.get("TRACTION_WALLET_KEY")
    endpoint = f"multitenancy/wallet/{wallet_id}/token"
    url = urljoin(base_url, endpoint)
    headers = {"Content-Type": "application/json", "accept": "application/json"}
    data = {"wallet_key": wallet_key}

    print(f"Requesting bearer token for walletId {wallet_id}")

    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        print("Token fetched successfully")
        response_data = json.loads(response.text)

        bearer_token = response_data["token"]
        return bearer_token
    else:
        print(f"Error fetcing token: {response.status_code}")


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

    print(f"Fetching connection {conn_id}")

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print("Conneciton fetched successfully")
        return json.loads(response.text)
    else:
        print(f"Error fetcing conneciton message: {response.status_code}")

    return None


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

    print(f"Sending message to {conn_id}, message = {content}")

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        print("Message sent successfully")
    else:
        print(f"Error sending message: {response.status_code}")


def offer_attestation_credential(conn_id):
    print("issue_attestation_credential")

    base_url = os.environ.get("TRACTION_BASE_URL")
    endpoint = "/issue-credential/send-offer"
    url = urljoin(base_url, endpoint)

    token = fetch_bearer_token()

    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    message_templates_path = os.getenv("MESSAGE_TEMPLATES_PATH")
    with open(os.path.join(message_templates_path, "offer.json"), "r") as f:
        offer = json.load(f)

    offer["connection_id"] = conn_id

    print(f"Sending offer to {conn_id}, offer = {offer}")

    response = requests.post(url, headers=headers, data=json.dumps(offer))

    if response.status_code == 200:
        print("Offer sent successfully")
    else:
        print(f"Error sending offer: {response.status_code}")


def get_schema(schema_id):
    print("get_schema")

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
        print("Schema queried successfully")
    else:
        print(f"Error quering schema: {response.status_code}")

    return response.json()


def create_schema(schema_name, schema_version, attributes):
    print("create_schema")

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
        print("Schema created successfully")
    else:
        print(f"Error creating schema: {response.status_code}")

    return response.json()
