# Pair 11

Which document would a smart engineer who does not know this project understand faster and more correctly?

---

# Document A

### Error-rate paging

This design pages the on-call engineer when the public API's 5xx error rate spikes. A 5xx response is a server error. The error rate is the share of requests that return one. The design replaces a cron job that emails a shared inbox nobody reads at 3 a.m.

**How it works in brief**
Every 60 seconds, two identical evaluator instances check the error rate over the last 5 minutes. If the rate is too high on 3 checks in a row, the system opens an incident and pages the primary on-call engineer. If nobody acknowledges (acks) the page within 5 minutes, it pages the secondary. If there is still no ack after another 5 minutes, it pages the engineering manager, who is the last level. If the error rate stays low for 10 checks in a row, the incident closes and everyone who was paged gets a "resolved" notice. All state is stored in Postgres.

**Terms used below**
- **Evaluation:** one check, run every 60 seconds, of the error rate over the trailing 5 minutes, for one service and one alert rule.
- **Breach:** an evaluation where more than 2% of requests were 5xx and the window holds at least 500 requests.
- **Clear:** an evaluation where less than 1% of requests were 5xx and the window holds at least 500 requests.
- **Neither:** an evaluation that is not a breach and not a clear. It is one of two kinds:
  - **Middle band:** the window holds at least 500 requests and the rate is 1% or more, but not above 2%.
  - **Low traffic:** the window holds fewer than 500 requests.
- **Streak:** a run of consecutive evaluations of the same kind. The breach streak counts breaches. The clear streak counts clears.
- **Incident:** one open alert for one (service, alert rule) pair. There is at most one open incident per pair.
- **Level:** a step in the escalation order. The levels are primary, secondary and engineering manager (manager).
- **Ack (acknowledgement):** an engineer taps Acknowledge in the paging app. This stops escalation.
- **Rota:** the on-call roster, which names the primary, secondary and manager. It changes at 09:00 each day. The system looks up the rota each time it pages someone, not once when the incident starts.

**Components**
- **Evaluator (two instances):** runs the check every 60 seconds. Both instances run the same logic.
- **Incident manager:** the logic that opens incidents, sends pages, escalates and closes incidents.
- **Postgres:** the database that holds all state.
- **Timer queue:** fires delayed steps, such as the 5-minute escalation.
- **Schedule service:** answers who is on call for a service right now.
- **Paging provider:** sends push notifications and SMS. It also calls our webhook when someone acks.

```mermaid
sequenceDiagram
    participant E as Evaluator
    participant IM as Incident manager
    participant DB as Postgres
    participant TQ as Timer queue
    participant SCH as Schedule service
    participant PP as Paging provider
    participant ENG as On-call engineer

    Note over E,IM: Every 60 seconds, both evaluator instances run the same check
    E->>IM: evaluation for minute M (breach, clear or neither)
    IM->>DB: store evaluation keyed by (service, rule, minute M), ignored if already stored
    IM->>DB: update breach streak or clear streak
    alt 3 consecutive breaches and no open incident
        IM->>DB: insert incident (unique index allows one open incident per service and rule)
        IM->>SCH: who is primary right now
        SCH-->>IM: primary
        IM->>PP: push page to primary
        PP-->>IM: result
        opt push failed
            IM->>PP: SMS page to primary
        end
        IM->>DB: write page_log row for primary
        IM->>TQ: set 5 minute escalation timer for this incident
    else breach and incident already open
        IM->>DB: add breach to the open incident, no page
    end

    TQ->>IM: escalation timer fires (incident, next level)
    IM->>DB: read incident state
    alt still open and no ack
        IM->>DB: claim page_log row for next level (unique key stops a second send)
        IM->>SCH: who is next level right now
        SCH-->>IM: secondary, or engineering manager
        IM->>PP: push page to next level
        PP-->>IM: result
        opt push failed
            IM->>PP: SMS page to next level
        end
        IM->>TQ: set next 5 minute timer, unless this was the last level
    else already acked or resolved
        IM->>IM: do nothing, timer ends
    end

    ENG->>PP: taps Acknowledge
    PP->>IM: webhook with incident id and engineer
    IM->>DB: set acked_at and acked_by (first ack wins)
    IM->>TQ: cancel pending escalation timer

    E->>IM: evaluation for minute M (clear)
    IM->>DB: increment clear streak
    alt 10 consecutive clear minutes
        IM->>DB: mark incident resolved
        IM->>TQ: cancel pending escalation timer
        loop each person paged on this incident
            IM->>PP: resolved notice (push, SMS if push fails)
        end
    end
```

**Where state lives**
- **Postgres is the single source of truth.** It holds three tables and one index:
  - `incidents`: one row per incident. It holds the state (open or resolved), the breach and clear streak counters, `acked_at`, `acked_by`, `next_escalation_at`, and the rota snapshot from the last successful schedule lookup.
  - `evaluations`: one row per (service, rule, minute). The unique key means both evaluator instances can write the same minute without it being counted twice. The first write wins, and the second is ignored.
  - `page_log`: one row per page attempt. Each row holds the incident id, level, channel (push or SMS), recipient, status and provider reference. A unique key on (incident, level) means only one writer can send a given level. Before sending, the writer inserts this row, which is called claiming the level. If the insert fails, another writer has already claimed it, so this writer does nothing.
  - A partial unique index on open incidents, per (service, rule), means two incidents cannot be open at once. "Partial" means the index applies only to rows whose state is open.
- **The timer queue only triggers the next step.** Timers are not the record of what happened. If the queue loses a timer, each evaluator also sweeps the table for incidents whose `next_escalation_at` has passed, and runs the next step for them. The `page_log` guard makes the sweep safe to run alongside the timers, because a level cannot be sent twice.
- **The two evaluators coordinate through Postgres, not with each other.** Both compute the same rates and write to the same minute key, and only the first write takes effect. No leader election is needed.

**How failures are handled**
- **Push fails:** send an SMS. The escalation clock does not wait for either send. The next timer is set right after the send attempts, whatever their result. Each failure is recorded in `page_log`.
- **Both push and SMS fail:** the incident still escalates on schedule. The failure is logged and flagged for follow-up.
- **Schedule service is down:** use the rota snapshot stored on the incident, from the last successful lookup. Retry the lookup in the background.
- **Postgres is down:** the evaluators cannot record anything, so nothing pages. This is a known gap. A separate dead-man check on the evaluators is recommended, but it is outside this design.
- **One evaluator is down:** the other keeps evaluating and can open incidents alone.

**Rule details to confirm**
- **Middle band resets:** the rule says any evaluation that is not a breach resets the breach streak. So a middle-band evaluation (1% to 2%, enough traffic) resets the breach streak. It also resets the clear streak, because the clear rule says any evaluation at or above 1% resets it. Confirm this is intended.
- **Low-traffic windows:** a window with fewer than 500 requests is neither a breach nor a clear. It does not add to either streak. It also does not reset a streak, so the streak pauses. A quiet service can therefore stay open after a spike. Confirm this is acceptable, and confirm that low traffic should pause the streaks rather than reset them.
- **Reopening:** once an incident resolves, a new breach opens a new incident.
- **First come:** the first ack or resolve wins. A later ack or resolve does not change it.
- **Crash after claiming:** if an evaluator crashes after claiming a level but before sending the page, that level is never paged. Confirm whether the sweep should resend claimed levels that have no provider result.

---

# Document B

### Error-rate paging

Today a cron script emails a shared inbox when a service's API error rate is high, and nobody reads it at 3 a.m. This design pages a person instead. Two evaluator instances check each service's error rate every minute and write each result to Postgres. After three breaching minutes in a row, an incident opens and the on-call primary is paged. If nobody acknowledges within 5 minutes, the page moves to the secondary, then to the engineering manager (EM), 5 minutes apart. The incident resolves itself after 10 quiet minutes. Postgres holds all state, so both evaluators and the timers agree on what is open, and for each minute only the evaluator whose write wins acts on it.

### Terms

- **5xx**: an HTTP server-error response (status 500 to 599).
- **Metrics store**: a time-series database. The API gateway writes request and 5xx counts per service every minute. The trailing 5-minute rate is the 5xx total divided by the request total over the last five one-minute buckets.
- **Breach**: a minute where the trailing window has more than 2% 5xx and at least 500 requests.
- **Clear minute**: a minute where the trailing window has less than 1% 5xx.
- **Neither**: any other minute that has requests.
- **Streak**: consecutive minutes of one kind. A minute of another kind resets it.
- **Alert rule**: a named condition on a service. Here, the 5xx rule above.
- **Incident**: one open problem for one service and one alert rule.
- **Schedule service**: says who is primary, secondary and EM for a service right now. Rotations hand over at 09:00 every day.
- **Paging provider**: an outside service that sends push notifications to its phone app, and SMS. Each send returns a provider reference. When the engineer taps Acknowledge (ack) in the app, the provider calls our webhook (an address on our side) with that reference.
- **Timer queue**: holds a message and delivers it after a delay. Used for the 5-minute escalation step.
- **Incident manager**: the code module that opens incidents, sends pages, escalates and handles acks. It is part of the app, not a separate service. The evaluator calls it directly after its database commit. The timer queue and the webhook call it too.
- **Escalation level**: 0 is primary, 1 is secondary, 2 is EM.
- **Row lock**: a Postgres lock on one row. Other transactions that need that row wait until the lock is released at commit.

### Flow

```mermaid
sequenceDiagram
    participant Ev as Evaluator (one of two)
    participant DB as Postgres
    participant IM as Incident manager
    participant Sch as Schedule service
    participant Pg as Paging provider
    participant TQ as Timer queue
    participant Eng as Engineer

    loop Every 60 s, both evaluators run
        Ev->>DB: insert evaluation row for service, rule, minute
        alt Insert succeeded
            Ev->>DB: update streaks and incident in one transaction
            alt Breach streak reaches 3 and no open incident
                Ev->>DB: insert incident at level 0
                Ev->>IM: incident opened, after commit
                IM->>Sch: who is primary now
                IM->>Pg: push page to primary
                opt Push failed or no answer in 10 s
                    IM->>Pg: SMS page to primary
                end
                IM->>DB: log each attempt
                IM->>TQ: escalate at level 0 in 5 min
            else Breach while incident open
                Ev->>DB: add breach to open incident, no page
            else Clear streak reaches 10 and incident open
                Ev->>DB: set incident resolved
                IM->>Pg: resolved notice to each paged person
                Pg->>Eng: resolved notice
            end
        else Insert conflicted
            Ev->>Ev: stop, other evaluator has this minute
        end
    end

    TQ->>IM: escalate (incident, level it was paged at)
    IM->>DB: lock incident row
    alt Still open, not acked, still at that level, next level exists
        IM->>DB: level plus 1
        IM->>Sch: who is next level now
        IM->>Pg: push page to next person
        opt Push failed or no answer in 10 s
            IM->>Pg: SMS page to next person
        end
        IM->>DB: log each attempt
        alt Next level is not EM
            IM->>TQ: escalate at new level in 5 min
        end
    else Acked, resolved, stale or no next level
        IM->>IM: do nothing
    end

    Eng->>Pg: tap Acknowledge
    Pg->>IM: webhook with page reference
    IM->>DB: find incident from page_log
    IM->>DB: lock incident row, set acked time if empty
```

### Rules

1. **Classify each minute.** A minute is breach, clear or neither, judged on its trailing window. A window with no requests changes nothing. This includes a service with no series in the store, because a missing series cannot show a clear rate. A neither minute resets both streaks. A breach resets the clear streak, and a clear minute resets the breach streak.
2. **One writer per minute.** Both evaluators run every 60 seconds and each tries to insert an `evaluation` row for the service, rule and minute. Only the insert that succeeds handles that minute. The other evaluator stops. The streak update and any incident change commit in one transaction, so each minute counts once.
3. **Open.** When the breach streak reaches 3 and `rule_state` has no open incident, the winner inserts an incident at level 0. A unique index allowing one open incident per service and rule backs this up. After the commit, the incident manager pages the primary.
4. **While open.** A breach adds one to the incident's breach count and sends no page.
5. **Resolve.** When the clear streak reaches 10 with an incident open, the status change to resolved commits in the same transaction. Then each person who was paged for the incident gets one resolved notice. A breach after that opens a new incident with fresh streaks.
6. **Every page uses one procedure.**
   - Look up the person for the level in the schedule service at the moment of sending, so a 09:00 handover is respected. If the lookup fails, write a failed row with no person and send nothing. Rule 7 still applies.
   - Send push. If the push call errors or gets no answer within 10 seconds, send SMS.
   - Write one `page_log` row per attempt, with the provider reference the provider returned.
   - Each page names the service, the alert rule and the current 5xx rate.
7. **Escalate timer.** After a page to the primary or secondary, queue an escalate message for 5 minutes later. Queue it whatever the page result. No timer follows the EM page.
8. **Escalate check.** The escalate message names the incident and the level it was paged at. The incident manager locks the row and acts only if the incident is open, not acked and still at that level. Then it pages the next level, as in rule 6. Otherwise it does nothing. In normal flow the check always passes, because each level queues one timer. The check exists for duplicate, redelivered or late timers, which then do nothing.
9. **Ack.** The webhook gives a provider reference. `page_log` maps it to the incident. The incident manager locks the row and sets acked time if it is empty. Any ack stops escalation, and later acks change nothing. An ack does not change breach counting or resolving. The incident stays open and counts breaches until 10 quiet minutes pass, acked or not.
10. **Ack and escalate share the row lock.** If the ack commits first, escalate does nothing. If escalate commits first, the next level is paged once, and the ack then stops any further levels.
11. **Resolved notices.** Each distinct person with a `page_log` row for the incident gets one resolved notice, however many attempts they had. People at levels never reached have no row and get nothing. Notices use push then SMS, with the person taken from `page_log` instead of a fresh lookup. They are logged with purpose resolved. No timer is queued. Timers that fire later do nothing, because the incident is no longer open.

### Where state lives

All state is in Postgres.

- `rule_state`: one row per service and rule. Holds the breach streak, the clear streak and a pointer to the open incident, if any.
- `evaluation`: one row per service, rule and minute. Its unique key picks the one evaluator that handles that minute.
- `incident`: status (open or resolved), level, breach count, acked time and resolved time.
- `page_log`: one row per page attempt and per resolved notice. Holds the incident, purpose (page or resolved), role, person (empty if the lookup failed), channel (push or SMS), result and provider reference. The ack webhook and resolved notices read it.

The timer queue holds only the pending escalate messages, each with its incident and level.

### When things fail

| What fails | What happens |
|---|---|
| One evaluator stops | The other evaluates every minute. The `evaluation` key still gives one writer per minute. |
| Both evaluators miss a minute, or the metrics store is unreachable | No evaluation row for that minute, so it is not counted. Streaks continue from the last counted minute. |
| Service has no requests in the window | Nothing changes. |
| Push errors or gets no answer in 10 s | Send SMS. Both attempts are logged. |
| Push and SMS both fail | Logged as failed. The escalate timer still runs. |
| Schedule lookup fails | Logged as failed, with no person. Nobody is paged at that level. The escalate timer still runs and moves on to the next level. |
| Push timed out but was delivered and acked | The timed-out attempt may have no provider reference, so the ack may not match any row. Escalation continues. See open questions. |
| Ack webhook lost | Escalation continues to the next level. |
| Resolved notice fails | Logged. Not retried. |
| Duplicate or late escalate message | The escalate check finds it stale and does nothing. |
| Timer queue loses a message | Not handled. See open questions. |
| Crash after commit, before a page is sent | Not handled. See open questions. |
| Postgres is down | Nothing is evaluated, paged or acked. See open questions. |

### Open questions

- A page or escalate message lost after commit, whether from a crash or a dropped timer, is never retried. Is a sweep for pending work needed?
- A Postgres outage stops detection and paging. Is a fallback needed?
- The 10-second push timeout is a guess. It must be checked against the provider's real response times.
- Does the provider return a reference when a push call times out? If not, an ack for a delivered push that timed out cannot be matched, and escalation continues without it.
- The exact wording and layout of the page are not set here.
