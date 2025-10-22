"""
Basic connection example.
"""

import redis
import os
from dotenv import load_dotenv
load_dotenv()

REDIS_PASS = os.getenv('REDIS_PASS')

r = redis.Redis(
    host='redis-10435.c311.eu-central-1-1.ec2.redns.redis-cloud.com',
    port=10435,
    decode_responses=True,
    username="default",
    password=REDIS_PASS
)

success = r.set('foo', 'bar')

result = r.get('foo')
print('foo:', result)

print('Deletion return:', r.delete('foo'))