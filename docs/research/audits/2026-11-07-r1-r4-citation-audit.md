# Citation audit of research reports R1–R4

Audit date: 2026-11-07, for issue #29. The auditor was an independent agent that
did not write any of the four reports. Scope:

- R1 [docs-for-agents-practice.md](../docs-for-agents-practice.md)
- R2 [capability-gradient.md](../capability-gradient.md)
- R3 [human-maintenance-and-drift.md](../human-maintenance-and-drift.md)
- R4 [context-layers.md](../context-layers.md)

Also covered: the claims these reports feed into `docs/journey.md` §7 and
`docs/evaluation/report-2026-11-07.md` §6.

**Method.** For each report I chose the claims that carry its bottom line or that
are quoted downstream. I then fetched each primary source: the arXiv abstract page
for metadata, plus the arXiv HTML, the ACL Anthology page, the author PDF or the
vendor page for the numbers. PDFs were converted to text with `pdftotext` and
searched. Some table values came through a web-fetch tool's extraction. Where a
number mattered, I checked it against a second source in the paper (abstract, body
text or a recomputation), and I recomputed the SkillsBench Spearman correlation
myself. I did not edit the four reports.

Verdicts:

- **VERIFIED:** the source exists and matches.
- **MINOR ISSUE:** rounding, a mislabel or a missing caveat that does not change
  the conclusion.
- **MISREPRESENTED:** the source says something materially different.
- **NOT FOUND:** the source could not be located, or appears fabricated.
- **UNREACHABLE:** the source could not be fetched.

## Summary

| Report | Claims checked | VERIFIED | MINOR ISSUE | MISREPRESENTED | NOT FOUND | UNREACHABLE |
|---|---|---|---|---|---|---|
| R1 docs-for-agents-practice | 9 | 5 | 4 | 0 | 0 | 0 |
| R2 capability-gradient | 8 | 5 | 3 | 0 | 0 | 0 |
| R3 human-maintenance-and-drift | 8 | 8 | 0 | 0 | 0 | 0 |
| R4 context-layers | 8 | 6 | 1 | 1 | 0 | 0 |
| **Total** | **33** | **24** | **8** | **1** | **0** | **0** |

**Every source checked exists.** Each arXiv ID that looks like a 2026 ID resolves
to a real paper whose title and authors match the citation:

- 2610.30571 (Xu & Wu, v1 2026-10-22)
- 2604.10345 (Sun et al., v1 2026-04-11; now at v2, 2026-07-29)
- 2602.12670 (SkillsBench, v4 2026-06-14)
- 2602.20478 (Vasilopoulos, *Codified Context*, v1 2026-02-24)
- 2511.12884 (Chatlatanagulchai et al., *Agent READMEs*, v2 2026-08-09)
- 2607.27250 (Khatri)
- 2608.21747 (Canedo)
- 2604.06793 (Wang et al., SWD-Bench)
- 2608.20195 (Gao & Chen)
- 2607.08885 (Kaufman et al.)
- 2604.02547 (Mehtiyev & Assunção)
- 2609.09242 (Pan et al.)
- 2606.15828 (dos Santos et al.)
- 2602.07609 (Su et al.)
- 2602.11988 (Gloaguen et al.)
- 2601.20404 (Lulla et al.)

No fabricated source was found. The only **MISREPRESENTED** item is R4's account of
*where* Sun et al. found rationale components.

## Per-claim detail

### R1: docs-for-agents-practice.md

**R1-1. Stale instruction files override the code (Xu & Wu).** MINOR ISSUE.
- **Where the claim appears:** bottom line ("Stale instruction files beat the
  existing code in 90% of convention choices"), §2.D, and implication 2. Quoted in
  journey §7 ("90% of the time").
- **Source:** Xiaonan Xu and Wenjing Wu, "Stale Instruction Files Override the Code
  in Coding Agents: A One-Sentence Fix", arXiv 2610.30571v1, 2026-10-22. The comments
  field says "Submitted to SN Computer Science".
- **Existence:** confirmed; the ID, title and authors match.
- **Numbers:** all match:
  - 40 Python projects, 320 runs, 720 choices per condition;
  - 90.1% (649/720) followed the file and 4.2% followed the code;
  - Claude Code named the conflict in 79 of 80 runs;
  - Codex rewrote code in 20 of 80 runs, and tests failed in 17 of those;
  - with the precedence sentence, 91.4% followed the code;
  - test passes rose from 89.4% to 100%;
  - Claude Code 2.1.302 with Sonnet 5.5, and Codex CLI 0.163.0 with GPT-6 Sol.
- **Characterization:** fair. One error: the limits list says "single runs", but the
  paper ran each project twice per agent and condition. What the paper means by
  "single" is that each task was completed in *a single unattended run*, with no
  user interaction. The per-agent split (Claude Code 86.4% and Codex 93.9% followed
  the file) is not reported and would be useful.

**R1-2. Khatri, REALM 2026: no measurable correctness change.** MINOR ISSUE.
- **Where the claim appears:** bottom line ("Two controlled studies ... no
  measurable gain"), §2.C, §3, and implication 6. Quoted in journey §7 ("controlled
  studies ... found no correctness gain").
- **Source:** Prakhar Khatri, "Do Context Files Help Coding Agents? A Two-Agent
  Ablation Study on Real Repositories", REALM 2026 (ACL Anthology
  2026.realm-1.5, pp. 57–67). Also on arXiv as 2607.27250v1.
- **Existence:** confirmed.
- **Numbers:** these match: 17 tasks, 3 repositories, 288 runs, no measurable change
  in correctness, an equivalence bound of about 10–15 pp, the AGENTS.md
  near-miss probe, and the quote "feature design, pattern selection, exact wiring".
- **Characterization:** two caveats are missing.
  1. Claude Code ran only 15 of the 17 tasks.
  2. The paper calls its TOST bound descriptive and "not a powered equivalence
     claim". It says the minimum detectable effect is ">>30pp": a 30 pp effect is
     detected only 57% of the time.

  R1 implication 6 ("could only bound the effect to ±10–15 points") therefore
  overstates the precision. R2 §3 reports the >30 pp minimum detectable effect
  correctly, so the two reports disagree on how precise this study is.

**R1-3. Lulla et al.: AGENTS.md reduces time and tokens.** VERIFIED.
- **Where the claim appears:** §2.C and §3. It also appears in R2 §2.4.
- **Source:** Lulla, Mohsenimofidi, Galster, Zhang, Baltes and Treude, "On the
  Impact of AGENTS.md Files on the Efficiency of AI Coding Agents", arXiv
  2601.20404v2, revised 2026-03-30.
- **Numbers:** match: gpt-5.2-codex, 124 PRs, 10 repositories, a median wall-clock
  drop of 28.64%, a median output-token drop of 16.58%, and Wilcoxon p<0.05.
- **Characterization:** fair. "Correctness was not measured" is accurate: the
  authors manually checked only 50 sampled tasks for non-trivial output.

**R1-4. SWD-Bench: generated docs add about 9 points on 57 issues.** VERIFIED.
- **Where the claim appears:** bottom line, §2.C and §3.
- **Source:** Wang, Hu, Gao, Gao and Peng, "Evaluating Repository-level Software
  Documentation via Question Answering and Feature-Driven Development", arXiv
  2604.06793v1, 2026-04-08.
- **Numbers:** match:
  - 57 SWE-bench Verified issues, SWE-Agent, and the top 4,096 tokens of documentation;
  - 43.86% with code retrieval only, 52.63% with RepoAgent docs, 47.37% with
    DeepWiki docs;
  - the "20.00%" headline is described in the body as a "relative issue-solving
    improvement";
  - no significance test (three repeats, averaged).
- **Characterization:** fair.

**R1-5. Canedo, *Architecture as Capability Equalizer*.** VERIFIED.
- **Where the claim appears:** §2.C, §3 and implication 5. The bottom line's "one
  small exploratory preprint" refers to this paper.
- **Source:** Arquimedes Canedo, arXiv 2608.21747v1, 2026-08-22.
- **Numbers:** match:
  - 90 trials: 5 formats × 6 models × 3 runs;
  - Gemini 2.5 Flash route coverage was 33% with prose and 100% with TypeScript
    contracts;
  - Sonnet 4.6 scored 5.08 with no guidance and 8.42 with prose;
  - LLM judge, no significance tests.
- **Characterization:** fair. One clarification: the 33% baseline is the *prose*
  arm, not "no spec".

**R1-6. *Codified Context*: structure, upkeep and staleness.** MINOR ISSUE.
- **Where the claim appears:** §2.A table and §2.D. It is also used in R2 §2.5 and
  R4 §2.A.
- **Source:** Aristidis Vasilopoulos, "Codified Context: Infrastructure for AI
  Agents in a Complex Codebase", arXiv 2602.20478v1, 2026-02-24.
- **Numbers:** these match:
  - 108,256 lines of C#;
  - 34 on-demand specs;
  - about 24.2% of the code's size;
  - "approximately 1–2 hours per week";
  - "No causal relationships are claimed";
  - "Specification staleness was the primary failure mode";
  - the legacy-stat-fields incident, which "only surfaced during testing".
- **Characterization:** the "about 16,000 lines" figure for the 34 specs is the
  paper's ~16,250-line Tier 3 total, which *includes* a ~1,600-line Python retrieval
  service. The specs alone are nearer 14,600 lines. The paper also says the 24%
  ratio is "not a target or finding".

**R1-7. *Agent READMEs*: edits mostly add.** MINOR ISSUE.
- **Where the claim appears:** §2.B.
- **Source:** Chatlatanagulchai et al., arXiv 2511.12884v2, 2026-08-09.
- **Numbers:** these match:
  - 59.4–67.0% of files were modified in more than one commit;
  - median gaps were 22.3 h (Codex), 23.8 h (Claude Code) and 68.0 h (Copilot);
  - median deletions were under 15 words per commit.
- **Characterization:** "19 of 100 sampled commits removed anything" is not what
  the paper reports. The paper reports 19 *deletion labels* among 139 label
  assignments across 100 commits (15 line-level and 4 section-level). That is not a
  count of commits.

**R1-8. dos Santos et al.: smells in 91% of files.** VERIFIED.
- **Where the claim appears:** §2.B.
- **Source:** dos Santos, Costa, Montandon, Silva and Valente, "Configuration Smells
  in AGENTS.md Files", arXiv 2606.15828 (v5), SCAM 2026.
- **Numbers:** match. The paper states: "We detected at least one smell in 91 agent
  configuration files." Context Bloat appears in 42%, and the abstract says Context
  Bloat co-occurs with Conflicting Instructions.

**R1-9. Vercel: an AGENTS.md index scores 100%.** VERIFIED.
- **Where the claim appears:** §2.C and §3.
- **Source:** Jude Gao, Vercel blog, 2026-01-27.
- **Numbers:** match: 53% with no docs, 53% with the skill, 79% with the skill plus
  explicit instructions, and 100% with an 8 KB index; the skill was not invoked in
  56% of cases; Next.js 16 APIs; the eval count and models are undisclosed.
- **Characterization:** fair, and R1 labels it as a vendor claim.

### R2: capability-gradient.md

**R2-1. SkillsBench: frontier gains of about 16–20 pp, and gain uncorrelated with
baseline.** MINOR ISSUE.
- **Where the claim appears:** bottom line, §2.1 and §2.4. It supports journey §7
  ("frontier models gain a lot from knowledge the code doesn't contain").
- **Source:** Li et al., "SkillsBench: Benchmarking How Well Agent Skills Work
  Across Diverse Tasks", arXiv 2602.12670v4, 2026-06-14.
- **Numbers:** every Table 2 cell cited matches:
  - Flash Lite 16.0→20.1, MiniMax M2.7 18.1→34.9, GPT-5.4 Mini +11.5;
  - Codex with GPT-5.5 46.8→66.5, Claude Code with Opus 4.7 43.0→61.2, OpenHands
    with Opus 4.8 +8.4;
  - self-generated Skills: −8.1, −11.3 and −11.5;
  - comprehensive docs +0.7 against +19.0 and +21.5 for focused Skills;
  - 13 of 87 tasks got worse;
  - software engineering 37.6→49.2;
  - the quotes "displace a stronger default strategy" and "are not always the
    largest beneficiaries".

  I recomputed Spearman ρ over all 18 rows: **−0.094** (p=0.71). This matches
  R2's "≈ −0.09".
- **Characterization:** the bottom line's "frontier configurations gains of about
  16–20 pp" picks the middle of a wide range. Frontier configurations gained between
  +8.4 (OpenHands with Opus 4.8) and +11.1 (OpenHands with Opus 4.7) at the low end,
  and up to +24.8 (Gemini CLI with Gemini 3.1 Pro) at the high end. SkillsBench is
  also multi-domain, and the software-engineering slice has n=16. The conclusion
  stands, but the range should be stated.

**R2-2. Gloaguen et al., Table 5: per-model effects and cost.** VERIFIED.
- **Where the claim appears:** §2.1, §2.4 and §3. Also used in R1 §2.C and R4 §2.B
  and §3.
- **Source:** Gloaguen, Mündler, Müller, Raychev and Vechev, "Evaluating AGENTS.md:
  Are Repository-Level Context Files Helpful for Coding Agents?", arXiv 2602.11988v3.
- **Numbers:** all eight per-model cells match: +7.9, +1.5, +2.9 and −2.9 for
  developer-written files, and the LLM-generated pairs. The average gain for
  developer-written files on CTXbench is +2.4, p=0.21 (Cochran–Mantel–Haenszel).
  Cost rose about 20% on SWE-bench and 23% on CTXbench for LLM-generated files.
  CTXbench has 138 instances and SWE-bench Lite 300.
- **Characterization:** fair. Note that Table 5 labels the benchmark "Plan-Bench",
  while the text calls it CTXbench.

**R2-3. SWE-Bench Pro: requirements and an interface roughly tripled frontier
success.** MINOR ISSUE.
- **Where the claim appears:** bottom line and §2.1.
- **Source:** SWE-Bench Pro, arXiv 2509.16941v2, Table 3.
- **Numbers:**
  - GPT-5 (high) 8.4→25.9 and Opus 4.1 8.2→22.7, in the capped run (50 turns, $2);
  - the quotes "the class and function names expected by the tests" and "grounded in
    the gold patch and test expectations";
  - reference patches average 4.1 files and 107.4 lines;
  - Haiku 4.5 39.5% and Sonnet 4.5 43.6%.

  All match.
- **Characterization:** the body caveats this well (§2.1 and §3). The bottom line,
  though, cites it as "context that carries knowledge absent from the code" without
  saying that the added context is derived from the gold patch and tests. That
  makes it partly an answer leak. Add the caveat to the bottom line.

**R2-4. Pan et al.: lower baselines gained more inside the weak tier.** VERIFIED.
- **Where the claim appears:** §2.1, §2.4 and implication 1.
- **Source:** Pan, Sun, Zhang, Lo and Du, "Talking to Itself While Coding: What
  Makes Comments Help Code Generation?", arXiv 2609.09242v1, 2026-09-08. The comments
  field says "Accepted to Findings of EMNLP 2026".
- **Numbers:** the mean gains over three sources match: +22.8, +18.1, +15.1 and
  +12.6. Wrong-topic comments cost about 15.3–34.1 pp. The repository replication
  compresses below 12% and near 66.7%. No frontier recipient was tested.
- **Characterization:** fair. Small note: the paper matches baselines per source
  subset, so the single baseline shown per model is the Gemini subset's.

**R2-5. CodeRAG-Bench: below a capability floor, context does nothing.** VERIFIED.
- **Where the claim appears:** §2.1.
- **Source:** CodeRAG-Bench, arXiv 2406.14497v2, Table 5.
- **Numbers:** all match:
  - DS-1000 and ODEX deltas for CodeLlama-7B, StarCoder2-7B, GPT-4o and GPT-3.5;
  - SWE-bench Lite: open models 0.0→≤0.7, GPT-3.5 0.7→6.3, GPT-4o 2.3→30.7;
  - HumanEval: +62.8 and +17.0;
  - the quote "when paired with strong core generation capabilities".
- **Characterization:** fair. The paper's text calls GPT-4o's gain "27.4%", while
  the table difference is 28.4 pp. R2 uses the table value.

**R2-6. CodeCrash: weaker models are misled more.** VERIFIED.
- **Where the claim appears:** bottom line ("weaker models are misled more by wrong
  context") and §2.4.
- **Source:** Lam, Wang, Huang and Lyu, "CodeCrash", arXiv 2504.14119v3. The
  comments field says "NeurIPS 2025".
- **Numbers:** match:
  - GPT-4o 14.0% and 29.1%; GPT-4o-mini 32.6% and 40.4%;
  - Sonnet 3.5 14.4% and 43.4%; Haiku 3.5 27.5% and 53.3%;
  - DeepSeek-R1's maximum drop is 3.5%.
- **Characterization:** fair, with two small points.
  1. o3-mini-high's 28.4% and DeepSeek-R1's figures come from Table 4, not Table 1.
  2. The "2–3× reasoning tokens" applies to *reasoning models* under misleading
     hints, not to Claude 3.5 Sonnet, as the §2.4 sentence order implies.

**R2-7. Khatri arXiv: the per-condition numbers and the minimum detectable
effect.** VERIFIED.
- **Where the claim appears:** §3.
- **Source:** arXiv 2607.27250v1, HTML.
- **Numbers:** match: Claude with Sonnet 4.6 scored 53.3% (none), 55.6%
  (always-on) and 55.6% (selective); the minimum detectable effect is described as
  ">>30pp". This is more accurate than R1's framing of the same study (see R1-2).

**R2-8. Mehtiyev and Assunção: scaffold sensitivity, and the wrong layer in 10 of
12 tasks.** MINOR ISSUE.
- **Where the claim appears:** §2.2 and §2.3.
- **Source:** "Beyond Resolution Rates: Behavioral Drivers of Coding Agent Success
  and Failure", arXiv 2604.02547v1, 2026-04-02.
- **Numbers:** match: 9,374 trajectories, 19 agents; 19.4 pp against 3.8 pp; Opus
  4.5 at 79.2%.
- **Characterization:** three points are loose.
  1. 85–93% per-task agreement across frameworks holds only for Claude 4 Sonnet and
     Opus 4.5. Claude 3.5 Sonnet's agreement is 71%.
  2. "The 12 tasks that no agent solved" is a subset: no agent solved 55 tasks, and
     12 of those have simple patches.
  3. It was the *best agent* that found the right file in 12 of 12 tasks. "Wrong
     layer" is R2's paraphrase of "architectural judgment" (patching a symptom, not
     the root cause).

### R3: human-maintenance-and-drift.md

**R3-1. Tan, Wagner and Treude: outdated references in READMEs and wikis.**
VERIFIED.
- **Where the claim appears:** bottom line and §B. Quoted in journey §7 ("82% of top
  projects had stale doc references at some point").
- **Source:** "Detecting Outdated Code Element References in Software Repository
  Documentation", arXiv 2212.01479 (ar5iv rendering).
- **Numbers:** match:
  - 28.9% of projects currently had an outdated reference, and 82.3% (658/800) had
    one at some point;
  - Google-owned sample: 5.4% and 29.7%;
  - about 55% of fixed references survived more than a month (read from a survival
    curve);
  - still-outdated references were 4.7 years old on average.
- **Characterization:** fair. The detector flags code-element references that no
  longer exist anywhere in the code, which R3 describes as "only deleted
  identifiers".

**R3-2. Gao and Chen: agents touched docs in 37% of code PRs.** VERIFIED.
- **Where the claim appears:** §B and implication 5. Quoted in journey §7.
- **Source:** "From Agent Behaviour to Agent-Friendly Documentation", arXiv
  2608.20195v1, 2026-08-20.
- **Numbers:** match:
  - 33,097 AIDev PRs;
  - 37.0% of the 28,574 code-touching PRs also touched docs;
  - the CI of 24.4–38.9% belongs to the 32.0% all-PR figure, and R3 labels it
    correctly;
  - code came first in 82.5% of split commits;
  - the quote "trails code rather than leading it".

  Docs were identified by path only, and there was no human baseline.
- **Characterization:** fair, including the caveat that 63% is not a drift rate.

**R3-3. *Echoes of AI*: no maintainability penalty.** VERIFIED.
- **Where the claim appears:** bottom line and §D. Quoted in journey §7 ("The one
  controlled trial found no penalty").
- **Source:** Borg et al., arXiv 2507.00788v3, published in *Empirical Software
  Engineering* 31(6), 2026, per the Lund University portal.
- **Numbers:** match:
  - 151 participants completed, out of 449 who were pre-screened;
  - preregistered;
  - phase 2 found "no significant differences in ... completion time or code
    quality" (CodeHealth);
  - data collected from November 2024 to January 2025.
- **Characterization:** fair. Journey §7 compresses this result into "Humans struggle
  to edit AI code *without comments*: not supported yet". The trial did not vary
  comments, so it says nothing about the "without comments" part. R3's own text says
  so; the journey row could too.

**R3-4. Kaufman et al.: assertions study.** VERIFIED.
- **Where the claim appears:** §D and §Counterevidence. Quoted in journey §7
  ("Comments raised confidence more than accuracy").
- **Source:** Kaufman, Brun, Murali and Endres, "Programmers Are Poor and
  Overconfident Judges of LLM-Generated Assertions", arXiv 2607.08885v1, 2026-07-09.
- **Numbers:** match: 86 programmers; exact comments gave no significant accuracy
  gain (p>0.1); under-specified against exact OR 0.58; confidence 4.25 against 3.99.
- **Characterization:** fair. R3 does not name the authors; adding them would help.

**R3-5. Fluri et al.: comments co-change with code (97% and 90%).** VERIFIED at
abstract level.
- **Where the claim appears:** bottom line, §A and §Counterevidence.
- **Source:** WCRE 2007, "Do Code and Comments Co-Evolve? On the Relation between
  Source Code and Comment Changes"; *Software Quality Journal* 17(4), 2009, "Analyzing
  the co-evolution of comments and source code".
- **Numbers:** match the abstracts: 97% of comment changes happen in the same
  revision as the code change; in six of eight systems, code and comments co-evolve
  90% of the time; API changes are re-documented in a later revision.
- **Access:** the dblp page was blocked by bot protection, Springer redirected to
  login, and the RERO record returned 410. The abstracts were confirmed through
  search-result records. R3 already says "checked at abstract level only".

**R3-6. Lethbridge, Singer and Forward 2003.** VERIFIED.
- **Where the claim appears:** bottom line, §B and §Counterevidence.
- **Source:** the IEEE Software PDF, converted to text.
- **Numbers:** match:
  - 25 of 48 survey respondents answered the timing question;
  - "SEs rarely update" documents, and "several weeks after";
  - 44% + 24% = 68% agree documentation is always outdated;
  - 53% + 28% = 81% agree it is still useful;
  - documentation was consulted in "12 times over 357 logged events";
  - code-level comments stay current because they are short and "right there".
- **Characterization:** fair. Small notes: the 68% and 81% are from 45 respondents,
  not 48. The "right there" line is the authors' synthesis in the discussion,
  introduced by "The interviews revealed", and is not a direct interviewee quote.

**R3-7. Roehm et al., ICSE 2012.** VERIFIED.
- **Where the claim appears:** bottom line and §C.
- **Source:** the author PDF, converted to text.
- **Numbers:** match:
  - 28 developers from 7 companies;
  - 21 named code and inline comments as their main source, against 4 for
    documentation;
  - 16 start with code, against 3 with documentation;
  - 17 prefer asking colleagues;
  - "we did not observe a single participant documenting rationale for own code".

**R3-8. Radmanesh et al.: inconsistency is about 1.5× as bug-prone.** VERIFIED.
- **Where the claim appears:** §A.
- **Source:** "Investigating the Impact of Code Comment Inconsistency on Bug
  Introducing", arXiv 2409.10781, 2024-09-16.
- **Numbers:** match: GPT-3.5 labelling; "around 1.5 times more likely"; the effect
  is strongest right after the inconsistency appears.

### R4: context-layers.md

**R4-1. Sun et al.: where rationale lives.** MISREPRESENTED, in part.
- **Where the claim appears:** §2.C, §3 and the AXIS-REJECTED-ALT implication.
  Journey §7 relies on R4 for "The knowledge least often written down is constraints
  and rejected alternatives", although that line rests mainly on Al Safwan.
- **Source:** Sun, Saha, De Silva, Mastropaolo and Chaparro, arXiv 2604.10345v1,
  2026-04-11. The title is "Recovering Fine-Grained Code Change Rationale from
  Multiple Software Artifacts", and a v2 followed on 2026-07-29.
- **Existence:** confirmed. Note that R4's link text, *Fine-grained Multi-Document
  Extraction*, is not the paper's title.
- **Numbers that match:**
  - 63 commits from 5 Java projects;
  - κ = 0.786;
  - inline comments held 3 rationale sentences, 0.4% of 829;
  - class Javadoc held 4 rationale sentences, which is 2.2% of 180;
  - no artifact held Constraints or Dependency.
- **What R4 gets wrong:**
  1. "Alternatives appear mainly in code review." The paper puts Alternatives
     mainly in **issues (60%)**, then pull requests (25%), with code reviews last
     (15%). The v2 abstract says "NEED and ALTERNATIVE appear more often in issues
     and pull requests".
  2. "Every component except Goal appeared only outside commit messages." Need
     also appeared in commit messages, in 10 commits: 8 in both places and 2 in
     commit messages only.
- **Effect on R4's conclusions:** the direction of the inference survives, since
  rationale still sits mostly outside commit messages and outside code. But the
  AXIS-REJECTED-ALT reasoning ("fresh readers do not consult reviews") rests on
  the wrong artifact. It should name issues and PRs.

**R4-2. Al Safwan and Servant, FSE 2019.** VERIFIED.
- **Where the claim appears:** §2.C, §2.D and the boundary table. This feeds journey
  §7 ("least often written down is constraints and rejected alternatives").
- **Source:** "Decomposing the Rationale of Code Commits: The Software Developer's
  Perspective" (the author PDF; DOI 10.1145/3338906.3338979).
- **Numbers:** match:
  - 20 interviews and 24 survey responses;
  - 15 components;
  - rationale is sought "multiple times a week or more often", and hard cases take
    "more than 20 minutes";
  - side effects and alternatives are hardest to find;
  - alternatives, the selected alternative, constraints and maturity stage are
    least often recorded;
  - three interviewees removed alternatives from their model.
- **Characterization:** fair. Strictly, the method is mixed (interviews, then a
  survey), not only a survey.

**R4-3. *Agent READMEs*: what context files contain.** VERIFIED.
- **Where the claim appears:** §2.B and §3. Also used in R1 §2.B.
- **Source:** arXiv 2511.12884v2.
- **Numbers:** match: 2,303 files from 1,925 repositories; testing 75.9%,
  implementation details 70.8%, architecture 68.1%, security 14.8%; the quote
  "frequent, small additions".

**R4-4. Mohsenimofidi et al.: half of AGENTS.md files never changed.** VERIFIED.
- **Where the claim appears:** bottom line, §2.B and §2.D. Also used in R1 §2.B.
- **Source:** "Context Engineering for AI Agents in Open-Source Software", arXiv
  2510.21413v4, MSR 2026.
- **Numbers:** match: 466 projects; 77 of 155 files were never changed; the
  top headings; the quote "short explanations after the rules"; co-evolution named
  as future work.

**R4-5. Copilot Memory: code citations, validation and the A/B test.** VERIFIED.
- **Where the claim appears:** §2.A and §3.
- **Sources:** GitHub Docs, "Copilot Memory"; the GitHub Blog post by Tiferet Gazit,
  "Building an agentic memory system for GitHub Copilot".
- **Numbers:** match:
  - citations to code locations, checked against the current branch;
  - downvoting of wrong memories;
  - a 90-day default expiry;
  - PR merge rate up from 83% to 90%, p<0.00001;
  - no sample size or method details.
- **Characterization:** fair, including the caveat about whether "7%" means
  percentage points. The post displays its date as 15 January 2026, while the URL
  slug says 2026-01-09; R4's "Jan 2026" is right either way.

**R4-6. *Codified Context*: staleness and the deprecated path.** MINOR ISSUE.
- **Where the claim appears:** §2.A and §2.D.
- **Numbers:** these match: the ~660-line constitution, 19 agent specs, 34 specs,
  283 sessions, 108k lines, 1–2 h a week, and the biweekly review.
- **Characterization:** R4 says "at least twice, outdated specs led the agent to
  wire code through a deprecated path". The paper says "On at least two occasions,
  outdated context documents caused agents to generate code that conflicted with
  recent refactors". The deprecated-path wiring is *one* of those occasions.

**R4-7. Claude Code memory documentation.** VERIFIED.
- **Where the claim appears:** §2.A, §2.D and the contamination guidance in §4.
- **Source:** code.claude.com/docs/en/memory and /best-practices, read 2026-11-07.
- **Quotes and settings:** all match:
  - "Claude may pick one arbitrarily";
  - target under 200 lines;
  - auto memory loads its first 200 lines or 25 KB;
  - "Auto memory is machine-local", with all worktrees of a repository sharing one
    directory;
  - `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` and `autoMemoryEnabled: false`;
  - `/doctor prompt-audit`.

  R1's quote "couldn't work out from the code itself" also matches the best-practices
  page.

**R4-8. Su et al.: LLMs detect ADR violations.** VERIFIED.
- **Where the claim appears:** §2.C and the boundary table.
- **Source:** "Evaluating Large Language Models for Detecting Architectural Decision
  Violations", arXiv 2602.07609, 2026-02-07.
- **Numbers and quotes:** match: 980 ADRs from 109 repositories; "explicit,
  code-inferable decisions"; "Accuracy falls short for implicit or
  deployment-oriented decisions".

### Downstream claims in journey §7 and the eval report §6

| Downstream statement | Source claim | Verdict |
|---|---|---|
| "82% of top projects had stale doc references at some point" | R3-1 | Verified |
| "Agents followed a stale instruction file over the actual code 90% of the time" | R1-1 | Verified. "Of convention choices, in synthetic conflicts" would be more precise |
| "Only 37% of agent pull requests that changed code touched docs" | R3-2 | Verified |
| "controlled studies of agent context files found no correctness gain" | R1-2, R2-2 | Verified. The Khatri bound is descriptive, not powered |
| "frontier models gain a lot from knowledge the code doesn't contain" | R2-1, R2-3 | Minor issue. The SWE-Bench Pro context is derived from the gold patch and tests, and the SkillsBench frontier range is 8–25 pp |
| "The one controlled trial found no penalty" | R3-3 | Verified. The trial did not vary comments |
| "Comments raised confidence more than accuracy" | R3-4 | Verified |
| "least often written down is constraints and rejected alternatives" | R4-2 | Verified (Al Safwan) |
| "value comes from knowledge the code doesn't contain" (eval report §6) | R2 and R4 synthesis | A fair reading of the reports. It remains a synthesis, not a measured result |

## Recommended corrections

The coordinator should apply these corrections. In priority order:

1. **R4 §2.C (Sun et al.).**
   - Replace "Alternatives appear mainly in code review" with "Alternatives appear
     mainly in issues (60%) and pull requests (25%); code review holds 15%".
   - Replace "Every component except Goal appeared only outside commit messages"
     with "Apart from Goal and, less often, Need, components appeared only outside
     commit messages".
   - Fix the link text to the real title: *Recovering Fine-Grained Code Change
     Rationale from Multiple Software Artifacts*.
   - Note that a v2 (2026-07-29) exists.
2. **R4 §4, AXIS-REJECTED-ALT.** Change "fresh readers do not consult reviews" to
   "fresh readers do not consult issues, PRs or reviews".
3. **R1 §2.C, §3 and implication 6 (Khatri).**
   - Add that the 10–15 pp equivalence bound is descriptive and "not a powered
     equivalence claim".
   - Add that the paper states a minimum detectable effect of ">>30pp".
   - Add that Claude Code ran 15 of the 17 tasks.
   - Reword implication 6 to match. R2 §3 already has it right.
4. **R2 §1 (bottom line).**
   - Change "about 16–20 pp (SkillsBench)" to "+8 to +25 pp across frontier
     configurations (SkillsBench; most +16 to +20)".
   - Add that the SWE-Bench Pro context is derived from the gold patch and tests.
5. **R1 §2.D (Xu & Wu limits).** Change "single runs" to "each task in a single
   unattended run (two runs per project, agent and condition)". Optionally add the
   per-agent split: 86.4% (Claude Code) and 93.9% (Codex) followed the file.
6. **R1 §2.B (*Agent READMEs*).** Replace "19 of 100 sampled commits removed
   anything" with "deletions accounted for 19 of 139 change labels in a 100-commit
   sample".
7. **R1 §2.A (*Codified Context*).** Change "34 on-demand specs of about 16,000
   lines" to "about 16,000 lines in tier 3, including a ~1,600-line retrieval
   service". Optionally note that the paper calls the 24% ratio "not a target or
   finding".
8. **R4 §2.A (*Codified Context*).** Change "at least twice, outdated specs led the
   agent to wire code through a deprecated path" to "on at least two occasions,
   outdated specs produced code that conflicted with recent refactors; in one, the
   agent wired damage through a deprecated path".
9. **R2 §2.2 and §2.3 (Mehtiyev and Assunção).**
   - State that 85–93% agreement applies to Claude 4 Sonnet and Opus 4.5, with
     Claude 3.5 Sonnet at 71%.
   - State that the 12 tasks are the simple-patch subset of 55 unsolved tasks, and
     that the best agent found the file in all 12.
   - Use "symptom rather than root cause" in place of "wrong layer", or mark "wrong
     layer" as R2's paraphrase.
10. **R2 §2.4 (CodeCrash).** Attach "2–3× reasoning tokens" to reasoning models
    (o3-mini-high, DeepSeek-R1, QwQ), not to Claude 3.5 Sonnet.
11. **R3 §B (Lethbridge).** Optional: note that 68% and 81% are from 45 respondents,
    and that "right there" is the authors' synthesis of the interviews.
12. **Journey §7.** Optional precision edits:
    - "90% of convention choices in synthetic conflicts";
    - "the one controlled trial (which did not vary comments) found no penalty".

No source needs to be removed. Of the 33 claims checked, none relied on a source
that could not be found.
