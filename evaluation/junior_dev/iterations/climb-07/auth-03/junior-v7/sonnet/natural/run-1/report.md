## Review of auth-03 (junior-v7, author sonnet, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Request flow: API now builds the full link from a configured base URL and enqueues {to, link}; worker sends the job as given (Q4).
- Link-click flow and F1: expired page includes a link to the /forgot-password form (Q3).
- F5: specified that the same form is shown again with a generic error, and the user retypes the password (Q2).
- Added a note defining the breached-password check and what 'unavailable' means (Q1).
- Added a note on who builds the email link (Q4).
- Added an Open questions section: where the breached-password list lives is not specified (Q1).
- Added a short opening summary that first describes today's system (API, Postgres users/sessions, email queue and worker) and then the new flow and why it is shaped this way.
- Added a Terms section (raw token, token hash, burned, live link, queue/worker, breached list, FOR UPDATE) in answer to the breached-list and worker questions.
- Added a Rules section that puts every brief requirement in one place: generic message, 3 per rolling hour, 30 minutes and once, new link burns old, check on load and submit, 12 characters plus breach list, logout on all devices, changed email, redirect without auto-login.
- Removed the F1-F8 codes. Inline outcomes in the flows now say what happens (expired page, form again, refuse and retry). The failure section keeps only the cases not already shown in the flows.
- Merged the duplicate F1, F2 and F3 entries into the submit and click flows, and dropped the unused (A) label and boxed branch in the request flow.
- Merged the 'Who builds the email' point into the diagram (the link is built from BASE_URL) and kept a single one-line note for it.
- Kept the F5 decision (same form, retype password, link usable), the expired page's link to /forgot-password, the BASE_URL link building, and the breached-list open question.
- Trimmed the notes (concurrency, no enumeration, raw token handling) to the reasons the diagram cannot show. Kept the Referrer-Policy header, the no-logging of payloads, the DB now() timing, the cleanup-job idea and the silent-failure lockout caveat.
- No facts from the first version were dropped.

### Holes
- Q1: What is the "breached list" and where does it live? Is it a local file or an outside service, and what makes it "unavailable"? (author: The brief only says 'the breached-password list' and does not say whether it is a local file or an outside service, so I don't know where it lives. The design treats it as a check the API calls; 'unavailable' means that check errors or times out, and then we fail closed (no reset, form shown again, link still valid). Added an open question and a note.)
