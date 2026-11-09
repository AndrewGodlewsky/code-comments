# Hygiene eval iteration 5 (sonnet)

Skill v4 against a one-line reminder and no skill. 2 runs per arm per case; scores are checks passed.

| Metric | Skill v4 | Reminder | No skill |
| --- | --- | --- | --- |
| Pass rate (%) | 97.4 ± 6.7 | 94.4 ± 9.9 | 93.3 ± 9.1 |
| Tokens | 40,714 | 38,247 | 38,333 |
| Seconds | 14.4 ± 2.3 | 12.2 ± 1.6 | 13.2 ± 2.6 |

| Case | Skill v4 | Reminder | No skill |
| --- | --- | --- | --- |
| capture-supported-reason | 4/5, 4/5 | 5/5, 5/5 | 4/5, 5/5 |
| change-contradicts-comment | 6/6, 6/6 | 6/6, 5/6 | 5/6, 6/6 |
| clause-goes-stale | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 |
| comment-only-preserve | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 |
| issue-pointer-beside-reason | 6/6, 5/6 | 5/6, 5/6 | 6/6, 5/6 |
| no-invented-reason | 5/5, 5/5 | 4/5, 4/5 | 4/5, 4/5 |
| no-issue-tag-routine | 5/5, 5/5 | 5/5, 5/5 | 5/5, 5/5 |
| reason-only-in-test | 6/6, 6/6 | 6/6, 4/6 | 5/6, 5/6 |
| rename-stale-refs | 5/5, 5/5 | 5/5, 5/5 | 5/5, 5/5 |
| retry-cap-elsewhere | 5/5, 5/5 | 5/5, 5/5 | 4/5, 5/5 |
| routine-edit-no-noise | 4/4, 4/4 | 4/4, 4/4 | 4/4, 4/4 |

## Notes

- Model: Sonnet subagents, 2 runs per arm per case (22 runs per arm), all new. Sonnet agents were told to read their prompt from a file; Haiku agents got it inline. The prompt text is the same.
- Pass rates (mean of per-run rates): skill 97.4%, reminder 94.4%, no skill 93.3%. Sonnet without the skill is already stronger than Haiku without it, so the skill's margin is smaller.
- issue-pointer-beside-reason barely discriminates on Sonnet: skill 6/6, 5/6; reminder 5/6, 5/6; no skill 6/6, 5/6. Most arms cited #212 unprompted; only no-skill run 2 missed it. The common failure was again rewriting the accurate export docstring.
- Cost of the skill on capture-supported-reason: both skill runs added six comment lines, over the case's limit of four (4/5 each); the reminder runs passed 5/5, and one no-skill run added five lines. On Sonnet the skill makes the model a little wordier when recording a reason.
- Where the skill helped on Sonnet: no-invented-reason (5/5 vs 4/5 in every other run); change-contradicts-comment (reminder run 2 dropped the vendor quota, no-skill run 1 left 'client sends at most 100 requests a minute' in place); reason-only-in-test (skill 6/6 twice, reminder 6/6 and 4/6, no skill 5/6 twice); retry-cap-elsewhere (no-skill run 1 left '14 seconds' and '2, 4 and 8' in place).
- Tokens per run: skill about 40,700, reminder 38,200, no skill 38,300 (about 6% more with the skill).
- Arms: with_skill = skill v4 (the version integrated in #45); reminder = no skill, with one sentence appended to the user's request: "Keep code comments accurate: fix or delete any comment, docstring or doc that your change makes false, and don't add comments that only restate the code."; without_skill = no skill and no reminder.
- The reminder tests the pilot's lesson: one general sentence matched the full skill downstream. Here the question is narrower: does the skill beat one comment-specific sentence on these hygiene cases?
- Grader change before the final grading: grade.py now skips tool caches (.pytest_cache, .mypy_cache, .ruff_cache). One Haiku no-skill run of reason-only-in-test had run pytest, and the README.md that pytest writes into its cache was counted as added comment lines. That run moved from 4/6 to 5/6; nothing else changed.
- Cases that do not discriminate (every arm full marks in every run on both models): clause-goes-stale, comment-only-preserve, no-issue-tag-routine, rename-stale-refs, routine-edit-no-noise.
- Clearest discriminator: no-invented-reason. The skill scored 5/5 in every run on both models; the reminder and no-skill arms scored 4/5 in every run, each time because they did not tell the user that no reason was given for the change. One Haiku reminder run (run-3) wrote no RESPONSE.md at all and fails that check for the same reason.
- Run isolation: some runs wrote scratch files outside their outputs folder (to /tmp or beside the repository), in every arm; one Haiku with_skill run also read an AGENTS.md outside its repository. Grading reads only outputs/, so scores are unaffected, but the runs were not fully sandboxed.
- Not tested: whether Claude loads the skill on its own. Every with_skill prompt tells the model to read SKILL.md first. Testing triggering needs claude plugin eval, which needs a spending cap the user has not yet approved.
