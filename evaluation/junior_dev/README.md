# Junior-dev eval

This eval measures whether the `junior-dev` plugin
([plugins/junior-dev](../../plugins/junior-dev)) makes plans and diagrams clearer. Issue
[#52](https://github.com/AndrewGodlewsky/code-comments/issues/52) tracks it. The
[design](../../docs/junior-dev/design.md) says what is measured and why, and the
[plan](../../docs/junior-dev/plan.md) gives the build order. The user's test for clarity is
that a smart, technical reader with no context can understand the artifact. Here that test
is a hidden quiz, answered by fresh readers who see only the final artifact.

## Cases

Opus 5.5 wrote 20 cases from fixed slots (`case_slots.json`), using
`templates/cases.js`. An independent Opus checker read each one, and a case that failed got
one rewrite. 18 passed: 12 for development and 6 held out, with each family entirely on one
side. Two were dropped with their reasons recorded in `case-generation.json`: mr-02's
quiz could be guessed from its wording, and dm-01's reference SQL policy was wrong.

Each case is in `cases/<id>/`:

- `visible/brief.md` is the request the author plans from, with a stated format. Seven cases
  also have a `visible/existing/` folder that describes the current system.
- `private/quiz.json` has 11 or 12 questions about how the system works.
  - "Brief" items have a fixed key.
  - "Design" items ask about choices the brief leaves open. In natural mode they are graded
    against the author's own answers. The author writes those answers in a sealed call after
    the loop, so a valid design that differs from the reference is not penalised.
- `private/requirements.json` lists what any acceptable artifact must contain.
- `private/reference.md` is a clear artifact.
- `private/seeded-presentation.md` holds the same information, badly laid out.
- `private/seeded-implicit.md` is the same design, with its relationships left implicit.
- `private/meta.json` has the slot, the checker's notes, and any point the brief leaves
  undecided on purpose (auth-02, dp-02, feat-02).

All 30 Mermaid blocks in the references and seeds parse under Mermaid 11. Run
`python -m evaluation.junior_dev.cases validate` to check the set.

## How a run works

`build.py` turns cases × arms × authors × repeats into Workflow scripts (`built/`, not
committed). Each script embeds the plugin's own `SKILL.md`, `junior-prompt.md` and
`teachback-prompt.md`, so the tournament always runs the text that ships. Every role is an
agent told to use no tools. A run goes through these steps:

1. **Draft** (natural mode): the author writes the artifact from the brief and the existing
   files.
2. **Review**, according to the arm (`arms.py`):
   - none;
   - same-budget self-review;
   - the one-line "write it for a junior" instruction;
   - a critic that sees only the artifact;
   - the junior loop;
   - the junior that also sees the brief.
3. **The junior loop** mirrors the plugin.
   - The junior sees the artifact and its own questions and answers.
   - The author revises the artifact and tags each answer `checked`, `decided` or `unknown`.
   - A fresh junior that reads only the artifact gives the teach-back, and the author gives
     a verdict on it.
   - The loop ends on a correct teach-back, the round cap, or 3 wrong teach-backs.
4. **Sealed key:** the author answers the design questions.
5. **Readers:** a hurried Haiku reader (low effort, at most 25 words) and a Sonnet reader
   answer the quiz from the final artifact alone. NOT STATED counts as wrong.
6. **Grader:** Sonnet (low effort) checks each answer against the key, judging what the
   question asks.
7. **Checker:** Sonnet checks the requirements, and whether any undecided point is reported
   as a hole or invented.

`collect.py` files each run under `iterations/<name>/<case>/<arm>/<author>/<mode>/run-<k>/`.
`score.py` computes comprehension (the mean over readers of the share of items correct),
paired differences per case with a bootstrap over cases (seed 52), and the user's decision
rule. `tools/dryrun.mjs` runs a built batch offline with stub agents.
`tests/test_junior_dev_harness.py` uses it to check what each role is shown.

```sh
python -m evaluation.junior_dev.build validation        # or pilot; writes built/<name>/*.js
# run each file with the Workflow tool, then:
python -m evaluation.junior_dev.collect <workflow-output-file> evaluation/junior_dev/iterations/<name>
python -m evaluation.junior_dev.score evaluation/junior_dev/iterations/<name>
```

The Mermaid guardrail uses `tools/mermaid-check` (`npm install --ignore-scripts` there) when
it is installed, and a heuristic lint otherwise.

## Grader validation (plan Task 7)

These runs had no review and no author. The readers and graders ran on each case's
reference, its two seeds, and a padded copy (the reference plus a generic "good practice"
paragraph), 72 runs per round. In round 2 the grader was told to judge what the question
asks, not every detail of an over-full key. That change came from ev-03, whose reference had
lost credit on answers that did answer the question.

| Check | Round 1 | Round 2 | Gate |
| --- | ---: | ---: | --- |
| Reference comprehension | 0.972 | 0.961 | 0.85 or more: pass |
| Implicit seed at least 0.15 below the reference | 18 of 18 cases (mean 0.061) | 18 of 18 (0.103) | at least 70% of cases: pass |
| Padded minus reference | -0.056 | -0.010 | padding earns no more than +0.05: pass |
| Sonnet and Opus graders agree | 807 of 860 (93.8%) | 815 of 860 (94.8%) | 90% or more: pass |
| Hurried reader: reference minus presentation seed | +0.056 | -0.014 | 0.10 or more: reported, not met |

What this means for the results that follow:

- **The quiz measures whether an artifact conveys its design.** That covers missing or
  implicit steps, ownership, ordering and failure paths. The range is wide, from about 0.06
  to 0.97.
- **The quiz does not measure layout.** A badly presented but complete document still lets
  an LLM reader find every answer, and that held even for a hurried Haiku reader. The
  user's "easy to read quickly" therefore rests on the blind pairwise clarity judge
  (`prompts/judge.md`), not on comprehension. Report the two separately.
- **Single runs are noisy.** On the same artifacts, comprehension moved by 0.06 on average
  between rounds, and by up to 0.29 for one case. The grader also changed between the
  rounds, so 0.06 is an upper bound on pure reader noise. Every comparison uses repeat runs,
  and differences are taken within each case.
- **The graders are Claude models only.** No other model family was available. The check
  against Opus shows the Sonnet grader is consistent; it does not show it agrees with a human.
  A sample of blinded pairs will be offered to the user to rate.

Each round used about 12.3 million subagent tokens (including about 35,000 tokens of fixed
input per agent call) and took about one minute per mode.

## Pilot (plan Task 8)

The pilot ran 4 development cases (auth-01, ms-01, mig-02, feat-01) × four arms (NoReview,
SelfReview, Critic, Junior v0) × two authors (Haiku 5.5, Sonnet 5.5), 1 run each, in
natural mode. The first Junior runs were invalid: the harness dropped every author answer
(see `iterations/pilot-invalid-answers-dropped/`). The Junior arm was rerun after the fix,
and those reruns are what the tables below show.

| Arm | Haiku comprehension | Haiku words | Sonnet comprehension | Sonnet words |
| --- | ---: | ---: | ---: | ---: |
| NoReview | 0.863 | 1,789 | 0.927 | 1,694 |
| SelfReview | 0.951 | 2,551 | 0.977 | 2,070 |
| Critic | 0.933 | 4,585 | 0.917 | 3,363 |
| Junior v0 | 0.947 | 5,853 | 0.948 | 5,133 |

The blind pairwise judge (Sonnet) saw each pair in both orders. "Preference" runs from -1
(always loses) to +1 (always wins).

| Pair | Haiku preference | Sonnet preference | Both orders agree |
| --- | ---: | ---: | --- |
| Junior v0 vs NoReview | -1.00 | -1.00 | 8 of 8 |
| Junior v0 vs SelfReview | -1.00 | -1.00 | 8 of 8 |
| Junior v0 vs Critic | -0.25 | -0.50 | 3 of 8 |
| SelfReview vs NoReview | +0.25 | 0.00 | 3 of 8 |

These are 4 cases with 1 run each, so they steer the next step and are not results.

- **Junior v0 makes plans less clear.**
  - It lost every blind judgment against both baselines. Its plans were 2.3 to 3.5 times
    longer, and its comprehension was no better than SelfReview's.
  - The judges' reasons are consistent: the core flow is "buried under" cross-referenced
    decisions, edge-case machinery, "not defined" caveats and long open-question lists.
- **The loop spirals into detail.**
  - The junior asks about edge cases, and the teach-back lists every unstated detail
    (TLS, cookie formats, `Retry-After`) as a gap.
  - The author counts each gap as a misreading and adds text. 7 of the 8 runs ended on 3
    wrong teach-backs, and the other one at the round cap.
  - The plugin's own SKILL.md and junior prompt drive this. The climb targets it first
    (Task 10).
- **There is little room on the quiz.** First drafts already score 0.86 to 0.93, and
  SelfReview 0.95 to 0.98, so no arm can beat SelfReview by 10 comprehension points. Clarity
  as the user means it ("simple, cleanly laid out, step by step") has to come from the blind
  judge, with comprehension as a guardrail.
- **The cost is the Sonnet junior's.** Estimated API-equivalent cost of the product roles
  per Haiku-authored run: NoReview $0.0015, SelfReview $0.009, Junior v0 $0.29, which is about
  ten times Sonnet's NoReview ($0.029). The estimate counts visible tokens only, not thinking
  tokens.

Usage: the pilot (32 runs), the Junior rerun (8 runs) and the judging (112 judgments) used
about 31 million subagent tokens. That is roughly $15 at API list prices, not counting
thinking tokens. Most of it is the fixed ~35,000-token input of each workflow agent.
