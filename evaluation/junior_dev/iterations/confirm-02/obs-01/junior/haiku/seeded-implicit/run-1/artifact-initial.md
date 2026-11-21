### Error-rate paging

Components: evaluator (x2), incident manager, Postgres, timer queue, schedule service, paging provider.

```mermaid
sequenceDiagram
    participant Evaluator
    participant IncidentManager
    participant Postgres
    participant TimerQueue
    participant Schedule
    participant Pager
    participant Engineer
    Evaluator->>IncidentManager: breach
    IncidentManager->>Postgres: incident
    IncidentManager->>Pager: page
    Pager->>Engineer: page
    TimerQueue->>IncidentManager: escalate
    IncidentManager->>Schedule: lookup
    IncidentManager->>Pager: page
    Engineer->>Pager: ack
    Pager->>IncidentManager: ack
    Evaluator->>IncidentManager: clear
    IncidentManager->>Pager: resolved
```

Notes:
- The evaluator checks the error rate every minute and opens an incident after 3 breaches (above 2%, 500 request minimum).
- Dedup on service + rule.
- Escalation: primary, secondary, EM, 5 min apart. Ack stops it.
- Auto-resolves after 10 min below 1%. Resolved notice goes out.
- Push with SMS fallback. Failures don't block escalation.
- Two evaluators are coordinated through Postgres.
- page_log table.
