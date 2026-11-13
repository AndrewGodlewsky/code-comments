# constraint-sweep: skill changes

Each version lists what changed in `skill/constraint-sweep/SKILL.md` and why. The
evidence behind each change is in the iteration-1 analysis (ANALYSIS.md, "Iteration 1").
No change was informed by the held-out cases, which were neither run nor opened.

## v2 (after iteration 1)

Two changes to the rules and one to the Report, in one revision. Each targets a
behaviour seen in `with_skill` runs, and each is written about the behaviour, not a
fixture. They act on different training cases, so their effects can be read apart in
the next iteration. `python incubator/harness.py lint constraint-sweep` printed
`lint ok` after the change, and `self-test ok` still holds. The body grew from 94 to 103
lines, as the linter counts them.

1. **Fix text your change made false. Do not hand the fix on.** Two places changed:
   - **The intro.** It now says the skill asks for no *new* comments. When a change makes
     an existing comment false in any file, `code-comments` governs only the wording, and
     the fix is part of the change, not a follow-up for the user.
   - **The stale-constraint rule.** It now says: if your change makes the stale text
     false, for example because it describes behaviour your change removes, correct or
     delete it in the same change, and reporting it does not replace the fix. Stale text
     the change does not make false is still left as it is and reported.

   Why: the v1 wording caused harm.
   - In `stale-constraint-elsewhere`, every `with_skill` run (Haiku 3/3, Sonnet 2/2) left
     the stale comment in place, though its own reply called the comment "now false",
     "now inaccurate", "now wrong" or "no longer true".
   - Three replies gave the reason: the wording fix "belongs to the code-comments skill".
     That skill is not loaded in this arm, so the deferral meant no fix at all.
   - Every run of the other three arms corrected the comment in place (15/15).
   - The shipped skill requires the fix ("fix or delete every comment your change made
     false ... callers' comments").
   - No check scores this. Check 05 accepts a reply that calls the comment stale.
   - v1's own Restraint bullet already allowed the edit ("to fix text your change made
     false"). The change removes the contradiction rather than adding a new permission.
2. **Moving the work into a dependent is not keeping the property where it is
   produced.** Option 1 of "A live constraint binds" now says three things:
   - Moving the work that provides the property out of the symbol and into a dependent
     is not that option. It edits a file the request did not name, and for a request
     about cost that dependent still pays it.
   - Look first for another way, such as a cheaper one, for the symbol itself to provide
     the property.
   - Move the work only when there is none, and say why in the reply.

   Why: a failure mode in `with_skill` runs that a general rule fixes.
   - In `sort-relied-on-elsewhere`, all three Haiku `with_skill` runs moved the work into
     the one consumer that needs the property. That fails checks 04 and 07 in each run,
     which is all six of Haiku `with_skill`'s failed checks.
   - Run 1's reply named the producer-side alternative and did not try it.
   - Both Sonnet `with_skill` runs kept the property at the producer and passed 7/7.
   - Haiku reminder (3/3) and bare (2/3) runs did the same as Haiku `with_skill`, so v1
     did not cause the move; it failed to prevent it. Nothing in v1 said relocation is
     not option 1.
3. **The Report asks whether each stale constraint was corrected.** This keeps the reply
   in line with change 1.

What to expect in iteration 2:
- `with_skill` corrects a comment its change made false, and still only reports stale
  text it did not make false.
- On Haiku, `with_skill` keeps the property inside the changed symbol more often.
- No graded check is worse than in iteration 1.

What would count against v2, and should lead to reverting the change concerned:
- edits to comments that state nothing;
- edits to stale text the change did not make false;
- keeping a cost the user asked to remove;
- refusing or asking instead of acting.

Not changed, with the reason:
- **Scope widening in one run.** Sonnet `positional-columns-in-sql-pointer` `with_skill`
  run 2 also extended the warehouse table and made the next load depend on a manual
  migration. That is one run in ten, no check failed, and v1's Restraint bullet already
  forbids the edit. A rule for one run would be tuning to noise.
- **The unrequested documentation edit.** One Sonnet `with_skill` run edited a doc to
  describe the new column (check 07). The other arms did this as often or more (bare
  4/10), and the Restraint bullet already covers it.
- **Keep the form the user named.** It held in 10/10 `with_skill` positional runs,
  against 0/10 bare. It is working, so it was left alone.
