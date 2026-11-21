## Review of feat-02 (junior-v5, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Note 1: stated that both 401 paths return the same status with no rate-limit headers, and that the body is the gateway's existing 401 (Q6).
- Note 2: added that the gateway reaches the primary through one address and that the discovery mechanism is open (Q4).
- Note 4: corrected the contradiction. The gateway does not count fail-open requests itself, but the store may still count one when the deadline fires (Q5).
- Note 5: stated that the customer loses one unit of budget for a forwarded, unchecked request, and why this is accepted for v1 (Q5).
- Note 6 (new): Key Service failure on a cache miss returns 503, forwards nothing and touches no counter; the per-instance 5 min cache is noted (Q1, Q2).
- Note 7 (new): the limit comes from plan config (Standard 100); Enterprise has no limit yet; the Enterprise skip sits after key resolution and before the counter call (Q3, Q8).
- Decisions table: Counter store row notes the single primary address; Headers on allowed requests row explains that Remaining is computed in the same script call and that no reset-time header is sent (Q4, Q7).
- Open items: added Enterprise flag timing and Primary discovery (Q4, Q8).
- Diagram 429 label now names all three headers (Retry-After, X-RateLimit-Limit, X-RateLimit-Remaining 0), and the design choices say a 429 always carries them (Q9).
- Plan config is described as a separate lookup from plan name to number, and its location is added to Open items (Q10).
- An unknown plan name is handled like Enterprise (check skipped, no headers, no counter, warning logged), and the Enterprise open item now covers it (Q11).
- The check script is described as one unit, so the GET, INCR and EXPIRE calls cannot be split (Q12).
- A new minute is explained as a new key with no reset step (Q13).
- The failure table and the step on backend failure now say the gateway's own 502 or 504 also carries the rate-limit headers (Q14).
- Retry-After is explained as 1 to 59 in practice, with the next window starting at zero (Q15).
- Removed the separate Decisions table and the numbered note cross-references (notes 1 to 7, Open items links), and folded the choices into the steps, a failure table and a short design-choices list, so each step stands alone.
- Split the content into what the system does (flow, steps, failures, design choices), a build-and-check section, and open questions at the end.
- Kept the Mermaid sequence diagram and the Lua check script, the Enterprise limit as open, and every fixed requirement.
- Cut the duplicated 'Request flow' explanation and the separate 'Design choices' repetition of the header rule; the header rule now appears once, in Design choices, with the 429 and admitted header behaviour stated in steps 8 and 9.
- Merged the 'Plan has no limit' rule with the 'plan missing from config' rule into step 5 and the failure table, so one rule covers both.
- Replaced the 'Note 1 to 7' cross-references and round-numbered answer references with plain statements in each step.
- Step 3 now says why the gateway returns 503 (it cannot identify the customer, so it cannot enforce auth or the limit).
- Step 5 now gives the reason for skipping rather than returning 503 on a plan missing from config (one typo must not take a plan down; the customer is already authenticated).
- Step 6 now says Redis runs the script as one unit and that the expiry is set on the INCR that creates each key; the script itself is unchanged except for shortened comments.
- Step 7 now says the increment stands if the script ran before the deadline, and why undoing it is not done in v1.
- Step 8 now states that Retry-After is 1 to 59 in practice, with 60 as the formula's upper bound.
- Step 9 now says Remaining comes from the same script call as the count, and that the backend timeout is the existing gateway setting.
- Failure table: split 'Key Service error' into its own row with the cache-miss condition; merged the plan-missing row into the no-limit row; added the note that the budget is not refunded after a backend failure.
- Diagram: label for the no-limit path now names both Enterprise and a plan missing from config; the 429 label now lists all three headers; the admitted label notes the backend response may be any status. Diagram structure is unchanged.
- Terms: added Key Service (returns plan name only), Plan config, Admitted, Rejected and Fail open as defined terms; defined the counter key and check script in one line each; rewrote the terms so none reference other sections.
- Open questions: added two items that were unknowns in the report (Key Service call transport, and whether unknown-key answers are cached). Reworded the existing items in plain words and removed the 'Enterprise limit is open' duplication from the Enterprise flag item.
- Kept the build checks in their own section, separate from how the system runs, as the skill requires.

### Holes
- Q4: The note says the check runs on the primary only. How does the gateway know which Redis node is the primary, and what does it do during a failover? (author: The plan says the script runs on the primary only, but it does not choose how the gateway finds the primary. Known: the gateway connects through one address, and during a failover the call errors or times out, so requests fail open. Not known: which mechanism moves the address (managed endpoint, Sentinel or DNS). Added to Open items.)
- Q10: Where does the plan config live and how does the gateway read it? Is it the same thing as the Key Service's plan name, or a separate lookup from the plan name to a number? (author: The Key Service returns only the plan name (checked earlier). The gateway maps that name to a number through plan config, which is a separate lookup. Where that config lives (a file, an environment variable or a service) is not in the brief or the plan, so it is not known. Added to Open items.)
