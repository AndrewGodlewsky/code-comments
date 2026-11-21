# Paging on-call for public API error-rate spikes: design

## Summary

Two identical evaluator instances run every minute. They share one SQL database that holds all state. Database constraints guarantee three things:
- Only one instance acts on each minute.
- Only one unresolved incident exists per (service, rule).
- Each escalation level is paged only once.

Escalation timers are deadlines stored in the database, not in-memory timers. A sweeper loop checks those deadlines every 10 seconds. It runs on both instances.

Terms used below:
- **Tick**: the scheduler's once-a-minute trigger. Minute `T` is the minute-aligned time of a tick.
- **Rule**: an alert rule. Today there is one, the error-rate rule. Everything is keyed by (service, rule).
- **CAS** (compare-and-set): an `UPDATE` whose `WHERE` clause states the state the caller expects. If another process changed the row first, zero rows match and the update does nothing.
- **Outbox**: a table of messages to send. A transaction writes the row first, and a separate dispatcher sends it later. A crash between the two steps loses nothing.

## Where state lives

All state is in one transactional SQL database, called "State DB" below. The design assumes Postgres-style features: unique partial indexes, `ON CONFLICT`, row locks and `FOR UPDATE SKIP LOCKED`. No state lives in evaluator memory, so either instance can crash or restart at any point.

| Table | Purpose |
|---|---|
| `evaluations(service, rule, minute_ts, requests, errors, rate, breaching, healthy)` | One row per (service, rule, minute). Its primary key is the coordination lock between the two instances. Streaks are computed from the latest rows. |
| `incidents(id, service, rule, status, opened_at, resolved_at, breach_count, last_breach_at, level, next_escalation_at, acked_by, acked_at)` | `status` is `open` or `resolved`. A unique partial index on `(service, rule) WHERE status <> 'resolved'` enforces at most one unresolved incident. `level` is the highest escalation level paged so far: 1 is primary, 2 is secondary, 3 is engineering manager. |
| `pages(id, incident_id, kind, level, recipient, status, channel_used, provider_ref)` | The page outbox. `kind` is `page` or `resolved`. `status` is `pending`, `sending`, `sent`, `failed` or `cancelled`. `recipient` is empty until the dispatcher sends the row. Two unique partial indexes prevent duplicates: `(incident_id, level) WHERE kind = 'page'` stops a level from being paged twice, and `(incident_id, recipient) WHERE kind = 'resolved'` gives each person one resolved notice. |

**Classifying evaluations.** Each evaluation row is classified as follows.
- `breaching`: the rate is above 2% and the window holds at least 500 requests.
- `healthy`: the rate is below 1%.
- Neither: everything else, such as a rate between 1% and 2%, or a rate of 1% or more on fewer than 500 requests.
- Assumption to confirm with the owners: a window with zero requests counts as healthy, because there is no error rate to speak of.

**Streak rules.**
- An incident opens when the last 3 consecutive `minute_ts` rows are all breaching. A missing minute breaks the run.
- An incident resolves when the last 10 consecutive minutes are all healthy. A minute that is breaching or neither resets the healthy run.

**Two evaluators.** Both run every tick for the same minute `T`.
1. Each opens a transaction and inserts the `evaluations` row for `(service, rule, T)` with `ON CONFLICT DO NOTHING`.
2. Only the instance whose insert succeeds proceeds. In Postgres, a concurrent inserter waits for the first transaction to finish. If the first instance crashes, its transaction rolls back and the other instance's insert succeeds, so the minute is never lost.
3. The winner queries the metrics store, stores the result and applies the incident changes inside that same transaction.
4. The unique partial index on `incidents` is a second guard. Even if the first mechanism failed, a second unresolved incident cannot be inserted.

**Timers.** There are no in-memory timers. Each open incident stores `level` and `next_escalation_at`.
- Opening sets `level = 1` and `next_escalation_at = T + 5 min`.
- Both instances run a sweeper every 10 s. It selects incidents where `status = 'open' AND acked_at IS NULL AND level < 3 AND next_escalation_at <= now()`.
- It claims an incident with a CAS update: `UPDATE ... SET level = level + 1, next_escalation_at = next_escalation_at + 5 min WHERE id = ? AND level = <seen> AND acked_at IS NULL AND status = 'open'`. Only one instance's update changes a row.
- The CAS update and the new `pages` row are written in one transaction.
- The new deadline is anchored to the previous deadline, not to when sending finished. A slow or failed send therefore cannot move the clock. Escalation lateness is at most about 10 s.
- Level 3 (engineering manager) is the last level, so the sweeper never selects it again.

**On-call lookup.** The recipient is resolved when the dispatcher sends a page, not when the incident opens. A 09:00 handover mid-incident is therefore picked up. The resolved person is stored on the `pages` row, and "resolved" notices go to the people stored on those rows, not to whoever is on call at that moment.

## How failures are handled

- **Push fails.** The dispatcher sends SMS to the same recipient, with the page id as the provider idempotency key. If both fail, the page is marked `failed`, retried with backoff for a bounded time and raises an internal alert. The escalation deadline is already stored, so it is untouched.
- **Dispatcher crash.** `pages` rows in `pending` or `sending` are picked up again by either instance. The idempotency key avoids duplicate sends on retry.
- **Evaluator crash.** The in-flight transaction rolls back and the other instance takes the minute. If both are down, the minutes are missing and the streaks reset, so there are no false pages. A dead-man's-switch alert should watch for the evaluators going silent.
- **Metrics store failure.** The tick records no breaching or healthy result, so the minute breaks both streaks. Alert on repeated failures. Escalation of an already-open incident does not depend on the metrics store.
- **On-call service failure.** Retry for a few seconds, then use the last known holder of that role. If there is none, record a failed page and continue. The clock advances regardless.
- **Acknowledgement.** The provider webhook is signature-checked and idempotent. It runs a CAS update: `UPDATE incidents SET acked_at = now(), acked_by = ? WHERE id = ? AND status = 'open' AND acked_at IS NULL`.
  - A person who was paged earlier can still acknowledge after handover.
  - A page claimed in the same instant as an ack may still go out. That is accepted, and no later level is claimed.
  - An ack on a resolved incident is recorded but ignored.
- **Resolve before ack.** Resolution sets `status = 'resolved'`, which fails the sweeper's claim condition, so escalation stops. Page rows not yet sent are marked `cancelled`. A "resolved" `pages` row is queued for each distinct recipient who has already been paged, and goes by push with SMS fallback.
- **New incident after resolution.** The old incident is no longer unresolved, so the unique index allows a new one. It still needs 3 fresh consecutive breaching evaluations.

## Sequence diagram

The diagram shows one evaluator (A) winning the minute and doing the work. The dispatcher and sweeper loops run on both instances, but the diagram draws them from A's side. The one exception is the sweeper, where B races A.

```mermaid
sequenceDiagram
    autonumber
    participant S as Scheduler
    participant A as Evaluator A
    participant B as Evaluator B
    participant M as Metrics store
    participant DB as State DB
    participant OC as On-call service
    participant PP as Paging provider
    participant P as On-call person
    participant WH as Ack webhook

    Note over S,WH: Detection, every 60 s. Both instances get the same tick for minute T

    S->>A: tick T
    S->>B: tick T
    par Evaluator A
        A->>DB: BEGIN, INSERT evaluation (service, rule, T) ON CONFLICT DO NOTHING
    and Evaluator B
        B->>DB: BEGIN, INSERT evaluation (service, rule, T) ON CONFLICT DO NOTHING
    end
    DB-->>A: inserted, A owns minute T
    DB-->>B: waits, then conflict, B skips this minute
    Note over B,DB: If A crashes, its transaction rolls back and B's insert succeeds

    A->>M: 5xx and request counts for the 5 min ending at T
    M-->>A: counts
    Note over A: rate = 5xx / requests<br/>breaching if rate above 2% and requests at least 500<br/>healthy if rate below 1%
    A->>DB: store result for T, read recent evaluations

    alt 3 consecutive breaching minutes and no unresolved incident
        Note over A,DB: Opening an incident
        A->>DB: INSERT incident, level 1, next_escalation_at = T + 5 min, ON CONFLICT DO NOTHING
        A->>DB: INSERT page row for level 1 (pending), COMMIT
    else breaching and an unresolved incident exists
        Note over A,DB: Duplicate suppression, no page is created
        A->>DB: UPDATE incident, breach_count + 1, last_breach_at = T, COMMIT
    else 10 consecutive healthy minutes and an unresolved incident
        Note over A,DB: Resolution
        A->>DB: UPDATE incident SET status resolved, resolved_at = T
        A->>DB: cancel unsent page rows, INSERT resolved notice rows, one per distinct paged recipient, COMMIT
    else nothing to change
        A->>DB: COMMIT
    end

    Note over A,PP: Dispatcher, run by either instance, for pending page rows
    loop each pending page row, claimed with FOR UPDATE SKIP LOCKED
        A->>OC: who holds this role for the service now
        OC-->>A: person
        A->>DB: store recipient on the page row
        A->>PP: send push (idempotency key = page id)
        alt push succeeds
            PP-->>P: push notification with Acknowledge button
            A->>DB: mark page sent via push
        else push fails
            A->>PP: send SMS (same idempotency key)
            PP-->>P: SMS
            A->>DB: mark page sent via sms, or failed after retries
        end
    end
    Note over A,DB: Send outcome never changes next_escalation_at

    Note over A,B: Escalation timer, sweeper on both instances every 10 s
    loop every 10 s
        par Evaluator A
            A->>DB: due incidents, status open, no ack, level below 3, next_escalation_at passed
        and Evaluator B
            B->>DB: due incidents, same query
        end
        A->>DB: CAS UPDATE level + 1, next_escalation_at + 5 min WHERE level = seen AND acked_at IS NULL AND status open
        B->>DB: same CAS
        DB-->>A: 1 row changed, A wins
        DB-->>B: 0 rows changed, B skips
        A->>DB: INSERT page row for the new level (pending, same transaction as the CAS)
        Note over A,PP: Dispatcher sends it as above, looking up the role for the new level (primary, then secondary, then engineering manager). Level 3 is the last, so the sweeper never selects it again
    end

    Note over P,WH: Acknowledgement
    P->>PP: taps Acknowledge
    PP->>WH: webhook, signed, with page ref
    WH->>DB: CAS UPDATE incident SET acked_at, acked_by WHERE status open AND acked_at IS NULL
    alt first ack
        DB-->>WH: 1 row changed
        Note over DB: The sweeper's claim condition now fails, escalation stops
    else duplicate ack or incident already resolved
        DB-->>WH: 0 rows changed, recorded and ignored
    end
    WH-->>PP: 200 OK

    Note over A,P: Resolved notices
    A->>PP: dispatcher sends resolved notice to each paged recipient (push, SMS fallback)
    PP-->>P: resolved notice
    Note over A,DB: If resolved before any ack, status resolved stops the sweeper, so no further levels are paged
```