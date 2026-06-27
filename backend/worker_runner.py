import os
import sys
import redis
from rq import Worker, Queue
from dotenv import load_dotenv

# Ensure the backend directory is in the import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL")

def main():
    if not UPSTASH_REDIS_URL:
        print("UPSTASH_REDIS_URL is not set. Cannot start background worker.")
        sys.exit(1)

    print(f"Connecting to Upstash Redis: {UPSTASH_REDIS_URL}")
    try:
        redis_conn = redis.from_url(UPSTASH_REDIS_URL)
        # Verify connection
        redis_conn.ping()
    except Exception as e:
        print(f"Failed to connect to Upstash Redis: {e}")
        sys.exit(1)

    # Listen to standard and priority queues. Priority queue is checked first.
    queues = [
        Queue("priority", connection=redis_conn),
        Queue("standard", connection=redis_conn)
    ]

    print("Starting RQ worker for priority and standard queues...")
    worker = Worker(queues, connection=redis_conn)
    worker.work()

if __name__ == "__main__":
    main()
