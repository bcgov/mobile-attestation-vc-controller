import json
import os
import sys

sys.path.insert(0, "./src")

from traction import create_presentation_request, send_presentation_request

# Set this to the id of the connection you want to send the proof to
connection_id = "3ecb6447-fc2a-4291-8079-************"

# You may need to adjust the `request_attest_verif.json` data to better match the
# schema and/or cred_def_id you would like to use in your proof.

with open(os.path.join("./fixtures/", "request_attest_verif.json"), "r") as f:
    proof_request = json.load(f)

# Step 1: Create a presentation request
create_presentation_response = create_presentation_request(proof_request)

# print(json.dumps(create_presentation_response, indent=2))

payload = {
    "connection_id": connection_id,
    "presentation_request": {
        **create_presentation_response["by_format"]["pres_request"],
    },
}

# print(json.dumps(payload, indent=2))

# Step 2: Send the presentation request
send_presentation_response = send_presentation_request(payload)

# print(json.dumps(send_presentation_response, indent=2))

# If the response is successful, you should see a state of "request_sent"
print(f"Send presentation status = {send_presentation_response['state']}")
