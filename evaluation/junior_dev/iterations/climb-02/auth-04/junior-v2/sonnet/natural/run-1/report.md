## Review of auth-04 (junior-v2, author sonnet, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Endpoints: GET /auth/google/start now says where next comes from and that an invalid value is dropped.
- Endpoints: confirm page now says how it is bound to the attempt (g_pending cookie, SameSite=Lax) and unlink needs a session and CSRF protection.
- Flowchart CRE node now says the new user gets Google's lowercased email; Notes reworded so 'never writes Google's email' no longer contradicts it.
- Failure handling: Redis unavailable now also covers the confirm page, with the pending record left to expire.
- Flowchart: unlink outcomes now say where the user lands (back to settings with a message).
- Added a note on signing in with Google while already holding a valid sid session.
- Added an Open questions section about CSRF on the sessionless confirm form.
- Merged the separate 'ID token invalid' failure bullet into the code-exchange failure bullet, since both are handled the same way.
- Merged the 'check order' note and the 'both entries share one callback' note into a single note.
- Merged the 'account takeover guard' note's content into a shorter 'No takeover by email' note.
- Cut the duplicated start_session description in the endpoints and notes, and trimmed the Redis/PostgreSQL background to what the main flow needs.
- Shortened the 'We keep no tokens' text and the endpoint descriptions; dropped repeated wording about the confirm page cookie.
- Changed the HG refusal message at RF2 from 'linked to a different Google account' to a neutral 'cannot be linked' message, because the node also covers the no-password case.
- Kept the flowchart, state tables and the single open question at the end unchanged in substance.

### Holes
- None.
