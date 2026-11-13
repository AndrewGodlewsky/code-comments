---
name: verify-before-relying
description: Before your new code relies on what a comment, docstring or doc says existing code does, check that claim against the implementation and its tests, and build on what really runs. Use when the code you are about to write depends on stated behaviour of existing code (units, rounding, ordering, return shape, the value returned on failure, the errors raised, what a helper does), when the request names a helper to use or repeats what a docstring or doc says, and when asked to bring a doc in line with the code. It settles a conflict by the kind of claim. A false description of the code is corrected to match the code; a requirement or outside fact that the code breaks is kept as written and reported. A claim that checks out is trusted and left untouched. Not for keeping comments true after your own edit (the code-comments skill does that), not for auditing every comment in a file, and not for instruction files or decision records.
---

# Verify before relying

A comment, docstring or doc that says what existing code does is a claim; the code
is what runs. When code you are about to write depends on such a claim, the claim
is **load-bearing**: check it before you build on it.

This complements the `code-comments` skill. That skill keeps comments true after
your change and governs how comments are worded; this one decides what to build when
what you read and what runs disagree. Word any correction by its rules.

## Find the load-bearing claims
- Before writing code that calls or extends existing code, name each claim it will
  depend on: units and scale, rounding, ordering, return shape and types, the value
  returned on failure, the errors raised, side effects, and what a named helper does.
- Claims come from comments, docstrings, docs, test names and the user's request. A
  helper the request tells you to use brings the claims in its docstring with it.
- Check only these. Most claims are true, and every other comment is the
  `code-comments` skill's business.

## Check each against what runs
- Read the body, not its description. Follow a helper into its own file and into
  what it calls.
- Read the tests that exercise it. A test's expected value is the best record of
  what the code does.
- Where the body leaves an argument out, the library default applies (a time zone,
  an encoding, a line ending). Look that default up; the docstring may name a
  different one.
- If the body and tests still leave it open, **probe**: run the code once from the
  shell (for example `python -B -c "..."`; `-B` stops Python writing bytecode
  caches) on an input where the claim and its alternative give different answers.
  Leave no files behind.

## Build on what the code does
- A claim that checks out is **trusted**. Build on it as written, keep its text word
  for word, and add no defensive conversion, guard or confirmation question for the
  case it rules out. If the reply mentions it, say it checked out.
- A claim that fails: build on the real behaviour, as the tests **pin** it. Naming
  the conflict is not enough; the new code must handle what really happens, such as
  the error really raised or the units really used.
- A named helper that does not do what the task needs: when a test pins its
  behaviour, other callers rely on it, so keep what they get. Meet the need beside
  the helper, or extend it so that existing calls behave as before (for example an
  optional argument whose default keeps today's behaviour). Say in the reply why
  you did not use it as it stands.
- Behaviour no test pins may be accidental. When the body is your only evidence,
  build on it and state that assumption in the reply.

## Settle a conflict by the kind of claim
Sort the claim before you change either side:
- **Description**: what this code does, returns, stores or raises. It loses to the
  code. Correct the text in place and keep working code as it is. Text naming a
  function, option or path the code no longer has is a description too: build on
  what exists.
- **Requirement**: what the code must do. It says must, never or required, or cites
  a policy, law, ticket or contract. Lowercase "must" counts (judgement).
- **Outside fact**: about a party beyond this code, such as a supplier's limit, an
  external format or another team's service.

A requirement or outside fact keeps its words when the code breaks it. What happens
to the code depends on the task:
- If the user asked for the behaviour that breaks it, make the change as asked and
  report the conflict, as the `code-comments` skill says.
- If the task is to fix that behaviour, change the code to meet it.
- Otherwise change neither side, and report the conflict as a possible bug.

A sentence that mixes a description with a requirement counts as a requirement:
keep it as written, and report what the code really does (judgement).

Asked to bring a doc in line with the code, update its descriptions only. Keep each
requirement, outside fact and true sentence exactly as written, and list in the
reply each requirement or outside fact the code breaks.

Edit only comments, docstrings and docs that describe code. A conflict with an
instruction file or a decision record goes in the reply; the file stays as it is.

## When the request carries the claim
The user's request may repeat a claim, often copied from a docstring. Check it like
any other. If it is false, deliver what the user plainly wants, built on the real
behaviour, and open the reply by saying the premise is wrong, with file:line and
what the code really does. If it is true, do exactly what was asked.

## Report
- For each false claim you met: file:line, what it says, what the code does, and
  what you did (corrected it, built around it, or kept it and why). A false premise
  from the request goes first.
- Corrections are the only comments this skill asks for. Any other comment follows
  the `code-comments` rules.

No rule here has been shown to improve results; each is a hypothesis until an eval
tests it. Rules marked *judgement* have no source at all.
