## Review of auth-03 (junior-v5, author sonnet, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Added a step in flow A showing the API server generating the raw token (32 CSPRNG bytes, base64url) before the transaction, because the junior could not tell where it came from.
- Showed the job payloads in the diagram ({email, raw} for reset, {email} for password changed) and the worker building APP_URL/reset?token=raw.
- Said in the diagram and notes that the token travels in a hidden form field and back in the POST body.
- Added notes on the raw token, the link and payloads, and the token in the form.
- Stated the generic reply status (200) and the client behaviour on 200 and 503.
- Made the enqueue-failure row say plainly that the earlier link was already killed, so the user has no working link until they request again.
- Added an Open questions section for the breach list location, the session identification mechanism and APP_URL.
- Added an opening paragraph: what this is, the main flow end to end, why only a hash is stored, and how mail and sessions work today (moved the existing-system description out of the brief into the document).
- Added a Terms section defining raw token, token hash, consumed, generic reply [G], expired page [E] and breach list, answering the junior's questions about the raw token and the breach list.
- Kept the diagram unchanged except: dropped the duplicated generic-reply text in flow A (now defined in Terms), and added a legend line for [E] and [G].
- Merged the raw token, link and job payload, token-in-form, and rejected-password notes into per-flow notes (Request, Job, Link click, Submit), so each step states where the token comes from, how the worker builds APP_URL/reset?token=raw, and that the token is sent in a hidden field in the POST body with no cookie.
- Merged the 'Generic reply', 'Rate limit and one live link' and 'Session logout' notes into the flows; moved the 503 'try again' client behavior into the failure table.
- Cut the repeated explanations of the unknown and over-limit paths skipping the enqueue and the repeated statement that the token is never stored raw.
- Left out the details the plan does not need yet: queue transport details, how the password-changed email template is chosen, and the client UI beyond the message.
- Kept the Open issue and Open questions (breach list location, session identification, APP_URL) at the end; no new mechanisms were added.

### Holes
- Q5: What is the breach list and where does it live? Is it a local file, a database table, or an external service? (author: I do not know where the breach list lives or how it is queried. Nothing I have says whether it is a local file, a table or an external service. The design only needs a yes/no lookup, and treats an unavailable lookup as a rejection. Added to Open questions.)
- Q6: What does the existing session mechanism look like? How does the API identify a request's session, and what is in the `sessions` table that makes deleting rows log the user out? (author: I have not seen the session code. The brief says sessions has one row per logged-in device and the API checks it on every request, so deleting the user's rows makes the next request fail the check. How the request carries the session id (cookie or header) is unknown to me. Added to Open questions.)
