# Gateway nodes (current system)

- Browsers connect over WebSocket to `/ws`. The load balancer spreads new
  connections round-robin across the gateway nodes (6 today, autoscaled).
  There is no stickiness by document: two people in the same document are
  usually on different nodes.
- On connect, the node checks the session cookie and assigns a `connId`
  (random UUID, new for every connection). `userId` comes from the session.
  One user with two tabs open has two connections and two connIds.
- Each node keeps, in memory only, `localSockets: Map<docId, Set<Conn>>`.
- Liveness: the node sends a WebSocket ping every 10 s. If no pong comes
  back within 20 s, it closes the socket.
- Nodes can be killed at any time (deploys, scale-in, crashes). A killed
  node does no cleanup at all.

## Edit path (do not change)

1. Client sends `op {docId, baseRev, ops}` to its node.
2. The node forwards it over HTTP to the document service.
3. The document service transforms it, appends it to Postgres, assigns `rev`,
   and publishes `{rev, ops}` on the Redis pub/sub channel `ops:{docId}`.
4. Every node subscribes to `ops:{docId}` while it has at least one local
   socket on that document, and forwards `remote_op` to those sockets.

## Shared infrastructure

- Redis 7 (one primary plus a replica), already used for `ops:{docId}` and
  available for presence work. Pub/sub only delivers to current subscribers;
  it stores nothing.
- Postgres, owned by the document service.

## Presence today

The "who's here" list is a Postgres table that is updated on open and close
and polled by clients every 30 s. Users on crashed nodes stay listed until a
nightly job removes them. There are no cursors.