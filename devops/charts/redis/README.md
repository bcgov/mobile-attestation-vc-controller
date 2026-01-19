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

You should see output similar to:

```console
>>> Performing hash slots allocation on 6 nodes...
Master[0] -> Slots 0 - 5460
Master[1] -> Slots 5461 - 10922
Master[2] -> Slots 10923 - 16383
Adding replica 10.97.108.183:6379 to 10.97.179.175:6379
Adding replica 10.97.170.247:6379 to 10.97.181.42:6379
Adding replica 10.97.176.209:6379 to 10.97.144.215:6379
M: 5b24aca2206372f42a372f1c55a6957cd8591f34 10.97.179.175:6379
   slots:[0-5460] (5461 slots) master
M: f7aed2b23c011533806280692870eacbca23391d 10.97.181.42:6379
   slots:[5461-10922] (5462 slots) master
M: 53894e46058104489254719a819d8e1c871aa8ea 10.97.144.215:6379
   slots:[10923-16383] (5461 slots) master
S: 9c63539ae8a31fc03860caea0c6bc4a370221ad7 10.97.176.209:6379
   replicates 53894e46058104489254719a819d8e1c871aa8ea
S: 787338c9558f666c32ac45f84af5e23cec26fb0b 10.97.108.183:6379
   replicates 5b24aca2206372f42a372f1c55a6957cd8591f34
S: 338d7065d323fb2b27bb59d8f77b4764cbf0d92b 10.97.170.247:6379
   replicates f7aed2b23c011533806280692870eacbca23391d
Can I set the above configuration? (type 'yes' to accept): yes
>>> Nodes configuration updated
>>> Assign a different config epoch to each node
>>> Sending CLUSTER MEET messages to join the cluster
Waiting for the cluster to join
.
>>> Performing Cluster Check (using node 10.97.179.175:6379)
M: 5b24aca2206372f42a372f1c55a6957cd8591f34 10.97.179.175:6379
   slots:[0-5460] (5461 slots) master
   1 additional replica(s)
M: 53894e46058104489254719a819d8e1c871aa8ea 10.97.144.215:6379
   slots:[10923-16383] (5461 slots) master
   1 additional replica(s)
M: f7aed2b23c011533806280692870eacbca23391d 10.97.181.42:6379
   slots:[5461-10922] (5462 slots) master
   1 additional replica(s)
S: 338d7065d323fb2b27bb59d8f77b4764cbf0d92b 10.97.170.247:6379
   slots: (0 slots) slave
S: 9c63539ae8a31fc03860caea0c6bc4a370221ad7 10.97.176.209:6379
   slots: (0 slots) slave
S: 787338c9558f666c32ac45f84af5e23cec26fb0b 10.97.108.183:6379
   slots: (0 slots) slave
[OK] All nodes agree about slots configuration.
>>> Check for open slots...
>>> Check slots coverage...
[OK] All 16384 slots covered.
```

**What to look for:**

- 3 master nodes (`M:`) each with a range of hash slots
- 3 slave/replica nodes (`S:`) each replicating a master
- `[OK] All nodes agree about slots configuration`
- `[OK] All 16384 slots covered`

## Verify Cluster Status

### Check Cluster Nodes

```console
oc exec -n $NAMESPACE -it shared-redis-0 -- redis-cli \
  --user $REDIS_USER \
  -c CLUSTER NODES
```

Expected output shows 3 masters and 3 slaves with their slot assignments:

```console
338d7065d323fb2b27bb59d8f77b4764cbf0d92b 10.97.170.247:6379@16379 slave f7aed2b23c011533806280692870eacbca23391d 0 1716930293077 2 connected
53894e46058104489254719a819d8e1c871aa8ea 10.97.144.215:6379@16379 master - 0 1716930292074 3 connected 10923-16383
9c63539ae8a31fc03860caea0c6bc4a370221ad7 10.97.176.209:6379@16379 slave 53894e46058104489254719a819d8e1c871aa8ea 0 1716930294082 3 connected
787338c9558f666c32ac45f84af5e23cec26fb0b 10.97.108.183:6379@16379 slave 5b24aca2206372f42a372f1c55a6957cd8591f34 0 1716930291000 1 connected
5b24aca2206372f42a372f1c55a6957cd8591f34 10.97.179.175:6379@16379 myself,master - 0 1716930291000 1 connected 0-5460
f7aed2b23c011533806280692870eacbca23391d 10.97.181.42:6379@16379 master - 0 1716930292000 2 connected 5461-10922
```

### Check Cluster Health

```console
oc exec -n $NAMESPACE -it shared-redis-0 -- redis-cli \
  --user $REDIS_USER \
  -c CLUSTER INFO
```

Expected output for a healthy cluster:

```console
cluster_state:ok
cluster_slots_assigned:16384
cluster_slots_ok:16384
cluster_slots_pfail:0
cluster_slots_fail:0
cluster_known_nodes:6
cluster_size:3
```

**Key indicators of a healthy cluster:**

- `cluster_state:ok` - The cluster is operating normally
- `cluster_slots_assigned:16384` - All hash slots are assigned
- `cluster_slots_ok:16384` - All hash slots are reachable
- `cluster_slots_pfail:0` and `cluster_slots_fail:0` - No failing slots
- `cluster_known_nodes:6` - All 6 nodes are visible
- `cluster_size:3` - 3 master nodes handling data
