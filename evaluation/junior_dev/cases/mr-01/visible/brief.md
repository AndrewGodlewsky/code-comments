## Failover plan: Region A to Region B

Our invoicing SaaS runs active-passive across two cloud regions: A serves all traffic, B is a warm standby. I need a plan for failing over to B when A is lost, without ever having two writable databases.

**What exists today**

- Each region has a stateless web/API tier behind a regional load balancer: 12 instances in A, 2 warm in B.
- PostgreSQL primary in A, with an asynchronous streaming replica in B. Each time the replica receives WAL from A, it records its replay lag (how far its replay trails A at that moment), typically under 5 s.
- Background jobs are rows in a `jobs` table in that database; workers poll it and mark a row `running` while working on it. B's workers are scaled to zero.
- Sessions live in a Redis cluster in each region, not replicated between regions.
- Users reach the app through one DNS name managed by a global traffic manager, with a 60 s TTL.

**Fixed requirements**

- Targets: RPO 30 s; RTO 15 min, measured from when on-call starts the failover.
- Detection: external probes call A's `/healthz` every 10 s from three locations; A is down when 2 of the 3 see 3 consecutive failures. That pages on-call and never fails over by itself.
- Failover is started by a person running a single failover command. No automatic promotion.
- Before promoting, the command checks B's last recorded replay lag (the value from when B last received WAL from A, so it does not grow while A is down). Over 30 s, it stops, and continues only with an explicit accept-data-loss override.
- A must be fenced before B's database is promoted. Fencing has to work even when we cannot reach A's cloud API or network at all: a partitioned A that is still running must not keep taking writes.
- B's workers start only once B's database is writable. DNS moves to B only after B's app is scaled up and passing its health check.
- Users signed in at failover time will have to sign in again; that's accepted.
- No automatic failback. A's old database is never reused as primary: when A returns it is rebuilt as a replica of B, and moving back is a separate planned switchover.

**What I want**

A Mermaid flowchart of the failover path from detection to traffic on B, with short notes before or after it. Make clear what triggers each step, where the active-region record is kept, what happens to jobs mid-run in A, and how a failed or interrupted run is handled.
