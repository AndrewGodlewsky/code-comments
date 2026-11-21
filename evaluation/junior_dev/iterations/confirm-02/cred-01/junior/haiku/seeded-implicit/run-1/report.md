## Review of cred-01 (junior, author haiku, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Replaced the vague 'usual 4xx codes' line with the specific 401 for bad tokens, a 503 when the token check fails, and 4xx for create refusals, with the reason for each.
- Changed 'update last used' from an unconditional write before the response to a write only when last_used_at is empty or over an hour old, sent in the background after the response. The old version wrote on every call and waited for the write, which broke the brief's rules.
- Added a Terms section and a Where state lives table, so each piece of state (session cookie, full token, token row) has a named home, and the plaintext is shown as existing only in the dialog and the user's own store.
- Added the api_tokens column list, with token_hash as the only stored form of the secret.
- Redrew the Mermaid sequenceDiagram as four flows: create (with the name, limit and lost-response branches), list, API call (bad token, database failure, valid token and the last-used write), and revoke (ownership check, immediate effect).
- Added the revoke ownership rule (404 for others' or missing tokens, so existence is not revealed) and the rule that revoke is immediate because validity is never cached.
- Added the rules that apply everywhere: name rules, the 10-token limit counting active tokens only, 90-day non-renewable expiry, the same 401 body for every token failure, and no plaintext in the database, logs or analytics.
- Added a failure table covering the limit, invalid names, lost create response, database failures, bad tokens, slow last-used writes and revoke failures.
- Added Open questions for the unset status codes for the limit and duplicate name, orphaned rows from lost responses and the lack of an expiry cleanup job.
- Terms: added API client (the Client in Flow 3) and stated that the settings endpoints accept only the session cookie, never an API token (Q1, Q9).
- Flow 1 diagram: added a lock on the user's row before the count and name check, so two concurrent creates cannot both pass the limit or the name check (Q10).
- Flow 1 diagram: added a note that a lost create response leaves the row in place and counted toward the limit (brief requirement).
- Notes: added that the create lock lasts one create, that the full token is never kept on the page, and that a list refresh never shows it (Q14, Q10).
- Notes: added that a CI script retries 503 after a wait and treats 401 as final (Q12).
- Notes: added that a token has the same full access as its user, since the brief sets no scopes (Q13).
- Notes: added what happens when the session cookie is missing or expired on create, list and revoke (Q15).
- Rules: added that a name can be reused after the old token is revoked or expired (Q11).
- Failure table: the 503 row now names its generic body and retry hint (Q12).
- Open questions: added full access without scopes, and the unspecified name character and case rules (Q11, Q13).
- Flow 3 diagram: a missing, malformed or non-pat_ Bearer header now gets 401 before any hash or database read (Q17).
- Notes on the flow: added which credential each route type reads and what happens when a request carries both (Q16).
- Notes on the flow: the create lock is now defined as a row lock on the user's account row, held until commit, and a second create waits rather than fails. The token is returned only after commit (Q18, Q20).
- Notes and failure table: an insert failure or a unique token_hash clash rolls back, shows nothing, and the user retries. A lost commit reply is covered by the existing lost-response case (Q20).
- Notes on the flow: the last-used write is one conditional update, runs on the server's own connection, and a restart before it runs loses that write until the next call (Q19).
- Rules and failure table: the failed-token rule now includes malformed tokens, and the header check has its own failure row (Q17).
- Kept every requirement, limit, number and rule from the brief and the first version: the name rules, pat_ plus 32 CSPRNG characters, shown once with a Copy button, SHA-256 only, 90-day expiry with no renewal, the 10-token limit, list fields with Never, the one-hour last-used staleness, immediate revoke with 401, the generic 401 body, the 404 for another user's token, and the four Mermaid flows with their failure branches.
- Kept all five open questions unchanged, and the 4xx, 503 and 404 codes from the earlier answers.
- Restructured to the skill's order: a summary of about three sentences, then terms, then the state table and diagram, then rules and flow notes, then the failure table, then open questions.
- Added one-line definitions for the terms a newcomer to this stack would not know: unique index, commit and row lock. Kept the existing definitions and made the Postgres and single-server context explicit in the summary.
- Merged the scattered rules into one Rules section (name, limit, expiry, ownership, generic 401, logs), so each rule is stated once instead of in the rules, the notes and the failure table.
- Cut repeated restatements: the no-cache rule, the immediate revoke effect, the new-token advice and the lost-reply case now each appear in one place. The failure table holds outcomes, and the notes hold only mechanism.
- Grouped the Flow 3 notes into ordered parts (credential split, header check, lookup, last-used write, client retries) and kept the reason in a short clause where it applies.
- Kept the diagram as it was, with one label changed to name the row lock. No behaviour was added or changed, and no new mechanism was introduced.

### Holes
- None.
