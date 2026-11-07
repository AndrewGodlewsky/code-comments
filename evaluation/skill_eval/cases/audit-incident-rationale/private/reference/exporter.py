import json

ENDPOINT = "https://warehouse.internal/api/v2/load"
BATCH_SIZE = 500


def encode(batch):
    return json.dumps(batch, sort_keys=True).encode("utf-8")


def export(records, send, start_after=None):
    """Send ``records`` to the warehouse in batches; return the last id sent.

    Pass the returned id back as ``start_after`` to resume a failed run.
    """
    # Sort by id before batching: resuming with start_after assumes every lower
    # id was already sent. In arrival order, a resumed run skipped records that
    # had not gone out yet (INC-231).
    ordered = sorted(records, key=lambda record: record["id"])
    if start_after is not None:
        ordered = [record for record in ordered if record["id"] > start_after]
    last_sent = start_after
    for start in range(0, len(ordered), BATCH_SIZE):
        batch = ordered[start:start + BATCH_SIZE]
        send(ENDPOINT, encode(batch))
        last_sent = batch[-1]["id"]
    return last_sent
