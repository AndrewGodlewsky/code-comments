---
name: code-comments-v5
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
- the reason for odd-looking code. Before simplifying, look for it in tests,
  callers and docs
- a rule that a rewrite hides. When you simplify or restructure code, its old
  shape may have been the only visible sign of a rule, such as which duplicate
  wins, an ordering or a tie-break. If a test, caller or doc explains that rule,
  state the rule and its reason beside the new code, even if behaviour is unchanged
- the source of a constant, not its copied value
- a rejected alternative that a future editor would plausibly try

Put caller contracts in interface docs and maintainer reasoning in the
implementation. Be specific. State the fact itself, not "per the ticket". When
a known issue or PR records the constraint, workaround or decision you are writing
down, add its id after the fact as a pointer, never instead of it. Give a TODO,
workaround or temporary hack the issue that tracks its removal, if one is known.
Reasons the next editor needs belong beside the code, not only in the commit or
your report.

## Never invent
- Write a reason, history or contract only when the request, a ticket, a test, a
  review or a doc you read supports it.
- Take the intended contract from evidence of intent, not from the code being
  fixed.
- Do not record ideas the evidence ruled out. Never invent issue ids.
- Report unverifiable gaps to the user. Do not guess in a comment.
- If you change a value or decision and no one gave a reason, record only the
  new value. Tell the user in your reply that the reason is
  missing, and ask for it.
- If the requested change breaks a limit or requirement that a comment states,
  make the change if asked and tell the user about the conflict in your reply.
  Keep the outside fact (a vendor quota, a law, another team's limit) as written;
  do not rewrite it to fit the change. Still update every statement of what this
  code does, so none describes the old behaviour.

## Restraint
- Do not restate code, names, types or signatures.
- A routine change usually needs no new comment.
- Do not tag code with the issue or PR that changed it ("added for #N"). That
  is history, and commits hold it.
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
