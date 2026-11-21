# Junior-dev Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `junior-dev` Claude Code plugin. Build the eval that shows whether it
makes plans and diagrams written by Haiku 5.5 and Sonnet 5.5 clearer, and at what cost.
Then hill-climb the plugin against that eval.

**Architecture:**
- **The loop.** The main agent drives it through a stdlib Python helper, `junior.py`. The
  helper keeps the loop's state and runs each junior turn as an isolated `claude -p` call
  from an empty temporary directory. The spike in Task 1 confirms the flags.
- **The trigger.** Hooks record each plan or diagram file that gets written, and remind or
  block the agent until it has been reviewed.
- **The tournament.** It runs in this session as generated Workflow scripts. Each script
  embeds the cases and the plugin's own prompt files, and Python collects and scores the
  results.
- **Headless plugin runs.** These cost at most $10 in total and test activation and
  fidelity.

**Tech Stack:**
- Python 3.10+ standard library, with `unittest`;
- Claude Code 2.1.317 plugins (skills and hooks), and `claude -p` with `--json-schema`;
- Workflow tool scripts (JavaScript);
- Node 24 (optional), for parsing Mermaid.

**Spec:** [design.md](design.md), approved by the user on 2026-11-12. The evidence is in
[research-2026-11-12.md](research-2026-11-12.md).

## Global Constraints

- **Models.** Only `claude-haiku-5-5`, `claude-sonnet-5-5` and `claude-opus-5-5`. In
  Workflow scripts these are the aliases `haiku`, `sonnet` and `opus`.
- **What the junior sees.** The artifact text and this loop's question-and-answer
  transcript. No repository, conversation, brief or tools. The only exception is the
  JuniorFull arm, which adds the brief.
- **The loop.**
  - The round cap defaults to 6, and the eval tunes it.
  - Each answer is tagged `checked`, `decided` or `unknown`. Answers tagged `unknown`
    become holes in the report.
  - The loop never asks the user anything partway through.
  - The teach-back comes from a fresh junior that reads only the artifact.
- **Files only.** Tiny artifacts are skipped. The starting threshold is fewer than 120
  words and no Mermaid diagram with at least 4 edges. The activation eval tunes it.
- **Headless spend.** `claude -p` spend is at most $10.00 in total, recorded in
  `evaluation/junior_dev/spend.json`.
  - Every headless call passes `--max-budget-usd`.
  - The runner refuses to start a call that could push the ledger over the cap.
  - The pilot comes first and spends at most $2.
- **The tournament** runs in this session through the Workflow tool, on the user's
  subscription. Usage is reported to the user and on #52 after the pilot and again after
  screening.
- **Decision rule**, applied on the confirmation set:
  - *Useful:* author plus Junior beats the same author's SelfReview by 10 or more
    comprehension points.
  - *Worth it for tokens:* within 5 points of Opus alone, at a lower API-equivalent cost.
  - Prices in dollars per million tokens (input / output): Haiku $0.10 / $0.50, Sonnet
    $2 / $10, Opus $4 / $20.
- **Code rules.**
  - Standard library only.
  - Read and write every file with `encoding="utf-8"`, never the console default.
  - Paths may contain spaces.
- **Leakage.** No 8-word run of any eval case's text may appear in `SKILL.md` or the
  prompt files. This is enforced by `scripts/lint_skills.py`.
- **Tests.** `python -m unittest discover -s tests -v` must pass at every checkpoint.
- **Checkpoints.** Commit and push each finished task to `Junior-dev` with `Refs #52`, then
  comment on #52 with the commit, the checks and what remains.

## Review Focus

1. **Prompts longer than the Windows command line** (about 32,000 characters). The prompt
   must go through stdin and never through argv.
   - Test: a 60,000-character artifact reaches the fake runner intact (Task 2).
2. **Recursion.** The nested junior session must not load this plugin and fire its hooks
   again.
   - Test: the junior command carries the isolation flags from Task 1, and the runner sets
     `JUNIOR_DEV_NESTED=1` (Task 2).
   - Test: both hooks exit at once when that variable is set (Task 4).
3. **Hooks that re-trigger on the loop's own edits, or block Stop forever.**
   - Test: an artifact under review, or reviewed with the same hash, is not recorded again.
   - Test: Stop does not block when `stop_hook_active` is true or nothing is pending
     (Task 4).
4. **Junior output that is malformed, empty, or never says it is done.**
   - Test: it is retried once, then recorded as an error rather than crashing.
   - Test: the round cap ends the loop with the reason `cap` (Task 2).
5. **Non-ASCII text and paths with spaces on Windows.** This session already hit a cp1252
   error.
   - Test: an artifact containing `→ Δ é` round-trips through a state folder whose path
     contains spaces (Task 2).

---

### Task 1: Mechanics spike

**Files:**
- Create: `docs/junior-dev/spike-2026-11-12.md`, `evaluation/junior_dev/__init__.py`,
  `evaluation/junior_dev/spend.json`
- Modify: `docs/junior-dev/design.md`: the isolation decision
- Scratch files go under the session scratchpad and are not committed.

**Interfaces:**
- Produces: `spend.json` as `{"cap_usd": 10.0, "entries": [{"when", "what", "usd"}]}`.
  Produces the exact isolation argv for the junior, the hook input field names, and the
  method used to check Mermaid. Tasks 2, 4 and 6 use these as recorded in the spike report.

Spend target: $0.50 or less.

- [ ] **Step 1: Check the isolated junior call.**
  - Work in an empty temporary directory that holds a canary `CLAUDE.md` containing
    `CANARY-PROJECT-52`.
  - Pipe a prompt on stdin to `claude -p --safe-mode --tools "" --system-prompt-file
    <file> --model haiku --output-format stream-json --verbose --no-session-persistence
    --max-budget-usd 0.05`. The prompt asks the model to list every instruction and every
    piece of context it has besides the system prompt.
  - Expected: no canary, no user `CLAUDE.md` text, an empty tool list in the `system/init`
    event, and no plugins.
  - If `--safe-mode` rejects `--system-prompt-file`, try `--restricted --setting-sources ""`
    and record what happens.
- [ ] **Step 2: Check structured output** under the flags from step 1. Pass
  `--json-schema` with `{"questions": [{"id", "text", "about"}], "done": bool}`. Expected:
  the result event carries the parsed object.
- [ ] **Step 3: Check the plugin hooks.**
  - Run `claude -p --plugin-dir <spike plugin> --model haiku` (neither `--bare` nor
    `--safe-mode`) with the task "write docs/plan.md containing a five-step plan".
  - The spike plugin's PostToolUse (`Write|Edit`) and Stop hooks append their stdin JSON to
    log files.
  - Record the exact fields: `tool_name`, `tool_input.file_path`, `tool_input.content` or
    `new_string`, `session_id`, `cwd` and `stop_hook_active`.
  - Then check whether Haiku acts on PostToolUse `additionalContext`, and on Stop
    `{"decision": "block", "reason": ...}`.
- [ ] **Step 4: Check the plugin-subagent route.**
  - Give a spike plugin agent `agents/junior.md` with `tools: []`. If an empty list is
    rejected, give it a single harmless tool.
  - Have it report the context it can see, with the canary `CLAUDE.md` in the working
    directory.
  - Record whether `CLAUDE.md`, the environment details and the skill listing reach it, and
    whether `SendMessage` exists under `-p`.
- [ ] **Step 5: Check workflow embedding.**
  - Write a workflow script file that holds a 50 KB JSON constant and runs two `haiku`
    agents. Run it with `Workflow({scriptPath})`.
  - Confirm that the agents see the data and that the model is Haiku: the agent states its
    model id.
  - Record the shape of the output file.
- [ ] **Step 6: Check Mermaid parsing.**
  - In the scratchpad, install pinned versions of `mermaid` and `jsdom` and parse one valid
    and one broken flowchart in Node.
  - If this is not working within 15 minutes, record that Task 6 uses the heuristic lint.
- [ ] **Step 7: Write the spike report.**
  - For each item, give the command, what was observed and the decision.
  - Choose the junior mechanism: the helper script with an isolated `claude -p` if step 1 is
    clean, otherwise the plugin subagent.
  - Update the isolation paragraph in `design.md` with what still leaks, and record the
    spend in `spend.json`.
- [ ] **Step 8: Commit** with the message `docs(junior-dev): record the mechanics spike (#52)`,
  then push.

### Task 2: Junior helper and loop state

**Files:**
- Create: `plugins/junior-dev/scripts/junior.py`
- Create: `plugins/junior-dev/skills/junior-dev/references/junior-prompt.md` and
  `teachback-prompt.md`
- Test: `tests/test_junior_dev_helper.py`, which loads `junior.py` by path with
  `importlib`, the same way `test_hygiene_eval.py` does.

**Interfaces:**
- Consumes: the isolation argv and schema behaviour from Task 1.
- Produces the CLI:
  - `junior.py start <artifact> [--rounds 6] [--model sonnet] [--state-root DIR]` prints the
    state folder.
  - `ask <state>` prints numbered questions, or `NO MORE QUESTIONS: run teachback`, or
    `ROUND CAP REACHED: run report`.
  - `answer <state> <answers.md>` reads lines of the form `Q<id> [checked|decided|unknown]:
    <text>`, plus optional `Changed: <what and why>` lines.
  - `teachback <state>` runs a fresh junior on the artifact alone and prints its
    explanation.
  - `verdict <state> correct|wrong [--notes FILE]`.
  - `report <state>` prints markdown: the rounds used, the end reason
    (`teachback-correct` or `cap`), what changed and the holes.
  - The state folder holds `state.json`, which contains: `artifact` (an absolute path),
    `artifact_hash`, `model`, `rounds_cap`, `round`, `phase`
    (`asking|teachback|done`), `transcript: [{round, questions: [{id, text, about}],
    answers: [{id, tag, text}]}]`, `teachbacks: [{text, verdict, notes}]`, `changes`,
    `holes` and `end_reason`.
- Produces the Python API, which Task 6 builds on:
  - `build_junior_message(artifact: str, transcript: list[dict]) -> str`
  - `build_teachback_message(artifact: str) -> str`
  - `parse_questions(raw: str) -> tuple[list[dict], bool]`
  - `parse_answers(text: str) -> tuple[list[dict], list[str]]`, which returns the answers
    and the changes
  - `junior_command(model: str, schema: dict) -> list[str]`, the argv with no prompt in it
  - `run_claude(argv: list[str], prompt: str, timeout_s: float = 300) -> str`, which sends
    the prompt on stdin with `encoding="utf-8"` and sets `JUNIOR_DEV_NESTED=1`
  - `class JuniorSession(state_dir: Path, runner=run_claude)`

Steps:

- [ ] **Step 1: Write the failing tests**, using a fake runner that records argv, stdin and
  env:
  - `test_message_contains_only_artifact_and_transcript`
    - The message contains the artifact and the earlier questions and answers.
    - It does not contain the artifact's path.
    - The fixed framing text contains none of `complete`, `final` or `approved`.
  - `test_command_is_isolated`
    - argv contains every isolation flag from Task 1, plus `--no-session-persistence` and
      `--max-budget-usd`.
    - The prompt is not in argv.
  - `test_long_artifact_goes_through_stdin`: a 60,000-character artifact arrives unchanged
    on stdin.
  - `test_runner_sets_nested_env`: the environment contains `JUNIOR_DEV_NESTED == "1"`.
  - `test_round_cap_ends_loop`
    - With the runner always asking questions and `--rounds 2`, the third `ask` prints
      `ROUND CAP REACHED`.
    - `phase == "done"` and `end_reason == "cap"`.
  - `test_wrong_teachback_returns_to_asking` and `test_correct_teachback_finishes`
    (`end_reason == "teachback-correct"`).
  - `test_teachback_message_has_no_transcript`: the teach-back message contains no question
    text from the transcript.
  - `test_malformed_output_retries_once_then_errors`
    - Two non-JSON outputs give one retry, then a `JuniorError`.
    - `state.json` stays unchanged.
  - `test_unknown_answers_become_holes` and `test_changed_lines_become_changes`.
  - `test_unicode_and_spaces`: an artifact containing `→ Δ é`, in a state root named
    `a b/c d`, round-trips through `start`, `ask`, `answer` and `report`.
- [ ] **Step 2: Run the tests and confirm they fail.** Run
  `python -m unittest tests.test_junior_dev_helper -v`. Expected: FAIL or ERROR, because
  the module does not exist yet.
- [ ] **Step 3: Implement `junior.py` to the interfaces above.**
  - Use `argparse` subcommands.
  - Write `state.json` atomically: write a temporary file, then replace.
  - Hash the artifact with sha256.
  - `ask` reads the artifact file fresh each time, so edits count.
- [ ] **Step 4: Write `junior-prompt.md` (version 0) from design Behaviour steps 2–3.**
  - The junior is smart and technical, but new to this stack and this software. It asks
    and never judges.
  - Its procedure:
    1. Trace one request from start to finish.
    2. For each step, node or edge, ask what triggers it, what data moves, who owns the
       state and what happens on failure.
    3. Treat anything the artifact does not state as unknown.
    4. Cite the step, node or edge each question is about.
  - It asks 3 to 8 questions per round.
  - It sets `done` only when nothing it would need to explain the system remains unclear.
- [ ] **Step 5: Write `teachback-prompt.md`.** The junior explains the system step by step
  in its own words, following one concrete request from start to finish, including what
  happens on failure. It uses only the artifact.
- [ ] **Step 6: Run the tests and confirm they pass**, along with the full suite.
- [ ] **Step 7: Commit** with the message `feat(junior-dev): add the loop helper and junior prompts (#52)`.

### Task 3: Skill and plugin packaging

**Files:**
- Create: `plugins/junior-dev/.claude-plugin/plugin.json`,
  `plugins/junior-dev/skills/junior-dev/SKILL.md` and `plugins/junior-dev/README.md`
- Modify: `.claude-plugin/marketplace.json`, to add `junior-dev`
- Modify: `scripts/lint_skills.py`, to add `evaluation/junior_dev/cases` to `CASES` and
  expose `lint_skill_dir(path, portable: bool)`
- Test: `tests/test_junior_dev_plugin.py`

**Interfaces:**
- Consumes: the `junior.py` subcommands from Task 2.
- Produces: the skill name `junior-dev`. Its description leads with "after you write or
  substantially rewrite a plan, spec, design or diagram file, before acting on it".

What `SKILL.md` (version 0) must contain, in 200 lines or fewer:

- when to run it;
- the loop, using the exact helper commands (`python "${CLAUDE_PLUGIN_ROOT}/scripts/junior.py"
  ...`, with `python3` as a fallback);
- the answer tags, and the rule never to invent a reason: tag `unknown` instead;
- the revision moves: simplify, clarify, restructure, or show it differently. Everything
  learned goes into the artifact;
- the teach-back verdict rule: compare the explanation with what was intended. Any
  misunderstanding means `wrong`, and the artifact must be fixed at that point;
- the final report to the user, listing what changed and the holes;
- never asking the user anything partway through.

Steps:

- [ ] **Step 1: Write the failing tests.**
  - `test_plugin_manifest`: `name == "junior-dev"`, and it has a version and a description.
  - `test_marketplace_lists_both_plugins`.
  - `test_skill_passes_lint`: run `lint_skill_dir(..., portable=False)`, which checks format
    and leakage only.
  - `test_skill_commands_exist`: every `junior.py <sub>` named in `SKILL.md` is an argparse
    subcommand.
  - `test_prompts_do_not_leak_cases`: there is no 8-word run from
    `evaluation/junior_dev/cases` in `SKILL.md` or `references/*.md`.
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Write the manifest, `SKILL.md`, the README draft** (purpose, install,
  limits, "results pending"), the marketplace entry and the lint hook.
- [ ] **Step 4: Run the tests and confirm they pass**, along with the full suite.
- [ ] **Step 5: Commit** with the message `feat(junior-dev): package the skill as a plugin (#52)`.

### Task 4: Trigger hooks

**Files:**
- Create: `plugins/junior-dev/hooks/hooks.json`, `plugins/junior-dev/scripts/hooks.py` (run
  as `hooks.py post-write|stop`) and `plugins/junior-dev/scripts/classify.py`
- Modify: `junior.py`. `start` marks the artifact `reviewing`, and `report` marks it `done`
  with its final hash.
- Test: `tests/test_junior_dev_hooks.py`

**Interfaces:**
- Consumes: the hook field names from Task 1.
- Produces:
  - `classify.is_artifact(path: str, text: str, min_words: int = 120) -> tuple[bool, str]`,
    which returns a decision and a reason.
  - `hooks.post_write(event: dict, root: Path) -> dict | None`.
  - `hooks.stop(event: dict, root: Path) -> dict | None`.
  - The registry: `<project>/.junior-dev/registry.json`, a map from an absolute path to
    `{hash, status: pending|reviewing|done}`. The folder holds a `.gitignore` containing
    `*`, so it is never committed.

Steps:

- [ ] **Step 1: Write the failing tests.**
  - `is_artifact`:
    - A Markdown file with a Mermaid fence of 4 or more edges is true.
    - `docs/plans/x.md` with 5 numbered steps and at least 120 words is true.
    - A five-line checklist is false, with the reason `tiny`.
    - A prose `README.md` is false.
    - A `.py` file is false.
    - A `.mmd` file with 4 edges is true.
  - `post_write`:
    - It records a pending artifact, and its `additionalContext` names the file and the
      skill.
    - It returns `None` when `JUNIOR_DEV_NESTED=1`.
    - It returns `None` for an artifact that is `reviewing`, or `done` with the same hash.
    - It records again when the artifact is `done` but its text has changed so that the
      `difflib` ratio is below 0.7.
  - `stop`:
    - It blocks with a reason that lists the pending paths.
    - It returns `None` when `stop_hook_active` is true.
    - It returns `None` when nothing is pending.
  - `hooks.json` has PostToolUse with the matcher `Write|Edit` (plus `MultiEdit` if Task 1
    found it), and Stop.
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement** `classify.py`, `hooks.py` and the registry updates in
  `junior.py`. The hook commands are `python "${CLAUDE_PLUGIN_ROOT}/scripts/hooks.py"
  post-write` and `... stop`. Use `python3` instead if Task 1 found that `python` is
  missing in the hook shell.
- [ ] **Step 4: Run the tests and confirm they pass**, along with the full suite.
- [ ] **Step 5: Commit** with the message `feat(junior-dev): add the plan and diagram trigger hooks (#52)`.

### Task 5: Case set

**Files:**
- Create: `evaluation/junior_dev/cases.py`, which handles the schema, writing and
  validation.
- Create: `evaluation/junior_dev/case_slots.json`.
- Create: for each case, `evaluation/junior_dev/cases/<id>/visible/brief.md` and an
  optional `visible/existing/*`.
- Create: for each case, `evaluation/junior_dev/cases/<id>/private/` containing
  `quiz.json`, `requirements.json`, `reference.md`, `seeded-presentation.md`,
  `seeded-implicit.md` and `meta.json` (family, format, complexity, split, undecided
  points).
- Test: `tests/test_junior_dev_cases.py`.

**Interfaces:**
- Produces: `cases.load(split: str | None) -> list[Case]`, with the fields `id`, `family`,
  `format`, `complexity`, `split` (`dev|heldout|confirm`), `brief`, `existing`
  (path → text), `quiz` (a list of `{id, kind: brief|design, question, key}`),
  `requirements`, `reference`, `seeded_presentation`, `seeded_implicit` and `undecided`.
  Also `cases.validate() -> list[str]` and `cases.write(output_json: Path, split: str)`.

The slots are 20 in all: 12 for development and 8 held out, with each family on one
side only.

- The families:
  - multi-service architecture;
  - event-driven architecture;
  - multi-region and failover;
  - migrations and refactors;
  - data pipelines;
  - authentication, sessions and credential storage (4 simple ones);
  - deployment and infrastructure;
  - small feature plans.
- The formats: prose step plans, checklists, and Mermaid flowchart, sequence, state and ER
  diagrams, plus ASCII diagrams.
- About 7 cases come with an existing-system folder, and 4 leave a point deliberately
  undecided.

Steps:

- [ ] **Step 1: Write the failing tests.**
  - `test_committed_cases_validate`: `validate() == []`.
  - `test_broken_fixture_fails`: a fixture with a missing key, 7 quiz items and a duplicate
    id produces three named errors.
  - `test_splits_disjoint_by_family`.
  - `test_quiz_rules`: 8 to 12 items, at least 4 design items, and every brief item has a
    key.
  - `test_quiz_not_in_brief`: no quiz question appears word for word in its brief.
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement `cases.py` and write `case_slots.json`.**
- [ ] **Step 4: Run the `junior-dev-cases` workflow** (Opus).
  - For each slot, a writer agent returns the case schema. The writer prompt describes "a
    planning-clarity benchmark" and never mentions Junior-dev.
  - Then an independent Opus checker for each case returns `{ok, problems[]}`. The workflow
    is a pipeline, so checks start as soon as each case is written. The checker verifies:
    - brief items are settled by the brief;
    - keys are unambiguous;
    - design items are worded so any valid design can answer them;
    - the reference answers every item;
    - the seeded versions are correct but unclear, in their two different ways;
    - nothing from the quiz leaks into the brief.
  - A failing case is rewritten once, using the checker's problems. If it still fails, it
    is logged and dropped, never dropped silently.
- [ ] **Step 5: Write the cases** with `cases.write`, then run the tests and confirm they
  pass.
- [ ] **Step 6: Commit** with the message `test(junior-dev): add the generated case set (#52)`.

### Task 6: Tournament harness (offline)

**Files:**
- Create in `evaluation/junior_dev/`: `arms.py`, `build.py`, `templates/tournament.js`,
  `templates/judge.js`, `prompts/{reader,grader,checker,judge,selfreview,critic}.md`,
  `collect.py`, `score.py` and `mermaid.py`.
- Create, if Task 1 chose the Node check: `tools/mermaid-check/` with a pinned
  `package.json`.
- Test: `tests/test_junior_dev_harness.py`.

**Interfaces:**
- Consumes: `cases.load` and the Task 2 Python API (the message builders, so that the
  tournament sends exactly the shipped framing). It reads the prompt text from
  `plugins/junior-dev/skills/junior-dev/references/` and `SKILL.md`.
- Produces:
  - `arms.Arm`, a frozen dataclass with these fields and defaults:
    - `name`;
    - `review`, one of `none|self|prompt|critic|junior|junior_full`;
    - `junior_model="sonnet"`, `rounds=6`, `batch="3-8"`;
    - `teachback="fresh"` (or `none|same`);
    - `teachback_form="free"` (or `scenario`);
    - `procedure="trace"` (or `free`);
    - `skill_rev`, a hash of the prompt files.
  - `arms.CONTROLS` and `arms.DEFAULT_JUNIOR`.
  - `build.build_batch(case_ids, arms, authors, reps, mode, out_dir, label) -> list[Path]`
    returns workflow files.
    - The `mode` is `natural|seeded-presentation|seeded-implicit|null`.
    - Each file holds at most 60 runs and is under 450 KB.
  - `build.build_judge_batch(iteration_dir, pairs, out_dir) -> list[Path]`.
  - `collect.collect(output_file: Path, iteration_dir: Path) -> list[Path]`. It writes
    `<iteration>/<case>/<arm>/<author>/run-<k>/{artifact-initial.md, artifact-final.md,
    transcript.json, report.md, author-key.json, readers.json, grades.json, checks.json,
    usage.json}`. It refuses to overwrite.
  - `score.score(iteration_dir) -> dict`.
  - `score.paired(summary, arm_a, arm_b, author) -> {mean_diff, ci95, n_cases}`, bootstrapped
    over cases with `seed=52` and 2000 resamples.
  - `score.decide(summary) -> dict`, which applies the Global decision rule. Scoring writes
    `summary.json` and `summary.md`.
  - `mermaid.check(text: str) -> list[str]`.
- Each run record from `tournament.js` contains these fields:
  - `run_id`, `case`, `arm`, `author`, `rep` and `mode`;
  - `artifact_initial`, `artifact_final`, `transcript`, `teachbacks` and `report`;
  - `author_key` (sealed);
  - `reader_answers` and `grades`, keyed by reader;
  - `honesty`, a list of `{point, reported_as_hole, invented}`;
  - `requirements`, a list of `{id, present}`;
  - `chars`, the input and output characters per role;
  - `errors`.
- The roles in each run:
  - **Draft:** the author.
  - **Review:** the arm's loop.
  - **Sealed key:** the author answers the design items after the loop, given the brief and
    the transcript.
  - **Readers:** Haiku at `effort: 'low'` with a short answer budget, and Sonnet.
  - **Grader:** Sonnet at `effort: 'low'`.
  - **Checker:** Sonnet, for requirements and honesty.
- Every role's prompt says "Use no tools."
- The SelfReview arm is matched to Junior's budget: it gets as many revision passes as the
  default Junior arm's mean number of rounds in the pilot.

Steps:

- [ ] **Step 1: Write the failing tests.**
  - `test_built_batch_parses`: `node --check` passes on every built file.
  - `test_embedded_prompts_match_plugin`: the embedded junior and teach-back text equals
    the files in `references/` byte for byte.
  - `test_batch_limits`: no file holds more than 60 runs or is 450 KB or larger.
  - `test_only_junior_full_sees_brief`: across every embedded junior message config, the
    brief text appears only for `junior_full`.
  - `test_readers_never_see_brief_or_transcript`.
  - `test_collect_writes_tree`, against `tests/fixtures/junior_dev/workflow-output.json`.
  - `test_collect_refuses_overwrite`.
  - `test_paired_bootstrap_recovers_known_diff`: with a synthetic difference of 0.12, the
    mean is within 0.01 and the CI contains 0.12.
  - `test_decide_thresholds`: differences of 0.10 and 0.09 come out useful and not useful.
    A result 0.05 below Opus at lower cost is worth it, and 0.06 below is not.
  - `test_mermaid_check_flags_broken`.
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement the modules and templates.**
  - `tournament.js` uses `pipeline()` over runs, so there is no barrier between runs.
  - Junior turns are `agent()` calls with the junior schema.
  - Token use is estimated from characters divided by 4 for each role, then calibrated
    against the workflow's reported total of subagent tokens.
- [ ] **Step 4: Run the tests and confirm they pass**, along with the full suite.
- [ ] **Step 5: Commit** with the message `feat(junior-dev): add the in-session tournament harness (#52)`.

### Task 7: Grader validation

**Files:** Create `evaluation/junior_dev/iterations/validation/` and
`evaluation/junior_dev/README.md` (cases, grading, how to run, results).

- [ ] **Step 1: Run `build.build_validation_batch`** with readers and the grader on four
  versions of each of the 20 cases, 1 run each: the reference, `seeded-presentation`,
  `seeded-implicit`, and `padded` (the reference plus fixed filler text). Add an Opus
  grader on 120 sampled items to measure agreement.
- [ ] **Step 2: Check the gates.**
  - The mean reference comprehension is 0.85 or higher.
  - `seeded-implicit` scores at least 0.15 below the reference on at least 70% of cases.
  - `padded` stays within ±0.05 of the reference mean.
  - The Sonnet grader agrees with Opus on at least 90% of items.
  - Also report whether the hurried Haiku reader separates the reference from
    `seeded-presentation` by at least 0.10. If it does not, the report says the
    presentation effect may not be measurable.
- [ ] **Step 3: Fix the cases or prompts and rerun, up to 2 rounds.** Record every change.
  If a gate still fails, report it to the user before going on.
- [ ] **Step 4: Commit** with the message `test(junior-dev): validate the graders (#52)`.

### Task 8: Pilot and usage report

- [ ] **Step 1: Run the pilot:** 4 development cases × [NoReview, SelfReview, Critic,
  Junior default] × authors [haiku, sonnet] × 1 run, in natural mode.
- [ ] **Step 2: Collect and score it.**
  - Record the agent count, the subagent tokens, the wall time, and the API-equivalent cost
    per run by arm and author.
  - Extrapolate to Tasks 9 to 12.
  - Read 4 transcripts end to end, and fix any harness bugs found.
- [ ] **Step 3: Report.** Post a comment on #52, report to the user, and commit
  `iterations/pilot/`.

### Task 9: Screening

All on the development set (12 cases), in natural mode, with Haiku and Sonnet authors and
2 runs each.

- [ ] **Stage A: controls.** NoReview, SelfReview, JuniorPrompt, Critic, JuniorFull and
  Junior (default).
- [ ] **Stage B: one factor at a time** from the default, with each winner carried forward:
  - `junior_model`: haiku or sonnet, plus opus on 4 cases;
  - `teachback`: none, same or fresh;
  - `teachback_form`: free or scenario;
  - `rounds`: 2, 4 or 6;
  - `procedure`: free or trace;
  - `batch`: 3–5 or 6–10.
- [ ] **Stage C: other modes.** Both seeded modes and null mode, for the default, SelfReview
  and NoReview, on 6 cases.
- [ ] **Pairwise judge:** the best Junior against SelfReview, in both orders.
- [ ] **Choose the default.** It is the variant with the highest mean of Junior minus
  SelfReview across authors, with no guardrail worse. A tie goes to the cheaper variant.
- [ ] **Report usage** to the user and on #52.
- [ ] **Commit** the iterations and the results table in the README.

### Task 10: Hill climb

The climb edits only `SKILL.md`'s loop text, `junior-prompt.md` and `teachback-prompt.md`.

- [ ] **Up to 6 iterations**, each making one change, on the development set with 3 runs,
  arms SelfReview and Junior. A change is kept only if all three hold:
  - the mean of Junior minus SelfReview improves across authors;
  - no guardrail gets worse (null-case drift, requirements present, honesty, invented
    facts);
  - neither author drops by more than twice Stage A's run-to-run SD.
- [ ] **Check against the held-out set** after iterations 3 and 6.
- [ ] **Run `lint_skill_dir`** every iteration.
- [ ] **Record each iteration** in the README table.
- [ ] **Commit each iteration** with the message `feat(junior-dev): climb iteration N, <change> (#52)`.

### Task 11: Plugin runs (headless, $10 cap)

**Files:**
- Create: `evaluation/junior_dev/live.py`, adapted from `evaluation/skill_eval/live.py`.
  It runs `claude -p --plugin-dir plugins/junior-dev` with `stream-json` and
  `--max-budget-usd`, and uses the spend ledger.
- Create: `evaluation/junior_dev/fixture/`, a tiny project.
- Create: `plugins/junior-dev/evals/<case>/`, using `load-*` and `skip-*` names as
  code-comments does.
- Test: `tests/test_junior_dev_live.py`, which runs offline. It covers the argv, the
  ledger refusing to go over the cap, and grading fidelity from a recorded stream fixture.

Steps:

- [ ] **11a: Pilot, $2 or less.** 2 activation prompts × {description only, hooks} × haiku,
  plus 1 fidelity run on Haiku.
- [ ] **11b: Activation.**
  - About 8 prompts that should trigger it and 6 that should not.
  - Each runs under {description only (a build without hooks), hooks} × {haiku, sonnet} ×
    1 run, with `--max-turns 8`.
  - Measure recall and false triggers.
- [ ] **11c: Fidelity.**
  - 3 cases × {haiku, sonnet}, 1 to 2 runs each, through the full loop.
  - Graded from the stream:
    - the helper steps ran in order;
    - the junior's prompt held only the artifact;
    - the rounds stayed within the cap;
    - the report lists the changes and the holes;
    - no question was put to the user partway through.
- [ ] **Ship the winning trigger.** It needs recall of at least 80% and at most 1 false
  trigger in 6. Stop and report if the ledger reaches $10.
- [ ] **Commit** the results under `evaluation/junior_dev/live-results/`, and the plugin
  README.

### Task 12: Confirmation and evidence report

- [ ] **Generate 12 fresh confirmation cases** with the Task 5 pipeline. They get new
  slots, and the writers are told what the existing ids cover, so the new cases differ.
- [ ] **Run the final configuration.**
  - Authors: haiku and sonnet with 3 runs each, plus an opus-author slice of 4 cases with
    1 run.
  - Arms: NoReview, SelfReview, JuniorPrompt, Critic and the final Junior.
  - Reference arms: Sonnet alone and Opus alone, NoReview, 3 runs.
  - Run the pairwise judge, score the runs, and apply the decision rule.
- [ ] **Write `docs/junior-dev/report-<date>.md`.** It includes:
  - per-model results with confidence intervals, and cost;
  - what improved and what did not, including null and negative results;
  - the limits: judges from the Claude family only, synthetic cases, sample size, and the
    tournament's isolation deviation;
  - the recommended default.

  Also prepare 10 to 20 blinded before-and-after pairs for the user to rate.
- [ ] **Commit.**

### Task 13: Knowledge files, review, integration

- [ ] **Update the knowledge files:**
  - `architecture.md`: the current system and the ownership rows;
  - `README.md`: the check commands and how to install the plugin;
  - `docs/research/README.md`: the status;
  - `intent.md`: the result;
  - `docs/roadmap.md`: a link;
  - the plugin README: its measured results.
- [ ] **Run the independent review, the PR to `main`, issue reconciliation, cleanup and the
  final audit**, following `docs/agents/git-workflow.md`.
