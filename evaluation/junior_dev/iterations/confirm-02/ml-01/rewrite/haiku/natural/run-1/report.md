## Review of ml-01 (rewrite, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a three-sentence summary that says how the current system works, how the main flow goes, and why it is shaped that way. Added a short text diagram of the request and shadow paths.
- Added a terms and parts section. It defines each named part once, including the terms a newcomer would not know: gateway, materialization, warehouse, feature bundle, compare-and-set, salt, bucket, circuit breaker.
- Merged the 'Scope and fixed decisions' list and the 'Components' list. The fixed rules now appear once, in a short list of four rules that hold everywhere. The component descriptions now sit in the terms section.
- Removed the duplicate statement of the gates. The numbers now appear only in the promotion gate step, where they apply.
- Corrected a wrong cross-reference. Step 5 said the cohort check was in step 6, which is materialization. It now points to the shadow cohort step (step 12).
- Kept each step's trigger, data, state and failure, so no separate failure table was needed. Kept every number and rule from the brief and the first draft: 150 ms, 30 ms, 90 ms inference deadline, 6 hours, 1 minute rollback, 10% shadow, 7 days, 0.5%, 80 ms, ML lead approval, the 15 s poll, the 60 s fleet check, the 2-hour lag alert and the 200 ms shadow timeout.
- Replaced the vague 'hash' in the cohort step with a concrete rule: SHA-256 or another stable hash, never a language's built-in hash.
- Kept all six open questions. Added a seventh flagging a conflict in the first draft: 'two consecutive failures put users into fallback' does not match the 6-hour staleness rule. The conflict is stated, not resolved, because it changes behaviour.
- Replaced most 'step N' references with the name of the step or rule, and kept the step numbers only where a reader needs to find a step. Did not change any decided behaviour except the cross-reference fix above. Did not add a rollout section, because the first draft had none.

### Holes
- None.
