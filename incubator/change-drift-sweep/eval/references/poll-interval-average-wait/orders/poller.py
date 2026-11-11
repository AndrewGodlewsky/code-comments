"""Poll the storefront for new orders.

run() checks for new orders every ten minutes and puts each one on the
fulfilment queue exactly once.
"""

import time

from orders.settings import PAGE_LIMIT, POLL_INTERVAL_S


def next_poll_at(last_poll, interval=POLL_INTERVAL_S):
    """Return when the poll after `last_poll` is due, in clock seconds."""
    return last_poll + interval


def run(storefront, queue, polls, clock=time.monotonic, sleep=time.sleep):
    """Poll `polls` times, queueing every order not seen before."""
    seen = set()
    last = None
    for _ in range(polls):
        if last is not None:
            sleep(max(0.0, next_poll_at(last) - clock()))
        last = clock()
        for order in storefront.new_orders(limit=PAGE_LIMIT):
            # The storefront can list an order in two polls; queue it once.
            if order["id"] not in seen:
                seen.add(order["id"])
                queue.append(order)
