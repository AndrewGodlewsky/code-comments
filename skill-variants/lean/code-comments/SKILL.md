---
name: code-comments
description: Keep code comments accurate and worth reading while you change code. Use whenever you edit, fix, refactor or review source code, and for comment-only refresh requests. It covers recording the non-obvious reasons, constraints and contracts that tickets, tests and discussion reveal; fixing or removing comments a change makes false; and avoiding comments that merely restate the code. Use it even when the user never mentions comments, because stale or missing explanation is what misleads the next agent that edits this code.
---

# Code Comments

Leave the code's explanation true, sufficient and lean for the next agent, who has
the code but not your session.

## Keep comments true
- Before finishing, fix or delete every comment your change made false. That
  includes comments outside the lines you edited: docstrings, module headers, and
  callers' comments.
- Check each clause of comments near changed code, not just the gist.
- When moving or extracting code, make sure its comments still describe their new
  neighbour.
- Correct wrong text. Do not label it "outdated" or "ignore this".
- Treat existing comments as claims. Check them against the code, tests and task.
- Describe the current design, not its history.
- If a false comment's fact is still worth stating, correct it in place. If it only
  restated code, delete it.

## Capture what the code cannot say
In the scope it governs, record what the evidence shows and the code does not:
- constraints, invariants, orderings, bounds and assumptions, at the point of
  reliance (and when they would stop applying, if known)
- the decisive choice that rules out a natural-looking wrong alternative
- deliberate oddities, and why they are intentional
- the reason for odd-looking code (look for it before simplifying)
- the source of a constant, not its copied value
- a rejected alternative that a future editor would plausibly try

Put caller contracts in interface docs and maintainer reasoning in the
implementation. Be specific. State the fact itself, not "per the ticket". Reasons
the next editor needs belong beside the code, not only in the commit or your
report.

## Never invent
- Write a reason, history or contract only when the request, a ticket, a test, a
  review or a doc you read supports it.
- Take the intended contract from evidence of intent, not from the code being
  fixed.
- Do not record ideas the evidence ruled out. Never invent issue ids.
- Report unverifiable gaps to the user. Do not guess in a comment.

## Restraint
- Do not restate code, names, types or signatures.
- A routine change usually needs no new comment.
- Give each fact one home. Point to it rather than copy it.
- Leave valid comments word for word.
- Never add commented-out code. Leave existing commented-out code alone and
  mention it to the user.
- In tests, let names and structure explain.

## Fit in
Match the comment style and vocabulary already in the file and project.

## Comment-only requests
Change no code at all. Fix false claims, add supported missing rationale, and keep
license headers, tool directives and accurate comments.
An accurate comment stays exactly as written, even if you now know more about it. Do not reword it, extend it, or add history or incident narration to it; change only what is false and add only what is missing.
