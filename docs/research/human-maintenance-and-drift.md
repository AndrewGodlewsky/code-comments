# Human maintenance, drift, and editing AI-written code

Research date: 2026-11-07, for issue #32 (R3). This is a targeted primary-source
review, not a systematic one, and no study was rerun. It extends
[comment maintenance and evaluation](comment-maintenance-and-evaluation.md), which
already covers Steidl et al. (2013), Wen et al. (2019) and Nielebock et al. (2019).
Agent-facing evidence lives in [agent-context evidence](agent-context-evidence.md)
and the [expanded review](comment-context-deep-dive.md). Those findings are cited
here, not repeated.

Evidence types: **measured** (experiment or repository mining with a stated
method), **survey** (self-report), **practitioner report**, **vendor claim**.

## Question and bottom line

1. Do human engineers keep separate documentation and code comments in sync, and
   how fast do they drift?
2. When humans must change AI-written code, do inline comments help more than
   separate documentation, or than nothing? Where do developers look first?

**Bottom line.** The evidence that separate documentation drifts is consistent
and moderately strong. Repository mining shows that outdated references
commonly survive for months or years. Surveys and observation show engineers
rarely update design documents. Comments co-change with code far more often, but
not reliably: comments on interfaces and callers lag, and stale comments are
still found in active projects. For where people look, observational studies
agree: developers start from code and inline comments and rarely consult
documents. For AI-written code, **no study compares inline comments, separate
documentation and nothing for human maintainers.** The nearest experiments show
that comments make people more likely to accept and trust AI code. They do not
reliably make people more accurate. One RCT found no maintainability penalty
when humans evolved AI-assisted code. The user's claim that humans "won't update
the docs" is well supported. The claim that humans will find AI code "very hard
without comments" is plausible but untested.

## Findings

### A. Comments co-change with code more often than documents do

- **Fluri, Würsch and Gall, WCRE 2007; Fluri, Würsch, Giger and Gall, Software
  Quality Journal 2009** (measured, mining; checked at abstract level only). The
  2007 study mined three Java systems and found **97% of comment changes**
  happened in the same revision as the related code change. Newly added code
  "barely gets commented." The 2009 extension covers eight systems. In six of
  them, code and comments co-evolve in **90%** of cases, but API changes are
  re-documented in a *later* revision.
  [dblp](https://dblp.org/rec/conf/wcre/FluriWG07);
  [DOI 10.1007/s11219-009-9075-x](https://doi.org/10.1007/s11219-009-9075-x).
  The figure is conditional: *when* a comment changes, it usually changes with
  the code. It does not show that every comment needing a change received one.
- **Wen et al., ICPC 2019** found obsolete rationale and delayed comment fixes
  after refactoring. That evidence is already summarized in
  [comment maintenance and evaluation](comment-maintenance-and-evaluation.md).
- **Huang, Chen, Chen and Zhou, arXiv 2403.00251v1, March 2024** (measured). This
  paper presents an outdated-comment detector, CoCC. In a field check on 900
  recent commits from three active Java projects, the authors counted **23 of 25**
  flagged comments as outdated, by majority vote of 20 developers. Comments
  beside code still go stale in maintained projects.
  [arXiv](https://arxiv.org/abs/2403.00251v1).
- **Radmanesh et al., arXiv 2409.10781v1, September 2024** (measured; preprint;
  inconsistencies labelled by GPT-3.5). Changes that left code and comment
  inconsistent were **about 1.5 times** as likely to be followed by a
  bug-introducing commit. The association was strongest right after the
  inconsistency appeared. [arXiv](https://arxiv.org/abs/2409.10781).

### B. Separate documentation drifts more often and for longer

- **Lethbridge, Singer and Forward, IEEE Software 2003** (survey of 48, with 25
  answering the timing question, plus observation and interviews). Apart from
  test documents, engineers "rarely update" documentation. When they do, it is
  usually "several weeks" after the code changes. 68% agreed that documentation
  is always outdated. In observation, engineers consulted documentation in only
  **12 of 357** logged events (3%). Interviewees said code-level comments stay
  current because they are short and "right there" (practitioner report within
  the study). [PDF](https://courses.cs.duke.edu//cps196.1/fall11/classwork/Lethbridge-Singer-Forward-2003.pdf).
- **Tan, Wagner and Treude, arXiv 2212.01479v1 (2022); Empirical Software
  Engineering 2024** (measured, mining). The authors searched README and wiki
  files for references to code elements that the code no longer contains. In
  their top-1000 sample, **28.9%** of projects currently had such a reference, and
  **82.3%** had one at some point. In a Google-owned sample the figures were 5.4%
  and 29.7%. About **55%** of outdated references that were eventually fixed
  survived longer than a month. References still outdated had been outdated for
  **4.7 years** on average. The detector catches only deleted identifiers, so this
  is a lower bound on semantic drift.
  [ar5iv rendering of v1](https://ar5iv.labs.arxiv.org/html/2212.01479).
- **Aghajani et al., ICSE 2019** (measured, qualitative coding of 878 mailing-list
  posts, Stack Overflow questions, issues and pull requests). Up-to-dateness made
  up **39%** of content-related documentation issues. Discrepancies were usually
  triggered by code changes. Some projects responded by putting documentation on
  the pull-request checklist or requiring Javadoc updates before merge.
  [PDF](https://emadpres.github.io/pdfs/icse2019.pdf).
- **Gao and Chen, arXiv 2608.20195v1, August 2026** (measured; preprint). This
  study covers 33,097 *agent-authored* pull requests from the AIDev dataset. Only
  **37.0%** of PRs that touched code also touched a documentation file (95% CI for
  all-PR co-change 24.4–38.9%). When code and docs changed in different commits,
  code came first in **82.5%** of cases. The authors conclude that documentation
  "trails code rather than leading it." Documentation was identified by file path
  only. The instrument cannot see inline comments or docstrings, and the study
  has no human baseline. Not every code change needs a documentation change, so
  the 63% figure is not a drift rate.
  [arXiv](https://arxiv.org/html/2608.20195v1).
- **Gao, Lin, Treude, Gay and Zahedi, arXiv 2603.00489v2, August 2026** (measured;
  preprint). The authors tested LLM recommendations for README updates on 25,511
  PRs. In manual annotation, **21.5%** of matched recommendations (6.1% on the
  most conservative reading) were README updates the developers had missed.
  [arXiv](https://arxiv.org/abs/2603.00489).

### C. Where developers look first

- **Roehm, Tiarks, Koschke and Maalej, ICSE 2012** (observation plus interviews,
  28 professionals at 7 companies). **21** participants said their main
  information source was source code and inline comments, against **4** who named
  documentation. **16** said they begin by reading source code, against **3** who
  begin with documentation. 17 preferred asking colleagues to reading documents.
  Participants valued rationale but rarely found it written down, and "we did
  not observe a single participant documenting rationale for own code."
  [PDF](https://memphis-cs.github.io/comp-7085-8085-2012-fall/papers/Roehm2012ICSE.pdf).
- **Abdelsalam, Peitek, Bergum and Apel, Empirical Software Engineering, accepted
  August 2025** (measured, eye tracking, 20 students). Participants mostly used a
  "code-first" reading strategy. Comments drew up to **23%** of fixations. Their
  effect on performance ranged from **−30% to +34%** across snippets.
  Participants rated comments as helpful, but performance did not consistently
  improve. A cited earlier study (Karas et al., 2024) found that comments drew
  only about 4.7% of visual attention.
  [Author manuscript](https://www.se.cs.uni-saarland.de/publications/docs/APB+25.pdf).

### D. Humans working on AI-written code

- **Tang et al., VL/HCC 2024** (measured, lab study with eye tracking, 28
  participants repairing Copilot-generated code). Participants noted that the
  LLM-generated code had more comments than human-written code. They switched
  often between code and comments to resolve mismatches between them. Some used
  Copilot to *generate* comments in order to understand buggy code. Being told the
  code came from an LLM improved repair performance.
  [PDF](https://www.nztang.com/assets/files/papers/tang_vlhcc24.pdf).
- **Li, Treude and Turel, Journal of Systems and Software 231, January 2026**
  (measured, 173 programmers, between-subjects). Including comments in
  AI-generated solutions significantly increased *adoption*, measured as code
  similarity, regardless of expertise. Correctness and comprehension were not
  measured. [arXiv 2503.11453v2](https://arxiv.org/abs/2503.11453).
- **arXiv 2607.08885v1, July 2026, *Programmers Are Poor and Overconfident Judges
  of LLM-Generated Assertions*** (measured; preprint; 86 programmers). Exact
  explanatory comments gave no significant accuracy gain over no comment.
  Under-specified comments lowered accuracy relative to exact ones (OR 0.58) and
  *raised* confidence (4.25 against 3.99 with no comment).
  [arXiv](https://arxiv.org/html/2607.08885v1).
- **Stapleton et al., ICPC 2020** (measured, 45 participants; predates LLMs).
  Participants did better with human-written method summaries than with
  machine-generated ones (3.52 against 3.40 of 5, p = .029). Their ratings of a
  summary's quality did not correlate with how well they understood the code.
  [PDF](https://maiziezhoulab.github.io/paper/huang-icpc2020.pdf).
- **Borg et al., *Echoes of AI*, arXiv 2507.00788v3, February 2026; Empirical
  Software Engineering** (measured, preregistered, 151 participants who completed).
  In phase 2, developers without AI evolved Java code that had been written with
  or without AI help. There were no significant differences in completion time or
  code health. The experiment ran in late 2024, before coding agents were common,
  and the code was AI-*assisted*, not wholly AI-written.
  [arXiv](https://arxiv.org/html/2507.00788v3).
- **Martin-Lopez et al., IEEE TSE 2026** (measured, 69 participants). Using AI
  more than doubled median task completeness, but participants were **12.5%** less
  able to answer technical questions about code they had just produced. The
  authors discarded questions that an explicit comment answered as trivial, a
  reminder that comments can carry locational knowledge.
  [Author version](https://sscalabrino.github.io/files/2026/TSE2026MoreCodeLess.pdf).

## Counterevidence and limits

- **Proximity reduces drift but does not prevent it.** Fluri's 97% and 90% are
  co-change rates, not correctness rates, and API comments lag. Wen and CoCC
  document stale inline comments in maintained code.
- **Stale documentation is not always harmful.** In Lethbridge, 81% agreed that
  documentation can be useful even when out of date, especially high-level and
  architectural documents. A drifted docs folder may keep much of its value for
  architecture while failing on details.
- **AI-facing documents are actively edited.** *Agent READMEs* (arXiv 2511.12884v2,
  preprint) found 59–67% of CLAUDE.md, AGENTS.md and Copilot instruction files
  modified in more than one commit, with median gaps of about one to three days.
  It did not measure whether the files stayed accurate.
  [arXiv](https://arxiv.org/html/2511.12884).
- **Comments help less than people believe.** Nielebock (in the existing report),
  Abdelsalam, Stapleton and the assertions study all find perceived benefit
  exceeding measured benefit. Li et al. and the assertions study show comments
  increasing acceptance and confidence, so a *stale* inline comment may mislead a
  human more than a stale document they never open. That inference is untested.
- **No penalty in the one RCT on evolving AI-assisted code.** *Echoes of AI*
  contradicts a strong form of "humans will struggle with AI code". It predates
  agents and did not vary comments.
- **Age and samples.** Lethbridge (2003), Roehm (2012) and Fluri (2007/2009)
  predate AI-written code. The eye-tracking samples are small and mostly
  students. Fluri was checked at abstract level only, and several 2026 sources
  are unreviewed preprints.

## Implications

### For #19's drift step

1. **Keep the step.** Evidence that separate documentation goes unmaintained is
   the strongest finding here. Without a drift step, arm B would be evaluated
   under unrealistically good conditions.
2. **Do not make the drift symmetric by assumption.** The evidence says humans
   update the comment beside their edit far more often than a distant document.
   Leaving every context artifact untouched tests worst-case robustness. It does
   not test the placement claim. Run two variants:
   - **D1, no maintenance:** code changes; neither comments nor `docs/` change.
     This measures how much stale context harms each reader tier.
   - **D2, local-edit human:** comments inside the edited hunk are updated, while
     comments at callers or interfaces and everything in `docs/` are left alone.
     This is the realistic test of whether inline placement reduces drift.
3. **Put some stale claims away from the edit site.** Interface and caller
   comments are where the inline arm should fail, according to Fluri's API lag
   and Wen's delayed fixes. A drift step that only ever leaves the edited
   function's own comment stale would flatter arm C.
4. **Score how the reader handles a conflict.** Record whether it followed the
   stale claim, noticed the conflict, or checked against code, separately for
   weak and frontier readers. Humans say they trust code over documents (Roehm).
   Models may follow stale comments, as reported in *When Comments Mislead*, which
   the expanded review covers.
5. **Treat arm B's own maintenance as an outcome.** Agents touched documentation
   in only 37% of code-changing PRs in AIDev. Do not assume the arm-B writer keeps
   `docs/` current; count what it actually updates at each step.
6. **Add a mechanical floor metric.** A Tan-style check for identifiers that the
   context mentions but the code no longer contains is cheap, works for both arms
   and complements the fact ledger.

### For the corpus (#8)

Prefer repositories with real history that contain both a docs folder and
substantive comments. Mine their code-to-docs and code-to-comment co-change
rates to calibrate how often #19 injects drift. Include cross-file contracts,
because interfaces are where comment lag is documented. Repositories with
AGENTS.md or CLAUDE.md add a modern documentation layer whose drift is not yet
measured.

### Is a small human study worth planning?

**Not as a confirmatory study.** Human comment experiments with larger samples
were null or mixed: Nielebock recruited 277, of whom 66 completed. A 10–20 person
study cannot detect a placement effect and would invite overreading.

**A small formative study may be worth planning later**, only if #19 shows a
model-level signal and the user approves recruitment. Five to eight developers
would think aloud while making a change in an AI-maintained repository that has
both `docs/` and inline comments, with planted stale claims. The study would
observe where they look first, whether they notice the stale claims, and which
artifacts they update. Cheaper first step: mine human update rates in the #8
repositories, which needs no participants.

## Search log

Searches (2026-11-07): Fluri co-evolution; Ibrahim et al. comment-update
practices; Lethbridge documentation state of practice; Tan/Wagner/Treude
outdated references; Roehm program comprehension; *Echoes of AI*; Aghajani 2019
and 2020; human studies of LLM-generated code with comments; outdated-comment
co-evolution in Python, 2024–2025; AGENTS.md/CLAUDE.md evolution; Xia et al.
comprehension field study; misleading or outdated comments with human
participants; documentation co-change in pull requests; AIDev documentation
co-change; Li/Treude/Turel comments and adoption; *More Code, Less
Understanding*; the Anthropic skill-formation RCT; de Souza et al. 2005;
inline comments against external documentation experiments; Abdelsalam et al.
eye tracking.

Excluded or downgraded:

- **Ibrahim et al., JSS 2012:** only secondary summaries were reachable.
- **de Souza et al., SIGDOC 2005, and Aghajani et al., ICSE 2020:** the full texts
  were paywalled or returned 403, so their artifact rankings could not be
  verified.
- **Anthropic skill-formation RCT (January 2026):** it measures learning, not
  maintenance of existing code.
- **Xia et al., TSE 2018:** reports no separate figure for time spent on
  documentation.
- **AgentPatterns.ai blog:** a secondary source.
- **KTH thesis *When Comments and Code Diverge*:** no findings were visible.
- **PMC pilot (n = 7):** studies LLM behaviour and is too small.
- **The 53.6K-edit Decode study:** does not separate comment edits from other
  edits.
- **Wilson et al., *Best Practices for Scientific Computing*:** an expert
  recommendation, not evidence.
- **The Google practice of keeping docs under source control:** already in the
  [comment-context collection](comment-context/sources/software-engineering-at-google/passages.md).
