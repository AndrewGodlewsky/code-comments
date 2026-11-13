## Review of auth-04 (self-review, author haiku, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a short "Terms used below" section defining OIDC, ID token, sub, PKCE, state, nonce, GETDEL, TTL, sid cookie and the flow cookie, for an engineer who has not seen the project.
- Replaced the "Notes on the diagram" list with a "Reading the diagram" section. It explains the two entry points, the callback order, failed exchanges, lookup order, the confirmation loop, the lock, the invariant and the cookie setting, in plainer sentences.
- Corrected the failure row for two callbacks creating the same user. The draft said the second callback "takes the confirm path", which the diagram does not do. The second callback now hits a unique violation, rolls back, rechecks by sub, and signs in to the user the first callback created. The diagram label now names both unique constraints.
- Clarified that a flow-cookie mismatch happens after the attempt is already deleted, so the failure row says so.
- Added a missing case: a confirm POST without the flow cookie gets the same error as an expired record. The diagram itself is unchanged.
- Explained in the diagram notes that the confirm record is found through the flow cookie, and that the 10-minute window starts at the callback.
- Added a note that a password reset can later set a password for a Google-only user, which keeps the invariant true.
- Stated that the Redis eviction decision means keeping `oidc:*` keys out of any eviction policy, or using a separate instance.
- Kept the diagram, the state table, the schema change, the failure table and the four decisions in their original form, apart from the fixes listed above. The Mermaid syntax was checked by reading it and nothing was rendered.
- Added a plain-language opening section that says what is being added, which data is read from Google, and that the session is the same as password login.
- Expanded the terms list: added origin, next, email_verified, attempt, confirm record, lockout, and clarified sid and flow cookie. Each term is defined before first use.
- Reworded diagram labels to say what each node does in plain words (for example, 'no password asked, emails not compared' on the Settings link node). The diagram logic is unchanged.
- Removed the unused success-path edge from the link insert that had no matching state, and made the unique-violation edge on Settings link point to the refuse-as-other-user outcome.
- Clarified the new-user race: a unique violation on the email (not only the sub) now falls through to the email-match path, and the failures table has a row for it.
- Added a note on successful confirmation: failed_logins is reset to 0 as password login does, and a racing second link loses at the insert.
- Split the reading notes into short sections (token checks, new Google user, email match, lock during confirmation, linking from Settings, unlinking) so each outcome can be found and read alone.
- Kept the state table, schema change, failures table and decisions list as they were, with the race row added and no change to their meaning.
- Added a short Overview section before the detailed sections, summarising the whole flow in plain words.
- Expanded the terms list: added Google/OIDC, authorization code, token exchange, callback, intent, transaction, unique violation, bcrypt, and explained start_session and the cross-site redirect.
- Rewrote the invariant as two numbered rules, and reworded its reasoning so each rule's justification is explicit.
- Split the long 'Reading the diagram' explanations into labelled, shorter paragraphs; reworded the cookie-settings note to explain why SameSite=Strict fails on the Google redirect.
- Clarified in the email-match paragraph that the form finds the confirm record through the flow cookie.
- Diagram, failure table, state table, schema, and decisions list are unchanged in substance; only the prose around them was clarified. No requirement or decision was altered.

### Holes
- None.
