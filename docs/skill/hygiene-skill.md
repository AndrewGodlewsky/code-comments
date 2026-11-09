# The comment hygiene skill: purpose and limits

This page explains what the `code-comments` plugin is for, where it helps, and what
it does not do. The plugin lives in
[plugins/code-comments/](../../plugins/code-comments/README.md), which also covers
install and removal. Issue
[#45](https://github.com/AndrewGodlewsky/code-comments/issues/45) tracks it.

## Why it exists

The project's original question was whether well-kept comments help a later, possibly
weaker, model make correct changes. The
[long-horizon pilot](../evaluation/pilot-report-2026-11-08.md) found no measurable
benefit. On six real pull requests, the full skill did no better than one general
sentence added to the task: "Keep the codebase clean: reuse what already exists,
change only what the feature needs, and don't rewrite working code."

That result does not make comments useless. It means **the skill cannot be sold as a
performance improvement.** It can still do a narrower job: stop agents leaving
comments that are false, and stop them burying the code in comments that say
nothing. A false comment is a cost even when no benchmark notices it: whoever reads
it next, person or model, is told something untrue. This plugin is that narrower
job, packaged so it can be installed and switched off.

## What it does

When Claude edits, fixes, refactors or reviews code, the skill gives it a short
checklist:

1. **Keep comments true.** Fix or delete every comment the change made false. That
   includes comments outside the edited lines, such as docstrings, module headers
   and comments in calling code. Correct the text; do not mark it "outdated".
2. **Capture what the code cannot say.** When the request, a ticket, a test or a doc
   gives a reason, constraint or contract that the code does not show, write it down
   beside the code it governs. This includes a rule that a rewrite hides: if a
   simplification removes the code that made a rule visible, state the rule and its
   reason beside the new code, even when behaviour is unchanged. When a known issue
   or PR records that reason, add its id after the reason, as in "(issue #212)", so
   that searching for the issue finds the code. The id is a pointer and never
   replaces the reason. A TODO or temporary workaround gets the issue that tracks
   its removal, if one is known.
3. **Never invent.** Write a reason only when the evidence supports it. If a change
   has no stated reason, record only what changed and tell the user the reason is
   missing. If a change breaks a stated limit, make the change and tell the user
   about the conflict: keep the outside fact (a vendor quota, a law), and update every
   statement of what this code does. Never invent an issue id.
4. **Restraint.** Don't restate code. A routine change usually needs no new comment,
   and no "added for #N" tag: which issue changed the code is history, and the
   commits hold it. Leave accurate comments word for word.
5. **Fit in.** Match the style already in the file.

`/code-comments:stale-refs` adds a mechanical check. It lists comments in your
changes that name a function, class, flag or file that no longer exists, and Claude
then fixes each one or explains why it left it.

## What it is good at

These are the behaviours the skill and its eval are built to test. Results from the
[hygiene eval](../../evaluation/hygiene/README.md) back them up or knock them down.

- **Comments far from the edit.** An agent changes a value and fixes the comment
  beside it, but misses the docstring in another file that still states the old
  value. The skill tells it to look.
- **Renames and removals.** After a rename, comments elsewhere still name the old
  function. The lint finds these mechanically.
- **Recording a reason that would otherwise be lost.** A ticket explains that rows
  must be sorted because a downstream loader merge-joins on them. Without a comment,
  the next editor sees an unexplained sort and may remove it.
- **Pointing from the reason to its issue.** Issue #212 says a finance vendor's
  importer rejects any amount without exactly two decimal places. The skill writes
  that rule beside the formatting code and ends it with "(issue #212)", so a later
  agent can search for #212 and land on the code, and can read the issue for more.
- **Not inventing reasons.** When a value changes and nobody says why, the skill
  says to report the gap, not make up a rationale.
- **Keeping a rule a rewrite would hide.** A convoluted loop that keeps the last
  stock update for each SKU is simplified. The behaviour stays the same, but the
  reason (the warehouse resends a SKU to correct a miscount, written only in a test)
  is no longer visible. The skill asks for the rule and its reason beside the new
  code.
- **Separating outside facts from the code's own claims.** A geocoding client's limit
  goes from 100 to 250 requests a minute, but the vendor's free tier allows 100. The
  skill keeps the quota, updates every statement of the client's own limit, and tells
  the user the two now conflict.
- **Leaving good comments alone.** In a comment-only review, accurate comments,
  licence headers and tool directives stay exactly as they were.
- **Staying quiet on routine work.** Adding a simple flag should not add a paragraph
  of comments, or an "added for #318" tag naming the issue that asked for it.

## What it helps with

- **Code review.** Fewer review notes of the kind "this comment is now wrong".
- **Handover.** The next person or agent can trust the comments beside the code.
- **Agent-heavy repositories.** Agents write a lot of code quickly. A small rule set
  that applies on every edit keeps comment quality from drifting.
- **Cleaning up.** A comment-only request ("check the comments in this file") fixes
  false claims without touching code.

## Where to use it

Install it where comments are read and agents do much of the editing:

- **Long-lived code that people or agents will change again.** The value of a true
  comment is paid out by the next editor, so it matters most where there will be one.
- **Code with reasons outside the code.** Vendor limits, legal rules, downstream
  consumers, past incidents: anything a ticket or a test knows and the code does not.
- **Refactors and clean-ups.** Renames, moved logic and simplifications are where
  comments go stale and hidden rules get lost.
- **Comment reviews.** Ask "check the comments in this file" to fix false claims
  without touching code. Run `/code-comments:stale-refs` before a pull request.

It adds little, and you can switch it off, for:

- **Throwaway code.** Scripts, spikes and prototypes nobody will maintain.
- **Codebases that keep almost no comments by policy.** It will not add them, and
  there is little to keep true.
- **Work where comments are generated** (API stubs, generated clients). Fix the
  generator instead.
- **Non-code requests.** It is meant to stay quiet there. Whether it does is not yet
  verified (see the evidence below).

## Evidence so far

From the [hygiene eval](../../evaluation/hygiene/README.md), iteration 4
(2026-11-08), Haiku subagents, two runs per case on eleven small cases:

| Configuration | Checks passed (mean per run) |
| --- | --- |
| This skill (v4) | 97.7% |
| Previous version (v3) | 97.0% |
| No skill | 91.4% |

- **Issue pointers:** both v4 runs cited #212 beside the vendor's rule. No run of v3
  or of the bare model cited it.
- **Other gains over no skill:** telling the user a reason is missing (5/5 twice,
  against 4/5 twice). Recording a reason held only in a test is mixed: v4 scored 4/6
  and 6/6, v3 6/6 and 5/6, no skill 4/6 and 5/6. Earlier versions did harm on the
  stated-limit case; v3 and v4 do not.
- **Failures that remain:** a run with or without the skill sometimes rewrites an
  accurate docstring while adding the reason (one v4 run, and both no-skill runs, on
  the pointer case). One v4 run of the test-only-reason case missed the reason in
  the test, as one v3 run did before.
- **No tagging seen in any configuration.** No run tagged a routine change with its
  issue, with or without the skill, so that case guards the rule rather than proves
  it.
- **Cost** is about the same: around 43,000 tokens a run with the skill and 40,400
  without.
- **Six cases do not discriminate.** Haiku without the skill already fixes distant
  comments, renames and simple stale clauses, and leaves routine work untagged.

Read these as small, encouraging signals, not proof:

- Two runs per case, on one model, on a weaker model, with one case per behaviour.
- The baseline is a bare model, not a one-line reminder. The pilot found that one
  general "keep the codebase clean" sentence did as well as the full skill
  downstream; whether a one-line comment reminder matches the skill on these cases
  is untested.
- Triggering is untested: the eval tells the model to read the skill, so it does not
  show that Claude loads it on its own.

## What it is not

- **Not a proven productivity gain.** The pilot found no downstream benefit over a
  one-sentence instruction. Treat it as hygiene, like a linter, not as something that
  makes a model smarter or a weaker model reliable.
- **Not a guarantee against stale comments.** The lint only catches names that no
  longer exist. A comment that says "retries three times" when the code now retries
  five times names nothing missing, so only reading catches it. The skill asks Claude
  to read; it cannot force it.
- **Not a documentation system.** It does not replace a README, design docs, ADRs or
  an onboarding guide. Those hold knowledge that spans files; comments hold knowledge
  about the code beside them.
- **Not a memory or index.** It keeps no central record of decisions and builds no
  map of the code. [ADR 0001](../adr/0001-context-lives-inline-no-central-index.md) explains why the
  project keeps context inline rather than in an index.
- **Not a replacement for tests or commit messages.** A test enforces a constraint;
  a comment explains it. A commit message records why a change happened; a comment
  records what the next editor needs to know. The skill does not move either into
  comments.
- **Not a style enforcer.** It does not reformat docstrings, impose a template or add
  doc comments to every function.
- **Not a fixer of old code.** It acts on code Claude is changing, plus comment-only
  requests. It does not sweep a repository for every weak comment.
- **Not a source of facts.** It cannot know a reason nobody wrote down. When the
  evidence is missing, the right output is a question to the user.

## How it is checked and improved

- **Source of truth.** The skill text is the lean variant,
  `skill-variants/lean/code-comments/SKILL.md`. The plugin carries a copy, and
  `tests/test_plugin.py` fails if they drift.
- **Version tested by the pilot.** The pilot used lean as of commit `baca8a2`. Later
  edits come from the hygiene eval below and have not been through the pilot.
- **Hygiene eval.** [evaluation/hygiene/](../../evaluation/hygiene/README.md) holds
  small, realistic editing tasks, each aimed at one behaviour above. Each case runs
  with and without the skill, and a script grades the results. That is the score
  being climbed.
- **Guarding against a bad climb.** Round 1 showed that a skill can win on a proxy
  while doing harm: weaker models given the skill rewrote valid comments. The eval
  therefore scores preservation and restraint alongside capture. A change that
  raises one at the cost of another is not an improvement.
