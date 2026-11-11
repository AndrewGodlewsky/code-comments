# constraint-sweep

**Status: evaluated. It shows no reliable gain over the one-line reminder or the bare
model on any graded check.** The skill was graded over 165 runs on Claude Haiku and
Sonnet:
- **Core checks.** It tied the reminder sentence in [eval/arms.json](eval/arms.json) and
  the bare model, in training and on the held-out pair.
- **The held-out pair.** All four arms tied on core. The only failed check in any arm
  was one reminder run's edit to `README.md`.
- **The shipped skill.** It beat the shipped `code-comments` skill only on the training
  cases. There the shipped skill broke a constraint it had found in 6 of 25 runs.
- **No core headroom.** The bare model passed every core check it was given (35 of
  35), so these fixtures left no room to test the skill's main claim.
- **One ungraded edge.** It kept the column position the user asked for and updated the
  positional load in step: 10 of 10 runs, against 3 of 10 with the reminder and 0 of 10
  bare. The graders accept both outcomes.

This README said before the runs that a tie means the honest recommendation is the
sentence, not this skill. The results are in [eval/RESULTS.md](eval/RESULTS.md), and the
samples are small (see Limits).

An incubator skill for issue [#50](https://github.com/AndrewGodlewsky/code-comments/issues/50),
from ideation candidate C1 ([candidates](../ideation/2026-11-11-candidates.json)), as
redirected by the coordinator. The installable skill is
[skill/constraint-sweep/SKILL.md](skill/constraint-sweep/SKILL.md). The sources, and how
they shaped each rule, are in [research.md](research.md). The eval cases are described in
[eval/CASES.md](eval/CASES.md).

## The problem

You ask an agent for what looks like a local change: speed up a function, simplify a
loop, raise an error instead of returning nothing, delete dead code, add a field. The
function's own file gives no warning. But another file relies on the old behaviour, and
the only record of that is a comment over there. It might be a caller that needs its
input in order, a database load that reads fields by position, or a config file that
names a function as a string. The agent never opens that file, the visible tests still
pass, and the break turns up later.

This is the gap that [ADR 0001](../../docs/adr/0001-context-lives-inline-no-central-index.md)
leaves to search. Context lives inline, and an agent finds context in another file only
by searching for it. The ADR's "Revisit if" clause is about exactly this failure: "the
agent never opens or searches the file that holds the fact". The shipped skill covers
the writing half (put the fact beside the code). Nothing tells the reader to search.

What the evidence said before this eval (details and limits in [research.md](research.md)):
- **Discovery had never been measured in this repository.** All 11 hygiene prompts list
  their input files, and their fixtures hold 2 to 7 files.
- **No run checked in this repository had broken behaviour.** The check covered round 1,
  the pilot, and all 15 iteration-5 `reason-only-in-test` runs. So the headroom this
  skill targets was a hypothesis. This eval found none (see Results).
- **Outside this repository, behaviour changes slip past visible tests.**
  - In Dristi and Dwyer, 19-35% of LLM refactorings changed behaviour, and about 21% of
    those passed the existing tests.
  - In Wang, Pradel and Liu, 29.6% of plausible SWE-bench patches behaved differently
    from the reference.
  - Liu et al. name "logical dependencies that are not explicitly enforced by the code
    structure" as a failure class.
- **What a search finds depends on its options.** In a local probe:
  - default ripgrep skipped `.github/`;
  - `--hidden` also entered `.git/`;
  - a `-t py` filter missed INI and JSON references;
  - a name built at run time matched only its fixed prefix.

## What it adds over the shipped skill

The shipped [`code-comments` skill](../../plugins/code-comments/skills/code-comments/SKILL.md)
governs the comment text a change leaves behind. Its one search line, "Before
simplifying, look for it in tests, callers and docs", is there to find a reason to write
down. Hygiene iteration 2 found that "The new "look in tests" line did not produce
the behaviour" ([evaluation/hygiene/README.md](../../evaluation/hygiene/README.md)).
That behaviour was recording a test's reason in the docstring, and the prompt listed the
test file, so it measured recording, not search.

This skill governs what the agent reads **before** changing behaviour, and whether the
code still honours constraints stated in other files. It adds:
1. **A trigger on behaviour changes**, including requests that look local: simplify,
   speed up, raise instead, remove dead code, add a field or argument.
2. **Named symbols and their own pointers.** List what will change, then open every
   file or symbol its docstring and comments name.
3. **An exact search recipe.**
   - Word-bounded, every file type, hidden directories in, `.git/` out.
   - The dotted and slash module paths.
   - Runtime-built names and import aliases.
4. **A way to sort mentions.** Each mention either states nothing, or states a
   constraint that is **live** (the code there still depends on it) or **stale** (it
   no longer does).
5. **What to do with each.**
   - **Keep a live constraint**, using the first of these that works:
     1. Keep the property where it is produced. Moving the work into a dependent does
        not count.
     2. If the request itself changes the property, update the dependent sites in the
        same change.
     3. Failing both, make the change and report the break.
   - **Keep the form the user named** (a position, a name, an error type).
   - **A stale constraint does not block the change.** Report it, and correct it in the
     same change if the change makes it false.
   - **Reliance the code at a mention demonstrably has** counts as a live constraint.
     Suspected reliance is only named in the reply.
   - **Removing dead code:** a name in config, a string or a script counts as a use.
   - **Files whose mentions state nothing** are left alone.

It asks for no new comments. When a change needs one, or makes an existing one false,
the agent follows `code-comments` for the wording, and fixes the false text as part of
the change.

The eval's `shipped_skill` arm tests this directly. On the training cases the shipped
skill scored below this one because it broke constraints it had found. On the held-out
pair they tie (see Results).

## When to use it, and when not

Use it before changing what existing code returns, raises, orders, deduplicates or
accepts, or whether it exists. That includes:
- simplifying, speeding up or restructuring a function;
- changing error handling, such as raising instead of returning a value;
- removing dead or unused code;
- adding a field, column or argument to something existing code already produces or
  accepts.

Leave it out for:
- new code that changes nothing existing;
- questions, explanations, formatting;
- comment wording and comment-only requests. Those belong to the shipped skill.

## How it works

Instructions only: a `SKILL.md` with a 103-line body (v2). There is no script, caller
graph or usage-flag analysis. It reads the code on each run and stores nothing: no index,
generated docs view, memory store or lookup service (ADR 0001). The search runs at edit
time with `rg` or `grep`.

The steps, in the order the agent meets them:
1. **Name the symbols** whose behaviour will change, with module and file paths.
2. **Follow the symbol's own pointers** in its docstring, comments and module header.
   This is ADR 0001's pointer mitigation.
3. **Search every text file**, with no type or glob filter:
   - `rg -n -w --hidden -g '!.git' NAME`;
   - `rg -n -F --hidden -g '!.git'` on the dotted and slash paths;
   - the fallback is `grep -rnw --exclude-dir=.git NAME .`;
   - runtime lookups and import aliases get extra searches.
4. **Sort each mention** as states nothing, live constraint, or stale constraint. Read
   the code there, the comment on or above it, the enclosing docstring and the test
   name.
5. **Change the code** to keep live constraints in the form the user named. Report stale
   ones and correct any the change makes false. Leave the rest alone.
6. **Report** with file:line:
   - each constraint that shaped the change;
   - each stale one and whether it was corrected;
   - each site of suspected reliance.

   Mention the sweep only when it changed the plan or found something stale.

v1, the version in iteration 1, deferred all fixes of false comments to `code-comments`
and said nothing about moving work into a dependent. v2 changed both rules after
iteration 1 ([eval/CHANGES.md](eval/CHANGES.md)).

Where each rule comes from (research.md "What this means for the skill's rules"):

| Rule | Support | Grade |
| --- | --- | --- |
| Trigger on behaviour changes | Liu et al.; Dristi and Dwyer; Wang, Pradel and Liu; Chesterton's fence | empirical failure mode; trigger wording untested |
| Name the symbols | the search needs names | hypothesis |
| Follow own pointers | ADR 0001 Consequences; inline-only trade-offs C1 | practitioner |
| Search recipe and its flags | local probe P1; ripgrep guide; `stale_refs.py` reads no `.sql` | repository probe |
| Runtime names, aliases | probe P1; Vulture; PyCG recall about 69.9% | repository probe |
| Reading window at each mention | Poshyvanyk et al. (abstract only); @tComment | hypothesis |
| Live or stale | principles P-21 (grade D); @tComment | practitioner |
| Ranked ways to keep a live constraint; keep the named form | the shipped skill's conflict rule ("make the change if asked and tell the user"); iteration 5 | repository eval |
| Demonstrable reliance binds; suspected reliance is only reported | ADR 0001 reason 1 (the code is the source of truth); Hyrum's Law | hypothesis, marked *judgement* |
| Restraint | round-1 proxy-win harm; Anthropic context engineering | repository eval |
| No new comments, instructions only | ADR 0001 reasons 2 and 4; the coordinator's direction | practitioner |

Two rules in the skill are marked *judgement*:
- narrowing a common name to its qualified forms;
- naming a suspected but unconfirmed dependency in the reply instead of coding around it.

The line telling the agent to make sure a built-in search tool covers hidden directories
rests on an open question: no documentation was found on whether Claude Code's Grep tool
skips them.

## Its eval

Seven cases in [eval/](eval/), five for training and two held out. Each fixture is a
small Python repository of 12 to 16 files. The prompts list no files, because finding
the context is what is measured. Each fixture also mentions the changed symbol in places
that state nothing binding. The four discovery cases were hardened after a bare-model gate
([eval/GATE.md](eval/GATE.md)).

| Case | Split | `core_needs_other_file` | What it tests |
| --- | --- | --- | --- |
| `sort-relied-on-elsewhere` | training | true | drop a sort the user thinks nothing needs, without breaking a shell upload that needs id order |
| `dispatched-by-name` | training | true | remove dead code but keep a handler whose name is built at run time from a config file's event kinds |
| `positional-columns-in-sql` | training | true | add a field "next to" another without breaking a positional SQL load |
| `positional-columns-in-sql-pointer` | training | false | the same task with a one-line pointer to the SQL in the edited file (ADR 0001's pointer mitigation) |
| `stale-constraint-elsewhere` | training | false | restraint: a stated constraint the code no longer relies on must not block the change, and is reported or corrected |
| `mention-without-constraint` | held out | false | restraint: descriptive mentions trigger no edits, defences or questions |
| `first-wins-reason-in-caller` | held out | true | simplify a loop the user thinks can keep any duplicate, and keep the first, a rule stated only in a billing SQL view |

The third column is `core_needs_other_file`: the evidence that rules out the natural
wrong edit is found only in another file, and nothing in the edited file points to it.
`case.yaml` also records:
- `context_in_other_file`;
- `pointer_at_edit`;
- `evidence_in`, the files holding the needed evidence.

An earlier control, `mirrored-column-order`, had a different task, so it mixed task
difficulty with where the context lives. It was replaced by the pointer twin before any
run and is kept in `eval/reserve/`.

How the checks work:
- **Core checks** are hidden tests in `eval/hidden/<case>/hidden_tests/`. They exercise
  the consumer, not the edited function alone.
- **Restraint checks** confirm the request was done (so refusing loses). In every case
  but `stale-constraint-elsewhere`, they also confirm that files the run only read are
  byte-identical.
- **Reply checks** are keyword heuristics, reported apart from the rest. Most are scored
  only when the outcome they describe happened.

There are four arms:
- `with_skill` reads this `SKILL.md` first.
- `shipped_skill` reads the shipped `code-comments` skill first. This is the
  falsification test: if it ties, constraint-sweep is a variant of the shipped skill and
  belongs under #21/#48.
- `reminder` adds the sentence in [eval/arms.json](eval/arms.json) to the request: grep
  the whole repository, every file type, for the names being changed, and keep or report
  any constraint stated there. If it ties the skill, recommend the sentence.
- `without_skill` gets the request alone.

Commands, from the repository root, with the iteration names the recorded runs used:

```sh
python incubator/harness.py self-test constraint-sweep   # references pass, inputs fail
python incubator/harness.py lint constraint-sweep        # format, portability, no copied case text

# 1. Gate: bare model only (recorded as gate-haiku, gate-sonnet)
python incubator/harness.py prepare constraint-sweep --iteration gate-haiku --arms without_skill --runs 2
# 2. All four arms on the training cases (iteration-1-*); re-run with_skill after a skill edit (iteration-2-*)
python incubator/harness.py prepare constraint-sweep --iteration iteration-1-haiku --runs 3 --split train
python incubator/harness.py prepare constraint-sweep --iteration iteration-2-haiku --arms with_skill --runs 3 --split train
# 3. Held-out pair, once, after the last skill edit (heldout-*)
python incubator/harness.py prepare constraint-sweep --iteration heldout-haiku --runs 3 --split held-out
#   ...give each prompt in eval/iterations/<name>/runs.json to a fresh agent of the chosen model...
python incubator/harness.py grade constraint-sweep --iteration heldout-haiku
python incubator/harness.py verify-reads constraint-sweep --iteration heldout-haiku TRANSCRIPT_DIR
python incubator/constraint-sweep/eval/discovery.py --iteration heldout-haiku TRANSCRIPT_DIR

python incubator/harness.py summary constraint-sweep iteration-1-haiku iteration-1-sonnet iteration-2-haiku iteration-2-sonnet heldout-haiku heldout-sonnet
```

Each Sonnet iteration repeats the Haiku one with `--runs 2`, except the gate, which ran
Sonnet once per case. `discovery.py` exists but was not run on any recorded iteration.
Model runs cost money, and each campaign needs the user's approval first
([intent.md](../../intent.md), "Decisions still open"). On 2026-11-11, after v2, `self-test`
and `lint` both printed ok.

## Results

165 graded runs:

| Run set | Runs |
| --- | --- |
| Iteration 1 (v1, training, all arms) | 100 |
| Iteration 2 (v2, training, `with_skill` only) | 25 |
| Held out (v2, all arms) | 40 |

The 21 gate runs are not counted. No run was excluded or re-run, and no ruling
(`overrides.json`) was made in any arm. Every skill-arm run read its skill before its
first edit.

Mean pass rate and checks passed, from `harness.py summary`:

| Iteration | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `iteration-1-haiku` (v1) | 94.3%, 90/96 | 85.7%, 81/96 | 92.4%, 88/96 | 92.4%, 88/96 |
| `iteration-1-sonnet` (v1) | 98.6%, 63/64 | 94.3%, 60/64 | 97.1%, 62/64 | 95.7%, 61/64 |
| `iteration-2-haiku` (v2) | 98.1%, 94/96 | not run | not run | not run |
| `iteration-2-sonnet` (v2) | 100.0%, 64/64 | not run | not run | not run |
| `heldout-haiku` (v2) | 100.0%, 33/33 | 100.0%, 33/33 | 96.7%, 32/33 | 100.0%, 33/33 |
| `heldout-sonnet` (v2) | 100.0%, 22/22 | 100.0%, 22/22 | 100.0%, 22/22 | 100.0%, 22/22 |

Core checks passed (hidden tests), both models together:

| Split | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| Training, iteration 1 | 25/25 | **19/25** | 25/25 | 25/25 |
| Training, iteration 2 (v2) | 25/25 | not run | not run | not run |
| Held out | 10/10 | 10/10 | 10/10 | 10/10 |

What the numbers show:
- **No graded gain over the reminder or the bare model.** The leads are one or two checks
  at 2 or 3 runs per cell, inside run-to-run variation. Core ties everywhere.
- **The held-out pair, the main test of whether it generalises, is a tie on core.**
  - No arm lost a core check, and every reply in every arm named the billing view that
    holds the reason.
  - The skill did no harm on new material, but there was no gain to carry over.
- **The win over the shipped skill is the shipped skill's harm.** In 6 of 25 iteration-1
  runs the shipped skill found the constraint, broke it, and said so in its reply. The
  bare model and the reminder did this in none.
- **ADR 0001's revisit question.** On these fixtures, the bare model passed every core
  check, so its replies and diffs show no missed context in other files. Discovery itself
  was not measured (see Limits). The pointer twin could not show an effect, because its
  base case was at ceiling too. So this eval gives no evidence for the revisit condition,
  and none against it in larger repositories.
  - Before the runs, Next step 4 and research.md (Counterevidence and limits) said "a null
    result is ADR 0001's revisit trigger". The result was null, but that trigger is not
    applied. The sentence treated "the skill shows no gain" as if it were the ADR's
    condition. The condition needs readers to miss context in other files first, and
    search or a pointer then not to fix it. The bare model passed every core check
    (35/35) and discovery was not measured, so the first half was never observed. This
    reading was decided after the runs.
- **Ungraded differences**, counted from diffs and replies
  ([eval/RESULTS.md](eval/RESULTS.md)):
  - **The named form.** With the skill, the column went where the user asked and the
    load was renumbered in step: 10/10 runs on v1 and again on v2. In iteration 1 the
    reminder did this in 3/10 runs, the shipped skill in 2/10 and the bare model in 0/10.
    The other runs appended it at the end, or left the load broken (3 shipped-skill runs).
  - **v1's stale comment.** v1 left a comment its own change made false in 5/5 runs; every
    other arm fixed it (15/15). v2 fixed it in 5/5.
  - **The sort fix.** v2 kept the sort at the producer (`ORDER BY id`) in 4/5 runs,
    against v1's 2/5. That gain is not established.
  - **Held out, against the skill.** The shipped skill and the reminder wrote the
    billing reason into the code more often (5/5 against 3/5). The bare model did in 1/5.
    On the restraint case the skill's replies reported a search that changed nothing
    (5/5), against its own Report rule. So did the reminder's (5/5).
  - **Reply length.** Replies ran 10 to 21% longer than the bare model's. They were
    shorter than the reminder's in the iterations where both ran.

## Limits

Of the eval:
- **Few runs.** 2 or 3 runs per cell detect only large effects: 3/3 against 0/3 has a
  two-sided Fisher exact p of 0.10, and 2/2 against 0/2 has 0.33. The arms tie at the
  ceiling in most cells, so the eval cannot rank them.
- **Small fixtures.** Seven small Python cases of 12 to 16 files each. A model can read
  all of one, so they cannot show what happens in a repository too large to read, where
  a search returns hundreds of hits.
- **One model family.** Claude Haiku and Sonnet only.
- **Cases built by agents.** Every case, reference and hidden test was written by an
  agent. None comes from a real repository or a user's report.
- **Audits made by an agent.** An auditor agent, not a human, read every failed check
  and the passing results of every heuristic check, and decided to make no rulings. It
  left three close calls unruled. The two on held-out Sonnet replies would lower the
  reminder and shipped-skill arms, not this skill.
- **Skill reads cannot be re-checked.** The `verify-reads.json` files were made from
  transcripts that are not stored in the repository. No script in the repository writes
  their other-arm and wrong-model lists; they come from the out-of-repository wrapper
  described in [incubator/README.md](../README.md).
- **Gate-based case selection.**
  - A bare-model gate ran first on all seven cases, the held-out pair included. Four
    cases were then hardened to leave room for a gain ([eval/GATE.md](eval/GATE.md)).
  - The bare gate was not re-run on the hardened fixtures. Iteration 1's bare arm was the
    first bare result on them, and it still passed every core check.
  - Selection by a bare gate favours cases where the bare model falls short. Here it
    found none.
- **Prompt read from a file.** Each agent read its task from `prompt.txt` instead of
  receiving it as a user's message, which is not how real requests arrive.
- **Activation is untested.**
  - The eval tells the agent to read the skill first, so it says nothing about whether
    the description makes the skill load on its own.
  - On its own, the shipped skill loaded in 0 of 18 Haiku and 3 of 18 Sonnet should-load
    runs.
  - This skill's trigger words (simplify, remove dead code) also compete with other
    installed simplification skills.
- **No core headroom.** The bare model passed all 35 of its counted core checks. So the
  eval never tested the skill's central claim where the bare model fails.
- **Key behaviours are ungraded.** These are where the column went, whether a now-false
  comment was fixed, and where the sort went. They come from the writer's reading of
  diffs and replies, and their p-values are on comparisons chosen after reading the runs.
- **Iteration 2 is compared across runs.** v2 ran only `with_skill`, so v2 is compared
  with the other arms' iteration-1 runs.
- **Discovery was not measured.** [eval/discovery.py](eval/discovery.py) was never run,
  so whether each run found the evidence is inferred from its reply and diff. It is
  still untested on real transcripts.
- **Tokens, turns and cost were not measured.**
- **The held-out pair is spent.** It ran once, on v2, and cannot judge a later version.
  It tests the trigger only on a "simplify" request; the dead-code and add-a-field
  requests are training cases.

Of the skill:
- **Grep is incomplete.** It misses:
  - names built at run time with no searchable fixed part;
  - SQL assembled as strings;
  - other repositories.

  Reliance that nobody wrote down, and that the code at a mention does not show, is out
  of scope by design: by Hyrum's Law almost every behaviour has some. No case tests
  reliance that only the code shows.
- **Some rules are not exercised.** No fixture has a hidden directory, so the `--hidden`
  rule goes untested. No case has stale text that the change leaves true, so v2's "leave
  it as it is" branch is untested.
- **It does not always follow its own rules.**
  - One v2 Haiku run still moved the sort into a consumer. Its reply named the cheaper
    producer-side fix and did not use it.
  - Every held-out restraint reply reported a sweep that changed nothing.
- **It asks for no new comments.** On held-out first-wins it wrote the reason beside
  the code less often than the shipped skill. That rule may be why; that is an
  interpretation, not tested. If both skills are installed together that may not matter,
  but no arm tested them together.
- **The pointer comparison rests on one task**, and both twins were at ceiling.
- **Overlap with C2.** The skeptic judge would give `stale-constraint-elsewhere` to
  verify-before-relying. Read their results on it together.

## Next steps

The gate, the four-arm run, one revision and the held-out run are done. In order:

1. **Put the deliverable to the user.** The graded data supports recommending the
   reminder sentence in [eval/arms.json](eval/arms.json), not this skill. Do not move the
   skill into a plugin unless the user decides otherwise.
   - The reminder showed no graded gain over the bare model either. Both passed core
     25/25 and 10/10, and on all checks they were within one check of each other in
     every iteration. So this rests on the tie rule set before the runs, not on a measured
     benefit of the sentence.
2. **Ask the user whether the named form matters.** It is the skill's one consistent
   edge: the column went where the user asked, with the load renumbered, in 10/10 runs
   on v1 and again on v2, against 3/10 for the reminder in iteration 1. The graders
   accept appending at the end with an explanation.
   - If the user wants the named form kept, add one sentence on it to the reminder
     ("keep the form I asked for, and update what depends on it").
   - Then run that arm against `with_skill` on the positional pair, Haiku x3 and
     Sonnet x2.
3. **Report the shipped-skill harm to the owners of #21 and #48.** In iteration 1 the
   shipped skill found a constraint, broke it and said so in its reply, in 6 of 25 runs.
   - The runs are in `eval/iterations/iteration-1-haiku/`:
     `positional-columns-in-sql/shipped_skill/run-{2,3}`,
     `positional-columns-in-sql-pointer/shipped_skill/run-2` and
     `sort-relied-on-elsewhere/shipped_skill/run-{1,3}`.
   - Plus `eval/iterations/iteration-1-sonnet/sort-relied-on-elsewhere/shipped_skill/run-1`.
   - The cause is a hypothesis: possibly its "make the change if asked and tell the user"
     conflict rule. Test it with a targeted eval of the shipped skill before changing it.
4. **Build cases with core headroom before any more skill edits.** The bare model passed
   35 of 35 core checks, so hardening by indirection did not work at this size. Try:
   - repositories too large to read in full;
   - names built at run time with no searchable fixed part;
   - a constraint in a hidden directory (`.github/`), which also exercises `--hidden`;
   - the reserve cases in the candidate record (`none-means-walk-in`,
     `none-means-missing`, `cron-budget-in-shell`).

   Gate each on the bare model (Haiku x3, Sonnet x2) and keep only cases with bare core
   failures. Build a fresh held-out pair, since this one is spent.
5. **Grade the ungraded behaviours.** Add checks to `eval/grade.py` for:
   - where the positional column went, reported as its own measure rather than a
     failure;
   - whether a comment the change made false was corrected, not only reported (tighten
     `stale-constraint-elsewhere` 05);
   - whether the sort fix stayed at the producer.

   Run `self-test`, then re-grade every iteration.
6. **Add a case for the untested stale branch.** It needs stale text that the change
   leaves true, to check that v2's correction rule does not spread into edits nobody
   asked for.
7. **Measure discovery and cost.**
   - Run [eval/discovery.py](eval/discovery.py) on the recorded transcripts (the
     workflow's `wf_*` folders that `verify-reads` used). Check its first real report by
     hand against a few transcripts.
   - Count tokens and turns per arm.
8. **Settle the Report rule.** Every held-out `with_skill` reply reported a search that
   changed nothing. Either drop "Mention the sweep only when..." or find out why it is
   ignored.
9. **Before any shipping decision:**
   - run an activation eval with should-load requests (simplify, speed up, raise instead,
     remove dead code) and near misses (find callers, explain, a new file);
   - add an arm with both this skill and `code-comments` loaded, since that is how they
     would ship;
   - use 5 or more runs per cell, and a model outside the Claude family.
10. **Close the lint gap.** The leak checks in `incubator/harness.py` and
    `scripts/lint_skills.py` only read `.md`, `.py` and `.json` (plus `.ts`/`.js` in the
    harness). So fixture text in `.sql`, `.ini`, `.yaml` and `.sh` is not checked
    against `SKILL.md`.
11. **Defer a script.** Write the candidate's `sweep.py` only if transcripts show misses
    that the recipe would not catch. Keep it to definitions, pointers and mentions with
    their nearest comment.
