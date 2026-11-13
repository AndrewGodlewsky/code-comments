# Code Comments

A comment hygiene skill for coding agents, and the evaluations used to decide what it
and its candidate neighbours should do. Product goals are in [intent.md](intent.md).

## Skills

**Shipped skill**:
The `code-comments` comment hygiene skill that the plugin installs. It is the only skill
that ships.
_Avoid_: the plugin (which also ships the stale-refs command)

**Candidate skill**:
A skill built and evaluated beside the shipped skill, which does not ship unless the
user decides it should.
_Avoid_: new skill, adjacent plugin

**Incubator**:
The place where candidate skills are researched, built and evaluated, each on its own.
_Avoid_: sandbox, staging

## Evaluation

**Arm**:
One condition of an evaluation. Every arm gets the same cases, and arms differ only in
the guidance the agent receives.
_Avoid_: variant (a variant is a version of a skill, which one arm may load)

**Skill arm**:
The arm whose agent reads the candidate skill before the task.

**Shipped-skill arm**:
The arm whose agent reads the shipped skill before the task. It asks whether a candidate
adds anything the shipped skill does not.

**Reminder arm**:
The arm whose request ends with one plain sentence asking for the behaviour a candidate
targets, with no skill loaded. A candidate has to beat it, not just the bare arm.
_Avoid_: prompt arm, instruction arm

**Bare arm**:
The arm that gets the request alone, with no skill and no reminder.
_Avoid_: control (the reminder arm is a comparison too), baseline

**Training case**:
A case whose results may be used to decide a skill edit.

**Held-out case**:
A case that is never used to decide a skill edit. It is run with the compared arms once,
after the last edit, as a check on overfitting, and after that it is spent. A gate may
run it first, without any skill arm, to choose or harden it; no gate result on it may
decide a skill edit. It tests a skill version blind only if no agent that saw it, in full
or described, edited that version.
_Avoid_: test case, validation case

**Gate** (case selection):
A run of the cases before any skill arm runs, used only to choose cases. A case that
every gate run passes cannot show a gain. Gate runs never count as results. A completion
gate, milestone gate or decision gate elsewhere in the repository is a checkpoint in the
work, not a set of runs.
_Avoid_: baseline run

**Headroom**:
The room a case leaves for one arm to do better than another. Over the bare arm, it
exists only where bare runs fall short. A case with no core headroom cannot test a
skill's main claim.

**Hardening**:
Changing a case the gate found at ceiling so that its needed facts are harder to find,
while keeping the request, the behaviour under test and the correct result. Until the
gate runs again, the new headroom is a hypothesis.
_Avoid_: tuning

**Focus**:
What a check grades: **core** (the target behaviour), **preservation** (what must not be
damaged), **restraint** (what must not be added) or **reply** (what the message to the
user says).

**Full-core run**:
A run that passed every core check. A **full-marks run** passed every check.

**Ruling**:
A recorded judgement, saying who made it and why, that a heuristic check misgraded one
run. The check's own result stays in the evidence beside it.
_Avoid_: override (the file that stores it), correction
