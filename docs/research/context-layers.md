# Context layers: decision memory, instructions, and code documentation

Research date: 2026-11-07, for issue #33 (R4). This targeted review tests the
user's three-layer theory (`intent.md`, "The user's fuller theory"): (1) localized
decision memory, (2) instructions and intent, (3) documentation of what the code
does, which the skill would move inline. It extends
[related systems](related-systems-and-researchers.md) (REM, MemUse and Keep the Why
are summarized there, in sections 8–10) and
[coding-agent evidence](agent-context-evidence.md) (the AGENTS.md study is
section 6). It does not repeat them. No experiment was run.

Evidence types: **measured** (an experiment or a mining study with a stated
method), **survey**, **practitioner report**, **vendor claim** (including product
documentation).

## 1. Question and bottom line

How do existing systems and research divide these layers, and which knowledge
belongs inline?

Existing systems do split context into roughly three stores, but they draw the
lines by **lifetime and scope**, not by "why" versus "what". Instruction files are
short, always loaded and prescriptive. Decision stores (ADRs, Keep the Why,
commit trailers) hold deliberation with an explicit status and supersession.
Memory that must stay true is increasingly **anchored to code locations** and
checked against them. Mining studies show the layers already blur: instruction
files commonly contain architecture and implementation descriptions, and half are
never edited after creation. Rationale is needed often but recorded rarely, and
what exists is scattered across issues, PRs and reviews. Almost none of it is in
code comments. **No study measures what misplacing knowledge costs by comparing
the same fact in two layers.** The proposed boundary below is therefore mostly
hypothesis, built on descriptive data and practitioner consensus.

## 2. Findings

### A. How existing systems divide the layers

| System | What it stores, and where | How it stays fresh | Evidence |
|---|---|---|---|
| [Nygard ADRs](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) (2011) | One architecturally significant decision per short file in the repo | Records are never rewritten; a reversed one is marked superseded. Argues "Large documents are never kept up to date" | Practitioner report |
| [Google design docs](https://www.industrialempathy.com/posts/design-docs-at-google/) (Ubl, 2020) | Context, goals, non-goals, trade-offs; "alternatives considered" is called one of the most important sections | Admits the docs "tend to get out of sync with reality"; advises against copying schemas or interfaces into them because they go stale | Practitioner report |
| [Keep the Why](https://github.com/oliver-zehentleitner/keep-the-why/blob/main/README.md) | `context/` topic files hold rationale. AGENTS.md holds "pointers and rules", with "no rationale attached". ADRs stay for major decisions | Entries carry status, supersession and "revisit when" triggers. Whether an entry is true "stays a human judgment". **Code comments are not discussed** | Practitioner report; one-fixture experiment in the [existing review](related-systems-and-researchers.md#10-keep-the-why-a-directly-relevant-existing-rationale-skill) |
| [Lore](https://arxiv.org/abs/2603.15566) (v1, 2026-03-16) | Constraints, rejected alternatives and agent directives as git commit trailers | Immutable, as commits are | Proposal; **no results** |
| [Claude Code memory](https://code.claude.com/docs/en/memory) (read 2026-11-07) | CLAUDE.md is for instructions loaded in every session (build commands, conventions, layout). Path-scoped rules load only with matching files. Auto memory holds Claude's own learnings: a 200-line index, **machine-local**, shared across all worktrees of a repo | Advises keeping files under 200 lines and warns that with contradictory instructions Claude "may pick one arbitrarily"; offers an audit command | Vendor claim |
| [Copilot Memory](https://docs.github.com/en/copilot/concepts/agents/copilot-memory) (read 2026-11-07) and its [engineering post](https://github.blog/2026-01-09-building-an-agentic-memory-system-for-github-copilot) (Jan 2026) | Repository facts (conventions, architectural decisions, commands), each **with citations to code locations** | Citations are checked against the current branch before use; wrong memories are downvoted; default expiry 90 days | Vendor claim. The post reports an A/B rise in PR merge rate from 83% to 90%, p<0.00001, without full method |
| Cursor Memories | Per-project learned memories | Staff said in [November 2025](https://forum.cursor.com/t/are-my-memories-gone/144057) that the feature was "intentionally removed starting from version 2.1.x". Users were told to export memories into Rules. No reason was given | Practitioner report (vendor forum) |
| [Codified Context](https://arxiv.org/html/2602.20478) (v1, 2026-02-24) | A ~660-line "constitution" loaded every session, 19 specialist agent specs, and 34 on-demand subsystem specs that mix design decisions with descriptions of how the code works | Specs updated in the same session as code; a biweekly review; a drift detector that maps files to specs. Upkeep about 1–2 h a week. **Staleness was the main failure mode**: on at least two occasions, outdated specs produced code that conflicted with recent refactors; in one, the agent wired damage through a deprecated path | Practitioner report (one developer, 283 sessions, 108k lines of C#, observational) |

What these share:

- **Instructions** (layer 2) are kept short and prescriptive and are loaded every
  session.
- **Decision memory** (layer 1) is scoped to a decision or topic, carries a status
  and is kept out of the always-loaded file.
- **Freshness**: the two systems most concerned with staying true attach knowledge
  to code. Copilot cites code locations; Codified Context maps files to specs.
- **No system separates "what the code does" from "why"** the way the user's
  theory does. Codified Context's cold specs and Copilot's repository facts hold
  both.

### B. What instruction files actually contain

- [Chatlatanagulchai et al., *Agent READMEs*](https://arxiv.org/abs/2511.12884)
  (arXiv v2, 2026-08-09; **measured**, mining study). 2,303 context files from
  1,925 repositories. Testing instructions appear in 75.9%, implementation details
  in 70.8%, architecture in 68.1%, security in 14.8%. The files grow "through
  frequent, small additions".
- [Mohsenimofidi et al.](https://arxiv.org/html/2510.21413v4) (MSR 2026, v4;
  **measured**). 466 projects. The commonest headings are conventions,
  contribution guidelines, architecture/structure and build commands. **77 of 155
  AGENTS.md files (50%) were never changed after creation.** Explanation appears
  only as "short explanations after the rules". How these files evolve alongside
  the code is left as future work.
- The AGENTS.md outcome study ([existing review §6](agent-context-evidence.md#6-repository-context-files-change-behavior-without-proven-general-success-gains))
  found generated files add cost without improving success. Removing the
  repository's documentation made them help, which suggests **redundancy between
  layers** carries a cost.

So in practice, layer-2 files already carry layer-3 content: architecture and
implementation descriptions that are often never updated.

### C. Decision memory: needed often, recorded rarely, scattered widely

- [Al Safwan & Servant, FSE 2019](https://people.cs.vt.edu/~khsaf/public/papers/fse19.pdf)
  (**survey**: 20 interviews, then 24 respondents). Developers split commit
  rationale into 15 components. Most respondents seek rationale several times a
  week and spend over 20 minutes on hard cases. They found **side effects and
  alternatives** hardest to find. They least often record **alternatives, the
  selected alternative, constraints and maturity stage**. Three of 20 interviewees
  thought alternatives were not rationale at all.
- [Sun et al., *Recovering Fine-Grained Code Change Rationale from Multiple Software Artifacts*](https://arxiv.org/html/2604.10345v1)
  (arXiv v1, 2026-04-11; a v2 appeared 2026-07-29; **measured** annotation, 63 commits in five Java
  projects, κ = 0.79).
  - Goal sits in commit messages and PRs. Need is mostly in issues. Alternatives
    appear mainly in issues (60%) and pull requests (25%); code review holds 15%. *(Corrected after the [2026-11-07 citation audit](audits/2026-11-07-r1-r4-citation-audit.md).)*
  - Apart from Goal and, less often, Need, components appeared only outside commit messages.
  - Inline comments held 3 rationale sentences (0.4% of their sentences), class
    Javadoc 4.
  - No artifact recorded Constraints or Dependency.
  - Small sample; Java only.
- **ADR adoption is thin.**
  - [Buchgeher et al.](https://research.jku.at/en/publications/using-architecture-decision-records-in-open-source-projects-an-ms/)
    (IEEE Access, 2023; **measured**, GitHub mining) report low adoption, and about
    half of the repositories that use ADRs hold only one to five. The sample size
    was not verified (full text blocked).
  - [Garcia de Santana Junior et al.](https://conf.researchr.org/details/icsa-2026/icsa-2026-papers/34/Architecture-Decision-Records-Adoption-Impact-and-Developer-Engagement-in-Open-Sou)
    (ICSA 2026; **measured**, 921 repositories, 5,800 ADRs) find about 63% of ADRs
    were created already "accepted", skipping the deliberation they exist to
    record. Correlations with quality metrics are "predominantly small". Only the
    abstract was read.
- [Su et al.](https://arxiv.org/abs/2602.07609) (arXiv v1, 2026-02-07;
  **measured**, 980 ADRs from 109 repositories). LLMs detected violations
  accurately for "explicit, code-inferable decisions". Accuracy fell for implicit
  or deployment-oriented ones. That suggests a natural seam: a decision visible
  in code can be checked at the code, and one that is not cannot.

### D. What the wrong layer costs

No study manipulates where a fact lives and measures the downstream cost. The
costs below are inferred from descriptive and observational data.

- **It isn't found.**
  - Rationale is costly to find (Al Safwan) and sits in issues, PRs and reviews
    (Sun). A fresh agent session does not see these unless it goes looking, and
    the project's [P-24](../skill/principles.md#p-24--put-rationale-the-next-editor-needs-in-the-source-not-only-in-the-commit-review-thread-or-your-report)
    already assumes so.
  - MemUse shows that memory can be delivered and still go unused
    ([existing review §9](related-systems-and-researchers.md#9-memuse-delivered-memory-may-never-influence-useful-work)).
  - Claude Code's auto memory is machine-local, so its knowledge is invisible to
    teammates and to human editors. That is a documented fact; the consequence is
    inference.
- **It duplicates.**
  - The AGENTS.md redundancy result above.
  - Claude Code's warning that contradictions are resolved arbitrarily (vendor
    claim).
  - The "one home per fact" consensus
    ([P-26](../skill/principles.md#p-26--give-each-fact-one-home-point-to-it-rather-than-copy-it);
    expert opinion).
- **It goes stale.**
  - Half of AGENTS.md files are never updated.
  - Design docs drift (Ubl); large documents are not kept current (Nygard).
  - Staleness was the main failure in Codified Context.
  - Inline placement does not prevent drift either: Wen et al. found rationale
    comments going obsolete too
    ([existing summary](comment-maintenance-and-evaluation.md#wen-nagy-bavota-and-lanza-2019-proximity-does-not-prevent-drift)).

## 3. Counterevidence and limits

- **External decision memory can work.** Keep the Why's positive result used an
  external `context/` file. Copilot's positive A/B used an external store anchored
  to code and validated at use time, not inline comments. Freshness may come from
  **anchoring and validation**, not from placement alone. This cuts against the
  view that inline is the only way to avoid drift.
- **Comments currently hold almost no rationale** (Sun: 0.4%). That may mean
  developers simply don't write it there, or that they judge comments the wrong
  place. Some interviewees did not count alternatives as rationale at all.
- **The theory's layers are not how practice divides knowledge.** Instruction files
  hold implementation details (70.8%), and agent specs mix decisions with
  descriptions. "The skill replaces layer 3" therefore overlaps content that
  already sits in layer-2 files.
- **Instruction files have weak outcome evidence.** Developer-written files gained
  2.4 points, not significant (existing review §6). The case for a dedicated
  instruction layer rests on convention, not on demonstrated effect.
- **Cursor folding Memories into Rules** may mean a separate learned-memory layer
  was redundant with instructions. That is weak evidence: a forum post with no
  stated reason.
- **Dates and models.** Al Safwan (2019), Buchgeher (2023), Nygard (2011) and Ubl
  (2020) predate current agents. The vendor pages are snapshots read on 2026-11-07
  and may change.
- **Unverified numbers.** The ICSA 2026 paper and Buchgeher were read only as
  abstracts. Copilot's A/B does not say whether "7%" means percentage points.

## 4. Implications

### Proposed boundary for the skill

The test: does the knowledge belong to one nameable code scope, and must it change
when that code changes? If so, it goes inline. Knowledge that spans scopes,
records a deliberation, or outlives the code goes to decision memory, with a
pointer. Knowledge that tells the agent how to work regardless of location goes to
instructions. The history of a change goes to the commit.

| Knowledge | Home | Status |
|---|---|---|
| Build and test commands, conventions, process rules | Instruction file, short and always loaded | **Evidence-backed** as practice (mining studies, vendor guidance). Benefit to outcomes: **hypothesis** (weak, non-significant evidence) |
| Product intent, goals, non-goals | Intent document or instruction file; not inline, since no code scope owns them | **Practitioner consensus**; untested |
| Contracts, invariants, couplings at the point of reliance, why this form | Inline at the owning scope (P-18, P-22, P-05) | Expert consensus. Agent benefit: **hypothesis**. Copilot's code citations support anchoring to code for freshness (vendor claim) |
| A rejected alternative that a later editor would plausibly reintroduce | One line inline at the choice | That it should be recorded: **survey-backed** (least recorded, hardest to find). Inline placement: **hypothesis** |
| Cross-module decision: full alternatives, status, supersession | ADR or decision log, if the repository has one. State the local consequence inline, with a pointer | **Hypothesis**, built on practitioner and expert sources. ADR adoption is thin (**measured**), so the skill cannot assume one exists |
| Deployment or organisational decisions not visible in code | A document, not a comment | Indirect **measured** support (Su et al.: LLMs are weak on implicit and deployment decisions) |
| Narrative of the change: what changed, which bug | Commit or PR (P-24, P-29) | Expert opinion |
| Session learnings and user preferences | Agent memory; outside the skill | Vendor design; **hypothesis** that code facts belong there only when anchored to code |
| Facts the code, names or types already state | Nowhere (P-09) | Expert consensus, plus the AGENTS.md redundancy result |

### Scope of the skill

- **The skill's layer is better defined as "code-owned knowledge, including local
  rationale" than "what the code does".** This diverges from the user's framing.
  The local slice of decision memory (constraints, the plausible rejected
  alternative) is the knowledge least recorded and hardest to find, and today it
  lives in review threads a fresh agent never reads. Pure "what it does" content is
  the most derivable from code. This is a **hypothesis** for #19 to test.
- **AXIS-PLACEMENT.** The evidence favours position (b), the linked hybrid limited
  to documents that already exist: state the local fact inline and point to an
  existing ADR. Keep "variants must not create separate documents". Position (c)
  is not supported for code-owned facts.
- **AXIS-REJECTED-ALT.** The evidence favours (c), recording inline only the
  alternative a later editor would plausibly reintroduce. Sun et al. weaken (b):
  commit messages carry mostly Goal, and fresh readers do not consult issues, PRs or reviews.
  Both remain hypotheses until #19 reports.
- **A possible audit duty, untested:** flag code facts duplicated in instruction
  files (P-26), since half of those files never change.

### #19's arms

- **Hold layers 1 and 2 constant across arms.** Give every arm the same
  instruction file, intent document and any ADRs. Otherwise arm B (docs folder)
  could win simply by also acting as a decision log. Specify in advance what arm
  B's folder may hold.
- **Tag each sequence step by knowledge type:** local constraint, local rejected
  alternative, cross-module decision, instruction. Pre-register the predictions:
  inline is at least as good as docs on local facts; docs or hybrid at least as
  good on cross-module facts; no difference on instruction facts. A placement
  effect that does not vary by type would undercut the boundary above.
- **Make arm D concrete** as the proposed boundary (inline for code-owned facts,
  documents for cross-module ones) rather than "both everywhere".
- **Contamination.** Claude Code auto memory is shared across all worktrees of one
  repository and loads in every session. Disable it for writer and reader runs
  (`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` or `autoMemoryEnabled: false`), and
  exclude Copilot Memory. Log which context files each reader opened (MemUse).
- **Drift steps** should score stale claims per layer, including the instruction
  file.

### Corpus (#8)

ADR-using repositories from the Buchgeher and ICSA datasets are a candidate pool
for real cross-module decisions with dated availability. Include cases whose
rationale lived only in code review or issues (Sun), so capturing it inline is
tested against a realistic baseline.

## 5. Search log

Queries (2026-11-07): `architecture decision records open source GitHub mining
study adoption`; `GitHub Copilot agentic memory citations verify against code
expire`; `empirical study agent context files CLAUDE.md AGENTS.md content`;
`architectural knowledge vaporization design rationale lost empirical survey`;
`Buchgeher architecture decision records ... number of repositories`;
`developers rationale where documented commit messages code comments issue
tracker`; `Lore git commit trailers decision context AI coding agents`;
`Codified Context infrastructure AI agents`; `Cursor removed Memories feature`;
`Decomposing the rationale of code commits`; `architecture decision records as
context for LLM coding agents evaluation`; `LaToza Myers hard-to-answer questions
about code`. Pages fetched: those linked above.

Excluded, with reasons:
- Secondary coverage of Copilot Memory (devops.com, CloudThat, Unblocked,
  dev.to). Used only as leads; GitHub's own documentation replaced them.
- The knowledge-vaporization literature (Jansen & Bosch, the Tofan thesis surveys,
  Carignano et al.). Seen only as search summaries; not read.
- LaToza & Myers. Full text not accessed.
- ADR-generation papers ([2604.03826](https://arxiv.org/pdf/2604.03826),
  [2403.01709](https://arxiv.org/abs/2403.01709),
  [2602.04445](https://www.arxiv.org/pdf/2602.04445)) and an Equal Experts blog.
  They concern generating ADRs, not layering or downstream outcomes.
- The QAC commit spec. A blog post, not a primary source.
- Pages that could not be fetched: the Al Safwan ACM page (403; the author's PDF
  was used instead), DOAJ (403; Buchgeher sample size unverified), and Cursor's
  changelog (not found; the staff forum reply was used).
- No benchmark was found that measures whether giving ADRs to a coding agent
  improves its changes.
