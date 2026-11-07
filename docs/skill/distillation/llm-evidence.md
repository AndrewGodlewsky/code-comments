# Distillation: Empirical evidence on comments for LLMs and coding agents

Sources read:

- `documentation-llm-understanding/passages.md` (Macke and Doyle 2024): all 20 passages read in full.
- `comment-traps/passages.md` (Huang et al. 2025): all 49 passages read in full, including figure transcriptions.
- `comments-bug-fixing/passages.md` (Vitale et al. 2026): all passages read in full except 007-009 (model background and related work), which were skimmed.
- `talking-while-coding/passages.md` (Pan et al. 2026): 001-047, 050-061 and 071-079 read in full. 048-049, 062-070 and 080-081 (model pools, decoding settings, per-model form and token tables) were skimmed by heading only.
- Secondary syntheses, read in full: `docs/research/agent-context-evidence.md`, `docs/research/comment-context-deep-dive.md`, `docs/research/comment-maintenance-and-evaluation.md`, `docs/research/ai-code-comments/README.md`. I also read `docs/research/ai-code-comments/when-comments-mislead-unavailable.md`.
- *When Comments Mislead* (Xia et al., ASE 2026) has **no primary text** in this repository. Only its conference abstract is described, through the secondary reports. It is cited here only through those reports, and nothing below depends on its numbers.

Reading conventions used below:

- Pan et al. report deltas such as "17.2%" and "20.8%". By my arithmetic from Table 1 (talking-while-coding-012), these are mean **percentage-point** differences from a matched-subset baseline. Comment Traps' "58.17%" is a **relative** increase in CodeQL-flagged defect counts, not a defect rate. Vitale et al. report **exact match** against a reference patch, not execution-based repair.
- All four primary studies measure one bounded task: test generation, single-method repair, completion at a cursor, or single-shot code generation with a prefilled comment block. None tests comments kept in a repository through successive agent edits. Every "agent" implication below therefore extrapolates beyond these settings.

## Candidate principles

### LLM-01 — Never leave a comment that is wrong about the code it sits on
- **Principle:** A comment that contradicts the code or describes a different unit is worse than no comment. Remove or correct it before you finish the edit.
- **Kind:** maintain
- **Sources:**
  - [documentation-llm-understanding-012](../../research/comment-context/sources/documentation-llm-understanding/passages.md#documentation-llm-understanding-012) — supports — "the random comments scenario performs worse than any other scenario on both GPT-3.5 and 4 (only 22.1% and 68.1% successes respectively)" — evidence: empirical-llm
  - [documentation-llm-understanding-018](../../research/comment-context/sources/documentation-llm-understanding/passages.md#documentation-llm-understanding-018) — supports — "but incorrect comments still confuse the LLMs" — evidence: empirical-llm
  - [talking-while-coding-017](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-017) — supports — "wrong-topic by 20.8% across 12 cells and random text by 17.9% on average (Table 14)." — evidence: empirical-llm
  - [comments-bug-fixing-035](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-035) — supports — "Comments generated from buggy code do not help and can mislead automated bug-fixing models." — evidence: empirical-llm
  - [documentation-llm-understanding-013](../../research/comment-context/sources/documentation-llm-understanding/passages.md#documentation-llm-understanding-013) — qualifies — "the proportion of errors and failed tests did not change between the base file with/without comments by a statistically significant margin" — evidence: empirical-llm
- **Conditions / limits:**
  - Macke and Doyle's "random comments" condition used a docstring from a *different* HumanEval function. It was not a subtly stale comment. GPT-3.5 and GPT-4 generated unit tests for 164 short functions, and the authors flag possible HumanEval contamination.
  - In that study, successes fell from a 44.7% baseline to 22.1% for GPT-3.5 and from 78.5% to 68.1% for GPT-4 (documentation-llm-understanding-013). Correct comments gave no significant gain in test success.
  - Pan et al.'s wrong-topic block is a prefill at the head of the model's own output, not a persisted repository comment.
  - The asymmetry is consistent across studies. Correct comments sometimes help a lot and sometimes not at all, but wrong comments reliably hurt.
- **Tension:** Conflicts with any "when in doubt, leave the old comment" conservatism. Also interacts with LLM-17: do not delete *correct* comments wholesale.
- **Testable as:** maintain / bad_claims; audit / bad_claims.

### LLM-02 — Make every clause true: one wrong step cancels the comment's value
- **Principle:** Check each clause of a comment you write or keep against the final code, not just its gist. One wrong step or algorithm name in an otherwise correct block can remove the benefit, and one inaccurate clause can steer a fix wrong.
- **Kind:** what
- **Sources:**
  - [talking-while-coding-015](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-015) — supports — "replacing the algorithm name or one key step while preserving length, line count, and tone" — evidence: empirical-llm
  - [talking-while-coding-016](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-016) — supports — "the corrupted condition falls back to the baseline range" — evidence: empirical-llm
  - [comments-bug-fixing-032](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-032) — supports — "We tried to change the comment by removing such a part of the comment, and this resulted in a correct fix." — evidence: empirical-llm
  - [comments-bug-fixing-032](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-032) — supports — "their completeness and correctness is key to fix bugs." — evidence: empirical-llm
- **Conditions / limits:**
  - In Pan et al., about 2.3 of roughly 10 comment lines were changed, and 50 samples were verified by hand. Qwen3-8B fell from 70.8% (correct) to 48.2% (corrupted), against a 53.6% baseline.
  - The Vitale et al. clause-removal case is a single anecdote (Figure 4), not a measured rate.
- **Tension:** Pulls against long multi-intent docstrings: more clauses means more surface that can go false (see LLM-18).
- **Testable as:** capture / bad_claims; maintain / bad_claims.

### LLM-03 — When your change falsifies a comment, revise or delete it in the same edit
- **Principle:** After changing behavior, find every comment and docstring whose claim the change makes false, including callers and interfaces. Fix or remove each one in the same diff, because a stale comment can pull later completions back toward the old implementation.
- **Kind:** maintain
- **Sources:**
  - [comment-context-deep-dive.md § Stale or defective annotations can transmit the wrong behavior](../../research/comment-context-deep-dive.md#stale-or-defective-annotations-can-transmit-the-wrong-behavior) — supports — "reports completion biased toward historical implementations under outdated comments" — evidence: empirical-llm
  - [comment-context-deep-dive.md § Stale or defective annotations can transmit the wrong behavior](../../research/comment-context-deep-dive.md#stale-or-defective-annotations-can-transmit-the-wrong-behavior) — qualifies — "Sample size, effect sizes, and controls remain unverified." — evidence: empirical-llm
  - [ai-code-comments/README.md § Reading notes](../../research/ai-code-comments/README.md#reading-notes) — qualifies — "only the conference abstract was available in this research session; its full methods and effect sizes have not been checked." — evidence: empirical-llm
  - [comment-maintenance-and-evaluation.md § Wen, Nagy, Bavota, and Lanza (2019): proximity does not prevent drift](../../research/comment-maintenance-and-evaluation.md#wen-nagy-bavota-and-lanza-2019-proximity-does-not-prevent-drift) — supports — "Rationale comments also become obsolete and sometimes need deletion." — evidence: empirical-human
  - [documentation-llm-understanding-018](../../research/comment-context/sources/documentation-llm-understanding/passages.md#documentation-llm-understanding-018) — supports — "we do show that incorrect comments do significantly affect an LLM’s ability to understand a piece of code." — evidence: empirical-llm
- **Conditions / limits:**
  - The only study aimed squarely at *outdated* comments and LLMs (*When Comments Mislead*) is abstract-only here.
  - The other LLM evidence uses proxies for staleness: unrelated docstrings, wrong-topic prefixes, and comments generated from buggy code. It does not use comments that went stale naturally.
  - Wen et al. is an observational study of human-maintained Java histories.
- **Tension:** Correcting a comment costs noise lines in the current grader, while deleting it is free (skill-evals "Known grader limitations"). A skill could learn to delete rather than correct.
- **Testable as:** maintain / bad_claims and recall; audit / bad_claims.

### LLM-04 — State intended behavior from evidence, not a paraphrase of the code as written
- **Principle:** When you document what code should do, take the contract from requirements, tests, tickets or the corrected implementation. Do not take it from the code you are reading, because that code may be the bug. A comment that faithfully explains buggy logic gives a later agent no way to see the bug.
- **Kind:** what
- **Sources:**
  - [comments-bug-fixing-017](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-017) — supports — "The comments generated from it might reflect such errors." — evidence: empirical-llm
  - [comments-bug-fixing-035](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-035) — supports — "since they document the buggy logic rather than the intended" — evidence: empirical-llm
  - [comments-bug-fixing-011](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-011) — supports — "where subtle requirements—such as sorting criteria—are conveyed through comments." — evidence: expert-opinion
  - [comment-context-deep-dive.md § Vitale and colleagues: repair gains include answer-derived information](../../research/comment-context-deep-dive.md#vitale-and-colleagues-repair-gains-include-answer-derived-information) — supports — "This directly limits the inference that automatically explaining existing code supplies useful repair knowledge." — evidence: empirical-llm
- **Conditions / limits:**
  - The bug-fixing gains came from comments generated from the *fixed* method, an oracle unavailable in practice. With comments generated from the buggy code, exact match was flat or worse (CodeT5+ 3.26% to 2.92%).
  - The models were small (220M and 1.3B), fine-tuned, and tested on isolated Java methods.
  - The `sorted(list)` case-sensitivity example (comments-bug-fixing-010/011) is an authors' thought experiment.
- **Tension:** A coding agent usually has only the current code. This principle and LLM-05 together imply that the agent often should *not* write a behavioral contract when it lacks evidence of intent.
- **Testable as:** capture / bad_claims (when the evidence contradicts the code); maintain / recall.

### LLM-05 — Do not manufacture rationale; leave unknown reasons unstated
- **Principle:** Write a why only when the evidence in hand (a requirement, test, ticket, commit or verified reference) supports it. Otherwise leave it out, or flag that the reason is unknown. A plausible but wrong explanation can harm a later model, and a confident tone does not make it helpful.
- **Kind:** avoid
- **Sources:**
  - [comment-maintenance-and-evaluation.md § Working hypothesis for this project](../../research/comment-maintenance-and-evaluation.md#working-hypothesis-for-this-project) — supports — "When evidence for a rationale is missing, it should leave that rationale unstated or ask for the missing decision instead of manufacturing an explanation." — evidence: expert-opinion
  - [talking-while-coding-014](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-014) — supports — "content describing a wrong solution leaves pass@1 essentially unchanged on the source-fail subset" — evidence: empirical-llm
  - [talking-while-coding-005](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-005) — supports — "probes find LLM-emitted comments themselves often" — evidence: empirical-llm
  - [documentation-llm-understanding-018](../../research/comment-context/sources/documentation-llm-understanding/passages.md#documentation-llm-understanding-018) — supports — "but incorrect comments still confuse the LLMs" — evidence: empirical-llm
- **Conditions / limits:**
  - The Kang et al. finding that LLM-emitted comments are often inaccurate is reported second-hand by Pan et al.; the sentence continues "inac-curate".
  - Pan et al.'s source-wrong null is confounded by floor effects, as the authors themselves flag (talking-while-coding-014). Wrong but *plausible* rationale in persistent comments has not been measured directly.
- **Tension:** Pulls against the capture family's push to record the why. Resolve it by requiring evidence, not by reducing capture.
- **Testable as:** capture / bad_claims (planted plausible-but-rejected rationale).

### LLM-06 — Explain only what names, types and code do not already say
- **Principle:** Do not restate what the code visibly does or what the function name already conveys. Comments that duplicate recoverable information showed little measurable benefit for models. Spend comment lines on information a reader cannot get from the code.
- **Kind:** avoid
- **Sources:**
  - [documentation-llm-understanding-018](../../research/comment-context/sources/documentation-llm-understanding/passages.md#documentation-llm-understanding-018) — supports — "correct comments do not add much information as it would be relevant to the creation of unit tests" — evidence: empirical-llm
  - [comments-bug-fixing-029](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-029) — supports — "there are generally other elements that help the model graspwhatthe method is aimed to do (e.g.,the method name or the identifiers)" — evidence: empirical-llm
  - [talking-while-coding-009](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-009) — supports — "# Sort the array only restates what the next line of code does" — evidence: expert-opinion
  - [agent-context-evidence.md § 6. Repository context files change behavior without proven general success gains](../../research/agent-context-evidence.md#6-repository-context-files-change-behavior-without-proven-general-success-gains) — supports — "A documentation-removal ablation yields +2.7 points for generated files. This suggests redundancy matters." — evidence: empirical-llm
  - [comments-bug-fixing-029](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-029) — qualifies — "The models give contrasting importance towhat comments." — evidence: empirical-llm
  - [documentation-llm-understanding-014](../../research/comment-context/sources/documentation-llm-understanding/passages.md#documentation-llm-understanding-014) — qualifies — "code with comments generated a higher average line coverage than all other methods" — evidence: empirical-llm
- **Conditions / limits:**
  - "Does not add much information" is the authors' conjecture about a null result.
  - SHAP importance is a token-attribution estimate, and the authors caution about it (comments-bug-fixing-039).
  - DeepSeek-Coder weighted "what" comments relatively highly.
  - Correct docstrings raised line coverage even without raising test success. "No benefit" is too strong a reading.
- **Tension:** Partly opposes LLM-17 (do not strip existing comments). Opposes "document everything" readings of the authors' own practical advice (comments-bug-fixing-036).
- **Testable as:** restrain / noise_lines; capture / noise_lines.

### LLM-07 — Do not add comments for volume; comment quantity does not track model performance
- **Principle:** Do not raise comment density as a goal. Across models, how much a model comments shows no reliable link to its success. Verbose comment policies multiply tokens with model-dependent effects on accuracy.
- **Kind:** when
- **Sources:**
  - [talking-while-coding-002](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-002) — supports — "a 700-fold gap that is invisible in pass@1" — evidence: empirical-llm
  - [talking-while-coding-025](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-025) — supports — "Compliance with the form instruction does not predict whether pass@1 goes up or down." — evidence: empirical-llm
  - [talking-while-coding-061](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-061) — supports — "The verbose form variants (top,dense,inline) inflate mean tokens to 0.7–2.6× thebasevalue" — evidence: empirical-llm
  - [documentation-llm-understanding-016](../../research/comment-context/sources/documentation-llm-understanding/passages.md#documentation-llm-understanding-016) — supports — "has little to no significant effect on an LLM’s understanding" — evidence: empirical-llm
  - [comment-maintenance-and-evaluation.md § Steidl, Hummel, and Juergens (2013): quality is not quantity](../../research/comment-maintenance-and-evaluation.md#steidl-hummel-and-juergens-2013-quality-is-not-quantity) — supports — "Comment density alone cannot distinguish useful explanation from irrelevant or obsolete material." — evidence: empirical-human
- **Conditions / limits:**
  - The 88-model observation concerns comments a model emits in its own output on LiveCodeBench, not comments read later from a repository.
  - The `dense` policy did help some models significantly (Qwen3-8B +4.3 points, GPT-5.4-Nano +5.8, per Table 4 in talking-while-coding-079) while hurting others. "No effect" is wrong; "model-dependent and not reliably positive" is right.
- **Tension:** Opposes the authors' practical advice in comments-bug-fixing-036 ("thoroughly documenting code"). That advice rests on oracle comments.
- **Testable as:** restrain / noise_lines.

### LLM-08 — Delete commented-out code instead of leaving it beside live code
- **Principle:** Do not leave disabled code in comments near code that you or a later agent will edit. Remove it, since version control keeps it. Models treat commented-out code as a pattern to reason from and complete, not as inert text.
- **Kind:** avoid
- **Sources:**
  - [comment-traps-001](../../research/comment-context/sources/comment-traps/passages.md#comment-traps-001) — supports — "defective CO code in the context causes AI coding assistants to generate more defective code, reaching up to 58.17 percent." — evidence: empirical-llm
  - [comment-traps-019](../../research/comment-context/sources/comment-traps/passages.md#comment-traps-019) — supports — "the AI still uses it as a reference when generating new code, thereby introducing defects in a way that may go unnoticed by developers." — evidence: empirical-llm
  - [comment-traps-022](../../research/comment-context/sources/comment-traps/passages.md#comment-traps-022) — supports — "are not fully robust to randomly CO code" — evidence: empirical-llm
  - [comment-traps-003](../../research/comment-context/sources/comment-traps/passages.md#comment-traps-003) — opposes — "It is commonly used for debugging, experimenting with alternative implementations, or preserving legacy logic for potential future use." — evidence: historical-practice
  - [ai-code-comments/README.md § Reading notes](../../research/ai-code-comments/README.md#reading-notes) — qualifies — "studies defective commented-out executable code, not ordinary explanatory prose. Its maximum 58.17% increase is relative, not a defective-output percentage." — evidence: empirical-llm
- **Conditions / limits:**
  - Huang et al. tested 1,000 Python samples × 11 insertion positions, using Copilot 1.257.0 and Cursor 0.44.11 with GPT-4o and Claude 3.5 Sonnet, and scored with CodeQL.
  - The defects were deliberately injected, cut from the same file. The mean relative increase was over 20% per tool/model.
  - Copilot showed a "Latter-Position Augmentation Effect": below-cursor commented-out code raised defects by more than 43%, against about 10% above (comment-traps-021). This suggests the risk is highest just below an edit point, at least for fill-in-the-middle tools.
  - Even random, defect-free commented-out code shifted outputs away from baseline in most settings.
  - The authors exclude TODOs and plain-text comments from scope (comment-traps-035).
- **Tension:** Developers keep commented-out code deliberately (comment-traps-003). An `audit` that deletes it may be refused by a user. This should probably be a variant axis: delete it, versus flag it in the report and leave it.
- **Testable as:** audit / bad_claims and preserved (only if a case plants commented-out code). Otherwise not covered by comment-edit.

### LLM-09 — Do not try to disarm misleading text with labels or "ignore this" notes
- **Principle:** If a comment or a commented-out block is wrong or obsolete, remove or correct it. Do not prefix it with a warning, a tag, a hedge, or an instruction to ignore it. Models still use the content.
- **Kind:** maintain
- **Sources:**
  - [comment-traps-029](../../research/comment-context/sources/comment-traps/passages.md#comment-traps-029) — supports — "AI coding assistants still recognize the defective CO code and introduce additional defects during generation." — evidence: empirical-llm
  - [comment-traps-031](../../research/comment-context/sources/comment-traps/passages.md#comment-traps-031) — supports — "the highest reduction rate was only 21.84%, which is still insufficient for effectively eliminating defects." — evidence: empirical-llm
  - [comment-traps-027](../../research/comment-context/sources/comment-traps/passages.md#comment-traps-027) — supports — "tools do not simply copy code from the CO code but instead use contextual information to infer and reconstruct complete defects from partial defective fragments." — evidence: empirical-llm
  - [talking-while-coding-016](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-016) — qualifies — "only removing specific task information hurts, and wording, length, and tone do not" — evidence: empirical-llm
- **Conditions / limits:**
  - The evidence on tagging, truncation and "Do not refer to the commented-out code." comes from commented-out code, not prose comments.
  - Instruction-induced reductions ranged from 4.93% to 21.84% (relative). They were tested only at the "below 1 line" position.
  - The Pan et al. result is an extrapolation: hedging a *correct* comment did not remove its lift. By analogy, hedging a *wrong* comment ("probably", "may be outdated") is unlikely to remove its harm. This analogy is untested.
- **Tension:** The Comment Traps authors count tagging a success *for alerting humans* ("successfully alerts developers while minimizing interference with the AI model", comment-traps-029). Human-facing and model-facing goals diverge here.
- **Testable as:** maintain / bad_claims; audit / bad_claims (a stale claim kept under an "outdated:" label still matches forbidden-claim anchors).

### LLM-10 — Keep each comment about the code it sits beside; never carry over a comment from another unit
- **Principle:** When you copy, move or extract code, check that each attached comment still describes its new neighbor. Delete text written for a different function, branch or problem. A coherent comment on the wrong topic hurt models more than random filler did.
- **Kind:** where
- **Sources:**
  - [documentation-llm-understanding-010](../../research/comment-context/sources/documentation-llm-understanding/passages.md#documentation-llm-understanding-010) — supports — "a random comment or docstring from a different HumanEval function" — evidence: empirical-llm
  - [talking-while-coding-017](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-017) — supports — "Source-written and wrong-topic prefixes are closely matched in token count, comment-line count, and density, yet produce sharply different pass@1." — evidence: empirical-llm
  - [talking-while-coding-017](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-017) — supports — "Coherent but topic-wrong comments hurt more than incoherent noise" — evidence: empirical-llm
  - [talking-while-coding-017](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-017) — supports — "The damage concentrates on easy problems (Table 15), where the recipient would often have solved the task unaided." — evidence: empirical-llm
- **Conditions / limits:**
  - Pan et al.'s wrong-topic versus random asymmetry is significant pooled over 10,076 pairs (946 vs 650 problems, talking-while-coding-054), but heterogeneous per cell.
  - The damage falls on *easy* problems, which a model would otherwise have solved. Misattached comments can therefore break routine work.
- **Tension:** None found.
- **Testable as:** capture / misplaced; maintain / bad_claims.

### LLM-11 — Record what the code cannot express: requirements, side-effect obligations, pre- and postconditions
- **Principle:** When evidence shows that code must do something its body does not make self-evident, state that obligation beside the code. Examples are notifying observers, ensuring an entry exists, or counting empty cells as zero. Such facts let a later agent see that a deviation is a bug.
- **Kind:** what
- **Sources:**
  - [comments-bug-fixing-002](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-002) — supports — "Without reading the comment and understanding this requirement, neither a human developer nor a model could identify or fix the bug." — evidence: expert-opinion
  - [comments-bug-fixing-032](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-032) — supports — "Theproperty-related comment most likely helped fix this bug since it explicitly says that the methodensures that an aggregation buffer is available for the specified grouping key" — evidence: empirical-llm
  - [comments-bug-fixing-026](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-026) — supports — "models trained without comments still benefit from comments at inference time" — evidence: empirical-llm
  - [agent-context-evidence.md § Requirements for a useful next experiment](../../research/agent-context-evidence.md#requirements-for-a-useful-next-experiment) — qualifies — "The research supports testing accurate information that code alone does not express." — evidence: empirical-llm
- **Conditions / limits:**
  - Inference-only effects (models fine-tuned without comments) were modest: exact match 3.26% to 3.73% (OR 1.44) and 5.57% to 7.90% (OR 3.42). GPT-4.1 zero-shot went from 6.11% to 8.63% (comments-bug-fixing-040).
  - The 2-3× headline gain needs comment-aware fine-tuning, and all of these comments were generated from the fixed method.
  - Figure 1 and Figure 5 are selected examples.
- **Tension:** Pairs with LLM-04 and LLM-05: the agent must have evidence of the obligation and must not infer it from the code alone.
- **Testable as:** capture / recall; maintain / recall.

### LLM-12 — Prefer concrete commitments over generic description
- **Principle:** Name the algorithm, the exact condition, the invariant or the bound rather than a vague category ("handles edge cases", "formatting"). Vague but correct comments lost much of their benefit, while paraphrase, compression and hedged tone did not.
- **Kind:** what
- **Sources:**
  - [talking-while-coding-046](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-046) — supports — "the block becomes less informative, not wrong." — evidence: empirical-llm
  - [talking-while-coding-050](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-050) — supports — "vague (specificity)−7.0 ∗∗∗ −5.3∗∗" — evidence: empirical-llm
  - [talking-while-coding-016](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-016) — supports — "only removing specific task information hurts, and wording, length, and tone do not" — evidence: empirical-llm
  - [comments-bug-fixing-016](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-016) — supports — "is documented with the one-word commentFormatting." — evidence: empirical-llm
- **Conditions / limits:**
  - Table 9 covers two recipients (Qwen3-8B, Seed-Coder-8B) with one source (Gemini). Values are pass@1 changes against source-correct; vague cost 7.0 and 5.3 points.
  - Compressed was neutral or positive (+3.4 for Seed-Coder): shortening without losing commitments did not hurt.
- **Tension:** Specific claims (exact thresholds, algorithm names) go stale faster than generic ones. This trades against LLM-03 and LLM-18.
- **Testable as:** capture / recall (anchor groups favour specific terms); capture / noise_lines.

### LLM-13 — Write down the decisive choice that rules out a plausible but wrong alternative
- **Principle:** When code depends on a choice where a natural-looking alternative would be wrong, state the choice and what it rules out. Examples are "sum, not product", "count empty cells as 0, do not skip them", and "store after lookup". These single decisions are what transferred most clearly to weaker models.
- **Kind:** what
- **Sources:**
  - [talking-while-coding-056](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-056) — supports — "prefix-source’s comment block typically reroutes the prefix-recipient from a plausible-but-wrong strategy to the correct one." — evidence: empirical-llm
  - [talking-while-coding-058](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-058) — supports — "The prefix-source’s prefix supplies a single strategic decision – “it’s a sum, not a product” – that the prefix-recipient was unable to find on its own." — evidence: empirical-llm
  - [comments-bug-fixing-012](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-012) — supports — "Without comments, the model might attempt to fix the method by adding a check to skip empty strings entirely." — evidence: expert-opinion
  - [comments-bug-fixing-012](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-012) — supports — "this would not resolve the issue but merely change the nature of the bug" — evidence: expert-opinion
- **Conditions / limits:**
  - The flip-atlas analysis is qualitative and selected: among 870 source-pass problems, 89 were "source-transferable" against 3 "source-toxic" (talking-while-coding-055).
  - The CSV example is a hypothetical in the bug-fixing paper's theory section.
- **Tension:** None found. This sharpens LLM-11 and LLM-12.
- **Testable as:** capture / recall; capture / bad_claims (when the rejected alternative is planted as a forbidden claim).

### LLM-14 — Capture knowledge while you have it; a later agent cannot reliably regenerate it on request
- **Principle:** If you hold verified, task-relevant knowledge that the code does not show, write it down now. Examples are a solution insight, a ruled-out approach, or a requirement from the ticket. A later model asked to "explain your reasoning" or "plan first" did not recover the content that a correct external comment supplied.
- **Kind:** agent
- **Sources:**
  - [talking-while-coding-004](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-004) — supports — "Prompt engineering controls what the comments look like, but cannot reliably control whether their content describes a correct solution." — evidence: empirical-llm
  - [talking-while-coding-023](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-023) — supports — "A correct comment from a stronger model is therefore not interchangeable with a prompt asking the recipient to write its own." — evidence: empirical-llm
  - [talking-while-coding-025](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-025) — supports — "self-produced plans still do not reliably encode a correct solution." — evidence: empirical-llm
  - [agent-context-evidence.md § 1. Correct comment content can help a weaker model](../../research/agent-context-evidence.md#1-correct-comment-content-can-help-a-weaker-model) — qualifies — "Comments are generation prefills; persistent maintenance, lifetime costs, and long-term model-tier substitution remain untested." — evidence: empirical-llm
- **Conditions / limits:**
  - In Pan et al., self-elicitation recovered at most about 24% of the external lift (Qwen3-8B `dense`, +4.4 vs +18.1). Self-planning and two-stage prompting changed pass@1 by between -0.6 and +1.9 points, none of them significant.
  - The "stronger source" had solved the problem and passed the tests, and was filtered on that outcome. A writing agent does not have that guarantee, so this only holds for knowledge that is actually verified.
  - The finding is about single-shot competitive programming, not persistent repository comments.
- **Tension:** Must be bounded by LLM-05 (verified only) and LLM-07 (not volume).
- **Testable as:** capture / recall. The real test is the downstream confirmation tier (fresh agent, follow-up change).

### LLM-15 — Write for the weakest likely reader: small models gain most from correct comments and lose most from wrong ones
- **Principle:** Do not skip an explanation because a strong model could infer it. A later, weaker model may not. For the same reason, treat accuracy as more important the weaker the expected reader.
- **Kind:** agent
- **Sources:**
  - [talking-while-coding-003](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-003) — supports — "Correct comments raise the recipient’s pass@1 by17.2% on average across the 12 (recipient, source) pairs." — evidence: empirical-llm
  - [comments-bug-fixing-027](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-027) — supports — "smaller ones can close much of the gap when guided by explicit contextual information such as comments." — evidence: empirical-llm
  - [comments-bug-fixing-027](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-027) — qualifies — "suggesting that bigger models can better exploit contextual information even without previous exposure" — evidence: empirical-llm
  - [documentation-llm-understanding-013](../../research/comment-context/sources/documentation-llm-understanding/passages.md#documentation-llm-understanding-013) — qualifies — "GPT-3.5 shows that providing partial comments causes an initial spike in the number of errors" — evidence: empirical-llm
  - [comments-bug-fixing-040](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-040) — qualifies — "observing an increase in EM from 6.11% (without comments) to 8.63% (with comments)." — evidence: empirical-llm
- **Conditions / limits:**
  - The direction depends on setting. In Vitale et al., the larger model gained more from inference-only comments, while the smaller gained more after comment-aware fine-tuning.
  - Wrong documentation cost GPT-3.5 about 22.6 points of test success, against about 10.4 for GPT-4, by my arithmetic from documentation-llm-understanding-012/013.
  - Pan et al.'s recipients were 4B-9B models; the lift was smaller where baselines sat near the floor or the ceiling.
  - "Weaker" here means lower baseline pass rate, not just parameter count.
- **Tension:** Pushes toward more explanation, against LLM-06 and LLM-07. The resolution is more *non-obvious* explanation, not more restatement.
- **Testable as:** not covered by comment-edit (single model). It needs the downstream tier across model tiers.

### LLM-16 — Concentrate explanation where the reader has headroom; leave routine code alone
- **Principle:** Spend comments on logic that a capable reader could plausibly get wrong. On easy code the gain is small and a wrong comment does the most damage. On medium-difficulty logic, correct content helped most.
- **Kind:** when
- **Sources:**
  - [talking-while-coding-021](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-021) — supports — "The effects concentrate where the recipient has headroom." — evidence: empirical-llm
  - [talking-while-coding-054](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-054) — supports — "Source-correct prefills lift pass@1 most on medium problems for most (recipient, source) pairs" — evidence: empirical-llm
  - [talking-while-coding-018](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-018) — supports — "concentrates on easy problems where the recipient would have picked the right approach unaided" — evidence: empirical-llm
  - [comment-maintenance-and-evaluation.md § Nielebock and colleagues (2019): useful-looking is not demonstrated usefulness](../../research/comment-maintenance-and-evaluation.md#nielebock-and-colleagues-2019-useful-looking-is-not-demonstrated-usefulness) — supports — "For its small Java tasks, the authors found no significant overall advantage in correctness or completion time from the tested commenting conditions." — evidence: empirical-human
  - [documentation-llm-understanding-020](../../research/comment-context/sources/documentation-llm-understanding/passages.md#documentation-llm-understanding-020) — qualifies — "including examples of more complex code and documentation" — evidence: empirical-llm
- **Conditions / limits:**
  - Difficulty here is LiveCodeBench's band per problem, not a property an agent can measure while editing.
  - The 89 problems that the correct prefill flipped from fail to pass still spanned all bands (56 medium, 18 easy, 15 hard).
  - Macke and Doyle's null came on simple HumanEval functions, which they flag as a limitation.
- **Tension:** None found. Restates the restrain family in empirical terms.
- **Testable as:** restrain / noise_lines; capture / recall.

### LLM-17 — Do not mass-strip existing comments; removal can hurt comment-reliant models
- **Principle:** In an audit or refactor, delete a comment because it is wrong, misplaced or pure restatement, never to reduce comment count. Removing all comments cost some models heavily, though it helped others. Whether comments help or hurt is model-specific.
- **Kind:** avoid
- **Sources:**
  - [talking-while-coding-026](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-026) — supports — "Models that comment heavily at baseline are the most damaged by being told not to." — evidence: empirical-llm
  - [talking-while-coding-029](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-029) — supports — "suppressing comments costs up to 14.5% on comment-dependent models, while helping others." — evidence: empirical-llm
  - [agent-context-evidence.md § 4. Comments can obstruct long-context retrieval](../../research/agent-context-evidence.md#4-comments-can-obstruct-long-context-retrieval) — opposes — "removing natural comments improves several models" — evidence: empirical-llm
  - [agent-context-evidence.md § 4. Comments can obstruct long-context retrieval](../../research/agent-context-evidence.md#4-comments-can-obstruct-long-context-retrieval) — qualifies — "This demonstrates sensitivity to context construction, not universal comment harm." — evidence: empirical-llm
- **Conditions / limits:**
  - Pan et al.'s `none` policy suppresses comments the model writes in its own output. Transfer to deleting repository comments is an inference.
  - The 14.5-point loss (Gemma-4-E4B-IT) is the extreme case. `none` lifted GPT-OSS-120B (talking-while-coding-023).
  - RepoQA concerns long-context function retrieval, with a synthetic-comment confound.
- **Tension:** Directly opposes aggressive restraint and "code should explain itself" positions. Also opposes LLM-06 if that is applied destructively to existing comments.
- **Testable as:** audit / preserved; maintain / preserved.

### LLM-18 — Implementation and invariant comments carry the most repair signal but drift fastest; write them only where you will maintain them
- **Principle:** A comment on *how* a method achieves its result, or on the invariant it maintains, helped repair models most. Write one only where the mechanism is non-obvious, and update it with every change to that mechanism. Comments on usage, rationale and properties still helped and change less often.
- **Kind:** what
- **Sources:**
  - [comments-bug-fixing-029](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-029) — supports — "Both models give much higher importance to comments describinghowthe implementation is done as compared to the other categories." — evidence: empirical-llm
  - [comments-bug-fixing-033](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-033) — qualifies — "developers might be reticent to provide comments regarding the implementation details because the such details might change frequently, thus leading to inconsistencies between comments and code" — evidence: expert-opinion
  - [comments-bug-fixing-034](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-034) — qualifies — "we still observe a significant boost in terms of EM, which is 91% higher than the baseline model" — evidence: empirical-llm
  - [comments-bug-fixing-039](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-039) — qualifies — "such an approach, like others available, only provide estimates on the importance given by the model to single tokens." — evidence: empirical-llm
  - [talking-while-coding-010](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-010) — qualifies — "We conclude that no robust intent signal was found, rather than that none exists" — evidence: empirical-llm
- **Conditions / limits:**
  - The "how" ranking comes from SHAP attributions on correct predictions (1,141 and 1,486 exact matches), and from one removal ablation on CodeT5+ only.
  - All comments were single GPT-3.5 sentences generated from fixed code.
  - The 91% figure is relative to an exact-match baseline of 3.26%.
- **Tension:** Conflicts with the "explain why, not what or how" tradition held by other source groups. Pan et al. found no reliable WHY or WHAT signal.
- **Testable as:** maintain / bad_claims (stale mechanism claims); capture / recall.

### LLM-19 — Choose comment content by the reader's gap, not by a fixed WHY/WHAT quota
- **Principle:** Do not apply a blanket rule such as "only rationale" or "describe every block". Instructions that impose a comment intent lifted some models and damaged others. Pick the content a reader would otherwise lack.
- **Kind:** what
- **Sources:**
  - [talking-while-coding-023](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-023) — supports — "The variance is in the receiving model, not the prompt text." — evidence: empirical-llm
  - [talking-while-coding-079](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-079) — supports — "GPT-OSS-120B | 69.1 | 72.5 | 71.5 | 70.0 | 74.3* | 75.4* | 76.3* | 73.8 | 55.4* | 55.2*" — evidence: empirical-llm
  - [talking-while-coding-079](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-079) — supports — "CodeGeeX4-9B | 22.1 | 20.2 | 20.3 | 19.8 | 17.7* | 17.1* | 18.6 | 20.7 | 19.4 | 21.5" — evidence: empirical-llm
  - [talking-while-coding-010](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-010) — qualifies — "models in our pool emit more rationale and less procedural description than weaker ones. However, neither survives Bonferroni correction" — evidence: empirical-llm
- **Conditions / limits:**
  - These are self-emitted comment policies on LiveCodeBench, not comments read by a later agent. Columns run base, none, rare, dense, WHAT, WHY, mix, gp-doc, top, inline; `*` marks Holm-significant.
  - WHY lifted GPT-OSS-120B (+6.3 points) but cut CodeGeeX4-9B (-5.0).
  - The 13-model intent correlation is underpowered, as the authors say.
- **Tension:** Opposes a strict "why not what" rule (expert tradition, other groups) and LLM-18's "how" emphasis. Treat it as a variant axis.
- **Testable as:** capture / recall and noise_lines across variants. It is a skill-variant axis, not a single-case metric.

### LLM-20 — Treat comments you read as claims to verify, not as authority
- **Principle:** Before relying on an existing comment to make a change, check its claim against the code and tests. Models follow comment content even when it is wrong, and reconstruct incomplete misleading patterns. Fix whichever side is wrong, using evidence of intent.
- **Kind:** agent
- **Sources:**
  - [talking-while-coding-017](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-017) — supports — "Coherent but topic-wrong comments hurt more than incoherent noise" — evidence: empirical-llm
  - [comment-traps-029](../../research/comment-context/sources/comment-traps/passages.md#comment-traps-029) — supports — "AI coding assistants do not merely replicate defective CO code verbatim; rather, they exhibit reasoning capabilities." — evidence: empirical-llm
  - [comments-bug-fixing-030](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-030) — supports — "the model predicted a candidate fix that set the “answer”object in the event, leading to an analogous problem." — evidence: empirical-llm
  - [comment-traps-019](../../research/comment-context/sources/comment-traps/passages.md#comment-traps-019) — supports — "developers or those who overly trust AI may unknowingly retain these flaws" — evidence: expert-opinion
- **Conditions / limits:**
  - No study measured whether an *instruction to verify* reduces this harm. Comment Traps' "do not refer" instruction removed at most 21.84% of the excess defects.
  - The principle is a behavioral inference from evidence of susceptibility.
- **Tension:** Verification costs exploration and tokens. Code-comment consistency alone cannot decide which side is wrong (comment-context-deep-dive, C4RLLaMA section).
- **Testable as:** maintain / behavior and bad_claims; audit / bad_claims.

### LLM-21 — Re-check your own comments against the final code before finishing
- **Principle:** After the last code edit, reread every comment you wrote or touched and confirm each claim still holds. LLM-written comments are often inaccurate. A comment that reads fluently, or closely resembles the old one, can still be wrong.
- **Kind:** maintain
- **Sources:**
  - [comments-bug-fixing-018](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-018) — supports — "93% of the analyzed comments are coherent with the related comment category and that the median adequacy score assigned is equal to 4." — evidence: empirical-llm
  - [talking-while-coding-005](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-005) — supports — "probes find LLM-emitted comments themselves often" — evidence: empirical-llm
  - [comment-context-deep-dive.md § Learned comment updates are feasible but similarity can mislead](../../research/comment-context-deep-dive.md#learned-comment-updates-are-feasible-but-similarity-can-mislead) — supports — "a nearly unchanged but incorrect sentence can resemble the human reference." — evidence: empirical-llm
  - [comment-context-deep-dive.md § C4RLLaMA exposes incomplete repair and a reporting inconsistency](../../research/comment-context-deep-dive.md#c4rllama-exposes-incomplete-repair-and-a-reporting-inconsistency) — supports — "The discussion identifies rewording that leaves the semantic error intact" — evidence: empirical-llm
- **Conditions / limits:**
  - In Vitale et al., GPT-3.5 comments were generated from *correct* code and still were not uniformly adequate: 7% were incoherent with their category, and the median adequacy was 4 of 5 on a 400-sample check.
  - The few-shot examples in their prompt are themselves vague (comments-bug-fixing-043).
  - The figure-level example in "Notable anti-patterns" below is my own reading, not an author finding.
- **Tension:** None found.
- **Testable as:** capture / bad_claims; maintain / bad_claims.

## Conflicts and open questions

- **Do correct comments help at all?**
  - Macke and Doyle: no significant gain in test success from correct docstrings, but better line coverage.
  - Vitale et al.: up to 3× exact match, but only with oracle comments plus comment-aware fine-tuning. Inference-only gains were small to medium.
  - Pan et al.: +17.2 points mean for weak recipients, but only with correct, solution-bearing content from a stronger model.
  - A consistent reading: a comment helps only if it carries correct information the reader lacks. This is a hypothesis to test, not a result.
- **Which comment intent matters?**
  - Vitale et al. rank *how* (implementation) comments highest by SHAP.
  - Pan et al. find no reliable WHY or WHAT association, and prompt-imposed intents help or hurt depending on the model.
  - Other source groups' expert tradition favors *why*. This should be a variant axis (LLM-18 vs LLM-19).
- **Delete or keep?**
  - Restraint and RepoQA suggest fewer comments can help (removal improved retrieval for several models).
  - Pan et al. show suppressing comments costs comment-reliant models up to 14.5 points.
  - The `restrain` family penalizes added noise. No family yet penalizes destructive removal of valid comments beyond `preserved` on protected items.
- **Which models benefit?**
  - Bigger models exploit inference-only comments better (Vitale et al.). Smaller ones benefit most after comment-aware fine-tuning, and weak recipients gain from strong-model comments (Pan et al.).
  - GPT-3.5 is hurt more than GPT-4 by wrong docs (Macke and Doyle).
  - "Weaker benefits more" is not settled across settings.
- **Commented-out code: practice vs. harm.**
  - Developers keep it for debugging and legacy logic (comment-traps-003). It measurably raises defects for Copilot and Cursor.
  - Its authors treat tags as good for humans but useless for models. Should an audit delete it, or only report it?
- **How big is the harm from stale comments?**
  - Every measured harm uses a proxy: unrelated docstrings, wrong-topic blocks, comments generated from buggy code, or injected defective code.
  - The directly relevant *When Comments Mislead* is abstract-only here, so the size of the harm from naturally stale comments is unknown.
- **Partial or incomplete documentation.**
  - Macke and Doyle cannot conclude whether partial docstrings hurt (GPT-3.5 error spike; minor and mostly non-significant for GPT-4).
  - It is unresolved whether an agent should trim a docstring to its verifiable parts or leave it whole.
- **Specificity vs. durability.**
  - Specific claims carried the benefit (LLM-12), and implementation detail was most used (LLM-18).
  - These are exactly the claims most likely to drift (comments-bug-fixing-033).
  - No study measured the net value over successive edits.
- **Transfer gap.** None of these studies tests comments that persist in a repository across fresh agent sessions, or compares them with the same facts in a separate document (agent-context-evidence, "Where the evidence stops"). Every agent-facing principle above is an extrapolation.

## Notable anti-patterns and worked examples

- **Commented-out insecure call above live code** ([comment-traps-038](../../research/comment-context/sources/comment-traps/passages.md#comment-traps-038)): `# ssl_s = ssl.wrap_socket(s, ...` sits above the completion point. Copilot then generates the deprecated `ssl.wrap_socket` without a protocol version (CWE-327). The control prompt ([comment-traps-037](../../research/comment-context/sources/comment-traps/passages.md#comment-traps-037)) yields `ssl.create_default_context()`. Bad example for LLM-08.
- **Tagging does not neutralize** ([comment-traps-044](../../research/comment-context/sources/comment-traps/passages.md#comment-traps-044)): `# (Vulnerable) ssl_s = ssl.wrap_socket(s, ... (/Vulnerable)` still raised defects about as much as the untagged code. Bad example for LLM-09.
- **A requirement comment that makes a bug visible** ([comments-bug-fixing-042](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-042)): "Empties the PWO metadata queue and notifies the dataset change to the nearby devices." The fix adds `notifyDataSetChanged()`. Good example for LLM-11.
- **Property comment enabling a correct fix** ([comments-bug-fixing-049](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-049), [050](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-050)): "Ensures that an aggregation buffer is available for the specified grouping key" points at the missing `hashMap.put`. Good example for LLM-11.
- **One misleading clause** ([comments-bug-fixing-045](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-045), [048](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-048)): the *how* line "...and catches any exceptions to set in the event" coincided with a wrong fix. Removing that clause produced a correct one. Bad example for LLM-02.
- **Vacuous comments** ([comments-bug-fixing-004](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-004), [016](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-016), [043](../../research/comment-context/sources/comments-bug-fixing/passages.md#comments-bug-fixing-043)): "// Argh!!! This method is WRONG !", the one-word "Formatting", and the generated "why: Generates code for this object." Bad examples for LLM-06 and LLM-12.
- **Restatement vs. reason** ([talking-while-coding-009](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-009), [073](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-073), [074](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-074)): `# Sort the array` and `# iterate over (index, value) pairs` restate the code. `# store after lookup to avoid using the same index twice` states a non-obvious ordering constraint. The latter is a good example for LLM-13.
- **Decisive choice that transferred** ([talking-while-coding-058](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-058)): "it's a sum, not a product". The weak model's unaided attempt multiplied group counts. Good example for LLM-13.
- **Fluent but probably wrong illustrative claims** ([talking-while-coding-077](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-077), [078](../../research/comment-context/sources/talking-while-coding/passages.md#talking-while-coding-078)): the paper's own example blocks say `seen[v] = earliest index` and `value -> first index seen`. Yet the code `seen[n] = i` overwrites on every visit, so it stores the latest index. *This is my reading; the transcription note explicitly declines to evaluate it.* If it holds, it shows how a confident, well-formed comment can misstate the code (LLM-21).
