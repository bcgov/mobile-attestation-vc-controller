import os

from redis.cluster import RedisCluster

# Get the Redis URL from environment variables
redis_uri = os.getenv("REDIS_URI")

redis_instance = RedisCluster.from_url(redis_uri, decode_responses=True)
