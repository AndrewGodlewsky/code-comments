# constraint-sweep: research

Researched 2026-11-11 for issue #50: candidate C1 in
[`incubator/ideation/2026-11-11-candidates.json`](../ideation/2026-11-11-candidates.json), as redirected by the
coordinator. Observations are kept apart from interpretation. Nothing here is a performance claim.

## Question

Before changing what existing code returns, raises, orders or accepts, or whether it exists (including
"simplify", "speed up", "raise instead" and "remove dead code" requests), does an agent read what **other**
files' comments, docstrings and test names say about the symbols it changes, and keep or openly report each
constraint stated there? Can a short instruction with a word-bounded search recipe make it do so, with no index,
script or stored state ([ADR 0001](../../docs/adr/0001-context-lives-inline-no-central-index.md)), without obeying
stale constraints or turning over-cautious? And, for ADR 0001's "Revisit if": do readers miss context in other
files, and does plain search fix it?

## Sources

All accessed 2026-11-11. Repository paths are relative to the repository root.

**Repository**

- **R1. ADR 0001 and `intent.md`.** Search is the only allowed route to context in other files, and missing that
  context is the revisit trigger. ADR 0001: "readers systematically miss context living in **other** files (the
  agent never opens or searches the file that holds the fact)". `intent.md`: "Revisit discovery aids only if
  evaluation shows agents missing context in other files, and then only in a form that manual edits cannot
  leave out of sync."
- **R2. `docs/skill/inline-only-tradeoffs.md`, C1.** "If changing `A` breaks `B`, and the fact is written only in
  `B`, an agent editing `A` never opens `B`." It lists as open "Whether pointer comments (C1) are enough for
  cross-file effects".
- **R3. The shipped skill's one search line.** `plugins/code-comments/skills/code-comments/SKILL.md` says "Before
  simplifying, look for it in tests, callers and docs", in aid of writing a reason. `evaluation/hygiene/README.md`
  (iteration 2): "The new "look in tests" line did not produce the behaviour."
- **R4. Iteration-5 grading of reason-only-in-test**
  (`evaluation/hygiene/iterations/iteration-5-{haiku,sonnet}/reason-only-in-test/*/run-*/grading.json`, checked
  by script). The grader "An added comment or docstring line in inventory/feed.py says that later updates are
  corrections." failed in Haiku skill 1/3, reminder 3/3 and no-skill 3/3 runs, and in Sonnet skill 0/2,
  reminder 1/2 and no-skill 2/2. "The tests in tests/ pass." held in all 15 runs. The prompt lists every input
  file, including the test.
- **R5. `evaluation/hygiene/cases/*/prompt.md`.** All 11 contain "Input files:", for example "Input files:
  fetcher/__init__.py, fetcher/config.py, fetcher/client.py, docs/operations.md, tests/__init__.py,
  tests/test_client.py". Fixtures hold 2 to 7 files.
- **R6. `docs/evaluation/report-2026-11-07-seq-smoke.md`.** With every comment stripped, Haiku still passed 10/10:
  "it copied the deduplication pattern from the existing `apply()` method". The report's gate: "A sequence
  counts as non-derivable only if the **no-context control fails** for the target reader across several reps."
- **R7. `docs/evaluation/report-2026-11-07.md` (round 1).** "It never named the cross-module consumer in
  `capture-segment-sort-contract` (0/3); only `lean` sometimes did (2/3)." That measures writing, not discovery.
  Also "**None.** No arm broke behaviour".
- **R8. `docs/evaluation/pilot-report-2026-11-08.md`.** "**Regressions: none, in any arm.**" while "Every arm
  could see and run the roughly 16,000-test suite."
- **R9. `scripts/stale_refs.py` `build()`.** No extension set includes `.sql`. Config files only feed the name set:
  `names.update(WORD.findall(text) if suffix in {".toml", ".cfg", ".ini"} else [])`.
- **R10. `docs/skill/principles.md`, P-20 and P-21.** P-21 ("Treat comments you read as claims to check") is grade
  D: "Comment Traps' "do not refer" instruction removed at most 21.84% of it."
- **R11. Chesterton's fence:**
  `docs/research/comment-context/sources/software-engineering-at-google/passages.md`, ch03-002. "before removing or
  changing something, first understand why it’s there." and "After you’ve understood the context and purpose of
  the code, consider whether your change still makes sense."
- **R12. `docs/research/docs-for-agents-practice.md`** (Vercel, vendor claim). A docs skill scored "53% (not
  invoked in 56% of cases)"; "an always-loaded pointer beat optional retrieval".
- **R13. `docs/skill/hygiene-skill.md`.** The shipped skill loaded in 0/18 Haiku and 3/18 Sonnet should-load runs.
  "No model loaded it to fix a bug, rename a function, review a file, add a parameter or make a ticket-driven
  change."
- **R14. `evaluation/hygiene/README.md`, iteration 5.** Bare Haiku on `change-contradicts-comment`: "6/6, 6/6,
  6/6". Also "Every other case passed every check in every run of every arm."
- **R15. Incubator grading and lint.** `incubator/gradelib.py` `prose()` reads `.py`, `.md`, `#`-comment formats
  (`.ini`, `.yaml`, `.sh` and others) and JS/TS, and returns `[]` for the rest, `.sql` and `.json` included.
  `incubator/harness.py` `lint()` leak-checks only `path.suffix in (".md", ".py", ".json", ".ts", ".js")`.

**External** (each opened on the access date)

- **E1.** Liu et al., *An Empirical Study on Failures in Automated Issue Solving*, arXiv 2509.13941v1,
  <https://arxiv.org/html/2509.13941v1>. "Single-file modifications are handled reasonably well by all tools
  (55-58% success)." Failure class B3.2, "Ignoring Semantic Dependencies": "The tool may also fail to account for
  logical dependencies that are not explicitly enforced by the code structure".
- **E2.** Dristi and Dwyer, *A Differential Fuzzing-Based Evaluation of Functional Equivalence in LLM-Generated
  Code Refactorings*, arXiv 2602.15761, <https://arxiv.org/abs/2602.15761>. "LLMs show a non-trivial tendency to
  alter program semantics, producing 19-35% functionally non-equivalent refactorings"; "about 21% of these
  non-equivalent refactorings remain undetected by the existing test suites".
- **E3.** Wang, Pradel and Liu, *Are "Solved Issues" in SWE-bench Really Solved Correctly?*, arXiv 2503.15223v2
  (ICSE 2026), <https://arxiv.org/abs/2503.15223>. "even more (29.6%) plausible patches induce different behavior
  than the ground truth patches".
- **E4.** Hyrum's Law, <https://www.hyrumslaw.com/>. "all observable behaviors of your system will be depended on
  by somebody."
- **E5.** ripgrep guide, <https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md>, and local `rg --help`
  14.1.1. Default filters include "Hidden files and directories."; "Hidden files and directories can be searched
  with the --hidden (-. for short) flag." For `-w`: "ripgrep will only show matches surrounded by word
  boundaries."
- **E6.** Vulture README, <https://github.com/jendrikseipp/vulture>. "Due to Python's dynamic nature, static code
  analyzers like Vulture are likely to miss some dead code." "Also, code that is only called implicitly may be
  reported as unused."
- **E7.** Salis et al., *PyCG*, arXiv 2103.00587 (ICSE 2021), <https://arxiv.org/abs/2103.00587>. "PyCG achieves
  high rates of precision ~99.2%, and adequate recall ~69.9%."
- **E8.** Poshyvanyk, Marcus, Ferenc and Gyimóthy, *Using information retrieval based coupling measures for impact
  analysis*, EMSE 14(1), 2009, <https://inf.u-szeged.hu/~ferenc/publication/pmf09>. Only the abstract page was
  read. The coupling is "based on measuring the degree to which the identifiers and comments from different
  classes" relate, and the measures "proved to be better predictors for classes impacted by changes".
- **E9.** Tan, Marinov, Tan and Leavens, *@tComment*, ICST 2012, <https://arxiv.org/abs/1201.6078v1>. "We evaluated
  @TCOMMENT on seven open-source projects and found 29 inconsistencies between Javadoc comments and method
  bodies."
- **E10.** Bairi et al., *CodePlan*, arXiv 2309.12499 (FSE 2024), <https://arxiv.org/abs/2309.12499>. Such tasks
  "cannot be solved directly using LLMs, since code within a repository is inter-dependent"; "CodePlan is based
  on a novel combination of an incremental dependency analysis, a change may-impact analysis" and adaptive
  planning.
- **E11.** Anthropic, *Effective context engineering for AI agents*,
  <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>. "primitives like glob and
  grep allow it to navigate its environment and retrieve files just-in-time"; "runtime exploration is slower
  than retrieving pre-computed data"; "an agent can waste context by misusing tools, chasing dead-ends".
- **E12.** PostgreSQL, *COPY*, <https://www.postgresql.org/docs/current/sql-copy.html>. "For `COPY FROM`, each field
  in the file is inserted, in order, into the specified column."
- **E13. Community impact skills.** athola `blast-radius` (<https://skills.sh/athola/claude-night-market/blast-radius>):
  "Analyze the impact of current code changes using the code knowledge graph."; "This skill requires the
  **gauntlet** plugin for graph data." aakash-dhar `impact-analysis` (<https://skills.sh/aakash-dhar/claude-skills/impact-analysis>):
  "map the full blast radius before anyone writes a line of code", saved under `project-decisions/`. Only the
  start of each SKILL.md was visible, so whether either reads prose constraints is **unverified**.
- **Not used.** Livshits et al., *In Defense of Soundiness* (CACM 2015): every copy tried returned 403 or 404.

**Local probe P1** (2026-11-11, ripgrep 14.1.1, GNU grep 3.0). An eight-file scratch fixture, built by
`C:/Users/godle/AppData/Local/Temp/constraint-sweep-probe/make_probe.py` outside the repository.
`rg -n -w fetch_rows` found a caller comment, an import and a shell comment, skipped `fetch_rows_v2`, and missed
`.github/workflows/nightly.yml`; `--hidden` found it, but here `rg --hidden --files` also lists 61 files under
`.git/`. `rg -w handle_chargeback` found an INI route and a JSON hook, and with `-t py` neither. A call through
`getattr(handlers, "handle_" + kind)` matched only the prefix `handle_`. `rg -F ledger.rows` found
`python -m ledger.rows` in a shell script. `grep -rnw` searched hidden directories by default.

## Findings

Observations:

1. **Discovery has never been measured here.** Every hygiene prompt lists its input files, and fixtures are 2 to 7
   files (R5).
2. **The one "look elsewhere" line did not change behaviour (R3).** Later Haiku failures on reason-only-in-test
   came from runs that did not use a reason held in a file they had been given (R4).
3. **No repository run has broken behaviour** (R4, R7, R8). A capable reader copied the needed pattern from nearby
   code (R6), and bare Haiku acted on a conflict it could see (R14).
4. **Elsewhere, behaviour changes slip past visible tests** (E2, E3). "Logical dependencies that are not explicitly
   enforced by the code structure" are a named failure class (E1).
5. **Structural tools miss names reached through strings and dynamic dispatch.** PyCG's recall is about 69.9% (E7),
   and Vulture flags code that is only called implicitly (E6). `stale_refs.py` reads no `.sql` comments (R9).
6. **What a search finds depends on its options** (P1, E5). ripgrep skips hidden directories, `--hidden` also
   enters `.git/`, a type filter misses INI and JSON, and names built at runtime match no full-name search.
7. **Prior art uses structure or stores something.** CodePlan runs dependency and may-impact analysis (E10); the
   community skills query a prebuilt graph or write a report file (E13); IR impact analysis ranks classes with a
   coupling model computed from comments and identifiers (E8); @tComment checks a method's own Javadoc (E9). None
   was found that reads a prose constraint where a symbol is mentioned and keeps it during an edit.

Interpretation:

- **The gap is plausible but not shown here.** Bare models keep behaviour that tests pin and report conflicts they
  see, so any headroom is in untested constraints held in files with no structural link to the edit: SQL, INI,
  JSON, shell, hidden CI directories, and caller comments that hold a reason.
- **A recipe needs exact options.** Told only to "search the repository", a model can search just `*.py`, or let
  ripgrep skip hidden directories, and still believe it searched everything.
- **Only stated constraints can bind.** By Hyrum's Law (E4) nearly every behaviour is relied on by someone, so
  guarding against suspected reliance would block every change. That restriction is also the rule's main limit.

## What this means for the skill's rules

1. **Trigger.** Apply before changing what existing code returns, raises, orders, deduplicates or accepts, or
   whether it exists, including simplify, speed-up, raise-instead and dead-code requests (E1 to E3, R11).
2. **Name the symbols** whose behaviour will change before the first edit. *Hypothesis*: the search needs names.
3. **Follow the symbol's own pointers.** Read its docstring and comments, and open every file or symbol they
   name. This is ADR 0001's pointer mitigation (R1, R2), and the mirrored-column-order control tests it.
4. **Search with a fixed recipe.** For each name, run `rg -n -w --hidden -g '!.git' NAME`. Then run
   `rg -n -F --hidden -g '!.git' pkg.module`, and the same for `pkg/module`. Use no type or glob filter, so SQL,
   INI, YAML, JSON, shell and Markdown are searched too. The fallback is `grep -rnw --exclude-dir=.git NAME .`
   (P1, E5, R9).
5. **Search runtime-built names.** When a name is reached through `getattr`, `importlib`, a registry or a string
   prefix, also search the dispatcher and the prefix (P1, E6, E7).
6. **Read the prose at each hit:** the comment on or above it, the enclosing function, and the test name.
   *Hypothesis*: the window size is unmeasured. Comments carry coupling and checkable claims (E8, E9).
7. **Check each stated constraint against the code.** If the code still relies on it, it binds the change: keep
   the property, update the paired site, or move the guarantee (for example, to `ORDER BY` instead of a Python
   sort). If the code no longer relies on it, report it as stale with its file:line, and do not let it block the
   change (R10, E9). Untested, and P-21 is grade D.
8. **If the user explicitly asked for the breaking change,** make it. Keep dependents working where possible, and
   name the constraint and its file:line in the reply. Never break a stated constraint silently. This matches the
   shipped skill's conflict rule (R3, R14).
9. **Only stated constraints and tests bind.** If a dependency seems likely but nothing states it, ask in the
   reply rather than coding around a guess (E4). *Hypothesis*: this cut-off.
10. **Restraint.** A mention that states nothing relevant is no reason to edit that file, add defensive code, ask
    or refuse. Edit no file you only read. Mention the sweep only when it changed the plan. Supported by E11 and
    round 1's proxy-win harm (`incubator/README.md`).
11. **No comment writing, and instructions only.** Comments stay with the shipped skill and this one reports in the
    reply. No script, caller graph or usage-flag analysis; nothing stored (ADR 0001 reasons 2 and 4; direction).

## What this means for the eval

**Measure discovery apart from outcome.** For each run, record whether, before its first edit, the agent read the
file that holds the constraint or saw it in a search result. That is ADR 0001's "never opens or searches" clause.
It needs a transcript check; `verify-reads` only checks skill reads today. Report discovery and hidden-test pass
rates by arm and by `context_in_other_file`.

**Cases.** The split is suggested. Holding out the simplify and dead-code request types tests whether the trigger
generalises.

*Superseded 2026-11-11: eval/CASES.md has the cases and split as run. mirrored-column-order was replaced by
positional-columns-in-sql-pointer. The held-out pair is first-wins-reason-in-caller and mention-without-constraint,
and dispatched-by-name is training. The reminder actually run is the sentence in eval/arms.json.*

| Case | Split | `context_in_other_file` | Constraint lives in | Natural wrong edit | Core hidden test |
| --- | --- | --- | --- | --- | --- |
| sort-relied-on-elsewhere | train | true | caller comment (merge join) | delete `sorted()` | reconcile pairs every row of out-of-order inserts |
| positional-columns-in-sql | train | true | `--` comment beside a COPY | currency beside amount, COPY untouched | simulated load lands each field in its same-named column |
| stale-constraint-elsewhere | train | true | stale caller comment | refuse, re-add a sort, stay silent | reconcile passes, sort gone, stale clause reported |
| mention-without-constraint | train | false | none (descriptive mentions) | edit `ui/` or `reports/`, defend, ask | CHF rounds to 0.05, default unchanged |
| mirrored-column-order | train, labelled control | false | docstring of the edited file | skip `ingest/layout.json` | export-then-ingest round trip |
| first-wins-reason-in-caller | held out | true | caller comment (activation date) | dict comprehension keeps last | first event per user, in first-seen order |
| dispatched-by-name | held out | true | INI comment and a string name | delete `handle_chargeback` | chargeback reaches its handler; dead helpers removed |

**Scoring rules.**
- **positional-columns-in-sql passes two ways:** currency goes last and the reply says why, or it goes beside
  amount and COPY gets an explicit column list in the same order (E12). A reorder with no column list fails. The
  hidden test parses the schema and the COPY statement and maps fields by position, so no database is needed.
- **Every case checks that the request was honoured**, so refusing loses. The stale and mention cases give the
  skill two ways to lose, so "always edit consumers" cannot win.

**What bare models already do well, which fixtures must defeat.** They keep behaviour that visible tests pin
(R4, R8), so visible tests must not pin the cross-file property. They copy nearby patterns (R6), so the
constraint must not show in code they read anyway. They report visible conflicts (R14), so the point-of-edit
control is expected to pass without the skill.

**Likely bare failures** (a hypothesis until the gate runs): skipping file types that nothing imports, type-filtered
or hidden-blind searches, and treating "no Python call site" as "dead".

**Fixtures.** Use 10 to 12 files, with distractor mentions that must stay byte-identical: a README line, a test
name, an unrelated consumer. Put hidden tests in `eval/hidden/<case>/hidden_tests/` with `core` focus. Reply
keyword checks get `reply` focus and no headline weight.

**Gate first.** Run bare Haiku three times and Sonnet twice per case (R6). Harden or drop any case both pass, for
example by moving a mention into `.github/workflows/`, or by having dispatched-by-name compute `"handle_" + kind`
so that only rule 5 finds the handler.

**Grading gaps (R15).** `gradelib.prose` ignores `.sql`, `.json` and `;` INI comments, so check those files with
`files_unchanged` or `keeps` and write INI comments with `#`. `lint()` does not leak-check `.sql`, `.ini`, `.yaml`
or `.sh`, so keep fixture wording out of SKILL.md or extend the lint.

**Arms.** The shipped-skill arm is the falsification test (a tie means this is a variant); the reminder arm uses the
candidate's sentence. Report tokens and turns, because the sweep adds reads (E11).

## Counterevidence and limits

- **No breakage in this repository's history** (R4, R7, R8). The reason-only-in-test misses were failures to read
  listed files, not to find unlisted ones. The headroom is a hypothesis until the gate runs.
- **A default search already finds INI and SQL mentions** (P1). If Sonnet greps without being told to, only the
  hidden-directory and runtime-name variants stay hard.
- **Up-front context may beat search,** and on-demand skills often don't load. An always-loaded index beat
  optional retrieval (R12, a vendor claim), and the shipped skill rarely loads on its own (R13), so results
  describe this skill once read. A null result is ADR 0001's revisit trigger; any fix must survive manual edits.
- **No study shows that an instruction to check claims reduces harm** (R10). The stale case may expose obedience
  to stale comments.
- **Grep is incomplete.** It misses aliased imports beyond the import line, runtime names without a prefix, SQL
  built as strings, and other repositories. Structural tools miss different things (E7), and reliance nobody
  stated (E4) is out of scope.
- **Small fixtures cannot show noise.** In a large repository a common name returns hundreds of hits, and that
  reading cost is unmeasured.

## Open questions

1. Does Claude Code's Grep tool apply ripgrep's hidden-file and `.gitignore` defaults? No documentation was found
   for this, and only a local `rg` was checked.
2. Is "the comment on or just above the mention" the right window, or do constraints sit further away, in module
   headers and test docstrings?
3. With both skills installed, this one reports a stale comment and the shipped one would correct it; the stale
   check accepts either. Is that the right boundary? Should mirrored-column-order stay out of the headline?
4. The skeptic judge would move stale-constraint-elsewhere to C2 (verify-before-relying). If both skills are
   built, read their results on that case together.
