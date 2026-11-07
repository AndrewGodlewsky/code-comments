---
name: code-comments
description: Keep code comments accurate and worth reading while you change code. Use whenever you edit, fix, refactor or review source code, and for comment-only refresh requests. It covers recording the non-obvious reasons, constraints and contracts that tickets, tests and discussion reveal; fixing or removing comments a change makes false; and avoiding comments that merely restate the code. Use it even when the user never mentions comments, because stale or missing explanation is what misleads the next agent that edits this code.
---

# Code Comments

The next person to edit this code is likely a fresh agent session. It has the
code, but not this conversation, the ticket you read, or the reasoning you did.
Comments are how what you learned survives into that session. A wrong comment
hurts that reader more than no comment, because models tend to believe what they
read. So the job is not "add comments". It is to leave the code's explanation
**true, sufficient and lean** when you finish.

Follow the three steps below, in order, on every code change. They are a
workflow, not a checklist to recite: use judgement at each step. The aim is that
a capable reader with only the code would not go wrong where you would not.

1. **Before editing:** read the comments you will touch as claims, and note what
   is protected.
2. **While editing:** note evidence-backed facts as you meet them, and write them
   in the scope they govern.
3. **Before finishing:** scan the diff, hunk by hunk and beyond it.

A request to refresh or review only comments has its own short path at the end.

## Step 1. Before editing: read the comments as claims

Comments describing the old behaviour do not update themselves, and you cannot
fix what you never read. So read first.

1. **Read the comments around the code you will change.** Include the enclosing
   function's docstring, the module header, comments in callers that describe
   this code, and any README or doc section about it. Keep a short list of them;
   Step 3 rechecks each one.
2. **Treat each one as a claim to check, not a fact.** Before you rely on a
   comment, compare it with the code, the tests and the task. When they disagree,
   use the evidence of intent (the request, a ticket, a test, a review comment)
   to decide which side is wrong, and fix that side.
3. **Look for the reason behind odd-looking code before you simplify it.** Check
   nearby comments, tests, history and task evidence. Code that looks unnecessary
   often guards something; if you find a reason that is not written down, note
   it for Step 2.
4. **Note protected text** so you do not damage it later:
   - License headers and tool directives (`noqa`, `type: ignore`, pragmas). These
     are never yours to remove.
   - Comments that are still true. Leave them word for word. Rewording a valid
     comment costs review effort and can introduce errors, for no gain.
   - Existing commented-out code near your edit. Leave it and mention it to the
     user at the end. It misleads models, but it may be there on purpose.
5. **Note the local comment form.** Look at the style and vocabulary in the
   file, then the module, then the project, so what you write in Step 2 fits in.

## Step 2. While editing: note evidence and write it in scope

The task often gives you knowledge that is invisible in the code. If you leave it
out, the next agent cannot regenerate it. It will reason from the code alone and
may "simplify" away the very thing that mattered. Capture it as you go, because
details you meet early are easy to lose by the end.

### Note facts with their source

As you read the request, ticket, tests, review comments, commits or docs, note
each non-obvious fact together with where you saw it. Three kinds of note need
special handling:

- **A hypothesis the evidence later ruled out.** Mark it as ruled out, so it
  never becomes the stated reason.
- **The intended contract during a bug fix.** Take it from the evidence of
  intent, not from the code you are fixing. A faithful description of buggy
  logic hides the bug.
- **Something that seems to matter but whose reason you cannot verify.** Note it
  as a gap for your final message. Do not guess at it in a comment.

### Decide what is worth writing

Spend explanation where a capable reader could plausibly go wrong. A routine
rename, a plain bug fix or a pass-through parameter usually needs no new comment
at all. Comment quantity is not the goal: every comment is a second copy of
something that has to be maintained, and noise hides the comments that matter.

Worth recording when the evidence shows it:

- **Constraints and assumptions, at the point of reliance.** An invariant, an
  ordering requirement, a bound, an input or environment assumption, behaviour
  you depend on from another component, or a convention every caller must
  follow. If the evidence says when the constraint stops applying, say that too,
  so a later editor knows when the decision has expired.
- **The decisive choice.** When a natural-looking alternative would be wrong
  ("compare as integers, not strings", "release the lock before the callback"),
  state the choice and what it rules out, on the line that makes it.
- **Deliberate oddities.** A fall-through, an empty catch, a no-op, or a sleep
  that looks like a mistake. Say that it is intentional, and why.
- **The reason you found for odd-looking code** in Step 1, written beside it.
- **Where a constant comes from.** Name its source (a spec, a measurement, an
  external limit, another value) so an editor knows what must change with it.
  Do not copy the value itself into prose; it will drift.
- **A rejected alternative, when a future editor would plausibly try it.** One
  line is enough: "not X, because Y".

### Write it in the right place and form

- Put **caller contracts** (inputs, outputs, errors, side effects, what is not
  promised) in the interface comment or docstring. Put **maintainer reasoning**
  next to the implementation it explains.
- **Be specific.** "Sorts by start time, then id, so ties keep a stable order
  across pages" helps; "handles edge cases" does not.
- **State the fact itself**, not "as discussed" or "per the ticket". A ticket
  reference is fine *in addition to* the fact. Never invent an issue number,
  owner or date.
- **Describe the design as it now is.** Write "Uses a min-heap so the cheapest
  job runs first", not "Changed from a list to a heap after the slowdown".
  Version control keeps the history, and a comment that narrates the past soon
  contradicts the present.
- **Keep the reason beside the code.** A commit message or your final report is
  not enough if the next editor needs it. Leave the story of the change itself
  (what you changed, which bug it fixed) to the commit.
- **Give each fact one home.** Explain it where it is owned, and point there from
  anywhere else rather than copying it.
- **Fit in.** Use the form and terms you noted in Step 1. When there is no
  convention, lead with what the unit does, key fact first, in plain prose.

### Keep comments with their code as you move it

When you move, extract, copy or inline code, check that each comment that
travelled still describes its new neighbour. A coherent comment about the wrong
thing misleads more than noise.

### Avoid adding clutter

- Never add commented-out code. Delete code (version control keeps it), or use a
  real skip or flag mechanism with a reason. A temporary workaround or TODO
  should say that it is temporary and why.
- In tests, let test names and arrange/act/assert structure do the explaining.
  Explain a chosen value only when the reason is not evident.
- Within the task's scope, a clearer name or an assertion can carry intent better
  than prose.

## Step 3. Before finishing: scan the diff

This is the step that catches what the edit itself does not: stale text away from
the lines you touched, a single wrong clause inside a good comment, and reasons
you wrote without evidence. Do it every time, even for small changes.

1. **List what changed.** From the diff, write down each changed name (function,
   parameter, constant, field, flag, error type) and each changed behaviour (a
   bound, an order, a default, a return value, an error raised, a side effect).
2. **Walk every hunk.** For each comment and docstring inside or next to a hunk,
   including ones you wrote, moved or left in place:
   - Check **each clause**, not the gist: every step, bound, condition, name and
     value against the final code. One wrong clause in an otherwise good comment
     can cancel its value or steer a later fix wrong.
   - If it is false and its fact is still worth stating, correct it in place. If
     it only restated code that changed, delete it.
   - Fix wrong text rather than labelling it. Notes such as "outdated", "may be
     wrong" or "ignore this" leave most of the misleading effect in place.
   - If the code under it moved, check that it still describes its neighbour.
3. **Search beyond the hunks.** For each name and behaviour from item 1, search
   the repository for comments, docstrings and docs that mention it, and recheck
   the list you kept in Step 1 (docstring, module header, callers, README).
   Correct or delete every one your change made false, in this same edit.
4. **Test each new or changed comment line for restatement.** Ask what a reader
   learns from it that the code, names and types do not already say. If nothing,
   delete it. Also remove narration of statements, construct labels
   ("Constructor") and docstrings that repeat the signature. Rewrite any line
   that narrates the change's history as the current design, or leave that story
   to the commit. Replace a copied value with its source, and a duplicated fact
   with a pointer to its home.
5. **Test each reason, history and contract for evidence.** For each one you
   wrote, name the request, ticket, test, review comment, commit or document you
   actually saw that supports it. If you cannot, remove it and report the gap. A
   plausible invented reason is the worst kind of comment, because it is wrong
   and it looks authoritative. Check that no ruled-out hypothesis became the
   reason, and that any contract came from evidence of intent.
6. **Check capture.** Go through your Step 2 notes. Each fact the code cannot
   show and the next editor needs should now be in a comment, in the scope it
   governs, and not only in the commit or your report.
7. **Check protected text.** Every comment you changed or removed should have
   been false, misattached, mere restatement, or missing a needed fact. Restore
   any you changed only for style or to lower the comment count. Confirm license
   headers, tool directives and existing commented-out code are untouched, and
   that you added no commented-out code.
8. **Report.** In your final message, name any gaps you could not verify and any
   existing commented-out code you found.

## Comment-only requests

When asked only to refresh or review comments, change **no code**: not even
formatting, names or imports. The code must stay identical apart from comments
and docstrings. Follow this short path instead:

An accurate comment stays exactly as written, even if you now know more about it. Do not reword it, extend it, or add history or incident narration to it; change only what is false and add only what is missing.

1. **Read**, as in Step 1, every comment in the requested scope as a claim, and
   note protected text: license headers, tool directives and valid comments.
2. **Gather evidence** of intent from the request, tests, docs and history, as in
   Step 2, and note the facts the code cannot show.
3. **Scan**, treating each comment in scope as a hunk: run items 2, 4, 5, 6 and 7
   of Step 3. Correct false claims, add missing rationale the evidence supports,
   and leave everything accurate untouched.
4. **Confirm the diff touches only comment and docstring lines.** If any code
   line changed, revert it. Then report gaps as in Step 3, item 8.
