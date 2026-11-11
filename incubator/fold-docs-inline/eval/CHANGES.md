# fold-docs-inline: skill changes

Each version lists what changed in `skill/fold-docs-inline/SKILL.md` and why. The
evidence behind each change is in the iteration-1 analysis (ANALYSIS.md, "Iteration 1").
No change was informed by the held-out cases. Their files under `cases/`, `references/`
and `hidden/` were not opened. GATE.md and CASES.md, which summarise them, were read
while orienting; no change below draws on those summaries.

## v2 (after iteration 1)

Three changes in one revision. Each targets a behaviour seen in `with_skill` training
runs, and each is written about the behaviour, not a fixture. They act on different
parts of the skill (the Moved fate, the Dropped fate, the fate list), so their effects
can be read apart in the next iteration. After the change,
`python incubator/harness.py lint fold-docs-inline` printed `lint ok` and
`python incubator/harness.py self-test fold-docs-inline` printed `self-test ok`. The file
grew from 88 to 97 lines (`wc -l`).

1. **A created docstring holds only the moved fact.** A new bullet under Moved:
   "Prefer a comment, or add to a docstring the symbol already has. A docstring you
   create holds only the moved fact. Give it no opening line saying what the code does,
   because that line restates the code."

   Why: v1 failed to prevent this on Haiku.
   - In 4 of 15 Haiku `with_skill` runs, a moved fact went to a symbol with no
     docstring. The run created one and opened it with a summary of what the code does.
   - One case is graded: `ops-notes-in-file-sections` run 3 (restraint 05). Its fate
     list marks the return-value claim Dropped, then its new docstring's first line
     states that claim.
   - The other three are ungraded: `spec-claim-code-disagrees` runs 1 to 3, each with
     the same restating first line on a new docstring.
   - The reminder, which asks for "one comment", created no docstring in 25 runs.
     Sonnet `with_skill` used comments in all 10 runs.
   - The bullet is a preference, not a ban. A caller contract can still go in a new
     docstring, which the shipped skill's "Put caller contracts in interface docs"
     expects when both skills are installed.

2. **A description is not a rule.** Added to Dropped: "A claim that only describes what
   the code is or does stays dropped, even if it could be read as a rule for later
   edits. Move it as a constraint only when the page itself states the rule or gives a
   reason for it; never supply the rule yourself."

   Why: v1 failed to prevent this, and its text left the case open.
   - In `restatement-only-page` Haiku run 1, a sentence that described the code was
     moved as a constraint: "The page states this as a constraint on future edits,
     which the code does not show." The comment also widened the claim into a rule the
     page does not state. The run failed core 01, and reply 06 by override.
   - Run 3 called the same sentence "the closest call" before dropping it.
   - v1's Moved fate lists "constraint" but does not say whether a description may be
     read as one.
   - The new sentence follows the shipped skill's "Never invent". It leaves alone the
     claims that state a rule ("has to stay", "do not raise") and the claims that give
     a reason ("because ..."), which v1 moved correctly in every run.

3. **One fate-list line per sentence, split only where fates differ.** The fate list's
   "One line per claim" became: "One line per sentence, bullet or table row, in page
   order ... Splitting is for checking: where parts of one sentence have different
   fates, give each part its own line, and keep parts that share a fate on one line.
   Headings are not claims."

   Why: v1's wording caused harm, as noise in the deliverable.
   - `with_skill` replies were the longest of all four arms in every case on both
     models. Haiku averaged 416 words and 13.0 list items, against the reminder's 264
     words and 6.7 items. Sonnet averaged 326 words and 9.9 items, against 223 and 5.8.
   - Some of the length is the per-claim list the skill asks for. Some is splitting
     that tells the user nothing. Haiku `restatement-only-page` run 2 gave nine lines to
     five sentences that were all Dropped. Haiku `slim-page-one-home` run 1 listed both
     headings as "kept" claims and gave a sentence's trailing clause its own line, with
     the same fate as the line before.
   - v1 asks for both: step 1 splits "wherever parts could differ in truth", and the
     fate list asks for one line per claim.
   - Step 1 is unchanged, so each part is still checked on its own. A sentence whose
     parts have different fates, such as a true reason beside a stale value, still
     gets a line per part.
   - Risk to watch: the reply checks look for each claim by anchor. A merged line must
     still name each claim.

Not changed:
- **The Kept list.** It made the one clear Haiku difference from the reminder:
  operational notes stayed out of code in 3/3 runs, against 0/3.
- **The fate of a page detail the code neither states nor contradicts.** Three Haiku
  runs gave the same unit three different fates. Nothing grades this, and the right
  fate is a question for the user.
