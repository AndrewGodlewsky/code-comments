## Review of auth-04 (junior-v6, author haiku, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Changed: step S1 now calls start_session, which redirects to next or /home, instead of redirecting to return_to. Why: a successful Google login must end where password login ends (Q1).
- Changed: return_to is removed from the flow record. Failure destinations now come from the intent (login goes to /login, link goes to /settings). Why: one field less, and a value derived from intent needs no separate check (Q1).
- Changed: the flow record and confirm record store next (login only) instead of return_to. Why: next is the value start_session needs after login (Q1).
- Changed: the gflow cookie check is its own step, with the flow record kept on a mismatch. Why: makes the no-consume rule visible in the diagram (Q3).
- Changed: a unique violation on create no longer loops back to the email lookup. It re-runs the linked-sub check once, then errors. Why: the first version had no bound and could send a same-sub race to the password form (Q8).
- Changed: added a passwordless-account check (L7) before the confirm form. Why: assumption 4 existed in the text but was not drawn in the flowchart (Q2).
- Changed: the link path checks that the session has not expired, not only that it maps to the user (Q6).
- Changed: the link insert now has edges for a unique-violation race and for a DB error. The login confirm insert has edges for unique violation and DB error. Why: the first version drew neither (Q8 and the failure table).
- Changed: the link success path is shown as redirect to /settings with the session unchanged. Why: the brief says no session change is needed for linking (Q6).
- Changed: the failure table now covers the passwordless match, the same-sub race and a locked target during confirm, and it no longer refers to a step by number.
- Kept the whole design and every rule from the brief and the first version: the flow, the flowchart, the two schema changes, the POST /login NULL rule, the lock and confirm rules, the 600-second limits, the state tables, the failure rules and assumptions 1 to 6 with open question 4.
- Added a plain summary before the terms that says how password sign-in works today and how the Google flow sits beside it. Added the 10-minute round-trip limit and the two design rules (identify by sub, never store Google email or tokens) to the summary.
- Terms: added Redis, Postgres, OpenID Connect, code exchange, login CSRF, session and sid, and unique violation, each in one line. Defined gflow and gconf by their purpose. Removed the return_to term, because failures now go to the start page for the intent and only next is used on success.
- Steps: rewrote them as numbered steps in diagram order. Each one says what starts it, what it does, which record holds its data, and what happens when it goes wrong. Removed the separate failure lists in the steps, so each failure appears once in the failure table.
- Added reasons in one clause where a part appears: gflow stops login CSRF and leaves the flow record alone (step 2), the CSRF token on the Settings link (step 1), and why an unlink needs a password, so the user can still sign in (step 11). The unlink reason is my own inference from the brief, not a stated rule.
- Added the answers from the questions: the callback reads the sid cookie on a top-level GET, which SameSite=Lax allows, and checks it against the flow's user id (step 5). Emails are lowercased and matched with no other change (step 7). A Google-created user has no password, so Google is their only way in until a reset (step 7). The retry after a unique violation runs the linked-sub check once, and a second violation is an error page (step 7). An expired lock is ignored and not cleared (step 6). The confirm record is not extended on wrong passwords (step 9). The passwordless-account guard is marked as a safety check (step 8 and open question 4).
- Merged: the two overlapping failure lists became one table. Two near-identical rows for a link that changed in the confirm step became one row. The notes list and the assumptions list became one open-questions section. The summary's repeated explanation of the flow was removed.
- Cut: the repeated explanation of the flow in the notes, and the separate return_to rules. Nothing that the brief or the first version states was dropped. The step-number references are only the step order, and no step relies on a code to find another part.
- The document length is within about 1.5 times the first version. The flowchart is unchanged from the first version, so its diagram form is kept.

### Holes
- None.
