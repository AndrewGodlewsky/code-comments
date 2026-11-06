# Offline trajectory diagnostic

The runner exercises three-step trajectories in disposable Docker containers.
It supports a known-answer **oracle** and a **no-op** adapter. Neither calls a
model. Passing this diagnostic shows that the machinery can carry, grade and
record changes; it is not evidence that comments improve coding.

This is an incomplete checkpoint for [#7](https://github.com/AndrewGodlewsky/code-comments/issues/7).
The full issue requires a real coding-agent runner and its acceptance review.
The user's offline-only direction remains in force.

## Run locally

Use Python 3.12+, Docker with a running Linux engine, and this immutable image.
The one-time pull needs network access; candidate containers have no network.
No Python packages or model credentials are needed.

```text
docker pull python@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54
python -B -m evaluation.runner --destination ../diagnostic-run --seed 17
python -B -m evaluation.runner --destination ../diagnostic-run --seed 17 --resume
```

Choose a new, disposable output directory outside the repository. It contains
public fixture answers in step records. Never expose it to a trial agent.
`--stop-after 1` pauses after one newly executed step; resume with the same seed,
mode and adapter. `--stop-after 0` writes only the manifest without Docker.
`--adapter noop` deliberately fails each trajectory at step 1; exit code 1 is
expected. Exit code 0 means a successful or intentionally paused diagnostic;
inspect `complete`. Configuration/record errors exit 2.

`--mode controlled` puts the current matched facts in the recorded prompt for
inline/external conditions; the baseline receives no added facts. The default
`discovery` mode reads the same guide, task, source and optional external file
through a scripted tool call. Actual returned text is recorded. This tests the
observation path, not autonomous discovery. Adapters do not reason over prompts.
Conditions are shuffled with the recorded seed and start independently. Later
steps inherit their condition's preceding code, with no earlier process/session.

The host supplies currently valid reference facts, retires the retry cap at
step 2, and adds delay rationale at step 3. This is oracle context maintenance.
It does not test a comment writer, maintenance skill, stale-comment arm,
token-equivalent prompts, or model use of either placement.

## Records and recovery

`manifest.json` pins the run ID, adapter, exposure mode, seed/order, image digest,
command limit and fixture/tool source hashes. Each `step-<condition>-<n>.json`
contains inputs, prompt, actual read/write observations, resulting code, patch,
grading, errors and timing. Hash envelopes detect damage, not a malicious host
that rewrites both data and hash. Files are created exclusively and flushed.
Resume validates configuration/source hashes and saved trajectory prefixes before
new work; it refuses records after a gap or terminal failure. All attempts,
including failures, contribute to summaries; later steps remain unattempted.
Success requires all three steps, not merely the last successful check.
Conditions must also form one execution prefix: later conditions cannot have
records while an earlier condition is incomplete. Independent review caught a
missing-record replay that per-condition checks alone allowed. Loss of a trailing
record with no later evidence is not detectable by these local checksum files;
durable provider reconciliation/idempotency is still future work.

`run.lock` excludes concurrent writers. `inflight.json` is flushed before an
attempt. Interrupted attempts or leftover locks block automatic resume: inspect
the run and task-owned `cc-eval-*` containers before manual recovery. Do not erase
guards to replay ambiguous work. Start a new run after preserving old evidence.
This does not prove duplicate-billing protection for a future provider.

Model calls/cost are zero; token counts and infrastructure monetary cost are null.
Attempt wall time includes setup/cleanup and grading, with command/grading detail;
it excludes image download and test overhead. There is no paid provider or spending
override. Adding one requires #6 and further ledger/limit validation.

## Isolation and grading limits

Each edit and grading phase gets a separate unprivileged container, pinned image,
read-only root, no host mounts/socket/network, dropped capabilities,
no-new-privileges, one CPU, 256 MiB memory, 64 processes and bounded tmpfs storage.
Commands time out after 10 seconds by default (maximum 30); output is limited to
256 KiB. Snapshots accept at most 64 UTF-8 files, 16 KiB each and 32 KiB total,
reject links/traversal/special files, and are never extracted onto the host.
These are small-fixture limits, not a general repository environment.

Docker cannot copy tmpfs through `docker cp`; integration testing caught an empty
snapshot. The current helper stops candidate processes and streams an archive
inside the container. A probe verifies stopped writers and stable contents.
Stopping a process can capture a partially written file; grading must evaluate
it without silent repair. See Docker's
[copy limitations](https://docs.docker.com/reference/cli/docker/container/cp/).

Expected outcomes remain on the host. Another container runs candidate calls
and returns values/types. PASS text, exits, malformed output, wrong return types
and lookalike exceptions do not establish success. However, candidate code shares
an interpreter with the collector and can tamper with frames or serialization.
The collector is not tamper-proof. Stronger adversarial grading remains required.
Docker shares its kernel with its host; this is a local development boundary,
not a multi-tenant security guarantee. Review
[Docker's security model](https://docs.docker.com/engine/security/) before extension.

All fixture assets are public. The oracle deliberately writes the current known
solution; this exception must not apply to real-agent workspaces. Future tasks,
reference files, Git history and host evaluator files are not mounted. No
held-out or contamination-free result is claimed.

## Verification and next work

```powershell
$env:CODE_COMMENTS_DOCKER='1'
python -B -m unittest discover -s tests -v
```

Without the opt-in variable, Docker tests are skipped. Linux CI runs them with the
pinned image and trusted fixture audit. Tests cover resource/time boundaries,
snapshot safety, wrong-type grading, temporal context, failed trajectories,
pause/resume, configuration drift and damaged/locked/in-flight records.

Remaining #7 work includes a real agent adapter/session boundary, provider usage
and total-budget accounting, independently validated natural discovery and fact
exposure, stronger grader tamper tests, broader corpus integration, and full
independent acceptance review. #8 owns corpus admission; #9 placement trials;
#10 the skill. Dependencies remain in the [roadmap](../roadmap.md).
