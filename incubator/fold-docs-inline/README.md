# fold-docs-inline

A candidate skill for the user who has already decided to slim or retire one docs page.
It gives every claim on that page a fate, so that each fact about the code ends with one
home beside the code it governs. The fates are:
- **dropped:** the code already says it;
- **moved:** it goes into a comment at the file and symbol it governs;
- **kept:** it stays in a document, because it has nothing in the code to sit beside;
- **not migrated:** the code contradicts it, so it is reported to the user.

The user reviews the per-claim fate list in the reply.

**Status: evaluated, over 165 graded runs on Claude Haiku and Sonnet. It beats the
shipped `code-comments` skill and the bare model in training. On the held-out pair it
leads both on checks, but at run level only its full-marks lead over the bare model
holds. Its held-out lead over the shipped skill is not established. It does not reliably
beat the one-line reminder in [eval/arms.json](eval/arms.json).**

Against the reminder:
- it tied on Sonnet training;
- it was one check behind on Haiku held-out;
- it was ahead on Haiku training (+4 checks) and Sonnet held-out (+8 checks), each lead
  coming from a single case at 2 or 3 runs per cell.

Page handling held in every skill run. It slimmed or deleted the retired page as the
answer key expects, and never left it whole: 0 of 60 runs. The reminder left the page
whole in 3 of 35 runs, all on one held-out case, `four-fates-page`, so the edge over the
reminder rests on one case. The results are in [eval/RESULTS.md](eval/RESULTS.md), and
the samples are small (see Limits).

It is ideation candidate C6 for issue
[#50](https://github.com/AndrewGodlewsky/code-comments/issues/50), and it does not ship.

- Skill: [skill/fold-docs-inline/SKILL.md](skill/fold-docs-inline/SKILL.md) (v2)
- Research: [research.md](research.md)
- Eval design: [eval/CASES.md](eval/CASES.md); case selection: [eval/GATE.md](eval/GATE.md)
- Results: [eval/RESULTS.md](eval/RESULTS.md); analysis: [eval/ANALYSIS.md](eval/ANALYSIS.md);
  skill edits: [eval/CHANGES.md](eval/CHANGES.md)

## The problem

The user used to keep an AI-maintained `docs/` folder beside the code. That gives
[two sources of truth](../../intent.md): the code, and a description of the code that
nobody keeps in sync. [ADR 0001](../../docs/adr/0001-context-lives-inline-no-central-index.md)
settles where code facts should live: in comments beside the code, with no index.
Nothing yet helps take an existing page apart safely. Asked to "move the docs into the
code", a model may do any of these:
- copy a value the code no longer has into a comment, at the point of edit where it
  misleads most;
- change the code to match the page;
- paste in paragraphs that only restate the code;
- leave each fact both in the page and in a comment;
- delete or bury notes that have no code home, such as runbook steps, contacts or
  product intent.

`intent.md` asks "Which kinds of shared documentation can be replaced without losing
useful context?" This skill applies one answer, a page at a time. That answer is the
boundary table in [context-layers.md §4](../../docs/research/context-layers.md), which
the repository itself calls a hypothesis.

## What it adds over the shipped skill

The shipped [`code-comments`](../../plugins/code-comments/README.md) hygiene skill acts on
code being changed and on comment-only reviews. It calls itself
["Not a documentation system"](../../docs/skill/hygiene-skill.md). It already says "Give
each fact one home" and "Do not restate code". This skill adds:
- **A different input and output.** It starts from one named document. Its outputs are
  deletions from that page, comments at the owning symbols, and a fate list.
- **Checking each claim against the code** before anything moves, with an explicit rule
  that the code decides what a comment may say. Which side is right stays the user's
  call.
- **A kept-in-a-document fate** for knowledge with no code home, so that a migration
  does not delete operational or organisational notes.
- **A not-migrated fate:** a contradicted claim reaches no comment and changes no code.
  It is quoted back with the code's evidence, and the user decides which side is right.
- **Hard limits:**
  - one page only;
  - no code change, no new file and no edit to an instruction file;
  - the page is deleted only when nothing kept remains.

It does not repeat the shipped skill's writing rules. When both are installed, the
shipped skill governs how each added comment reads.

These additions were designed before any run. "Results" below says which of them made a
measured difference. Against the shipped skill, most did. Against the reminder, only the
page handling and, on Haiku, the kept fate did.

## When to use it

Use it on an explicit request that names one page the user has decided to retire or
slim. For example: "we're retiring docs/x.md, put what belongs beside the code", or "fold
this page into comments and delete it". If the request names a folder or no page, the
skill asks which single page to do first.

Do not use it for:
- updating a doc after a code change (the shipped skill and bare models already do this);
- explaining or summarising a doc, or writing a new one;
- editing `AGENTS.md`, `CLAUDE.md` or another instruction file. When one is named, the
  skill gives the fate list only and edits nothing;
- clearing out a whole `docs/` folder;
- ordinary code edits.

## How it works

The skill is instructions only, with no script. It runs in five steps:

1. **Split** the page into claims (sentences, bullets and table rows), down to each
   value, count, order or name.
2. **Check** each claim against the code and its tests.
3. **Decide** a fate for each claim.
4. **Edit** only the page and the comments.
5. **Reply** with one line per claim.

The fate list names, for each claim:
- **moved:** the file and symbol;
- **dropped:** where the code states it;
- **not migrated:** the file, symbol and actual value.

After the list, the reply names:
- other files that also state a moved fact, such as an instruction file or another doc.
  These are left for the user;
- files that link to the removed page or section;
- gaps the user must fill.

## Where each rule comes from

Grades follow [research.md](research.md):
- **measured:** an experiment or mining study;
- **practitioner:** expert or vendor guidance;
- **repo-eval:** this repository's own runs;
- **hypothesis:** no source tests it;
- **judgement:** the skill writer's choice, named so it can be challenged.

| Rule in SKILL.md | Source | Grade |
| --- | --- | --- |
| One named page; ask when a folder or no page is named | Coordinator direction; judges' fix suggestions for C6; `intent.md` (the user's fuller theory still values a docs folder) | hypothesis |
| Edit only the page and comments; other files, instruction files included, stay byte-identical | Direction; context-layers.md §4 calls the instruction-file duty "untested"; Agent READMEs (E10) | hypothesis |
| A named instruction file gets a fate list only | Direction (never edit instruction files); research open question 4 | judgement |
| Change no code, even where the page says the code should differ | Xu & Wu (E5): Codex rewrote code to match a stale file in 20 of 80 runs; churn-2026-11-07 (R10) counts Haiku's excess code edits | measured hazard |
| Add no file | ADR 0001; P-26; direction | practitioner |
| Delete the page only when asked and nothing kept remains; never a folder | Google docguide (E1); do-docs-audit's deletion limit (E11); direction | practitioner |
| Split to the level of each value, count, order or name | Research rule 3; the shipped skill's "Check each clause" | judgement |
| Check each claim against the code; the code decides what a comment may say, the user decides which side is right | E5 (a precedence sentence raised code-following to 91.4%); E6, E7; P-21 (graded D); ADR 0001 reason 1 | measured hazard; the remedy is hypothesis |
| Dropped: the code, its tests or an accurate comment already state it | P-09, P-26, E4, E9, Pragmatic Programmer (R13). Counterevidence: R14, PEP 257 (E3) | practitioner |
| Moved: one comment at the narrowest owning scope; keep the ticket id; take values from the code; add beside an accurate comment; pointer only where a dependent site would break the fact | context-layers.md §4 table; E1; the shipped skill's capture rules; ADR 0001 consequences; P-27; R8 (accurate docstrings rewritten in every arm) | practitioner / repo-eval |
| Kept: operational steps, other systems no code relies on, intent, decision history, explanation with no single owner | inline-only-tradeoffs C7 (R4); E1, E2, E4; Software Engineering at Google ch10 (R12) | practitioner |
| Keep an overview in the page and tell the user it could be a module docstring | inline-only-tradeoffs Q1 (open, for the user); E9 | hypothesis, left to the user |
| A claim about code outside this repository, or one that cannot be checked, is kept and listed as a gap; a name this repository no longer has is not migrated | The shipped skill's "Never invent" (report gaps) | judgement |
| A kept step that names disagreeing code is flagged, not removed | Follows from the kept and not-migrated fates | judgement |
| Not migrated: in no comment and no code; quoted with the code's evidence; the user decides | E5; spec-kit #4940 in docs-for-agents-practice.md ("deciding which side is right stays a human choice"); the shipped skill's "Never invent" | measured hazard; the rule is hypothesis |
| A not-migrated claim leaves the page; the reply quotes it | ADR 0001 reason 1 (the code is the source of truth); E1 ("Stragglers can always be recovered"); E5 (agents follow stale files) | judgement |
| An outside fact the code breaks keeps its text, and the conflict is reported | The shipped skill's "Never invent"; hygiene eval (a reminder deleted a true vendor quota in 2 of 3 Haiku runs) | repo-eval |
| One home: moved and dropped claims leave the page, with no "moved" note | P-26; R13; ADR 0001; the devjiro fix (R6) | practitioner. Counterevidence: Google suggests an onward pointer (R12) |
| The reply is a per-claim fate list | Judges' fix suggestion for C6; in the hygiene eval the clearest discriminator was a reply duty | hypothesis |
| Report other files that duplicate a moved fact, and links to the page | context-layers.md §4 audit duty (untested); E10 | judgement |
| Prefer a comment or an existing docstring; a docstring the skill creates holds only the moved fact, with no opening line saying what the code does (v2) | Iteration 1: 4 of 15 Haiku runs created a docstring that opened by restating the code; iteration 2: 0 of 15 | repo-eval |
| A claim that only describes the code stays dropped; it moves as a constraint only when the page states the rule or gives its reason (v2) | Iteration 1: one Haiku run moved a description as an invented, widened rule; iteration 2: 0 of 3. The shipped skill's "Never invent" | repo-eval |
| One fate-list line per sentence, split only where fates differ; headings are not claims (v2) | Iteration 1: the skill's replies were the longest arm in every case. Iteration 2 showed no measurable shortening | repo-eval; no effect shown |

## The eval

[eval/CASES.md](eval/CASES.md) has the full design. In short:
- **Cases:** seven small Python repositories with unittest tests. Five are for training
  and two are held out (`held_out: true` in `case.yaml`).
- **Requests:** each names one page the user has decided to retire and asks for what
  belongs next to the code to be moved there. No request says "move everything".
- **Arms:**
  - `with_skill` reads this skill;
  - `shipped_skill` reads the shipped hygiene skill;
  - `reminder` adds the sentence in [eval/arms.json](eval/arms.json). It names every
    fate and asks for each claim to be checked against the code. It is deliberately the
    strong competitor; CASES.md says why it was chosen over research.md's shorter
    sentence;
  - `without_skill` gets the request alone.
- **Traps:** in every stale case the value that contradicts the page sits in a different
  file from where the moved fact must be written. Two cases hold a partly true claim: a
  true reason that must move, in the same sentence as a stale value that must not. One
  case has an `AGENTS.md` that repeats a moved fact.
- **Graded:** only what nobody disputes:
  - a stale claim reaches no added comment and no other document, negated or not;
  - the page's restatements of the code are not copied into comments;
  - a moved fact has one home;
  - a kept note stays in exactly one document;
  - the code is unchanged by AST;
  - no file is added;
  - every original comment and docstring is kept, and `AGENTS.md` is byte-identical
    where it exists;
  - the reply flags each stale claim and gives every claim on the page a fate (reply
    focus, keyword checks).
- **Placement** of a moved fact near its symbol, or near the code that uses it, is a
  secondary heuristic. Its graders carry `weight: 0.5`, which the harness ignores, so
  read those rows apart from the rest of `core`.
- **Ungraded:** whether an overview belongs in a module docstring, and whether a
  not-migrated claim stays on the page.
- **Hidden tests** pin the behaviour that a stale claim misdescribes. A run that changes
  the code to match the page fails them; they sit in the preservation check.

The reminder names every fate and asks for each claim to be checked, so on the
repository checks a tie with the skill is a plausible result. Two things the reminder
does not ask for are where the skill can show a difference:
- the per-claim fate list in the reply, and the report of an instruction file that
  repeats a moved fact;
- splitting a sentence whose parts differ in truth.

The reply checks are keyword heuristics, so a win there needs reading the replies before
it is reported. If the skill does not beat the reminder and the shipped skill, that null
result goes here.

Neither expected difference appeared:
- **The reply duties.** The reminder gave every claim a fate and reported the `AGENTS.md`
  duplicate in every run, though its sentence asks for neither: reply checks 70/70,
  against the skill's 69/70.
- **The partly true claims.** Every arm kept the stale value out of the code in nearly
  every run. The skill's two held-out failures were both splitting errors on Haiku.

What did separate the skill from the reminder was not a duty the reminder lacks. It was
two decisions:
- whether to edit the page at all;
- on Haiku, whether an operational note that names a function stays in a document.

## Results

165 graded runs:

| Run set | Runs |
| --- | --- |
| Iteration 1 (v1, training, all arms) | 100 |
| Iteration 2 (v2, training, `with_skill` only) | 25 |
| Held out (v2, all arms) | 40 |

What else applies to these runs:
- **Gate runs.** The 21 gate runs are not counted.
- **Exclusions.** Two held-out runs were excluded and re-run, because the run-limits guard
  blocked them from writing their reply.
- **Skill reads.** Every skill-arm run read its skill before its first edit.
- **Rulings.** The numbers include 27 rulings by auditor agents. Net, they cost the skill
  2 checks and gave the reminder 5.

Mean pass rate and checks passed, from `harness.py summary`:

| Iteration | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `iteration-1-haiku` (v1) | 97.4%, 132/135 | 71.3%, 95/135 | 94.8%, 128/135 | 71.4%, 96/135 |
| `iteration-1-sonnet` (v1) | 100.0%, 90/90 | 89.1%, 79/90 | 100.0%, 90/90 | 82.8%, 75/90 |
| `iteration-2-haiku` (v2) | 99.3%, 134/135 | not run | not run | not run |
| `iteration-2-sonnet` (v2) | 100.0%, 90/90 | not run | not run | not run |
| `heldout-haiku` (v2) | 93.3%, 56/60 | 79.3%, 47/60 | 95.5%, 57/60 | 82.8%, 50/60 |
| `heldout-sonnet` (v2) | 100.0%, 40/40 | 88.6%, 35/40 | 81.8%, 32/40 | 73.5%, 29/40 |

Core checks passed, without the weight-0.5 placement rows, both models together:

| Split | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| Training, iteration 1 (v1) | 54/55 | 36/55 | 52/55 | 35/55 |
| Training, iteration 2 (v2) | 55/55 | not run | not run | not run |
| Held out (v2) | 23/25 | 17/25 | 19/25 | 20/25 |

What the numbers show:
- **Over the shipped skill and the bare model: a clear gain in training. Held out, a lead
  on checks that holds at run level only against the bare model.**
  - Training, iteration 1: 222/225 checks for the skill, against 174/225 and 171/225.
  - Held out: 96/100 checks, against 82/100 and 79/100. Full-mark runs 8/10 against 4/10
    for the shipped skill (stratified exact p = 0.14; 1/10, p = 0.0067, before three
    auditor rulings on its stale-ordering-reason runs) and 1/10 for the bare model
    (p = 0.0067). Full core 8/10 against 6/10 and 7/10.
  - Training, iteration 1, the shipped skill and the bare model:
    - left the page whole while copying its facts into code;
    - copied the page's restatements into docstrings;
    - wrote the disputed rule into code as a to-do;
    - missed the `AGENTS.md` duplicate.
  - The shipped skill scored no better than the bare model on Haiku training (71.3%
    against 71.4%).
  - On held-out Haiku the bare model did better on core (15/15 against 13/15), but lost
    on restraint, preservation and reply.
- **Over the reminder: not established.**
  - **Training, Haiku (+4 checks).** The lead is one case, `ops-notes-in-file-sections`
    (+6), less 2 on `restatement-only-page`, where v1 did worse. On the ops-notes case,
    v1 kept the operational notes out of code in 3/3 runs, against 0/3 for the reminder
    (Fisher p = 0.10). v2 also kept them out in 3/3, but the reminder was not re-run in
    iteration 2 and v2 was revised on these training cases, so the v2 runs are not a
    second comparison.
  - **Training, Sonnet.** A tie, 90/90 each.
  - **Held out, Haiku.** The reminder was one check ahead.
  - **Held out, Sonnet (+8 checks).** The lead is one case: both reminder runs on
    `four-fates-page` left the page whole for the user to delete (p = 0.33), and left
    the NOTIF-9 reason out of the code.
- **The held-out pair, meant as the main test of whether it generalises.** It guards the
  v2 revision against overfitting, but it is not a blind test of v1's rules, whose writer
  saw both cases described and whose build fixer edited them (see Limits, "Held-out
  exposure"). So "carried over" means it held on cases the skill's authors had seen:
  - **Carried over:** the page decision (0 of 10 runs left the page whole), no
    preservation harm (25/25), restraint 19/20, and a fate for every claim (20/20).
  - **Did not carry over:** the Haiku lead over the reminder. Neither held-out case tests
    operational notes that name a function.
  - **New on Haiku:** the skill's two failures were both at the split boundary. One run
    left a true reason out because it sat beside a stale value. Another moved a rule
    whose only stated reason was stale.
- **v2 fixed two of its three targets on the training cases:**
  - created docstrings that open by restating the code: 4/15 Haiku runs to 0/15;
  - a description moved as a rule (`restatement-only-page` core 01, Haiku): 2/3 to 3/3.

  Its third change, shorter fate lists, had no measurable effect: 416 to 423 words on
  Haiku.
- **Cost: longer replies.** The skill's replies ran 1.5 to 1.7 times the reminder's length
  (Haiku held-out: 450 words against 265). Part of this is the per-claim fate list with
  evidence, which is the deliverable.
- **Close calls.** Two ungraded or close calls go to the user (see Next steps):
  - a page detail the code neither states nor contradicts, such as a currency unit;
  - whether a reason given for a stale value should move.

## Running the eval

From the repository root:

```sh
python incubator/harness.py lint fold-docs-inline
python incubator/harness.py self-test fold-docs-inline
python incubator/harness.py prepare fold-docs-inline --iteration iteration-1-haiku --runs 3 --split train
#   give each prompt in eval/iterations/iteration-1-haiku/runs.json to a fresh agent of the chosen model
python incubator/harness.py grade fold-docs-inline --iteration iteration-1-haiku
python incubator/harness.py verify-reads fold-docs-inline --iteration iteration-1-haiku TRANSCRIPT_DIR
python incubator/harness.py summary fold-docs-inline iteration-1-haiku iteration-1-sonnet
```

Run the held-out cases (`--split held-out`) only once, at the end, under their own
iteration name. Exclude and re-run any skill-arm run that `verify-reads` reports as not
reading the skill before its first edit. Record rulings on paraphrases in the run's
`overrides.json`.

The held-out pair (`four-fates-page`, `stale-ordering-reason`) has now run once, on v2.
It is spent: it cannot judge a later version. A v3 needs a fresh held-out pair.

## Limits

Of the eval:
- **Few runs.** 2 or 3 runs per cell detect only large effects. Two-sided Fisher exact
  p-values:
  - 3/3 against 0/3: 0.10;
  - 2/2 against 0/2: 0.33;
  - 0/5 against 3/5: 0.17.

  Every lead over the reminder is one case at these sizes. Totals pool checks that one
  decision can fail together, so they describe the runs; they are not tests.
- **Small fixtures.** Seven small Python repositories with short pages, one case per
  behaviour and one phrasing per request. A long real page will need more judgement than
  the cases test.
- **One model family.** Claude Haiku and Sonnet only. The iteration folders do not
  record exact model versions.
- **Cases built by agents.** Every case, reference, grader and hidden test was written by
  an agent. None comes from a real repository or a user's report.
- **Rulings made by agents.** All 27 rulings (`overrides.json`) were made by auditor
  agents, not a human.
  - Net, they cost the skill 2 checks and gave the reminder 5.
  - One threshold paraphrase was ruled a fail in iteration 2. The same paraphrase passed
    unruled in two iteration-1 runs. Either choice leaves every comparison as it is.
  - Several anchors in `eval/grade.py` misgrade some paraphrases (listed in RESULTS.md).
- **Gate-based case selection.**
  - A bare-model gate ran first on all seven cases, the held-out pair included. Two
    cases were rebuilt to leave headroom, one of them held out ([eval/GATE.md](eval/GATE.md)).
  - The gate was not re-run on the rebuilt fixtures. The bare model still passed their
    stale checks in most runs: `stale-number-elsewhere` 4 of 5, `stale-ordering-reason`
    4 of 5.
  - Selection by a bare gate favours cases where the bare model falls short.
- **Held-out exposure.** The pair is not a blind test of v1's rules.
  - The v1 writer opened no held-out case file, but it read `eval/CASES.md`, which then
    described both held-out cases (at `0679686` it names `four-fates-page` 5 times and
    `stale-ordering-reason` 5 times).
  - The build fixer made 6 tool calls naming a held-out case, read and edited those case
    files, and in the same session made 6 edits to SKILL.md.
  - The v2 reviser made no tool call naming a held-out case, though it read GATE.md and
    CASES.md, which summarise them. The gate shaped one of them.
  - So the pair guards v2 against overfitting. Its comparisons with the reminder and the
    shipped skill are not established, so the exposure produced no false win there. Its
    one held-out lead that holds, full marks over the bare model (8/10 against 1/10), is
    on cases the skill's authors had seen, which may have helped it (a hypothesis).
  - Counts are from the coordinator's scan of the build transcripts
    ([incubator README](../README.md), "Held-out exposure during the builds").
- **Prompt read from a file.** Each agent read its task from `prompt.txt` as its first
  tool call. A real request arrives as a user's message.
- **Activation is untested.**
  - The eval tells the skill arms to read the skill first, so it says nothing about
    whether the description makes the skill load on its own.
  - On its own, the shipped skill loaded in 0 of 18 Haiku and 3 of 18 Sonnet
    should-load runs (#20).
- **Iteration 2 is compared across runs.** v2 ran only `with_skill`. It is compared with
  the other arms' iteration-1 runs.
- **Keyword reply checks.** The reply checks are anchors and keywords. The auditors read
  every failed check and at least a third of the passing heuristic results in each arm.
  For iteration 2 and the held-out pair they read all of them. A paraphrase can still
  slip through.
- **Not measured:** tokens, turns, cost, and whether the user finds the longer fate list
  worth reading.
- **Some behaviours are ungraded.** These include the fate of a big-picture sentence and
  of a page detail the code does not state, such as a currency unit. They come from the
  writer's reading of runs.

Of the skill:
- **No downstream benefit is shown or claimed.** The user's fuller theory is that a
  docs folder helps weaker models on large projects. Retiring a page can remove help
  that this eval does not measure, so the skill is not advice to delete docs.
- **The kept/moved boundary is a hypothesis** (context-layers.md §4). The eval grades
  only claims at its clear ends. The rigour and skeptic judges asked for the user to
  confirm the boundary before building. The skill was built first, and the
  module-docstring question is still open (see Next steps).
- **The split boundary is its weak point on Haiku.** Two held-out runs got it wrong in
  opposite directions:
  - one left a true reason out because it sat beside a stale value;
  - one moved a rule whose only stated reason was stale.
- **Longer replies.** The skill's replies ran 1.5 to 1.7 times the reminder's length,
  and v2's change to the fate list did not shorten them.
- **One home stops at the named page.** Duplicates in instruction files and other
  documents are reported, not removed. Until the user acts on the report, the fact still
  has two homes.
- **Some choices are judgement and still open:**
  - removing not-migrated claims from the page;
  - giving no onward pointer in a slimmed page, which Google's guidance suggests;
  - giving instruction files a fate list only.
- **Comments drift too.** Moving a fact does not keep it true; the shipped skill and its
  `stale-refs` check do that afterwards.

## Next steps

The gate, the four-arm run, one revision (v2) and the held-out run are done. In order:

1. **Put the result to the user.**
   - The graded data support the skill over the shipped skill and the bare model, not
     over the reminder sentence in [eval/arms.json](eval/arms.json).
   - Do not move the skill into a plugin unless the user decides to.
   - Offer the user two options:
     - use the reminder sentence;
     - keep the skill for its page handling and its per-claim evidence.
2. **Ask the user the open questions.** The first two are new from the runs:
   - When the page gives a reason for a value the code contradicts, should the reason
     move to the code's value, or be quoted back with the stale value? Held-out
     `four-fates-page` split the arms on this.
   - What fate does a page detail get when the code neither states nor contradicts it?
     Three Haiku runs gave a currency unit three different fates.
   - Is a module docstring an acceptable home for the big picture (inline-only-tradeoffs
     Q1)?
   - May a slimmed page keep a one-line onward pointer?
   - Should not-migrated claims stay in the page, flagged, instead of leaving it?
   - Should the skill ever edit an instruction file the user names?
3. **Test the page-handling edge against a stronger reminder.** If the user wants the
   skill and the reminder told apart:
   - Add a second reminder arm whose sentence also says to edit the page yourself,
     leaving on it only what has no code home. `harness.prepare` reads only `reminder`,
     so this needs a harness change.
   - Run it against `with_skill` with 5 or more runs per cell, on Haiku and Sonnet. Use
     the cases where the two diverged: `ops-notes-in-file-sections`,
     `slim-page-one-home` and `four-fates-page`. `four-fates-page` is no longer a
     held-out test.
4. **Fix the anchor gaps in `eval/grade.py`.** RESULTS.md, "Rulings", lists nine. Then:
   - run `python incubator/harness.py self-test fold-docs-inline`;
   - re-grade every iteration with `harness.py grade`;
   - check that each `overrides.json` ruling still matches the check or is no longer
     needed. Keep the rulings as a record.
5. **Settle the threshold-paraphrase standard.** The run is
   `iteration-2-haiku/ops-notes-in-file-sections/with_skill/run-3`. A human should decide
   whether its ruling stands:
   - if it stands, add the same ruling to `iteration-1-haiku/ops-notes-in-file-sections`
     `with_skill/run-2` and `reminder/run-2`;
   - if not, withdraw it.

   Then re-grade and update RESULTS.md.
6. **Do not edit the skill from the held-out failures.** If the split boundary is worth
   fixing:
   - build training cases for both errors: a true reason attached to a stale value, and
     a rule whose only stated reason is stale;
   - gate them on the bare model (Haiku x3, Sonnet x2) and keep cases with bare
     failures;
   - make a v3 from training failures only;
   - build a fresh held-out pair, and run it once.
7. **Decide whether reply length matters.** If the user finds the fate list too long:
   - try one change on the training cases, such as a cap on lines or one line per page
     bullet;
   - measure words and list items, and check that the reply checks do not regress.
8. **Harness fixes**, all in `incubator/harness.py`:
   - make `verify-reads` store its own result in the iteration folder (the stored
     `verify-reads.json` files were written by an out-of-repository wrapper; see
     [incubator/README.md](../README.md));
   - add a `placement` focus, so the weight-0.5 rows leave Core;
   - tell run agents to write RESPONSE.md with a file-writing tool rather than a shell
     heredoc. The run-limits guard read `>` in reply text as a redirect, and blocked two
     runs.
9. **Before any shipping decision:**
   - run an activation eval, with should-load requests and near misses: updating a doc
     for a change, explaining a doc, writing a setup README;
   - add an arm with both this skill and `code-comments` loaded, since that is how they
     would ship;
   - use a model outside the Claude family;
   - try one long page from a real repository.
10. **Deferred, as before:**
    - a read-only `doc_claims.py` worksheet, only if runs show missed stale claims. In
      60 skill runs, one carried part of a stale claim into a comment. It had found the
      contradiction, and the error was in the split, which a worksheet would not fix.
    - the TypeScript case with a cross-file pointer that research.md proposed.
