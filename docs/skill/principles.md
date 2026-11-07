# Code Comments principles ledger

This ledger is the reduce step of the skill pipeline in [README.md](README.md). It
merges the 89 candidate principles from the four map files in `distillation/`
(`historical.md` HIS-01 to HIS-21, `industry.md` IND-01 to IND-24, `craft.md`
CRA-01 to CRA-23, `llm-evidence.md` LLM-01 to LLM-21) into 33 deduplicated
principles. They are ordered by importance for an agent editing code. Each
principle names the candidates it merges, copies its key citations verbatim from
those candidate files, and states a grade, its limits and the `comment-edit`
metric that would detect it. Candidates that were not merged are listed with
reasons at the end, so every candidate id appears exactly once as a primary
assignment. Citations are machine-checked by
`python scripts/check_distillation.py`: passage ids must exist and quotes must
appear verbatim. Dispositions (core, variant axis, rejected) are design
decisions, not findings. Revise them when the tournament, the downstream tier
(#19) or the placement pilot (#9) produces evidence. No principle here has been
tested as skill text against a model.

## Evidence grading

- **A** — consistent empirical evidence on LLMs: at least two independent studies
  agree in direction. The studies may still be small, use isolated functions or
  single-shot tasks, or rely on proxies; the limits are stated per principle.
- **B** — empirical evidence that is mixed, indirect (proxy settings, one study,
  answer-derived comments) or human-only; or strong expert consensus across
  three or more independent traditions.
- **C** — expert opinion or historical practice from one or two traditions, with
  no empirical test.
- **D** — inference or extrapolation: the behaviour the principle asks for has not
  been tested, even if the problem it addresses has been measured.

Grades rate the support for following the principle as written, not the
importance of the topic. Core principles may carry any grade when the action is
low-risk and consistent with the eval.

## Principles

### P-01 — Correct or remove every comment your change makes false, in the same edit
- **Principle:** After changing behaviour, find each comment, docstring and cross-reference whose claim the change falsifies, including ones outside the edited lines (callers, interfaces, module headers), and fix or delete it before you finish. A wrong comment is worse than none, because models follow it.
- **Disposition:** core — the one effect every LLM study agrees on, and every source tradition agrees with it.
- **Grade:** A — wrong or unrelated comments lowered LLM performance in three independent studies (Macke and Doyle; Pan et al.; Vitale et al.), while correct comments helped inconsistently.
- **Merged from:** HIS-04, IND-07, CRA-13, LLM-01, LLM-03
- **Key citations:**
  - [documentation-llm-understanding-012](../research/comment-context/sources/documentation-llm-understanding/passages.md#documentation-llm-understanding-012) — supports — "the random comments scenario performs worse than any other scenario on both GPT-3.5 and 4 (only 22.1% and 68.1% successes respectively)" — evidence: empirical-llm
  - [comments-bug-fixing-035](../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-035) — supports — "Comments generated from buggy code do not help and can mislead automated bug-fixing models." — evidence: empirical-llm
  - [comment-context-deep-dive.md § Stale or defective annotations can transmit the wrong behavior](../research/comment-context-deep-dive.md#stale-or-defective-annotations-can-transmit-the-wrong-behavior) — supports — "reports completion biased toward historical implementations under outdated comments" — evidence: empirical-llm
  - [rational-design-process-008](../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-008) — supports — "If a change is made, all documentation that is invalidated must be changed." — evidence: expert-opinion
- **Conditions / limits:** Every measured harm uses a proxy for staleness: a docstring from a different function, a wrong-topic prefill, comments generated from buggy code. The only study of naturally outdated comments (*When Comments Mislead*) is abstract-only in this repository, so the size of the harm from real drift is unknown. All settings are isolated functions or single-shot tasks. Comments far from the edit are hard to find, and Google reports that same-change updating was not widely adopted even with docs beside the code. Whether to correct or delete is AXIS-STALE. This principle does not license rewriting comments that are still true (P-13).
- **Eval signal:** maintain / bad_claims and preserved; audit / bad_claims.

### P-02 — Never write an unverified reason as fact
- **Principle:** Write a why, a history ("we tried X") or an intended contract only when the evidence in hand supports it: the task, a ticket, a test, a review comment, a commit or a reference you have actually read. An invented but plausible reason is a wrong comment that looks authoritative to the next agent.
- **Disposition:** core — every group agrees and the eval punishes violations. What to do with the gap instead is AXIS-UNVERIFIED.
- **Grade:** B — indirect empirical support (wrong comments harm models; a second-hand report says LLM-emitted comments are often inaccurate) plus strong cross-source expert agreement. The harm of plausible-but-wrong rationale in persistent comments has not been measured directly.
- **Merged from:** HIS-12, LLM-05
- **Key citations:**
  - [comment-maintenance-and-evaluation.md § Working hypothesis for this project](../research/comment-maintenance-and-evaluation.md#working-hypothesis-for-this-project) — supports — "When evidence for a rationale is missing, it should leave that rationale unstated or ask for the missing decision instead of manufacturing an explanation." — evidence: expert-opinion
  - [historical-comment-design.md, "Do not turn inference into history"](../research/historical-comment-design.md#do-not-turn-inference-into-history) — supports — "Without supporting evidence, the new sentence manufactures an explanation." — evidence: expert-opinion
  - [rational-design-process-010](../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-010) — supports — "If a piece of informatio n is unavailable, that fact is noted in the part of the document where the informa tion should go" — evidence: expert-opinion
  - [talking-while-coding-005](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-005) — supports — "probes find LLM-emitted comments themselves often" — evidence: empirical-llm
- **Conditions / limits:** The historical authors explained their own code; an agent explaining someone else's code faces a fabrication risk they did not. Pan et al.'s null result for wrong-solution content is confounded by floor effects. A description verified against the code is not an inference and is not restricted by this principle.
- **Eval signal:** capture / bad_claims (planted plausible-but-unsupported rationale).

### P-03 — Check every clause of a comment against the final code
- **Principle:** After the last code edit, reread each comment you wrote, moved or left beside changed code, and confirm that every clause (each step, algorithm name, condition) still holds, not only the gist. One wrong clause can cancel a comment's benefit or steer a later fix wrong, and fluent or near-identical wording does not prove accuracy.
- **Disposition:** core — low cost, and it directly reduces the harm in P-01.
- **Grade:** B — one controlled LLM study (Pan et al.: changing one key step returned the lift to baseline, two recipients) plus a single repair anecdote and secondary reports on comment-update models.
- **Merged from:** LLM-02, LLM-21
- **Key citations:**
  - [talking-while-coding-015](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-015) — supports — "replacing the algorithm name or one key step while preserving length, line count, and tone" — evidence: empirical-llm
  - [talking-while-coding-016](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-016) — supports — "the corrupted condition falls back to the baseline range" — evidence: empirical-llm
  - [comments-bug-fixing-032](../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-032) — supports — "We tried to change the comment by removing such a part of the comment, and this resulted in a correct fix." — evidence: empirical-llm
  - [comment-context-deep-dive.md § Learned comment updates are feasible but similarity can mislead](../research/comment-context-deep-dive.md#learned-comment-updates-are-feasible-but-similarity-can-mislead) — supports — "a nearly unchanged but incorrect sentence can resemble the human reference." — evidence: empirical-llm
- **Conditions / limits:** The clause-removal repair is one anecdote, not a rate. GPT-3.5 comments generated from *correct* code were still 7% incoherent with their category (median adequacy 4 of 5). More clauses means more surface that can go false; that argues for short comments, not for skipping needed ones.
- **Eval signal:** capture / bad_claims; maintain / bad_claims.

### P-04 — Keep each comment attached to the code it describes
- **Principle:** When you copy, move, extract or inline code, check that each comment travelling with it still describes its new neighbour, and delete text written for a different function, branch or problem. A coherent comment on the wrong topic hurt models more than random filler, mostly on easy problems they would otherwise have solved.
- **Disposition:** core — well supported and cheap to follow.
- **Grade:** A — two independent LLM studies agree (an unrelated docstring in Macke and Doyle; a wrong-topic prefill in Pan et al.).
- **Merged from:** LLM-10
- **Key citations:**
  - [documentation-llm-understanding-010](../research/comment-context/sources/documentation-llm-understanding/passages.md#documentation-llm-understanding-010) — supports — "a random comment or docstring from a different HumanEval function" — evidence: empirical-llm
  - [talking-while-coding-017](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-017) — supports — "Coherent but topic-wrong comments hurt more than incoherent noise" — evidence: empirical-llm
  - [talking-while-coding-017](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-017) — supports — "The damage concentrates on easy problems (Table 15), where the recipient would often have solved the task unaided." — evidence: empirical-llm
- **Conditions / limits:** Test-generation and prefill settings, not comments that an agent moved inside a repository. The wrong-topic versus random asymmetry is significant pooled but varies by model pair.
- **Eval signal:** capture / misplaced; maintain / bad_claims.

### P-05 — Record the non-obvious knowledge the evidence gives you, in the scope it governs
- **Principle:** When the task evidence holds something a future editor needs but cannot recover from the code (a requirement or side-effect obligation, a constraint, a trade-off, an incident, the reason the code takes its present form), write it in a comment in the scope it governs during this edit. A later agent cannot reliably regenerate it on request, and leaving out a needed comment to look "clean" fails the next reader.
- **Disposition:** core — the `capture` family requires it; P-09 and P-10 bound it from the other side.
- **Grade:** B — empirical LLM evidence is positive but mixed and partly answer-derived: correct, solution-bearing comments lifted weak recipients by 17.2 points on average (Pan et al.), inference-only repair gains were small to medium (Vitale et al.), and correct docstrings gave no significant test-success gain (Macke and Doyle). Expert consensus across all four groups.
- **Merged from:** HIS-01, IND-02, IND-04, CRA-02, CRA-17, LLM-11, LLM-14
- **Key citations:**
  - [rational-design-process-001](../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-001) — supports — "They make a long sequence of design decisions with no clear statement of why they do things the way they do. Their rationale is rarely explained." — evidence: expert-opinion
  - [pragmatic-programmer-004](../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "Engineering trade-offs, why decisions were made, what other alternatives were discarded, and so on." — evidence: expert-opinion
  - [comments-bug-fixing-026](../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-026) — supports — "models trained without comments still benefit from comments at inference time" — evidence: empirical-llm
  - [talking-while-coding-023](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-023) — supports — "A correct comment from a stronger model is therefore not interchangeable with a prompt asking the recipient to write its own." — evidence: empirical-llm
- **Conditions / limits:** Verified knowledge only (P-02): Pan et al.'s source comments were filtered on passing tests, and Vitale et al.'s were generated from the fixed method. No study tests comments that persist across fresh agent sessions, or compares them with the same facts in a document (#9). Parnas and Google would put much of this in design documents, and Knuth's commentary is woven WEB prose, not inline comments. Google's "comment liberally" is not calibrated against noise. Rejected design alternatives are AXIS-REJECTED-ALT.
- **Eval signal:** capture / recall, with bad_claims for invented reasons; usefulness to a later agent needs #19.

### P-06 — State the decisive choice that rules out a natural-looking wrong alternative
- **Principle:** When correctness depends on a choice where a plausible alternative would be wrong ("sum, not product", "count empty cells as zero, do not skip them", "store after lookup"), state the choice and what it rules out at the line that makes it. This single-decision content transferred most clearly to weaker models.
- **Disposition:** core — it is the most specific form of P-05 with the clearest LLM signal.
- **Grade:** B — a qualitative, selected flip analysis in one LLM study (89 source-transferable against 3 source-toxic problems out of 870) plus a hypothetical from the bug-fixing paper.
- **Merged from:** LLM-13
- **Key citations:**
  - [talking-while-coding-056](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-056) — supports — "prefix-source’s comment block typically reroutes the prefix-recipient from a plausible-but-wrong strategy to the correct one." — evidence: empirical-llm
  - [talking-while-coding-058](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-058) — supports — "The prefix-source’s prefix supplies a single strategic decision – “it’s a sum, not a product” – that the prefix-recipient was unable to find on its own." — evidence: empirical-llm
  - [comments-bug-fixing-012](../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-012) — supports — "Without comments, the model might attempt to fix the method by adding a check to skip empty strings entirely." — evidence: expert-opinion
- **Conditions / limits:** Only when the evidence establishes the choice. Name the alternative as what the code rules out, not as history ("we tried X") unless the evidence shows that (P-02). This differs from recording design alternatives that were deliberated and rejected (P-28).
- **Eval signal:** capture / recall; capture / bad_claims when the wrong alternative is planted as a forbidden claim.

### P-07 — Take the intended contract from evidence of intent, not from the code you are fixing
- **Principle:** When you document what code should do, especially during a bug fix, derive it from requirements, tests, the ticket or the corrected implementation. A comment that faithfully paraphrases buggy logic hides the bug from the next agent.
- **Disposition:** core — low-risk and directly tied to bad_claims.
- **Grade:** B — one LLM study (Vitale et al.): comments generated from buggy code left exact match flat or worse; small fine-tuned models on isolated Java methods.
- **Merged from:** LLM-04
- **Key citations:**
  - [comments-bug-fixing-035](../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-035) — supports — "since they document the buggy logic rather than the intended" — evidence: empirical-llm
  - [comments-bug-fixing-017](../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-017) — supports — "The comments generated from it might reflect such errors." — evidence: empirical-llm
  - [comment-context-deep-dive.md § Vitale and colleagues: repair gains include answer-derived information](../research/comment-context-deep-dive.md#vitale-and-colleagues-repair-gains-include-answer-derived-information) — supports — "This directly limits the inference that automatically explaining existing code supplies useful repair knowledge." — evidence: empirical-llm
- **Conditions / limits:** The `sorted(list)` case-sensitivity example is the authors' thought experiment. When the current code is the only evidence of intent, do not write a behavioural contract; handle the gap per AXIS-UNVERIFIED.
- **Eval signal:** capture / bad_claims where the evidence contradicts the code; maintain / recall.

### P-08 — Be specific: name the exact condition, algorithm, bound or invariant
- **Principle:** Prefer a concrete commitment to a vague category such as "handles edge cases" or "formatting". Vague but correct comments lost much of their benefit, while paraphrase, compression and hedged tone did not. Point to a constant rather than copying its value (P-27).
- **Disposition:** core — consistent with the eval and with every other group.
- **Grade:** B — one LLM study, two recipients and one source model (Pan et al. Table 9: vagueness cost 7.0 and 5.3 points).
- **Merged from:** LLM-12
- **Key citations:**
  - [talking-while-coding-046](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-046) — supports — "the block becomes less informative, not wrong." — evidence: empirical-llm
  - [talking-while-coding-050](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-050) — supports — "vague (specificity)−7.0 ∗∗∗ −5.3∗∗" — evidence: empirical-llm
  - [comments-bug-fixing-016](../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-016) — supports — "is documented with the one-word commentFormatting." — evidence: empirical-llm
- **Conditions / limits:** Specific claims go stale faster than generic ones, so this depends on P-01 and P-03. No study measures the net value of specificity over successive edits.
- **Eval signal:** capture / recall (anchor groups favour specific terms); capture / noise_lines.

### P-09 — Do not restate what the code, names or types already say
- **Principle:** Do not narrate statements step by step, label the construct ("Constructor", "Sample method"), restate the signature in a docstring, repeat a good name in a purpose line, or comment every declaration by rule. Each is a second copy to maintain, and restating comments showed little measurable benefit for models.
- **Disposition:** core — strong consensus and the `restrain` family tests it.
- **Grade:** B — indirect LLM evidence (a null result for correct docstrings in test generation; SHAP attributions showing models lean on method names and identifiers) plus strong cross-source expert consensus.
- **Merged from:** HIS-06, HIS-20, IND-20, CRA-03, LLM-06
- **Key citations:**
  - [pragmatic-programmer-004](../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "This kind of mechanical comment writing actually makes it more difficult to maintain code. Now there are two things to update when you make a change." — evidence: expert-opinion
  - [documentation-llm-understanding-018](../research/comment-context/sources/documentation-llm-understanding/passages.md#documentation-llm-understanding-018) — supports — "correct comments do not add much information as it would be relevant to the creation of unit tests" — evidence: empirical-llm
  - [rational-design-process-009](../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-009) — supports — "Lots of words are used to say what could be said by a single programming language statement, a formula or a diagram." — evidence: expert-opinion
  - [software-engineering-at-google-ch10-006](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-006) — supports — "Adding explicit boilerplate sections would make the comment more verbose and ... repetitive, but ... no clearer (and arguably less clear)." — evidence: expert-opinion
- **Conditions / limits:** "No benefit" is too strong: correct docstrings raised line coverage, and DeepSeek-Coder weighted "what" comments. Von Neumann's per-order explanatory column served self-modifying machine code and does not transfer. A purpose card made sense with six-character FORTRAN names. Linters or docstring rules in the repository may require a minimal comment; follow them (P-31). This governs new comments; removing existing ones is governed by P-13.
- **Eval signal:** restrain / noise_lines; capture / noise_lines.

### P-10 — Do not comment for volume; spend comments where a reader could go wrong
- **Principle:** Comment quantity is not the goal. Put explanation on the few facts with the most leverage (logic a capable reader could plausibly get wrong, invariants, constraints, non-obvious dependencies) and leave routine code alone. Marking everything as important hides what matters.
- **Disposition:** core — the empirical and expert evidence agree on the direction; only the threshold is open (AXIS-DENSITY).
- **Grade:** B — empirical LLM evidence on self-emitted comments: comment volume did not predict pass@1 across 88 models, dense policies helped some models and hurt others, and correct content helped most on medium problems. Human studies agree that density is not quality.
- **Merged from:** LLM-07, LLM-16, CRA-16, IND-24
- **Key citations:**
  - [talking-while-coding-025](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-025) — supports — "Compliance with the form instruction does not predict whether pass@1 goes up or down." — evidence: empirical-llm
  - [talking-while-coding-021](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-021) — supports — "The effects concentrate where the recipient has headroom." — evidence: empirical-llm
  - [comment-maintenance-and-evaluation.md § Steidl, Hummel, and Juergens (2013): quality is not quantity](../research/comment-maintenance-and-evaluation.md#steidl-hummel-and-juergens-2013-quality-is-not-quantity) — supports — "Comment density alone cannot distinguish useful explanation from irrelevant or obsolete material." — evidence: empirical-human
  - [philosophy-of-software-design-010](../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-010) — supports — "This mistake leads to situations where important information is hidden" — evidence: expert-opinion
- **Conditions / limits:** Pan et al. measured comments in a model's own output, not comments read later from a repository. Problem difficulty bands are not something an agent can measure while editing. MemUse (memory stores, not comments) is only a warning that delivered context may go unused.
- **Eval signal:** restrain / noise_lines; capture / recall.

### P-11 — Choose comment content by the reader's gap, not by a fixed why/what quota
- **Principle:** The tradition says to explain why, not how or what. The LLM evidence does not settle it: repair models attended most to comments on how the implementation works, and imposed WHY or WHAT policies lifted some models and hurt others. Variants decide between why-only and why plus the decisive what or how.
- **Disposition:** variant-axis:AXIS-CONTENT — expert consensus and the LLM evidence conflict.
- **Grade:** B — mixed: SHAP attributions on two small fine-tuned repair models, self-emitted comment policies on LiveCodeBench, an underpowered 13-model intent correlation, and expert opinion favouring why.
- **Merged from:** CRA-01, LLM-18, LLM-19
- **Key citations:**
  - [pragmatic-programmer-004](../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "So restrict your non-API commenting to discussing why something is done, its purpose, and its goal." — evidence: expert-opinion
  - [comments-bug-fixing-029](../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-029) — supports — "Both models give much higher importance to comments describinghowthe implementation is done as compared to the other categories." — evidence: empirical-llm
  - [talking-while-coding-023](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-023) — supports — "The variance is in the receiving model, not the prompt text." — evidence: empirical-llm
  - [talking-while-coding-010](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-010) — qualifies — "We conclude that no robust intent signal was found, rather than that none exists" — evidence: empirical-llm
- **Conditions / limits:** Interface comments necessarily say what a unit does, even in the why-only tradition (P-22). Mechanism comments drift fastest, so any position that writes how must also maintain it (P-01). The SHAP ranking comes from comments generated from fixed code.
- **Eval signal:** capture / recall and noise_lines across variants; maintain / bad_claims (stale mechanism claims).

### P-12 — Set the omission threshold for the next reader
- **Principle:** Leave out what a capable reader can easily reconstruct, and record the major decisions that a newcomer (a fresh or weaker agent session) would lack. Where that line falls is open.
- **Disposition:** variant-axis:AXIS-DENSITY — the sources pull in opposite directions and the eval is two-sided.
- **Grade:** B — mixed: weak LLM recipients gained from correct comments (Pan et al.), but which models benefit most changes with the setting (Vitale et al.; Macke and Doyle); historical and expert sources conflict.
- **Merged from:** HIS-07, HIS-17, LLM-15
- **Key citations:**
  - [planning-and-coding-020](../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-020) — supports — "wi II not impose a real strain on the reader, due to the annunt of impl icitly given rrøterial that he rust rerrerr,ber." — evidence: expert-opinion
  - [rational-design-process-009](../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-009) — supports — "Unfortunately, the result is a document useful to people who know the system well but impenetrable for newcomers." — evidence: expert-opinion
  - [talking-while-coding-003](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-003) — supports — "Correct comments raise the recipient’s pass@1 by17.2% on average across the 12 (recipient, source) pairs." — evidence: empirical-llm
  - [comments-bug-fixing-027](../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-027) — qualifies — "suggesting that bigger models can better exploit contextual information even without previous exposure" — evidence: empirical-llm
- **Conditions / limits:** "Weaker" means a lower baseline pass rate, not parameter count. The von Neumann criterion governs flow-diagram storage fields and applies to comments only by analogy. The "fresh session as newcomer" framing is untested.
- **Eval signal:** restrain / noise_lines against capture / recall; effects across model tiers are not covered by comment-edit (needs #19 or #20).

### P-13 — Leave valid comments alone
- **Principle:** Keep still-accurate comments word for word. Change or delete a comment only because it is false, misattached, pure restatement, or missing a needed fact; never for style, spelling variants, your own phrasing, or to lower the comment count. Removing comments cost some comment-reliant models heavily.
- **Disposition:** core — protects `preserved` and limits diff noise.
- **Grade:** B — mixed empirical LLM evidence in other settings (suppressing self-emitted comments cost some models up to 14.5 points and helped others; removing natural comments helped long-context retrieval for several models) plus Google practice against cosmetic churn.
- **Merged from:** IND-21, LLM-17
- **Key citations:**
  - [talking-while-coding-029](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-029) — supports — "suppressing comments costs up to 14.5% on comment-dependent models, while helping others." — evidence: empirical-llm
  - [agent-context-evidence.md § 4. Comments can obstruct long-context retrieval](../research/agent-context-evidence.md#4-comments-can-obstruct-long-context-retrieval) — opposes — "removing natural comments improves several models" — evidence: empirical-llm
  - [agent-context-evidence.md § 4. Comments can obstruct long-context retrieval](../research/agent-context-evidence.md#4-comments-can-obstruct-long-context-retrieval) — qualifies — "This demonstrates sensitivity to context construction, not universal comment harm." — evidence: empirical-llm
  - [software-engineering-at-google-ch22-004](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch22-004) — supports — "we do not want the resulting tools to be used as a mechanism to fight over the proper spelling of “gray” or “grey” in comments." — evidence: historical-practice
- **Conditions / limits:** Pan et al.'s `none` policy suppressed comments in the model's own output; transfer to deleting repository comments is an inference. A typo that changes meaning (a wrong identifier in a comment) is a correctness fix. Rewording a comment while moving it counts as new noise in the grader.
- **Eval signal:** audit / preserved; maintain / preserved; noise_lines.

### P-14 — Do not try to disarm wrong text with a label or an "ignore this" note
- **Principle:** If a comment or commented-out block is wrong or obsolete, correct it or remove it. Prefixing it with "outdated:", "(Vulnerable)", a hedge or "do not refer to this" left most of its effect on models.
- **Disposition:** core — the only evidence points one way, and the action (fix or remove) is already required by P-01.
- **Grade:** B — one LLM study (Comment Traps): tags and instructions removed only 4.93% to 21.84% of the excess defects, tested on commented-out code at one position. Extending it to prose comments rests on Pan et al.'s finding that tone and hedging did not change a correct comment's effect.
- **Merged from:** LLM-09
- **Key citations:**
  - [comment-traps-029](../research/comment-context/sources/comment-traps/passages.md#comment-traps-029) — supports — "AI coding assistants still recognize the defective CO code and introduce additional defects during generation." — evidence: empirical-llm
  - [comment-traps-031](../research/comment-context/sources/comment-traps/passages.md#comment-traps-031) — supports — "the highest reduction rate was only 21.84%, which is still insufficient for effectively eliminating defects." — evidence: empirical-llm
  - [talking-while-coding-016](../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-016) — qualifies — "only removing specific task information hurts, and wording, length, and tone do not" — evidence: empirical-llm
- **Conditions / limits:** The Comment Traps authors count tagging as useful for alerting humans; human-facing and model-facing goals diverge here. In the grader, a labelled stale claim still matches forbidden-claim anchors.
- **Eval signal:** maintain / bad_claims; audit / bad_claims.

### P-15 — When a comment is false, correct it in place or delete it
- **Principle:** Both remove the false claim that P-01 requires removing. Correcting keeps a fact the next editor may need; deleting is shorter and cannot introduce a new error. Variants choose a default. "Mark obsolete" notes, which suit standalone documents, are excluded for inline comments by P-14.
- **Disposition:** variant-axis:AXIS-STALE — no evidence compares the two for agents.
- **Grade:** C — Google practice for standalone documents plus expert opinion; one human observational study shows rationale comments also become obsolete.
- **Merged from:** IND-08
- **Key citations:**
  - [software-engineering-at-google-ch10-014](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-014) — supports — "when a document no longer serves any purpose, either remove it or identify it as obsolete (and, if available, indicate where to go for new information)." — evidence: historical-practice
  - [software-engineering-at-google-ch03-005](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch03-005) — supports — "if you find a mistake or omission in the documentation, fix it!" — evidence: expert-opinion
  - [comment-maintenance-and-evaluation.md § Wen, Nagy, Bavota, and Lanza (2019): proximity does not prevent drift](../research/comment-maintenance-and-evaluation.md#wen-nagy-bavota-and-lanza-2019-proximity-does-not-prevent-drift) — supports — "Rationale comments also become obsolete and sometimes need deletion." — evidence: empirical-human
- **Conditions / limits:** The grader now credits each removed stale line against one replacement line (2026-11-07), so a same-length correction costs no more than deletion; a longer correction still spends noise budget.
- **Eval signal:** maintain / recall, bad_claims and noise_lines; audit / preserved.

### P-16 — Never add commented-out code; give temporary states a reason and a real tracking reference
- **Principle:** Do not disable code or tests by commenting them out. Delete the code, since version control keeps it, or use the framework's skip or flag mechanism with a reason. A TODO, workaround or stub you leave should say that it is temporary and why, and cite an issue only if one exists; never invent an ID.
- **Disposition:** core — consistent with the empirical harm in P-17 and with the restrain family.
- **Grade:** B — Google practice and expert opinion, consistent with one large LLM study showing that models reuse commented-out code. Pragmatic Programmer's "board it up" advice dissents.
- **Merged from:** IND-15, CRA-19, CRA-20
- **Key citations:**
  - [software-engineering-at-google-ch23-003](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch23-003) — supports — "The team could easily disable tests by commenting them out, but that would make the failures too easy to forget about." — evidence: historical-practice (one team case study)
  - [software-engineering-at-google-ch17-001](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch17-001) — supports — "or a bug ID in a comment to the corresponding bug report." — evidence: historical-practice
  - [pragmatic-programmer-016](../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-016) — supports — "Version control systems keep track of every change you make in your source code and documentation." — evidence: expert-opinion
  - [pragmatic-programmer-003](../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-003) — opposes — "Perhaps you can comment out the offending code or display a not implemented message, or substitute dummy data instead." — evidence: expert-opinion
- **Conditions / limits:** Even tracked disable tags piled up at Google until cleanup was automated, so a tracked TODO is not self-maintaining. No source specifies a TODO format. Agents rarely know a file's intended lifespan unless the task says so.
- **Eval signal:** restrain / noise_lines (commented-out code counts as new comment lines).

### P-17 — Existing commented-out code near the edit: delete it or flag it
- **Principle:** Models treat commented-out code as a pattern to reason from, so leaving it beside code you or a later agent will edit raises defect risk. Developers also keep it on purpose. Variants decide between deleting it and leaving it while flagging it in the report.
- **Disposition:** variant-axis:AXIS-COMMENTED-OUT — measured harm against user ownership of existing code.
- **Grade:** B — one large LLM study (1,000 samples by 11 positions; Copilot and Cursor with GPT-4o and Claude 3.5 Sonnet), with deliberately injected defects; no replication.
- **Merged from:** LLM-08
- **Key citations:**
  - [comment-traps-001](../research/comment-context/sources/comment-traps/passages.md#comment-traps-001) — supports — "defective CO code in the context causes AI coding assistants to generate more defective code, reaching up to 58.17 percent." — evidence: empirical-llm
  - [comment-traps-019](../research/comment-context/sources/comment-traps/passages.md#comment-traps-019) — supports — "the AI still uses it as a reference when generating new code, thereby introducing defects in a way that may go unnoticed by developers." — evidence: empirical-llm
  - [comment-traps-003](../research/comment-context/sources/comment-traps/passages.md#comment-traps-003) — opposes — "It is commonly used for debugging, experimenting with alternative implementations, or preserving legacy logic for potential future use." — evidence: historical-practice
  - [ai-code-comments/README.md § Reading notes](../research/ai-code-comments/README.md#reading-notes) — qualifies — "studies defective commented-out executable code, not ordinary explanatory prose. Its maximum 58.17% increase is relative, not a defective-output percentage." — evidence: empirical-llm
- **Conditions / limits:** The 58.17% is a relative increase in flagged defects. Even defect-free commented-out code shifted outputs in most settings. For Copilot the risk was highest just below the cursor. TODOs and prose comments were outside the study's scope.
- **Eval signal:** audit / bad_claims and preserved only if a case plants commented-out code; otherwise not covered by comment-edit (needs #19 or #20).

### P-18 — State constraints, assumptions and couplings at the point of reliance
- **Principle:** When correctness depends on something not visible locally (an invariant, an ordering, a bound, an input or environment assumption, undocumented dependency behaviour, a resource another routine owns, a convention every caller must follow), state it on the line or variable that relies on it. Where the evidence shows it, also state the condition under which it stops holding, so a later editor can tell when the decision has expired.
- **Disposition:** core — consistent across traditions, and the eval's `capture` and `misplaced` metrics test it.
- **Grade:** B — strong cross-source consensus (Knuth, the FORTRAN manual, von Neumann, Parnas, Pragmatic Programmer, Google); no direct empirical test, though P-05's obligation comments are the same kind of fact.
- **Merged from:** HIS-08, HIS-11, HIS-15, CRA-08, CRA-10, IND-05
- **Key citations:**
  - [literate-programming-005](../research/comment-context/sources/literate-programming/passages.md#literate-programming-005) — supports — "square ← p[ord] ∗ p[ord]; { at this point ord ≤ k }" — evidence: historical-practice
  - [fortran-1956-005](../research/comment-context/sources/fortran-1956/passages.md#fortran-1956-005) — supports — "The programmer anticipates that BIGA will usually be greater than A(I), a plausible guess if the A(1) are randomly arranged but not if they tend to increase with increasing I." — evidence: historical-practice
  - [pragmatic-programmer-038](../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-038) — supports — "For routines you call, rely only on documented behavior. If you can't, for whatever reason, then document your assumption well." — evidence: expert-opinion
  - [software-engineering-at-google-ch08-005](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch08-005) — supports — "With influencing factors clearly noted, we are able to identify when changes related to one or more of these factors warrant reevaluating the rule." — evidence: historical-practice
- **Conditions / limits:** Most sources keep these facts in manuals, diagrams or design documents, so inline placement is untested. Pragmatic Programmer's remedy for hidden coupling is restructuring, and Google's "influencing factors" evidence concerns style-guide rules. Where an assertion, type or structure could carry the fact, see AXIS-CODE-FIRST.
- **Eval signal:** capture / recall and misplaced; whether constraints survive later edits needs #19.

### P-19 — Flag deliberate oddities and departures from the expected pattern
- **Principle:** When code intentionally does something that looks like a mistake (a switch fall-through, an empty or swallowing catch, a deliberate no-op, a nonstandard control path, a broken local convention), say where it happens that it is intentional and why. Readers predict from the pattern, so an unflagged departure is where they go wrong.
- **Disposition:** core — low-risk and consistent across three traditions.
- **Grade:** B — cross-source practice (Google style guides, von Neumann, Knuth); no empirical test.
- **Merged from:** IND-03, HIS-13
- **Key citations:**
  - [software-engineering-at-google-ch08-004](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch08-004) — supports — "specific cases that must include in-code documentation—cases in which intent is not always obvious, such as fall-through in switch statements, empty exception catch blocks, and template metaprogramming." — evidence: historical-practice
  - [planning-and-coding-146](../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-146) — supports — "we will encounter deviations and cornplications which should be ccmnented" — evidence: expert-opinion
  - [literate-programming-012](../research/comment-context/sources/literate-programming/passages.md#literate-programming-012) — supports — "the name of a section should explicitly mention any nonstandard control structures, even though its data structures can often be left implied." — evidence: expert-opinion
- **Conditions / limits:** An intent-revealing name such as `ignored` can say "intentional" but not why. Trivial departures need no note (P-10). State the why only if the evidence gives it (P-02).
- **Eval signal:** capture / recall; restrain / noise_lines for trivial departures.

### P-20 — Before removing odd-looking code, look for its reason, and write it down once found
- **Principle:** Before simplifying or deleting code that looks unnecessary, look for its reason in nearby comments, tests, history and the task evidence. Keep any rationale you find. If the evidence shows a reason that is not written down, record it beside the code so the next agent does not repeat the investigation or the "fix".
- **Disposition:** core — low-risk, and the only LLM experiment on rationale points the same way.
- **Grade:** B — one small LLM experiment (Keep the Why: 20 sessions, one fixture, rationale in an external file) plus expert opinion.
- **Merged from:** IND-06, CRA-23
- **Key citations:**
  - [software-engineering-at-google-ch03-002](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch03-002) — supports — "before removing or changing something, first understand why it’s there." — evidence: expert-opinion
  - [related-systems-and-researchers.md § 10. Keep the Why: a directly relevant existing rationale skill](../research/related-systems-and-researchers.md#10-keep-the-why-a-directly-relevant-existing-rationale-skill) — supports — "Seven of ten controls offered an already-rejected change as an option, versus none with recorded rationale." — evidence: empirical-llm (20 sessions, one fixture, external context file rather than inline comment)
  - [related-systems-and-researchers.md § 10. Keep the Why: a directly relevant existing rationale skill](../research/related-systems-and-researchers.md#10-keep-the-why-a-directly-relevant-existing-rationale-skill) — qualifies — "**Neither arm broke the wrapper.**" — evidence: empirical-llm
  - [pragmatic-programmer-037](../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-037) — supports — "If you can see what drove them to write code that way, you may find that the job of understanding it becomes a lot easier." — evidence: expert-opinion
- **Conditions / limits:** Keep the Why varied whether rationale was available, not where it was placed, and neither arm broke the code; the effect was on proposals. Preserving a rationale is not the same as preserving the code.
- **Eval signal:** maintain / preserved; audit / preserved; capture / recall; the re-proposal effect needs #19.

### P-21 — Treat comments you read as claims to check
- **Principle:** Before relying on an existing comment to make a change, check its claim against the code, tests and task evidence. When they disagree, fix whichever side is wrong, using evidence of intent.
- **Disposition:** core — low-risk and consistent with `maintain` and `audit`.
- **Grade:** D — that models follow wrong comments is empirical, but no study tests whether an instruction to verify reduces the harm; Comment Traps' "do not refer" instruction removed at most 21.84% of it.
- **Merged from:** LLM-20
- **Key citations:**
  - [comment-traps-029](../research/comment-context/sources/comment-traps/passages.md#comment-traps-029) — supports — "AI coding assistants do not merely replicate defective CO code verbatim; rather, they exhibit reasoning capabilities." — evidence: empirical-llm
  - [comments-bug-fixing-030](../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-030) — supports — "the model predicted a candidate fix that set the “answer”object in the event, leading to an analogous problem." — evidence: empirical-llm
  - [comment-traps-019](../research/comment-context/sources/comment-traps/passages.md#comment-traps-019) — supports — "developers or those who overly trust AI may unknowingly retain these flaws" — evidence: expert-opinion
- **Conditions / limits:** Verification costs exploration and tokens. Code-comment consistency alone cannot decide which side is wrong.
- **Eval signal:** maintain / behavior and bad_claims; audit / bad_claims.

### P-22 — Keep caller contracts at the interface and maintainer rationale in the implementation
- **Principle:** In an interface comment or docstring, state what callers may rely on (behaviour, inputs, outputs, errors, side effects, preconditions) and what is not promised. Put design reasoning and implementation detail inside the implementation, beside the code it explains. Do not hide from callers something they actually need.
- **Disposition:** core — consistent across traditions and tested by `misplaced`.
- **Grade:** B — cross-source expert consensus (Parnas, Google, Ousterhout, Pragmatic Programmer); no empirical test.
- **Merged from:** HIS-14, IND-09, IND-16, CRA-06, CRA-07
- **Key citations:**
  - [software-engineering-at-google-ch10-004](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-004) — supports — "API comments don’t need to discuss implementation details or design decisions and can’t assume a user is as versed in the API as the author." — evidence: expert-opinion
  - [philosophy-of-software-design-008](../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-008) — supports — "The interface of a module reflects what matters to users of that module; things that don't matter to the module's users should be hidden in the implementation," — evidence: expert-opinion
  - [pragmatic-programmer-021](../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-021) — supports — "or, more importantly, what it doesn't promise to deliver, before you write the code is a huge leap forward in writing better software." — evidence: expert-opinion
  - [software-engineering-at-google-ch14-001](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch14-001) — qualifies — "the effective user contract applies to all visible behaviors, not just a stated contract." — evidence: expert-opinion
- **Conditions / limits:** In a small private codebase the caller and the maintainer may be the same agent. Callers depend on any observable behaviour (Hyrum's Law), so a "may change" note protects the owner's decision more than it constrains callers. Where an assertion or type can express the contract, see AXIS-CODE-FIRST. Whether to add interface comments at all is AXIS-API-DOCS. Google ranks design documents above implementation comments for rationale (AXIS-PLACEMENT).
- **Eval signal:** capture / misplaced; maintain / bad_claims (a contract left false).

### P-23 — Write for a reader who has the code but not your session
- **Principle:** State the constraint itself, not "as discussed", "per the ticket" or "see above". Assume the next reader, whether a person or a fresh agent session, has the code but not your conversation, ticket or reasoning. A pointer to an issue is fine in addition to the stated fact.
- **Disposition:** core — low-risk and needed for anchors to match.
- **Grade:** B — cross-source expert consensus about human readers (Google, Ousterhout, Beck, Pragmatic Programmer); the fresh-agent framing is this project's extrapolation.
- **Merged from:** IND-17, CRA-15
- **Key citations:**
  - [software-engineering-at-google-ch10-003](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-003) — supports — "One of the most important mistakes that engineers make when writing documentation is to write only for themselves." — evidence: expert-opinion
  - [philosophy-of-software-design-006](../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-006) — supports — "Without adequate documentation, developers may have to read large amounts of code to reconstruct what was in the designer's mind." — evidence: expert-opinion
  - [beck-design-rules-003](../research/comment-context/sources/beck-design-rules/passages.md#beck-design-rules-003) — supports — "it reminds us that when writing code we should always be thinking of the reader." — evidence: expert-opinion
- **Conditions / limits:** Writing for a reader with no context pushes toward longer comments; P-10 bounds it. Whether LLM agents benefit as human newcomers do is the project's open hypothesis.
- **Eval signal:** capture / recall (anchor phrases must state the fact, not refer to it).

### P-24 — Put rationale the next editor needs in the source, not only in the commit, review thread or your report
- **Principle:** If the next editor of this code needs a reason to avoid breaking it, including the answer to a reviewer's or user's "why?" and any decision reached during the task, put it beside the code or make the code clearer. Leave the narrative of the change itself (what changed, which bug) to the commit or PR.
- **Disposition:** core — the eval scores only what lands in source files, and this matches the product intent. It is not the inline-versus-documents question (AXIS-PLACEMENT).
- **Grade:** C — Google practice and Pragmatic Programmer opinion; Google also treats review history as a legitimate record.
- **Merged from:** IND-18, IND-19, CRA-22
- **Key citations:**
  - [software-engineering-at-google-ch19-001](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch19-001) — supports — "following some technical decisions that are explained in code review interactions (e.g., when inline comments are lacking)." — evidence: historical-practice
  - [software-engineering-at-google-ch17-005](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch17-005) — supports — "given the rate of commits for machine-generated changes, naive “blame” tracking has less value than it does in more change-averse ecosystems." — evidence: historical-practice
  - [software-engineering-at-google-ch09-004](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch09-004) — supports — "If, during the code review process, a new decision is reached, update the change description, or add appropriate comments within the implementation." — evidence: historical-practice
  - [software-engineering-at-google-ch09-003](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch09-003) — opposes — "Moreover, because each change becomes part of the codebase, code review acts as a historical record." — evidence: historical-practice
- **Conditions / limits:** Google's history is easy to search through Code Search and Critique; most repositories and agents have nothing comparable. Not every review question signals a lasting gap. The boundary between rationale the code needs and change narrative is a judgment that each eval case must state.
- **Eval signal:** capture / recall (a fact stated only in the agent's final message scores zero).

### P-25 — Make the code carry the intent before writing a comment
- **Principle:** Before writing a comment, check whether a clearer name, a type, an assertion, a test or a structural change within the task's scope would carry the intent and be checked mechanically. Variants decide how far to go before falling back to prose.
- **Disposition:** variant-axis:AXIS-CODE-FIRST — the expert sources genuinely disagree, and the cost depends on task scope.
- **Grade:** C — expert opinion in conflict (Beck, Fowler, Pragmatic Programmer and Google against Ousterhout's objection to names as comments); no empirical test.
- **Merged from:** IND-01, IND-13, CRA-04, CRA-18
- **Key citations:**
  - [beck-design-rules-002](../research/comment-context/sources/beck-design-rules/passages.md#beck-design-rules-002) — supports — "the key to enabling understanding is to express your intention in the code, so that your readers can understand what your purpose was when writing it." — evidence: expert-opinion
  - [pragmatic-programmer-006](../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-006) — supports — "From our point of view, it simply compensates for some bad naming and layout." — evidence: expert-opinion
  - [philosophy-of-software-design-007](../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-007) — opposes — "Even with all these words, names like this are cryptic" — evidence: expert-opinion
  - [code-as-documentation-001](../research/comment-context/sources/code-as-documentation/passages.md#code-as-documentation-001) — qualifies — "Such a principle is not saying that code is the only documentation." — evidence: expert-opinion
- **Conditions / limits:** Renaming, adding tests or adding assertions changes code: it is forbidden in `audit` (AST comparison) and may be scope creep or break callers elsewhere. Tests document what is implemented, not what was intended. A name cannot carry rationale, so the why stays in prose under every position.
- **Eval signal:** restrain / noise_lines; audit / behavior (renames break AST equality); capture / behavior and recall.

### P-26 — Give each fact one home; point to it rather than copy it
- **Principle:** Do not repeat in a comment what the code, a type, a test, another comment or an owning document already states. When two places need the fact, explain it at the owner and point to it from elsewhere. Code that only coincidentally matches is not duplication.
- **Disposition:** core — consistent across traditions; how much to repeat at call sites is AXIS-REPEAT.
- **Grade:** B — cross-source expert consensus (Parnas, Beck, Google, Pragmatic Programmer); Ousterhout and Google's conceptual documents allow purposeful repetition.
- **Merged from:** HIS-05, IND-11, CRA-12
- **Key citations:**
  - [pragmatic-programmer-006](../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-006) — supports — "every piece of knowledge must have a single, unambiguous, authoritative representation within a system." — evidence: expert-opinion
  - [rational-design-process-009](../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-009) — supports — "There must be one, and only one, place for every fact that will be in the document." — evidence: expert-opinion
  - [beck-design-rules-002](../research/comment-context/sources/beck-design-rules/passages.md#beck-design-rules-002) — supports — "everything should be said “Once and only Once.”" — evidence: expert-opinion
  - [philosophy-of-software-design-010](../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-010) — opposes — "Another way to emphasize is with repetition: key ideas appear over and over again." — evidence: expert-opinion
- **Conditions / limits:** Parnas assumes a complete, reviewed external documentation set; where none exists, the comment may be the only home. A summary followed by detail within one comment is acceptable. Beck's rule concerns duplicated logic and applies to prose by extension.
- **Eval signal:** restrain / noise_lines; maintain / bad_claims (a duplicate left stale); capture / misplaced.

### P-27 — Explain a constant by its origin and ties; do not copy volatile values into prose
- **Principle:** When a literal comes from a derivation, a measurement, an external limit or another value, state that source or link so an editor knows what else must change with it. Do not restate numbers, rule tables or exception lists the code already holds, and keep fixed invariants distinct from changeable policy.
- **Disposition:** core — low-risk and consistent with `maintain` and `restrain`.
- **Grade:** C — Knuth, the FORTRAN manual and Pragmatic Programmer; no empirical test.
- **Merged from:** HIS-19, CRA-09, CRA-11
- **Key citations:**
  - [literate-programming-005](../research/comment-context/sources/literate-programming/passages.md#literate-programming-005) — supports — "It turns out that ord never exceeds 30 when m = 1000." — evidence: historical-practice
  - [pragmatic-programmer-006](../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-006) — supports — "The intent of this function is given twice. Once in the comment and again in the code. The customer changes a fee and we have to update both." — evidence: expert-opinion
  - [pragmatic-programmer-022](../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-022) — supports — "Be sure not to confuse requirements that are fixed, inviolate laws with those that are merely policies that might change with a new management regime." — evidence: expert-opinion
- **Conditions / limits:** A rationale sometimes must name a value ("must stay below the 30 s gateway timeout"); state the reason and point to the constant. Knuth's constant comments partly stand in for short Pascal names, which a descriptive name now replaces. The derivation still needs words.
- **Eval signal:** capture / recall; maintain / bad_claims; restrain / noise_lines.

### P-28 — Record a rejected design alternative at the choice
- **Principle:** When an attractive alternative was actually considered and rejected, a short note at the choice ("not X, because Y") can stop a later editor reverting to it. Whether that note belongs inline or in the commit, an ADR or the report is open.
- **Disposition:** variant-axis:AXIS-REJECTED-ALT — supported in principle, but placement and length are contested.
- **Grade:** C — Parnas, von Neumann, Knuth and Pragmatic Programmer; the Keep the Why result (P-20) concerns rationale availability in an external file, not inline placement.
- **Merged from:** HIS-02
- **Key citations:**
  - [rational-design-process-010](../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-010) — supports — "recording all of the design alternatives that we considered and rejected. For each, we explain why it was considered and why it was finally rejected." — evidence: expert-opinion
  - [planning-and-coding-075](../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-075) — supports — "the first method is about ... We will nevertheless code this Probletn according to the second method, because this offers a good opportunity to exemplify" — evidence: historical-practice
  - [historical-comment-design.md, "Candidate taxonomy to test"](../research/historical-comment-design.md#candidate-taxonomy-to-test) — qualifies — "At the consequential choice; longer deliberation elsewhere." — evidence: expert-opinion
  - [pragmatic-programmer-005](../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-005) — supports — "when you make decisions, document those decisions somehow, write them in your day book or make a note in the code." — evidence: expert-opinion
- **Conditions / limits:** Only alternatives the evidence shows were considered; an invented "we considered X" is a bad claim (P-02). Parnas recorded every alternative in external documents; inline, keep only the one a future editor would plausibly reach for. Version control now holds chronology, which none of these authors had.
- **Eval signal:** capture / recall and bad_claims; noise_lines.

### P-29 — Describe the design as it now stands
- **Principle:** Write comments as the account of the current design. Do not narrate the path ("previously this used X", "after debugging we found"). When a change alters the design, rewrite the explanation as if the new design had been the original; version control holds the history.
- **Disposition:** core — low-risk and directly tested by stale-text claims.
- **Grade:** C — Parnas and Clements; Knuth qualifies it by treating composition order as a good reading order.
- **Merged from:** HIS-03
- **Key citations:**
  - [rational-design-process-010](../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-010) — supports — "Those who read the softwa re documentation want to unders tand the programs, not to relive their discovery." — evidence: expert-opinion
  - [rational-design-process-008](../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-008) — supports — "If a change invalidates a design document, it and all subsequent design documents must be faked to look as if the change had been the original design." — evidence: expert-opinion
  - [literate-programming-011](../research/comment-context/sources/literate-programming/passages.md#literate-programming-011) — qualifies — "the decisions that Dijkstra made as he composed the original program2 appear in the WEB documentation in the same order." — evidence: historical-practice
- **Conditions / limits:** Rejected alternatives are the exception (AXIS-REJECTED-ALT). Parnas's "faking" assumes a reviewed, disciplined documentation process.
- **Eval signal:** maintain / bad_claims (stale "previously..." text) and noise_lines (appended amendment notes instead of revision).

### P-30 — Interface comments: every exported entry point, or only where the contract is not obvious
- **Principle:** An interface comment lets a caller use code without reading its body, but comment-every-function mandates produce boilerplate. Variants decide how many public entry points get one.
- **Disposition:** variant-axis:AXIS-API-DOCS — the sources disagree on breadth and the `restrain` family is sensitive to it.
- **Grade:** C — Pragmatic Programmer, Ousterhout and Google practice disagree; no empirical test.
- **Merged from:** CRA-05
- **Key citations:**
  - [pragmatic-programmer-004](../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "we recommend adding comments to modules and exported functions to give other developers a leg up." — evidence: expert-opinion
  - [philosophy-of-software-design-007](../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-007) — supports — "instead of reading the entire body of a method, a developer can read a short interface comment to get all the information they need in order to invoke the method." — evidence: expert-opinion
  - [pragmatic-programmer-004](../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "this doesn't mean we agree with the folks who say that every function, data structure, type declaration, etc. needs its own comment." — evidence: expert-opinion
  - [software-engineering-at-google-ch10-005](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-005) — opposes — "All public classes (and structs) at Google must contain a class comment describing the class/struct, important methods of that class, and the purpose of the class." — evidence: historical-practice
- **Conditions / limits:** Repository linters or style guides that require docstrings override both positions. Google's mandate assumes external API consumers. Neither source tests whether agents read interface comments before calling.
- **Eval signal:** restrain / noise_lines; capture / misplaced and recall.

### P-31 — Match the local comment form and vocabulary
- **Principle:** Follow the comment and docstring form already used in the file, then the module, then the project, and use the project's established terms for its concepts. When you write a reference comment and no convention exists, lead with what the unit does in integrated prose, with the key fact first.
- **Disposition:** core — low-risk; form is not scored.
- **Grade:** C — Google practice and Pragmatic Programmer, with Parnas on organising documents around readers' questions.
- **Merged from:** IND-10, IND-22, CRA-21, HIS-16
- **Key citations:**
  - [software-engineering-at-google-ch08-003](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch08-003) — supports — "“Be consistent” starts locally, where the norms within a given file precede those of a given team" — evidence: historical-practice
  - [software-engineering-at-google-ch10-006](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-006) — supports — "It is often clearer to present such information in a single prose comment that’s not broken up into artificial section boundaries:" — evidence: historical-practice
  - [pragmatic-programmer-047](../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-047) — supports — "It's important that everyone on the team knows what these words mean and that they use them consistently." — evidence: expert-opinion
  - [rational-design-process-009](../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-009) — supports — "Each document is designed by stating the questions that it must answer" — evidence: expert-opinion
- **Conditions / limits:** Local consistency does not justify copying a bad habit such as restating comments or commented-out code. Projects whose docstring conventions require `Args:` and `Returns:` sections override integrated prose. Question-driven organisation matters mainly for long module or type headers.
- **Eval signal:** not covered by comment-edit (anchor grading ignores form; consistent vocabulary may help anchors incidentally).

### P-32 — In tests, let names and structure explain
- **Principle:** Rely on test names and arrange/act/assert layout. Add section comments only to tests complex enough that their stages are not obvious, and explain why a test value or helper default was chosen when that is not evident.
- **Disposition:** core — low-risk, and it extends P-09 to tests.
- **Grade:** C — Google practice only.
- **Merged from:** IND-23
- **Key citations:**
  - [software-engineering-at-google-ch12-005](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch12-005) — supports — "This level of description isn’t always necessary in trivial tests, and it’s usually sufficient to omit the comments and rely on whitespace to make the sections clear." — evidence: historical-practice
  - [software-engineering-at-google-ch12-005](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch12-005) — supports — "However, explicit comments can make more sophisticated tests easier to understand." — evidence: historical-practice
  - [software-engineering-at-google-ch12-010](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch12-010) — supports — "it can be difficult to understand why a particular value was chosen for a test." — evidence: expert-opinion
- **Conditions / limits:** Frameworks such as Cucumber build the structure into the test itself.
- **Eval signal:** restrain / noise_lines when the task adds a simple test.

### P-33 — Inline explanation versus a linked document
- **Principle:** Explanation owned by one nameable scope goes beside that code. For explanation spanning several modules, or a long external argument (a proof, a specification, a design record), the sources split between stating the property locally and pointing outward, and keeping everything in the source people edit.
- **Disposition:** variant-axis:AXIS-PLACEMENT — product-level; the placement pilot (#9) owns it, and skill variants stay inline-focused unless the user decides otherwise.
- **Grade:** C — expert and historical opinion in direct conflict (Parnas and Google design documents against Knuth's single source and Pragmatic Programmer's "keep code and documentation together"); no direct empirical test of placement.
- **Merged from:** HIS-09, HIS-18, IND-12
- **Key citations:**
  - [literate-programming-013](../research/comment-context/sources/literate-programming/passages.md#literate-programming-013) — supports — "it is therefore customary to work with hardcopy documentation that is slightly obsolete" — evidence: historical-practice
  - [software-engineering-at-google-ch10-009](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-009) — supports — "The only logical place to document such complex behavior is through a separate conceptual document." — evidence: expert-opinion
  - [planning-and-coding-020](../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-020) — supports — "sorp reference to the place where the proof can be found ney be made" — evidence: expert-opinion
  - [software-engineering-at-google-ch03-005](../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch03-005) — supports — "the documentation is predictably located right next to the source code, as opposed to off in an (unfindable) document or webpage somewhere." — evidence: historical-practice
- **Conditions / limits:** Knuth's single source is a WEB file that tooling weaves and tangles, which he distinguishes from well-commented Pascal. A pointer must name something that exists and that the agent has read (P-02). Variants must not create separate documents.
- **Eval signal:** capture / misplaced in part; otherwise not covered by comment-edit (needs #9, #19 or #20).

## Variant axes

Each axis is an open disagreement for the tournament to test, not to settle by
editorial choice. A variant takes one position per axis it varies and the core
principles everywhere. Predicted signatures are hypotheses about the offline
`comment-edit` proxy; the grader's known limitations (anchors miss paraphrase;
see `docs/evaluation/skill-evals.md`) apply to every prediction.

### AXIS-CONTENT — What kind of comment should the agent write?
- Positions: (a) why-only: rationale, purpose and constraints, never what or how outside interface comments; (b) why plus the decisive what or how: rationale, and also the mechanism or the single decision that rules out a wrong approach when it is non-obvious; (c) gap-driven: no category rule, write whatever the next reader would lack.
- Evidence for each: (a) P-11 (CRA-01), P-09 (HIS-06, CRA-03); (b) P-11 (LLM-18), P-06 (LLM-13), P-08 (LLM-12); (c) P-11 (LLM-19), P-10 (CRA-16).
- Predicted eval signature: (a) lowest noise_lines on restrain, but lower capture recall where the required fact is a mechanism or decisive choice; (b) higher capture recall, more noise_lines, and more maintain bad_claims risk because mechanism claims drift; (c) between the two, with the most run-to-run variance because the judgment is unconstrained.

### AXIS-DENSITY — How much should the agent write?
- Positions: (a) sparse: comment only what would strain a capable reader; (b) newcomer: record the major decisions a fresh or weaker session would lack, even if a strong model could infer them; (c) budgeted: newcomer content, capped per change at a fixed number of comment blocks.
- Evidence for each: (a) P-12 (HIS-07), P-10 (LLM-07, LLM-16, IND-24); (b) P-12 (HIS-17, LLM-15), P-23 (IND-17, CRA-15), P-05 (CRA-17); (c) P-10 (CRA-16).
- Predicted eval signature: (a) passes restrain, risks capture recall; (b) raises capture recall and noise_lines, likely fails some restrain budgets; (c) protects restrain at some recall cost on cases with several required facts. Model-tier benefits are invisible to the single-model proxy (#19, #20).

### AXIS-CODE-FIRST — Make code carry intent first, or write the explanation?
- Positions: (a) code-first: within task scope, prefer a clearer name, type, assertion or test, and comment only what remains; (b) comment-first: leave code structure as the task requires and explain in prose; (c) family-aware: code-first only when the request allows code changes, never in a comment-only request.
- Evidence for each: (a) P-25 (IND-01, IND-13, CRA-04, CRA-18); (b) P-25 (opposing Ousterhout quote), P-05 (CRA-17), P-18 (CRA-10 limits); (c) P-25 conditions.
- Predicted eval signature: (a) fewer noise_lines, but audit behavior failures (AST changes) and possible behavior regressions or lower recall when a rename replaces a needed why; (b) higher recall and noise_lines, audit-safe; (c) should match (a) on restrain and (b) on audit.

### AXIS-UNVERIFIED — What to do with a reason the evidence does not establish?
- Positions: (a) omit: write nothing about it; (b) hedge inline: write it with a visible marker ("presumably", "reason unknown"); (c) report: leave the code silent and tell the user about the gap outside the code.
- Evidence for each: (a) P-02 (LLM-05); (b) P-02 (HIS-12: the FORTRAN "presumably" and Parnas's "information unavailable" slot); (c) P-02 (LLM-05: ask for the missing decision), P-14 (LLM-09: hedges do not disarm wrong content).
- Predicted eval signature: (a) and (c) score the same on the proxy (zero bad_claims, zero noise); (c)'s value lies in the final message, which comment-edit does not grade. (b) adds noise_lines, and a hedged claim that matches a forbidden anchor still counts as a bad claim, because the grader cannot see the hedge.

### AXIS-COMMENTED-OUT — Existing commented-out code near the edit: delete or flag?
- Positions: (a) delete it when it sits in the scope being edited; (b) leave it and flag it in the report; (c) delete only in a comment-refresh request, flag otherwise.
- Evidence for each: (a) P-17 (LLM-08), P-16 (IND-15, CRA-20); (b) P-17 (comment-traps-003 opposing quote), P-13 (LLM-17: do not strip as a goal); (c) both.
- Predicted eval signature: (a) helps only if a case plants commented-out code as a forbidden claim, and costs preserved if a case protects it; (b) neutral on current metrics; (c) between. Mostly not covered by comment-edit until a case plants commented-out code.

### AXIS-STALE — A false comment: correct it in place or delete it?
- Positions: (a) correct: rewrite it to the new truth when the fact is still worth stating; (b) delete: remove it and add a fresh comment only if a required fact needs one; (c) correct rationale, delete restatement.
- Evidence for each: (a) P-15 (IND-08), P-01 (CRA-13); (b) P-15 (Wen et al. citation), P-01 (LLM-03: revise or delete); (c) P-09 with P-15.
- Predicted eval signature: (a) keeps maintain recall; a correction longer than the stale text spends noise_lines; (b) zero noise but recall loss where the corrected fact was required, and preserved loss if a still-valid part was deleted; (c) should pass most maintain cases if budgets allow one corrected block.

### AXIS-REJECTED-ALT — Rejected design alternatives: inline, or elsewhere?
- Positions: (a) inline at the choice, one line naming the alternative and why it lost; (b) only in the commit message or the agent's report; (c) inline only when the alternative is one a future editor would plausibly reintroduce (a natural-looking simplification or optimisation).
- Evidence for each: (a) P-28 (HIS-02), P-05 (CRA-02), P-20 (IND-06); (b) P-29 (HIS-03), P-24 opposing citation (review history as record); (c) P-28 conditions, P-06 (LLM-13).
- Predicted eval signature: (a) raises capture recall on cases whose required fact is a rejected alternative, with more noise and a higher risk of invented alternatives (bad_claims); (b) scores zero recall for those facts; its value only appears downstream (#19); (c) close to (a) on recall with less noise.

### AXIS-PLACEMENT — Inline in the source, or in an external document?
- Positions: (a) inline only; (b) linked hybrid: the local fact inline, with a pointer to an existing document for cross-module or long explanation; (c) document-first for rationale, with comments limited to contracts and pointers.
- Evidence for each: (a) P-33 (HIS-18), P-24 (CRA-22); (b) P-33 (HIS-09, IND-12); (c) P-33 (Google ch10-009), P-26 (HIS-05).
- Predicted eval signature: (c) would fail capture recall and raise misplaced, because the proxy scores comments. The question cannot be answered by comment-edit. **#9 owns this axis.** Skill variants stay at (a), or (b) restricted to documents that already exist, unless the user decides otherwise.

### AXIS-API-DOCS — How many public entry points get an interface comment?
- Positions: (a) every new or changed exported symbol gets a contract docstring; (b) only where the contract is not obvious from name and signature; (c) follow whatever the repository already does.
- Evidence for each: (a) P-30 (CRA-05; Google ch10-005 mandate); (b) P-30 (CRA-03 quote), P-09; (c) P-31 (IND-22).
- Predicted eval signature: (a) fails restrain noise budgets where the change adds or touches public functions; (b) baseline; (c) depends on the case repository, so it is the most context-sensitive.

### AXIS-REPEAT — State a constraint only at its owner, or also where it is used?
- Positions: (a) owner only; (b) owner plus a short pointer at call sites that depend on it; (c) owner plus a one-line restatement at dependent call sites.
- Evidence for each: (a) P-26 (CRA-12, IND-11, HIS-05); (b) P-26 conditions; (c) P-26 (philosophy-of-software-design-010 opposing quote on emphasis by repetition).
- Predicted eval signature: (a) lowest noise, and misplaced unaffected because recall is scored at the owner; (b) slightly more noise; (c) more noise and more maintain bad_claims when a later change updates one copy and not the other.

## Rejected or deferred candidates

Every other candidate is merged into a principle above.

| Candidate id | Reason |
| --- | --- |
| HIS-10 | Does not transfer: the source case is self-modifying machine code, and the extension to code generation, decorators or overrides is untested. Low confidence even by its own map file. The general idea (flag where behaviour differs from what the text shows) survives in P-19. |
| HIS-21 | Deferred: a process claim ("if you cannot write why, investigate") resting on Knuth's self-report, which he tells readers to discount. It produces no comment output that comment-edit can grade (needs #19). It also invites filled-in reasons, which P-02 forbids. |
| CRA-14 | Deferred: an intent-first one-sentence comment belongs to a disposable prototype in its source, and the content of Ousterhout's comment-first chapter is not in the local extract. Process, not output; not covered by comment-edit. |
| IND-14 | Out of scope for a comment skill: deprecation is an API mechanism (`@deprecated`, warnings) whose value depends on Google's tooling. It is a code change, and no eval family covers it. |
