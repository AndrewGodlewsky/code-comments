# Talking to Itself While Coding: source passages

Generated from records.json and the pinned reading text. No ranking or recommendation is implied.

Extent: `local_paper`. Text SHA-256: `89de1fbd2b74f3c7968039a6f19729a5b526b282057ddeb0bf3ce852ddc85baa`.

[Selections](records.json) · [Coverage and gaps](coverage.json) · [Collection index](../../README.md)

- Figure 2 on physical page 9 is concatenated/garbled in base text; visual inspection complete and supplemental transcription pending integration.
- Tables 4 (p8), 16 and 17 (p24) contain concatenated numeric fields in base extraction. Original tables were visually checked; use original column layout.
- Bold table emphasis, superscripts and indentation are not preserved by the base extraction. Prompts retain source-rendered typography rather than runnable code-fence syntax.

<a id="talking-while-coding-001"></a>
## talking-while-coding-001 — Abstract

Source: [physical PDF page 1](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=1); reading unit `p001`, lines 5–33.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-002](#talking-while-coding-002)

```text
Abstract
Large Language Models (LLMs) often generate
natural-language comments while writing code,
and these comments become part of the context
used to generate the code that follows. How-
ever, it remains unclear which properties of
comments affect code-generation performance.
We study this question through observational
analyses and controlled interventions. On Live-
CodeBench, neither comment frequency nor
broad comment intent reliably predicts pass@1.
We then prefill weaker recipient models with
comment blocks written by stronger source
models, allowing us to separate comment sur-
face form from the solution content they convey.
Comments from source solutions that pass the
tests raise recipient pass@1 by 17.2% on aver-
age. In contrast, comments describing failed
solutions provide no reliable gain, while com-
ments written for a different problem reduce
pass@1 by 20.8%. Finally, across a wide range
of models and prompt variants, most recipi-
ent models show no significant recovery of the
external-comment gain, and the best case re-
covers only 24%. These results show that com-
ments help code generation not merely because
they are comments, but because they can pro-
vide correct solution content that prompting
cannot reliably elicit.
```

<a id="talking-while-coding-002"></a>
## talking-while-coding-002 — Introduction: human readers and self-emitted comments

Source: [physical PDF page 1](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=1); reading unit `p001`, lines 34–87.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; cited findings remain attributed to the named third-party authors

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-001](#talking-while-coding-001), [talking-while-coding-003](#talking-while-coding-003)

```text
1 Introduction
Code comments have long been studied as text
for human readers. They explain rationale to fu-
ture maintainers and share intent with collabora-
tors. Empirical work has shown that informative
comments measurably improve human program
comprehension (Tenny, 1988). Subsequent tax-
onomies classify comments by intent and trace how
each category supports a distinct maintenance activ-
ity (Storey, 2005; Pascarella and Bacchelli, 2017).
In LLM-based code generation, the reader
changes from a human to the model itself. The
*Corresponding author.
comments and the code are emitted in the same
forward pass by the same model. The model reads
its own comments as context for the code that fol-
lows. We call these self-emitted comments, and
their role in the model’s own solution is not obvi-
ous. These comments are not free: they are billed
as output tokens (Pan et al., 2025), and whether
they can be safely suppressed depends on whether
they causally help.
Do these comments causally affect the model’s
own pass@1? Prior work has shown that natural-
language preambles in code generation can help
(Jiang et al., 2024; Chen et al., 2024; Shi et al.,
2025; Di and Zhang, 2025; Jiang et al., 2026), but
has not isolated which of their properties—surface
form, line order, topic, intent, or the correctness
of the solution they describe—is responsible. As
a first observational check, we ask whether the
most visible properties of natural comments pro-
vide a simple explanation for pass@1. We be-
gin with comment volume and surface form. If
these properties provided such an explanation, we
would expect some consistent association between
commenting behavior and performance. On Live-
CodeBench (Jain et al., 2024), OpenReasoning-
Nemotron-32B and Gemini-2.5-Pro-03-25 reach
81.0% and 81.5% pass@1 respectively, while self-
emitted comments account for 0.1% of Nemotron’s
output tokens and 71.4% of Gemini’s: a 700-fold
gap that is invisible in pass@1. Among the 16
models scoring above 80.0% pass@1, commenting
rates range from under 2.0% (4 models) to over
30.0% (5 models), showing no apparent link to
pass@1.
In addition to the volume of comments, the intent
of the comments also fails to track pass@1. Specif-
ically, we label every comment across 13 models
along the WHY/WHAT axis from comment tax-
onomies (Storey, 2005; Pascarella and Bacchelli,
2017)—whether it explains a choice or describes
what the code does, and check whether models that
```

<a id="talking-while-coding-003"></a>
## talking-while-coding-003 — Observational limits and controlled intervention

Source: [physical PDF page 2](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=2); reading unit `p002`, lines 1–34.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-002](#talking-while-coding-002), [talking-while-coding-004](#talking-while-coding-004)

```text
explain choices more often tend to score higher.
We find that stronger models do explain choices
a bit more often ( ρ= +0.61 , raw p= 0.027 ),
but the trend does not survive Bonferroni correc-
tion. Therefore, from the natural distribution alone,
neither comment volume/form nor coarse intent
provides a reliable explanation for pass@1. This
observational result cannot determine whether com-
ments causally matter, so we turn to a controlled
intervention (Section 4). We prefill a weakerre-
cipientmodel’s decoding context with a comment
block from a strongersourcemodel, and let the re-
cipient continue from there, then vary only the com-
ment’s content while holding the recipient, prompt,
and problem fixed. The source is chosen to be
strong for a reason: its comments are correct when
its own solution passes the tests and wrong when it
fails, letting us control content correctness directly
instead of merely measuring it. The external pre-
fix is thus a measurement instrument rather than
a model of natural self-commenting: it identifies
what property a comment must have to help, and
Section 4.2 then asks whether the model’s own
comments can supply that property.
The intervention separates which property of
the comment moves pass@1. Correct comments
raise the recipient’s pass@1 by17.2% on average
across the 12 (recipient, source) pairs. Same-form
comments with wrong content leave pass@1 un-
changed. Comment-shaped text on the wrong topic
damages pass@1 by 20.8%, and length-matched
random text damages it by17.9%. Pass@1 changes
with whether the comment describes a correct solu-
tion, not with what the comment looks like.
```

<a id="talking-while-coding-004"></a>
## talking-while-coding-004 — Self-elicitation overview and research artifacts

Source: [physical PDF page 2](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=2); reading unit `p002`, lines 35–62.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-003](#talking-while-coding-003), [talking-while-coding-005](#talking-while-coding-005)

```text
A natural follow-up question is whether the re-
cipient can produce a comparable comment from
its own prompt, without an external source. Across
14 models and 10 prompt variants (Section 4.2),
the answer is largely no. Models follow what the
prompt asks at the surface, such as producing more
or fewer comments, or adopting different styles.
However, the best prompt recovers at most about
24% of the external-comment lift, and the same
instruction can move pass@1 in opposite direc-
tions on different recipients. Prompt engineering
controls what the comments look like, but cannot
reliably control whether their content describes a
correct solution.
The overall structure of our study is de-
picted in Figure 1. In summary, the natural
distribution of self-emitted comments does not
track pass@1. Under controlled intervention,
a correct comment from a stronger model lifts
a weaker model’s pass@1 while prompting
the weaker model to write its own comments
falls short. Talking to itself is not enough, and
what matters is whether the talk carries correct
solution content. To facilitate reproducibility, we
release our code, generation outputs, per-problem
pass/fail evaluations, and per-cell statisti-
cal summaries at https://github.com/pdfCN/
What-Makes-Comments-Help-Code-Generation .
```

<a id="talking-while-coding-005"></a>
## talking-while-coding-005 — Related work and in-context-learning comparisons

Source: [physical PDF page 2](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=2); reading unit `p002`, lines 63–102.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; cited findings remain attributed to the named third-party authors

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-004](#talking-while-coding-004), [talking-while-coding-006](#talking-while-coding-006)

```text
2 Related Work on Code Comments in
Code Generation
Code comments have historically been studied
as text written for human readers (Tenny, 1988;
Storey, 2005; Pascarella and Bacchelli, 2017).
However, in LLM-based code generation, com-
ments can also become context for the model it-
self. Existing work has explored two related direc-
tions. In the first, the comment is input read by
the model. Rationale comments help auto bug-fix
(Vitale et al., 2026), removing comments lifts some
downstream tasks (Imani et al., 2025; Liu et al.,
2024), mismatched comments degrade unit-test
generation (Macke and Doyle, 2024), and probes
find LLM-emitted comments themselves often inac-
curate (Kang et al., 2024). In the second direction,
the model itself emits natural language as a pream-
ble to its own code. Plan-then-code prompting
(Jiang et al., 2024), comment-then-code training
(Chen et al., 2024), natural-language outlines above
code (Shi et al., 2025), bidirectional comment-code
grounding (Di and Zhang, 2025), and placement
variation during decoding (Jiang et al., 2026) all
show that getting the model to produce natural lan-
guage before code helps.
None of these works isolates which property of
the preamble is responsible for the effect. Can-
didates include the surface form, the line order,
the topic, the intent and the correctness of the de-
scribed solution content. Whether any property is
dominant remains open.
We adapt the approach from In-Context Learn-
ing (ICL) studies that pull demonstrations apart
along format, label distribution, order, and surface
structure (Min et al., 2022; Lu et al., 2022; Sclar
et al., 2024; Li et al., 2025). Min et al. (2022)
found that ground-truth labels matter little in ICL
demonstrations, while a counterpoint shows that
labels can still matter when demonstrations are cho-
sen carefully (Yoo et al., 2022). Our intervention
```

<a id="talking-while-coding-006"></a>
## talking-while-coding-006 — Figure 1 and related-work continuation

Source: [physical PDF page 3](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=3); reading unit `p003`, lines 1–71.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; cited findings remain attributed to the named third-party authors

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-005](#talking-while-coding-005), [talking-while-coding-007](#talking-while-coding-007)

```text
§3.1  Does form track pass@1?88 models
diverse LLMs
form metricstok-cmt%
% tokens incomments
block%
blockcomment %
inline%
inlinecomment %
doc%
docstringcomment %
pass@1correlation
Spearman ρper metric
Compute per-model metrics on self-emitted comments; correlate with pass@1.Form does not reliably track pass@1.
§3.2  Does intent track pass@1?comments
self-emittedcomments
intent labelsWHYrationale
WHATalgorithm/step /mechanism/definitionOTHERdecoration/misleading
labelers
LLM judge(Gemini)
human check(validation)
pass@1correlation
Spearman ρper intent
Label each comment by intent; compare intent proportions with pass@1.Intent does not reliably track pass@1.
What property ofcomments changes pass@1?
§4.1  External Comment PrefixWhat happens when we prefill the model with someone else’s comments?strongsource model
high pass@1
externalcomments
prefill
weakrecipient model
low pass@1
generatedcode
evaluatepass@1
source-correct
comments fromstrong model oncorrect solution
source-wrong
comments fromstrong model onincorrect solution
shuffled
correct commentsin random order
wrong-topic
comments aboutunrelated problemCorrect content lifts pass@1; wrong-topic comments hurt.
§4.2  Self-ElicitationCan prompting alone reproduce the external-comment lift?prompt policy
instructions tothe model
recipient model
(weak model)
self-emittedcomments
generated bythe model
generatedcode
evaluatepass@1
prompt controls (independent factors)volume
none/rare/dense
intent
WHY / WHAT /WHY+WHAT
format
gp-doc/top/inlinePrompting controls form, but effects are inconsistent.
+
🤔
🙁
🙁
😊
 😑
Figure 1: The four core sub-experiments. Section 3.1 profiles comment form across 88 models; Section 3.2 profiles
comment intent across 13 models. Section 4.1 attaches a stronger source’s comment block to a weaker recipient and
varies its content. Section 4.2 asks whether self-prompting can elicit the same lift.
attaches a comment block from a stronger source,
varies one property at a time while holding the oth-
ers fixed, and identifies content correctness as the
dominant property in the comment interface. In
this decomposition our finding lands closer to Yoo
et al. (2022): it can be read as a reproduction and
extension of the ICL content-versus-form question
through the comment interface.
```

<a id="talking-while-coding-007"></a>
## talking-while-coding-007 — Observational design and comment-form profile

Source: [physical PDF page 3](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=3); reading unit `p003`, lines 72–109.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-006](#talking-while-coding-006), [talking-while-coding-008](#talking-while-coding-008)

```text
3 Observing Self-Emitted Comments
We first ask whether the natural distribution of
self-emitted comments shows any pattern with
pass@1. If commenting style differed sharply be-
tween strong and weak models, we would already
have direct evidence that comments support the
model’s own generation. If not, the question de-
mands a controlled experiment. We test this on
two axes. The first isform, the surface shape of
the comments (Section 3.1). The second isintent,
what each comment line says (Section 3.2).
3.1 Does form track pass@1?
We analyse 88 models on LiveCodeBench v6 (Jain
et al., 2024), listed in Appendix C.1. Of these, 14
are run by ourselves and 74 come from the public
leaderboard (LiveCodeBench Authors, 2024). We
run 10 via OpenRouter and 4 locally with vLLM.
We measure commenting style with four metrics
computed under a single shared tokenizer:tok-
cmt%(fraction of output tokens inside a comment)
and the PEP-8 partition (van Rossum et al., 2001)
intoblock%,inline%, anddoc%(formal defini-
tions in Appendix D.2).
We test whether form tracks pass@1 at two lay-
ers. Across models, Table 10 (Appendix D.3)
reports the spread of each form axis at matched
pass@1. Within each model, we compute the
Spearman rank correlation ρ (Spearman, 1904) be-
tween each per-problem form feature and pass@1.
At matched pass@1, commenting volume and
form vary widely.Of the 16 top-tier models
with pass@1 ≥80.0% , 4 emit fewer than 2.0%
comment tokens while 5 exceed 30.0%: tok-cmt%
spans 0.1% (OpenReasoning-Nemotron-32B) to
71.4% (Gemini-2.5-Pro-03-25), a 700-fold spread,
and the other three axes vary just as widely (Ta-
ble 10). The same pattern extends across all 88
models: 10.2% emit fewer than 2.0% comment
```

<a id="talking-while-coding-008"></a>
## talking-while-coding-008 — Within-model form correlations

Source: [physical PDF page 4](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=4); reading unit `p004`, lines 1–15.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-007](#talking-while-coding-007), [talking-while-coding-009](#talking-while-coding-009)

```text
tokens and 45.5% emit more than 20.0%. Low
comment volume is not by itself a signal of model
weakness, and cross-model comparison alone can-
not tell us whether commenting tracks pass@1.
A model’s commenting habits look the same on
problems it solves and problems it fails.On
the three format axesblock%,inline%, anddoc%,
the strongest per-model |ρ| across the 88-model
pool is only 0.32 (Appendix D.4), and at most
13.0% of models exceed |ρ|=0.20, the conven-
tional small-effect threshold. The tok-cmt% axis
shows a slightly larger upper tail, with 22.0% of
models exceeding |ρ|=0.20 and a maximum of
0.53, still too small to change the conclusion. Form
does not track pass@1 at either layer.
```

<a id="talking-while-coding-009"></a>
## talking-while-coding-009 — Intent definitions and annotation method

Source: [physical PDF page 4](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=4); reading unit `p004`, lines 16–47.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-008](#talking-while-coding-008), [talking-while-coding-010](#talking-while-coding-010)

```text
3.2 Does intent track pass@1?
The form of a comment does not capture what it
says. Two block comments can look identical on
every form axis but mean very different things.
For example, # Use dynamic programming
because subproblems repeat explains the rea-
soning, while # Sort the array only restates
what the next line of code does. We therefore ask
whether intent tracks pass@1.
We label each comment line along the
WHY/WHAT axis standard in code-comment tax-
onomies (Storey, 2005; Pascarella and Bacchelli,
2017), plus an OTHER catch-all (about 10% of
lines); the three buckets aggregate a finer seven-
class codebook whose per-label reliability guides
the bucket boundaries (codebook and mapping in
Appendix A.1). We compute intent fractions on
a 13-model pool spanning the LCB pass@1 spec-
trum, with 8 self-run models and 5 leaderboard
submissions (Appendix C.1). Labels come from an
LLM judge, Gemini-3.1-Flash-Lite, validated
against a stratified 100-snippet human-labelled cal-
ibration set (judge prompt in Appendix B.2): the
anchor labels of WHY and WHAT reach Cohen’s
κ (Cohen, 1960) of +0.74 and +0.72, and bucket-
level agreement is in Appendix A.1. For each
intent, we compute the cross-model Spearman ρ
between the model’s mean intent fraction and its
pass@1. The mean is taken over samples that con-
tain at least one comment, to remove the volume
confound. We apply Bonferroni correction over the
three intents.
```

<a id="talking-while-coding-010"></a>
## talking-while-coding-010 — Intent results and limits of the null result

Source: [physical PDF page 4](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=4); reading unit `p004`, lines 48–71.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-009](#talking-while-coding-009), [talking-while-coding-011](#talking-while-coding-011)

```text
Intent does not track pass@1 either.The rank
correlations are positive on WHY ( ρ= +0.61 )
and negative on WHAT ( ρ=−0.20 ): stronger
models in our pool emit more rationale and less
procedural description than weaker ones. However,
neither survives Bonferroni correction, with raw
p of 0.027 on WHY and 0.52 on WHAT, neither
below the corrected thresholdα=0.0167.
The rank correlation cannot tighten further be-
cause models at similar pass@1 emit very different
intent distributions. At nearly identical pass@1
around 60%, WHY-fraction ranges from 18.1% on
Qwen3-235B-A22B to 40.7% on GPT-5.4-Nano
(per-model breakdown in Appendix A.2). A sin-
gle rank correlation across the pool averages these
opposite sub-populations into one number, and its
small magnitude is consistent with that averaging-
out. We conclude that no robust intent signal was
found, rather than that none exists: the 13-model
pool bounds the detectable effect size, and bucket-
level label reliability is mixed (WHY is reliable
while OTHER is not; Appendix A.1). This null
motivates the controlled intervention of Section 4
rather than establishing evidence of absence.
```

<a id="talking-while-coding-011"></a>
## talking-while-coding-011 — Content interventions and source/recipient selection

Source: [physical PDF page 4](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=4); reading unit `p004`, lines 72–99.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-010](#talking-while-coding-010), [talking-while-coding-012](#talking-while-coding-012)

```text
4 Intervening on Comment Content
The observational evidence in Section 3 cannot de-
termine whether self-emitted comments function-
ally affect pass@1. We now run two controlled
interventions. In Section 4.1 we attach a comment
block written by a stronger source model to the
head of a recipient model’s output. We hold every-
thing except the comment content fixed, isolating
which property drives the change in pass@1. The
candidates are content correctness, line order, topic,
and surface form. Throughout, “content” refers to
largely order-insensitive local claims about the so-
lution rather than an ordered derivation, a scope the
shuffled condition makes precise. In Section 4.2,
we ask whether the recipient itself can produce a
comparable comment from its own prompt. We
test this with 14 models and 10 prompt variants,
varying what we ask the recipient to write.
4.1 What happens when we prefill the model
with external comments?
We use four weakprefix-recipients
(Gemma-4-E4B-IT, Seed-Coder-8B-Instruct,
Qwen3-8B, CodeGeeX4-9B) and three stronger
prefix-sources. The sources are the two top per-
formers in our self-run pool,Grok-4.1-Fast and
Gemini-3.1-Flash-Lite, together with the state-
of-the-art proprietary model Claude-Opus-4.7.
Each source writes #-prefixed comments at the
```

<a id="talking-while-coding-012"></a>
## talking-while-coding-012 — Table 1: recipient results by comment condition

Source: [physical PDF page 5](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=5); reading unit `p005`, lines 1–28.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-011](#talking-while-coding-011), [talking-while-coding-013](#talking-while-coding-013)

```text
Recipient Source Baseline Source-written Source-correct Source-wrong Shuffled Wrong-topic
Gemma-4-E4B-IT
gemini
54.2
64.3 (+9.9)∗ 85.2 (+13.9)∗ 10.5 (−0.3) 76.2 (+4.9) 46.6 (−24.7) ∗
claude 62.5 (+6.6) ∗ 71.0 (+8.3)∗ 3.9 (−5.4) 67.4 (+4.7) 40.1 (−22.5) ∗
grok 69.9 (+14.1) ∗ 79.4 (+15.6)∗ 10.1 (+4.3) 74.0 (+10.2) ∗ 46.3 (−17.5)∗
Qwen3-8B
gemini
39.2
52.0 (+12.6)∗ 70.8 (+17.2)∗ 3.7 (+1.0) 67.4 (+13.7) ∗ 19.6 (−34.1)∗
claude 53.3 (+12.8) ∗ 60.5 (+14.7)∗ 3.1 (+0.0) 58.4 (+12.6) ∗ 21.7 (−24.1)∗
grok 60.5 (+19.7) ∗ 69.5 (+22.5)∗ 3.6 (+2.2) 63.6 (+16.6) ∗ 18.0 (−29.0)∗
Seed-Coder-8B
gemini
32.3
42.7 (+10.3)∗ 58.3 (+14.4)∗ 2.7 (−0.3) 53.1 (+9.2) ∗ 26.3 (−17.6)∗
claude 44.5 (+11.1) ∗ 50.8 (+12.8)∗ 0.8 (−0.8) 48.3 (+10.3) ∗ 22.6 (−15.4)∗
grok 49.4 (+15.7) ∗ 56.9 (+18.2)∗ 2.2 (+0.0) 48.9 (+10.1) ∗ 23.4 (−15.3)∗
CodeGeeX4-9B
gemini
19.4
38.1 (+18.6)∗ 52.3 (+25.9)∗ 1.7 (+0.0) 45.4 (+19.0) ∗ 8.5 (−18.0)∗
claude 36.5 (+16.5) ∗ 41.5 (+18.7)∗ 2.3 (+0.8) 39.0 (+16.3) ∗ 6.5 (−16.3)∗
grok 40.6 (+20.4) ∗ 46.8 (+23.8)∗ 2.2 (−0.7) 36.0 (+13.0) ∗ 7.7 (−15.3)∗
∗ Holm-significant at pholm<0.001 (paired McNemar, m=60). The 14 non-significant cells are all 12 source-wrong cells plus 2 Gemma shuffled cells (gemini,
claude sources). Column definitions in Section 4.1.
Table 1: Recipient pass@1 (%) under each source-comment condition. Parentheses give∆vs baseline.
```

<a id="talking-while-coding-013"></a>
## talking-while-coding-013 — Prefix conditions, baselines and multiplicity correction

Source: [physical PDF page 5](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=5); reading unit `p005`, lines 29–57.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-012](#talking-while-coding-012), [talking-while-coding-014](#talking-while-coding-014)

```text
head of its solution to each LCB problem; we
keep only its leading #-block as the prefix attached
to a recipient’s output (extraction details and the
source prompt in Appendix B.1). We define all
prefix conditions here.Source-writtenattaches
the source’s comment block on all problems and is
the union ofsource-correct(the subset where the
source’s own solution passes) andsource-wrong
(the subset where it fails);shuffledpermutes the
line order of source-correct blocks;wrong-topic
attaches a comment block written for a different
problem;random-textattaches length-matched
random text (Appendix D.5). Together they
test content correctness, line order, topic, and
surface form alone. Decoding parameters are in
Appendix C.2.
Every ∆ in Table 1 is measured against a
matched-prompt baseline. The baseline is the
recipient’s pass@1 on the cell’s problem subset,
run under the same prompt the source uses with no
external comment attached. This holds the prompt
setting fixed and isolates the effect ofwhichcom-
ment block is attached. Each cell is tested with a
paired exact McNemar (Mcnemar, 1947) against
this baseline; we apply Holm-Bonferroni correc-
tion (Holm, 1979) over m=60 tests at family-wise
α=0.05. The 60 tests cover 12 cells each for
source-written, source-correct, source-wrong, shuf-
fled, and wrong-topic.
```

<a id="talking-while-coding-014"></a>
## talking-while-coding-014 — Correct versus wrong source content and residual confound

Source: [physical PDF page 5](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=5); reading unit `p005`, lines 58–88.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-013](#talking-while-coding-013), [talking-while-coding-015](#talking-while-coding-015)

```text
Same-form comments lift the recipient only
when their content is correct.Source-correct
and source-wrong directly compare two blocks
with the same form, differing only in whether the
described solution is correct. The two subsets are
disjoint by construction, and each is tested against
its own matched-prompt baseline to control for dif-
ficulty. Correct content lifts the recipient’s pass@1
by 17.2% on average on the source-pass subset.
All 12 (recipient, source) source-correct cells pass
Holm-Bonferroni at pholm<0.001 (Table 1). Same-
form content describing a wrong solution leaves
pass@1 essentially unchanged on the source-fail
subset, and none of the 12 source-wrong cells
reaches significance. With form fixed and difficulty
controlled at the subset level, the property that car-
ries the lift is whether the comment describes a
correct solution. One residual confound is worth
flagging. Source-wrong comments are written on
harder problems and may also differ from source-
correct in tentative or confused style. The matched-
subset baselines control for problem difficulty in
pass@1 terms, but equalizing the baseline level
does not equalize headroom: recipients sit near the
floor on the source-fail subset, so the source-wrong
null cannot by itself separate wrong content from
unsolvable problems. We therefore treat source-
wrong as supporting evidence, and rest the content
claim on two comparisons that avoid the source-fail
subset entirely: the corrupted-comment condition
and the wrong-topic contrast below.
```

<a id="talking-while-coding-015"></a>
## talking-while-coding-015 — Minimal-corruption design

Source: [physical PDF page 5](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=5); reading unit `p005`, lines 89–98.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-014](#talking-while-coding-014), [talking-while-coding-016](#talking-while-coding-016)

```text
Corrupting one step of a correct comment re-
moves the lift on the same problems.On the
source-pass subset, we ask an LLM to make each
correct comment block wrong in exactly one place,
replacing the algorithm name or one key step while
preserving length, line count, and tone (on average
2.3 of about 10 lines change; 50 samples verified
by hand; prompt in Appendix B.6). This holds
difficulty, form, and style fixed while flipping only
content correctness. For all four recipients tested,
```

<a id="talking-while-coding-016"></a>
## talking-while-coding-016 — Table 2: corrupted-comment results and style controls

Source: [physical PDF page 6](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=6); reading unit `p006`, lines 1–18.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-015](#talking-while-coding-015), [talking-while-coding-017](#talking-while-coding-017)

```text
Recipient Baseline Source-correct Corrupted
Qwen3-8B 53.6 70.8 (+17.2) ∗ 48.2 (−5.4)∗
Seed-Coder-8B 43.9 58.3 (+14.4) ∗ 41.9 (−2.0)
CodeGeeX4-9B 26.4 52.3 (+25.9) ∗ 28.4 (+2.0)
Gemma-4-E4B-IT 71.3 85.2 (+13.9) ∗ 74.2 (+2.9)
∗ Holm-significant vs baseline. The drop from source-correct to corrupted
is Holm-significant atp holm<0.001for all four recipients.
Table 2: Recipient pass@1 (%) on the source-pass sub-
set (gemini source) when the correct comment block is
minimally corrupted. Parentheses give∆vs baseline.
the corrupted condition falls back to the baseline
range, and the drop from source-correct is Holm-
significant atp holm<0.001(Table 2).
Style rewrites of the same correct blocks (para-
phrased, compressed, hedged, vague) corrobo-
rate this: only removing specific task information
hurts, and wording, length, and tone do not (Ap-
pendix D.1).
```

<a id="talking-while-coding-017"></a>
## talking-while-coding-017 — Wrong-topic and random-prefix controls

Source: [physical PDF page 6](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=6); reading unit `p006`, lines 19–40.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-016](#talking-while-coding-016), [talking-while-coding-018](#talking-while-coding-018)

```text
Wrong-topic and random prefixes hurt rather
than help.Two controls replace the useful con-
tent while preserving the comment-block form.
Wrong-topic comments use natural-language com-
ments from a different problem, while length-
matched random text removes coherent problem
content entirely (Appendix D.5). Both reduce recip-
ient pass@1: wrong-topic by 20.8% across 12 cells
and random text by 17.9% on average (Table 14).
Thus, the lift cannot be explained by merely plac-
ing extra tokens or comment-shaped text before
the code. Source-written and wrong-topic prefixes
are closely matched in token count, comment-line
count, and density, yet produce sharply different
pass@1. Coherent but topic-wrong comments hurt
more than incoherent noise, suggesting that recipi-
ents tend to follow the content of the prefix rather
than ignore it; a direct paired comparison confirms
this asymmetry is significant (Appendix D.5). The
damage concentrates on easy problems (Table 15),
where the recipient would often have solved the
task unaided.
```

<a id="talking-while-coding-018"></a>
## talking-while-coding-018 — Line-shuffling results

Source: [physical PDF page 6](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=6); reading unit `p006`, lines 41–50.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-017](#talking-while-coding-017), [talking-while-coding-019](#talking-while-coding-019)

```text
Most of the source-correct lift survives line shuf-
fling.We shuffle the source-written lines on each
problem, preserving content and form but breaking
order. The recipient retains 68.0% of the source-
correct lift on average ( +11.7% vs +17.2%, Ta-
ble 1), and 10 of 12 shuffled cells survive Holm cor-
rection at pholm<0.001. The remaining 32.0% loss
concentrates on easy problems where the recipient
would have picked the right approach unaided (full
per-recipient breakdown in Appendix D.6). Our
```

<a id="talking-while-coding-019"></a>
## talking-while-coding-019 — Table 3 and shuffling interpretation

Source: [physical PDF page 6](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=6); reading unit `p006`, lines 51–77.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-018](#talking-while-coding-018), [talking-while-coding-020](#talking-while-coding-020)

```text
Recipient Split Source-correct Source-wrong Wrong-topic
Qwen3-8B C# 19.2 (+0.0) 5.7 (+2.9) 0.0 (−9.8)
Java 61.1 (+16.7) 3.4 (−3.4) 13.8 (−13.8)∗
Seed-Coder-8BC# 38.5 (+15.4) 2.9 (+0.0) 9.8 (−1.6)
Java 72.2 (+5.6) 6.9 (−5.2) 37.7 (−4.6)
CodeGeeX4-9BC# 15.4 (+0.0) 0.0 (−2.9) 4.9 (−3.3)
Java 73.6 (+1.4) 3.4 (+0.0) 35.4 (−6.2)
Gemma-4-E4B-ITC# 34.6 (+15.4) 2.9 (+0.0) 4.9 (−4.9)
Java 76.4 (+11.1) 3.4 (−6.9) 29.2 (−11.5)
∗ Holm-significant at α=0.05 over m=24 (recipient, split, condition)
tests. Every cell that reaches significance moves in the direction of Sec-
tion 4.1; no cell moves significantly against it.
Table 3: Recipient pass@1 (%) on RepoClassBench
(Claude-Opus-4.7 source). Parentheses give ∆ vs the
matched baseline; condition definitions follow Sec-
tion 4.1.
data is consistent with comment lines functioning
as local hints, each contributing largely indepen-
dently of the others with a smaller order-sensitive
component. They do not behave as a step-by-step
derivation. At the per-problem level, 89 problems
flip from fail to pass under correct prefill while
only 3 flip the other direction, a 30:1 ratio (Ap-
pendix D.7). These 89 problems span all difficulty
bands (56 medium, 18 easy, 15 hard), so the lift
is not confined to rescuing the hardest problems.
Qualitative examples are in Appendix D.8.
```

<a id="talking-while-coding-020"></a>
## talking-while-coding-020 — Repository-level replication design and results

Source: [physical PDF page 6](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=6); reading unit `p006`, lines 78–103.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-019](#talking-while-coding-019), [talking-while-coding-021](#talking-while-coding-021)

```text
The content effect generalizes beyond Python
single-file tasks to C# and Java repository-level
settings.LiveCodeBench is single-file Python
competitive programming, so we replicate the core
intervention on both splits of RepoClassBench
(Deshpande et al., 2024): C# (61 tasks) and Java
(130 tasks, excluding 2 whose build environment
fails in every condition). Each task asks the model
to write a complete class from its natural-language
description inside a real repository, and a genera-
tion passes only if it compiles against the repos-
itory and passes the repository’s own tests. Our
strongest prefix-source,Claude-Opus-4.7, writes
a comment block for each task; we inject it into
all four prefix-recipients (Qwen3-8B, Seed-Coder-
8B, CodeGeeX4-9B, Gemma-4-E4B-IT) under the
baseline, source-written, and wrong-topic condi-
tions of Section 4.1, and test with paired exact
McNemar as before.
In Table 3, every cell that reaches significance
moves in the direction Section 4.1 predicts, and
no cell moves significantly against it; the remain-
ing cells are flat within noise. Correct comments
lift pass@1 on Java when pooled across recipients
(41 problems gained versus 16 lost, p=0.001), and
wrong-topic comments hurt on both splits (Java:
```

<a id="talking-while-coding-021"></a>
## talking-while-coding-021 — Repository replication: significance and headroom

Source: [physical PDF page 7](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=7); reading unit `p007`, lines 1–21.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-020](#talking-while-coding-020), [talking-while-coding-022](#talking-while-coding-022)

```text
18 gained versus 65 lost, p<0.001; C#: 4 versus
16, p=0.012). Qwen3-8B’s Java wrong-topic cell
is the only individually Holm-significant cell, mov-
ing −13.8% (pholm=0.022); its Java source-correct
cell shows the largest individual lift at +16.7% but
does not survive per-cell correction alone, consis-
tent with the effect emerging most clearly at the
pooled level above. On the same source-pass tasks,
with task, model, and comment form all matched,
the correct comment beats the wrong-topic com-
ment 75 to 9 on Java and 20 to 2 on C# (both
p<0.001).
The effects concentrate where the recipient has
headroom. The C# baselines sit below 12%, and
Seed-Coder-8B starts from 66.7% on the Java
source-pass subset; in both regimes the per-cell
deltas compress toward zero, echoing the difficulty
analysis of Table 15. The content effect is therefore
not an artifact of single-file Python competitive
programming, although its visible size depends on
how much room the recipient has to move.
```

<a id="talking-while-coding-022"></a>
## talking-while-coding-022 — Self-elicitation policies and comparison design

Source: [physical PDF page 7](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=7); reading unit `p007`, lines 22–73.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-021](#talking-while-coding-021), [talking-while-coding-023](#talking-while-coding-023)

```text
4.2 Can prompting alone reproduce what
prefilling external comments gives us?
We showed in Section 4.1 that a correct external
comment block lifts the recipient’s pass@1 substan-
tially. A natural follow-up is whether the recipient
can produce a comparable comment from its own
prompt, without an external source. We test this
with 14 models and 10 prompt variants.
The pool comprises the four prefix-recipients
from Section 4.1 plus 10 popular self-run models
spanning the pass tiers of Section 3.1 (full list in
Appendix C.1). Nine prompt policies vary along
three dimensions;base(no policy) serves as the
natural comparison anchor, for 10 conditions in
total.
V olumecontrols the amount of commenting the
model produces:noneforbids all comments (in-
line, block, and docstrings),rarecaps comments at
one short note per logical block and disallows doc-
strings or multi-line explanations,denserequires
a 2–5 line comment before each major block, with
explicit reasoning about why the approach is cor-
rect.
Intentcontrols what the comments say, mirror-
ing the WHY/WHAT axis of Section 3.2:WHAT
requires every block or non-trivial line to carry a
comment describing what the code does,WHYre-
quires comments explaining the motivation behind
each design choice,mixrequires both in the same
comment.
F ormatcontrols how the comments are orga-
nized:gp-docprovides a human-convention refer-
ence — the Google Python Style Guide (Google,
2024) that pairs per-function docstrings with sparse
inline comments on non-obvious parts,topreuses
the prefix-source’s prompt template from Sec-
tion 4.1, requesting a 5–15 line#-prefixed comment
block at the head of the recipient’s output,inline
embeds reasoning as inline comments interleaved
with the code, adapted from Jiang et al. (2026).
The full policy text for each variant is in Ap-
pendix B.4. Figure 2 shows representative output
under each variant on a common code body.
Decoding follows Appendix C.2, with only the
appended system policy varying across cells. For
each (model, variant) cell we report ∆pass@1
against the model’sbasepass@1 on the same
problems, paired-tested with McNemar and cor-
rected with Holm-Bonferroni over the 126 non-
baseline cells at family-wise α=0.05. We also
report whether each model follows the surface in-
struction of its variant.
```

<a id="talking-while-coding-023"></a>
## talking-while-coding-023 — Prompt gains, losses and recipient differences

Source: [physical PDF page 7](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=7); reading unit `p007`, lines 74–102.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-022](#talking-while-coding-022), [talking-while-coding-024](#talking-while-coding-024)

```text
Across the four recipients, self-elicitation pro-
duces at most a quarter of the external-comment
lift.Among the four prefix-recipients from Sec-
tion 4.1, only Qwen3-8B underdenseachieves
a Holm-significant prompt-induced lift ( +4.4%).
For comparison, the same model gains 18.1% on
average when given an external correct comment
block (Table 1). Self-prompting therefore recovers
only about 24% of that effect. For the other three
recipients, no variant achieves a Holm-significant
lift (Appendix D.10). A correct comment from
a stronger model is therefore not interchangeable
with a prompt asking the recipient to write its own.
The same prompt lifts some models and dam-
ages others.Every non-baseline variant in Ta-
ble 4 has at least one model it lifts and at least
one it damages. The Holm-significant cells in Ap-
pendix D.10 include substantial moves in both di-
rections for each variant. GPT-5.1-Codex-Mini
underWHATgains 4.9% (pholm = 3.3×10 −3),
while Gemma-4-E4B-IT undernoneloses 14.5%
(pholm = 2.3×10 −30).toplifts DeepSeek-V3.2 by
6.2% but drops GPT-OSS-120B by 13.7%.none
lifts GPT-OSS-120B but is the largest damaging
cell in the grid for Gemma-4-E4B-IT. The variance
is in the receiving model, not the prompt text. A
generic “the prompt was unclear” explanation does
not fit, since the same instruction unlocks pass@1
on some models.
```

<a id="talking-while-coding-024"></a>
## talking-while-coding-024 — Table 4: full prompt-variant results

Source: [physical PDF page 8](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=8); reading unit `p008`, lines 1–18.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together. Several adjacent table values are concatenated in pinned text; the original Table 4 is needed to distinguish columns.

Related: [talking-while-coding-023](#talking-while-coding-023), [talking-while-coding-025](#talking-while-coding-025)

```text
Volume Intent Format
Model base none rare dense WHAT WHY mix gp-doc top inline
♦Grok-4.1-Fast 85.1 84.8 84.4 83.3 82.0 81.0 ∗ 82.4 82.8 83.7 84.8
♦Gemini-3.1-Flash-Lite 72.5 65.6 ∗ 67.0 ∗ 72.4 69.8 71.6 70.7 72.3 66.7 ∗ 72.7
GPT-OSS-120B 69.172.5 71.5 70.0 74.3 ∗ 75.4 ∗ 76.3 ∗ 73.855.4 ∗ 55.2 ∗
GPT-5.1-Codex-Mini 64.6 64.2 64.4 56.5 ∗ 69.5 ∗ 69.0 ∗ 68.9 ∗ 67.751.1 ∗ 55.3 ∗
DeepSeek-V3.2 64.3 58.2 ∗ 58.8 ∗ 65.962.766.7 65.759.2 ∗ 70.4 ∗ 60.5
Qwen3-235B-A22B 59.8 58.3 58.660.8 61.4 65.5 ∗ 63.2 61.6 61.358.7
GPT-5.4-Nano 59.6 46.1 ∗ 57.065.4 ∗ 63.0 63.3 62.3 61.457.664.8 ∗
MiMo-V2-Flash 55.956.3 56.2 61.6 ∗ 58.8 63.1 ∗ 58.9 57.946.9 ∗ 60.2
Gemma-4-E4B-IT † 53.7 39.2 ∗ 46.1 ∗ 42.2 ∗ 47.4 ∗ 52.5 50.9 49.7 ∗ 54.252.2
Llama-4-Maverick 45.3 43.5 45.2 44.6 32.6 ∗ 45.442.9 38.5 ∗ 33.7 ∗ 45.6
Mistral-Small-2603 44.2 42.5 42.948.5 ∗ 44.246.2 46.5 46.6 45.4 46.8
Seed-Coder-8B † 33.435.4 33.929.535.131.734.231.5 32.336.1
Qwen3-8B † 37.0 35.4 36.441.3 ∗ 39.7 40.1 38.5 39.2 39.2 39.6
CodeGeeX4-9B † 22.1 20.2 20.3 19.8 17.7 ∗ 17.1 ∗ 18.6 20.7 19.4 21.5
∗ Holm-significant atα=0.05(paired McNemar,m=126; 38/126 survive).♦= prefix-source; † = prefix-recipient. Variant prompts in Appendix B.4.
Table 4: Effect of 10 prompt variants on pass@1 across 14 models.Bold= exceedsbase.
```

<a id="talking-while-coding-025"></a>
## talking-while-coding-025 — Compliance, explicit planning and two-stage results

Source: [physical PDF page 8](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=8); reading unit `p008`, lines 19–45.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-024](#talking-while-coding-024), [talking-while-coding-026](#talking-while-coding-026)

```text
Compliance with the form instruction does
not predict whether pass@1 goes up or down.
Prompt instructions are followed in practice across
all 10 variants, yet pass@1 still moves in both di-
rections on each model. The token shift undernone
does not explain the pass@1 changes.
Stronger self-planning prompts and a two-stage
pipeline do not close the gap.Two further set-
tings test whether the gap reflects weak prompt-
ing rather than a deeper limitation. An explicit
self-planning prompt (SP) asks the model to write
a structured plan before coding, while a two-
stage pipeline (TS) first elicits a standalone plan
and then feeds it back to the same model be-
fore regeneration (full prompts in Appendix B.5).
We test both on two deliberately favorable mod-
els: Gemini-3.1-Flash-Lite, whose external
comment blocks strongly help recipients, and
GPT-OSS-120B, the grid model most responsive
to intent-style prompts. Across the four cells,
pass@1 changes by only +1.6%, +1.9%, −0.6%,
and +0.9%, with none significant. Even the largest
estimate recovers only about a tenth of the aver-
age external-comment effect. Thus, the gap is not
explained by weak prompting or the single-pass
format: self-produced plans still do not reliably
encode a correct solution.
```

<a id="talking-while-coding-026"></a>
## talking-while-coding-026 — Length changes and baseline commenting habits

Source: [physical PDF page 8](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=8); reading unit `p008`, lines 46–77.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-025](#talking-while-coding-025), [talking-while-coding-027](#talking-while-coding-027)

```text
Output-length changes do not explain the
pass@1 effects.Undernone, mean code tokens
change by −21.8% across the 14-model pool, rang-
ing from −59% on Gemma-4-E4B-IT to +46%
on MiMo-V2-Flash (Appendix D.12). Yet these
large length shifts do not correspond to propor-
tional pass@1 changes: Mistral-Small-2603 loses
43% of its code tokens with no significant accuracy
change, while MiMo-V2-Flash gains 46% with
none either. The direction of the pass@1 effect
instead depends on the receiving model. This again
supports the diagnosis from Section 4.1: prompt-
ing controls comment form, but not whether the
content encodes a correct solution.
Models that comment heavily at baseline are the
most damaged by being told not to.The three
biggest losses in the grid all come fromnoneap-
plied to models with a strong head-block comment-
ing habit at baseline. These are Gemma-4-E4B-IT
(−14.5%), GPT-5.4-Nano (−13.6%), and Gemini-
3.1-Flash-Lite (−6.9%). Each is the model’s own
largest single damage cell (Appendix D.10). The
natural reading is that these models depend on the
comment block their own decoding produces, and
noneremoves it. This is the cleanest cross-model
pattern in the grid. Intent-prompt effects do not par-
tition the pool by baseline form alone. GPT-OSS-
120B and GPT-5.1-Codex-Mini gain from intent
variants, but other low-comment models such as
Llama-4-Maverick are damaged by the same vari-
ants. The effect of each variant otherwise remains
tied to the receiving model.
```

<a id="talking-while-coding-027"></a>
## talking-while-coding-027 — Conclusion opening

Source: [physical PDF page 8](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=8); reading unit `p008`, lines 78–82.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-026](#talking-while-coding-026), [talking-while-coding-028](#talking-while-coding-028)

```text
5 Conclusion
In this paper, we asked whether comments, natural-
language text an LLM emits in the same forward
pass as the code it generates, functionally sup-
port its own pass@1. The natural distribution
```

<a id="talking-while-coding-028"></a>
## talking-while-coding-028 — Figure 2: Two-Sum comment variants

Source: [physical PDF page 9](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=9); reading unit `p009`, lines 1–18.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: The base extraction concatenates code/comment lines and line numbers. This is not a faithful code transcription. Figure 2 was visually inspected; supplemental transcription supplied for coordinator integration.

Related: [talking-while-coding-027](#talking-while-coding-027), [talking-while-coding-029](#talking-while-coding-029)

```text
rare1234567
# one-pass with hash mapseen ={}fori,n inenumerate(nums):iftarget -n inseen:return[seen[target -n],i]seen[n]=ireturn[]
dense1234567891011121314151617
# Build a hash map from value to# index for O(1) complement lookup.# Naive O(n^2) search -> O(n).seen ={}# Walk (index, value) pairs once.# Complement of n is target -n.fori,n inenumerate(nums):# Check complement BEFORE add# Avoid pairing same index# with itself if target = 2*n.iftarget -n inseen:return[seen[target -n],i]# Insert after lookup to keep# the invariant.seen[n]=i# No valid pair satisfies the sum.return[]
WHAT123456789101112
# initialize hash map value -> indexseen ={}# iterate over (index, value) pairsfori,n inenumerate(nums):# check if complement was storediftarget -n inseen:# return matching indicesreturn[seen[target -n],i]# record value with its indexseen[n]=i# no pair foundreturn[]
WHY123456789101112
# use a hash map to reduce time# complexity from O(n^2) to O(n)seen ={}fori,n inenumerate(nums):# complement lookup is O(1),# avoiding inner loop scaniftarget -n inseen:return[seen[target -n],i]# store after lookup to avoid# using the same index twiceseen[n]=ireturn[]
mix12345678910111213
# use a hash map for O(n) lookups# instead of an O(n^2) double loopseen ={}# maps value -> indexfori,n inenumerate(nums):# scan each value once, in ordercomplement =target -n# has the complement been seen?ifcomplement inseen:return[seen[complement],i]# store only after the check so# an index never pairs with selfseen[n]=ireturn[]
gp-doc12345678910111213141516
"""Return indices of two numbers innums that sum to target.Args:nums: list of integers.target: integer sum.Returns:list[int]: pair of indices i < jwith nums[i] + nums[j] == target,or [] if no such pair exists."""seen ={}fori,n inenumerate(nums):iftarget -n inseen:return[seen[target -n],i]seen[n]=ireturn[]
top123456789101112131415161718
# Core Strategy: one-pass hash-map# lookup -O(n) time, O(n) space.# State Mapping: seen[v] = earliest# index where value v was observed.# Invariant: when testing target -n# at index i, all j < i are in seen.# Complexity: O(1) amortized per# op, O(n) total.# Corner Cases:#   -no pair found -> return []#   -duplicate values: store after#     lookup to avoid reuseseen ={}fori,n inenumerate(nums):iftarget -n inseen:return[seen[target -n],i]seen[n]=ireturn[]
inline123456
seen ={}# value -> first indexseenfori,n inenumerate(nums):# walkleft to rightiftarget -n inseen:# complement already stored?return[seen[target -n],i]# match foundseen[n]=i  # record current forlater complementsreturn[]# no pair exists
Figure 2: Output under each prompt variant on the same Two-Sum body (a classic competitive-programming
problem).
```

<a id="talking-while-coding-029"></a>
## talking-while-coding-029 — Conclusion and authors? practical implications

Source: [physical PDF page 9](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=9); reading unit `p009`, lines 19–49.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-028](#talking-while-coding-028), [talking-while-coding-030](#talking-while-coding-030)

```text
of commenting habits across 88 models on Live-
CodeBench does not track pass@1, whether we
measure how much models comment or what their
comments say. A controlled intervention then at-
tached a comment block from a stronger source
to a weaker recipient and varied what the source’s
comment said while holding everything else fixed.
Correct content raises the recipient’s pass@1 by
17.2% on average across 12 such pairings, while
comments matched in surface form but describing
a wrong solution leave it unchanged, and coher-
ent comments on a different problem damage it by
20.8%. The lift therefore comes from the correct-
ness of the described solution.
Asking the recipient to produce the same com-
ments from its own prompt fails for three of the
four recipients, and recovers at most about 24% of
the external-comment lift in the best case. Prompt
engineering controls how the comments look but
not whether their content is correct. A comment
helps pass@1 only when its content describes a
correct solution, which a stronger source can pro-
vide but a recipient cannot reliably elicit through
its own prompt.
Practically, a model’s reliance on comments can
be checked cheaply with the none-versus-base con-
trast, and comment policies should follow that pro-
file: suppressing comments costs up to 14.5% on
comment-dependent models, while helping others.
Closing the gap itself likely requires training-time
methods, which we leave to future work.
```

<a id="talking-while-coding-030"></a>
## talking-while-coding-030 — Limitations and calibration provenance

Source: [physical PDF page 9](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=9); reading unit `p009`, lines 50–66.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-029](#talking-while-coding-029), [talking-while-coding-031](#talking-while-coding-031)

```text
Limitations
Although our intervention isolates content cor-
rectness as the property that drives the comment-
induced lift, the experimental scope remains lim-
ited. Despite testing ten prompt variants plus ex-
plicit self-planning and two-stage pipelines (Sec-
tion 4.2), we did not find a prompting method
that reliably reproduces the external-comment lift
through self-elicitation; closing this gap likely re-
quires training-time methods, which we leave to
future work.
Ethics Statement
This work is an empirical study of code generated
by publicly available LLMs on a public bench-
mark (LiveCodeBench-v6) under its public release
terms. No human subjects research was conducted.
The 100-snippet calibration set used to validate
```

<a id="talking-while-coding-031"></a>
## talking-while-coding-031 — Calibration, compute and authorship statement

Source: [physical PDF page 10](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=10); reading unit `p010`, lines 1–10.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-030](#talking-while-coding-030), [talking-while-coding-032](#talking-while-coding-032)

```text
the LLM judge was hand-labelled by one of the
authors. Self-run generations are produced via
publicly available APIs and open-weights models
with their corresponding licences. Total compute
is approximately $500 USD of API spend plus 200
A100-hours of local GPU time. The authors used
commercial LLM assistants for sentence-level writ-
ing revision and analysis-script drafting, while all
experimental design, statistical claims, and final
manuscript content remain the authors’ own.
```

<a id="talking-while-coding-032"></a>
## talking-while-coding-032 — Appendix A.1: codebook, calibration and Table 5

Source: [physical PDF page 11](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=11); reading unit `p011`, lines 57–105.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-031](#talking-while-coding-031), [talking-while-coding-033](#talking-while-coding-033)

```text
A Statistical details
A.1 LLM-judge calibration on 100-snippet
stratified subset
Seven-class codebook.The human reference an-
notator and the LLM judge in Section 3.2 both
apply a seven-class codebook to each in-code com-
ment line.rationaleexplains WHY a design choice
was made (algorithm trade-off, edge case justi-
fication, motivation).algorithmnames or sum-
marises the high-level approach (“binary search”,
“two-pointer”, “DP with memoisation”).stepde-
scribes what a specific line or local block of code
does in procedural terms.mechanismexplains a
specific code mechanism, invariant, or low-level
detail.definitionlabels or names a variable, data
structure, or quantity.decorationcovers metadata,
TODOs, section headers, and aesthetic comments.
misleadingis factually incorrect with respect to the
code it accompanies. The main-text WHY / WHAT
/ OTHER aggregation maps rationale to WHY ,
algorithm + step + mechanism + definition
to WHAT, and decoration + misleading to
OTHER.
Calibration.We hand-labelled 100 in-code com-
ment snippets stratified by intent class and com-
pared the human annotation against the LLM judge
(Gemini-3.1-Flash-Lite) on the same snippets.
For each of the seven intent classes, we compute
the per-label binary κ (does the human / does the
judge assign this label).
Label Binaryκ95% bootstrap CI
rationale+0.74 [+0.58,+0.87]
algorithm+0.72 [+0.55,+0.86]
mechanism+0.38 [+0.18,+0.57]
definition+0.48 [+0.27,+0.66]
step+0.02 [−0.12,+0.16]
decoration+0.11 [−0.04,+0.27]
misleading∼0(n=2, too sparse)
Table 5: Per-label binary Cohen’sκ on the 100-snippet
calibration subset. The two anchor labels (rationale
for WHY ,algorithm for WHAT) show κ≥0.7 ; the
remaining five labels have lower agreement and are
absorbed into WHY/WHAT/OTHER.
Bucket-level agreement.Because Sec-
tion 3.2 draws its conclusions on the aggregated
WHY/WHAT/OTHER buckets, we also report
agreement at the bucket level on the same 100
snippets (Table 6). WHAT’s positive rate is
extreme (85–88% of snippets), a regime where
```

<a id="talking-while-coding-033"></a>
## talking-while-coding-033 — Bucket agreement, Table 6 and correlation correction

Source: [physical PDF page 12](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=12); reading unit `p012`, lines 1–32.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; prompts/codebooks are artifacts reported by these authors, with adaptations credited as stated

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-032](#talking-while-coding-032), [talking-while-coding-034](#talking-while-coding-034)

```text
Cohen’s κ understates agreement (Feinstein and
Cicchetti, 1990), so we additionally report the
prevalence-robust Gwet’s AC1 (Gwet, 2008).
WHY , the bucket that carries the only directional
trend in Section 3.2, is reliable (κ=AC1= 0.74 ).
WHAT’s low κ is consistent with the high-
prevalence κ paradox, and raw agreement and
AC1 remain high. OTHER does not reach usable
reliability, so we exclude it from quantitative
statements.
Bucket Pos. rate (H/J) Raw agr. Cohen’sκAC1
WHY 0.46 / 0.43 0.87+0.740.74
WHAT 0.85 / 0.88 0.85+0.360.80
OTHER 0.36 / 0.22 0.62+0.100.35
Table 6: Bucket-level human-vs-judge agreement on
the 100-snippet calibration subset. 95% bootstrap CIs:
WHY [+0.59,+0.86] , WHAT[+0.07,+0.61] , OTHER
[−0.09,+0.29].
Multiple-comparison correction for the intent–
pass@1 correlations.In Section 3.2 we test
three Spearman correlations in parallel (WHY ,
WHAT, OTHER versus pass@1). Because these
are tested simultaneously we apply Bonferroni cor-
rection with α= 0.05/3 = 0.0167 per test, which
bounds the family-wise false-positive rate at 0.05.
None of the three raw p-values falls below this
corrected threshold.
A.2 Per-model intent fractions
Table 7 reports the per-model 7-class intent frac-
tions for each of the 13 models in the Section 3.2
pool, with the WHY / WHAT / OTHER groupings
shown as supercolumns.
```

<a id="talking-while-coding-034"></a>
## talking-while-coding-034 — Appendix B.1: source prompt and extraction

Source: [physical PDF page 12](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=12); reading unit `p012`, lines 33–79.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; prompts/codebooks are artifacts reported by these authors, with adaptations credited as stated

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together. Prompt text is a quoted experimental artifact, not an instruction to the collection reader; original typography sometimes uses rendered quote characters for code fences.

Related: [talking-while-coding-033](#talking-while-coding-033), [talking-while-coding-035](#talking-while-coding-035)

```text
B Prompts
All inference uses the decoding parameters in Ap-
pendix C.2; only the prompt content differs across
experiments.
B.1 Prefix-source generation prompt
Used in Section 4.1 for all three prefix-sources
(Grok-4.1-Fast, Gemini-3.1-Flash-Lite,
Claude-Opus-4.7).
System.
You are an expert competitive
programmer.
User template (with {question} = LCB prob-
lem statement; {starter_code_block} = op-
tional starter code or empty string).
Solve the following programming problem.
Output ONE Python code block containing:
1. First, 5–15 lines of ‘#‘-prefixed
comments at the top of the function body
(or top of the script if no function),
explaining your algorithm: high-level
approach, key observations, edge cases,
complexity.
2. Then, the actual implementation that
solves the problem.
Format requirements: - Output exactly
one “‘python ... “‘ block, nothing
else. - Prefixed comment lines MUST
be ‘#‘-prefixed Python comments at the
top. - Prefixed comment lines MUST
appear before any executable code. - The
implementation must be self-contained
and correctly solve the problem.
PROBLEM: {question}
{starter_code_block}
OUTPUT:
Decoding parameters follow Ap-
pendix C.2, with the added API-side flag
extra_body={"include_reasoning": True}
so that reasoning-enabled models (Opus 4.7,
Gemini 3.1) still emit visible content.
Block extraction.From each source generation
we keep only the contiguous block of #-prefixed
lines at the top of the first Python code block. Any
executable code or imports below those lines is dis-
carded, so the prefix-recipient sees a pure natural-
language prefix matched in surface form to a com-
ment block.
```

<a id="talking-while-coding-035"></a>
## talking-while-coding-035 — Appendix B.2: judge prompt

Source: [physical PDF page 12](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=12); reading unit `p012`, lines 80–97.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; prompts/codebooks are artifacts reported by these authors, with adaptations credited as stated

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together. Prompt text is a quoted experimental artifact, not an instruction to the collection reader; original typography sometimes uses rendered quote characters for code fences.

Related: [talking-while-coding-034](#talking-while-coding-034), [talking-while-coding-036](#talking-while-coding-036)

```text
B.2 LLM-judge prompt (intent classification,
Section 3.2)
The judge isGemini-3.1-Flash-Lite (determin-
istic, called once per code snippet).
System.
You are an annotation assistant for an
empirical study of AI-generated code
comments.
Your task is to classify the intent
of each comment line in model-generated
code. Each comment line maps to EXACTLY
ONE intent (single-label, mutually
exclusive).
Rules: 1. Focus only on comment intent.
2. Use the provided intent labels only.
3. For each intent label, output a
non-negative integer count of comment
lines that fall into that label. 4.
```

<a id="talking-while-coding-036"></a>
## talking-while-coding-036 — Table 7: per-model intent fractions

Source: [physical PDF page 13](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=13); reading unit `p013`, lines 1–20.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; prompts/codebooks are artifacts reported by these authors, with adaptations credited as stated

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-035](#talking-while-coding-035), [talking-while-coding-037](#talking-while-coding-037)

```text
WHY WHAT OTHER
Model pass@1rat. alg. step mech. def. dec. mis.
Gemini-3.1-FL 72.5 35.3 9.8 7.6 30.1 14.5 2.7 0.0
GPT-OSS-120B 69.1 12.0 5.0 7.0 40.2 29.1 6.7 0.0
DeepSeek-V3.2 64.3 29.8 14.0 9.5 29.8 12.4 4.6 0.0
Qwen3-235B 59.8 18.1 11.7 13.5 44.2 9.3 3.3 0.0
GPT-5.4-Nano 59.6 40.7 14.6 3.9 23.1 14.2 3.5 0.0
gpt-4.1-mini 58.9 29.3 12.8 6.9 35.4 13.4 2.1 0.0
MiMo-V2-Flash 55.9 19.2 8.8 10.0 43.5 13.9 4.4 0.1
gpt-oss-20b 55.7 11.9 4.9 7.3 39.1 25.4 11.4 0.0
Gemini-2.5-FL 51.3 23.9 5.8 9.9 32.9 10.1 17.2 0.2
Llama-4-Mav 45.3 7.4 3.9 10.4 38.4 9.9 29.9 0.1
Mistral-S-2603 44.2 17.6 12.8 12.5 29.3 6.6 20.3 0.7
Qwen3-Coder-30B 38.5 12.5 7.5 20.3 46.9 8.7 4.1 0.1
DSCoder-V2-Lite 25.2 3.5 7.9 39.2 36.3 7.4 5.5 0.2
Table 7: Per-model 7-class intent fractions (%) across the 13-model Section 3.2 pool. Column abbreviations: rat.
= rationale, alg. = algorithm, mech. = mechanism, def. = definition,dec. = decoration, mis. = misleading. The
three groupings used in Section 3.2 are:WHY= rat.;WHAT= alg. + step + mech. + def.;OTHER= dec. +
mis.. Fractions are averaged over each model’s comment-bearing samples on LiveCodeBench, sorted by pass@1
descending. Rows sum to 100%.
```

<a id="talking-while-coding-037"></a>
## talking-while-coding-037 — Judge prompt continued and label tie-breaks

Source: [physical PDF page 13](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=13); reading unit `p013`, lines 21–53.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; prompts/codebooks are artifacts reported by these authors, with adaptations credited as stated

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together. Prompt text is a quoted experimental artifact, not an instruction to the collection reader; original typography sometimes uses rendered quote characters for code fences.

Related: [talking-while-coding-036](#talking-while-coding-036), [talking-while-coding-038](#talking-while-coding-038)

```text
Each comment line counts in EXACTLY ONE
intent. If a comment fits multiple
labels, apply the tie-break priority
below and pick the highest. 5. Therefore:
total comment lines in the snippet ==
rationale + algorithm + step + mechanism
+ definition + decoration + misleading.
6. If there are no meaningful comments at
all, set "none" to 1 and all other intent
counts to 0. If "none" is positive,
every other intent count must be 0.
7. Output exactly one JSON object and
nothing else.
Tie-break priority (when a comment fits
multiple intents, pick the highest):
misleading > rationale > algorithm
> step > mechanism > definition >
decoration
User template ({CODE} = code snippet to anno-
tate).
Analyze the intent of each comment line
in the following code output. Each line
is assigned to EXACTLY ONE intent.
Return exactly one JSON object with
these fields: - rationale - algorithm
- step - mechanism - definition -
decoration - misleading - none -
evidence
[. . . full label definitions and
tie-break priority repeated here. . . ]
Code: {CODE}
Full label definitions follow the seven-class code-
book in Section 3.2.
```

<a id="talking-while-coding-038"></a>
## talking-while-coding-038 — Recipient prompt and injection mechanism

Source: [physical PDF page 13](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=13); reading unit `p013`, lines 54–90.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; prompts/codebooks are artifacts reported by these authors, with adaptations credited as stated

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together. Prompt text is a quoted experimental artifact, not an instruction to the collection reader; original typography sometimes uses rendered quote characters for code fences.

Related: [talking-while-coding-037](#talking-while-coding-037), [talking-while-coding-039](#talking-while-coding-039)

```text
B.3 Prefix-recipient base prompt (Section 4.1
and Section 4.2)
Prefix-recipients use the standard LCB system
prompt and user template.
System (generic).
You are an expert Python programmer.
You will be given a question (problem
specification) and will generate a
correct Python program that matches the
specification and passes all tests.
User (for stdin/stdout problems).
### Question:
{question_content}
### Format: Read the inputs from stdin
solve the problem and write the answer
to stdout (do not directly test on the
sample inputs). Enclose your code within
delimiters as follows. Ensure that when
the python program runs, it reads the
inputs, runs the algorithm and writes
output to STDOUT.
“‘python # YOUR CODE HERE “‘
### Answer: (use the provided format
with backticks)
Prefix-injection mechanism (Section 4.1).
The injection conditions in Section 4.1 use
tokenizer.apply_chat_template(messages,
continue_final_message=True): the user
prompt is unchanged, and a new assistant-role
message is appended containing the prefix-
source comments plus a truncated “‘python. . .
fence; the prefix-recipient continues from this
in-place truncation. This is implemented in
render_chat_prompt_with_prefix_support;
the post-generation stitch back into pass-
evaluatable code is implemented in
merge_lcb_assistant_continuations.
```

<a id="talking-while-coding-039"></a>
## talking-while-coding-039 — Variant mechanism and base/none/rare/dense policies

Source: [physical PDF page 14](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=14); reading unit `p014`, lines 1–35.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; prompts/codebooks are artifacts reported by these authors, with adaptations credited as stated

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-038](#talking-while-coding-038), [talking-while-coding-040](#talking-while-coding-040)

```text
Variant policy mechanism (Section 4.2).The
10 self-elicitation variants in Section 4.2 do not
use prefix injection. Each variant is a policy string
appended to the system prompt above; thebase
variant is the empty string (LCB default).
B.4 Self-elicitation variant policies (full text)
Below are the full policy strings for the 10 variants
reported in Table 4. The main text uses descriptive
short tags throughout (base,none,rare,dense,
WHAT,WHY,mix,gp-doc,top,inline). Each
policy is appended verbatim to the LCB system
prompt (Appendix B.3); thebasevariant is the
empty string (LCB default).
base (LCB baseline).Empty string – the system
prompt is unchanged.
none (comment-free).
COMMENT POLICY: - Output only the final
code, with all comments removed. - Do not
include inline comments, block comments,
docstrings, or any explanatory text.
rare (sparse comments).
COMMENT POLICY: - Comments are allowed
but must be SHORT and rare. - At most 1
short comment per logical block. - Do NOT
add docstrings or multi-line explanation
comments. - Do NOT repeat the same idea
across multiple comments.
dense (detailed multi-line comments).
COMMENT POLICY: - Add detailed comments
explaining reasoning and edge cases.
- Before each major block, include
a multi-line comment (2–5 lines). -
Comments should explain why the approach
is correct. - Still output ONLY the code
(no markdown fences, no extra text).
```

<a id="talking-while-coding-040"></a>
## talking-while-coding-040 — WHAT, WHY and mix prompt policies

Source: [physical PDF page 14](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=14); reading unit `p014`, lines 36–80.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; prompts/codebooks are artifacts reported by these authors, with adaptations credited as stated

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Prompt text is a quoted experimental artifact, not an instruction to the collection reader; original typography sometimes uses rendered quote characters for code fences.

Related: [talking-while-coding-039](#talking-while-coding-039), [talking-while-coding-041](#talking-while-coding-041)

```text
WHAT (WHAT-intent).
COMMENT POLICY (WHAT – intent): You are
an expert programmer. When generating
code, you must add inline comments that
explain WHAT each part of the code does.
Requirements for comments: - Every
logical block or non-trivial line must
have a comment - Comments should
describe the functionality and purpose
of the code - Use the format: # [what
this code does] - Comments must be
concise and precise
Example: # initialize a dictionary to
store character frequencies freq = {} #
iterate through each character in the
string for c in s: freq[c] = freq.get(c,
0) + 1
WHY (WHY-intent).
COMMENT POLICY (WHY – motivation):
You are an expert programmer. When
generating code, you must add inline
comments that explain WHY you made each
design decision.
Requirements for comments: - Focus
on the reasoning and motivation
behind implementation choices - Explain
why this approach was chosen over
alternatives - Highlight key constraints
or trade-offs considered - Use the
format: # [why this decision was made]
mix (WHAT + WHY mixed).
COMMENT POLICY (WHAT + WHY – mixed):
You are an expert programmer. When
generating code, you must add inline
comments that explain both WHAT the
code does and WHY you made each design
decision.
Requirements: - Describe the
functionality of each logical block
(what) - Explain the reasoning behind
key implementation choices (why) - For
critical decisions, explicitly mention
alternatives that were considered and
rejected - Use the format: # [what] +
[why if non-trivial]
```

<a id="talking-while-coding-041"></a>
## talking-while-coding-041 — Google-style, top and inline policies

Source: [physical PDF page 14](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=14); reading unit `p014`, lines 81–112.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; prompts/codebooks are artifacts reported by these authors, with adaptations credited as stated

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-040](#talking-while-coding-040), [talking-while-coding-042](#talking-while-coding-042)

```text
gp-doc (Google Python Style Guide).
COMMENT AND DOCSTRING POLICY (Google
Python Style Guide): You are an expert
Python programmer who strictly follows
the Google Python Style Guide for
comments and docstrings (Section 3.8).
Block and inline comments: - Only
comment tricky or non-obvious parts.
- Put a short comment block before
complicated operations to explain
intent. - Use inline comments only for
non-obvious behavior. - Focus comments
on WHAT you are trying to achieve and
the intent, not how.
Docstrings: - Every function must have
a docstring using triple double quotes.
- First line is a one-line summary (<=
80 chars) ending with a period. - After
a blank line, include Args / Returns /
Raises sections when relevant.
top (reasoning-at-top, mirrors the prefix-source
prompt).This variant uses the same prompt
template as the prefix-source generation in Ap-
pendix B.1, so that a model’s self-elicitedtop out-
put is the directly-comparable analogue of the pre-
fix that a stronger model would have produced for
the same problem.
inline (inline reasoning, adapted from Jiang
et al., 2026).The wording of this variant is
adapted from Jiang et al. (2026), who study on-
demand inline reasoning at arbitrary token posi-
tions during code generation.
```

<a id="talking-while-coding-042"></a>
## talking-while-coding-042 — Inline-reasoning policy continued

Source: [physical PDF page 15](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=15); reading unit `p015`, lines 1–12.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; prompts/codebooks are artifacts reported by these authors, with adaptations credited as stated

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-041](#talking-while-coding-041), [talking-while-coding-043](#talking-while-coding-043)

```text
You need to generate code with inline
reasoning embedded as comments.
Generate code where your reasoning
process is expressed as inline comments
within the code itself.
Rules: 1. Reasoning MUST appear as
inline comments (# or //) embedded
within the code 2. Comments MUST appear
immediately before or alongside the code
they reason about 3. The code must remain
valid and executable 4. Do not output
any text outside the code block
```

<a id="talking-while-coding-043"></a>
## talking-while-coding-043 — Self-planning and two-stage prompt text

Source: [physical PDF page 15](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=15); reading unit `p015`, lines 13–49.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; prompts/codebooks are artifacts reported by these authors, with adaptations credited as stated

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Prompt text is a quoted experimental artifact, not an instruction to the collection reader; original typography sometimes uses rendered quote characters for code fences.

Related: [talking-while-coding-042](#talking-while-coding-042), [talking-while-coding-044](#talking-while-coding-044)

```text
B.5 Self-planning (SP) and two-stage (TS)
prompts (Section 4.2)
Both conditions append to or replace the same LCB
system prompt used throughout (Appendix B.3);
SPis single-pass,TSis a two-call pipeline that
elicits a standalone plan before code.
SP (self-planning policy, appended to the system
prompt).
Before writing any code, produce an
explicit solution plan as # comment
lines at the top of your code block:
restate the core difficulty, choose
an algorithm and justify why it is
correct for the constraints, decompose
the implementation into numbered steps,
and list edge cases you will handle.
Only after completing this written plan,
implement the code that follows it step
by step.
TS stage 1 (plan-only user prompt; no code).
Write a detailed SOLUTION PLAN for the
following problem. Do NOT write any
code. The plan must: restate the
core difficulty, choose an algorithm
and justify its correctness against the
constraints, decompose the solution into
numbered implementation steps, and list
the edge cases to handle.
### Question: {question}
### Plan:
TS stage 2.The stage-1 plan is inserted ver-
batim into the standard LCB user prompt imme-
diately before the answer marker ( "### Your
plan (written by you in a previous
step):\n{plan}\n\n### Answer:" ), and the
model implements from there with no further
system-prompt change.
```

<a id="talking-while-coding-044"></a>
## talking-while-coding-044 — Minimal semantic corruption prompt and validation

Source: [physical PDF page 15](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=15); reading unit `p015`, lines 50–99.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; prompts/codebooks are artifacts reported by these authors, with adaptations credited as stated

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Prompt text is a quoted experimental artifact, not an instruction to the collection reader; original typography sometimes uses rendered quote characters for code fences.

Related: [talking-while-coding-043](#talking-while-coding-043), [talking-while-coding-045](#talking-while-coding-045)

```text
B.6 Corrupted-comment prompt (Section 4.1)
Used to produce the corrupted condition of Table 2.
The corruptor is Gemini-3.1-Flash-Lite at tem-
perature 0 with JSON output; inputs are the correct
comment blocks on the source-pass subset.
System (abridged; requirement lists shown in
full).
You are assisting a controlled
experiment on code comments. Your task
is MINIMAL SEMANTIC CORRUPTION: given a
programming problem and a comment block
that correctly describes a working
solution, edit the comment block so
that it describes an INCORRECT solution
to this problem, while changing as
little of the surface text as possible.
1. CORRUPT THE CONTENT. Change exactly
ONE central algorithmic commitment so
the described approach would NOT solve
the problem correctly: replace the core
algorithm/technique with one that fails
for this problem, OR invert/break one
key step, condition, or invariant the
solution relies on. The corrupted
approach must be genuinely wrong for
THIS problem, not an alternative valid
solution.
2. MINIMAL EDIT. Rewrite only the lines
that state or directly depend on the
corrupted commitment. Copy every other
line VERBATIM. Aim to keep at least half
of the lines unchanged.
3. PRESERVE ALL SURFACE PROPERTIES:
same number of lines and indentation;
each edited line within roughly±20%
of the original length; same confident,
declarative tone (never “maybe”, “I
think”); same specificity (keep concrete
names, quantities, and complexity
claims, updated to match the corrupted
approach); same phrasing patterns.
4. STAY PLAUSIBLE. The corrupted
block must read like a competent
programmer confidently describing a
reasonable-sounding approach.
The model returns the corrupted block together
with one-sentence statements of the removed and
introduced commitments and the number of lines
edited; we verify a difficulty-stratified sample of
50 corruptions by hand.
```

<a id="talking-while-coding-045"></a>
## talking-while-coding-045 — Style-rewrite prompt skeleton and conditions

Source: [physical PDF page 15](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=15); reading unit `p015`, lines 100–112.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; prompts/codebooks are artifacts reported by these authors, with adaptations credited as stated

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Prompt text is a quoted experimental artifact, not an instruction to the collection reader; original typography sometimes uses rendered quote characters for code fences.

Related: [talking-while-coding-044](#talking-while-coding-044), [talking-while-coding-046](#talking-while-coding-046)

```text
B.7 Style-rewrite prompts (Section 4.1)
Used to produce the four rewrites of Table 9, shar-
ing one system skeleton whose invariants require
the rewritten block to describe the same solution
(same algorithm, steps, conditions, and invariants)
and to change exactly one surface property. The
per-condition modulation instructions are:
paraphrased Reword every line with different vocabulary
and sentence structure but the same meaning; same line
count, tone, and specificity.
compressed Reduce the block to roughly 40–60% of its char-
acter count while remaining information-lossless at the
level of algorithmic commitments.
```

<a id="talking-while-coding-046"></a>
## talking-while-coding-046 — Hedged/vague rewrites and validation

Source: [physical PDF page 16](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=16); reading unit `p016`, lines 1–12.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; prompts/codebooks are artifacts reported by these authors, with adaptations credited as stated

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-045](#talking-while-coding-045), [talking-while-coding-047](#talking-while-coding-047)

```text
hedged Keep every claim identical but rewrite the tone from
confident to tentative, weaving hedges (“maybe”, “I
think”, “probably”) across most lines.
vague Replace concrete commitments with generic descrip-
tions at every line (algorithm names→broad category,
exact conditions → qualitative phrasing, complexity
claims → vague assurances), without introducing any
incorrect claim: the block becomes less informative, not
wrong.
Rewrites failing an automatic validation of these
surface constraints are discarded, giving the per-
conditionnin Table 9.
```

<a id="talking-while-coding-047"></a>
## talking-while-coding-047 — Repository replication setup

Source: [physical PDF page 16](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=16); reading unit `p016`, lines 13–33.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; prompts/codebooks are artifacts reported by these authors, with adaptations credited as stated

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-046](#talking-while-coding-046), [talking-while-coding-048](#talking-while-coding-048)

```text
B.8 RepoClassBench replication setup
(Section 4.1)
Tasks come from the C# and Java splits of Re-
poClassBench (Deshpande et al., 2024); each pro-
vides a natural-language class description, a target
file inside a real repository, and the repository’s
own build and test harness (dotnet/xunit for C#,
Maven/JUnit for Java). The recipient prompt con-
tains the class description, the file path, and the
original file’s import/namespace header; the gener-
ated class is written back into the repository, and
a generation passes only if the repository com-
piles and the task’s test class passes. The prefix-
source (Claude-Opus-4.7) is prompted as in Ap-
pendix B.1 with //-prefixed comments; recipients
receive the extracted comment block through the
same assistant-prefill mechanism as Section 4.1.
Two Java tasks whose Maven build fails in every
condition, including baseline, are excluded. Pooled
contrasts use paired exact McNemar over the union
of (task, recipient) pairs.
```

<a id="talking-while-coding-048"></a>
## talking-while-coding-048 — Model pools and execution configuration

Source: [physical PDF page 16](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=16); reading unit `p016`, lines 34–92.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du; prompts/codebooks are artifacts reported by these authors, with adaptations credited as stated

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-047](#talking-while-coding-047), [talking-while-coding-049](#talking-while-coding-049)

```text
C Models and compute
C.1 Model pool
Self-run by us (Section 3.1; 14 models).Ten
models run via the OpenRouter API with homoge-
neous decoding (listed by base pass@1 descend-
ing):
•Grok-4.1-Fast
•Gemini-3.1-Flash-Lite
•GPT-OSS-120B
•GPT-5.1-Codex-Mini
•DeepSeek-V3.2
•Qwen3-235B-A22B
•GPT-5.4-Nano
•MiMo-V2-Flash
•Llama-4-Maverick
•Mistral-Small-2603
Four additional weak models run locally
with vLLM ( trust_remote_code=True,
dtype=bfloat16, max_model_len=16384,
gpu_memory_utilization=0.8,
enforce_eager=True); these same four also
serve as the prefix-recipients in Section 4.1 (listed
by base pass@1 descending):
•google/gemma-4-E4B-it
•Qwen/Qwen3-8B
•ByteDance-Seed/Seed-Coder-8B-Instruct
•zai-org/codegeex4-all-9b
Leaderboard submissions (Section 3.1; 74 mod-
els).LCB leaderboard submission generations as
published by LiveCodeBench Authors (2024); the
full per-model identifiers and form metrics appear
in Tables 11–12.
Intent-analysis pool (Section 3.2; 13 models).8
of the 10 self-run OpenRouter models above (those
that produce enough comments per problem for
reliable per-model intent estimation), plus 5 LCB
leaderboard submissions selected to broaden pass-
spectrum coverage of the LLM-judge call:
•GPT-4.1-Mini-2025-04-14
•Qwen3-Coder-30B-A3B-Instruct
•Gemini-2.5-Flash-Lite
•GPT-OSS-20B
•DeepSeek-Coder-V2-Lite-Instruct
Prefix-sources used in Section 4.1 (3 strong mod-
els, OpenRouter API).
•x-ai/grok-4.1-fast
•google/gemini-3.1-flash-lite-preview
•anthropic/claude-opus-4.7
Self-elicit pool used in Section 4.2 (14 models,
listed by base pass@1 descending).
•Grok-4.1-Fast , Gemini-3.1-Flash-Lite
(also prefix-sources)
•GPT-OSS-120B , GPT-5.1-Codex-Mini,
DeepSeek-V3.2, Qwen3-235B-A22B,
GPT-5.4-Nano, MiMo-V2-Flash,
Llama-4-Maverick,Mistral-Small-2603
•Gemma-4-E4B-IT , Qwen3-8B,
Seed-Coder-8B-Instruct, CodeGeeX4-9B
(also prefix-recipients)
```

<a id="talking-while-coding-049"></a>
## talking-while-coding-049 — Decoding Table 8, compute and reproducibility

Source: [physical PDF page 17](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=17); reading unit `p017`, lines 1–37.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-048](#talking-while-coding-048), [talking-while-coding-050](#talking-while-coding-050)

```text
C.2 Decoding hyperparameters
Table 8 summarises the decoding parameters across
all experiments.
Parameter Value Where
T(temperature) 0 all
n (samples / prob-
lem)
1 all
max_tokens4096 §4.1, §4.2
top_p0.95 prefix-source API
max_model_len16384 vLLM recipients
dtypebfloat16 vLLM recipients
trust_remote_codeTrue vLLM recipients
enforce_eagerTrue vLLM recipients
Judge MIME JSON §3.2 judge
Judge
include_reasoning
True §4.1 API
Table 8: Decoding hyperparameters across experiments.
All experiments use n=1 and T=0 ; the only variable is
the prompt content.
C.3 Compute statement
Local GPU.All prefix-recipient inference (Sec-
tion 4.1) and self-elicit grid (Section 4.2) ran on
a single NVIDIA A100 80GB with 240 GB host
memory and 13 CPU workers. Total: approxi-
mately 200 A100-hours across all generations.
API spend.Prefix-source generation
(Grok-4.1-Fast, Gemini-3.1-Flash-Lite,
Claude-Opus-4.7) on the full LCB-v6 used
approximately $500 USD of OpenRouter credit.
Reproducibility.Re-analysis (recomputing met-
rics from the existing generations) requires no
GPU or API spend; re-running the controlled-
decomposition section end-to-end requires the
A100 budget above plus access to the listed Open-
Router models.
```

<a id="talking-while-coding-050"></a>
## talking-while-coding-050 — Style-rewrite Table 9 and form metric definitions

Source: [physical PDF page 17](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=17); reading unit `p017`, lines 38–69.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-049](#talking-while-coding-049), [talking-while-coding-051](#talking-while-coding-051)

```text
D Supplementary results
D.1 Style-rewrite results
D.2 Form metric definitions
Each of the 88 model outputs is parsed under one
shared tokenizer (cl100k_base) so that comment
volumes are comparable across vendors, since na-
tive tokenizers are not available for all leaderboard
submissions. The four form metrics are defined
as follows.tok-cmt%is the fraction of output to-
kens that fall inside a comment, where “inside a
comment” covers the span from a comment marker
(#, or a triple-quoted string used as a docstring)
to the end of that comment.block%,inline%,
Rewrite (axis) Qwen3-8B Seed-Coder-8B
paraphrased (wording)−1.0−1.0
compressed (length)−2.7 +3.4 ∗
hedged (confidence)−0.3 +1.4
vague (specificity)−7.0 ∗∗∗ −5.3∗∗
∗p<0.05, ∗∗p<0.01, ∗∗∗p<0.001; unmarked cells are not significant.
Table 9: Change in pass@1 (%) vs source-correct un-
der four single-axis style rewrites of the same correct
comment blocks (gemini source; n=691/700/724/618
rewrites pass validation per condition).
anddoc%follow the PEP-8 partition of comment
forms (van Rossum et al., 2001).block%is the
share of comment tokens that are full-line # com-
ments.inline%is the share of comment tokens
that are # comments appearing on the same line as
code.doc%is the share of comment tokens that
are docstrings. These three shares sum to 100%
over the subset of samples that contain at least one
comment.
```

<a id="talking-while-coding-051"></a>
## talking-while-coding-051 — Form profile and within-model correlation definitions

Source: [physical PDF page 17](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=17); reading unit `p017`, lines 70–88.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-050](#talking-while-coding-050), [talking-while-coding-052](#talking-while-coding-052)

```text
D.3 Full 88-model form profile
Table 10 reports the form spread of the 16 top-tier
models at matched pass@1. Tables 11–12 report
the full per-model form profile for all 88 models,
sorted by pass@1 descending.
D.4 Within-modelρvs pass@1
Table 13 reports the within-model Spearman ρ be-
tween each form axis and per-problem pass@1,
computed independently for each of the 88 mod-
els in the pool. On three of the four axes (block%,
inline%,doc%) no model exceeds |ρ|=0.32 and at
most 13.0% exceed |ρ|=0.20. Comment volume
(tok-cmt%) has a non-trivial upper tail: 22.0% of
models exceed |ρ|=0.20 and the maximum reaches
|ρ|=0.53, which still corresponds to under 30.0%
explained variance. A minority of models there-
fore do exhibit within-model variation, but never
at a magnitude that would change the Section 3.1
conclusion.
```

<a id="talking-while-coding-052"></a>
## talking-while-coding-052 — Random-text control design

Source: [physical PDF page 17](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=17); reading unit `p017`, lines 89–97.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-051](#talking-while-coding-051), [talking-while-coding-053](#talking-while-coding-053)

```text
D.5 Length-matched random-text control
Table 14 reports the recipient’s pass@1 under the
length-matched random-text control ( #-prefixed
filler matched in length to the source-written block).
The control is run on all three sources’ source-pass
subsets (gemini/claude/grok, n=757/892/870)
across four recipients (12 cells), mirroring the
wrong-topic design in Table 1; the matched-prompt
baseline is the recipient’s pass@1 on the same sub-
```

<a id="talking-while-coding-053"></a>
## talking-while-coding-053 — Table 10: matched-performance form profile

Source: [physical PDF page 18](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=18); reading unit `p018`, lines 1–18.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-052](#talking-while-coding-052), [talking-while-coding-054](#talking-while-coding-054)

```text
Model pass@1 tok-cmt% block% inline% doc%
DeepSeek-R1-0528 84.4 0.1 33.8 66.2 0.0
EXAONE-4.0-32B 80.9 0.1 55.0 45.0 0.0
OpenReasoning-Nemotron-32B 81.0 0.1 58.6 41.4 0.0
Grok-4.1-Fast 85.1 1.4 90.4 9.6 0.0
Kimi-k1.6-IOI 80.2 7.7 81.3 18.7 0.0
XBai-o4-medium 80.1 8.5 89.1 10.9 0.0
Kimi-k1.6-IOI-high 86.0 10.7 87.2 12.8 0.0
QwQ-Max-Preview 80.0 12.5 89.8 10.2 0.0
Qwen3-235B-A22B 80.4 13.5 90.8 9.2 0.0
O4-Mini (High) 87.3 28.2 95.2 3.6 1.2
O4-Mini (Medium) 84.5 28.9 94.8 4.0 1.2
O3 (High) 84.7 32.4 48.1 25.0 26.8
O1-2024-12-17 (High) 83.2 50.1 81.7 3.6 14.6
Gemini-2.5-Pro-06-05 84.3 50.4 80.7 1.4 17.9
Gemini-2.5-Pro-05-06 82.8 53.6 89.4 9.3 1.3
Gemini-2.5-Pro-03-25 81.5 71.4 78.0 4.3 17.7
Table 10: Comment form across the 16 LCB models with pass@1≥80.0%, sorted bytok-cmt%.
```

<a id="talking-while-coding-054"></a>
## talking-while-coding-054 — Random-control comparisons and difficulty analysis

Source: [physical PDF page 18](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=18); reading unit `p018`, lines 19–44.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-053](#talking-while-coding-053), [talking-while-coding-055](#talking-while-coding-055)

```text
set (the same per-cell baseline convention as Ta-
ble 1). Random text damages pass@1 on all four
recipients (mean ∆=−17.9% across 12 cells), but
the damage is smaller than the wrong-topic dam-
age reported in Table 1 (mean ∆=−20.8% across
12 cells). We test this asymmetry directly with a
paired comparison between the wrong-topic and
random-text pass vectors on common problems, per
(recipient, source) cell with Holm correction over
12 cells, plus a pooled test. Pooled over 10,076
paired observations, 946 problems pass only under
random text versus 650 only under wrong-topic
(p<0.001). Per cell, 5 of 12 are individually Holm-
significant, all in the wrong-topic-worse direction,
and no cell reverses, though the per-cell effect is
heterogeneous.
D.6 Difficulty stratification:
per-prefix-recipient table
Table 15 reports the per-(recipient, source, condi-
tion) breakdown across LCB difficulty bands. Each
row’s∆ is computed against the matched-prompt
baseline on the corresponding (cell, difficulty) sub-
subset. Source-correct prefills lift pass@1 most
on medium problems for most (recipient, source)
pairs; wrong-topic and random-text damage con-
centrates on easy problems.
```

<a id="talking-while-coding-055"></a>
## talking-while-coding-055 — Flip-atlas definitions and counts

Source: [physical PDF page 18](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=18); reading unit `p018`, lines 45–58.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-054](#talking-while-coding-054), [talking-while-coding-056](#talking-while-coding-056)

```text
D.7 Per-problem flip atlas
The flip atlas is computed across the 4 prefix-
recipients under the source-correct (grok prefix-
source) condition vs the matched-prompt baseline,
on the 870-problem source-pass subset. Of these,
89 (10.2%) aresource-transferable(at least 3 of
the 4 prefix-recipients flip baseline-fail to source-
correct-pass, with 0 loss in the opposing direction),
3 (0.3%) aresource-toxic(at least 3 flip the other
way with 0 gain), and 778 ( 89.4%) are mixed or
neutral.
Difficulty distribution of source-transferable
problems.Among the 89 source-transferable
problems: 56 medium, 18 easy, 15 hard.
```

<a id="talking-while-coding-056"></a>
## talking-while-coding-056 — Qualitative transfer example and injected comments

Source: [physical PDF page 18](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=18); reading unit `p018`, lines 59–86.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-055](#talking-while-coding-055), [talking-while-coding-057](#talking-while-coding-057)

```text
D.8 Per-problem flip atlas: qualitative
anchors
Among the 119 problems where 6 or more of 12
voters lift unanimously (and no voter loses), the
prefix-source’s comment block typically reroutes
the prefix-recipient from a plausible-but-wrong
strategy to the correct one.
Example: LeetCode 3617 (easy, 12/12 voters lift).
Prefix-source: Gemini-3.1-Flash-Lite. Prefix-
recipient: Qwen3-8B.
The prefix-source’s comment block (injected as
prefix-recipient prefix) reads:
# The problem asks for the number of
possible original strings given that #
at most one character group could have
been typed with extra repetitions. #
1. Identify all contiguous groups of
identical characters. # 2. For each
group of length L>1, there are (L-1)
ways to have # extra characters in this
specific group. # 3. Total possibilities
= 1 (the word itself) + sum of (L_i - 1)
for all groups. # 4. This simplifies to:
1 + sum(L_i - 1) for all groups.
Without the prefix, Qwen3-8B’s baseline attempt
multipliesthe group counts (a plausible-looking but
incorrect approach derived from the structure of the
problem):
```

<a id="talking-while-coding-057"></a>
## talking-while-coding-057 — Table 11: form profile part 1

Source: [physical PDF page 19](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=19); reading unit `p019`, lines 1–45.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-056](#talking-while-coding-056), [talking-while-coding-058](#talking-while-coding-058)

```text
Model Source pass@1 tok-cmt% block% inline% doc%
O4-Mini (High) sub 87.3 28.2 95.2 3.6 1.2
Kimi-k1.6-IOI-high sub 86.0 10.7 87.2 12.8 0.0
Grok-4.1-Fast sr 85.1 1.4 90.4 9.6 0.0
O3 (High) sub 84.7 32.4 48.1 25.0 26.8
O4-Mini (Medium) sub 84.5 28.9 94.8 4.0 1.2
DeepSeek-R1-0528 sub 84.4 0.1 33.8 66.2 0.0
Gemini-2.5-Pro-06-05 sub 84.3 50.4 80.7 1.4 17.9
O1-2024-12-17 (High) sub 83.2 50.1 81.7 3.6 14.6
Gemini-2.5-Pro-05-06 sub 82.8 53.6 89.4 9.3 1.3
Gemini-2.5-Pro-03-25 sub 81.5 71.4 78.0 4.3 17.7
OpenReasoning-Nemotron-32B sub 81.0 0.1 58.6 41.4 0.0
EXAONE-4.0-32B sub 80.9 0.1 55.0 45.0 0.0
Qwen3-235B-A22B sub 80.4 13.5 90.8 9.2 0.0
Kimi-k1.6-IOI sub 80.2 7.7 81.3 18.7 0.0
XBai-o4-medium sub 80.1 8.5 89.1 10.9 0.0
QwQ-Max-Preview sub 80.0 12.5 89.8 10.2 0.0
Grok-3-Mini (High) sub 78.4 18.4 75.5 24.5 0.0
O1-2024-12-17 (Med) sub 78.3 56.8 76.7 3.0 20.3
DeepSeek-R1-Preview sub 77.9 8.4 85.8 13.7 0.5
Llama-3-1-Nemotron-Ultra-253B-v1 sub 77.7 4.6 92.0 8.0 0.0
O3-Mini-2025-01-31 (High) sub 77.7 45.4 94.4 5.5 0.2
O4-Mini (Low) sub 77.4 29.9 93.8 4.0 2.1
Gemini-2.5-Flash-05-20 sub 76.2 60.4 91.9 5.4 2.7
O1-2024-12-17 (Low) sub 75.9 58.5 82.4 2.6 14.9
O3-Mini-2025-01-31 (Med) sub 75.4 46.1 94.3 5.5 0.1
Gemini-2.5-Flash-04-17 sub 75.1 66.2 92.4 4.1 3.5
DeepCoder-14B-Preview sub 73.3 23.5 94.0 6.0 0.0
Gemini-3.1-Flash-Lite sr 72.5 39.5 97.1 0.3 2.7
O3-Mini-2025-01-31 (Low) sub 70.6 45.3 94.8 5.0 0.2
Claude-Opus-4 (Thinking) sub 70.4 20.6 90.4 8.7 0.8
GPT-OSS-120B sr 69.1 15.7 71.4 23.5 5.0
Claude-Sonnet-4 (Thinking) sub 68.5 15.9 85.8 13.3 0.9
O1-Mini-2024-09-12 sub 68.4 9.1 93.0 6.6 0.3
GPT-5.1-Codex-Mini sr 64.6 0.6 88.5 11.5 0.0
Llama-3-1-Nemotron-Nano-8B-v1 sub 64.4 3.9 96.4 3.6 0.0
DeepSeek-V3.2 sr 64.3 22.6 99.1 0.9 0.0
Claude-3.7-Sonnet sub 63.5 23.9 81.4 14.9 3.7
DeepSeek-R1-Lite-Preview sub 63.1 13.4 91.3 8.7 0.0
Claude-Opus-4 sub 62.4 26.8 93.0 5.9 1.1
QwQ-32B-Preview sub 59.9 12.5 89.4 10.4 0.2
Qwen3-235B-A22B sr 59.8 37.7 96.8 3.0 0.3
GPT-5.4-Nano sr 59.6 39.4 97.8 2.1 0.1
Table 11: Full per-model form profile on LCB (part 1 of 2: top 42 of 88 models, sorted by pass@1).sr= self-run
(10 OpenRouter + 4 vLLM);sub= LCB leaderboard submission. Form metrics defined in Appendix D.2.
```

<a id="talking-while-coding-058"></a>
## talking-while-coding-058 — Qualitative example: baseline and prefixed implementation

Source: [physical PDF page 19](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=19); reading unit `p019`, lines 46–64.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-057](#talking-while-coding-057), [talking-while-coding-059](#talking-while-coding-059)

```text
def possibleStringCount(self, word):
total = 1
. . . count consecutive groups. . .
total *= count # wrong: product, not
sum
return total
With the prefix, Qwen3-8B implements the
prefix-source’s stated formula (sum of group-
lengths minus 1, plus 1) and passes:
total = 1 + sum(g - 1 for g in groups)
The prefix-source’s prefix supplies a single
strategic decision – “it’s a sum, not a product” –
that the prefix-recipient was unable to find on its
own. Across the 119 strong-transferable problems,
this pattern repeats: the prefix-source’s correct algo-
rithmic choice is reflected verbatim into the prefix-
recipient’s solution, while the prefix-recipient ab-
sent prefix would commit to one of several mor-
phologically similar but incorrect strategies.
```

<a id="talking-while-coding-059"></a>
## talking-while-coding-059 — Full-grid significance results

Source: [physical PDF page 19](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=19); reading unit `p019`, lines 65–74.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-058](#talking-while-coding-058), [talking-while-coding-060](#talking-while-coding-060)

```text
D.9 McNemar+Holm-Bonferroni grid (full
statistics for Section 4.2)
Of the 126 (model, variant) non-baseline cells in
Table 4, 38 survive Holm–Bonferroni at α=0.05;
these are highlighted in Tables 4 and 16. The
strongest signals are:
•Gemma-4-E4B-IT none: ∆=−14.5%,
pholm = 2.3×10 −30
•GPT-OSS-120B inline: ∆=−13.9%, pholm =
2.1×10 −25
```

<a id="talking-while-coding-060"></a>
## talking-while-coding-060 — Significance and bootstrap details

Source: [physical PDF page 20](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=20); reading unit `p020`, lines 1–16.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-059](#talking-while-coding-059), [talking-while-coding-061](#talking-while-coding-061)

```text
•GPT-OSS-120B top: ∆=−13.7%, pholm =
9.3×10 −29
•GPT-5.4-Nano none: ∆=−13.6%, pholm =
4.3×10 −20
•GPT-OSS-120B mix: ∆=+7.2%, pholm =
2.3×10 −6
Paired-bootstrap 95% confidence intervals
(Efron, 1979) (1000 resamples on problem ID)
have median width 4.4%. All cells with |∆| ≥6%
survive Holm correction.
D.10 Self-elicit grid: per-model dramatic-cell
audit
Table 16 reports the full 14-row per-model audit
with baseline form profile, the largest- and smallest-
∆ variant per model (bold where Holm-significant),
and significant-cell count per model.
```

<a id="talking-while-coding-061"></a>
## talking-while-coding-061 — Variant compliance, exceptions and output length

Source: [physical PDF page 20](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=20); reading unit `p020`, lines 17–58.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-060](#talking-while-coding-060), [talking-while-coding-062](#talking-while-coding-062)

```text
D.11 Self-elicit grid: variant compliance
details
Table 17 reports per-variant mean output code to-
kens and mean tok-cmt% aggregated across the 14
models (column means of Table 18). Models reli-
ably follow the form instruction at the population
level (nonedrops mean tok-cmt% from 22.7% to
6.3%;dense,WHY,mix,top,inlineall push it
above 50%), yet the pass@1 effect is decoupled
from compliance (Section 4.2).
D.12 Per-cell mean code tokens and tok-cmt%
Table 18 reports the per-cell mean output code to-
kens and tok-cmt% across the 14 ×10 self-elicit
grid; this is the per-(model, variant) detail behind
the per-variant aggregates in Table 17.
Two patterns stand out. First, form policies are
followed in aggregate:nonepushes tok-cmt% be-
low 10% on 12 of 14 models (Qwen3-235B at
26.6% and MiMo-V2-Flash at 24.6% remain par-
tially compliant), anddense,WHY, andmixpush
tok-cmt% above 40% on 13 of 14 models (one
model exception per variant: Seed-Coder-8B under
denseat 37.2%, Llama-4-Maverick underWHY
at 34.4% and undermixat 26.0%). Second, the
token shift undernoneis highly model-dependent:
mean output code tokens shift by an average of
−21.8% across the 14 models, with the range span-
ning Gemma-4-E4B-IT contracting from 1067 to
437 tokens (−59%) up to MiMo-V2-Flashexpand-
ingfrom 1119 to 1628 tokens ( +46%) — the only
model whose mean tokens grow undernone, be-
cause the lost comment scaffolding lets the model
fail to stop on its longest tail of generations. The
verbose form variants (top,dense,inline) inflate
mean tokens to 0.7–2.6× thebasevalue, peaking
at Mistral-Small-2603 undertop(365 to 953, 2.6×)
and DeepSeek-V3.2 undertop(603 to 1094, 1.8×);
the lower end comes from MiMo-V2-Flash under
inline(1119 to 767, 0.7×). These shifts describe
how strictly each model complies with theformof
the prompt; they do not predict the corresponding
pass@1 effect (Section 4.2).
```

<a id="talking-while-coding-062"></a>
## talking-while-coding-062 — Output-token shift definition

Source: [physical PDF page 20](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=20); reading unit `p020`, lines 59–66.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Related: [talking-while-coding-061](#talking-while-coding-061), [talking-while-coding-063](#talking-while-coding-063)

```text
D.13 Per-model output token shift under none
Table 19 reports the per-model mean output code
token count underbaseandnone, measured un-
der a sharedcl100k_base tokenizer over all 1055
LCB problems. The token shift is asymmetric: 13
of 14 models contract undernone(largest drop:
Gemma-4-E4B-IT, −59%), but MiMo-V2-Flash
actuallyexpandsby+46%.
```

<a id="talking-while-coding-063"></a>
## talking-while-coding-063 — Table 12: form profile part 2

Source: [physical PDF page 21](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=21); reading unit `p021`, lines 1–48.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-062](#talking-while-coding-062), [talking-while-coding-064](#talking-while-coding-064)

```text
Model Source pass@1 tok-cmt% block% inline% doc%
Claude-Sonnet-4 sub 59.4 24.6 88.7 10.6 0.7
gpt-4.1-mini-2025-04-14 sub 58.9 50.2 98.4 1.6 0.0
Gemini-Flash-2.0-Thinking-12-19 sub 56.5 30.2 90.2 5.5 4.3
MiMo-V2-Flash sr 55.9 36.3 99.5 0.4 0.1
gpt-oss-20b sub 55.7 20.8 59.4 13.0 27.6
Gemini-Flash-2.0-Thinking-01-21 sub 55.7 30.3 90.1 6.3 3.6
O1-Preview-2024-09-12 sub 55.6 12.4 78.8 21.2 0.0
MetaStone-L1-7B sub 54.1 7.0 87.3 12.7 0.0
Gemma-4-E4B-IT sr 53.7 58.6 96.5 0.8 2.8
gemini-2.5-flash-lite sub 51.3 38.4 96.2 3.6 0.2
Gemini-Flash-2.0-Thinking sub 51.2 3.0 76.4 23.1 0.5
DeepSeek-V3 sub 51.0 31.0 98.5 1.5 0.0
Gemini-Exp-1206 sub 50.0 0.1 71.9 28.1 0.0
Qwen2.5-Ins-72B sub 49.1 8.8 94.9 5.1 0.0
Claude-3.5-Sonnet-20241022 sub 48.7 20.3 93.4 6.5 0.1
Qwen2.5-Coder-Ins-32B sub 48.3 9.4 96.1 3.9 0.0
Claude-3.5-Sonnet-20240620 sub 48.0 7.7 89.7 10.3 0.0
Qwen2.5-Ins-32B sub 47.1 6.7 93.7 6.3 0.0
Llama-4-Maverick sr 45.3 11.3 86.5 5.0 8.5
Mistral-Small-2603 sr 44.2 16.9 98.7 1.3 0.0
GPT-4O-2024-05-13 sub 43.4 12.3 95.3 4.7 0.0
Gemini-Pro-1.5-002 sub 42.1 1.5 95.1 4.9 0.0
Gemini-Flash-2.0-Exp sub 41.8 1.3 90.0 7.5 2.5
Qwen3-Coder-30B-A3B-Instruct sub 38.5 27.5 92.2 6.9 0.8
GPT-4O-2024-08-06 sub 38.3 21.5 95.5 4.3 0.1
GPT-4-Turbo-1106 sub 37.4 26.0 97.5 2.5 0.0
GPT-4-Turbo-2024-04-09 sub 37.3 25.8 93.7 5.9 0.4
Mistral-Large sub 37.3 12.6 96.9 3.1 0.0
Qwen3-8B sr 37.0 12.5 99.4 0.6 0.0
LLama3.3-70b-Ins sub 36.8 26.1 70.2 1.0 28.8
Gemini-Flash-1.5-002 sub 36.1 2.1 85.1 14.9 0.0
GPT-4O-mini-2024-07-18 sub 35.5 21.6 84.9 14.9 0.2
Codestral-Latest sub 35.3 14.0 97.6 2.4 0.0
Qwen2.5-Coder-Ins-7B sub 34.1 8.6 98.7 1.3 0.0
GPT-4-0613 sub 33.9 0.9 94.8 5.2 0.0
Seed-Coder-8B-Instruct sr 33.4 13.2 96.4 3.6 0.0
Qwen2-Ins-72B sub 30.6 4.5 87.4 4.4 8.2
Qwen2.5-Ins-7B sub 30.1 5.4 98.9 1.1 0.0
DSCoder-33b-Ins sub 26.7 5.2 99.9 0.1 0.0
DeepSeek-Coder-V2-Lite-Instruct sub 25.2 9.5 96.8 3.2 0.0
GLM-4.7-Flash sub 24.8 21.2 95.0 5.0 0.0
Claude-3-Haiku sub 22.5 14.5 95.3 1.2 3.5
CodeGeeX4-All-9B sr 22.1 11.8 98.2 1.8 0.0
AzeroGPT-64b sub 22.0 8.0 70.8 10.7 18.6
DSCoder-6.7b-Ins sub 19.8 7.4 98.9 1.1 0.0
DSCoder-1.3b-Ins sub 8.6 5.4 100.0 0.0 0.0
Table 12: Full per-model form profile on LCB (part 2 of 2: remaining 46 models). Continuation of Table 11.
```

<a id="talking-while-coding-064"></a>
## talking-while-coding-064 — Table 13: within-model correlations

Source: [physical PDF page 21](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=21); reading unit `p021`, lines 49–56.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-063](#talking-while-coding-063), [talking-while-coding-065](#talking-while-coding-065)

```text
Form axis MedianρMax|ρ|%|ρ|>0.20
tok-cmt%−0.05 0.53 22%
block%−0.06 0.31 13%
inline%−0.08 0.32 6%
doc%−0.01 0.24 4%
Table 13: Within-model Spearmanρ between each form metric and per-problem pass status, computed independently
for each of the 88 models. Max |ρ| and threshold-crossing fractions bound the share of models with non-trivial
within-model variation.
```

<a id="talking-while-coding-065"></a>
## talking-while-coding-065 — Table 14: length-matched random text

Source: [physical PDF page 22](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=22); reading unit `p022`, lines 1–22.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-064](#talking-while-coding-064), [talking-while-coding-066](#talking-while-coding-066)

```text
Recipient Source Random pass@1∆vs baseline
Gemma-4-E4B-IT
gemini51.4−19.9 ∗
claude45.3−17.4 ∗
grok42.8−21.0 ∗
Qwen3-8B
gemini23.8−29.9 ∗
claude35.7−10.2 ∗
grok20.5−26.6 ∗
Seed-Coder-8B
gemini27.1−16.8 ∗
claude27.1−10.9 ∗
grok23.3−15.4 ∗
CodeGeeX4-9B
gemini6.5−19.9 ∗
claude12.2−10.5 ∗
grok6.2−16.8 ∗
mean∆across 12 cells−17.9
Table 14: Length-matched random-text control across 12 (recipient, source) cells. The prefix is #-prefixed filler
matched in length to each source-written block. ∆ is against the recipient’s matched-prompt baseline on the same
per-cell subset. ∗ = Holm-significant against the baseline at pholm<0.001 (paired McNemar, m=12 within this
control family).
```

<a id="talking-while-coding-066"></a>
## talking-while-coding-066 — Table 15: difficulty-stratified deltas

Source: [physical PDF page 23](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=23); reading unit `p023`, lines 1–51.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-065](#talking-while-coding-065), [talking-while-coding-067](#talking-while-coding-067)

```text
Recipient Source Condition Easy∆Medium∆Hard∆
Gemma-4-E4B-IT gemini source-correct+2.5 +22.7+20.3
Gemma-4-E4B-IT gemini shuffled−6.0 +13.2+11.6
Gemma-4-E4B-IT gemini wrong-topic−32.7−19.7−17.4
Gemma-4-E4B-IT gemini random-text−27.9−12.8−17.4
Gemma-4-E4B-IT claude source-correct−3.8 +13.3 +17.5
Gemma-4-E4B-IT claude shuffled−5.3 +11.6+8.3
Gemma-4-E4B-IT claude wrong-topic−30.4−19.4−16.2
Gemma-4-E4B-IT claude random-text−23.8−15.1−11.8
Gemma-4-E4B-IT grok source-correct+2.8 +25.3+18.9
Gemma-4-E4B-IT grok shuffled+0.0 +19.0+11.2
Gemma-4-E4B-IT grok wrong-topic−22.2−14.7−15.0
Gemma-4-E4B-IT grok random-text−33.9−14.4−12.6
Qwen3-8B gemini source-correct+12.1 +24.0+13.8
Qwen3-8B gemini shuffled+8.3 +19.7+13.0
Qwen3-8B gemini wrong-topic−52.1−24.3−14.5
Qwen3-8B gemini random-text−43.2−22.4−15.9
Qwen3-8B claude source-correct+9.1 +20.3+14.0
Qwen3-8B claude shuffled+7.2 +19.1+10.1
Qwen3-8B claude wrong-topic−39.8−18.8−10.1
Qwen3-8B claude random-text−11.0−10.1−9.2
Qwen3-8B grok source-correct+14.2 +31.9+19.4
Qwen3-8B grok shuffled+6.6 +25.3+17.0
Qwen3-8B grok wrong-topic−50.0−21.0−10.2
Qwen3-8B grok random-text−46.5−17.8−10.7
Seed-Coder-8B gemini source-correct+10.2 +20.7+10.1
Seed-Coder-8B gemini shuffled+2.2 +17.8+6.5
Seed-Coder-8B gemini wrong-topic−33.3−7.2−4.3
Seed-Coder-8B gemini random-text−35.9−3.9−1.4
Seed-Coder-8B claude source-correct+11.0 +18.0+7.5
Seed-Coder-8B claude shuffled+7.5 +16.2+5.3
Seed-Coder-8B claude wrong-topic−32.0−8.1−3.1
Seed-Coder-8B claude random-text−23.2−4.3−3.5
Seed-Coder-8B grok source-correct+17.4 +22.7+11.7
Seed-Coder-8B grok shuffled+4.7 +16.7+7.3
Seed-Coder-8B grok wrong-topic−26.9−11.5−3.9
Seed-Coder-8B grok random-text−35.1−4.6−3.4
CodeGeeX4-9B gemini source-correct+27.3 +33.2+6.5
CodeGeeX4-9B gemini shuffled+17.8 +24.7+9.4
CodeGeeX4-9B gemini wrong-topic−38.7−3.6−2.2
CodeGeeX4-9B gemini random-text−41.0−6.2−2.2
CodeGeeX4-9B claude source-correct+19.4 +24.6+8.8
CodeGeeX4-9B claude shuffled+17.9 +21.7+5.7
CodeGeeX4-9B claude wrong-topic−39.2−4.9−1.3
CodeGeeX4-9B claude random-text−23.5−4.6−1.3
CodeGeeX4-9B grok source-correct+25.9 +29.9+10.2
CodeGeeX4-9B grok shuffled+6.6 +23.0+5.8
CodeGeeX4-9B grok wrong-topic−34.8−6.3−0.5
CodeGeeX4-9B grok random-text−40.2−4.9−1.0
Table 15: ∆ pass@1 (%) against the recipient’s matched-prompt baseline on the source-pass subset, stratified by
LCB difficulty band. Recipients sorted by base pass@1 descending.Bold= largest-magnitude band per row.
```

<a id="talking-while-coding-067"></a>
## talking-while-coding-067 — Table 16: per-model prompt extremes

Source: [physical PDF page 24](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=24); reading unit `p024`, lines 1–17.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together. Table 16 last numeric fields and Table 17 none row have concatenated values in pinned text; original column layout governs.

Related: [talking-while-coding-066](#talking-while-coding-066), [talking-while-coding-068](#talking-while-coding-068)

```text
Model (base %) Best (variant,∆%) Worst (variant,∆%) #sig
Grok-4.1-Fast (85.1) inline−0.3WHY−4.11
Gemini-3.1-Flash-Lite (72.5) inline+0.2none−6.93
GPT-OSS-120B (69.1)mix+7.2inline−13.95
GPT-5.1-Codex-Mini (64.6)WHAT+4.9top−13.56
DeepSeek-V3.2 (64.3)top+6.2none−6.14
Qwen3-235B (59.8)WHY+5.7none−1.51
GPT-5.4-Nano (59.6)dense+5.8none−13.63
MiMo-V2-Flash (55.9)WHY+7.2top−9.03
Gemma-4-E4B-IT (53.7) top+0.5none−14.55
Llama-4-Maverick (45.3) inline+0.3WHAT−12.73
Mistral-Small (44.2)dense+4.4none−1.71
Qwen3-8B (37.0)dense+4.4none−1.61
Seed-Coder-8B (33.4) inline+2.8dense−3.90
CodeGeeX4-9B (22.1) inline−0.6WHY−5.02
Table 16: Per-model dramatic-cell audit, sorted bybasepass@1 descending. #sig: Holm-significant cells per model
(global Holm overm=126, Table 4).Bold∆= Holm-significant.
```

<a id="talking-while-coding-068"></a>
## talking-while-coding-068 — Table 17: mean tokens and comment proportion

Source: [physical PDF page 24](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=24); reading unit `p024`, lines 18–31.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together. Table 16 last numeric fields and Table 17 none row have concatenated values in pinned text; original column layout governs.

Related: [talking-while-coding-067](#talking-while-coding-067), [talking-while-coding-069](#talking-while-coding-069)

```text
Variant Mean tokens Mean tok-cmt%
base 463 22.7
none3686.3
rare 411 14.9
dense 740 55.4
WHAT 566 49.6
WHY 658 54.6
mix 685 55.6
gp-doc 594 45.5
top 655 57.3
inline 604 56.7
Table 17: Per-variant mean output code tokens and tok-cmt%, averaged across the 14 models in the self-elicit grid
(column means of Table 18). Models reliably comply with surface form instructions, but compliance does not track
pass@1 effect (Section 4.2).
```

<a id="talking-while-coding-069"></a>
## talking-while-coding-069 — Table 18: full token/comment grid

Source: [physical PDF page 24](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=24); reading unit `p024`, lines 32–49.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together. Table 16 last numeric fields and Table 17 none row have concatenated values in pinned text; original column layout governs.

Related: [talking-while-coding-068](#talking-while-coding-068), [talking-while-coding-070](#talking-while-coding-070)

```text
Model base none rare dense WHAT WHY mix gp-doc top inline
Grok-4.1-Fast 277/1.4 267/0.3 269/0.6 479/46.6 399/43.5 510/57.8 524/57.2 295/16.9 456/51.5 383/36.3
Gemini-3.1-Flash-Lite 440/39.5 235/0.1 255/18.8 541/59.9 441/51.6 556/61.3 575/62.7 458/52.3 629/66.0 581/61.6
GPT-OSS-120B 224/15.7 183/1.4 195/6.5 372/52.3 352/38.7 381/44.7 416/48.4 400/48.0 437/64.7 388/54.6
GPT-5.1-Codex-Mini 154/0.6 130/0.1 138/0.2 286/55.8 383/53.7 353/50.6 393/53.5 249/31.4 259/44.5 310/52.9
DeepSeek-V3.2 603/22.6 269/0.1 239/5.9 929/56.0 671/44.2 803/49.6 826/53.1 796/49.0 1094/77.6 1022/72.8
Qwen3-235B-A22B 495/37.7 429/26.6 384/27.2 811/64.1 821/55.4 637/48.8 923/57.6 747/52.1 1057/56.8 778/65.3
GPT-5.4-Nano 679/39.4 486/9.4 613/29.9 843/64.5 821/56.8 862/60.4 916/62.7 802/51.9 776/64.5 839/63.9
MiMo-V2-Flash 1119/36.3 1628/24.6 1864/28.2 2722/66.7 1168/58.0 1582/69.1 1309/65.8 1400/59.2 992/59.3 767/61.7
Gemma-4-E4B-IT 1067/58.6 437/7.3 668/42.0 1222/73.2 1003/68.2 1181/72.2 1218/72.5 986/65.2 1246/71.7 1168/71.9
Llama-4-Maverick 239/11.3 193/0.6 222/12.9 365/46.8 316/38.4 318/34.4 286/26.0 278/28.2 228/15.3 405/52.3
Mistral-Small-2603 365/16.9 207/0.3 210/2.6 657/60.4 574/55.3 772/65.9 979/65.2 704/56.0 953/76.6 740/66.1
Qwen3-8B 399/12.5 347/6.4 309/9.9 642/51.1 465/48.1 669/57.3 659/60.0 665/53.5 474/50.7 584/49.8
Seed-Coder-8B 207/13.2 170/3.5 190/8.9 225/37.2 224/37.2 294/46.7 280/46.2 259/33.0 298/52.9 233/39.0
CodeGeeX4-9B 210/11.8 176/7.1 202/14.7 265/40.6 279/44.7 296/46.0 282/47.4 276/40.0 270/50.4 265/45.8
Table 18: Per-cell mean output code tokens and tok-cmt% across the 14×10 self-elicit grid (Section 4.2), sorted by
basepass@1 descending. Each cell shows tok/cmt%: mean output code tokens under cl100k_base, and the mean
fraction of those tokens that fall inside a comment.
```

<a id="talking-while-coding-070"></a>
## talking-while-coding-070 — Table 19: token shift and pass significance

Source: [physical PDF page 25](../../../ai-code-comments/2026-talking-to-itself-while-coding.pdf#page=25); reading unit `p025`, lines 1–18.

Attribution: Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo and Xiaoning Du

Context: Main paper and appendices in physical-page order. Neighboring records preserve cross-page context; all percentages/deltas and significance conventions retain the source?s wording.

Transcription/context notes: Tables/notation visually inspected where present; base extraction flattens column alignment, bold emphasis and superscripts. Read headers/captions and linked baseline/metric definitions together.

Related: [talking-while-coding-069](#talking-while-coding-069)

```text
Model base none shift % pass sig?
Grok-4.1-Fast 277 267−3.6–
Gemini-3.1-Flash-Lite 441 235−46.5✓
GPT-OSS-120B 225 183−18.4✓
GPT-5.1-Codex-Mini 154 130−15.9–
DeepSeek-V3.2 603 269−55.4✓
Qwen3-235B-A22B 495 429−13.3–
GPT-5.4-Nano 679 486−28.4✓
MiMo-V2-Flash 1119 1628+45.5–
Gemma-4-E4B-IT 1067 437−59.0✓
Llama-4-Maverick 239 193−19.5–
Mistral-Small-2603 365 207−43.2–
Qwen3-8B 399 347−13.2–
Seed-Coder-8B 207 170−17.6–
CodeGeeX4-9B 210 177−15.9–
Table 19: Per-model mean output code tokens underbasevsnone, sorted by base pass@1 descending. Tokens
count code only (markdown fences, surrounding explanation, and<think> tags excluded). The pass-sig column
marks whethernone’s pass@1 effect survives Holm-Bonferroni in Appendix D.10.
```
