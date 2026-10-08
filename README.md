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
- Python 3.12 (see `.python-version`)
- Traction >= 0.3.2
- Suitable tool for exposing localhost to the internet:
  1. [Cloudflared](https://github.com/cloudflare/cloudflared)
  2. [ngrok](https://ngrok.com/download)
  3. [localtunnel](https://www.npmjs.com/package/localtunnel)

## How it Works

When run, this program will act as a "controller" to an ACA-py agent. It uses Flux to handle DidComm basic messages, and, when prompted, will use Traction to issue a basic demo Attestation Credential.

## Running

### Running Locally

The controller needs three things: a Redis cluster for nonces, a Traction tenant to
issue through, and a public URL Traction can post webhooks to. A
[Traction Sandbox](https://traction-sandbox-tenant-ui.apps.silver.devops.gov.bc.ca)
tenant is the easiest way to get the second.

**Step 1 — Redis.** The app's client is a `RedisCluster`, so a plain Redis won't do:

```bash
docker compose -f docker-compose.local.yml up -d
```

That starts one cluster-enabled node owning all 16384 slots, reachable at
`127.0.0.1:6379`. Check it came up with
`docker compose -f docker-compose.local.yml exec redis redis-cli cluster info` —
you want `cluster_state:ok`.

**Step 2 — `.env`.** Copy `src/.env.sample` to `src/.env` and fill it in. From your
Sandbox tenant's UI, the tenant ID and API key are under **Settings → Tenant Profile**,
and the public DID is on the same page.

```bash
TRACTION_BASE_URL="https://traction-sandbox-tenant-proxy.apps.silver.devops.gov.bc.ca"
TRACTION_TENANT_ID="<your tenant id>"
TRACTION_TENANT_API_KEY="<your api key>"
TRACTION_LEGACY_DID="<your tenant's public DID>"
REDIS_URI="redis://127.0.0.1:6379/0"
MESSAGE_TEMPLATES_PATH="fixtures/"
APPLE_ATTESTATION_ROOT_CA_URL="https://www.apple.com/certificateauthority/Apple_App_Attestation_Root_CA.pem"
GOOGLE_AUTH_JSON_PATH="google_oauth_key.json"
ALLOW_TEST_BUILDS="true"
```

**Step 3 — schema and cred def.** Your tenant has neither, and the controller refuses
to issue (error 32604) unless a cred def whose issuer DID matches `TRACTION_LEGACY_DID`
is configured. Create them, then point the controller at the result:

```bash
python scripts/schema.py
python scripts/cred_def.py      # prints the new cred def ID
```

Add the printed ID to your `.env`:

```bash
ATTESTATION_CRED_DEF_IDS="<the cred def ID just created>"
```

**Step 4 — run it.**

```bash
source .venv/bin/activate
python src/controller.py         # serves on 5501
```

`curl -i localhost:5501/topic/ping/` should return 204.

**Step 5 — expose it.** Traction pushes webhooks, so it needs to reach you:

```bash
npx ngrok http 5501
```

Put the public URL in Traction under **Settings → Tenant Profile → WebHook URL**.
Note the port: the app listens on 5501, though gunicorn serves 5000 in the container.

Attestation itself can't be exercised from a simulator — App Attest and Play Integrity
both need real hardware, and Play Integrity additionally needs the app's package to
resolve a Google Cloud project. Point a device build at your tunnel instead.

#### Alternative: Devcontainer

`.devcontainer/` has its own three-node Redis cluster and a Python 3.12 workspace. Open
the folder in VSCode and choose **Reopen in Container**. Redis is reached by container
hostname there (`REDIS_URI=redis://redis-1:6379/0`, already set), and the cluster needs
creating once per rebuild:

```bash
redis-cli --cluster create redis-1:6379 redis-2:6379 redis-3:6379 --cluster-replicas 0
```

Everything else is the same. Use this if you want the three-node topology; the host
route above is faster to iterate on.

### Working on the Code

The project targets the Python version in `.python-version`. If you use [mise](https://mise.jdx.dev), `mise install` picks it up. Check with `python3 --version`

```bash
python3 -m venv .venv
```

Then activate it in each new shell

```bash
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

To leave it:

```bash
deactivate
```

Day to day:

```bash
ruff check src scripts tests            # lint
ruff format src scripts tests           # apply formatting (--check to only report)
pytest                                  # unit tests
```

CI runs exactly these three and will not build the image unless all pass, so running
them before pushing saves a round trip.

#### Adding or Changing a Dependency

```bash
pip-compile --generate-hashes requirements.in
pip-compile --generate-hashes --allow-unsafe requirements-dev.in
pip install -r requirements.txt -r requirements-dev.txt
```

CI installs with `--require-hashes`, so a package added to an `.in` file without
recompiling fails the build rather than being silently ignored.

### Configuration

Beyond the values in `.env.sample`, two settings govern which apps this deployment
serves. Both are set per environment in `devops/charts/controller/values_*.yaml`.

| Variable                       | Purpose                                                                                                         |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| `ALLOWED_APPLE_APP_IDS`        | Comma-separated `<AppleTeamID>.<bundle id>` values accepted for App Attest.                                     |
| `ALLOWED_GOOGLE_PACKAGE_NAMES` | Comma-separated Android package names accepted for Play Integrity.                                              |
| `DEFAULT_CREDENTIAL_PROTOCOL`  | `v1` (issue-credential/1.0) or `v2` (issue-credential/2.0 + anoncreds), used when a client doesn't request one. |
| `ATTESTATION_CRED_DEF_IDS`     | Comma-separated cred defs this deployment may issue; the one whose issuer DID matches `TRACTION_LEGACY_DID` is used. |
| `ALLOW_TEST_BUILDS`            | When `true`, accepts Play Integrity verdicts other than `PLAY_RECOGNIZED`, so non-Play builds can attest.       |

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
