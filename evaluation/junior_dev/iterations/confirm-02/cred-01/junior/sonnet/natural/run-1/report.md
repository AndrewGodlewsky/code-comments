## Review of cred-01 (junior, author sonnet, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Added a sentence under the table: name uniqueness is enforced only by the check in the locked create transaction, and revoked rows keep their name (Q1).
- Flow 3 diagram step now reads 'Handle request as the user_id on the matched row', and a Using a token note says tokens have full user API access except the token-management endpoints, with no scopes (Q3).
- Notes under Creating now say who takes the row lock and that a second create waits at it (Q4).
- Fixed a mistake in the revoke flow: removed 'expired' from the 0-rows/404 case in the diagram and the failure table, and added a note that a direct DELETE on an expired id returns 204 (Q6).
- Added a Using a token note that only status and body are identical and timing is not equalised, with the reason (Q8).
- Added an Open questions section for the session 401 behaviour, the lock wait timeout, the browser create timeout and waiting display, and the redaction mechanism (Q2, Q4, Q5, Q7).
- Added a two-to-three sentence summary at the top, including how login and settings endpoints work today, why there is no cache, and the four flows.
- Added a Terms section: personal API token, plaintext, CSPRNG, active token, orphan, SELECT FOR UPDATE, generic 401, session-cookie endpoints. Moved the definition of active token here from under the schema.
- Merged the name-uniqueness sentence and the partial-index reasoning into one paragraph under the schema, so the reasoning is no longer repeated in the Creating notes.
- Added to the state table the brief's rule that nobody, including support and engineering, can show the token again, and that a lost token means creating a new one.
- Merged the two Listing bullets into one. Merged the 'all failures return the same status' and 'cannot be told apart' bullets in Using a token. Removed the repeated 'revoke takes effect on the next request' phrasing from the state table, since the summary says it.
- Added a line that the notes only add what the diagram cannot show. Kept the diagram unchanged.
- Moved the 'no database write on every API request' requirement into the last-used note, and the 'session cookie only' rule into the Using a token bullet about access.
- Renamed Failure summary to 'What happens when things fail' and added rows for no valid session and list DB error, which the diagram already showed.
- Checked the first version line by line. All requirements, limits, numbers (1-40, 36 length, 10 tokens, 90 days, 1 hour, 190 bits), the schema, and the Open questions are kept.

### Holes
- Q2: What does the "existing session check" do and what does it return? The document says a 401 uses "existing login behaviour". What does the browser see or do on that 401? (author: The existing session check and the browser's handling of its 401 belong to the existing login code, which this document does not describe. Added to Open questions.)
- Q5: In the lost-response case, how does the browser decide it timed out? Is there a fixed timeout, and what does the user see in the dialog while waiting? (author: The brief and the document do not fix a timeout value or the waiting display. The create button is disabled while the request is in flight. The timeout value and waiting display are listed in Open questions.)
- Q7: The create flow says the response is 201 with the plaintext, and the server redacts the create response body from logs and analytics. What does the redaction, and where in the request path does it happen? Is it per-endpoint config or a general filter? (author: The requirement is fixed: the create response body, the Authorization header and analytics payloads must be excluded or scrubbed, and only the token id is logged. Whether that is a general filter or per-endpoint config depends on the existing logging stack, which I have not seen. Added to Open questions.)
