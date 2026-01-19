# Controller Helm Chart

This Helm chart deploys the Mobile Attestation VC Controller to an OpenShift cluster.

## Prerequisites

Before deploying the controller, ensure you have:

- Access to an OpenShift cluster with `oc` CLI configured
- Helm 3.x installed
- A Traction tenant with:
  - Tenant ID
  - Tenant API Key
  - Legacy DID
- A Google OAuth JSON key file (for Android attestation)
- Redis cluster deployed (see [Redis chart](../redis/README.md))

## Environment Setup

First, set your namespace:

```console
export NAMESPACE=$(oc project --short)
```

### New Deployment

If this is a fresh deployment, you'll need to obtain credentials from your Traction tenant and set them as environment variables:

```console
export TRACTION_TENANT_ID=<your-tenant-id>
export TRACTION_TENANT_API_KEY=<your-api-key>
export TRACTION_LEGACY_DID=<your-legacy-did>
```

### Existing Deployment

If you're updating a namespace that already has a controller deployed, you can retrieve the existing credentials:

```console
export TRACTION_LEGACY_DID=$(oc get secret/bcwallet-attestation-controller-traction-creds -o json -n $NAMESPACE | jq -r ".data.TRACTION_LEGACY_DID" | base64 -d)
```

```console
export TRACTION_TENANT_ID=$(oc get secret/bcwallet-attestation-controller-traction-creds -o json -n $NAMESPACE | jq -r ".data.TRACTION_TENANT_ID" | base64 -d)
```

```console
export TRACTION_TENANT_API_KEY=$(oc get secret/bcwallet-attestation-controller-traction-creds -o json -n $NAMESPACE | jq -r ".data.TRACTION_TENANT_API_KEY" | base64 -d)
```

## Installation

Install the chart with a release name of your choice. The release name must be unique within the namespace.

```console
helm install <RELEASE> devops/charts/controller \
  -f ./devops/charts/controller/values_<ENVIRONMENT>.yaml \
  --set-string tenant_id=$TRACTION_TENANT_ID \
  --set-string tenant_api_key=$TRACTION_TENANT_API_KEY \
  --set-string traction_legacy_did=$TRACTION_LEGACY_DID \
  --set-string namespace=$NAMESPACE \
  --set-file google_oauth_key.json=./google_oauth_key.json
```

### Example: Deploy to Dev

```console
helm install bcwallet-attestation-controller devops/charts/controller \
  -f ./devops/charts/controller/values_dev.yaml \
  --set-string tenant_id=$TRACTION_TENANT_ID \
  --set-string tenant_api_key=$TRACTION_TENANT_API_KEY \
  --set-string traction_legacy_did=$TRACTION_LEGACY_DID \
  --set-string namespace=$NAMESPACE \
  --set-file google_oauth_key.json=./google_oauth_key.json
```

## Upgrade

To update an existing release with new configuration or image:

```console
helm upgrade bcwallet-attestation-controller devops/charts/controller \
  -f ./devops/charts/controller/values_dev.yaml \
  --set-string tenant_id=$TRACTION_TENANT_ID \
  --set-string tenant_api_key=$TRACTION_TENANT_API_KEY \
  --set-string traction_legacy_did=$TRACTION_LEGACY_DID \
  --set-string namespace=$NAMESPACE \
  --set-file google_oauth_key.json=./google_oauth_key.json
```

## Uninstall

To remove the controller:

```console
helm uninstall bcwallet-attestation-controller
```

## Configuration

| Parameter               | Description                        | Required |
| ----------------------- | ---------------------------------- | -------- |
| `tenant_id`             | Traction tenant ID                 | Yes      |
| `tenant_api_key`        | Traction tenant API key            | Yes      |
| `traction_legacy_did`   | Traction legacy DID                | Yes      |
| `namespace`             | OpenShift namespace                | Yes      |
| `google_oauth_key.json` | Path to Google OAuth JSON key file | Yes      |

## Values Files

- `values_dev.yaml` - Development environment
- `values_test.yaml` - Test environment
- `values_prod.yaml` - Production environment
