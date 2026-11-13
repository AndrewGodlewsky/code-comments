"""Background job queue (existing).

Jobs run on the `worker` pool. Each worker process has 512 MB of memory
and runs one job attempt at a time.
"""

from dataclasses import dataclass

MAX_ATTEMPTS = 3                # a job is tried at most 3 times in total
BACKOFF_SECONDS = [60, 300]     # wait before attempt 2, and before attempt 3
ATTEMPT_TIMEOUT_SECONDS = 1800  # an attempt still running after 30 min is killed


@dataclass
class JobContext:
    job_id: str
    attempt: int  # 1, 2 or 3


def job(name, on_final_failure=None):
    """Decorator that registers a job handler: handler(ctx, payload).

    An attempt fails if the handler raises, hits the timeout, or its worker
    dies. A failed attempt is retried after BACKOFF_SECONDS until
    MAX_ATTEMPTS is reached. The queue keeps no progress between attempts:
    each attempt calls the handler again from the start with the same payload.

    on_final_failure(ctx, payload, error) is called once, after the last
    attempt has failed.
    """


def enqueue(name, payload):
    """Queue a job and return its job_id.

    payload must be JSON-serialisable and under 64 KB. Delivery is at least
    once: a handler may occasionally run again for a job that already
    succeeded, so handlers must tolerate that.
    """
