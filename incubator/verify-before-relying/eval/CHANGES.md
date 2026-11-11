# verify-before-relying: skill changes

Each version lists what changed in `skill/verify-before-relying/SKILL.md` and why. The
evidence behind each change is in [ANALYSIS.md](ANALYSIS.md). No change was informed by the
held-out cases.

## v2 (after iteration 1)

Only the reply wording changed. No rule about what to check, build or edit was changed,
because no `with_skill` run failed a graded check. `lint ok` and `self-test ok` after the
change. The body grew from 91 to 94 lines.

1. **Point to a claim by file and name, not `file:line`.** In "When the request carries the
   claim" and in the Report, the claim is now located by the file and the function, constant
   or heading it sits in. v1 asked for `file:line`.
   - Why: the rule caused harm. Only `with_skill` replies cited line numbers: 112 citations in
     25 runs, against none in the other 75 runs. Five pointed past the end of the file, in 3
     runs: Haiku `request-quotes-stale-docstring` run-3, Sonnet `request-quotes-true-docstring`
     run-2, and Sonnet `stale-cents-comment` run-2. In the last of these, all five citations
     were wrong. The bare and reminder replies passed the same reply checks without line
     numbers. The research cites no source for line numbers: S1's sentence asks only to "point
     out each inconsistency".
   - The new wording states the target and never mentions line numbers, so it does not
     prompt them.
2. **"Premise" means a claim the request itself states.** The Report bullet now says that a
   false claim met in a comment, docstring or doc is reported as that text's claim. "A false
   premise from the request goes first" stays.
   - Why: a failure mode in `with_skill` runs that a general rule fixes. 4 of 5 `with_skill`
     replies in `stale-cents-comment` called a comment's claim "the premise". The request made
     no claim about the code, so the reply wrongly tells the user their request was wrong. One
     `true-cents-comment` reply did the same. No other arm did either. In the two request
     cases, `with_skill` used the word correctly in 10 of 10 runs.

What to expect in iteration 2: fewer false line pointers and no misplaced "premise", with no
graded check worse than iteration 1. If a graded check drops, revert v2.

Not changed, with the reason:
- **The mixed-sentence rule (*judgement*).** It kept a false description in the synced doc in
  5 of 5 runs. No graded check failed, and whether to add a status sentence instead is a
  policy choice for the user.
- **Reply length.** `with_skill` replies are longer than the bare model's but shorter than the
  reminder's. That alone does not justify cutting a rule.

Docs outside the skill folder that are now out of date, for the coordinator:
- `incubator/verify-before-relying/README.md` still says the body has 91 lines.
- It still says the skill reports each false claim "with file:line" (in "What it adds over
  the shipped skill", item 4, and in "How it works", rule 5).
- `research.md`, "What this means for the skill's rules", items 8 and 10, says the same.
