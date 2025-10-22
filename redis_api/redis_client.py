import redis
import os
from dotenv import load_dotenv

load_dotenv()

redis_client = redis.Redis(
    host='redis-10435.c311.eu-central-1-1.ec2.redns.redis-cloud.com',
    port=10435,
    decode_responses=True,
    username="default",
    password=os.getenv('REDIS_PASS')
)

def get_redis():
    return redis_client