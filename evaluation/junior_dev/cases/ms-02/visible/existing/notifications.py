# app/notifications.py -- current in-process notification sending (monolith)
import uuid
from datetime import timedelta
from app import db, mailrelay, templates, alerts, clock

MAX_ATTEMPTS = 5
BACKOFF_MINUTES = [1, 2, 4, 8]   # wait before attempts 2, 3, 4, 5
POLL_SECONDS = 5
BATCH_SIZE = 50


def enqueue_notification(tx, user, ntype, payload):
    """Called by business code INSIDE its own transaction (checkout,
    carrier webhook, password reset). The row exists only if the
    caller's transaction commits."""
    tx.execute(
        "INSERT INTO notifications (id, type, user_id, email, payload,"
        " status, attempts, next_attempt_at, created_at)"
        " VALUES (%s, %s, %s, %s, %s, 'pending', 0, now(), now())",
        (str(uuid.uuid4()), ntype, user.id, user.email, payload),
    )


def run_worker():
    """Background thread started on every monolith instance."""
    while True:
        with db.transaction() as tx:          # one commit per batch
            rows = tx.query(
                "SELECT * FROM notifications"
                " WHERE status = 'pending' AND next_attempt_at <= now()"
                " ORDER BY created_at LIMIT %s FOR UPDATE SKIP LOCKED",
                (BATCH_SIZE,),
            )
            for row in rows:
                _deliver(tx, row)
        clock.sleep(POLL_SECONDS)


def _deliver(tx, row):
    subject, body = templates.render(row.type, row.payload)
    attempts = row.attempts + 1
    try:
        mailrelay.send(to=row.email, subject=subject, body=body)
    except mailrelay.Error as err:            # includes timeouts
        if attempts >= MAX_ATTEMPTS:
            tx.execute("UPDATE notifications SET status = 'failed',"
                       " attempts = %s WHERE id = %s", (attempts, row.id))
            alerts.page_oncall("notification failed", row.id, str(err))
        else:
            wait = timedelta(minutes=BACKOFF_MINUTES[attempts - 1])
            tx.execute("UPDATE notifications SET attempts = %s,"
                       " next_attempt_at = now() + %s WHERE id = %s",
                       (attempts, wait, row.id))
        return
    tx.execute("UPDATE notifications SET status = 'sent', attempts = %s"
               " WHERE id = %s", (attempts, row.id))
