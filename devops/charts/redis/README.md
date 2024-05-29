

### Deploy

Deploy to the selected namespae. Some commands assume you're already in the given namespace. Adjust the name your cluster by replacing `shared` appropriatly.

```console
export REDIS_USER=$(openssl rand -hex 16)
export REDIS_PASSWD=$(openssl rand -hex 16)
export NAMESPACE=$(oc project --short)
```

```console
export NAMESPACE=$(oc project --short)
export REDIS_USER=$(oc get secret -n $NAMESPACE shared-redis-creds -o jsonpath='{.data.username}' | base64 -d)
export REDIS_PASSWD=$(oc get secret -n $NAMESPACE shared-redis-creds -o jsonpath='{.data.password}' | base64 -d)
```



```console
helm template shared devops/charts/redis -f devops/charts/redis/values.yaml --set-string password=$REDIS_PASSWD --set-string username=$REDIS_USER --set-string namespace=$NAMESPACE | oc apply -n $NAMESPACE -f -
```

You should see the following output:

```console
networkpolicy.networking.k8s.io/shared-redis-cluster created
secret/shared-redis-creds created
configmap/shared-redis created
service/shared-redis-headless created
statefulset.apps/shared-redis created
```

Check all redis pods are running with the command

```console
oc get pods -l "app.kubernetes.io/component=redis"
```

You should see output similar to the following:

```console
NAME             READY   STATUS    RESTARTS   AGE
shared-redis-0   1/1     Running   0          5m55s
shared-redis-1   1/1     Running   0          5m11s
shared-redis-2   1/1     Running   0          4m28s
shared-redis-3   1/1     Running   0          3m6s
shared-redis-4   1/1     Running   0          2m30s
shared-redis-5   1/1     Running   0          112s
```

If you are re-deploying or updating the cluster, you will want to keep the same password and username.


### Create a Cluster

This only needs to be done one time following the initial deployment of the redis cluster. Adjust the name your cluster by replacing `shared` appropriatly.

The number of nodes and the distribution of master and replica nodes in a Redis cluster depend on various factors such as the desired level of availability, redundancy, and performance requirements. Here are some guidelines to help you decide:

**Basic Configuration:***
Minimum Nodes: A Redis cluster requires at least 6 nodes to ensure high availability with automatic failover.
3 Master Nodes: Each master node will handle a subset of the data (hash slots).
3 Replica Nodes: Each master node will have one replica for redundancy.
Considerations for Node Configuration:
High Availability: Ensure that each master has at least one replica. This setup provides redundancy and allows for automatic failover if a master node fails.
Data Distribution: Redis clusters distribute data across master nodes using hash slots. More master nodes mean more granular data distribution.
Read Scalability: If read operations are high, having multiple replicas can help distribute the read load.
Fault Tolerance: More replicas increase fault tolerance. If you have a higher tolerance for failures, you can configure more replicas per master.

Basic High Availability:

6 Nodes Total: 3 Masters and 3 Replicas.
Each master has one replica.

The paremeter `--cluster-replicas 1` is the number of replicas for each master node. Adjust the name your cluster by replacing `shared` appropriatly.

```console
oc exec -n $NAMESPACE -it shared-redis-0 -- redis-cli --user $REDIS_USER -a $REDIS_PASSWD --cluster create --cluster-replicas 1 $(oc get pods -n $NAMESPACE -l "app.kubernetes.io/component=redis" -o jsonpath='{range.items[*]}{.status.podIP}:6379 {end}')
```

You should see the following output:

```console
Warning: Using a password with '-a' or '-u' option on the command line interface may not be safe.
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
S: 338d7065d323fb2b27bb59d8f77b4764cbf0d92b 10.97.170.247:6379
   slots: (0 slots) slave
   replicates f7aed2b23c011533806280692870eacbca23391d
M: 53894e46058104489254719a819d8e1c871aa8ea 10.97.144.215:6379
   slots:[10923-16383] (5461 slots) master
   1 additional replica(s)
S: 9c63539ae8a31fc03860caea0c6bc4a370221ad7 10.97.176.209:6379
   slots: (0 slots) slave
   replicates 53894e46058104489254719a819d8e1c871aa8ea
S: 787338c9558f666c32ac45f84af5e23cec26fb0b 10.97.108.183:6379
   slots: (0 slots) slave
   replicates 5b24aca2206372f42a372f1c55a6957cd8591f34
M: f7aed2b23c011533806280692870eacbca23391d 10.97.181.42:6379
   slots:[5461-10922] (5462 slots) master
   1 additional replica(s)
[OK] All nodes agree about slots configuration.
>>> Check for open slots...
>>> Check slots coverage...
```

### Status

Check the status of the current cluster. This will show the number of nodes and the number of replicas. The parameter `-i` is any node in the cluster. Adjust the name your cluster by replacing `shared` appropriatly.


Check you have the expected number of nodes as described in values.yaml `replicas`.

```console
oc exec -n $(oc project --short) -i shared-redis-0 -- redis-cli --user $REDIS_USER -c CLUSTER NODES
```

You should see output similar to the following:

```console
338d7065d323fb2b27bb59d8f77b4764cbf0d92b 10.97.170.247:6379@16379 slave f7aed2b23c011533806280692870eacbca23391d 0 1716930293077 2 connected
53894e46058104489254719a819d8e1c871aa8ea 10.97.144.215:6379@16379 master - 0 1716930292074 3 connected 10923-16383
9c63539ae8a31fc03860caea0c6bc4a370221ad7 10.97.176.209:6379@16379 slave 53894e46058104489254719a819d8e1c871aa8ea 0 1716930294082 3 connected
787338c9558f666c32ac45f84af5e23cec26fb0b 10.97.108.183:6379@16379 slave 5b24aca2206372f42a372f1c55a6957cd8591f34 0 1716930291000 1 connected
5b24aca2206372f42a372f1c55a6957cd8591f34 10.97.179.175:6379@16379 myself,master - 0 1716930291000 1 connected 0-5460
f7aed2b23c011533806280692870eacbca23391d 10.97.181.42:6379@16379 master - 0 1716930292000 2 connected 5461-10922
```



Confirm the cluster is healthy.

```console
oc exec -n $(oc project --short) -i shared-redis-0 -- redis-cli --user $(oc get secret -n $(oc project --short) shared-redis-creds -o jsonpath='{.data.username}' | base64 -d) -c CLUSTER INFO
```

You should see output similar to the following:

```console
cluster_state:ok
cluster_slots_assigned:16384
cluster_slots_ok:16384
cluster_slots_pfail:0
cluster_slots_fail:0
cluster_known_nodes:6
cluster_size:3
cluster_current_epoch:6
cluster_my_epoch:1
cluster_stats_messages_ping_sent:109
cluster_stats_messages_pong_sent:107
cluster_stats_messages_sent:216
cluster_stats_messages_ping_received:102
cluster_stats_messages_pong_received:109
cluster_stats_messages_meet_received:5
cluster_stats_messages_received:216
total_cluster_links_buffer_limit_exceeded:0
```