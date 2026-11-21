## Review of auth-02 (simplify-only, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Replaced the bullet Summary with a two-paragraph 'What this is' that first describes how config and keys work today, then the new flow.
- Moved the term definitions (store, secret names, snapshot, V1, version endpoint, security on-call) into a dedicated Terms section placed before the steps, and removed the scattered 'Names used below' list.
- Renamed every step's fields to the same four parts: Starts when, What it does, Data lives in, If it goes wrong.
- Gave Part A and Part B plain headings that separate rollout from runtime behavior.
- Merged the two startup tests (4 attempts spaced 2 seconds, then exit non-zero) into one test line.
- Turned the step 2 verification table into one sentence, and merged step 2 bullets that said the same thing about engineers.
- Folded step 10's separate empty-value rejection into the retry rule, and moved the 'logs carry names only' note into the failure line.
- Removed the repeated 'nothing in production has changed' lines and the duplicated explanations of why disable precedes delete and why steps 2 and 3 precede the merge.
- Removed the Summary bullet about the CI guard (covered in step 4) and the rollout-specific wording that repeated step 6 details.
- Shortened the scheduled rotation open question to one sentence with the same four actions.

### Holes
- None.
