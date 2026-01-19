# Redis Cluster Helm Chart

This Helm chart deploys a Redis cluster to OpenShift for use with the Mobile Attestation VC Controller.

## Prerequisites

- Access to an OpenShift cluster with `oc` CLI configured
- Helm 3.x installed

## Deploy

Deploy to the selected namespace. Adjust the release name by replacing `shared` as appropriate.

### New Installation

Generate new credentials and set your namespace:

```console
export REDIS_USER=$(openssl rand -hex 16)
export REDIS_PASSWD=$(openssl rand -hex 16)
export NAMESPACE=$(oc project --short)
```

### Upgrade Existing Cluster

If you're upgrading an existing cluster, retrieve the current credentials to keep them:

```console
export NAMESPACE=$(oc project --short)
export REDIS_USER=$(oc get secret -n $NAMESPACE shared-redis-creds -o jsonpath='{.data.username}' | base64 -d)
export REDIS_PASSWD=$(oc get secret -n $NAMESPACE shared-redis-creds -o jsonpath='{.data.password}' | base64 -d)
```

### Install or Upgrade

Use `install` for a new deployment, or `upgrade` for an existing one:

```console
helm install shared devops/charts/redis \
  -f devops/charts/redis/values.yaml \
  --set-string password=$REDIS_PASSWD \
  --set-string username=$REDIS_USER \
  --set-string namespace=$NAMESPACE
```

You should see output similar to:

```console
networkpolicy.networking.k8s.io/shared-redis-cluster created
secret/shared-redis-creds created
configmap/shared-redis created
service/shared-redis-headless created
statefulset.apps/shared-redis created
```

### Verify Pods

Check that all Redis pods are running:

```console
oc get pods -l "app.kubernetes.io/component=redis"
```

Expected output:

```console
NAME             READY   STATUS    RESTARTS   AGE
shared-redis-0   1/1     Running   0          5m55s
shared-redis-1   1/1     Running   0          5m11s
shared-redis-2   1/1     Running   0          4m28s
shared-redis-3   1/1     Running   0          3m6s
shared-redis-4   1/1     Running   0          2m30s
shared-redis-5   1/1     Running   0          112s
```

## Create the Cluster

> **Note:** This only needs to be done once after the initial deployment.

### Node Configuration

A Redis cluster requires at least 6 nodes for high availability with automatic failover:

- **3 Master Nodes** - Each handles a subset of hash slots
- **3 Replica Nodes** - Each master has one replica for redundancy

The `--cluster-replicas 1` parameter specifies one replica per master node.

### Initialize the Cluster

```console
oc exec -n $NAMESPACE -it shared-redis-0 -- redis-cli \
  --user $REDIS_USER \
  -a $REDIS_PASSWD \
  --cluster create \
  --cluster-replicas 1 \
  $(oc get pods -n $NAMESPACE -l "app.kubernetes.io/component=redis" -o jsonpath='{range.items[*]}{.status.podIP}:6379 {end}')
```

When prompted, type `yes` to accept the configuration.

## Verify Cluster Status

### Check Cluster Nodes

```console
oc exec -n $NAMESPACE -it shared-redis-0 -- redis-cli \
  --user $REDIS_USER \
  -c CLUSTER NODES
```

### Check Cluster Health

```console
oc exec -n $NAMESPACE -it shared-redis-0 -- redis-cli \
  --user $REDIS_USER \
  -c CLUSTER INFO
```

You should see `cluster_state:ok` in the output.
