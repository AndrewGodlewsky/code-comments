# Hygiene eval iteration 5 (haiku)

Skill v4 against a one-line reminder and no skill. 3 runs per arm per case; scores are checks passed.

| Metric | Skill v4 | Reminder | No skill |
| --- | --- | --- | --- |
| Pass rate (%) | 97.5 ± 8.5 | 90.6 ± 15.8 | 91.1 ± 17.4 |
| Tokens | 43,193 | 40,820 | 40,521 |
| Seconds | 22.8 ± 3.8 | 17.5 ± 4.7 | 20.4 ± 23.0 |

| Case | Skill v4 | Reminder | No skill |
| --- | --- | --- | --- |
| capture-supported-reason | 5/5, 5/5, 5/5 | 5/5, 5/5, 5/5 | 5/5, 5/5, 5/5 |
| change-contradicts-comment | 6/6, 6/6, 6/6 | 5/6, 6/6, 5/6 | 6/6, 6/6, 6/6 |
| clause-goes-stale | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 |
| comment-only-preserve | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 |
| issue-pointer-beside-reason | 5/6, 6/6, 4/6 | 3/6, 3/6, 3/6 | 3/6, 3/6, 2/6 |
| no-invented-reason | 5/5, 5/5, 5/5 | 4/5, 4/5, 4/5 | 4/5, 4/5, 4/5 |
| no-issue-tag-routine | 5/5, 5/5, 5/5 | 5/5, 5/5, 5/5 | 5/5, 5/5, 5/5 |
| reason-only-in-test | 4/6, 6/6, 6/6 | 5/6, 4/6, 5/6 | 4/6, 5/6, 5/6 |
| rename-stale-refs | 5/5, 5/5, 5/5 | 5/5, 5/5, 5/5 | 5/5, 5/5, 5/5 |
| retry-cap-elsewhere | 5/5, 5/5, 5/5 | 5/5, 5/5, 5/5 | 5/5, 5/5, 5/5 |
| routine-edit-no-noise | 4/4, 4/4, 4/4 | 4/4, 4/4, 4/4 | 4/4, 4/4, 4/4 |

## Notes

- Model: Haiku subagents, 3 runs per arm per case (33 runs per arm). with_skill and without_skill runs 1-2 are the iteration-4 runs, reused unchanged (same prompt, same skill text); run 3 of those arms and all reminder runs are new. New with_skill runs read the skill from a snapshot path rather than the plugin path; the text is identical.
- Pass rates (mean of per-run rates): skill 97.5%, reminder 90.6%, no skill 91.1%. The reminder did not help Haiku on these cases.
- issue-pointer-beside-reason: skill 5/6, 6/6, 4/6; reminder 3/6 three times; no skill 3/6, 3/6, 2/6. Only skill runs cited #212 beside the vendor rule (3/3). Reminder runs wrote a docstring about two decimal places but never stated the vendor reason or the issue; no-skill runs stated the reason but never cited #212. Every arm sometimes rewrote the accurate docstring 'Return value formatted for the export file.' (skill runs 1 and 3 too).
- change-contradicts-comment: the skill and no-skill arms passed 6/6 every time; reminder runs 1 and 3 deleted the outside fact that Geoway's free tier allows 100 requests a minute (5/6). The reminder's 'fix or delete any comment your change makes false' may have encouraged deleting a comment that was still true.
- reason-only-in-test is mixed: skill 4/6, 6/6, 6/6; reminder 5/6, 4/6, 5/6; no skill 4/6, 5/6, 5/6.
- Tokens per run: skill about 43,200, reminder 40,800, no skill 40,500 (the skill costs about 6% more).
- Arms: with_skill = skill v4 (the version integrated in #45); reminder = no skill, with one sentence appended to the user's request: "Keep code comments accurate: fix or delete any comment, docstring or doc that your change makes false, and don't add comments that only restate the code."; without_skill = no skill and no reminder.
- The reminder tests the pilot's lesson: one general sentence matched the full skill downstream. Here the question is narrower: does the skill beat one comment-specific sentence on these hygiene cases?
- Grader change before the final grading: grade.py now skips tool caches (.pytest_cache, .mypy_cache, .ruff_cache). One Haiku no-skill run of reason-only-in-test had run pytest, and the README.md that pytest writes into its cache was counted as added comment lines. That run moved from 4/6 to 5/6; nothing else changed.
- Cases that do not discriminate (every arm full marks in every run on both models): clause-goes-stale, comment-only-preserve, no-issue-tag-routine, rename-stale-refs, routine-edit-no-noise.
- Clearest discriminator: no-invented-reason. The skill scored 5/5 in every run on both models; the reminder and no-skill arms scored 4/5 in every run, each time because they did not tell the user that no reason was given for the change. One Haiku reminder run (run-3) wrote no RESPONSE.md at all and fails that check for the same reason.
- Run isolation: some runs wrote scratch files outside their outputs folder (to /tmp or beside the repository), in every arm; one Haiku with_skill run also read an AGENTS.md outside its repository. Grading reads only outputs/, so scores are unaffected, but the runs were not fully sandboxed.
- Not tested: whether Claude loads the skill on its own. Every with_skill prompt tells the model to read SKILL.md first. Testing triggering needs claude plugin eval, which needs a spending cap the user has not yet approved.
