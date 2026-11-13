---
name: fold-docs-inline
description: Slim or retire one named docs page by giving every claim on it a fate. A claim is dropped (the code already says it), moved into a comment at the file and symbol it governs, kept in a document (nothing in the code to sit beside), or not migrated (the code contradicts it). The reply is a per-claim fate list for the user to review. Use only when the user has already decided to retire, slim or fold a specific Markdown page, or one section of it, into the code, such as "we're retiring docs/x.md, put what belongs beside the code" or "fold this page into comments and delete it". If the request names a folder or no page, ask which single page to do. Not for updating a doc after a code change, explaining or summarising a doc, writing new docs, editing AGENTS.md or CLAUDE.md, or ordinary code edits, which the code-comments skill covers.
---

# Fold a docs page into the code

The user has decided to slim or retire one docs page. Give every claim on it a
**fate**, so each fact about the code ends with **one home** beside the code it
governs, nothing false or merely restating reaches a comment, and knowledge with no
code home stays in a document. The deliverable is the **fate list** in your reply,
which the user reviews.

This skill decides what happens to each claim. The code-comments skill, when
present, governs how a comment reads; follow it for every comment you add.

## Scope
- Work on the one page the user named. If they named a folder, several pages or
  none, ask which single page to do first and change nothing until they answer.
- You edit two things: the named page, and comments or docstrings in source files.
  Every other file stays byte-identical: code, tests, config, other docs, and
  instruction files such as AGENTS.md and CLAUDE.md.
- If the named page is itself an instruction file, edit nothing. Give the fate list
  only, for the user to apply.
- Change no code, even where the page says the code should differ.
- Add no file. The slimmed page and the comments are the whole result.
- Delete the page only if the user asked to retire it and no kept claim remains.
  Never delete a folder.

## Steps
1. **Split** the page into claims: each sentence, bullet and table row. Split
   further wherever parts could differ in truth, so each value, count, order or
   name is checked on its own.
2. **Check** each claim against the code before giving it a fate. Search for the
   names, values and files it mentions, and read that code and its tests. When the
   page and the code disagree, the code decides what a comment may say, because a
   comment describes the code as it is. Which side is right is the user's call.
3. **Decide** one fate per claim, from the four below.
4. **Edit.** Write each moved claim as a comment. Remove every moved, dropped and
   not-migrated claim from the page. Leave kept claims as written, with no note of
   what left; remove a heading only when nothing remains under it.
5. **Reply** with the fate list.

Done when every claim on the original page appears exactly once in the fate list,
the page holds only kept claims, and nothing changed outside the page and comments.

## The four fates
**Dropped.** The code, names, types, signatures or tests at that spot already state
it, or an accurate comment there already does. It gets no comment. A claim that only
describes what the code is or does stays dropped, even if it could be read as a rule
for later edits. Move it as a constraint only when the page itself states the rule or
gives a reason for it; never supply the rule yourself.

**Moved.** A fact owned by one piece of code that the code cannot show: a
constraint, invariant, ordering, reason, coupling, outside contract the code relies
on, or an alternative a later editor would plausibly try.
- Write it once, in the file's comment style, at the narrowest scope it governs:
  the symbol whose change would break it. Keep any ticket id the page gives.
- Prefer a comment, or add to a docstring the symbol already has. A docstring you
  create holds only the moved fact. Give it no opening line saying what the code
  does, because that line restates the code.
- Take every value about this code from the code, never from the page.
- Where an accurate comment already covers part of it, add only the missing part
  beside that comment and leave the comment word for word.
- Add a one-line pointer at a dependent site only where that site, edited alone,
  would break the fact.

**Kept.** Nothing in the code to sit beside: operational steps (running, deploying,
releasing, recovering), facts about other systems that no code here relies on,
product intent, decision history, and explanation spanning modules with no single
owner. Also keep:
- an overview of the whole module or system. Tell the user it could live in a
  module docstring instead; that choice is theirs.
- a claim about code outside this repository, or one you cannot check against the
  code here. List it as a gap.
- a kept step that names code which disagrees with it. Flag it in the reply.

**Not migrated.** The code contradicts it: a different value, order or behaviour,
or a name this repository no longer has. Put it in no comment and change no code to
fit it. Quote it in the reply with the code's evidence and ask which side is right.
Only the code's own behaviour contradicts a claim: an outside fact the code breaks
(a vendor limit, another team's rule) is moved or kept as written, and the conflict
reported.

## The fate list
One line per sentence, bullet or table row, in page order: the claim, quoted or
closely paraphrased; its fate; and its evidence. Splitting is for checking: where
parts of one sentence have different fates, give each part its own line, and keep
parts that share a fate on one line. Headings are not claims. For moved, give the
file and symbol. For dropped, say where the code states it. For not migrated, give
the file, symbol and actual value.

After the list, name:
- other files that also state a moved fact (an instruction file, another doc), by
  file and line, for the user to reconcile;
- files that link to the page or to a section you removed;
- gaps the user must fill, and whether the page was deleted or what it still holds.
