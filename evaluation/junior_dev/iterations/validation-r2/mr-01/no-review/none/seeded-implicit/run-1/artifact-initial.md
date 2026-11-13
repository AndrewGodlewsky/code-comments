# Failover plan

Pieces: health probes, on-call, failover command, control store, Postgres (A primary, B replica), job workers, Redis, global traffic manager.

```mermaid
flowchart TD
    Probes --> OnCall[On-call]
    OnCall --> Cmd[Failover command]
    Cmd --> Lock[Take lock]
    Lock --> Fence[Fence A]
    Fence --> Lag[Lag check]
    Lag --> Promote[Promote B]
    Promote --> Jobs[Fix up jobs]
    Jobs --> Scale[Scale up B]
    Scale --> Health[Health check]
    Health --> DNS[Switch DNS]
```

Notes:
- Lag check against the RPO, with an override available.
- Fencing goes through the control store, and the apps respect it.
- Jobs need to be idempotent.
- The command logs its progress and can be resumed or aborted.
- Sessions don't carry over.
- Failback is a separate planned job; A's DB gets rebuilt.
