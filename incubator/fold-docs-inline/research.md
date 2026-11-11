# fold-docs-inline: research

Research date: 2026-11-11, for issue #50 (ideation candidate C6). No experiment was run.
Evidence types: **measured** (an experiment or mining study), **practitioner** (expert or
vendor guidance), **repo-eval** (this repository's own runs), **hypothesis**.

## Question

The user has already decided to slim or retire one named docs page. How should an agent
decide, claim by claim, what happens to the page's content, so that no stale claim reaches a
comment, no restatement of the code is copied in, each fact ends with one home, and the code
does not change? The four fates are **dropped** (the code already says it), **moved** (a
comment at the file and symbol it governs), **kept** (no code owns it, so it stays in a
document) and **not migrated** (the code contradicts it, and the user is told).

What do bare models already do here, and where would a skill add something that the shipped
hygiene skill and a one-line reminder do not?

Scope comes from the coordinator's direction. The skill acts only on an explicit request
that names one page. It never deletes a folder, never edits `AGENTS.md` or another
instruction file, never changes code and never creates a file. It makes no performance
claim.

## Sources

Repository sources were read at the staging clone on 2026-11-11. External sources were
opened on 2026-11-11 unless marked otherwise.

| # | Source | What it shows | Verbatim quote |
| --- | --- | --- | --- |
| R1 | `intent.md` | Selective replacement is the stated goal, and the boundary is open | "Selective replacement is the goal. Research records, installation guidance, product intent, and other documents can retain distinct purposes. The exact replacement boundary is part of the investigation." |
| R2 | `docs/adr/0001-context-lives-inline-no-central-index.md` | Facts live inline; no index or generated view | "The skill keeps context only in comments, as close as possible to the code they describe." |
| R3 | `docs/research/context-layers.md` §1, §4 | The inline / document / nowhere boundary table, labelled a hypothesis | "The proposed boundary below is therefore mostly hypothesis, built on descriptive data and practitioner consensus." Table row: "Deployment or organisational decisions not visible in code \| A document, not a comment" |
| R4 | `docs/skill/inline-only-tradeoffs.md` C2, C7, Q1 | Some knowledge has no code home; module docstrings for the big picture are an open question to the user | C7: "Some knowledge has no code to sit beside. Deployment topology, external service contracts, product decisions, onboarding". Q1: "Is a module or package docstring an acceptable home for the big picture (C2)?" |
| R5 | `docs/skill/principles.md` P-09, P-21, P-26 | Do not restate; check claims; one home. P-21 is graded D | P-26: "Do not repeat in a comment what the code, a type, a test, another comment or an owning document already states." P-21 grade: "no study tests whether an instruction to verify reduces the harm" |
| R6 | `docs/research/docs-for-agents-practice.md` §2D, §3 | Practitioner fix for drifting AI docs; description of the code adds little in either place | devjiro case: "The fix was one source of truth per module linked from the code, doc updates in the same PR, and audits that delete outdated docs." §3: "That argues against plain what-the-code-does description **in either placement**." |
| R7 | `evaluation/skill_eval/arms/docs-folder/project-docs/SKILL.md` | The user's earlier practice: area docs mix derivable and code-owned content | "Each covers what it does, the contracts callers rely on, the constraints and invariants it must keep, the non-obvious reasons it is built this way, and what else depends on it." |
| R8 | `docs/skill/hygiene-skill.md`, "Evidence so far" | The commonest remaining failures, in every arm | "**Failures that remain:** in every arm, runs sometimes rewrite an accurate docstring while adding the reason. Seven runs wrote more comment lines than a case allowed" |
| R9 | `evaluation/hygiene/iterations/iteration-5-haiku/benchmark.md` | Bare Haiku already updates a doc beside a code change (`retry-cap-elsewhere` 5/5 in every arm) and already leaves accurate comments alone | "Cases that do not discriminate (every arm full marks in every run on both models): clause-goes-stale, comment-only-preserve, no-issue-tag-routine, rename-stale-refs, routine-edit-no-noise." |
| R10 | `docs/evaluation/churn-2026-11-07.md` | Haiku changes **code** lines beyond the task far more often than Sonnet. This measures code churn, not comment churn | Method: "Comments, docstrings and formatting are removed through an AST round-trip, and changed code lines are counted". Finding: "Haiku rewrites more code than the task needs far more often." |
| R11 | `docs/evaluation/report-2026-11-07-seq-smoke.md` | Sonnet writes the reason into comments unprompted. The docs-folder arm cost more in one 10-sequence smoke run | "Sonnet 5.5 with no skill put the required facts into comments in 9 of 10 sequences." "the docs-folder practice cost **73% more per sequence** than code-only" |
| R12 | `docs/research/comment-context/sources/software-engineering-at-google/passages.md` ch10-009, ch10-014 (local copy of *Software Engineering at Google*, ch. 10, Manshreck) | Conceptual docs duplicate on purpose and sometimes have no place in code. Retired docs may point onward | "In almost all cases, a conceptual document is meant to augment, not replace, a reference documentation set. Often this leads to duplication of some information, but with a purpose: to promote clarity." "The only logical place to document such complex behavior is through a separate conceptual document." "when a document no longer serves any purpose, either remove it or identify it as obsolete (and, if available, indicate where to go for new information)." |
| R13 | `.../pragmatic-programmer/passages.md` pragmatic-programmer-006 (an unverified machine transcript of the audiobook) | DRY applied to comments that restate code | "The intent of this function is given twice. Once in the comment and again in the code. The customer changes a fee and we have to update both." |
| R14 | `.../comments-bug-fixing/passages.md` comments-bug-fixing-005 (PDF text extraction) | Counterevidence: in one study, comments explaining *how* mattered most to a bug-fixing model | "Our analysis revealed that the most influential category of comments were those documenting how the method achieves its goal." |
| E1 | Google, *Documentation Best Practices*, https://google.github.io/styleguide/docguide/best_practices.html | Migration advice; what inline comments are for; what a docs directory holds | "Default to delete or leave behind if migrating. Stragglers can always be recovered." "The primary purpose of inline comments is to provide information that the code itself cannot contain". Docs directory items: "Run its tests." "Release the binary." |
| E2 | Diátaxis, https://diataxis.fr/how-to-guides/, https://diataxis.fr/reference/, https://diataxis.fr/explanation/ | Task guides and explanation are forms with no single code location. Reference describes the machinery | "A how-to guide describes an executable solution to a real-world problem or task." "Reference material describes the machinery." "For the user, explanation joins things together." |
| E3 | PEP 257, https://peps.python.org/pep-0257/ | The convention asks module docstrings for a summary of what the module exports, a sanctioned restatement | "The docstring for a module should generally list the classes, exceptions and functions (and any other objects) that are exported by the module, with a one-line summary of each." |
| E4 | Anthropic, *Best practices for Claude Code*, https://code.claude.com/docs/en/best-practices | Vendor tool and guidance: cut what the code shows; deploy knowledge belongs in a document | "That's why the file works best when it only holds what Claude couldn't work out from the code itself". "`/doctor` suggests cuts for anything Claude can already work out from the code." Listed keep item: "Decisions that aren't in the repo: which error helper the team settled on, how deploys work, what needs a migration review" |
| E5 | Xu & Wu, *Stale Instruction Files Override the Code in Coding Agents*, arXiv 2610.30571 v1 (2026-10-22), https://arxiv.org/abs/2610.30571 | **Measured**: agents follow stale written claims over the code, and one agent rewrote code to match the file | "Without the sentence, 90.1% of the agents' choices followed the stale file." "Claude Code pointed out the conflict in 79 of 80 runs and still followed the file." "Codex CLI rewrote the existing code to match the file in 20 of 80 runs," |
| E6 | Treude & Baltes, *Context Rot in AI-Assisted Software Development*, arXiv 2606.09090 v1 (2026-06-08), https://arxiv.org/abs/2606.09090 | **Measured**: AI configuration files hold stale code references | "identifies stale code element references in 23.0% of repositories" |
| E7 | Tan, Wagner & Treude, arXiv 2212.01479 (2022), https://arxiv.org/abs/2212.01479 | **Measured**: documentation that names code goes stale | "most projects contain at least one outdated code element reference at some point in their history." |
| E8 | Kang, Milliken & Yoo, arXiv 2406.14836 v1 (2024), https://arxiv.org/abs/2406.14836 | **Measured**: comments that LLMs write are often false | "roughly a fifth of its comments contained demonstrably inaccurate statements." |
| E9 | Gloaguen et al., *Evaluating AGENTS.md*, arXiv 2602.11988 v3 (2026-09-29), https://arxiv.org/abs/2602.11988 | **Measured**: restating context adds cost without gain; overviews did not help | "providing context files does not generally improve task success rates". "repository overviews, although popular and recommended by model providers, are not helpful." |
| E10 | Chatlatanagulchai et al., *Agent READMEs*, arXiv 2511.12884 v2 (2026-08-09), https://arxiv.org/abs/2511.12884 | **Measured**: instruction files carry code descriptions | "implementation details (70.8%)" |
| E11 | `do-docs-audit` community skill, registry mirror https://claudskills.com/skills/do-docs-audit/SKILL.md (source repository not identified) | Prior art: it audits docs against the code, deletes, moves and edits CLAUDE.md. It never mentions comments | "Only DELETE when the document's entire subject matter no longer exists in the codebase." |
| E12 | LyingDocs 0.1.4 (2026-04-16), https://pypi.org/project/lyingdocs/ | Prior art: LLM claim extraction and checking against the code, report only. Categories include "Code contradicts documentation" | "Hermes reconciles documented claims with observed implementation behavior and outputs a report of misalignments." |
| E13 | docrot, https://github.com/dager23/docrot | Prior art: deterministic resolution of the references in Markdown and agent files | "Semantic truth of prose isn't deterministically checkable; references and anchored claims are." |
| E14 | Swimm docs, https://docs.swimm.io/new-to-swimm/benefits-of-code-coupled-documentation | Prior art: documentation kept outside the code and synced to snippets | "Swimm's Auto-sync feature automatically keeps your code snippets up to date when your code changes." |

Not used:
- The PyPI page for docrot failed to load; the GitHub README was used instead.
- Swimm's storage model is unverified: the page does not say whether its docs are separate files.
- Ousterhout's cross-module "design notes" advice is not in the local corpus and was not opened.
- Martraire's *Living Documentation* was not opened.

## Findings

Observations only. Interpretation follows in the next section.

1. **The boundary is a hypothesis.** The repository's own placement table is "mostly
   hypothesis" (R3), and the user has not answered the module-docstring question (R4 Q1).
   No study moves the same fact between a document and a comment and measures the cost (R3 §2D).
2. **Written claims about code go stale, and agents follow them.**
   - Stale code references appear in most projects' documentation at some point (E7).
   - They appear in 23.0% of repositories' AI configuration files (E6).
   - Agents followed a stale instruction file in 90.1% of choices, even after naming the
     conflict (E5).
   - One agent rewrote correct code to match the file in 20 of 80 runs (E5).
   - E5 covered auto-loaded convention files, not a docs page read through a tool (R6 §3).
3. **Copying adds risk.** LLM-written comments were false in about a fifth of cases (E8).
   DRY and P-26 warn that a duplicate is a second thing to update (R5, R13). Context files
   that restate the repository added cost without improving success (E9).
4. **Some knowledge has no code to sit beside.** Every guidance source that discusses it
   keeps it in a document: deployment and onboarding (R4 C7), how deploys work (E4), running
   tests and releasing (E1), task guides and explanation (E2), and conceptual documents that
   span modules (R12).
5. **Guidance on duplication is split.** Google's conceptual documents duplicate "with a
   purpose" (R12), PEP 257 asks a module docstring to summarise its exports (E3), and in one
   bug-fixing study *how* comments were the most influential (R14). Against these, P-09 and
   P-26 (R5) and vendor guidance (E4) say to cut what the code shows.
6. **Migration advice favours leaving things behind.** Google: "Default to delete or leave
   behind if migrating" (E1). Google also suggests a retired page can point onward (R12).
7. **What bare models already do (repo-eval):** Haiku and Sonnet update a doc that states a
   changed value (R9, `retry-cap-elsewhere`) and leave accurate comments alone in comment-only
   reviews (R9). Sonnet records reasons in comments unprompted in 9 of 10 sequences (R11).
   Claude Code names conflicts between file and code in 79 of 80 runs (E5).
8. **What they get wrong (repo-eval):**
   - In every arm, runs rewrite accurate docstrings and overrun comment-line limits (R8).
   - Haiku changes code beyond the task far more often than Sonnet: 53/360 against 6/360 (R10).
   - **Correction to the C6 evidence:** R10 counts code lines with comments stripped. It
     does not measure comment churn, so it bears on the "code unchanged" check, not on
     comment volume.
9. **Prior art covers parts of the job, but none moves facts into comments.** do-docs-audit
   checks docs against the code, then deletes, moves and edits CLAUDE.md (E11). LyingDocs and
   docrot only report (E12, E13). Claude Code's `/doctor` suggests cuts to CLAUDE.md, the
   "dropped" fate for instruction files only (E4). Swimm keeps the second artefact and syncs it
   (E14), which ADR 0001 rejects (R2). The shipped skill works on code being changed and says
   it is "Not a documentation system" (`docs/skill/hygiene-skill.md`).

## What this means for the skill's rules

Each rule names its sources. "Hypothesis" means no source tests it.

1. **Act only on an explicit request that names one page.**
   - If no page is named, ask which one.
   - Never delete a folder, and never present the work as advice to delete docs.
   - Sources: direction; judges' fixes; the user's fuller theory still values docs (`intent.md`). *Practitioner / hypothesis.*
2. **Never edit an instruction file**, even when it duplicates a moved fact. List the duplicate
   in the reply instead. Sources: direction; R3's instruction-file duty is "untested"; E10 shows
   such duplicates are common. *Hypothesis.*
3. **Split the page into claims** (a sentence, a bullet or a table row). Check each against the
   code before giving it a fate. Sources: E5, E6, E7, R5 P-21. The hazard is *measured*; that
   checking reduces it is *hypothesis* (P-21 is graded D). E5's one-sentence precedence fix
   suggests that an explicit "the code wins" rule is worth stating.
4. **Dropped:** the code, names, types or tests plainly state it. It gets no comment. Sources:
   R5 P-09, R13, E4, E9, R6. *Practitioner (B)*, with R14 and E3 as counterevidence. Where a
   repository convention asks for a summary (E3, P-31), follow the convention.
5. **Moved:** a code-owned fact the code cannot show goes into one comment at the scope it
   governs, named in the reply by file and symbol.
   - That covers a constraint, reason, coupling, external contract or plausible rejected alternative.
   - Keep any ticket id the page gives, as the shipped skill does.
   - Add a pointer at a dependent site only where that site would otherwise break the fact
     (ADR 0001 consequences; AXIS-REPEAT b).
   - Sources: R3 table, E1 ("information that the code itself cannot contain"), the shipped
     skill's capture rules. *Practitioner; the boundary itself is hypothesis.*
6. **Kept:** whatever has no code to sit beside stays in the document. That covers operational
   steps, cross-cutting explanation, other systems and intent. Sources: R4 C7, E1, E2, E4, R12.
   *Practitioner.*
7. **Not migrated:** a claim the code contradicts goes into no comment and changes no code.
   - Report it with the code's evidence (file, symbol, actual value) and leave the user to
     decide which side is right.
   - Sources: E5 (code rewritten to match a file), `docs-for-agents-practice.md` on spec-kit
     #4940 ("deciding which side is right stays a human choice"), shipped "Never invent".
     *Measured hazard; the rule is hypothesis.*
8. **One home per fact.**
   - Remove each moved or dropped claim from the page.
   - Add no index, map, summary page or new file.
   - A one-line onward pointer inside the slimmed page is not settled (see Open questions).
   - Sources: R5 P-26, R13, R2, R6 devjiro fix. *Practitioner.*
9. **Change no code. Leave accurate comments word for word. Match the file's style.**
   Sources: R8, R10, shipped skill. *Repo-eval.*
10. **Delete the page only when the user asked to retire it and nothing of fate 3 remains.**
    List every removal. Sources: E1, E11's own limit, direction. *Practitioner / hypothesis.*
11. **Make the reply the deliverable:** one line per claim, giving its fate, file and symbol, or
    the contradicting evidence, plus any gaps the user must fill. Sources: judges' fix; in the
    hygiene eval the clearest discriminator was a reply duty (`no-invented-reason`, R9). *Hypothesis.*
12. **Big-picture overviews:** do not settle the module-docstring question. Keep the overview in
    the page and tell the user it could also go in a module docstring. Sources: R4 Q1, R12
    (file comment versus separate document), E9 (overviews did not help agents). *Hypothesis; left
    to the user.*

How it differs from the shipped skill:
- The shipped skill's input is a code change and its output is accurate comments.
- This skill's input is one named document. Its outputs are deletions from that document and
  a fate list.
- The shipped skill already says "Give each fact one home" and "Do not restate code". The
  `shipped_skill` arm will show whether rules 3, 6, 7 and 11 add anything.

## What this means for the eval

Grade only what nobody disputes (direction):
- **Stale claims never reach a comment.** `gradelib.added_text` contains no stale value or phrase.
- **Restatements are not copied in.** No added prose line contains the page's restating phrases.
- **One home.** A moved fact's anchor word is absent from the page and occurs in exactly one file.
- **Code unchanged.** `gradelib.same_code` on every source file.
- **No new files.** `gradelib.new_files` is empty.

Treat placement (the anchor word sits within a few lines of the right symbol) as a secondary
heuristic. The harness has no `placement` focus. Either keep those checks in separate grader
files, report them apart in the README, or add a focus to `harness.FOCUSES`; that is the
coordinator's call. Rule on paraphrases with `overrides.json`.

Request wording:
- Phrase every request as "move what belongs next to the code", never "move everything".
  Literal compliance with "everything" is contestable (rigor judge).
- Leave module-docstring placement ungraded.
- Do not grade whether the page still exists. Grade what happened to its claims.

Likely bare-model failures. Each is a prediction for a trap, not a demonstrated result:
- **Copying a stale value into a comment.** Predicted from E5, where agents followed stale
  files. A tool-read page may differ (R6 §3). *Hypothesis.*
- **Changing code to match the page** (for example, setting `MAX_BATCH` to 50). Predicted
  from E5's Codex runs and from R10's Haiku churn. The AST check catches it.
- **Pasting restatements into docstrings, and rewriting accurate docstrings.** R8 shows every
  arm does the second today. Budgets on added lines (`gradelib.at_most`) and `nothing_lost`
  catch both.
- **Leaving a moved fact in the page as well as the code.** *Hypothesis*, untested here.
- **Creating a "moved to code" file or index.** *Hypothesis.*

What bare models already do well, so expect ceilings: updating docs beside a code change (R9),
leaving accurate comments alone (R9), noticing conflicts (E5) and, on Sonnet, writing reasons
unprompted (R11). So a reply check like "mentions the stale claim" may not discriminate on Sonnet. One home,
restraint and the "not migrated" check are where headroom is most likely. Five of the eleven
hygiene cases hit the ceiling in every arm (R9). Build traps that a careful bare model fails
in a pilot run, not traps that only look hard.

Case set: 7 cases, 5 training and 2 held out.
- Keep C6's `retire-mixed-doc`, `derivable-only-doc` and `stale-claims-not-migrated`.
- Rephrase `no-code-home` as above.
- Drop `agents-md-code-facts`, which edits an instruction file.
  - Replace it with a bystander case. The named page is under `docs/`, and `AGENTS.md`
    also states one moved fact.
  - Graders: `AGENTS.md` byte-identical (`files_unchanged`), and the reply names the
    duplicate.
- Held-out candidates:
  - a TypeScript page, since `gradelib` reads `//` comments, with a cross-file coupling
    that needs a pointer;
  - a clause-level stale claim, for example "retries three times with a 2 s backoff"
    where only the count is wrong.

Reminder arm: C6's sentence is "Keep only what the code cannot show, put each fact beside the
code it governs, and give each fact one home." It omits "check each claim against the code",
which fairly tests whether rule 3 earns its place. In the hygiene eval a "fix or delete"
reminder deleted a true outside fact in two of three Haiku runs (R9 notes). This sentence may
likewise delete operational content; record it if it does.

## Counterevidence and limits

- **No downstream benefit is shown or claimed.** The pilot found none for the shipped skill
  (`hygiene-skill.md`). R11's cost figure comes from one 10-sequence smoke run and is not a
  claim for this skill.
- **Docs may help.** The user's fuller theory is that a docs folder helped weaker models on large
  projects (`intent.md`). Generated docs added about 9 points on 57 issues, without a
  significance test, and an always-loaded index beat optional retrieval (R6 §2C, not reopened
  here). Retiring a page can remove help that this eval does not measure.
- **Purposeful duplication is legitimate** in conceptual documents (R12) and in PEP 257 module
  summaries (E3). "Restates the code" is a judgement, and graders can only use keywords.
- **Inline comments drift too** (`human-maintenance-and-drift.md`: CoCC found 23 of 25 flagged
  comments outdated). Moving a fact does not make it stay true.
- **E5's setting differs.** It used conventions in auto-loaded files, not docs read through
  tools. Claim 2 transfers only as a hypothesis.
- **Prior-art evidence is thin.** E11 to E14 are self-described tools with no outcome data.
  E11 was read through a registry mirror. Treat them as design comparisons only.
- **Small cases test single decisions**, not a real retirement of a long page.

## Open questions

1. Is a module or package docstring an acceptable home for big-picture overviews (R4 Q1)?
   This is for the user; until answered, keep overviews in the page and leave them ungraded.
2. May the slimmed page keep a one-line onward pointer ("rounding: see `invoice_total` in
   `billing/totals.py`"), as Google suggests (R12)? Or is that the stub or index that ADR 0001
   rules out? It names code, so a later rename leaves it stale, which `stale_refs.py` does not check.
3. When a page is a conceptual overview that duplicates with purpose (R12), should its restating
   sentences be dropped or kept?
4. When the page names an instruction file, should the skill refuse, or only report the
   code-describing lines it found there?
5. Is a read-only `doc_claims.py` worksheet (the candidate's mechanism) worth adding? Add it
   only if runs show missed stale claims. docrot (E13) shows that reference resolution is
   checkable and prose truth is not.
6. Does the skill need its own activation eval? The trigger is explicit by design, which is
   the favourable case seen in #20.
