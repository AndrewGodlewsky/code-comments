# Incubator: candidate skills next to the hygiene skill

The incubator holds candidate skills that sit next to the shipped
[`code-comments` hygiene skill](../plugins/code-comments/README.md). Each one was
researched, built and evaluated on its own (issue
[#50](https://github.com/AndrewGodlewsky/code-comments/issues/50)). None of them ships.
None makes a performance claim beyond what its own eval shows. A skill moves from here
into a plugin only after the user decides it should.

Each skill keeps to the same limits as the shipped skill:
- No index, generated docs view, memory store or lookup service
  ([ADR 0001](../docs/adr/0001-context-lives-inline-no-central-index.md)).
- Context lives in the source files.
- Any script uses only the Python standard library.

## Results across the four skills

None of the four reliably beat its one-line reminder on graded checks, on either model,
in training or on the held-out pair. Nothing here ships. The
[planning-research overview](../docs/planning-research-2026-11-11.html) sets out what this
means and which decisions it leaves to the user. Each skill's README has its own result,
limits and next steps.

The table counts checks passed, pooled over the runs where all four arms ran: iteration 1
and the held-out pair, 35 runs per arm per skill. The `with_skill` column mixes v1
(training) and v2 (held out). These are pooled n/N, not the mean per-run rates that the
skill READMEs headline.

| Skill | with_skill | shipped_skill | reminder | without_skill | Against the reminder | Its README's next step |
| --- | --- | --- | --- | --- | --- | --- |
| [verify-before-relying](verify-before-relying/README.md) | 220/220 | 214/220 | 220/220 | 200/220 | Tie after the rulings. Before them the reminder led by one check on Haiku training (95/96 against 94/96) | Recommend the reminder sentence, not the skill |
| [fold-docs-inline](fold-docs-inline/README.md) | 318/325 | 256/325 | 307/325 | 250/325 | Not established: each lead comes from one case | Offer the reminder sentence, or the skill for its page handling |
| [constraint-sweep](constraint-sweep/README.md) | 208/215 | 196/215 | 204/215 | 204/215 | Tie on core. The bare model passed every core check (35/35), so there was no headroom | Recommend the reminder sentence, by the rule set before the runs |
| [change-drift-sweep](change-drift-sweep/README.md) | 220/220 | 218/220 | 219/220 | 208/220 | Tie | Its rule set before the runs makes it a plugin enhancement (#21, #48) |

Across the four skills, with 140 runs per arm, counted from each iteration's
`benchmark.json` and `grading.json`:
- **Against the reminder: no evidence of a difference.**
  - Full-marks runs: 132 with the skill and 126 with the reminder (two-sided stratified
    exact test by skill, iteration and case, p = 0.15).
  - Full-core runs: 137 and 133 (p = 0.28).
  - This does not show that the two are equal.
- **Against the bare model, pooled: every guided arm gained, and only on prose, reply,
  preservation and restraint checks.**
  - The skill and reminder arms gained mostly on Haiku: +69 and +63 checks of 588, against
    +35 and +25 of 392 on Sonnet. The shipped-skill arm's smaller gain was mostly on
    Sonnet: +16 checks, against +6 on Haiku.
  - The bare model had 73 full-marks runs. The reminder accounts for 53 of the skills' 59
    extra full-marks runs.
  - In constraint-sweep alone, the reminder showed no gain over the bare model.
- **Hidden behavioural tests.** The skill, reminder and bare arms each passed them in
  120 of 120 runs. The shipped-skill arm passed in 111 of 120.
  - Each of the 9 failing runs noticed the constraint or error, then built the narrower
    or breaking change anyway.
  - They fall in two evals (verify-before-relying and constraint-sweep) and in five
    case-model cells. Eight of them are on Haiku.
  - This comparison was chosen after reading the runs. Its cause is a hypothesis: the
    shipped skill's "make the change if asked and tell the user" conflict rule, or its
    ask-first guidance.
- **Rulings.** The pooled numbers include 32 rulings by auditor agents:
  verify-before-relying 5, fold-docs-inline 26, change-drift-sweep 1 and
  constraint-sweep none. Five more are in the iteration-2 `with_skill` re-runs, for 37 in
  all, none by a human.

## Layout

```text
incubator/
  harness.py            shared eval harness: prepare, grade, summary, self-test, lint, verify-reads
  gradelib.py           shared readers for comments, docstrings and code shape
  ideation/             how the four skills were chosen (a dated record)
  <skill>/
    README.md           what it is for, results, limits and next steps
    research.md         sources, findings and how they shaped the skill
    skill/<skill>/      the installable skill: SKILL.md, plus scripts/ if it has any
    eval/
      arms.json         the one-line reminder used as the comparison arm
      cases/<case>/     prompt.md, case.yaml, graders/, files/, place-files.sh
      hidden/<case>/    hidden tests, which the agent never sees
      references/<case>/  a good result for the case, which passes every check
      grade.py          one mechanical check per grader file
      CASES.md, GATE.md, CHANGES.md, RESULTS.md, ANALYSIS.md
                        case design, case selection, skill edits, results, reasoning
      HELD-OUT.md       held-out case design, kept from the skill writer (where a skill has one)
      iterations/<name>/  run records, grades, benchmark.md and verify-reads.json;
                        outputs/ is gitignored
```

Cases use the layout that `claude plugin eval` reads, the same as
[`evaluation/hygiene/`](../evaluation/hygiene/README.md).

## Running an eval

```sh
python incubator/harness.py self-test                 # every skill: references pass, inputs fail
python incubator/harness.py lint                      # every skill: format, portability, no copied case text

# 1. Gate: the bare model only, for case selection, on the training cases
python incubator/harness.py prepare SKILL --iteration gate-haiku --arms without_skill --runs 2 --split train
#   ...give each prompt in eval/iterations/<name>/runs.json to a fresh agent of the chosen model...
python incubator/harness.py grade SKILL --iteration gate-haiku

# 2. All four arms on the training cases; after a skill edit, re-run with_skill only under a new name
python incubator/harness.py prepare SKILL --iteration iteration-1-haiku --runs 3 --split train
python incubator/harness.py grade SKILL --iteration iteration-1-haiku
python incubator/harness.py verify-reads SKILL --iteration iteration-1-haiku TRANSCRIPT_DIR
python incubator/harness.py prepare SKILL --iteration iteration-2-haiku --arms with_skill --runs 3 --split train

# 3. The held-out cases, once, after the last skill edit
python incubator/harness.py prepare SKILL --iteration heldout-haiku --runs 3 --split held-out
python incubator/harness.py grade SKILL --iteration heldout-haiku

python incubator/harness.py summary SKILL iteration-1-haiku iteration-1-sonnet iteration-2-haiku heldout-haiku
```

`--split train` leaves out cases marked `held_out: true` and `--split held-out` keeps only
those. Without `--split`, `prepare` takes every case, held-out ones included.

`prepare` snapshots the skill into the iteration, so the files a run read are kept with
its grades. It copies each case's `files/` into a fresh `outputs/` folder per run. It
writes the exact prompt for each run to `runs.json` and `prompt.txt`, with a fingerprint
of each case's `files/` and hidden tests. The prompt follows the hygiene eval's wording:
- **with_skill** runs must read the snapshot of the candidate skill's `SKILL.md` first.
- **shipped_skill** runs must read a snapshot of the shipped `code-comments` skill first.
  This arm asks whether the candidate skill adds anything the existing one does not.
- **reminder** runs get one sentence from `arms.json` added to the request. The pilot
  found one general sentence as good as the full skill downstream, so a candidate skill
  has to beat this arm, not just the bare model.
- **without_skill** runs get the request alone.

Each grader's frontmatter sets a `focus`:
- `core`: the target behaviour, graded by hidden tests where it can be. Hidden tests live
  in `eval/hidden/<case>/hidden_tests/`. The agent never sees them, and
  `gradelib.run_hidden_tests` runs them on a copy of the run.
- `preservation`, `restraint`: what must not be damaged or added.
- `reply`: what the message to the user says. These are mostly keyword checks.

The headline is the mean of each run's share of checks passed. Within a run every check
counts the same, reply checks included, and the harness does not read a grader's
`weight:` field. Each run then counts the same, so the headline can differ from the
pooled checks-passed ratio. The benchmark also reports each focus separately, so a lead that rests on keyword checks
of the reply shows up there.

`grade` needs every run's `outputs/`, which is gitignored, so it refuses on a clone: it
stops, writing nothing, when a run listed in `runs.json` has no `outputs/`. It also stops
when a case's `files/` or hidden tests differ from the fingerprint `prepare` stored, or
when `grade.py`, `gradelib.py` or a grader file differs from the fingerprint in the
iteration's `benchmark.json`. `--force` lifts those two stops for a deliberate regrade,
such as after a grader fix. A forced grade keeps the old fingerprints in `benchmark.json`
beside the new ones and prints what changed. The 32 iterations of #50 were graded before
fingerprints existed, so regrading any of them needs `--force`. Leave the gate iterations
as graded, as each skill's GATE.md asks: cases were hardened after gate runs, so a regrade
would compare those runs with other files. A ruling in
`overrides.json` must match a current grader text and give `passed` as JSON `true` or
`false`, or `grade` and `self-test` name the file.

`verify-reads` reads the agent transcripts and lists any skill-arm run (`with_skill` or
`shipped_skill`) that made no Read call on its own arm's snapshot `SKILL.md` (the path its
prompt names) before its first Edit, Write, MultiEdit or NotebookEdit call. Exclude and
re-run those. A Read with a `limit` or `offset` still counts, since an agent may read in
chunks, but is listed under `partial_reads`. Transcript lines that are not JSON are
counted under `transcripts_with_unparsable_lines`. Shell commands count as neither: a
file written by a heredoc or `sed` is not seen as an edit, and a skill read with `cat` is
not seen as a read.

**Stored results.** Each counted iteration's `verify-reads.json` in #50 was written by a
wrapper outside the repository, `tools/verify_all_reads.py` beside the staging clone.
`harness.py verify-reads` only prints its result. The wrapper applied the same
read-before-edit rule as the harness did then, and stores that result as `skill_arms`
(checked, missing_transcripts, skipped_skill) and `skill_arm_runs` (runs). It adds four
lists of its own: `other_arm_skill_reads` (runs in other arms whose tool input named a
`SKILL.md`), `wrong_model` (the transcript's model id against the iteration's model),
`runs_with_several_transcripts` and `runs_without_transcript`. It reads the agent
transcripts, which are not in git, so the files cannot be re-checked from the
repository.

**Runs blocked by the run-limits guard.** In #50 the guard that runs subagents misread
`sed -i` and heredoc commands, taking a `>` inside a heredoc for a redirect. It also
blocked a reply written to a path respelled `/tmp/...`. Six runs were excluded and re-run,
and two more counted without a reply. The exclusion rule was decided only after the
runs. Before the next run:
- write the exclusion rule for guard-blocked runs into the skill's README
  ([change-drift-sweep's](change-drift-sweep/README.md#running-the-eval) states the rule
  #50 applied);
- until the `prepare` prompt says so itself, tell run agents to make every file change,
  and write `RESPONSE.md`, with the file-writing tools at the absolute path the prompt
  gives.

`tests/test_incubator.py` runs every skill's self-test and lint with the rest of the
suite, tests the harness on a synthetic skill, and loads change-drift-sweep's script tests
(`test_value_drift.py`). change-drift-sweep's graded variants are not in that suite,
because they include held-out variants. After any edit to `gradelib.py`, `harness.py` or
a `grade.py`, also run:

```sh
python -B -m unittest discover -s incubator/change-drift-sweep/eval -p "test_*.py"
```

The other three skills' graders have no kept variant tests yet. Their self-test only shows
that the reference passes every check and the unchanged input fails one, so a check that
starts passing a specific wrong answer goes unnoticed. Add a pinning variant before each
grader fix those skills' READMEs plan.

`lint` checks a skill's Markdown and the comments, docstrings and string literals of its
`.py` files for any 8-word run of case, reference or hidden-test text. It skips the code
itself, so a shared code idiom is not counted as a copy.

## Cost of #50

- **Approval.** The user's request of 2026-11-11 asked to "research, test, implement, and
  eval all of your ideas as separate skills" and said "it is totally fine if Opus runs
  until it hits its usage limit". The cap was the plan's usage limit. No dollar or
  per-run cap was set, and no cost estimate was made before the runs.
- **Measured usage.** Counted on 2026-11-11 from the transcripts of the session's 11
  subagent workflows, the eval runs and the agent work around them, each assistant message
  once by its id. The count leaves out the
  coordinating session itself, and the review workflow was still running when it was
  made, so it is a lower bound.

  | Model | Messages | Output tokens | Cache-write input | Cache-read input | Uncached input |
  | --- | --- | --- | --- | --- | --- |
  | Haiku 5.5 | 3,879 | 2,663,000 | 16,796,524 | 187,274,742 | 7,758 |
  | Sonnet 5.5 | 1,562 | 660,888 | 9,112,129 | 67,906,438 | 3,124 |
  | Opus 5.5 | 4,705 | 6,753,885 | 22,984,216 | 699,689,357 | 9,446 |

  The runs used subscription usage, so no billed cost exists, and no list-price
  equivalent was computed. The transcripts are not in the repository.

## Limits shared by every eval here

- Skill arms are told to read the skill first, so no eval here tests whether a skill
  loads on its own.
- No arm loads a candidate skill together with `code-comments`, which is how it would ship.
- The harness records no model id. Only an iteration's name says Haiku or Sonnet, so
  exact model versions are not kept.
- In all four evals, each agent read its task from `prompt.txt` instead of receiving it
  as a user's message. Every case, reference and hidden test was written by an agent,
  none from a real repository. The models are one family.
- The fixtures have 5 to 16 files, so every run could read them whole. No eval here
  measures a skill's search steps or change-drift-sweep's script, which matter only in a
  repository too large to read.
- The reminder sentence was only ever appended to the request. Where it would live in
  real use is untested.

## Rules for every skill here

- **Score preservation and restraint alongside the target behaviour.** Round 1 of the
  tournament showed that a skill can win on a proxy while doing harm.
- **Keep held-out cases.** Cases marked `held_out: true` in `case.yaml` are never used
  to decide a skill edit. They are run at the end, as a check on overfitting.
- **Record rulings, never hide them.** A heuristic check that misgrades a run gets an
  `overrides.json` entry that says who made the ruling and why. The check's own result
  stays in the evidence.
- **Publish null and negative results.** A skill that does not beat the one-line
  reminder says so in its README.
