## Live cursors and presence in the editor

We're adding Google-Docs-style presence to the document editor: an avatar list of who is in the document, and a coloured caret for every other user, both updated live.

Before you start, read `existing/gateway.md` (how gateway nodes, the edit path and Redis work today) and `existing/editor-protocol.ts` (what the client editor already has). Build on them. Don't add new infrastructure, and don't change the edit path or the load balancer. People in the same document will often be connected to different gateway nodes.

Fixed requirements:

- **Presence list.** The list is per user, not per tab. A user with two tabs open appears once, and disappears only when their last connection to the document goes away. A client that joins a document gets the full current list straight away, then live changes. This replaces the Postgres polling described in the gateway doc.
- **Cursors on join.** A user who has just joined must see everyone's caret immediately, including users who are idle and not moving.
- **Cursor rate.** Clients send at most one cursor update every 50 ms. The server enforces this per connection and silently drops anything faster.
- **Cursors are ephemeral.** They never go through the document service and are never written to Postgres.
- **Revisions.** A caret position only means something at a particular document revision, so every cursor update carries the sender's applied revision. A client must never draw a caret at a revision it has not applied yet: it holds that cursor and draws it once it has applied that revision. Positions from older revisions are moved forward with `transformPosition`, following its contract.
- **No backwards jumps.** A receiver must never move a caret back to a position the sender reported before the one already shown, even if messages arrive out of order.
- **Leaving.** When a tab closes cleanly, other users see the change within 2 s. When a gateway node dies, its users must disappear from everyone else's list within 45 s, and nothing may be left behind in Redis for good.

Deliverable: a **Mermaid `sequenceDiagram`**, with short notes before or after it. Show one user joining a document on one node while another user is already in it on a different node, then a cursor move, the heartbeat, a clean leave and a node crash. Make clear where each piece of state lives and what refreshes or removes it.
