## Review of auth-02 (rewrite-v7, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered to the required layout: summary (with how things work today), terms, then steps, then open question; moved the two ordering constraints into the summary and the assumptions next to the terms.
- Added a Terms section defining secret store, KMS key, version id, APP_ENV, snapshot, service identity, security on-call and rotation (no junior questions were supplied, so these target names a newcomer would not know).
- Added a short 'Rules that apply to every step' list (memory-only values, no failed customer request, 4 replicas/identity, engineers cannot read prod) and removed their repeated restatements from individual steps.
- Merged the separate 'Code changes' and 'Retry behaviour' sub-bullets into single 'what it does' lines; merged old Part A steps' repeated 'snapshot never mixed' and logging statements.
- Cut the repeated explanation of why old keys must stay valid from steps 9 and 11 (stated once in the summary and step 13); replaced the cross-reference 'until step 14' in step 9 with step 13, where rollback is actually blocked (fixes an inconsistency).
- Replaced the verbose 'Why now' and note paragraphs with shorter clauses; shortened step 14 and 15 wording while keeping every gate item, the 24-hour quiet period, second person and cleanup items.
- Kept all stated facts: secret names, access policy table, 3 retries 2s apart, exit non-zero (code 70 example), 5-minute refresh, last-good-value plus warning, 15-minute alert, CI check with prefixes, dev-offline guard, verification of the _check secret, and the unchosen rotation cadence.
- Removed 'Rollback property' as its own bullet and 'Safeguard' duplication; failure handling stays inside each step with its own If-it-fails line instead of a separate table.

### Holes
- None.
