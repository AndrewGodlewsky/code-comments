# Paging on-call for public API error-rate spikes

## Design in brief

- **All state lives in one HA Postgres database.** The evaluator instances hold no state that matters. Either instance can do any step at any time, and a crash loses only work that was never committed.
- **The two instances coordinate through unique keys, not leader election.** Both instances evaluate every minute. The `evaluations` table has a primary key on `(service, rule, minute)`, so only one instance can commit a result for a given minute. The other instance's insert fails and it skips that minute. A partial unique index on `incidents (service, rule) WHERE status <> 'resolved'` enforces the "one unresolved incident" rule as a second guard.
- **The 5-minute timers are rows in a `jobs` table.** When an incident opens, the same transaction writes all three escalation jobs, due at T0, T0+5m and T0+10m, where T0 is when the incident opened. A worker loop runs in both instances, polls every 5 s and claims due jobs with `FOR UPDATE SKIP LOCKED`. Due times are fixed when the incident opens and never depend on when or whether a page was delivered, so a failed or slow page cannot delay the clock. An acknowledgement or a resolution cancels the pending jobs.
- **Every time comes from the database's `now()`**, both minute buckets and `due_at`. Clock skew between the instances therefore has no effect.

## Sequence

```mermaid
sequenceDiagram
    autonumber
    participant MS as Metrics store
    participant EA as Evaluator A
    participant EB as Evaluator B
    participant DB as State DB (Postgres)
    participant W as Escalation worker (in A and B)
    participant SCH as Schedule service
    participant PP as Paging provider
    participant P as On-call phones
    participant WH as Ack webhook (in A and B)

    Note over EA,EB: Both tick 10 s past every minute (DB time).<br/>Each evaluates the last complete minute M over window M-4..M.

    rect rgb(232,240,255)
    Note over MS,DB: 1. Detection, per service and alert rule
    par Both instances read the same window
        EA->>MS: sum(requests), sum(5xx) for minutes M-4..M
        MS-->>EA: requests=1840, 5xx=61, rate 3.3%
    and
        EB->>MS: same query
        MS-->>EB: same result
    end
    EA->>DB: BEGIN. INSERT evaluation (service, rule, M, outcome=breach)
    EB->>DB: BEGIN. INSERT evaluation (service, rule, M, outcome=breach)
    Note right of DB: B's insert waits on the primary key until A commits
    Note over EA,DB: breach = rate above 2% and requests at least 500.<br/>Streak = breach rows for contiguous minutes M, M-1, M-2.
    end

    rect rgb(232,255,236)
    Note over EA,DB: 2. Open an incident or suppress
    EA->>DB: SELECT unresolved incident for (service, rule) FOR UPDATE
    alt No unresolved incident and streak reached 3
        EA->>DB: INSERT incident I (status=open, opened_at=T0)
        Note right of DB: Partial unique index on (service, rule)<br/>where status is not resolved
        EA->>DB: INSERT jobs page L1 due T0, L2 due T0+5m, L3 due T0+10m
        EA->>DB: COMMIT
    else Unresolved incident already exists
        EA->>DB: INSERT incident_breach (I, M). No jobs, nobody paged
        EA->>DB: COMMIT
    else Streak below 3
        EA->>DB: COMMIT (evaluation row only)
    end
    DB-->>EB: unique violation on (service, rule, M)
    EB->>DB: ROLLBACK. B does nothing for minute M
    end

    rect rgb(255,246,230)
    Note over W,P: 3. Escalation level 1 (primary). Workers poll jobs every 5 s
    W->>DB: claim due pending jobs FOR UPDATE SKIP LOCKED, lease 60 s
    DB-->>W: job L1 for incident I
    W->>SCH: who is primary for this service now?
    SCH-->>W: alice
    W->>DB: lock I, check status=open, INSERT page (I, L1, alice) unique on (I, level), job done, COMMIT
    W->>DB: re-check I is still open just before sending
    W->>PP: push(alice, ref=I-L1)
    alt Push accepted
        PP->>P: push notification to alice
    else Push error or no answer within 10 s
        W->>PP: sms(alice, ref=I-L1)
        PP->>P: SMS to alice
    end
    W->>DB: record page outcome (push, sms or failed)
    Note over W,DB: L2 is still due at T0+5m, whatever this outcome was.
    end

    rect rgb(255,246,230)
    Note over W,P: 4. T0+5m with no ack yet: level 2 (secondary)
    DB-->>W: job L2 due, I still open
    W->>SCH: who is secondary now?
    SCH-->>W: bob (may differ after the 09:00 handover)
    W->>DB: INSERT page (I, L2, bob), job done, COMMIT
    W->>PP: push(bob, ref=I-L2), SMS if push fails
    PP->>P: page to bob
    Note over EA,DB: Further breaches meanwhile take the "already exists" branch of step 2
    end

    rect rgb(245,235,255)
    Note over PP,WH: 5. Acknowledgement, or the last level
    alt Someone acknowledges before T0+10m
        P->>PP: bob taps Acknowledge
        PP->>WH: POST webhook (ref=I-L2, event id)
        WH->>WH: verify signature
        WH->>DB: INSERT ack_event (event id). On conflict, already handled
        WH->>DB: lock I, UPDATE status=acknowledged, acked_by=bob WHERE status=open
        WH->>DB: UPDATE jobs of I SET cancelled WHERE state=pending, COMMIT
        WH-->>PP: 200 OK (also for a repeated event id)
        Note over W,DB: L3 is cancelled. A worker that already claimed it<br/>finds I acknowledged and drops it.
    else No ack by T0+10m
        DB-->>W: job L3 due, I still open
        W->>SCH: who is engineering manager now?
        SCH-->>W: carol
        W->>DB: INSERT page (I, L3, carol), job done, COMMIT
        W->>PP: push(carol, ref=I-L3), SMS if push fails
        PP->>P: page to carol
        Note over W: Last level. There are no more jobs for I.
    end
    end

    rect rgb(235,250,250)
    Note over EA,P: 6. Resolution
    loop Every minute while I is unresolved (winner of minute M)
        EA->>MS: window query for M-4..M
        EA->>DB: INSERT evaluation (M), clean = requests above 0 and rate below 1%
    end
    EA->>DB: are minutes M-9..M all present and all clean?
    alt Yes, 10 consecutive clean minutes
        EA->>DB: UPDATE I SET resolved WHERE status is not resolved
        EA->>DB: cancel pending page jobs of I (stops escalation if nobody acked)
        EA->>DB: INSERT notice jobs, one per distinct recipient in pages of I, COMMIT
        W->>DB: claim notice jobs, INSERT notice unique on (I, recipient)
        W->>PP: push "resolved" to alice and bob (and carol if paged), SMS if push fails
        PP->>P: resolved notices
    else Any minute not clean, or missing
        EA->>DB: COMMIT, clean streak starts again
    end
    Note over EA,DB: A later streak of 3 breaches opens a new incident,<br/>because the partial index ignores resolved rows.
    end
```

## Where state is kept

All of it is in Postgres, in these tables:

| Table | Key | Holds |
|---|---|---|
| `evaluations` | PK `(service, rule, minute)` | Requests, 5xx, rate, and an outcome of `breach`, `clean`, `neutral` or `unknown`. The PK makes sure one instance per minute does the work. Breach streaks and clean streaks are both computed from these rows. |
| `incidents` | partial unique `(service, rule) WHERE status <> 'resolved'` | `open`, `acknowledged` or `resolved`, plus opened, acked and resolved times and who acknowledged. |
| `incident_breaches` | `(incident_id, minute)` | Breaches recorded on an unresolved incident. They never page anyone. |
| `jobs` | id, index on `(state, due_at)` | Durable timers for the L1, L2 and L3 pages and the resolved notices: `due_at`, `state` (`pending`, `claimed`, `done` or `cancelled`), `lease_until`. |
| `pages` | unique `(incident_id, level)` and unique `(incident_id, recipient)` for notices | Who was actually paged, by which channel, and the outcome. The resolved notices go to the people in this table, not to whoever is on call when the incident resolves. |
| `ack_events` | PK provider event id | Makes the webhook idempotent. |
| `schedule_cache` | `(service, role)` | The last good answer from the schedule service, refreshed every minute. |

Outcomes:
- **breach:** rate above 2% and at least 500 requests.
- **clean:** at least 1 request and rate below 1%.
- **neutral:** anything else, for example a rate of 1 to 2%, or a rate above 2% on fewer than 500 requests.
- **unknown:** the metrics query failed.

Any outcome other than breach resets the breach streak, and so does a missing minute. Any outcome other than clean resets the clean streak.

The page `ref` we send to the provider is `incident-level`. We use it to match the acknowledgement webhook to the right incident, and as the provider's dedup key on retries.

## How failures are handled

| Failure | Behaviour |
|---|---|
| One evaluator instance is down | The other instance wins every minute's insert and runs the worker and the webhook. There is no failover step. |
| An instance crashes in the middle of an evaluation | Its transaction rolls back. The other instance's insert was waiting on the key, so it now succeeds and that instance evaluates the minute. |
| Both instances are down for a while | No rows are written for those minutes. On start, an instance first evaluates any missing minutes from the last 10 (the metrics are stored), then resumes normal ticks. |
| A worker crashes after claiming a job | The lease expires after 60 s and the other instance claims the job again. The unique `(incident, level)` constraint stops a second page row. A page row left in "sending" is resent with the same `ref`, so at worst the person is notified twice, but they are never missed. |
| The push call fails or times out | The page goes by SMS instead, right away, with the same `ref`. |
| Push and SMS both fail | The page is marked `failed` and SMS is retried up to 3 times, 30 s apart. A notice goes to the ops chat. The next level still fires at its fixed due time. |
| Push is accepted but never reaches the phone | We cannot detect this. Escalation covers it, because the next level fires anyway. |
| The schedule service is slow or down | We use `schedule_cache`. If the cached answer is older than the last 09:00 handover, we still page that person and flag the page as stale. With no answer at all, the level counts as a failed page and the next level fires on time. |
| An ack arrives while a page is being sent | The ack and the worker lock the same incident row, so they run one after the other. The worker checks the status again just before calling the provider. The only remaining risk is a page that leaves a few milliseconds after the ack. The person who gets it sees that the incident is already acknowledged. |
| The webhook is down, or an ack is lost | The provider retries, and `ack_events` drops duplicates. If the ack never arrives, escalation continues. This errs toward paging more people, never fewer. |
| An ack arrives for a resolved incident, or arrives twice | It is recorded and has no other effect. |
| The metrics store query fails | The outcome is `unknown`, which resets both streaks. After 3 `unknown` minutes in a row, the primary gets a one-off "monitoring blind" push or SMS. This opens no incident and starts no escalation. |
| The database is down | Nothing evaluates or pages. We mitigate with HA Postgres (a synchronous replica and automatic failover). We also add a dead-man check outside the database: the existing cron script is repointed to send one SMS through the provider if no `evaluations` row has been written for 3 minutes. |

## Assumptions and open questions

- **Late metrics.** We evaluate minute M 70 s after it starts, which assumes the gateway's per-minute counts are complete by then. If they arrive later, we increase the delay.
- **A provider ref we can match on.** We assume the provider accepts a client reference or dedup key and sends it back in the ack webhook.
- **"Stayed below 1% for 10 consecutive minutes."** We read this as 10 consecutive one-minute evaluations, each with a trailing 5-minute rate below 1%. A minute with zero requests is not counted as clean, so an outage that drives traffic to zero does not resolve itself. The brief has no manual resolve, and we need to decide whether to add one.
- **After an ack.** The person who acknowledged stays the owner, even across a 09:00 handover, and nobody is paged again for that incident.