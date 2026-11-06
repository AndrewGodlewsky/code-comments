# Offline longitudinal runner design

Issue #7, branch `agent/7-longitudinal-runner`. This implements the offline
execution boundary and deterministic trajectory recorder before any model adapter
or paid campaign. #7 remains open for any acceptance criteria not demonstrated;
downstream claims and model choice remain gated by #6/#9. No API keys are loaded.

## Execution boundary

Use the installed Docker Desktop Linux engine and an official Python 3.12 image,
resolved to a content digest in configuration. Each edit gets a new unprivileged
container with no network, no host mounts, read-only root, dropped capabilities,
no-new-privileges, bounded writable tmpfs, CPU/memory/PID caps and host-enforced
command deadlines/output caps. Copy only bounded UTF-8 workspace files through
stdin. Export snapshots through a fixed isolated Python helper; reject symlinks,
special files, traversal, Git metadata and oversized output. Clean up only named
task containers on success, failure and interruption. Docker is a local isolation
boundary, not a defense against all kernel exploits or a public multi-tenant service.

The trusted coordinator and grader stay on the host. Candidate code runs only
in a separate grading container. Host-side assertions compare returned values
and exception names against hand-derived expectations; never trust a candidate's
claim that tests passed. Do not send expected answers, later requests, reference
files, repository history, credentials or the fact ledger into an agent container.
The development oracle adapter deliberately supplies the current known solution
as its edit to verify plumbing; label its output as oracle replay, not inference.

## Trajectories and recording

Build on the authored retry-policy development fixture. Randomize the order of
the three paired conditions with a recorded seed. Support controlled fact exposure
and natural file discovery as distinct modes. Preserve workspace snapshots within
a trajectory; reset processes and state between edits and between conditions.
Apply currently available reference facts, including retirement of the legacy cap,
equally in inline/external arms. The baseline receives no added inventory.

An immutable manifest records run ID, seed/order, adapter, mode, image digest,
fixture and runner hashes, limits and zero model-spending policy. Write each
step as a separate record with prompt, actual read outputs, input/output snapshots,
patch, grading result, elapsed time and usage fields. Model usage is not applicable
for deterministic adapters; infrastructure monetary cost is unpriced, not zero.
Use strict all-step success and mark later unattempted steps separately from failure.

Exclusive run locks prevent concurrent writers. Completed step records are reused
on resume, never rerun. A durable inflight marker means interruption is ambiguous:
fail closed on resume and require inspection/new run rather than silently retrying.
Allow a controlled stop between steps for a reproducible resume test. Record failed
grading and timeouts; do not retry or repair them into unassisted success.

## Verification and limits

Unit tests cover configuration, isolation options, safe paths, deterministic order,
state/resume rules and summaries. Opt-in Docker tests exercise actual host-canary,
private-file, network, root-write and symlink probes, excessive output, timeouts,
candidate spoofing, successful oracle replay, failure propagation and resume.
CI runs offline tests and Docker integration on a Linux runner; public workflow
uses pinned official actions. No model campaign or experiment budget is implied.

The fixture is public and small. Replay validates runner behavior, not comment
benefit, writer quality, natural model tool use or pilot validity. Real agent
integration, general repository grading, token/cost adapters and a representative
corpus remain explicit gates rather than simulated successes.
