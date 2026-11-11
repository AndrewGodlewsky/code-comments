"""Re-export the days a failed nightly job missed."""

from datetime import date, timedelta
from pathlib import Path

from app.cli import main


def backfill(source, first_missing, outdir, today=None):
    """Write one export per day from `first_missing` to `today` into `outdir`.

    Each file holds every row changed on or after its day, as the nightly job
    would have written it.
    """
    today = today or date.today()
    written = []
    day = first_missing
    while day <= today:
        target = Path(outdir) / f"orders-{day.isoformat()}.csv"
        main(["export", str(source), "--after", day.isoformat(), "--output", str(target)])
        written.append(target)
        day += timedelta(days=1)
    return written
