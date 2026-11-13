# fold-docs-inline: derivability gate

The gate asks one question of each case before any evaluation run: can a bare model
already do the core behaviour? A case whose core checks every bare run passes cannot
show what the skill adds. The gate ran each of the seven cases with no skill and no
reminder (`without_skill`): Haiku twice and Sonnet once, on 2026-11-11.

Gate runs are for case selection only. They will not be reused as evaluation runs, and
no skill edit may be based on them. The run records are in
[iterations/gate-haiku](iterations/gate-haiku) and [iterations/gate-sonnet](iterations/gate-sonnet).
Their `grading.json` files come from the grader and fixtures as they were before this
change, and are left as recorded. The two rebuilt cases cannot be regraded, because
their `files/` changed.

## Results per case

The numbers are checks passed per run, by focus, as recorded. "Core at ceiling" means
every core check passed in all three runs.

| Case | Split | Haiku run 1 | Haiku run 2 | Sonnet run 1 | Core at ceiling | Outcome |
| --- | --- | --- | --- | --- | --- | --- |
| `stale-number-elsewhere` | train | 9/10 (core 4/4) | 8/10 (core 4/4) | 9/10 (core 4/4) | yes | rebuilt |
| `restatement-only-page` | train | 6/7 (core 1/2) | 6/7 (core 1/2) | 6/7 (core 1/2) | no | kept |
| `slim-page-one-home` | train | 7/11 (core 3/3) | 6/11 (core 1/3) | 7/11 (core 1/3) | no | kept, reply anchor fixed |
| `ops-notes-in-file-sections` | train | 5/9 (core 2/3) | 6/9 (core 2/3) | 8/9 (core 3/3) | no | kept, reply anchor fixed |
| `spec-claim-code-disagrees` | train | 6/8 (core 1/2) | 6/8 (core 1/2) | 6/8 (core 1/2) | no | kept |
| `stale-ordering-reason` | held out | 7/9 (core 3/3) | 8/9 (core 3/3) | 9/9 (core 3/3) | yes | rebuilt |
| `four-fates-page` | held out | 10/11 (core 4/4) | 10/11 (core 4/4) | 7/11 (core 2/4) | no | kept |

Under the fixed reply anchors, three recorded reply results change. All three are reply
checks, so no core result changes:
- `ops-notes-in-file-sections`, Haiku run 1: reply 1/1 (was 0/1).
- `slim-page-one-home`, Sonnet run 1: reply 2/3 (was 1/3).
- `stale-number-elsewhere`, Haiku run 2: reply 2/2 (was 1/2).

## Every failed check, and the ruling

A check that failed a run doing the right thing is a grader bug. A check that failed a
run doing the wrong thing stays.

### Grader bugs (fixed)

1. **`stale-number-elsewhere` reply 10, Haiku run 2.** The reply gives paging its fate:
   "The page-by-page read and the empty-page stop condition are now in the
   `sync_orders()` docstring". The anchor `empty (page|list)` needed a space. It now
   accepts `empty[- ]` and `page[- ]by[- ]page`. The run still fails restraint 05 for
   adding that docstring.
2. **`slim-page-one-home` reply 11, Sonnet run 1.** The reply gives the `invoice_total`
   restatement its fate: "The description of what `invoice_total()` and `invoice_lines()`
   do was already in their docstrings, so I did not repeat it." No anchor matched. The
   anchor now also accepts `what invoice_total` and `invoice_total ... already` within one
   sentence. Haiku runs 1 and 2 still fail it: neither reply mentions that claim at all.
3. **`ops-notes-in-file-sections` reply 09, Haiku run 1.** The reply gives `send_refund`'s
   return value its fate: "docstring of send_refund(): what it returns". The anchor had no
   word for "returns". It now accepts `send_refund ... returns` within one sentence, and
   "what it returns". The run still fails restraint 05 for that docstring.

The three fixes were checked against the recorded replies. The three misgraded runs now
pass. Every other run's result on these checks is unchanged, including the two genuine
misses in `slim-page-one-home`.

### A false pass, fixed by the rebuild

`stale-ordering-reason` check 01, Haiku run 2, passed but should not have. It added this
to the `stock_rows` docstring: "The result is sorted by SKU so the / feed is written in a
stable order; write_feed() does not depend on that order." That is commentary on the
stale coupling at the sort, and it invents a reason for the sort. The statement says
negated phrasings count. The line-level check missed it because the sentence was split
across two docstring lines. The rebuilt check reads whole blocks, and fails any line
added at `stock_rows` that names `write_feed` or the merge. A synthetic copy of this edit
on the rebuilt case fails check 01.

### Real failures (kept)

- **The retired page left whole, its facts copied into code.** This happened in
  `four-fates-page` (Sonnet: "docs/digests.md itself is untouched; delete it when
  ready") and `slim-page-one-home` (Haiku run 2, Sonnet). It fails "one home" (core) and,
  where a kept note was also copied to `docs/oncall.md`, "in exactly one document". The
  ruling is that it is a real failure. The user asked to *move* the facts. After the run
  the repository holds every moved fact twice, which is the drift this project exists to
  remove. A later deletion is promised by nobody. The runs left the page whole to protect
  a note with no code home, and slimming the page would have kept that note. This is one
  decision failing two or three checks, so read those rows together.
- **Restating docstrings copied from the page.** In `restatement-only-page`, all three
  runs gave the undocumented `is_blank` the page's sentence as a docstring. The body is
  one line that says the same, so the check stands. The file's other functions have
  docstrings, so this is the most style-like trap in the set. The evidence it needs (the
  one-line body) is in the file.
  - Haiku run 2 also put the "csv only" note in the module docstring.
  - In `four-fates-page`, `build_digest` gained "Group a user's unread notifications by
    project." (Haiku, both runs) and "Group the unread notification texts by project."
    (Sonnet).
  - In `stale-number-elsewhere`, `sync_orders` and `upsert` gained docstrings and
    comments (all runs).
  - In `ops-notes-in-file-sections`, `send_refund` gained "Post the refund to the
    provider and return the provider's refund id." (all runs).
  - In `spec-claim-code-disagrees`, whitespace trimming and `NameTaken` were restated
    (all runs).
- **The disputed ACC-12 rule written into the code.** In `spec-claim-code-disagrees`,
  all three runs added a note at `normalise_name` such as "although ACC-12 specifies
  case-insensitive usernames. Fixing that means lowercasing here" and "Open: decide
  whether to fold case here (see ACC-12)". The case's rule stands: the next editor is told
  to change the code to match a page that may be wrong, and which side is right is the
  user's call. Every run also reported the conflict in its reply, so the reply checks
  pass.
- **Operational notes moved into code, or deleted.** In `ops-notes-in-file-sections`,
  both Haiku runs put the #fin-ops escalation in `can_send`'s docstring, put the key
  rotation in `send_refund`'s, and deleted the page. In `slim-page-one-home`, Haiku run 1
  deleted the page with its "Who to ask" notes and left them only in the reply.
- **An accurate docstring extended.** "Return the order's items as invoice lines." became
  "..., sorted by SKU." (`slim-page-one-home`, both Haiku runs), and the `stock_rows`
  docstring gained ", sorted by SKU." (`stale-ordering-reason`, Haiku run 1). The
  preservation check asks for word-for-word, and the added clause restates the code.
- **The AGENTS.md duplicate not reported** (`slim-page-one-home`, all runs), and the
  `invoice_total` restatement given no fate (`slim-page-one-home`, both Haiku runs).

## Hardening the two ceiling cases

Both cases share one pattern. The contradicting value sat one import away, it was plainly
different from the page, and the page named the function to check. Every run opened it,
saw the difference, and kept the stale claim out. The rebuilt cases test the same
behaviour, with the same fate. Each claim's surface now checks out: the numbers match a
settings file, or the mechanism the page describes really exists. The contradiction
takes one more step to see. All the evidence a careful editor needs is still in the
repository. Requests, prompts and held-out status are unchanged; only the
`stale-number-elsewhere` prompt's "Input files" list gained the new file.

### `stale-number-elsewhere` (training)

- **Before:** the page said "up to 3 times, 2 seconds apart"; `orders/settings.py` had
  `ATTEMPTS = 5` under a comment naming it.
- **Now:**
  - The page says "up to 5 times, 2 seconds apart". `orders/settings.py` has
    `ATTEMPTS = 5` and `PAUSE_SECONDS = 2`, commented as the wait "after the first failed
    attempt". Both of the page's numbers match.
  - The retry loop in `ShopClient.get_page` sleeps `pause_after(attempt)`, from the new
    `orders/backoff.py`, which returns `PAUSE_SECONDS * 2 ** (failures - 1)`. The pauses
    are 2, 4, 8 and 16 seconds, so "2 seconds apart" is stale.
  - The visible test checks one retry and its single 2-second pause, which is true and
    looks like confirmation.
- **Natural wrong edit:** verify both numbers against `orders/settings.py`, then copy "up
  to 5 times, 2 seconds apart, because ... (OPS-19)" into a comment at the loop or at
  `ATTEMPTS`.
- **Evidence:** the body of `pause_after()`, imported by name into the edited file. The
  word "first" in the settings comment is a further hint.
- **Checks changed:**
  - 01 is now "no added sentence states a fixed 2-second spacing". It reads whole blocks,
    sentence by sentence. "Apart", "every 2 seconds" and "a fixed pause" always fail,
    negated or not. "2 seconds between attempts" fails unless the same sentence says the
    pauses grow or that 2 is the first.
  - 04 (placement) also accepts `PAUSE_SECONDS` and `pause_after`.
  - 05 also anchors "up to 5 tries", a restatement of `ATTEMPTS`.
  - 06's hidden tests pin the doubling pauses and the five attempts.
  - 09 asks the reply to contrast the fixed spacing with the doubling.

### `stale-ordering-reason` (held out)

- **Before:** `write_feed` looked prices up with `prices.get(sku)`, so it plainly needed
  no order.
- **Now:**
  - `write_feed` is a real merge pass over `(sku, value)` pairs, and its docstring says
    "The two lists are walked together in a single merge pass". The page's description of
    the mechanism is true.
  - But the loop runs over `sorted(rows)` and `sorted(prices)`. The page's requirement on
    `stock_rows()`, and its "a row that arrives out of order is silently skipped", are
    stale.
  - The `sorted()` in `stock_rows` has no stated reason, which invites one.
- **Natural wrong edit:** open `write_feed`, find the merge pass, and write the page's
  reason at the unexplained sort.
- **Evidence:** `sorted(rows)` on the loop line of `write_feed`, the function the page
  names.
- **Checks changed:**
  - 01 fails any line added at `stock_rows` that ties its sort to `write_feed`, the merge
    or a requirement, negated or not.
  - Elsewhere, 01 fails a sentence saying rows must arrive sorted or that a row out of
    order is skipped. A negated sentence passes, and so does one about `write_feed`
    sorting its own input ("sorted here first"), because both are true of the code.
  - 05's hidden tests pin that rows and prices in any order are all written, in SKU
    order.
  - 08 asks the reply to say the claim is out of date because `write_feed` sorts the rows
    itself.

### How the rebuilt checks were tested

`python incubator/harness.py self-test fold-docs-inline` prints `self-test ok`: every
reference passes every check, and every untouched `files/` fails at least one. Each
fixture's own tests pass on `files/` and on the reference. Synthetic runs were graded
with the real checks: the reference plus one edit each.

- **`stale-number-elsewhere`, edits that fail check 01:**
  - the whole clause copied at the loop (it also fails restraint 05 for "up to 5");
  - "retried 2 seconds apart" at `ATTEMPTS`;
  - "a 2-second pause between attempts";
  - a docstring sentence wrapped over two lines;
  - "Not 2 seconds apart, as the old page said".
- **`stale-number-elsewhere`, edits that pass:** "the first pause is 2 seconds and each
  later pause doubles", and "2 seconds between the first two attempts, doubling after
  that".
- **`stale-number-elsewhere`, code changed to fixed spacing:** fails the AST check and the
  hidden tests.
- **`stale-ordering-reason`, edits that fail check 01:**
  - the coupling as a comment at the sort;
  - the coupling added to the `stock_rows` docstring (which also fails preservation);
  - the gate's Haiku run-2 sentence;
  - "Callers must pass rows sorted by SKU" at `write_feed`;
  - the requirement added to README.md.
- **`stale-ordering-reason`, edits that pass check 01:**
  - "Sorted by SKU." at `stock_rows` (it fails restraint 04 only);
  - "Both inputs are sorted here first, so callers may pass rows in any order";
  - "The merge pass relies on sorted input, so both lists are sorted here first".
- **`stale-ordering-reason`, code changed to stop sorting the rows:** fails the AST check
  and the hidden tests.

## Cases kept as they are

None of the five other cases is at ceiling: each has a core failure in at least one bare
run.
- `restatement-only-page` and `spec-claim-code-disagrees` failed core in all three runs.
- `slim-page-one-home` failed core in two runs.
- `ops-notes-in-file-sections` failed core in both Haiku runs.
- `four-fates-page` failed core in the Sonnet run.

No case was kept at ceiling as a control. `four-fates-page` is close on Haiku (core 4/4
twice), and its only core failures came from one decision, leaving the page whole. It is
held out, so it is not tuned further.

The reminder sentence in `arms.json` is unchanged. The skill's `SKILL.md` was neither
read nor edited for this work.

## Notes for the coordinator

- `README.md` (outside `eval/`) says the two partly true claims pair a true reason with "a
  stale count". In `stale-number-elsewhere` the stale part is now the spacing ("2 seconds
  apart"), and in `four-fates-page` it was always a duration. "A stale value" would be
  accurate. Its other trap summary still holds: in every stale case, the code that
  contradicts the page sits in a different file from where the moved fact must be
  written.
- `python incubator/harness.py lint` with no argument currently stops at
  `change-drift-sweep`, which has no `SKILL.md` yet. That breaks
  `tests/test_incubator.py::test_every_skill_lints_clean`. It is not caused by this
  change: `lint fold-docs-inline` prints `lint ok`, and the other 12 incubator tests pass.
