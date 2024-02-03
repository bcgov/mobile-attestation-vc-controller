# import redis
import os
from rediscluster import RedisCluster

# Get the Redis URL from environment variables
redis_uri = os.getenv("REDIS_URI")

# redis_instance = redis.from_url(redis_url, decode_responses=True)
redis_instance = RedisCluster.from_url(redis_uri, decode_responses=True)
