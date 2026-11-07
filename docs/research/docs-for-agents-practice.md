# Docs for agents in practice: do they help, and do they drift?

Research date: 2026-11-07, for issue #30 (R1). This targeted web review asks whether
AI-generated or AI-maintained documentation kept beside code makes coding agents
more reliable on larger projects, and whether teams report the two-sources-of-truth
drift described in `intent.md`. It extends three earlier reports and does not repeat
them:

- [Coding-agent evidence](agent-context-evidence.md), section 6, covers Gloaguen et
  al.'s AGENTS.md evaluation.
- [Related systems](related-systems-and-researchers.md) covers RepoAgent, DeepWiki,
  Code Wiki, memory systems and Keep the Why.
- [Context layers](context-layers.md) (#33) covers Codified Context, the two
  AGENTS.md mining studies, and the Claude Code, Copilot and Cursor memory features.

No experiment was run. Evidence types: **measured** (experiment or mining study
with a stated method), **survey**, **practitioner report**, **vendor claim**
(including product documentation).

## 1. Question and bottom line

Practitioners widely report that repository docs written for agents help on larger
projects. Real teams have built elaborate `docs/` structures for this. The **measured**
evidence for better task success is weak:

- Two controlled studies of context files find no measurable gain in correctness.
- One study finds a gain in speed.
- One small preprint, without significance tests, finds that freshly generated
  repository documentation added about 9 points on 57 issues.

Teams that keep docs folders report drift almost everywhere. One study has now measured
its harm on current agents. **Stale instruction files beat the existing code in 90% of
convention choices**, even when the agent noticed the conflict. A single sentence giving
the code precedence reversed this.

No source measures an AI-maintained docs folder over a sequence of changes, or
compares it with equivalent inline comments. That comparison remains #19's job. The
claim that weaker models benefit more rests on one small exploratory preprint.

## 2. Findings

### A. How real teams structure docs for agents

| Source | Structure | How it is kept fresh | Evidence |
|---|---|---|---|
| OpenAI Codex team, "Harness engineering" (Lopopolo, Feb 2026) | A root `AGENTS.md` of about 100 lines that works as a table of contents, plus `ARCHITECTURE.md`. Under `docs/`: `design-docs/` (an index and core beliefs), `exec-plans/active` and `completed`, a tech-debt tracker, `product-specs/`, `generated/db-schema.md`, and `references/*-llms.txt` for dependencies | Linters, CI jobs and a recurring "doc-gardening" agent that opens fix-up PRs | Practitioner report. **The original returned HTTP 403.** The layout comes from two secondary summaries that agree: [agent-harness wiki](https://ericfode.github.io/agent-harness-wiki/raw/articles/openai-harness-engineering), [ai-playbooks review](https://ai-playbooks.pages.dev/reviews/harness-engineering-leveraging-codex-in-an-agent-first-world) |
| [Codified Context](https://arxiv.org/html/2602.20478) (v1, 2026-02-24) | Three tiers for a 108k-line C# project ([context layers](context-layers.md)). 34 on-demand specs; tier 3 is about 16,000 lines, including a ~1,600-line retrieval service; the whole setup is about 24% of the code's size | Same-session updates, a review every two weeks and a file-to-spec drift detector: about **1–2 h a week**, the only quantified upkeep bill found | Practitioner report (one developer, observational, "No causal relationships are claimed") |
| [Cline Memory Bank](https://docs.cline.bot/best-practices/memory-bank) | Six files (`projectbrief`, `productContext`, `activeContext`, `systemPatterns`, `techContext`, `progress`), all read at every task start | An "update memory bank" command reviews every file | Vendor documentation; no outcome data |
| Spec-driven tools ([Böckeler, 2025-10-15](https://www.martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)) | Kiro: steering files (`product.md`, `tech.md`, `structure.md`) plus per-feature requirements, design and tasks. spec-kit: a `constitution.md` plus a spec folder per change. Tessl: a spec per code file, with generated code marked "GENERATED FROM SPEC - DO NOT EDIT" | Böckeler judged Kiro and spec-kit "spec-first" in practice: specs serve one change and are not maintained | Practitioner report (hands-on trial) |
| [spec-kit "persisting specs" guide](https://github.com/github/spec-kit/blob/main/docs/how-to/persisting-specs.md) (last changed 2026-11-06) | Four post-delivery models, none the default: flow-back, flow-forward (immutable history), living spec, and constitution-only. **Spec Kit's own repository tracks only the constitution and gitignores `specs/`** | Flow-back's stated "main risk is silent divergence". Maintainers closed [#4940](https://github.com/github/spec-kit/issues/4940) (Oct 2026) without adding a core step to update specs when the code is right; deciding which side is right stays a human choice | Vendor documentation |
| [Claude Code best practices](https://code.claude.com/docs/en/best-practices) (read 2026-11-07) | `CLAUDE.md` should hold only what Claude "couldn't work out from the code itself": test commands, misleading code, decisions not in the repo, and repeated corrections. Under 200 lines, with path-scoped rules and skills for anything larger | `/doctor prompt-audit` flags instructions that point at missing files or contradict each other | Vendor claim |
| [HumanLayer](https://www.humanlayer.dev/blog/writing-a-good-claude-md) (2025-11-25) | Under 300 lines, plus an `agent_docs/` folder | `file:line` pointers, not copied snippets that go stale | Practitioner opinion |

The pattern is consistent. A short, always-loaded root file acts as a map, and deeper
docs are read on demand. Whatever can be derived (schemas, wikis) is generated, not
hand-maintained. Vendor guidance tells authors to **leave out what the code already
shows**. That is the user's third layer: documentation of what the code does.

### B. What the files contain and how they evolve (measured, descriptive)

[Context layers](context-layers.md) reports the content figures: architecture
appears in 68.1% of 2,303 files, and 50% of 155 AGENTS.md files were never edited.
Three further points:

- **Edits mostly add.** In [Agent READMEs v2](https://arxiv.org/html/2511.12884v2)
  §4.2, 59–67% of files were edited more than once, with a median gap of 22–68
  hours. Median deletions were under 15 words per commit; deletions accounted for 19 of
  139 change labels in a 100-commit sample.
- **Defects are common.** [dos Santos et al.](https://arxiv.org/abs/2606.15828)
  (SCAM 2026) find at least one smell in 91% of 100 popular files: "Context Bloat"
  in 42%, with "Conflicting Instructions" co-occurring.
- **Accuracy is not measured.** No mining study checks whether a statement still
  matches the code. Mohsenimofidi et al. name code–context co-evolution as future
  work.

### C. Measured effects on agent outcomes

- **Context files, correctness.**
  - Gloaguen et al. found null or small effects at about 20% higher cost
    ([existing review §6](agent-context-evidence.md#6-repository-context-files-change-behavior-without-proven-general-success-gains)).
  - [Khatri, REALM 2026](https://aclanthology.org/2026.realm-1.5/) (ACL workshop,
    Oct 2026; **measured**) ran Claude Code and Codex on 17 real tasks from 3
    repositories (288 runs). The context strategy produced **no measurable change in
    correctness**. Its 10–15-point equivalence bound is descriptive, "not a powered
    equivalence claim": the stated minimum detectable effect is ">>30pp", and Claude
    Code ran 15 of the 17 tasks. *(Corrected after the [2026-11-07 citation audit](audits/2026-11-07-r1-r4-citation-audit.md).)* A real AGENTS.md never turned a near-miss into a pass. Failures were
    traced to "feature design, pattern selection, exact wiring", not to missing
    repository knowledge.
- **Context files, efficiency.** [Lulla et al.](https://arxiv.org/html/2601.20404v2)
  (arXiv v2, 2026-03-30; **measured**) ran gpt-5.2-codex on 124 small PRs from 10
  repositories, with and without AGENTS.md. **Median wall-clock time fell 28.6%** and
  median output tokens fell 16.6% (Wilcoxon p<0.05). Correctness was not measured.
- **Generated repository documentation.**
  [Wang et al., SWD-Bench](https://arxiv.org/html/2604.06793) (arXiv v1, 2026-04-08;
  **measured**) gave SWE-Agent the top 4,096 tokens of retrieved documentation on 57
  SWE-bench Verified issues. Resolution rose from **43.86%** (code retrieval only) to
  **52.63%** with RepoAgent docs and **47.37%** with DeepWiki; the headline "+20%" is
  relative. No significance test was reported, each issue is worth about 1.75
  points, and docs generated from the same snapshot had zero drift: a best case.
- **Pointers to docs the model has not seen.**
  [Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)
  (Gao, 2026-01-27; **vendor claim**; eval count and models undisclosed) tested
  Next.js 16 APIs absent from training data. Pass rates: no docs 53%; a docs skill
  53% (not invoked in 56% of cases); the skill with explicit instructions 79%; an
  8 KB AGENTS.md index pointing to local doc files **100%**. The lesson is
  **discoverability**: an always-loaded pointer beat optional retrieval. The content
  was external API documentation, not a description of the repository's own code.
- **llms.txt.** [Lance Martin](https://rlancemartin.github.io/2025/04/03/vibe-code)
  (2025-04-03; practitioner report, Claude 3.7 era) ran one round of five LangGraph
  challenges. An LLM-rewritten llms.txt beat a vector store, a standard llms.txt and
  full-doc stuffing. **No measured evidence was found for llms.txt describing a
  project's own code.**
- **Architecture docs and model capability.**
  [Canedo, *Architecture as Capability Equalizer*](https://arxiv.org/html/2608.21747v1)
  (arXiv v1, 2026-08-22; **measured**, exploratory) ran 90 trials: 5 specification
  formats × 6 models × 3 runs, building a TypeScript API from an empty directory.
  Format barely mattered for Sonnet 4.6 and GPT-5. For weaker models,
  code-proximate formats (OpenAPI, TypeScript contracts) recovered most of the gap;
  the weakest model's route coverage rose from 33% to 100%. Without any guidance,
  Sonnet's judge score was 5.08, against 8.42 with prose (n=3 each). Limits:
  greenfield only, an LLM judge, no statistical tests, pre-current models.

### D. Stale documentation and drift

- **Stale instruction files override the code.**
  [Xu & Wu](https://arxiv.org/html/2610.30571v1) (arXiv v1, 2026-10-22, submitted to
  *SN Computer Science*; **measured**) built 40 small synthetic Python projects. In
  each, `CLAUDE.md`/`AGENTS.md` asked for one convention while the code used another.
  The agents were Claude Code 2.1.302 with Sonnet 5.5 and Codex CLI 0.163.0 with
  GPT-6 Sol, over 320 runs.
  - **90.1% of 720 convention choices followed the stale file; 4.2% followed the
    code.** Claude Code named the conflict in 79 of 80 runs and followed the file
    anyway. Codex rewrote existing code in 20 of 80 runs, breaking tests in 17.
  - A user-level sentence (follow the existing code's conventions; report
    inconsistencies) raised code-following to 91.4% and test passes from 89.4% to
    100%. The authors' explanation: the file arrives as an instruction, the code as
    tool output.
  - Limits: conventions, not behavior; synthetic projects; each task in a single unattended run (two runs per project,
    agent and condition; 86.4% of Claude Code and 93.9% of Codex choices followed the file); auto-loaded
    files, not a docs folder read with tools.
- **Incorrect comments mislead too.** Incorrect docstrings harm results (Macke and
  Doyle), and *When Comments Mislead* reports the same for stale comments
  ([expanded review](comment-context-deep-dive.md#stale-or-defective-annotations-can-transmit-the-wrong-behavior),
  abstract only). Staleness is a hazard for any placement, not only for docs folders.
- **Codified Context** calls staleness its "primary failure mode". In one case, a
  spec mentioning legacy stat fields led the agent to route damage through a
  deprecated path, which was caught only in testing (see
  [context layers](context-layers.md)).
- **A team that generated docs with almost every change.**
  [devjiro, DEV](https://dev.to/devjiro/we-pushed-claude-to-generate-as-much-documentation-as-possible-and-it-backfired-4ifg)
  (posted Feb 22, year not shown; practitioner report, no numbers) asked Claude for
  READMEs, ADRs, API references and runbooks alongside nearly every change. The docs
  crowded code out of the context window, went stale unflagged, and described the
  same module in conflicting ways, so developers stopped trusting them. Verdict:
  stale docs were "worse than no documentation at all". The fix was one source of
  truth per module linked from the code, doc updates in the same PR, and audits
  that delete outdated docs. This is the closest match found to the user's own
  practice, and to its failure.
- **Spec-driven development.** Böckeler saw spec-kit's agent ignore research notes
  about existing classes and regenerate duplicates. She wrote: "I'd rather review
  code than all these markdown files." The
  [Thoughtworks Radar](https://www.thoughtworks.com/radar/techniques/spec-driven-development)
  (Nov 2025, "Assess") warns of hard-to-review spec files and a possible "bitter
  lesson": hand-crafting detailed rules for AI does not scale.

### E. How teams manage drift (reported mechanisms)

1. **Shrink and point.** Keep the always-loaded file small and link instead of
   copying (Anthropic, HumanLayer, OpenAI).
2. **Generate what is derivable.** Examples are OpenAI's `docs/generated/`, plus Code
   Wiki, DeepWiki and Doxygen
   ([related systems](related-systems-and-researchers.md)).
3. **Update in the same change** (devjiro, Codified Context).
4. **Detect mechanically.** Examples: a file-to-doc drift detector (Codified
   Context), linters, CI and a doc-gardening agent (OpenAI), and the dead-reference
   audit (Anthropic).
5. **Give the code precedence.** State that code wins and that conflicts must be
   reported (Xu & Wu, measured).
6. **Retire instead of maintaining.** spec-kit's constitution-only and flow-forward
   models.

None of these mechanisms comes with outcome data showing that drift actually stays
low. Only one, the precedence sentence, has a measured effect on behavior.

## 3. Counterevidence and limits

- **The strongest controls are null.** The positive measured results are efficiency
  (Lulla), information missing from code and training data (Vercel), or small and
  without significance tests (SWD-Bench, Canedo). The two controlled correctness studies, Gloaguen and
  Khatri, show no reliable gain.
- **Practitioner successes are uncontrolled.** They come from the people who built
  the systems and are confounded by learning over time. Codified Context says so
  explicitly.
- **Different objects.** Context files are not docs folders. Mining studies count
  edits, not accuracy. Measured stale-doc harm covers conventions in auto-loaded
  files. A docs folder read through tools reaches the model as tool output, like code
  and inline comments, and the precedence effect may not carry over. **Untested.**
- **Where the evidence complicates the user's intuition:**
  - *The third layer is the one vendors say to cut.* Vendor guidance and the
    Gloaguen redundancy result both say restating what the code shows adds cost
    without benefit. That argues against plain what-the-code-does description **in
    either placement**. The user's docs folder may help through facts the code does
    not show (relationships, constraints, external APIs), not through description.
  - *Agents drift too, not only humans.* Half of AGENTS.md files are never edited,
    and in the devjiro case Claude wrote the docs. Without enforcement, neither an
    AI-maintained folder nor a skill escapes drift. This supports the drift premise
    but weakens the claim that humans are the main failure.
  - *Capability.* Canedo supports larger gains for weaker models, but from
    **code-proximate contracts**, not prose. The frontier-agent nulls (Gloaguen,
    Khatri) do not contradict the idea that frontier models need docs less.
  - *Placement.* No evidence either way. Vercel shows that discoverability matters,
    but the winner was a central index, not text placed beside the code.
- **Dates and coverage.** Lance Martin, Vercel and Canedo predate the current
  frontier; Xu & Wu, Khatri and Lulla use recent agents. The search was English and
  non-systematic, and several primary pages were blocked.

## 4. Implications

### For #19 (inline skill vs AI-maintained docs folder vs code only)

1. **Give the docs arm a realistic layout and policy, not a bare folder.**
   - **Layout:** a root AGENTS.md of 100–200 lines serving as an index; an
     `ARCHITECTURE.md`; per-subsystem docs whose index maps each doc to source
     paths; derivable material (schemas) regenerated, not edited.
   - **Upkeep:** the editing agent updates affected docs in the same change, plus a
     gardening pass at a fixed interval.
   - **Two variants if budget allows:** *as practised* (the user's current folder)
     and *best practice* (adding the file-to-doc map and a drift-detector warning).
     An inline win over the first alone could be dismissed as beating a straw man.
2. **Control the precedence instruction.** One sentence moved convention-following
   from 4% to 91%. Use the same code-wins sentence in every arm, or vary it as a
   factor. Otherwise an arm difference may reflect the instruction channel, not
   placement.
3. **Record the injection channel and exposure.** For each arm, record whether docs
   were auto-loaded or retrieved, and log whether the next agent actually read the
   relevant doc or comment, as recommended in the MemUse lesson in
   [related systems](related-systems-and-researchers.md).
4. **Measure drift as an outcome.** Count stale or contradictory claims per
   transition in each arm, plus the tokens and time spent on upkeep. Seed stale
   conditions with both convention conflicts (as in Xu & Wu) and behavior or
   relationship conflicts (untested so far).
5. **Hold equal facts, weighted toward what code cannot show.** Pure description of
   behavior is predicted to add little in either arm. Treat code-proximate
   contracts (types, tests) as a recorded confound or a possible reference arm,
   given Canedo's weaker-model result.
6. **Plan power for small effects.** With 288 runs, Khatri could not detect effects
   below about 30 points; its ±10–15-point bound is descriptive only. Follow the
   [evaluation protocol](evaluation-protocol.md)'s cluster-aware design.

### For the corpus (#8)

- Prefer repositories whose docs folders or AGENTS.md files co-evolve with the code
  in history, so that real stale passages can be mined as natural fixtures. Candidate
  sources: the Agent READMEs and Mohsenimofidi samples, and CTXbench's 12 repositories
  with developer context files
  ([benchmark landscape](benchmark-landscape.md)).
- The [Codified Context companion repository](https://github.com/arisvas4/codified-context-infrastructure)
  provides example specs and a retrieval server, but not the game's source. Treat it
  as a template for the docs arm. Its license was not checked.
- Keep external-API cases like Vercel's separate. They test missing knowledge, not
  the code's own description.

## 5. Search log

Queries run on 2026-11-07 (WebSearch, standard mode), abbreviated: `empirical
study AGENTS.md context files`; `OpenAI harness engineering AGENTS.md docs folder
doc-gardening`; `stale documentation misleads coding agents`; `Context Engineering
for AI Agents in Open-Source Software`; `Vercel AGENTS.md outperforms skills`;
`"Codified Context"`; `Böckeler spec-driven development Kiro spec-kit Tessl`; `Cline
memory bank`; `llms.txt effect on coding agents`; `generated repository
documentation SWE-bench`; `Claude Code best practices CLAUDE.md`; `"stale docs"
"worse than no docs" benchmark`; `agent context files co-evolution drift`;
`spec-driven development empirical evaluation`; `architecture documentation coding
agent with and without`; `effective harnesses for long-running agents`;
`Thoughtworks Radar spec-driven development`; `inline comments versus separate
documentation placement experiment`; `context rot Chroma`; `AIDev documentation
updates`; `docs folder drift practitioner`; `memory bank stale abandoned`; `DORA
2025 AI-accessible internal data`. Also `gh search issues` in `github/spec-kit`
and its persistence guide via `gh api`.

Excluded or downgraded:

- **OpenAI "Harness engineering" original:** HTTP 403. Only secondary summaries
  were used, and they are labelled as such.
- **Towards AI "fact-check their own documentation"** (3,250 trials; stale docs
  reported worse than none): HTTP 403, an author with a stated conflict of
  interest, and no inspectable method. A related Reddit dataset post could not be
  verified. Excluded.
- **Roo Code, "Codebase Indexing Beats Memory Banks"** (vendor argument): only a
  preview mirror and search snippets were reachable; the page returned 404.
  Excluded.
- **Chroma "Context Rot":** the primary report was not fetched, and it concerns long
  context in general rather than docs. Excluded.
- **DORA 2025 capabilities model:** survey evidence was found only through secondary
  summaries and not verified. Excluded.
- **Not used:** a Cline subreddit thread, "Should we deprecate Memory Bank?"
  (reachable only through a mirror; authorship unclear); Anthropic's long-running
  harness post (progress files, not code documentation; no ablation); Google
  spec-driven test generation (arXiv 2608.17177; talk abstract only); Kuissi et al.
  (retrieval-benchmark drift, not agents); vendor marketing for doc-freshness tools
  (Unblocked, Swimm, MeetLess); SEO guides to llms.txt.
