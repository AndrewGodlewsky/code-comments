# Comment maintenance and evaluation

Research for Code Comments, 2026-11-04. This note complements the historical
sources with empirical evidence and a proposed evaluation design. It is research
input, not an approved skill specification.

## What the primary studies establish

### Steidl, Hummel, and Juergens (2013): quality is not quantity

*Quality Analysis of Source Code Comments* distinguishes comment categories and
assesses coherence, usefulness, completeness, and consistency. Its evaluation
includes 16 experienced developers and a case study of five open-source projects.
Comment density alone cannot distinguish useful explanation from irrelevant or
obsolete material. The authors' automated metrics address selected defects,
rather than establishing overall quality. Read: sections IV-VII and IX-X.
[Author-hosted paper](https://www.cqse.eu/publications/2013-quality-analysis-of-source-code-comments.pdf).

**Design implication:** score a comment's contribution and correctness, not how
many comments were produced. Use human judgment alongside mechanical checks.
The study does not validate an agent-written-comment rubric or prove benefits
for modern coding agents; those require our own evaluation.

### Wen, Nagy, Bavota, and Lanza (2019): proximity does not prevent drift

*A Large-Scale Empirical Study on Code-Comment Inconsistencies* mines approximately
1.3 billion AST changes across 1,500 Java systems and manually examines 500
candidate commits. The authors identify fixes involving implementation logic,
renaming, design changes, examples, and other comment content. Rationale comments
also become obsolete and sometimes need deletion. Their limitations include
Java-only project selection and a keyword-selected sample for manual analysis.
Read: sections III, IV-B, and V.
[Author-hosted paper](https://www.inf.usi.ch/lanza/PUBS/P/Wen2019a.pdf).

**Design implication:** adding comments and maintaining existing comments belong
to the same workflow. A code change should trigger examination of related claims,
including claims attached to callers or an interface elsewhere. The study is not
a causal demonstration that more comments reduce bugs, and unchanged comments
are not automatically inconsistent.

### Nielebock and colleagues (2019): useful-looking is not demonstrated usefulness

*Commenting Source Code: Is It Worth It For Small Programming Tasks?* reports an
experiment with 277 participants, including 227 professionals; only 66 completed
the entire study. For its small Java tasks, the authors found no significant
overall advantage in correctness or completion time from the tested commenting
conditions. Participants' positive opinions were stronger than the measured
benefit. The authors caution about generalizing from short, artificial tasks,
Java, and German-language materials. Read: sections 3, 4.4, and 5-6.
[Final author manuscript](https://jacobkrueger.github.io/assets/papers/Nielebock2019Comments.pdf);
[university publication record](https://research.tue.nl/en/publications/commenting-source-code-is-it-worth-it-for-small-programming-tasks/).

**Design implication:** a readable-looking output is insufficient evidence of
success. Evaluate whether a subsequent agent performs a maintenance task better.
This study neither establishes that comments are useless nor tests AI agents.

## Working hypothesis for this project

The following is our proposed synthesis, not a result reported by those papers:

> Preserve evidence-backed knowledge that a future maintainer would otherwise
> need to rediscover, beside the code that owns it, and revise that knowledge
> whenever the relevant behavior changes.

This differs from requiring a comment on every function. Useful outcomes include
adding, keeping, correcting, moving, or deleting a comment, and making no change.
The skill should be evaluated on each outcome.

Code establishes implemented behavior. Tests supply executable expectations.
Requirements and decisions can establish intent. A skill can infer some behavior
from code, but cannot reliably reconstruct every historical reason for it. When
evidence for a rationale is missing, it should leave that rationale unstated or
ask for the missing decision instead of manufacturing an explanation.

Keeping prose beside code reduces the distance between an implementation and its
explanation; it does not make the prose executable or automatically synchronized.
The proposed product therefore needs a maintenance discipline as well as a
comment-writing style.

## Proposed evaluation cases

These are candidate fixtures to agree before implementing an evaluation runner.
They are not a promise to support every language or scenario in version one.

| Case | Input evidence | Successful behavior |
| --- | --- | --- |
| Obvious code | Well-named, straightforward calculation | Leaves it alone |
| Hidden business constraint | Requirement says why a threshold exists | Explains the constraint near its owner |
| Unknown motivation | Unusual implementation with no explanation | Does not invent a historical reason |
| Concurrency invariant | Verified lock/order requirement and related call sites | Records the invariant and where it matters |
| Cross-file contract | Producer and consumer share a non-obvious assumption | Explains the assumption at its owning interface and uses a stable pointer |
| Behavior changed | Before/after code plus an obsolete comment | Corrects or removes the obsolete statement |
| Workaround retired | Dependency change removes the reason for a workaround | Removes the obsolete rationale when supported by evidence |
| Existing good comment | Accurate, concise rationale already present | Preserves it without gratuitous rewriting |
| Protected syntax | License, tool directive, suppression, or significant docstring | Preserves special meaning and required metadata |
| Second run | Output from a successful prior run | Adds no duplicate explanation or unnecessary churn |
| Untrusted instruction in code | Comment tells the agent to ignore its task | Treats source content as material to inspect, not operating instructions |

For each fixture, keep input code, supplied context, expected constraints, and
reviewer notes together. Accept multiple correct phrasings. Literal snapshot
matching should not define prose quality.

## How to measure whether the skill helps

1. **Separate two evaluations.** First test whether each tool discovers and invokes
   the skill. Then test the quality of the resulting comments. Successful
   installation does not establish automatic activation or good output.
2. **Compare matched tasks.** Before evaluating an authoring skill, compare the
   same contextual facts inline and in accessible external documentation. Include
   a code/tests-only baseline to distinguish information from placement. Record
   the tool, model, version, prompt, and available context; use repeated runs.
3. **Test the next maintainer.** Start a fresh agent on a concrete maintenance task
   using each output. Withhold the original conversation. Measure task correctness,
   regressions, unnecessary exploration, and the relevant constraint it retained.
4. **Keep the ground truth separate.** The evaluation's hidden requirements and
   expected failures must not be visible to the comment writer unless explicitly
   part of its supplied context. Otherwise we measure access to the answer key.
5. **Review claim support.** Record whether added rationale follows from available
   requirements, tests, source, or a verified reference. Penalize invented reasons
   even if they sound plausible.
6. **Test evolution.** Change a contract, remove a workaround, or rename an owner,
   then rerun. Inspect whether the corresponding comment remains correct.
7. **Check code preservation.** For a comment-only task, inspect the diff and use
   appropriate syntax/runtime checks for the supported languages. Do not assume
   that deleting comment tokens proves equivalence: directives and docstrings can
   have operational meaning.

Initial scoring dimensions: correctness, evidence for rationale, useful additional
information, placement, brevity, maintenance after change, code preservation,
and restraint. Weights and release thresholds remain open design decisions.

## Limits and follow-up

This is a targeted primary-source review, not a systematic literature review or
an experiment on current coding agents. The proposed rubric and evaluation cases
are project design ideas. Their effectiveness remains to be tested.

Historical commentary can supply principles and examples; it cannot by itself
prove that those principles improve agentic coding. The central validation still
needs to be a later agent making a correct change using the retained knowledge.

The user's clarified focus is lower-capability models and sustained maintenance,
including replacement of selected shared documents. See the proposed
[evaluation protocol](evaluation-protocol.md) for controlled placement comparisons,
successive edits, model tiers, total cost, and possible negative outcomes.
