import logging
import os
import random

from redis.cluster import RedisCluster

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the Redis URL from environment variables
redis_uri = os.getenv("REDIS_URI")
logger.info(f"Connecting to redis at {redis_uri}")

redis_instance = RedisCluster.from_url(redis_uri, decode_responses=True)

auto_expire_nonce = 60 * 10

redis_instance.setex(f"{random.randint(0, 1000000)}", auto_expire_nonce, random.randint(0, 1000000))
logger.info("Redis setex smoke test succeeded")
