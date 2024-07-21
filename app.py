import time

import redis
from flask import Flask


app = Flask(__name__)
# Access environment variables
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')  # Default to 'localhost' if not set
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))    # Default to 6379 if not set

# Connect to Redis
cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
#cache = redis.Redis(host='redis', port=6379)


def get_hit_count():
    retries = 5
    while True:
        try:
            return cache.incr('hits')
        except redis.exceptions.ConnectionError as exc:
            if retries == 0:
                raise exc
            retries -= 1
            time.sleep(0.5)


@app.route('/')
def hello():
    count = get_hit_count()
    return 'Hello World! I have been seen {} times.\n'.format(count)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

