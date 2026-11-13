# change-drift-sweep: research

Ideation candidates C3 and C7 ([candidates](../ideation/2026-11-11-candidates.json)). The
coordinator of #50 changed the order: value drift in comments and docstrings comes first, then the
Markdown docs that are still kept. Review mode for finished diffs (C7) is out of scope for v1.
Anything not quoted from a source is our interpretation. A rule with no source is labelled a
hypothesis.

## Question

After a change gives something a new value, name or place, prose elsewhere (a comment, a
docstring in another module, a Markdown doc) can still state the old value: in digits, as a number
word ("fifty"), in another unit (900 s as "15 min") or as a figure worked out from it (a backoff
total, a product, a per-day count). Can an agent find all of it, correct the living descriptions of
the code, and leave records and outside facts word for word? Does a stdlib script that writes and
stores nothing make the search more reliable? And does this beat the bare model, a one-line
reminder, and the shipped skill's "fix every comment your change made false"?

## Sources

All accessed 2026-11-11. Each web source was opened, and its quote was checked on the page. No PDF
was converted.

**Repository evidence**
- **R1.** [hygiene-skill.md](../../docs/skill/hygiene-skill.md), "What it is not": "A comment that
  says "retries three times" when the code retries five times names nothing missing, so only
  reading catches it." Activation: the skill loaded on its own in 0 of 18 Haiku runs and 3 of 18
  Sonnet runs.
- **R2.** [Shipped SKILL.md](../../plugins/code-comments/skills/code-comments/SKILL.md): "fix or
  delete every comment your change made false. That includes comments outside the lines you
  edited"; "the source of a constant, not its copied value"; "Keep the outside fact (a vendor
  quota, a law, another team's limit) as written"; "Describe the current design, not its history."
- **R3.** Hygiene `retry-cap-elsewhere`, recounted from `evaluation/hygiene/iterations/*/retry-cap-elsewhere/*/run-*/grading.json`:
  37 graded runs, 33 distinct (iteration 5 Haiku reuses 4); Haiku ran 9 of the 11 bare runs. The
  stale-figure check failed once, Sonnet `without_skill` run 1: "found ['14 seconds', '2, 4 and 8']".
  The line left was `fetcher/client.py:28`, "# Waits are 2, 4 and 8 seconds: 14 seconds in all before
  we give up.", in a file the run had edited; its diff recomputed the doc's total right ("A report
  that still fails after about 62 seconds"). The prompt lists every input file ("Input files: ...").
- **R4.** [Hygiene README](../../evaluation/hygiene/README.md), iteration 5: "two Haiku reminder runs
  and one Sonnet reminder run deleted the vendor's free-tier quota". Also: "Five cases still do not
  discriminate", and `rename-stale-refs` is one of them.
- **R5.** [scripts/stale_refs.py](../../scripts/stale_refs.py) docstring: "A name the project's
  Markdown or reST docs put in backticks also counts"; Markdown is read only for known names, and
  values are never compared. [Command doc](../../plugins/code-comments/commands/stale-refs.md): "it
  cannot tell whether a comment's claim about behaviour is still true". Scratch fixture
  (`%TEMP%/c3research2/fx`, `MAX_ATTEMPTS` 4 to 6, `--since` renamed `--after`): a comment saying
  "four attempts, waiting 1, 2 and 4 s: about 7 s" and `docs/cli.md` showing `export --since` both
  survived; `--base-dir` exited 0.
- **R6.** [human-maintenance-and-drift.md](../../docs/research/human-maintenance-and-drift.md): "comments
  on interfaces and callers lag". **R7.** [context-layers.md](../../docs/research/context-layers.md),
  Nygard row: "Records are never rewritten; a reversed one is marked superseded."
- **R8.** [principles.md](../../docs/skill/principles.md). P-27 (grade C): "Do not restate numbers,
  rule tables or exception lists the code already holds". P-26: "Code that only coincidentally
  matches is not duplication." P-29 quotes Parnas: "If a change invalidates a design document, it
  and all subsequent design documents must be faked to look as if the change had been the original
  design."
- **R9.** [comment-context-deep-dive.md](../../docs/research/comment-context-deep-dive.md), on C4RLLaMA:
  "nor can code consistency alone decide whether code violated the requirement or the comment
  became obsolete."
- **R10.** [ADR 0001](../../docs/adr/0001-context-lives-inline-no-central-index.md): "Mechanical checks
  that read the code itself remain compatible with this decision."
- **R11.** Sibling skills. The [fold-docs-inline](../fold-docs-inline/skill/fold-docs-inline/SKILL.md)
  description says it is "Not for updating a doc after a code change". [verify-before-relying
  research](../verify-before-relying/research.md) S20 notes that eval subagents can see an AGENTS.md
  outside the fixture.

**Drift in documents and its cost**
- **W1.** Tan, Wagner and Treude, *Detecting Outdated Code Element References in Software Repository
  Documentation*, EMSE ([ar5iv](https://ar5iv.labs.arxiv.org/html/2212.01479)): "28.9% of the most
  popular projects on GitHub currently contain at least one outdated reference"; "Our approach also
  cannot detect outdated relationships between the repository and documentation if the code
  elements are still present."
- **W2.** Gao and Chen, *From Agent Behaviour to Agent-Friendly Documentation*, [arXiv 2608.20195v1](https://arxiv.org/html/2608.20195v1):
  "which is 37.0% of the 28,574 code-touching PRs"; "code comes first in 82.5% of orderable cases";
  "Documentation is identified by file path."
- **W3.** Gao, Lin, Treude, Gay and Zahedi, *Does My README File Need To Be Updated?*, [arXiv 2603.00489](https://arxiv.org/abs/2603.00489):
  "21.5% of temporally matched recommendations identify updates overlooked by developers" (6.1% on
  the most conservative reading).
- **W4.** Radmanesh et al., [arXiv 2409.10781v1](https://arxiv.org/html/2409.10781v1), labels by
  GPT-3.5: "inconsistent changes are around 1.5 times more likely to lead to a bug-introducing
  commit than consistent changes."

**Detectors and updaters (prior art)**
- **W5.** Panthaplackel et al., AAAI 2021, [arXiv 2010.01625](https://arxiv.org/abs/2010.01625): "detect
  whether a comment becomes inconsistent as a result of changes to the corresponding body of code".
  **W6.** Ratol and Robillard, Fraco, ASE 2017 ([project page](http://cs.mcgill.ca/~swevo/Fraco/)), a
  Java Eclipse plug-in: "Fragile comments are those comments that become inconsistent with the
  related source code upon renaming a program element." The page gives no numbers.
- **W7.** Ge et al., *LLMCup*, [arXiv 2507.08671v1](https://arxiv.org/html/2507.08671v1). It describes
  HebCup (Lin et al., ICPC 2021) as "A simple yet effective heuristic alternative to CUP that updates
  comments via token-level edits"; its Table I gives accuracy 0.257 for HebCup, 0.177 for CUP, 0.383
  for LLMCup. LLMCup "performs worst on Non-Code-Ind & Multi-Tokens (0.095, 374/3922), highlighting
  challenges in understanding or inferring comment changes that lack code anchoring." Table V: 4,896
  of 8,125 test samples are non-code-indicative. HebCup's own paper is PDF-only; unverified here.
- **W8.** Zhong et al., *CCISolver* (method level), [arXiv 2506.20558](https://arxiv.org/abs/2506.20558):
  "a substantial portion of sampled data are mislabeled." **W9.** Kiecker et al., *CASCADE*,
  [arXiv 2604.19400](https://arxiv.org/abs/2604.19400): "false positives carry serious consequences:
  wasting developer time and discouraging practical adoption."
- **W10.** Tools. [Doqtor](https://github.com/cachevector/doqtor) analyses "changed functions,
  parameters, and types" and opens fix PRs. [borghei doc-drift-detector](https://borghei.github.io/Claude-Skills/skills/engineering/doc-drift-detector.html),
  a Claude skill with stdlib scripts, covers "Structural, factual, referential, temporal, semantic"
  drift with a "weighted 0-100 freshness score", AST signature checks and link checks; its page does
  not say it compares values or handles records. [Swimm Auto-sync](https://docs.swimm.io/features/keep-docs-updated-with-auto-sync/)
  "automatically keeps code snippets up to date with routine code changes via your CI" and marks
  the rest "potentially out of date".

**How prose states numbers, and what records are**
- **W11.** [Microsoft Writing Style Guide, Numbers](https://learn.microsoft.com/en-us/style-guide/numbers):
  "In body text, spell out whole numbers from zero through nine, and use numerals for 10 or
  greater."; "Spell out zero through nine ... for days, weeks, and other units of time"; "Use commas
  in numbers that have four or more digits." **W12.** [Google developer documentation style guide](https://developers.google.com/style/numbers)
  spells out "Numbers from zero through nine" but uses numerals for "Technical quantities, such as
  amounts of memory, amounts of disk space, numbers of queries, or usage limits."
- **W13.** [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/): "A changelog is a file which
  contains a curated, chronologically ordered list of notable changes"; "Keep an `Unreleased` section
  at the top to track upcoming changes."; and in its FAQ, "There are always good reasons to improve a
  changelog." **W14.** Nygard, [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions):
  "If a decision is reversed, we will keep the old one around, but mark it as superseded."

## Findings

Observations only; interpretation follows.

1. **No mechanical check we found sees value drift.** stale_refs ignores values and Markdown prose
   (R5, confirmed on the fixture). Tan's detector "cannot detect" drift while the named element
   still exists (W1). Doqtor's and borghei's pages describe names, signatures, examples, links and
   freshness scores, not values (W10).
2. **Detection research checks the comment on the changed code**: the comment on the changed body
   (W5), method level (W8), Java renames (W6). We found no study of value drift in distant prose or
   Markdown, so its frequency is unmeasured; W1 is a names-only lower bound.
3. **Token-level heuristics update comments well; unanchored edits are the hardest.** HebCup beat a
   learned model, and LLMCup did worst on changes that "lack code anchoring"; non-code-indicative
   updates were 60% of its test set (W7). A number word, a converted unit or a derived total is not
   anchored in the code diff (our reading).
4. **The repository's one recorded value-drift miss was a derived figure that does not contain the
   old value.** "2, 4 and 8" and "14 seconds" do not include 3. The line was in a file the run had
   edited, and the same run computed the doc's new total right (R3). It was 1 of 33 distinct runs,
   the prompt listed every file, and every Haiku bare run passed.
5. **Bare models already handle renames and a single distant mention** when told which files exist
   (R4). Caller and interface comments lag (R6).
6. **Prose writes numbers in both forms, and style guides disagree.** Microsoft spells out zero to
   nine, including units of time, and puts commas in four-digit numbers (W11). Google uses numerals
   for technical quantities and usage limits (W12). A search for digits misses "seven seconds". A
   search for words misses "15 min". A search for "1800" misses "1,800".
7. **A reminder to fix whatever the change made false over-applied.** It deleted a true outside
   quota in 3 of 5 runs (R4).
8. **Records are true about their own date.** Changelog entries belong to a version (W13). ADRs are
   superseded, not rewritten (W14, R7). But Keep a Changelog allows improving old entries (W13), and
   Parnas would rewrite a *design* document so that it reads as the new design (R8). Which documents
   count as living is a judgment.
9. **Docs trail code** in agent PRs (W2), developers miss README updates (W3), and inconsistent
   changes are associated with later bugs (W4, LLM labels).
10. **False alarms are the main cost of detectors** (W9); detection benchmarks are often mislabelled (W8).

**Prior art, and how this skill differs.** The detectors and tools above work on names,
signatures, examples, links, snippets or the method's own comment; learned updaters need a model;
Doqtor opens PRs, and Swimm keeps docs in its own format, a second artefact (R10). This skill acts
at the edit, is value-aware (digits, number words, units, derived figures), searches all prose
including other modules and Markdown, sorts each hit (living, record, outside fact, unrelated), and
its script only reports. It sits beside the shipped skill, whose rule 1 says to fix false comments
(R2) but gives no way to find value restatements and no protection for records. fold-docs-inline
excludes post-change doc updates (R11).

## What this means for the skill's rules

The mechanism is instructions plus an optional `scripts/value_drift.py`.

1. **Sweep before finishing, after you re-value, rename or move** a constant, default, limit,
   timeout, count, size, unit, flag, config key or file. Only reading catches value drift (R1, R5).
   The trigger list is a hypothesis.
2. **List the old forms before you search**: digits with and without thousands separators, number
   words (W11, W12), every unit form (900 s, 15 min, "fifteen minutes"), and every figure derived
   from the old value (totals, products, wait sequences, per-day counts). Search each (Findings 3,
   4). That the list improves recall is a hypothesis.
3. **Search all of the prose**: comments and docstrings in every module, and Markdown and other text
   docs, not only the files you edited (R3, R6, W1, W2). Use the script if you can. If not, grep the
   same list (R10; the coordinator's requirement).
4. **Read each hit in context. The script finds candidates; you decide.** Change a hit only when its
   sentence is about the thing that changed. Leave a fact that shares the number but describes
   something else (P-26 in R8; W9).
5. **Sort each hit.** A **living description** (comment, docstring, README, current doc): correct
   only the false clause, rest word for word (R2). A **record** (released changelog entry, ADR,
   dated report, incident or migration note): leave it word for word (W13, W14, R7). An **outside
   fact** (vendor, other team, law): keep it, report any conflict (R2, R4). **Unrelated**: leave it.
6. **Recompute derived figures from the code** (arithmetic shown or a one-line snippet), never by
   analogy (R3). That a snippet prevents errors is a hypothesis.
7. **A comment that points to the constant needs nothing.** Do not copy the new value into it, and
   add no "changed from 4" note (R2, P-27, P-29).
8. **Drift your change did not cause: report it, do not fix it.** Nothing shows which side is right
   (R9).
9. **If the change contradicts an ADR, leave the ADR alone** and say it may need superseding (W14).
   Add a changelog line only under an existing `Unreleased` heading (W13). Whether to add one at all
   is open (question 4).
10. **Report** what you corrected, the records and outside facts you kept, pre-existing mismatches
    and any conflict (R2).
11. **Renames and moves:** also run stale-refs for code comments. Search Markdown by hand for
    backticked names, fenced examples and relative links, because stale-refs skips them (R5).

**The script, `value_drift.py ROOT --old V [--old V2 ...] [--new N] [--unit s|ms|min|h|day]`.** It
reads files with `tokenize`, `ast` and line scans every run, writes nothing and exits 1 on hits. It
prints `file:line`, the matched form (digits, word, converted unit) and a path hint (`record?` for
CHANGELOG*, HISTORY*, NEWS*, docs/adr/** or dated filenames) that decides nothing (Finding 8). It
reads Python comments and docstrings, `#` and `//` comments elsewhere, and Markdown prose with
fenced blocks labelled. `--old` repeats, so the agent passes rule 2's old derived figures; the
script cannot compute them. `scripts/test_value_drift.py` should cover word bounds (`15` vs `150`,
`1.5`), "1,800", "fifteen", "twenty-five", "15-minute", "15 min", ignored code literals, the record
hint, and that no file is written.

## What this means for the eval

- **Run a gate first.** In the hygiene eval, the derived miss was 1 of 33 distinct runs, with every
  file listed (R3). These prompts list no files. Run the bare arms on both models before anything
  else, and drop a case that every bare run passes.
- **The reminder in `arms.json` names number words, unit conversions, derived figures, records and
  outside facts.** It states most of rules 2 and 5 in one sentence, so a tie on the core checks is
  likely. The skill has to win on precision (unrelated numbers, records) or on derived figures. If
  it does not, report the tie.
- **The shipped-skill arm** tests whether rule 1 plus its outside-fact line already does this. Under
  rule 1, a literal reading may rewrite records. Score that apart.
- **Record per run whether `value_drift.py` ran and what it listed.** This separates the value of
  the script from the value of the instructions. It also measures the script's false-positive load
  on each fixture (W9).
- **Grade new figures, not only the absence of old ones** (derived-backoff-total check 03).
  Sentence-regex checks will need overrides for wordings such as "half an hour", as CASES.md plans.
- **Keep the held-out cases** (pointer-comment restraint, per-day) **out of skill edits**.
- **Instruction files stay out of the cases**: subagents can see an outside AGENTS.md (R11).
- **A reserve case (hypothesis):** a size in KB or MB, where prose may mean 1,000 or 1,024.

## Counterevidence and limits

- **Headroom is thin and unmeasured.** The only recorded miss is one Sonnet run (R3). Nothing shows
  bare models rewriting a CHANGELOG or an ADR. How often value drift happens in distant prose has
  never been measured (Finding 2).
- **The record boundary is a policy.** Keep a Changelog invites improving entries (W13). Parnas
  rewrites design documents to look as if the change came first (R8). A misjudged "record" leaves a
  living doc false. A misjudged "living" doc rewrites history. The user should confirm the rule.
- **Number forms are open-ended** ("a quarter of an hour", "twice a day", both kinds of KB); the
  word table will miss some, and reading cannot recover what the search never listed. In
  number-heavy files the script may flood the agent into editing unrelated numbers (W9).
- **The research base is narrow:** method-level comments, mostly Java, learned models, doubtful
  labels (W5 to W8); none tests an agent following instructions. We did not run Doqtor or
  borghei's scripts, which may cover more than their pages say.
- **Activation:** the shipped skill rarely loads on its own (R1); this eval forces the read.
- **No performance claim** follows: small cases, few runs, one model family.

## Open questions

1. Without a list of input files, do Sonnet 5.5 and Haiku 5.5 miss number words, unit forms or
   derived figures at all? (This is the gate.)
2. Does the script add anything over the grep recipe? Count the runs where a script hit was the only
   route to a fix.
3. Should a value in bytes match both the 1,000 and the 1,024 conversions, or only the unit the
   prose states?
4. Should the agent add an `Unreleased` changelog line for a change in behaviour, or leave
   changelogs to the user? The shipped skill says history belongs in commits (R2).
5. Should instruction files (AGENTS.md, CLAUDE.md) get report-only treatment? Should the
   Markdown-link check become a stale-refs enhancement (#21/#48) instead of living here?
6. Next steps (C7): add a review mode (`--base-dir`/`--diff`) that reports value drift in a finished
   diff written by a human. It needs base and head trees, and a findings format that can be graded.
