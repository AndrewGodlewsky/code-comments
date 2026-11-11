# Notifications

The batcher sends up to 100 notifications in one provider call.
A partial batch is flushed after 60 seconds, so a notification is never held longer than a minute.

The push provider accepts at most 500 notifications per call and 20 calls a second per app.
