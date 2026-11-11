# constraint-sweep

**Status: built; evaluation pending.** No run has been graded, so nothing here is a
result. The skill makes no performance claim.

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
the only record of that is a comment over there: a caller that needs its input in order,
a database load that reads fields by position, a config file that names a function as a
string. The agent never opens that file, the visible tests still pass, and the break
turns up later.

This is the gap that [ADR 0001](../../docs/adr/0001-context-lives-inline-no-central-index.md)
leaves to search. Context lives inline, and an agent finds context in another file only
by searching for it. The ADR's "Revisit if" clause is about exactly this failure: "the
agent never opens or searches the file that holds the fact". The shipped skill covers
the writing half (put the fact beside the code). Nothing tells the reader to search.

What the evidence says (details and limits in [research.md](research.md)):
- **Discovery has never been measured in this repository.** All 11 hygiene prompts list
  their input files, and their fixtures hold 2 to 7 files.
- **No run in this repository has broken behaviour.** That covers round 1, the pilot, and
  all 15 iteration-5 `reason-only-in-test` runs. So the headroom this skill targets is a
  hypothesis, which the no-skill gate must confirm.
- **Outside this repository, behaviour changes slip past visible tests.** In Dristi and
  Dwyer, 19-35% of LLM refactorings changed behaviour, and about 21% of those passed the
  existing tests. In Wang, Pradel and Liu, 29.6% of plausible SWE-bench patches behaved
  differently from the reference. Liu et al. name "logical dependencies that are not
  explicitly enforced by the code structure" as a failure class.
- **What a search finds depends on its options.** In a local probe, default ripgrep
  skipped `.github/`, `--hidden` also entered `.git/`, a `-t py` filter missed INI and
  JSON references, and a name built at run time matched only its fixed prefix.

## What it adds over the shipped skill

The shipped [`code-comments` skill](../../plugins/code-comments/skills/code-comments/SKILL.md)
governs the comment text a change leaves behind. Its one search line, "Before
simplifying, look for it in tests, callers and docs", is there to find a reason to write
down, and hygiene iteration 2 found that "The new "look in tests" line did not produce
the behaviour" ([evaluation/hygiene/README.md](../../evaluation/hygiene/README.md)).

This skill governs what the agent reads **before** changing behaviour, and whether the
code still honours constraints stated in other files. It adds:
1. **A trigger on behaviour changes**, including requests that look local: simplify,
   speed up, raise instead, remove dead code, add a field or argument.
2. **Named symbols and their own pointers.** List what will change, then open every
   file or symbol its docstring and comments name.
3. **An exact search recipe.** Word-bounded, every file type, hidden directories in,
   `.git/` out, plus the dotted and slash module paths, runtime-built names and import
   aliases.
4. **A way to sort mentions.** Each mention either states nothing, or states a
   constraint that is **live** (the code there still depends on it) or **stale** (it
   no longer does).
5. **What to do with each.** Keep a live constraint: keep the property where it is
   produced; if the request itself changes the property, update the dependent sites in
   the same change; failing both, make the change and report the break. Keep the form
   the user named (a position, a name, an error type). Report a stale constraint and do
   not obey it. Treat reliance the code at a mention demonstrably has as a live
   constraint, and only name suspected reliance in the reply. Treat a name in config, a
   string or a script as a use when removing dead code. Leave files whose mentions state
   nothing alone.

It writes no comments. When a change needs one, the agent follows `code-comments`.

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

Instructions only: a `SKILL.md` with a 95-line body. There is no script, caller graph
or usage-flag analysis. It reads the code on each run and stores nothing: no index,
generated docs view, memory store or lookup service (ADR 0001). The search runs at edit
time with `rg` or `grep`.

The steps, in the order the agent meets them:
1. **Name the symbols** whose behaviour will change, with module and file paths.
2. **Follow the symbol's own pointers** in its docstring, comments and module header.
   This is ADR 0001's pointer mitigation.
3. **Search every text file** with
   `rg -n -w --hidden -g '!.git' NAME` and `rg -n -F --hidden -g '!.git'` on the dotted
   and slash paths, with no type or glob filter. The fallback is
   `grep -rnw --exclude-dir=.git NAME .`. Runtime lookups and import aliases get extra
   searches.
4. **Sort each mention** by the code there, the comment on or above it, the enclosing
   docstring and the test name: states nothing, live constraint, or stale constraint.
5. **Change the code** to keep live constraints in the form the user named, report
   stale ones, and leave the rest alone.
6. **Report** each constraint that shaped the change, each stale one and each site of
   suspected reliance, with file:line. The skill does not mention the sweep when it
   changed nothing.

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
| No comments, instructions only | ADR 0001 reasons 2 and 4; the coordinator's direction | practitioner |

Two rules in the skill are marked *judgement*: narrowing a common name to its qualified
forms, and naming a suspected but unconfirmed dependency in the reply instead of coding
around it. The line telling the agent to make sure a built-in search tool covers hidden
directories rests on an open question: no documentation was found on whether Claude
Code's Grep tool skips them.

## Its eval

Seven cases in [eval/](eval/), five for training and two held out. Each fixture is a
small Python repository of 11 or 12 files. The prompts list no files, because finding
the context is what is measured. Each fixture also mentions the changed symbol in places
that state nothing binding.

| Case | Split | `core_needs_other_file` | What it tests |
| --- | --- | --- | --- |
| `sort-relied-on-elsewhere` | training | true | drop a sort the user thinks nothing needs, without breaking a consumer that needs the order |
| `dispatched-by-name` | training | true | remove dead code but keep a function a config file names as a string |
| `positional-columns-in-sql` | training | true | add a field "next to" another without breaking a positional SQL load |
| `positional-columns-in-sql-pointer` | training | false | the same task with a one-line pointer to the SQL in the edited file (ADR 0001's pointer mitigation) |
| `stale-constraint-elsewhere` | training | false | restraint: a stated constraint the code no longer relies on must not block the change, and is reported |
| `mention-without-constraint` | held out | false | restraint: descriptive mentions trigger no edits, defences or questions |
| `first-wins-reason-in-caller` | held out | true | simplify a loop the user thinks can keep any duplicate, and keep the first, a rule stated only in a caller |

The third column is `core_needs_other_file`: the evidence that rules out the natural
wrong edit is found only in another file, and nothing in the edited file points to it.
`case.yaml` also records `context_in_other_file`, `pointer_at_edit` and `evidence_in`
(the files holding the needed evidence). An earlier control, `mirrored-column-order`,
had a different task, so it mixed task difficulty with where the context lives. It was
replaced by the pointer twin before any run and is kept in `eval/reserve/`.

Core checks are hidden tests in `eval/hidden/<case>/hidden_tests/`. They exercise the
consumer, not the edited function alone. Restraint checks confirm the request was done
(so refusing loses) and that files the run only read are byte-identical. Reply checks
are keyword heuristics, reported apart from the rest, and most are scored only when the
outcome they describe happened.

There are four arms:
- `with_skill` reads this `SKILL.md` first.
- `shipped_skill` reads the shipped `code-comments` skill first. This is the
  falsification test: if it ties, constraint-sweep is a variant of the shipped skill and
  belongs under #21/#48.
- `reminder` adds the sentence in [eval/arms.json](eval/arms.json) to the request: grep
  the whole repository, every file type, for the names being changed, and keep or report
  any constraint stated there. If it ties the skill, recommend the sentence.
- `without_skill` gets the request alone.

**ADR 0001's revisit question.** [eval/discovery.py](eval/discovery.py) reads the
agent transcripts and reports whether each run read or searched its case's
`evidence_in` files before its first edit, which separates "never found it" from "found
it and ignored it". The bare arm's discovery and core pass rates on the
`core_needs_other_file` cases show whether readers miss context in other files.
`positional-columns-in-sql` against its pointer twin shows whether a pointer at the
point of edit fixes it, on the same task. `with_skill` and `reminder` against the bare
arm show whether search fixes it. [eval/CASES.md](eval/CASES.md) has the detail.

Commands, from the repository root:

```sh
python incubator/harness.py self-test constraint-sweep   # references pass, inputs fail
python incubator/harness.py lint constraint-sweep        # format, portability, no copied case text

# 1. Gate: bare model only, training cases plus first-wins (Haiku x3; repeat with Sonnet x2)
python incubator/harness.py prepare constraint-sweep --iteration iteration-0-gate-haiku --arms without_skill --runs 3 --split train
python incubator/harness.py prepare constraint-sweep --iteration iteration-0-gate-haiku --arms without_skill --runs 3 --cases first-wins-reason-in-caller
#   ...give each prompt in eval/iterations/<name>/runs.json to a fresh agent of the chosen model...
python incubator/harness.py grade constraint-sweep --iteration iteration-0-gate-haiku
python incubator/constraint-sweep/eval/discovery.py --iteration iteration-0-gate-haiku TRANSCRIPT_DIR

# 2. All four arms on the training cases
python incubator/harness.py prepare constraint-sweep --iteration iteration-1-haiku --runs 3 --split train
python incubator/harness.py grade constraint-sweep --iteration iteration-1-haiku
python incubator/harness.py verify-reads constraint-sweep --iteration iteration-1-haiku TRANSCRIPT_DIR
python incubator/constraint-sweep/eval/discovery.py --iteration iteration-1-haiku TRANSCRIPT_DIR

# 3. Held-out pair, once, after the last skill edit
python incubator/harness.py prepare constraint-sweep --iteration held-out-haiku --runs 3 --split held-out
python incubator/harness.py grade constraint-sweep --iteration held-out-haiku

python incubator/harness.py summary constraint-sweep iteration-1-haiku iteration-1-sonnet
```

Repeat each step with a `-sonnet` iteration. `verify-reads` lists any skill-arm run that
edited before reading its skill; exclude and re-run those. Running the bare gate on the
held-out `first-wins-reason-in-caller` does not tune the skill, so it does not spend the
case; its skill arms still run only once, at the end. Model runs cost money, and
each campaign needs the user's approval first ([intent.md](../../intent.md), "Decisions
still open"). On 2026-11-11, `self-test` and `lint` both printed ok.

## Limits

- **Headroom is unproven here.** No repository run has broken cross-file behaviour. If
  Sonnet greps the name unprompted, a plain search already finds the INI, JSON and SQL
  mentions, and only the harder variants stay hard.
- **Activation is untested.** The eval tells the agent to read the skill. On its own the
  shipped skill loaded in 0 of 18 Haiku and 3 of 18 Sonnet should-load runs. The trigger
  words (simplify, remove dead code) also compete with other installed simplification
  skills.
- **Grep is incomplete.** It misses names built at run time with no searchable fixed
  part, SQL assembled as strings, and other repositories. Reliance that nobody wrote
  down and the code at a mention does not show is out of scope by design: by Hyrum's
  Law almost every behaviour has some. No case tests reliance that only the code shows.
- **The pointer comparison rests on one task.** The positional pair isolates the pointer
  on one fixture; it does not show that pointers help on other kinds of constraint.
- **Some skill rules are not exercised.** No fixture has a hidden directory or a name
  built only at run time, so the `--hidden` and runtime-name rules go untested.
- **The stale rule may fail either way.** No study shows that an instruction to check a
  comment's claim reduces harm (P-21 is grade D). The agent may still obey a stale
  comment, or start ignoring live ones.
- **Noise is unmeasured.** In a large repository a common name returns hundreds of hits.
  Fixtures of 11 or 12 files cannot show that cost, or whether the agent stops early.
- **The sweep adds reads.** Tokens and turns per arm are unmeasured. The hygiene skill
  added about 6%.
- **The held-out pair differs from research.md's suggestion.** The eval holds out
  `mention-without-constraint` and `first-wins-reason-in-caller`. The dead-code request
  type (`dispatched-by-name`) is therefore a training case, so only the simplify request
  tests whether the trigger generalises.
- **Overlap with C2.** The skeptic judge would give `stale-constraint-elsewhere` to
  verify-before-relying. If both skills are evaluated, read their results on it together.
- **Small evidence base**: seven small Python cases, few runs, one model family.

## Next steps

1. **Run the gate** (`without_skill`, training split plus `first-wins-reason-in-caller`,
   Haiku x3 and Sonnet x2). Harden or drop any discovery case that both bare models
   pass, and record the decision. `dispatched-by-name` is the likeliest to sit at
   ceiling; [eval/CASES.md](eval/CASES.md) gives the hardening (a handler name built at
   run time).
2. **Measure discovery apart from outcome.** Run [eval/discovery.py](eval/discovery.py)
   on every iteration's transcripts. It has been tested on synthetic transcripts only,
   so check its first real report by hand against a few transcripts.
3. **Run all four arms** on the training cases. Read the core and restraint columns as
   the headline (the harness ignores grader weights), and split core results by
   `core_needs_other_file` and by the positional pair.
4. **Decide the deliverable.** If `shipped_skill` ties, record a variant finding for
   #21/#48. If `reminder` ties, recommend the sentence. Publish either result, and a
   null result is ADR 0001's revisit trigger.
5. **Run the held-out pair once**, after the last skill edit.
6. **Close the lint gap.** The leak checks in `incubator/harness.py` and
   `scripts/lint_skills.py` only read `.md`, `.py` and `.json` (plus `.ts`/`.js` in the
   harness). Fixture text in `.sql`, `.ini`, `.yaml` and `.sh` is not checked against
   `SKILL.md`.
7. **Before any shipping decision,** run an activation eval with should-load requests
   (simplify, speed up, raise instead, remove dead code) and near misses (find callers,
   explain, a new file). Consider the reserve cases in the candidate record:
   `none-means-walk-in`, `none-means-missing` and `cron-budget-in-shell`.
8. **Defer a script.** Write the candidate's `sweep.py` only if transcripts show misses
   that the recipe would not catch, and keep it to definitions, pointers and mentions
   with their nearest comment.
