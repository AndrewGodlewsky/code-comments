# fold-docs-inline: eval cases

Seven cases, designed on 2026-11-11 before any result existed: five for training and two
held out (`held_out: true` in `case.yaml`). The same day, still before any run, a review
found the stale-claim checks too lenient and the traps too easy, and the cases were
rebuilt (see "Changes after review" below). A derivability gate then ran each case
without any skill (Haiku twice, Sonnet once). Bare models passed every core check of two
cases in all three runs, so those two were rebuilt, and three reply anchors that misgraded
correct replies were fixed. [GATE.md](GATE.md) has the gate results and every change.
Each case is a small Python repository with unittest tests. In every case the user names
one docs page they have decided to retire, and asks for what belongs next to the code to
be moved there. No request says "move everything".

Each claim on a page has one fate:
- **dropped:** the code already says it;
- **moved:** it goes into a comment at the code it governs;
- **kept:** it stays in a document, because it has no code to sit beside;
- **not migrated:** the code contradicts it, so it is reported to the user.

A claim can split: in two cases one sentence carries a true reason, which moves, and a
stale value, which does not.

## What is graded

Only what nobody disputes is graded:
- **A stale claim reaches no comment and no other document.** No added comment or
  docstring line, and no added line in a document other than the retired page, states it.
  There is no exemption for negated or historical lines ("not three times as the old page
  said"): the code never holds the stale value, and a "the page said" note is history,
  which the not-migrated fate keeps out of the code. A to-do that treats the claim as an
  unmet requirement ("ACC-12 wants case-insensitive names; not done yet") also fails,
  because which side is right is the user's call. In `stale-number-elsewhere` and
  `stale-ordering-reason` the check reads whole comment blocks, docstrings and paragraphs,
  sentence by sentence, so a claim wrapped over two docstring lines is still seen. In
  `stale-ordering-reason`, `write_feed()` really does sort its own input, so a sentence that
  says so ("both inputs are sorted here first") is a true statement of the code and
  passes. Any line added at `stock_rows()` that ties its sort to `write_feed` or the merge
  fails, negated or not.
- **The page's restatements are not copied into comments.** Each case lists narrow anchors
  for its restating clauses, and some cases also require named files or symbols to gain
  no comment at all.
- **A moved fact has one home:** it is in the code and in no document. In
  `slim-page-one-home` the instruction file `AGENTS.md` also states the fact; it must not
  be edited, so it is set aside for this check.
- **A kept note stays in exactly one document** and in no comment.
- **The code is unchanged** by AST, plus hidden behaviour tests where a stale claim
  invites "fixing" the code. These are preservation checks.
- **No file is added**, and instruction files are byte-identical.
- **The reply** flags each stale claim in one bullet or paragraph (the stale value and
  the code's value or a contrast word together), and gives every claim on the page a
  fate, by one anchor per claim. The per-claim fate list is the skill's own deliverable,
  and the reminder sentence does not ask for it.

**Placement** beside the governing symbol is a secondary heuristic (grader `weight: 0.5`).
It accepts the symbol the fact names and the code that uses it, such as the retry loop
for a retry count. The harness ignores weights and has no `placement` focus, so these
rows are counted in Core; read them apart. Adding a focus to `harness.FOCUSES` is the
coordinator's call.

**Ungraded:**
- whether a big-picture claim belongs in a module docstring or a document
  (inline-only-tradeoffs Q1);
- whether a not-migrated claim stays on the page, flagged, or leaves it (an open question
  in the README). The stale checks skip the retired page.

**The graders are more lenient than the skill in one place.** The skill keeps a kept
claim on the page and leaves every other document byte-identical. The graders only ask
that a kept note sits in exactly one document, so moving it into an existing document
such as README.md passes. Other documents may gain lines but lose none.

**Hidden tests** (`hidden/<case>/hidden_tests/`) pin only the behaviour a stale claim
misdescribes: pauses that double (2, 4, 8, 16 seconds), case-sensitive names, rows in any
order (because `write_feed` sorts them itself), a 6-hour gap. A run
that changes the code to match the page fails them. The AST check catches the same
edit, so they add a behavioural reading and confirm that the answer key's "stale"
verdicts are true of the code. They sit inside the preservation check "code unchanged".

## Cases

Check kinds:
- **M:** mechanical (AST, file existence, byte identity, symbol spans, hidden tests).
- **A:** anchor. Mechanical, but it relies on the fact keeping its number or ticket id
  (such as `250`, `FIN-88`, `#fin-ops`), so a paraphrase without it misgrades.
- **H:** keyword heuristic. Record a misgrade in `overrides.json`.

Every case has at least one core check and at least one preservation or restraint check.
Reply checks have `focus: reply`.

| Case | Split | Behaviour | Trap a competent but unaware editor falls into | Where the evidence lives | H and A checks |
| --- | --- | --- | --- | --- | --- |
| `stale-number-elsewhere` | train | A claim that is only partly true: move the reason, keep the stale detail out, when the numbers seem to match and the contradiction is in a third file | Checks the page's numbers against `orders/settings.py` (`ATTEMPTS = 5`, `PAUSE_SECONDS = 2`: both match), then copies "up to 5 times, 2 seconds apart, because ... (OPS-19)" into a comment at the retry loop or at `ATTEMPTS`. The loop calls `pause_after(attempt)`, which doubles each pause. Also pastes the paging restatements into docstrings | `orders/backoff.py`: `pause_after()` returns `PAUSE_SECONDS * 2 ** (failures - 1)`. `orders/settings.py` calls `PAUSE_SECONDS` the wait "after the first failed attempt" | 01 H, 02 A, 03 A, 04 H (placement), 05 H, 09 H (reply), 10 H (reply) |
| `restatement-only-page` | train | Dropped: every claim restates the code or an existing docstring | Adds a docstring to `is_blank` or extends the accurate docstrings with the page's wording | `ingest/rows.py`: the one-line body of `is_blank` and the existing docstrings | 06 H (reply), 07 H (reply) |
| `slim-page-one-home` | train | One home when part of the page must stay, and an instruction file repeats a moved fact | The request only says "retiring", so the editor deletes the page with its "Who to ask" notes, or leaves it whole. Or it edits `AGENTS.md` to remove its FIN-88 line, or drops the FIN-88 reason from the move because `AGENTS.md` already has it | `docs/billing.md`: the "Who to ask" section is about people. `AGENTS.md` line 5 repeats FIN-88 and is an instruction file | 01 A, 02 A, 03 H (placement), 04 A, 05 H, 09 to 11 H (reply) |
| `ops-notes-in-file-sections` | train | Kept: operational notes stay in a document, though the request says the page "is going" | The page is organised by source file, and its operational notes name `can_send()` and `send_refund()`. The editor moves each file's section into that file, ops notes included, or deletes them with the page | `refunds/approval.py` and `refunds/provider.py` contain no escalation channel, sandbox or API-key handling | 01 A, 02 A, 03 A, 04 H (placement), 05 H, 09 H (reply) |
| `spec-claim-code-disagrees` | train | Not migrated, and no code change, when the page reads like a requirement and the contradiction is one import away | Treats "case-insensitive (ACC-12)" as a spec. It adds `.lower()` to `normalise_name`, or writes the claim at `find_user`, whose call to `normalise_name()` reads as if it might fold case | `accounts/names.py`: `normalise_name()` returns `name.strip()`. The request asks only for a docs migration | 01 H, 02 A, 03 H, 07 H (reply), 08 H (reply) |
| `stale-ordering-reason` | **held out** | Not migrated: a stale coupling (a reason, not a value) whose mechanism still exists, in a file that the moved fact does not touch | Opens `write_feed`, finds the merge pass the page describes (its docstring says "walked together in a single merge pass"), and writes "must stay sorted: write_feed merge-joins with the price list" at the unexplained sort in `stock_rows` | `stock/feed.py`: `write_feed` loops over `sorted(rows)` and `sorted(prices)`, so the order it is given does not matter | 01 H, 02 A, 03 H (placement), 04 H, 08 H (reply), 09 H (reply) |
| `four-fates-page` | **held out** | All four fates on one page, with a partly true claim and an ungraded big-picture sentence | Copies "until 24 hours after the last one ... (NOTIF-9)" into `due()`, keeps MAIL-71 on the page, moves the `#mail-ops` note into code, or deletes the page with its kept notes | `notify/settings.py`: `MIN_HOURS_BETWEEN_DIGESTS = 6`, while `due()` in `notify/digest.py` shows only the name. `SUBJECT_LIMIT` is in `notify/mail.py`. Nothing in the code handles pausing | 01 H, 02 A, 03 A, 04 H (placement), 05 A, 06 H, 10 H (reply), 11 H (reply) |

Every case also has these mechanical checks:
- **Code unchanged:** an AST comparison of every original `.py` file, with comments and
  docstrings removed. It includes the hidden tests where the case has them.
- **Prose and docs kept:** every original comment and docstring is kept word for word,
  and other documents lose no line. AGENTS.md must be byte-identical where it exists.
- **No new files.**

## Answer key: claim fates per case

| Case | Dropped | Moved (where) | Kept in a document | Not migrated | Ungraded |
| --- | --- | --- | --- | --- | --- |
| `stale-number-elsewhere` | module purpose; paging until an empty page; `upsert` replaces by id; "up to 5 times" (`ATTEMPTS = 5` says it) | OPS-19 reason → retry loop in `ShopClient.get_page` (or `ATTEMPTS`); PAGE_SIZE at or below 250, HTTP 400 → `PAGE_SIZE` in orders/client.py | none (page deleted) | "2 seconds apart" (code: 2, 4, 8, 16 seconds, from `pause_after` in orders/backoff.py) | none |
| `restatement-only-page` | all five claims | none | none (page deleted) | none | none |
| `slim-page-one-home` | `invoice_total` sums and rounds | FIN-88 half-up → `invoice_total`; packing slips → `invoice_lines` | Who to ask (FINQ, accounts-receivable lead) | none. AGENTS.md's FIN-88 line is reported as a duplicate, not edited | none |
| `ops-notes-in-file-sections` | `needs_second_approver` threshold; `send_refund` posts | PAY-31 → `SECOND_APPROVER_THRESHOLD`; idempotency key → `send_refund` | #fin-ops escalation; 90-day key rotation | none | sandbox Monday reset (kept in the reference) |
| `spec-claim-code-disagrees` | spaces ignored; `NameTaken`; the member role | ACC-30 spam wave → `grant_role` | none (page deleted) | case-insensitive names, ACC-12 (code is exact) | none |
| `stale-ordering-reason` | no-stock filter; tab-separated lines | MKT-204 four-digit column → `MAX_FEED_QTY` in stock/format.py | none (page deleted) | `stock_rows` must sort for the merge join, and out-of-order rows are skipped (code: `write_feed` sorts both inputs itself) | none |
| `four-fates-page` | `build_digest` groups by project | NOTIF-9 reason → `due()` (or `MIN_HOURS_BETWEEN_DIGESTS`); MAIL-71 relay folding → `SUBJECT_LIMIT` in notify/mail.py | #mail-ops incident note | "24 hours" (code: 6) | nightly-cleanup ordering (module docstring or document) |

## Headroom (expectations, not results)

A run that changes nothing passes the preservation and restraint checks, as any "do not
do X" check must, and the stale-claim check. It fails every reply check and, in six
cases, every moved-fact check: between 4 and 6 checks out of 7 to 11 per case. In the
partly true claims, only a run that both moves the reason and checks the stale detail
passes both core checks.

These were the expectations before the gate. [GATE.md](GATE.md) has what the bare models
actually did.

- **Haiku:** expected to fail the core checks in most cases. It changes code beyond the
  task far more often than Sonnet: 53 of 360 attempts against 6 of 360 in
  `churn-2026-11-07.md`, which counts changed code lines with comments stripped. That
  bears on the code-unchanged check, not on how many comments it writes. These requests
  also invite literal copying.
- **Sonnet:** expected to fail most often here:
  - `stale-number-elsewhere`: copying "2 seconds apart" with the reason, because both of
    the page's numbers match `orders/settings.py`;
  - `four-fates-page`: copying the whole sentence when it moves the reason without
    opening the settings file;
  - `spec-claim-code-disagrees`: trusting the name `normalise_name`;
  - `restatement-only-page`: adding a docstring to the undocumented `is_blank`;
  - `slim-page-one-home`: deleting the page because the user is "retiring" it, or
    tidying `AGENTS.md`;
  - `ops-notes-in-file-sections`: notes that name a function.
- **Ceiling risk:** if bare models routinely follow a name to its definition, the stale
  cases will sit at ceiling on core. The skill would then show its effect only in the
  reply checks (the fate list and the duplicate report) and in restatement restraint.
  The gate found exactly this in two cases, where the contradicting value was one import
  away and plainly different from the page. Those two were rebuilt before any evaluation
  run, so that the page's numbers or mechanism look confirmed and the contradiction needs
  one more step to see (GATE.md). If they still sit at ceiling in the evaluation, report
  it; do not harden them again from evaluation results.
- **Reminder arm:** see below. It is expected to match the skill on most repository
  checks.

## The reminder arm

`arms.json` holds one sentence: "Before moving anything off that page, check each claim
against the code: leave out what the code already shows, don't carry over anything the
code contradicts (tell me about it instead), put each remaining code-specific fact in one
comment beside the code it governs and take it off the page, keep anything with no code
to sit beside in a document, and don't change any code or create new files."

It was chosen over the shorter sentence that research.md proposed from the C6 candidate
("Keep only what the code cannot show, put each fact beside the code it governs, and give
each fact one home"). That one leaves out checking claims against the code and keeping
notes with no code home, so the skill would beat it on those rules almost by
construction, which is close to a strawman. The chosen sentence names every fate. A tie
with the skill on the repository checks is therefore a plausible and honest result. What
the skill adds over it is measured by:
- the reply checks for a per-claim fate list and for naming a duplicate in an
  instruction file, which the reminder does not ask for;
- the partly true claims, where the reminder says "check each claim" but not "split a
  sentence whose parts differ in truth".

Running both sentences as separate arms would need a second reminder arm in
`harness.prepare`, which reads only `reminder`; that is the coordinator's call.
research.md's "Reminder arm" paragraph still describes the shorter sentence.

## Changes after review (2026-11-11, before any run)

- Stale checks no longer exempt negated lines, cover added lines in other documents, and
  have wider patterns (ACC-12, "case ignored", "SKU order").
- The contradicting value now sits in a different file from where the moved fact must be
  written: `ATTEMPTS` in `orders/settings.py` while the retry loop and `PAGE_SIZE` are in
  `orders/client.py`; `normalise_name` in `accounts/names.py`; `MAX_FEED_QTY` in
  `stock/format.py` while `write_feed` is in `stock/feed.py`; `SUBJECT_LIMIT` in
  `notify/mail.py` while the gap is in `notify/settings.py`.
- `stale-number-elsewhere` and `four-fates-page` now hold a partly true claim (the
  clause-level case research.md proposed).
- Every case has a restatement check, and every case has a reply check that each claim
  is accounted for.
- `slim-page-one-home` gained the bystander `AGENTS.md` duplicate research.md proposed.
- The prompts of `slim-page-one-home`, `ops-notes-in-file-sections` and `four-fates-page`
  no longer say that some of the page may stay.
- Placement checks accept the code that uses a constant.
- Hidden tests lost their incidental assertions. In `spec-claim-code-disagrees` they moved
  into the preservation check "code unchanged".

## Changes after the derivability gate (2026-11-11, before any evaluation run)

[GATE.md](GATE.md) has the reasons. In short:
- **`stale-number-elsewhere` rebuilt.** The page's count is now true (`ATTEMPTS = 5`), and
  so is its first pause (`PAUSE_SECONDS = 2`). Its "2 seconds apart" is stale: the retry
  loop calls `pause_after()` in the new `orders/backoff.py`, which doubles each pause. The
  stale check, the hidden tests, the placement homes, a restatement anchor ("up to 5
  tries") and the reply check changed to match. The bullet above about `ATTEMPTS` in
  `orders/settings.py` describes the case before this change.
- **`stale-ordering-reason` rebuilt.** `write_feed()` is now a real merge pass over
  `(sku, value)` pairs, but it sorts both inputs itself, so the page's requirement on
  `stock_rows()` is stale even though its mechanism is not. The stale check, the hidden
  tests and the reply check changed to match.
- **Stale checks of these two cases read blocks.** They read whole comment blocks,
  docstrings and paragraphs, so a sentence wrapped over docstring lines is seen. The old
  line-level check let one gate run's coupling note at `stock_rows` pass for that reason.
- **Three reply anchors widened** where a correct reply was failed: "empty-page" and
  "page-by-page" (`stale-number-elsewhere`), "what invoice_total() ... do was already in
  their docstrings" (`slim-page-one-home`), and "send_refund(): what it returns"
  (`ops-notes-in-file-sections`).

## Limits

- One case per behaviour, one realistic phrasing per case, and Python only.
- The boundary between "kept" and "moved" is a hypothesis (context-layers.md §4). Only
  claims at its clear ends are graded: operational and organisational notes with no
  code referent, and reasons tied to one named symbol.
- Anchor checks miss a paraphrase that drops the number or ticket id. The reference
  replies keep them, and the shipped skill asks for ticket ids to be kept.
- The strict stale checks fail a correct comment that happens to repeat the stale value
  ("this is not the 24 hours the page claimed"). That is by design, but a ruling in
  `overrides.json` may still be warranted for an unusual phrasing.
- Three rulings in GATE.md decide contested runs, and the checks follow them:
  - Leaving the retired page whole, with the moved facts copied into the code, fails
    "one home".
  - A docstring on `is_blank` that restates its one-line body fails, although the file's
    other functions have docstrings.
  - A to-do in the code about the disputed ACC-12 rule fails.
  A reader who disagrees should re-read those runs, not loosen the checks.
- The reply checks are keyword checks over bullets and paragraphs. They accept number
  words, but a reply that names a claim only by a pronoun misgrades.
