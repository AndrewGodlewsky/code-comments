"""Take payment events off the queue and post their ledger entries."""
from events.dispatch import dispatch


def consume(messages, post, kinds=None):
    """Post the entries for each message, and return the messages that failed.

    The queue puts failed messages back and dead-letters them after five tries.
    """
    failed = []
    for message in messages:
        try:
            post(dispatch(message, kinds))
        except KeyError:
            failed.append(message)
    return failed
