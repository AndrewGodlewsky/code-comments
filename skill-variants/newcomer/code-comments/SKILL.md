---
name: code-comments
description: Keep code comments accurate and worth reading while you change code. Use whenever you edit, fix, refactor or review source code, and for comment-only refresh requests. It covers recording the non-obvious reasons, constraints and contracts that tickets, tests and discussion reveal; fixing or removing comments a change makes false; and avoiding comments that merely restate the code. Use it even when the user never mentions comments, because stale or missing explanation is what misleads the next agent that edits this code.
---

# Code Comments

The next person to edit this code is likely a fresh agent session. It has the
code, but not this conversation, the ticket you read, or the reasoning you did.
Comments are how what you learned survives into that session. That makes them
powerful in both directions. Correct, specific explanation helps later agents.
A wrong comment hurts them more than no comment, because models tend to believe
what they read. So the job is not "add comments". It is to leave the code's
explanation **true, sufficient and lean** when you finish.

## Who you are writing for

Write for a newcomer: a fresh session that may run on a weaker or cheaper model
than you. That reader gains the most from correct comments. A single stated
decision ("sum, not product") is often what steers it away from a plausible wrong
approach it would otherwise take, and models repairing code lean heavily on
comments that say how the implementation works. A strong model might work these
things out from the code. A weaker one often will not, and it cannot tell which of
your choices were deliberate and which were accidents.

So set the bar lower than "would a capable reader strain here?". Ask instead:
would a fresh, less capable session lack this decision or mechanism, and go wrong
without it? If so, write it down.

Writing more raises the stakes of every other duty. Each extra claim is one more
thing that can go false, and mechanism claims drift fastest, so keep them true
(section 1) with extra care. Never fill the extra room with reasons you do not
have (section 3). This stance asks you to write down more of what you *know*, not
to guess more.

Use judgement. The aim is that a fresh, possibly weaker reader with only the code
would not go wrong where you would not.

## 1. Keep every comment true (most important)

When you change behaviour, the comments describing the old behaviour do not update
themselves. Before you finish:

- **Find what your change falsified.** That includes comments outside the lines
  you edited: the function's docstring, the module header, callers that describe
  what this code does, and the README section about it. Correct each one or delete
  it in the same edit.
- **Check each clause, not the gist.** Reread every comment you wrote, moved, or
  left next to changed code. One wrong step, bound or condition inside an
  otherwise good comment can cancel its value or steer a later fix wrong.
- **Keep comments attached to their code.** When you move, extract, copy or inline
  code, make sure each comment that travelled still describes its new neighbour.
  A coherent comment about the wrong thing misleads more than noise.
- **Fix wrong text. Do not label it.** Notes such as "outdated", "may be wrong" or
  "ignore this" leave most of the misleading effect in place. Correct the claim or
  remove it.
- **Treat existing comments as claims to check, not facts.** Before you rely on
  one, compare it with the code, tests and task. When they disagree, use the
  evidence of intent to decide which side is wrong, and fix that side.
- **Describe the design as it now is.** Write "Uses a min-heap so the cheapest
  job runs first", not "Changed from a list to a heap after the slowdown".
  Version control keeps the history. A comment that narrates the past soon
  contradicts the present.

When a comment is false and its fact is still worth stating, correct it in place.
When it only restated code that changed, delete it.

## 2. Capture what the code cannot say

The task often gives you knowledge that is invisible in the code: why a limit
exists, what a caller relies on, which incident forced an ordering. If you leave
it out, the next agent cannot regenerate it. It will reason from the code alone and
may "simplify" away the very thing that mattered. Write it down, in the scope it
governs, during this edit.

Worth recording when the evidence shows it:

- **Constraints and assumptions at the point of reliance.** An invariant, an
  ordering requirement, a bound, an input or environment assumption, behaviour you
  depend on from another component, or a convention every caller must follow. If
  the evidence says when the constraint stops applying, say that too, so a later
  editor knows when the decision has expired.
- **The decisive choice.** When a natural-looking alternative would be wrong
  ("compare as integers, not strings", "release the lock before the callback"),
  state the choice and what it rules out, on the line that makes it.
- **The mechanism, when it is not obvious.** Besides why, say how when a newcomer
  could not see it from reading the code: the algorithm or technique in use, the
  order a multi-step update must follow, or the trick that makes a bound hold.
  Name it specifically ("walks breadth-first so the shallowest match wins") in a
  sentence or two. Explain the decisive part only; line-by-line narration is still
  restatement (section 4).
- **The major decisions a newcomer would lack.** Record the significant design
  decisions behind this code that the evidence reveals, even when a strong model
  could infer them from the code. A weaker session reading the same code may not,
  and without the note it cannot tell a deliberate decision from an accident.
- **Deliberate oddities.** A fall-through, an empty catch, a no-op, or a sleep that
  looks like a mistake. Say that it is intentional, and why.
- **The reason behind odd-looking code.** Before you simplify something that looks
  unnecessary, look for its reason (nearby comments, tests, history, task
  evidence). If you find a reason that is not written down, write it beside the
  code.
- **Where a constant comes from.** Name its source (a spec, a measurement, an
  external limit, another value) so an editor knows what must change with it. Do
  not copy the value itself into prose; it will drift.
- **The rejected alternative, at each consequential choice.** When the evidence
  shows an alternative was considered and turned down, record it in one line at
  the choice: "not X, because Y". Do this at every consequential choice, not only
  where you expect someone to try X. A newcomer cannot judge which alternatives
  are tempting, and the line stops it reopening a settled question. Only an
  alternative the evidence shows was actually considered qualifies; never write
  "we considered X" to make a choice look deliberated. Phrase it as what the
  design rules out, not as a story of the change.

Put **caller contracts** (inputs, outputs, errors, side effects, what is not
promised) in the interface comment or docstring. Put **maintainer reasoning** next
to the implementation it explains. Be **specific**: "sorts by start time, then
id, so ties keep a stable order across pages" helps; "handles
edge cases" does not. State the fact itself, not "as discussed" or "per the
ticket". A ticket reference is fine *in addition to* the fact.

If a reason matters for the next editor, it belongs beside the code. A commit
message or your final report is not enough. Leave the story of the change itself
(what you changed, which bug it fixed) to the commit.

## 3. Never invent

Write a reason, a history ("we tried X"), or an intended contract only when
something in hand supports it: the request, a ticket, a test, a review comment, a
commit, or documentation you actually read. A plausible invented reason is the
worst kind of comment, because it is wrong and it looks authoritative. A weaker
reader is the least able to doubt it.

- When documenting what code *should* do (especially during a bug fix), take the
  contract from the evidence of intent. Do not paraphrase the code you are fixing,
  because a faithful description of buggy logic hides the bug.
- When a ticket or discussion contains a hypothesis that was later ruled out, do
  not record the ruled-out idea as the reason.
- Never invent an issue number, owner or date.
- If you believe something matters but cannot verify why, leave the code silent
  on it and tell the user about the gap in your final message.

## 4. Restraint

Comment quantity is not the goal. Every comment is a second copy of something that
has to be maintained, and noise hides the comments that matter. Writing for a
newcomer lowers the bar for decisions and mechanisms; it does not make routine
code worth narrating.

- Do not restate what the code, names or types already say. Don't narrate
  statements, label constructs ("Constructor"), or repeat the signature in a
  docstring.
- Spend explanation where a newcomer could plausibly go wrong. A routine rename,
  a plain bug fix, or a pass-through parameter usually needs no new comment at
  all.
- Give each fact one home. Explain a constraint fully where it is owned. Where
  other code depends on it (a caller that must honour it, a site that would break
  if it changed), add a short pointer to the owner, such as "must hold the index
  lock; see `rebuild_index`", rather than a copy. A newcomer editing the call site
  may never open the owner, and the pointer tells it where to look, while a
  copied explanation drifts as soon as one copy is updated and the other is not.
  Point only to something that exists.
- Leave valid comments exactly as they are. Change a comment only because it is
  false, misattached, mere restatement, or missing a needed fact. Never change one
  for style or to lower the comment count.
- Never add commented-out code. Delete code (version control keeps it), or use a
  real skip or flag mechanism with a reason. A temporary workaround or TODO should
  say that it is temporary and why.
- If you find existing commented-out code near your edit, leave it, and mention it
  to the user. It misleads models, but it may be there on purpose.
- In tests, let test names and arrange/act/assert structure do the explaining.
  Explain a chosen value only when the reason is not evident.
- Within the task's scope, a clearer name or an assertion can carry intent better
  than prose. In a comment-only request, change comments only.

## 5. Fit in

Follow the comment and docstring style already used in the file, then the module,
then the project. Use the project's established terms. When there is no
convention, lead with what the unit does, key fact first, in plain prose.

## Comment-only requests

When asked only to refresh or review comments, change **no code**. Not even
formatting, names or imports. Correct false claims, add missing rationale the
evidence supports, and leave everything accurate untouched. License headers and
tool directives (`noqa`, `type: ignore`, pragmas) are never yours to remove.
An accurate comment stays exactly as written, even if you now know more about it. Do not reword it, extend it, or add history or incident narration to it; change only what is false and add only what is missing.

## Before you finish

Look at your diff once more and ask:
1. Did any comment, here or elsewhere, become false? Fix it.
2. Did the evidence teach me something a newcomer could not get from the code: a
   constraint, a major decision, a non-obvious mechanism, a rejected alternative?
   It should be in a comment, in the right scope.
3. Do the call sites that depend on a constraint I explained point to its owner,
   without copying it?
4. Is every reason and every rejected alternative I wrote backed by evidence I
   actually saw?
5. Did I add any comment that only restates the code? Remove it.
6. Did I change or remove any comment that was still true? Restore it.
