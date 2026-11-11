# fold-docs-inline

A candidate skill for the user who has already decided to slim or retire one docs page.
It gives every claim on that page a fate, so that each fact about the code ends with one
home beside the code it governs. The fates are:
- **dropped:** the code already says it;
- **moved:** it goes into a comment at the file and symbol it governs;
- **kept:** it stays in a document, because it has nothing in the code to sit beside;
- **not migrated:** the code contradicts it, so it is reported to the user.

The user reviews the per-claim fate list in the reply.

**Status: built; evaluation pending.** No run has been made, so there is no result to
report. The skill makes no performance claim. It is ideation candidate C6 for issue
[#50](https://github.com/AndrewGodlewsky/code-comments/issues/50), and it does not ship.

- Skill: [skill/fold-docs-inline/SKILL.md](skill/fold-docs-inline/SKILL.md)
- Research: [research.md](research.md)
- Eval design: [eval/CASES.md](eval/CASES.md)

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
  true reason that must move, in the same sentence as a stale count that must not. One
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

## Limits

- **No downstream benefit is shown or claimed.** The user's fuller theory is that a
  docs folder helps weaker models on large projects. Retiring a page can remove help
  that this eval does not measure, so the skill is not advice to delete docs.
- **The kept/moved boundary is a hypothesis** (context-layers.md §4). The eval grades
  only claims at its clear ends.
- **Graders are partly keyword and anchor checks.** A paraphrase that drops a number
  or ticket id can misgrade.
- **The cases are small.** There is one case per behaviour, the code is Python only,
  and the pages are short. A long real page will need more judgement than the cases
  test.
- **One home stops at the named page.** Duplicates in instruction files and other
  documents are reported, not removed. Until the user acts on the report, the fact still
  has two homes.
- **Some choices are judgement and still open:**
  - removing not-migrated claims from the page;
  - giving no onward pointer in a slimmed page, which Google's guidance suggests;
  - giving instruction files a fate list only.
- **Comments drift too.** Moving a fact does not keep it true; the shipped skill and its
  `stale-refs` check do that afterwards.
- **Activation is not measured.** The trigger is an explicit, named request, the
  favourable case seen in #20, but no activation eval has been run.

## Next steps

1. Pilot the training split on Haiku and Sonnet with all four arms. Paid runs need the
   user's approval, with the estimated and actual cost reported.
2. Grade the pilot, check reads with `verify-reads`, and record overrides. Then compare
   `with_skill` against `reminder` and `shipped_skill` focus by focus. Report a tie or a
   loss as a result.
3. Edit the skill only from training-split failures. Then run the held-out split once.
4. Ask the user the open questions:
   - Is a module docstring an acceptable home for the big picture (inline-only-tradeoffs
     Q1)?
   - May a slimmed page keep a one-line onward pointer?
   - Should not-migrated claims stay in the page, flagged, instead of leaving it?
   - Should the skill ever edit an instruction file the user names?
5. Add a read-only `doc_claims.py` worksheet only if runs show missed stale claims. It
   would list the names and values each claim mentions and where the code defines them.
   It would use the standard library only and store nothing.
6. Consider the case research.md proposed that this set still lacks: a TypeScript page
   with a cross-file pointer. The bystander `AGENTS.md` and the partly true claim are now
   part of `slim-page-one-home`, `stale-number-elsewhere` and `four-fates-page`.
7. Decide whether the harness gets a `placement` focus, so that the weight-0.5 placement
   checks leave the Core column, and whether research.md's shorter reminder sentence
   should run as a second reminder arm. Both need changes to `incubator/harness.py`.
8. If the user wants it in the plugin, write activation cases for it, including near
   misses: updating a doc for a change, explaining a doc, and writing a setup README.
