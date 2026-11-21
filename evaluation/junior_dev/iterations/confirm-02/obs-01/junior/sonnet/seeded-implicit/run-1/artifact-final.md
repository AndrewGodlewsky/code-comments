### Error-rate paging

Today a cron script only emails a shared inbox that nobody reads at night. This replaces it with paging. Two identical evaluators check each service's error rate every minute. After 3 breaching minutes in a row, the incident manager opens an incident and pages the primary on-call person. If nobody acknowledges, 5-minute timers page the secondary and then the engineering manager. The incident resolves after 10 quiet minutes. Postgres holds all state, so either evaluator can fail and nothing is lost.

Terms:
- Evaluator: a scheduled job, run as two identical instances, that reads the metrics store (a time-series database the API gateway writes per-minute request and 5xx counts to) and decides whether a service is breaching or recovered.
- Breach: one evaluation where the trailing 5-minute error rate (5xx / requests) is above 2% and that window holds at least 500 requests.
- Streak: a count of consecutive evaluations (breaching, or below 1%), kept in an alert_state row per (service, rule). It counts evaluations, not wall-clock time.
- Rule: the alert rule being checked. The incident limit applies per (service, rule).
- Incident manager: the service that owns incidents, pages, timers and acks.
- Timer queue: a queue that delivers a message after a delay. Here it carries escalate(incident id, level), where level is the level to page when the timer fires.
- Levels: 1 primary, 2 secondary, 3 engineering manager (EM, the last level).
- Schedule service: says who is on call for a service and level right now. Rotations change at 09:00, so it is asked at every page.
- Paging provider ("Pager"): sends a push notification or SMS and calls our webhook when someone taps Acknowledge. We pass it an incident id and person with each send, and it echoes them back in the webhook (assumed, see open questions).

```mermaid
sequenceDiagram
    participant Evaluator
    participant IncidentManager
    participant Postgres
    participant TimerQueue
    participant Schedule
    participant Pager
    participant Engineer
    Evaluator->>Postgres: one transaction: claim (service, rule, minute) and update streaks
    Evaluator->>IncidentManager: breach (every breaching minute once streak is 3 or more)
    IncidentManager->>TimerQueue: escalate(new incident id, level 2) due in 5 min
    IncidentManager->>Postgres: insert incident (one unresolved per service+rule); if one exists, only record the breach
    IncidentManager->>Schedule: who is on call for level 1
    IncidentManager->>Pager: page (push, else SMS)
    IncidentManager->>Postgres: page_log row
    Pager->>Engineer: page
    TimerQueue->>IncidentManager: escalate(incident, level N)
    IncidentManager->>Postgres: read incident; stop if acked or resolved
    IncidentManager->>Postgres: set current level N
    IncidentManager->>TimerQueue: escalate(incident, level N+1) due in 5 min (only if N is 2)
    IncidentManager->>Schedule: who is on call for level N
    IncidentManager->>Pager: page (push, else SMS)
    IncidentManager->>Postgres: page_log row
    Engineer->>Pager: ack
    Pager->>IncidentManager: ack webhook (incident, person)
    IncidentManager->>Postgres: mark acked, only if still open
    Evaluator->>IncidentManager: clear (every minute once 10 consecutive minutes below 1%)
    IncidentManager->>Postgres: mark resolved
    IncidentManager->>Pager: resolved notice to everyone successfully paged in page_log
```

Steps:
1. Evaluate (every 60 seconds, both evaluators). Each evaluator tries to insert a row for (service, rule, minute); the unique key lets one win. The winner updates the streaks in the same transaction, then sends breach or clear to the incident manager. The loser does nothing. So there are no double incidents or pages, and if one evaluator is down the other still wins. No lock or standby is needed.
   - Streaks: a breach adds one to the breach streak and zeroes the quiet streak. A rate below 1% (zero requests counts as below 1%) adds one to the quiet streak and zeroes the breach streak. A rate from 1% to 2%, or above 2% with fewer than 500 requests, resets both.
   - Sending: breach is sent on every breaching minute once the breach streak is 3 or more. Clear is sent on every minute once the quiet streak is 10 or more. The call is direct. If it fails, the evaluator logs it and the next minute repeats it.
   - Crash: if the winner dies before its transaction commits, nothing was claimed or counted. That minute is skipped and the streak continues next minute, so detection is at most a minute late. If it dies after the commit but before sending, the next minute sends again.
2. Open (incident manager gets breach). Every incident manager action below is safe to repeat. If an unresolved incident exists for (service, rule), go to step 3. Otherwise it generates the incident id, queues escalate(id, level 2) due in 5 minutes, inserts the incident, looks up the level 1 person, pages them and writes page_log. Postgres allows only one unresolved incident per (service, rule); if two inserts race, the loser stops and its timer finds no incident and does nothing.
   - Failure: if the manager dies before the insert, the next minute's breach opens the incident with a new id. If it dies after the insert but before paging, the next breach finds an unresolved incident with no page_log rows and pages level 1 then. The level 2 timer still runs either way.
3. Duplicate breach. A breach while an unresolved incident exists is only recorded on it (breach count, last breach time) and pages nobody. This covers the 4th and later breaches, and a new streak of 3 after a reset while the incident is still open. A breach after resolution opens a new incident.
4. Escalate (timer fires with a level). The manager reads the incident and stops if it is acked or resolved. Otherwise it sets current level to the timer's level and queues the next timer, which is level 3 after level 2; level 3 queues nothing. Then it looks up who is on call for that level and pages them. Timers are never cancelled; reading the incident when they fire avoids cancellation logic and races. After the EM is paged, nothing more is sent until an ack or resolution.
   - Failure: the next timer is queued before the page is sent, so a failed page never stops or delays escalation. If the schedule lookup fails or nobody is on call, the manager writes a page_log row with no person, pages nobody at that level, and the next timer fires as normal.
5. Page (used by steps 2 and 4). The manager calls the push API, and calls the SMS API only if push returns an error. The provider does not decide this. It writes one page_log row per attempt.
6. Ack (webhook says which incident and person). The manager sets acked_by and acked_at and state acked, only if the incident is still open. A second ack, or an ack after the incident resolved, is ignored. Any ack stops escalation. An acked incident can still resolve.
7. Resolve (incident manager gets clear). It marks the incident resolved (nothing to do if none is unresolved). Then it sends "resolved" to everyone in page_log who was successfully reached by push or SMS. People whose pages all failed, and lookup-failure rows, are skipped. A failed resolved notice uses the same push-then-SMS rule, is logged, and is not retried; the incident stays resolved. If it resolves before an ack, the next timer sees "resolved" and escalation stops.

Data in Postgres:
- alert_state: per (service, rule), the breach streak and the quiet streak.
- Minute claim: one row per (service, rule, minute), unique.
- Incident: id, service, rule, state (open, acked, resolved), current level, acked_by, acked_at, opened_at, resolved_at, breach count, last breach time.
- page_log: one row per page attempt: incident, level, person, channel (push or SMS), result, provider reference, time. Written by the incident manager after each attempt. It decides who gets the resolved notice.

Open questions:
- Does the paging provider echo a reference we send with each page in its ack webhook? If not, the webhook cannot name the incident and person, and the plan needs another way to match acks.
- An ack after resolution is ignored (assumed, not confirmed with the team).