// Client side: what the editor already has.

// Client -> server
type Open   = { t: "open"; docId: string };
type SendOp = { t: "op"; docId: string; baseRev: number; ops: Op[] };

// Server -> client
type Ack      = { t: "ack"; rev: number };
type RemoteOp = { t: "remote_op"; rev: number; ops: Op[] };

// The last revision this editor has applied. It only moves forward.
declare let appliedRev: number;

// The editor keeps the ops of the last 500 revisions.
// Maps a character offset that was valid at fromRev to the same place at
// toRev (fromRev <= toRev <= appliedRev).
// Throws HistoryGone if fromRev is older than the kept history.
// Callers must drop the position when it throws.
declare function transformPosition(pos: number, fromRev: number, toRev: number): number;