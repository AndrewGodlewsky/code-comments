# Learning during development

Maintain useful repository knowledge as part of each task. This is a workflow for
reviewable file changes; it runs when an agent follows these instructions, rather
than as an unattended background service.

## During the task

Capture an explicit user correction or settled decision in its owning file while
the context is available. For observed failures, establish what happened and what
fixed it before promoting an explanation into durable guidance. Label an untested
idea as a hypothesis and keep it with the relevant research or task notes.

Repo-local corrections and evidence-backed guidance updates are part of normal
authorized work. Keep changes scoped to this project. A proposed change to the
user's goals or a costly architectural choice still needs a real decision; an
agent's preference alone does not settle it.

## Before completing a task

1. Review the task's user corrections, failed attempts, verified findings, and
   decisions. Identify lessons that would change a future agent's behavior.
2. Check the existing owner before adding a file or rule. Use the routing table
   below and the [architecture overview](../../architecture.md).
3. Make the smallest useful update. State the triggering situation and required
   action. Retain supporting evidence or rationale where a future reader needs it.
4. Replace obsolete guidance and consolidate duplicates. A one-off workaround is
   not a universal rule; record its applicability and removal condition.
5. Run applicable checks, inspect the diff, and confirm that linked files exist.
   For commits, run `git diff --cached --check` after staging the intended files;
   a working-tree diff alone does not check untracked additions.
   Report the knowledge files changed and any unverified claim that remains.
   If there is no new durable lesson, leave the instructions alone.
6. Complete the [Git workflow](git-workflow.md), including independent review,
   remote `main` integration, issue reconciliation, cleanup, and final audit.
   Report any unresolved gate as incomplete.

Knowledge maintenance is complete when the relevant knowledge was reconciled with
its existing owner, or the agent determined there was nothing durable to add.
Task completion additionally requires the integration and cleanup in step 6.
Producing a session summary does not satisfy either criterion by itself.

## Where each lesson belongs

| Learning | Destination |
| --- | --- |
| User changes product intent or scope | Root `intent.md` |
| System structure or responsibility changes | Root `architecture.md`; ADR when the trade-off warrants it |
| A domain term becomes precise | Root `GLOSSARY.md`, created when needed |
| A study, experiment, or compatibility check changes our understanding | Relevant research report or experiment record; update its index and status |
| A local constraint or rationale matters to code maintenance | Beside the owning code, with support for the claim; evaluate according to the project's agreed policy |
| A repeated mechanical mistake can be detected reliably | A focused automated check and its existing validation entry point |
| A reviewer needs a judgment rule | The relevant review guidance; create `CODING_STANDARDS.md` when warranted |
| Agents repeatedly miss a source or invoke the wrong workflow | A short, conditional pointer in `AGENTS.md` |
| Tracker or task procedure changes | The corresponding file in `docs/agents/` |

Research results belong with their method, source or run identifier, observed
outcome, and limitations. If a result changes a recommendation, update that
recommendation too. Preserve counterevidence; successful examples alone do not
establish a reliable general rule.

## Instruction quality

Use Matt's `writing-for-agents` principles: one owner per meaning, explicit
triggers, checkable completion criteria, and details loaded only when needed.
Prefer a deterministic check for a mechanical failure and concise guidance for a
judgment call. Keep installation adapters as pointers to the shared instructions.

When practical, verify a new instruction against the failure that motivated it.
Record a rule as unvalidated if it has only been inspected, rather than claiming
it has improved model behavior. Revisit a rule when later evidence contradicts it
or when the code/tooling makes it redundant.

## Skill discovery lesson

During initial setup, `ask-matt` and `setup-matt-pocock-skills` were installed but
absent from the displayed skill catalog. A filesystem search found their actual
`SKILL.md` files. Resolve an explicitly requested skill from the installed package
before substituting a generic workflow; absence from the displayed list alone
does not establish that the skill is unavailable.

Matt's `retro` can support a deeper review after a difficult session. It supplements
this task closeout process; routine corrections need not wait for a retrospective.
