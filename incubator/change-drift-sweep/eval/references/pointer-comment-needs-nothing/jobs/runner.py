"""Run queued jobs on a thread pool and collect their results."""

from concurrent.futures import ThreadPoolExecutor

from jobs import limits


class JobFailed(Exception):
    """A job raised on every try."""


def _run_with_tries(job):
    for attempt in range(1, limits.MAX_TRIES + 1):
        try:
            return job()
        except Exception as error:
            if attempt == limits.MAX_TRIES:
                raise JobFailed(repr(error)) from error


def run_all(jobs):
    """Run every job and return their results in submission order.

    Never more than MAX_PARALLEL jobs run at once.
    """
    # The pool size is the concurrency cap, so no separate semaphore is needed.
    with ThreadPoolExecutor(max_workers=limits.MAX_PARALLEL) as pool:
        return list(pool.map(_run_with_tries, jobs))
