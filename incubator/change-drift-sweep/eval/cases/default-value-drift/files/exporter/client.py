"""Read changed rows from the ledger API.

fetch_changed() asks for 50 rows per request and stops at the first short page.
"""

from exporter.config import PAGE_SIZE, REQUEST_TIMEOUT_S


def fetch_changed(session, since):
    """Yield every ledger row changed on or after `since`, oldest first.

    Pages are numbered from 1.
    """
    page = 1
    while True:
        rows = session.get(
            "/ledger/changes",
            params={"since": since, "page": page, "per_page": PAGE_SIZE},
            timeout=REQUEST_TIMEOUT_S,
        )
        yield from rows
        if len(rows) < PAGE_SIZE:
            return
        page += 1
