# Failover plan: Region A to Region B

This plan covers a person-started failover from detection to traffic on B. Normally region A serves all traffic and region B is a warm standby: a small, always-running copy of the stack that is scaled up when needed. The one hard rule is that two writable databases must never exist at once.

In short: monitoring pages on-call, and on-call runs one command. The command locks the run in a small external record, waits for A to fence itself, promotes B's database, then recovers jobs and scales up B's app in parallel. When B is healthy, it moves DNS to B. The plan rests on one new component, the active-region record, described in section 1.

Terms used below:
- **RPO** (recovery point objective): the most data we accept losing, here 30 s.
- **RTO** (recovery time objective): the longest we accept being down, here 15 min, counted from when on-call starts the failover.
- **WAL**: PostgreSQL's write-ahead log, the stream of changes that B's replica receives from A's primary.
- **Replay lag**: how far the replica's replay trails A. B records it each time it receives WAL from A.
- **Fencing**: making sure A's database can no longer accept writes.
- **Compare-and-set (CAS)**: an update that succeeds only if the record still holds the value the writer last read. A writer with stale data fails and must re-read.
- **Lease**: a permission that expires after a fixed time (its TTL) unless the holder renews it.
- **Epoch**: a counter that rises on every change to the active-region record.

## 1. The active-region record

This is a small, strongly consistent key-value store that supports compare-and-set and expiring leases. It lives **outside both regions**, in a third region or provider. It does not exist today and has to be added. Neither region's database, Redis or DNS can hold it. If it lived in A, it would be lost with A, and A's fence would then depend on A being reachable.

It holds one document:

| Field | Meaning |
|---|---|
| `active` | `A` or `B`, the region allowed to hold the writable database |
| `epoch` | Integer, incremented on every transition. A writer holding an old epoch loses its compare-and-set. |
| `state` | `A_ACTIVE`, `FENCING`, `B_PROMOTED`, `B_ACTIVE` |
| `run` | Run id, start time, operator, whether the data-loss override was used, and progress flags (`requeued`, `workers_started`) |

The record does three jobs.

1. **Lock.** The command changes the record with compare-and-set, so two people running the command cannot both proceed.
2. **Fence.** See section 2.
3. **Resume point.** Every step reads the record to learn what is already done. This is how an interrupted run continues (section 5).

## 2. How A is fenced when A is unreachable

The command cannot rely on reaching A's API or network, so A fences itself.

- A's database host runs a lease agent. While the record says `active=A`, the agent renews a write lease every 10 s. Each lease lasts 30 s (the TTL).
- If the agent cannot renew, or reads a higher `epoch` or `active=B`, it sets the primary read-only and then stops Postgres. A local watchdog stops Postgres if the agent itself hangs.
- A restarted A database comes up read-only. It takes writes only after it reads `active=A` from the record.
- The command first moves the record to `FENCING` (with `active=B`), which ends all renewals. It then waits for the TTL plus a 5 s clock-skew margin, 35 s in all. After that wait, A is fenced whether it is partitioned, hung or healthy. In parallel, the command makes a best-effort stop through A's cloud API. Its failure is logged and ignored.
- Only after that wait does the command promote B.

The fence holds because a partitioned A cannot reach the record, so it cannot renew its lease, and its database stops itself when the lease runs out. This is why promotion waits for lease expiry and does not just call A's API.

## 3. Flowchart

How to read it: the top path is detection and the human decision. The middle is the lock, fence and promotion. After promotion the flow splits in two: job recovery on one branch, app scale-up and the DNS move on the other. Both must finish before the run is done. If a run dies, rerunning the command re-enters at the top, and the record sends it to the right step.

```mermaid
flowchart TD
    D["Probes: 2 of 3 locations see 3 consecutive failures of A /healthz"]
    D --> PG["Page on-call. No automatic action."]
    PG --> CMD["On-call runs the single failover command. RTO clock starts."]

    CMD --> PRE{"Read the record: what is the state?"}
    PRE -- "B_ACTIVE" --> NOP["Stop: nothing to do"]
    PRE -- "FENCING (resume)" --> FENCE
    PRE -- "B_PROMOTED (resume)" --> REC1
    PRE -- "A_ACTIVE" --> LAG{"B last recorded replay lag over 30 s?"}
    LAG -- "yes" --> OVR{"Operator passes accept-data-loss override?"}
    OVR -- "no" --> ABORT["Stop. Nothing changed. A still active."]
    OVR -- "yes" --> LOG["Record override in run field"]
    LAG -- "no" --> CAS
    LOG --> CAS

    CAS["Compare-and-set record: state=FENCING, epoch+1, active=B. Acts as the lock."]
    CAS --> FENCE["Fence A: lease renewals stop. Best-effort stop via cloud API, failure ignored. Wait lease TTL 30 s + 5 s margin."]
    FENCE --> PROM["Promote B database"]
    PROM --> WR{"pg_is_in_recovery is false and a test write succeeds?"}
    WR -- "no" --> RETRY["Retry promote. Persistent failure: escalate (section 5)"]
    RETRY --> PROM
    WR -- "yes" --> REC1["Record: state=B_PROMOTED"]

    REC1 --> JOBS["One transaction: set every jobs row with status running back to pending. Skipped if the record says requeued or workers_started."]
    JOBS --> WRK["Scale B workers from 0 and start them"]

    REC1 --> SCALE["Scale B app tier from 2 to 12 instances, pointed at the now-writable B database"]
    SCALE --> HC{"B app health check passes, including a database write probe?"}
    HC -- "no" --> HCR["Keep retrying and scaling. DNS stays unchanged."]
    HCR --> HC
    HC -- "yes" --> DNS["Traffic manager: point the DNS name at B"]

    WRK --> DONE
    DNS --> DONE["Record: state=B_ACTIVE. Traffic reaches B within the 60 s TTL. Users sign in again."]

    INT["Command dies or any step errors"] -. "rerun the same command" .-> CMD
```

What triggers each step:

| Step | Trigger |
|---|---|
| Page | The probe rule, automatic. It pages and does nothing else. |
| Everything from the command onward | A person running the command. Nothing after it needs another human action, except the override prompt and escalations. |
| Lag check | The command's first action, before any change. It runs only on a fresh run (`A_ACTIVE`), not on a resume. |
| Fence | The compare-and-set to `FENCING` succeeding. |
| Promote | The fence wait finishing. |
| Requeue and workers | `B_PROMOTED` recorded, which means the database is verified writable. |
| App scale-up | `B_PROMOTED` recorded. It runs in parallel with the job steps. |
| DNS | The B health check passing. |

## 4. Jobs running in A at failover

Jobs are rows in the `jobs` table. A worker marks a row `running` while it works on it.

- Rows that were `running` in A are copied to B's database as `running`, because the replica knows nothing about A's workers. Those workers are fenced and gone, so nothing is actually working on those rows.
- The requeue step sets all `running` rows to `pending` in one transaction. It runs after promotion and **before** B's workers start, so no worker sees a stale `running` row. The command records `requeued` after the transaction commits, and `workers_started` just before it starts the workers. A rerun skips the requeue once either flag is set, because by then a `running` row may be real work on B. If the command dies after the transaction but before the `requeued` flag is written, the rerun requeues again, which is harmless because no worker has started.
- Jobs are therefore at-least-once. A job that finished its side effect in A just before the loss, or whose completion was not replicated, will run again. Job handlers that send email, charge a card or call external systems need idempotency keys. This is a requirement on the job code, not something the failover can provide.
- Jobs enqueued or completed in A within the final unreplicated WAL are gone. This is the RPO window. After failover, reconcile from the invoice records and customer-visible state.

## 5. Failed or interrupted runs

The command is idempotent. Rerunning it reads the record and resumes at the first incomplete step.

| Interrupted at | State | Handling |
|---|---|---|
| Before the compare-and-set | `A_ACTIVE` | Nothing changed. Rerun or abandon. |
| Lag over 30 s, no override | `A_ACTIVE` | Stops cleanly. Rerunning with the override is the only way forward. |
| During fence wait | `FENCING` | A is already fenced or will be within the TTL. Rerun, which waits the fence period again. Never promote before the wait ends. |
| Promote fails or hangs | `FENCING` | Retry. If B's database cannot be made writable, no region is writable, but A's data is intact. Only a human can decide to reactivate A, by deliberately moving the record back to `active=A` with a new epoch. The command never does this on its own. |
| After promote verified | `B_PROMOTED` | Roll forward only. The command never demotes B. Rerun to finish requeue, workers, scale-up and DNS. |
| Health check never passes | `B_PROMOTED` | DNS stays unchanged. Fix B or scale further, then rerun. Users see A's outage, but no second writer exists. |
| DNS update fails | `B_PROMOTED` | Retry. The update is idempotent. |
| Two operators run it at once | any | The second one loses compare-and-set and attaches to the run in progress. |

Once the record leaves `A_ACTIVE`, a returning A cannot take writes. It stays read-only until it is rebuilt as a replica of B. A's old database is never reused as primary. Failing back is a separate planned switchover, with its own plan.

## 6. Time budget

These are estimates to confirm in a rehearsal, not measurements. The budget starts when on-call runs the command. The app scale-up path is the longest, so the job steps, which run alongside it, add nothing to the total.

| Step | Estimate |
|---|---|
| Preflight, lag check, compare-and-set | about 10 s |
| Fence wait | 35 s |
| Promote and verify | 30 to 60 s |
| App scale 2 to 12 and health check | 3 to 6 min |
| DNS change and TTL expiry | about 90 s |
| **Total** | **about 6 to 10 min, against a 15 min RTO** |
| (in parallel with scale-up) Requeue and workers | about 1 min |

Scale-up is the largest item and the main risk to the RTO. Keeping B at 2 instances is a cost choice that the RTO depends on, so rehearse it.

## 7. Caveats

- **The lag value understates data loss.** B records its lag when it last received WAL from A, so the value freezes when A dies. It says nothing about transactions A committed after that moment. Passing the 30 s check does not prove the RPO was met. Have the command print the time of the last WAL receipt, so on-call can see how stale the number is. Treat a pass as "no known violation", not as a guarantee.
- **The record store is a new dependency.** If the command cannot reach it, failover cannot proceed. This is deliberate, because proceeding without it would give up the fence. Run it with its own redundancy.
- **Sessions.** B's Redis starts empty, so every signed-in user must sign in again. Expect a login spike right after DNS moves, and size B's app and auth path for it.
- **Lease TTL trade-off.** A shorter TTL speeds up failover but makes A fence itself on brief blips of the record store. A 30 s TTL with a 10 s renewal interval tolerates two missed renewals.
