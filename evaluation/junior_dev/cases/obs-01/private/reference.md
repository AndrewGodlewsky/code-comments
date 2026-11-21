### API error-rate paging: design

**Components**
- *Existing:* API Gateway, Metrics Store (time-series), On-call Schedule, Paging Provider (push, SMS, Acknowledge webhook).
- *New:* Alert Evaluator (2 instances, each runs every 60 s), Incident Manager (service), Incident DB (Postgres), Timer Queue (delayed messages, at-least-once delivery).

**State, all kept in the Incident DB**
- `rule_state(service, rule, last_minute, breach_count, clear_count)`: the counters for consecutive evaluations.
  - Breaching evaluation (rate above 2% and at least 500 requests in the 5-min window): `breach_count += 1`, `clear_count = 0`.
  - Rate below 1%: `clear_count += 1`, `breach_count = 0`.
  - Anything else: both reset to 0.
- `incidents(id, service, rule, status open|acked|resolved, opened_at, last_fired_at, breach_total, acked_by, resolved_at)`, with a **unique constraint on (service, rule) where status is not resolved**. This constraint is the deduplication key.
- `page_log(incident_id, level, recipient, channel, result)`: one row per page sent.

**Who calls whom:** the evaluator reports *every* breaching evaluation to the Incident Manager, with the current `breach_count`. The Incident Manager decides: record it on an unresolved incident, open a new one (count 3 or more), or do nothing yet (count below 3).

```mermaid
sequenceDiagram
    autonumber
    participant GW as API Gateway
    participant MS as Metrics Store
    participant EV as Alert Evaluator (2 instances)
    participant DB as Incident DB
    participant IM as Incident Manager
    participant TQ as Timer Queue
    participant SCH as On-call Schedule
    participant PP as Paging Provider
    actor ENG as Engineers

    Note over GW,ENG: 1. Detect (every 60 s, per service and rule)
    GW->>MS: write request and 5xx counts each minute
    EV->>MS: query trailing 5 min
    MS-->>EV: requests, 5xx
    EV->>DB: compare-and-set rule_state for minute m, update counters
    Note over EV,DB: Only the instance that wins minute m goes on. The other skips this minute.

    Note over GW,ENG: 2. Open or suppress (sent on every breaching evaluation)
    EV->>IM: breach(service, rule, breach_count)
    IM->>DB: find unresolved incident for (service, rule)
    alt unresolved incident exists
        IM->>DB: record breach on it (last_fired_at, breach_total + 1)
        Note over IM: Duplicate suppressed, nobody paged
    else none, and breach_count is 3 or more
        IM->>DB: insert incident (open)
        Note over IM,DB: If the insert hits the unique constraint, record the breach on the existing incident and page nobody
        IM->>TQ: schedule escalate(incident, level 2) due in 5 min
        IM->>SCH: who is primary right now
        SCH-->>IM: primary
        IM->>PP: push page to primary (SMS if push call fails)
        PP->>ENG: page
        IM->>DB: append page_log (level 1, recipient, channel, result)
    else none, and breach_count below 3
        Note over IM: Not 3 in a row yet, do nothing
    end

    Note over GW,ENG: 3. Escalate (timer fires 5 min after the previous page)
    TQ->>IM: escalate(incident, level N)
    IM->>DB: read status and page_log
    alt status open and level N not in page_log
        opt N is 2
            IM->>TQ: schedule escalate(incident, level 3) due in 5 min
        end
        IM->>SCH: who holds level N right now
        SCH-->>IM: secondary (N=2) or engineering manager (N=3)
        IM->>PP: push page (SMS if push call fails)
        PP->>ENG: page
        IM->>DB: append page_log (level N, recipient, channel, result)
    else acked, resolved, or level already paged
        Note over IM: Drop the timer, send nothing
    end

    Note over GW,ENG: 4. Acknowledge
    ENG->>PP: tap Acknowledge
    PP->>IM: ack webhook (incident, engineer)
    IM->>DB: set status acked and acked_by, only if status is open
    Note over IM,TQ: Pending timer is not cancelled. It fires, sees acked and drops.

    Note over GW,ENG: 5. Resolve (rule_state.clear_count reaches 10 in step 1)
    EV->>IM: clear(service, rule)
    IM->>DB: set unresolved incident to resolved, with resolved_at
    IM->>DB: read distinct recipients from page_log
    IM->>PP: resolved notice to each recipient
    PP->>ENG: resolved notice
    Note over IM,TQ: Any pending timer sees resolved and drops, so escalation stops.
```

**Failure and edge behaviour**
- **The clock never waits on delivery.** The next escalation timer is put on the Timer Queue *before* the page is sent. If push fails, the page goes by SMS. If SMS also fails, `page_log.result = failed` and the next level is still paged when its timer fires.
- **Timers are at-least-once.** A repeated `escalate` whose level is already in `page_log` is skipped. If the Incident Manager is down when a timer is due, the queue redelivers it once the manager is back. That page is late but not lost.
- **Level 3 (engineering manager) is the last level.** No timer is scheduled after it. The incident stays open until someone acknowledges it or it resolves.
- **Who to page is looked up at send time for each level**, so a 09:00 handover during an incident pages whoever holds the role at that moment.
- **Two evaluator instances.** The compare-and-set on `last_minute` lets only one instance process each minute. The unique constraint is the backstop: if two inserts race, one fails and that breach is recorded on the existing incident.
- **Every breach while unresolved is recorded**, including the first one or two after the counters were reset, because the evaluator reports each breaching evaluation and the Incident Manager checks for an unresolved incident first.
- **After resolution** the old row no longer falls under the unique constraint. The next 3 consecutive breaching evaluations open a new incident and page the primary again.
