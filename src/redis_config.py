import redis

redis_instance = redis.Redis(host='redis', port=6379, decode_responses=True)
