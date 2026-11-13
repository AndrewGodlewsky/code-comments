## Review of feat-02 (junior-v3, author haiku, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Removed the numbered requirement references (1, 3, 4, 5, 6, 7) and stated each constraint in place, so the file no longer depends on the brief.
- Removed the separate limitFor(plan) step from the diagram and moved the plan-to-limit rule into step 3 of the steps list.
- Added a short summary and a terms section (customer, plan, window, counter, counted request) before the diagram.
- Added numbered steps and a failure-handling table, so each failure case is in one place.
- Defined the handling of an unrecognised plan value (treated as Standard) and stated that 429 responses carry no X-RateLimit headers.
- Explained the 120 s expiry, the clock source for windowStart and Retry-After, and the budget effect of backend failures.
- Merged the trade-offs and the store-durability note into one short list of accepted trade-offs.
- Collected the unresolved items (Key Service failure, backend timeout, 429 body, Enterprise limit, metric owner, Redis topology) under one open questions heading.
- Cut the 'Main flow' paragraph under 'What this is', because it repeated the steps. The summary now states the main flow in two sentences.
- Added 'Fail open' and 'OPEN' to the terms, since the steps and diagram use both without defining them.
- Merged the old steps 1 and 2 (resolve the key, and return 401 for a missing or unknown key) into one step. The step list is now 6 steps, down from 7.
- Clarified in step 6 that rate-limit headers appear only when the check ran and allowed the request. The old forward step contradicted the fail-open and OPEN branches, which send no headers.
- Moved the Retry-After formula into the 429 step, and merged the two clock sentences into one paragraph.
- Shortened the script explanation to the points a newcomer needs: a missing key reads as 0, and the 120 s expiry only covers clock skew.
- Trimmed the failure table, and changed the Key Service row to point to the open questions instead of repeating them.
- Grouped the fixed-window, Redis failover and plan-cache trade-offs into one short list under the failure section.
- Replaced the 'see open questions' references with plain wording where possible. Kept the Mermaid diagram unchanged, because its branches already match the steps.

### Holes
- Q8: What does the Key Service return when it is down or slow, and how does that interact with the 5 minute gateway cache? (author: The brief and the design do not say what happens when the Key Service errors or is slow. The gateway already has a 5 minute in-memory cache for key answers. How a Key Service failure is handled today is not in the material I have. This design does not change it. It needs to be confirmed, and it is listed under open questions.)
