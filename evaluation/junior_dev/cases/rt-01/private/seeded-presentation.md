Notes (read these first, or after, either way): so the main thing is the presence map in redis (the room hash / presence:{docId}, one field per conn, with userId nodeId lastSeen and the cursor stuff pos rev seq in it) and the WS boxes write their own fields, though the sweeper on any server can delete other people's, and there's also the pub/sub topic with the same name presence:{docId} which is NOT ops:{docId}, that one is edits, and edits keep going op -> node -> doc service -> Postgres -> ops:{docId} like now, and cursors never go to the doc service or Postgres. Also the client keeps userId -> connIds so two tabs is one avatar, and the avatar goes when the last connId goes. Timing for crash is 30 + 5 = 35 worst case, under the 45: lastSeen can't be later than the crash since nobody refreshes after it, then the 30 s stale threshold, then up to 5 s to the next sweep. Key EXPIRE 120 s is refreshed on every write so nothing sticks around. No sticky LB needed because everything fans out through redis.

```mermaid
sequenceDiagram
    participant C1 as client1 (Alice)
    participant S1 as WS-1
    participant RD as redis
    participant S2 as Srv2
    participant C2 as client 2
    Note over S2: crash - no cleanup
    loop 5s
        S1->>RD: HGETALL room hash
        S1->>RD: HDEL connB
        RD-->>S1: 1
        S1->>RD: PUBLISH leave connB userB
        RD-->>S1: leave
        S1-->>C1: leave
    end
    Note right of S1: stale means lastSeen > 30 s. if HDEL gives 0 someone else got it, don't publish
    C1->>S1: cursor
    Note left of C1: pos rev seq, seq +1 each time, client sends max every 50ms
    alt fast
        Note over S1: under 50ms since last accepted for this conn, drop, silently
    else ok
        S1->>RD: PUBLISH cursor
        RD-->>S2: cursor
        RD-->>S1: cursor
        S2-->>C2: cursor
        S1->>RD: HSET cursor into presence key
    end
    Note right of RD: the HSET of cursor is max 1/sec per conn, and the last one gets flushed at the end of the 1 s window so the final spot is saved, that's what new joiners see for idle people
    Note over S1: own publish comes back, send to the other local sockets on the doc but not the sender conn
    C1->>S1: open D
    S1->>RD: SUBSCRIBE (if first local socket on D)
    S1->>RD: HSET connA lastSeen etc + EXPIRE 120
    S1->>RD: HGETALL
    RD-->>S1: entries
    S1-->>C1: snapshot
    S1-->>C1: buffered then live
    S1->>RD: PUBLISH join
    RD-->>S2: join
    S2-->>C2: join
    Note left of S1: buffering starts right after subscribe, before HGETALL. stale (over 30s) entries skipped + HDELed in snapshot
    Note over C2: drop if seq not higher than last seen for that conn (also snapshot cursor vs buffered). rev ahead of appliedRev - don't draw, hold latest, draw once that rev is applied. rev behind - transformPosition(pos, rev, appliedRev), HistoryGone means drop it
    loop 10s
        S1->>C1: ping
        C1-->>S1: pong
        S1->>RD: HSET lastSeen + EXPIRE
    end
    C1-xS1: close (tab 2, connA2)
    S1->>RD: HDEL connA2
    S1->>RD: PUBLISH leave
    RD-->>S2: leave
    S2-->>C2: leave
    S1->>RD: UNSUBSCRIBE if none left on D
    Note over C2: Alice still shown if connA still there. Bob reconnecting goes anywhere, new connId, does the open thing again
```

Also, the gateway closes sockets after 20 s without a pong and then does the same HDEL plus leave. A clean close is immediate, so under 2 s. If nobody is on the doc to sweep, the next open's snapshot cleans stale entries, and the EXPIRE handles the rest. Events are applied by connId so replaying a buffered join is harmless. Bob's old entry, if he reconnected, lingers until swept, but he's grouped by userId so he isn't shown twice.
