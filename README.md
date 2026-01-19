# Mobile Attestation VC Controller

This is a Proof of Concept (PoC) of an ACA-py controller for mobile application attestation. It verifies that requests come from legitimate mobile apps running on genuine devices.

## Features

- [x] Apple App Attestation
- [x] Android Play Integrity API
- [ ] Apple Fraud Detection API
- [ ] AppStore Receipt Checking (iOS <14.0)

# Getting Started

While this controller can be run as a controller for any ACA-py instance, it was developed using "Traction" as the front end. Any documentation or references should be considered in that context.

## Prerequisites

- VSCode
- [Docker](https://docs.docker.com/get-docker/)
- Traction >= 0.3.2
- Suitable tool for exposing localhost to the internet:
  1. [Cloudflared](https://github.com/cloudflare/cloudflared)
  2. [ngrok](https://ngrok.com/download)
  3. [localtunnel](https://www.npmjs.com/package/localtunnel)

## How it Works

When run, this program will act as a "controller" to an ACA-py agent. It uses Flux to handle DidComm basic messages, and, when prompted, will use Traction to issue a basic demo Attestation Credential.

## Running

### Local Development

Follow these steps to get the controller running locally:

**Step 1:** Create a `.env` file in the root of your project by copying `env.sample` to `.env`, then fill in your own values.

> **Note:** For Android Attestation, you'll also need a Google OAuth JSON key file in `/src` configured for your app.

**Step 2:** Create a schema and credential definition ID in your Traction instance, then add it to `fixtures/offer.json` following the existing format.

**Step 3:** Start the dev container. This repo includes a `.devcontainer` configuration to help you get up and running quickly. Open the project in VS Code and use the "Reopen in Container" command.

**Step 4:** Once the container is running, initialize the Redis cluster. You can access the `redis-1` container via Docker Desktop and run:

```bash
redis-cli --cluster create redis-1:6379 redis-2:6379 redis-3:6379 --cluster-replicas 0
```

**Step 5:** Start the controller:

```bash
python src/controller.py
```

The output should look something like this:

```bash
vscode ➜ /work (main) $ python src/controller.py
 * Serving Flask app 'controller'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 107-923-082
```

**Step 6:** Expose the local server to the internet. Flask runs on port `5000`, and you'll need to make it publicly accessible. For example, using ngrok:

```bash
npx ngrok http 5000
```

**Step 7:** Configure Traction to use your public URL. Copy the public endpoint from ngrok (or your chosen tunneling tool) and add it to Traction by going to **Settings → Tenant Profile** and entering the URL in the **WebHook URL** field.

### OpenShift Cluster

For deploying to OpenShift, this project includes two Helm charts:

1. **[Redis Chart](devops/charts/redis/README.md)** - Deploy the Redis cluster first
2. **[Controller Chart](devops/charts/controller/README.md)** - Deploy the attestation controller

Each chart's README contains detailed instructions for installation, upgrade, and configuration.

#### Quick Start

```bash
# Set your namespace
export NAMESPACE=$(oc project --short)

# Deploy the controller
helm install bcwallet-attestation-controller devops/charts/controller \
  -f ./devops/charts/controller/values_dev.yaml \
  --set-string tenant_id=$TRACTION_TENANT_ID \
  --set-string tenant_api_key=$TRACTION_TENANT_API_KEY \
  --set-string traction_legacy_did=$TRACTION_LEGACY_DID \
  --set-string namespace=$NAMESPACE \
  --set-file google_oauth_key.json=google_oauth_key.json
```

See the [Controller Chart README](devops/charts/controller/README.md) for complete setup instructions, including how to retrieve credentials from an existing deployment.

---

# Reference

## Android Device Integrity

For more details on Android device integrity verdicts, see the [Play Integrity API documentation](https://developer.android.com/google/play/integrity/verdicts#device-integrity-field). This helps you distinguish between `MEETS_BASIC_INTEGRITY` and `MEETS_STRONG_INTEGRITY`.

## Useful Packages

These packages may be helpful when integrating attestation into your mobile app:

### React Native Firebase App Check

- [GitHub](https://github.com/invertase/react-native-firebase/tree/main#readme)
- [npm](https://www.npmjs.com/package/@react-native-firebase/app-check)

```bash
npm install @react-native-firebase/app-check
```

### React Native Google Play Integrity

- [GitHub](https://github.com/kedros-as/react-native-google-play-integrity)
- [npm](https://www.npmjs.com/package/react-native-google-play-integrity)

```bash
npm install react-native-google-play-integrity
```

### Expo Attestation

- [GitHub](https://github.com/bpofficial/expo-attestation#readme)
- [npm](https://www.npmjs.com/package/expo-attestation)

```bash
npm install expo-attestation
```

## Handy Test Commands

These commands are useful for testing the controller locally:

**Create a basic message with encoded content:**

```bash
jq --arg content "$(cat fixtures/request_issuance.json | base64)" --arg name "jason" '.content |= $content | .name |= $name' fixtures/basic_message.json
```

**Send a test request to the controller:**

```bash
jq --arg content "$(cat fixtures/request_issuance.json | base64)" '.content |= $content' fixtures/basic_message.json | curl -v -X POST -H "Content-Type: application/json" -d @- http://localhost:5000/topic/basicmessages/
```

**Merge two JSON files:**

```bash
jq -s '.[0] * .[1]' source.json target.json
```

**Send a challenge response:**

```bash
jq --arg content "$(jq -s '.[0] * .[1]' fixtures/chalange_response.json attestation.json | base64)" '.content |= $content' fixtures/basic_message.json | curl -v -X POST -H "Content-Type: application/json" -d @- http://localhost:5000/topic/basicmessages/
```

## Apple Verification Steps

The controller performs the following verification steps for Apple App Attestation (all currently implemented):

- [x] Use the decoded object, along with the key identifier that your app sends, to perform the following steps

- [x] Verify that the x5c array contains the intermediate and leaf certificates for App Attest, starting from the credential certificate in the first data buffer in the array (credcert). Verify the validity of the certificates using Apple’s App Attest root certificate.

- [x] Create clientDataHash as the SHA256 hash of the one-time challenge your server sends to your app before performing the attestation, and append that hash to the end of the authenticator data (authData from the decoded object).

- [x] Generate a new SHA256 hash of the composite item to create nonce.

- [x] Obtain the value of the credCert extension with OID 1.2.840.113635.100.8.2, which is a DER-encoded ASN.1 sequence. Decode the sequence and extract the single octet string that it contains. Verify that the string equals nonce.

- [x] Create the SHA256 hash of the public key in credCert, and verify that it matches the key identifier from your app.

- [x] Compute the SHA256 hash of your app’s App ID, and verify that it’s the same as the authenticator data’s RP ID hash.

- [x] Verify that the authenticator data’s counter field equals 0.

- [x] Verify that the authenticator data’s aaguid field is either appattestdevelop if operating in the development environment, or appattest followed by seven 0x00 bytes if operating in the production environment.

- [x] Verify that the authenticator data’s credentialId field is the same as the key identifier.

After successfully completing these steps, you can trust the attestation object.

## Android Verification Steps

The controller performs the following verification steps for Android Play Integrity (all currently implemented):

- [x] Get Integrity Verdict from Google's server via their python client
- [x] Verify the package info matches our app
- [x] Verify the device integrity fields
- [x] Verify the app integrity fields
- [x] Verify the nonce in the verdict payload matches the nonce the controller sent to the device
