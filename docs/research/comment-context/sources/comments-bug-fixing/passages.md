# On the Impact of Code Comments for Automated Bug-Fixing: An Empirical Study: source passages

Generated from records.json and the pinned reading text. No ranking or recommendation is implied.

Extent: `local_paper`. Text SHA-256: `903f616c0dc3e38ceefc5a8df9ddb6c6ee786ce8ea7ec1275b587d8aa7241bee`.

[Selections](records.json) · [Coverage and gaps](coverage.json) · [Collection index](../../README.md)

- Figures 1, 2, 4 and 5 now have supplemental visual transcriptions. Source screenshot clipping and ellipses remain explicit; original figure owns indentation and highlighting.
- A code-versus-prose category-label discrepancy is preserved in Figure 5 supplement notes; no author intent inferred.

<a id="comments-bug-fixing-001"></a>
## comments-bug-fixing-001 — Abstract

Source: [physical PDF page 1](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=1); reading unit `p001`, lines 19–41.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-002](#comments-bug-fixing-002)

```text
Abstract
Large Language Models (LLMs) are increasingly relevant in Soft-
ware Engineering research and practice, with Automated Bug Fixing
(ABF) being one of their key applications. ABF involves transform-
ing abuggymethod into itsfixedequivalent. A common preprocess-
ing step in ABF involves removing comments from code prior to
training. However, we hypothesize that comments may play a criti-
cal role in fixing certain types of bugs by providing valuable design
and implementation insights. In this study, we investigate how the
presence or absence of comments, both during training and at infer-
ence time, impacts the bug-fixing capabilities of LLMs. We conduct
an empirical evaluation comparing two model families, each evalu-
ated under all combinations of training and inference conditions
(withandwithoutcomments), and thereby revisiting the common
practice of removing comments during training. To address the
limited availability of comments in state-of-the-art datasets, we use
an LLM to automatically generate comments for methods lacking
them. Our findings show that comments improve ABF accuracy by
up to threefold when present in both phases, while training with
comments does not degrade performance when instances lack them.
Additionally, an interpretability analysis identifies that comments
detailing method implementation are particularly effective in aiding
LLMs to fix bugs accurately.
```

<a id="comments-bug-fixing-002"></a>
## comments-bug-fixing-002 — Introduction: ABF context and comments

Source: [physical PDF page 1](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=1); reading unit `p001`, lines 46–89.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto; named/cited studies and the Chen et al. taxonomy remain third-party work reported by these authors

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-001](#comments-bug-fixing-001), [comments-bug-fixing-003](#comments-bug-fixing-003)

```text
1 Introduction
Large Language Models (LLMs), are increasingly becoming indis-
pensable tools for assisting software developers in their daily tasks.
These models enable the automation of a wide range of activi-
ties. Furthermore, developers can easily leverage advanced LLM-
powered tools, such as GitHub Copilot, which are seamlessly inte-
grated into modern Integrated Development Environments (IDEs)
to enhance productivity and streamline workflows.
Among these applications, Automated Bug Fixing (ABF) has
emerged as one of the most researched and impactful coding tasks
[5, 10, 26, 34, 39, 56, 68]. ABF involves identifying and resolving
bugs within a method (e.g.,a scenario where a test case fails). While
the concept may seem straightforward, ABF holds significant value
for developers, as bug fixing is notoriously challenging and often
demands considerable effort [15, 46]. By alleviating this burden,
ABF has the potential to substantially enhance developer efficiency
and reduce the time spent on error resolution.
Early research on using deep learning (DL) and LLMs for ABF
established the foundation for the field. Tufanoet al.[ 56] presented
one of the first DL-based approaches to automatically fix bugs,
quickly followed by several others [10, 34, 68]. A key contribution
of the work by Tufanoet al.[ 56] was the release of a benchmark
dataset, which remains a standard for training and evaluating ABF
models [3, 8, 14, 19, 23, 24, 39, 63, 65]. Such a dataset, mined from
GitHub, contains couples of buggy Java methods and their respec-
tive fixed versions. Given the limitations of the specific ML model
they adopted (Recurrent Neural Networks — RNNs), they needed
to pre-process the source code of the methods so that identifiers
are abstracted (i.e.,they appear like IDi, where i is an incremental
number) and comments are removed.
However, code comments may not only be important [61], but
often essential for fixing bugs. Comments, indeed, might contain
precious information about the requirements, which are sometimes
necessary to understand what is wrong with the code and, thus to
fix it. Let us consider the example in Fig. 1. The buggy code lacks
mNearbyDeviceAdapter.notifyDataSetChanged(). Such an in-
struction notifies the dataset change to the nearby devices. Without
reading the comment and understanding this requirement, neither
a human developer nor a model could identify or fix the bug.
Unlike the RNNs employed by Tufanoet al.[ 56], modern LLMs
are well-equipped to process code comments. Despite this capability,
prior research has overlooked the potential value of incorporat-
ing comments—a potentially critical source of information—for
Automated Bug Fixing (ABF).
```

<a id="comments-bug-fixing-003"></a>
## comments-bug-fixing-003 — Dataset and study overview

Source: [physical PDF page 1](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=1); reading unit `p001`, lines 90–98.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-002](#comments-bug-fixing-002), [comments-bug-fixing-004](#comments-bug-fixing-004)

```text
In this work, we investigate how the presence or absence of code
comments, both during training and at inference time, impacts on
the bug-fixing capabilities of Large Language Models (LLMs). First,
we build a new dataset for ABF based on the one introduced by
Tufanoet al.[ 56]. To do this, we consider the same repositories
and commits, but we re-extract the instances by considering the
raw source code (i.e.,we do not abstract identifiers and keep the
original comments). Differently from the previous work, which only
consideredsmall- ( ≤ 50 tokens) andmedium-sized ( ≤ 100 tokens)
```

<a id="comments-bug-fixing-004"></a>
## comments-bug-fixing-004 — Figure 1 and generated-comment setup

Source: [physical PDF page 2](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=2); reading unit `p002`, lines 2–18.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Figure code/comment specimens are image-only in the original and absent from pinned base text; physical page visually inspected. Supplemental transcription is being supplied separately for coordinator integration.

Related: [comments-bug-fixing-003](#comments-bug-fixing-003), [comments-bug-fixing-005](#comments-bug-fixing-005)

```text
Figure 1: Example of a buggy method and its fixed version
(the green line is the fix, which was missing in the buggy
version).
methods in two distinct datasets, we merge them in a single dataset,
in which we also includebigmethods (≤512 tokens).
We noticed, however, that only a minority of the code instances in
our dataset contained comments (< 20%) and that many of them are
low quality (e.g.,“// Argh!!! This method is WRONG !”). For this
reason, we use an automated procedure to generate higher-quality
comments needed in our experiment. Considering the taxonomy
of code comments introduced by Zhaiet al.[ 69], we use an LLM to
generate five comments, documentingwhatthe method does,how
it does it, the intendedusageof the method, the reasonwhythe
method is there, andpropertiesof the method (e.g.,pre-conditions
and post-conditions). We do this on the fixed version rather than on
the buggy one to simulate the ideal scenario in which developers
properly document the methods they develop.
```

<a id="comments-bug-fixing-005"></a>
## comments-bug-fixing-005 — Experiment and interpretability overview

Source: [physical PDF page 2](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=2); reading unit `p002`, lines 19–56.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-004](#comments-bug-fixing-004), [comments-bug-fixing-006](#comments-bug-fixing-006)

```text
To evaluate our hypothesis that code comments play a crucial
role in Automated Bug Fixing (ABF), we designed a controlled ex-
periment manipulating the presence of comments both during train-
ing and inference. We fine-tuned two types of models—CodeT5+
[64] and DeepSeek-Coder [ 20]—under all combinations of these
conditions (withvs.withoutcomments). For the training phase,
comments were either removed from or automatically generated
for each instance, while at inference time the models were tested
on inputs with or without comments accordingly.
When comparing the four training-inference combinations, we
found that models benefit from comments in both phases. Com-
ments provided only at inference time already lead to noticeable
improvements, while training with comments does not harm perfor-
mance on instances lacking comments. The greatest improvements
occur when comments are present in both phases, increasing ac-
curacy by up to threefold. These results demonstrate that code
comments can substantially enhance models performance, under-
scoring their importance in ABF tasks.
To gain deeper insights into the impact of the five categories of
comments on model performance, we conducted an interpretabil-
ity study based on SHAP [33], employing the GradientExplainer
method. This method assigns an importance score to each input
token with respect to every token generated during the inference of
a single generation. Our analysis revealed that the most influential
category of comments were those documentinghowthe method
achieves its goal.
Interestingly, the importance of other comment categories varied
between the two models. For one model,i.e.,CodeT5+, comments
describingwhatthe method does were the least important, likely
because they provide high-level information that is often redun-
dant (e.g.,already conveyed by the method name). For the other
model,i.e.,DeepSeek-Coder, the lowest importance was attributed
to comments describing the method’susageand itsproperties.
In summary, our findings reinforce a recurring theme in Software
Engineering research:Developers should document their code not
only for themselves and future collaborators but also to enable LLMs
to provide better assistance.
All code and data used in our study is publicly available [1].
```

<a id="comments-bug-fixing-006"></a>
## comments-bug-fixing-006 — Background: coding models

Source: [physical PDF page 2](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=2); reading unit `p002`, lines 57–95.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto; named/cited studies and the Chen et al. taxonomy remain third-party work reported by these authors

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-005](#comments-bug-fixing-005), [comments-bug-fixing-007](#comments-bug-fixing-007), [comments-bug-fixing-042](#comments-bug-fixing-042)

```text
2 Background and Related Work
We first present some background on Machine Learning (ML) for
coding tasks, with specific focus on the Automated Bug Fixing
(ABF) task. Then, we present some related works.
2.1 ML for Coding Tasks
Software Engineering ML tasks are typical software engineering
activities that can be supported by Machine Learning. Among these,
Coding ML Tasks (or simply Coding Tasks) concern source code.
They may involve code classification (e.g.,vulnerability detection),
regression (e.g.,bug-fix time prediction), or code generation (e.g.,
automated bug fixing). We focus on the latter, which includes code
summarization [2, 21, 29, 36], code completion [11, 54], and auto-
mated bug fixing [10, 56]. While several approaches tried to repre-
sent source code as trees (e.g.,AST) or graphs (e.g.,CFG) to devise
ML-approaches able to perform specific tasks, most models simply
represent source code as text. Thus, neural networks used in Natural
Language Processing (NLP) tasks found their way into the SE com-
munity. The first approaches defined to tackle coding tasks were
based on Recurrent Neural Networks (RNNs). RNNs are designed to
process sequential data through recurrent connections that allow
information to persist across sequence steps. Their basic input unit
is thetoken, which represents a word, subword, or character, de-
pending on the tokenizer used to convert text into token sequences.
Since RNNs handle numeric vectors, tokens are transformed into
vector representations through anembeddingstep.
The Transformer architecture [60] constituted a revolution in
this field. Such an architecture has been adopted both for NLP [50]
and coding tasks [37, 39, 65]. The Transformer architecture relies
on a self-attention mechanism to capture long-range dependencies
among tokens. Unlike RNNs, which process tokens sequentially,
this architecture can handle longer context windows (i.e.,larger
amounts of tokens) efficiently given its parallel tokens processing.
While the definition ofLarge Language Model(LLMs) is fuzzy,
most use such a term to refer to any artificial neural network that
relies on the Transformer architecture [60] to perform a specific
task. Thus, we use such a term with this meaning from now on.
LLMs work in two steps:pre-trainingandfine-tuning. In the
pre-trainingstep, the model is trained to perform a self-supervised
task (e.g.,predicting the next token in a sequence). This allows
```

<a id="comments-bug-fixing-042"></a>
## comments-bug-fixing-042 — Figure 1: buggy method and added fix (visual transcription)

Source: [physical PDF page 2](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=2); reading unit `p002`, lines 97–108.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Manual visual transcription from original PDF physical page 2, pypdfium2 scale 2.6 render. Supplemental reading text appended after the extracted page text; consult the original figure for layout.

Transcription/context notes: Editor line numbers/UI omitted; indentation approximated from image. The notifyDataSetChanged line is green with a + marker: it is absent in the buggy version and present in the fix.

Related: [comments-bug-fixing-006](#comments-bug-fixing-006)

```text
/*
 * Empties the PWO metadata queue and notifies the dataset
 * change to the nearby devices.
 */
private void emptyPwoMetadataQueue() {
    Collections.sort(mPwoMetadataQueue);
    for (PwoMetadata pwoMetadata : mPwoMetadataQueue) {
        mNearbyDeviceAdapter.addItem(pwoMetadata);
    }
    mPwoMetadataQueue.clear();
    mNearbyDeviceAdapter.notifyDataSetChanged();
}
```

<a id="comments-bug-fixing-007"></a>
## comments-bug-fixing-007 — Pretraining, fine-tuning and studied model families

Source: [physical PDF page 3](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=3); reading unit `p003`, lines 2–17.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto; named/cited studies and the Chen et al. taxonomy remain third-party work reported by these authors

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-006](#comments-bug-fixing-006), [comments-bug-fixing-008](#comments-bug-fixing-008)

```text
the model to learn the language(s) that it must treat. In thefine-
tuningstep, instead, the model is trained to perform a specific
task (e.g.,to transform a given input sequence to a given output
sequence). For example, for the ABF task on which we focus in
this paper, the input sequence represent abuggymethod, while the
output sequence is thefixedversion of the same method. Since 2021,
several LLMs specialized in source code have emerged [37, 39, 64,
65]. Among them, CodeT5+ [64] extends the T5 architecture [50].
It is pre-trained on nine programming languages using multiple
code-oriented objectives, includingspan denoising, andcausal LM,
and is available in sizes from 220M to 16B parameters. DeepSeek-
Coder [20], instead, is trained from scratch on 2T tokens across
87 languages, building on the Llama architecture [55]. It employs
next-token predictionandfill-in-the-middlepre-training objectives,
and is available in base and instruction-tuned variants ranging from
1.3B to 33B parameters.
```

<a id="comments-bug-fixing-008"></a>
## comments-bug-fixing-008 — Related work: automated bug fixing

Source: [physical PDF page 3](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=3); reading unit `p003`, lines 18–49.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto; named/cited studies and the Chen et al. taxonomy remain third-party work reported by these authors

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-007](#comments-bug-fixing-007), [comments-bug-fixing-009](#comments-bug-fixing-009)

```text
2.2 Automated Bug Fixing
One of the first studies regarding the use of DL to fix bugs is the one
by Tufanoet al.[ 56]. The authors use a Neural-Machine-Translation
(NMT) approach to address ABF. They found that it was able to fix
between 9% and 50% of the bugs from their dataset.
Lutellieret al.[ 34] proposedCoCoNuT, a program repair tech-
nique combining ensemble learning and context-aware NMT. The
method uses convolutional neural networks (CNNs) to encode
buggy code and context independently, enhancing accuracy and
capturing a wide range of strategies.CoCoNuTwas observed to
outperform 27 strategies in four languages, fixing 509 bugs (309 of
which were unique).
Previous work mostly rely on word-level tokenizers that split
the input/output text into tokens based on words defined from a
given vocabulary. Therefore, they inherently suffer from the out-
of-vocabulary (OOV) problem: If a word not belonging to the vo-
cabulary appears in the test data, it can not be handled and it is
often replaced with a special token (e.g., <UNK>). Also, they mostly
relied on Recurrent Neural Networks, which are not capable of
considering a large context while predicting tokens.
The introduction of Transformers and advanced tokenizers like
Byte Pair Encoding (BPE) [28] allowed to overcome such limitations.
Mastropaoloet al.[ 38, 39] relied on the T5 architecture to tackle
several coding tasks, including ABF. Their results show that such
an approach achieves better results than the approach by Tufano
et al.[56] on their two datasets.
Jianget al.[ 25] studied severalCode Language Models– LLMs
for coding tasks –i.e.,PLBART [ 3], CodeT5 [65], CodeGen [45], and
InCoder [17] in the bug-fixing context. The authors showed that
the best CLM, without fine-tuning, fixes 72% more bugs than the
state-of-the-art deep learning-based techniques, while fine-tuning
enables CLMs to fix 46%–164% more bugs than previous techniques.
```

<a id="comments-bug-fixing-009"></a>
## comments-bug-fixing-009 — Related work: data quality and contextual information

Source: [physical PDF page 3](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=3); reading unit `p003`, lines 50–67.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto; named/cited studies and the Chen et al. taxonomy remain third-party work reported by these authors

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-008](#comments-bug-fixing-008), [comments-bug-fixing-010](#comments-bug-fixing-010)

```text
2.3 Data Quality in Coding Tasks
A few studies analyzed the impact of training data quality on the
resulting model. Liuet al.[ 31] addressed the method-name pre-
diction task enriching the instances with (i) documentation, (ii)
local context, and (iii) project-specific context. This allowed them
to train a model which outperformed state-of-the-art approaches by
a large margin. Prenneret al.[ 49] studied the importance of local
context in instances for automated program repair models. Given
different measures of context (e.g.,lines before the bug), the au-
thors trained different Transformer models, finding that the repair
success increases when the local context is bigger. The work most
closely-related to ours is the one by Van Damet al.[59]. The authors
show that enriching the code instances for the code completion
task with their original comments results in higher effectiveness.
Differently from Van Damet al., we (i) focus on the ABF task, and
(ii) do not rely on the original comments by the authors but on pos-
sibly higher-quality and more complete comments, automatically
generated with GPT-3.5.
```

<a id="comments-bug-fixing-010"></a>
## comments-bug-fixing-010 — Theory: comments and intended behavior

Source: [physical PDF page 3](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=3); reading unit `p003`, lines 68–109.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-009](#comments-bug-fixing-009), [comments-bug-fixing-011](#comments-bug-fixing-011)

```text
3 Theory: Why and What Comments Matter
In this section, we present our theory on the significance of com-
ments for ABF through LLMs and outline the types of informative
content in the comments that we expect could play a crucial role.
3.1 Why Comments Matter for ABF with LLMs
LLMs are, at their core, language models: Their goal is to predict
the most likely token 𝑡𝑛+1 given acontext 𝜒, which is a sequence of
tokens ⟨𝑡1, . . . , 𝑡𝑛⟩. The fine-tuning step, which teaches the model
how to perform a specific task, is performed through a datasetΦ, in
which each instance is represented as a pair ⟨input,output⟩ , where
both elements are token sequences. Let us consider the ABF task,
i.e.,the task of transforming a givenbuggymethod 𝑚𝑏 into a non-
buggy (or fixed) method 𝑚𝑓 . In the fine-tuning step, the model is
trained to generate, one at a time, the tokens in 𝑚𝑓 (output) given
the ones in 𝑚𝑏 (input). LLMs are auto-regressive models [60]: For
each token to generate, the context is constituted by the union
of theinputsequence ( 𝑚𝑏 for ABF) and the previously generated
tokens, until a special token is generated to indicate the end of the
outputsequence. Formally, the context that is adopted to generate
the token 𝑡𝑘 can be recursively expressed as 𝜒𝑡𝑘 =𝜒 𝑡𝑘−1 ∪𝐺(𝜒 𝑡𝑘−1 ),
where 𝜒𝑡0 is simply the input sequence (buggy method 𝑚𝑓 in ABF)
and 𝐺 indicate the inference procedure that predicts the next token
given a context.
Consider two identical methods, 𝑚𝑎 and 𝑚𝑏, both consisting
of a single line of Python code: return sorted(list). The first
method, 𝑚𝑎, is intended to sort a list of strings in a case-sensitive
manner and is therefore bug-free. In contrast, 𝑚𝑏 is meant to sort a
list of strings in a case-insensitive manner, making it buggy. This
example illustrates how the same source code can be simultane-
ouslybug-freein one context andbuggyin another. Now, let us
introduce two models: 𝑀Φ𝑏 and 𝑀Φ𝑐 . The model 𝑀Φ𝑏 is fine-tuned
on a dataset Φ𝑏 that contains only code without comments, while
𝑀Φ𝑐 is fine-tuned on Φ𝑐, a dataset enriched with comments that
describe the code in each instance. The difference between these
models lies in their learning capabilities. 𝑀Φ𝑏 learns to generate
code-related tokens solely based on other code-related tokens. In
essence, it focuses on repeating patterns of changes within the
code itself. Conversely, 𝑀Φ𝑐 is exposed to a broader set of patterns,
enabling it to learn not only code-to-code transformations but also
natural language-to-code mappings, akin to what happens in the
code generation task. This additional context allows 𝑀Φ𝑐 to bet-
ter infer the intended behavior of the code, particularly in cases
```

<a id="comments-bug-fixing-011"></a>
## comments-bug-fixing-011 — Table 1: comment taxonomy and examples

Source: [physical PDF page 4](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=4); reading unit `p004`, lines 2–32.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto; named/cited studies and the Chen et al. taxonomy remain third-party work reported by these authors

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-010](#comments-bug-fixing-010), [comments-bug-fixing-012](#comments-bug-fixing-012)

```text
Table 1: Multi-intent comment taxonomy [9].
CategoryDescription Example
What Describes the functionality of a
method
“A helper function that processes
the stack. ”
Why Explains the reason why a
method is provided or the de-
sign rationale of the method
“Get a copy of the map (for diag-
nostics)”
Usage Describes the usage or the ex-
pected set-up of using a method
“Should be called before the ob-
ject is used”
How Describes the implementation
details of a method
“Convert the byte[] to a secret
key”
Property Asserts properties of a method
including pre-conditions or
post-conditions of a method
“Wait until seqno is greater than
or equal to the desired value or
we exceed the timeout. ”
Others Unspecified or ambiguous com-
ments
“The implementation is awe-
some. ”
where subtle requirements—such as sorting criteria—are conveyed
through comments.
```

<a id="comments-bug-fixing-012"></a>
## comments-bug-fixing-012 — Comment intents and CSV example

Source: [physical PDF page 4](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=4); reading unit `p004`, lines 33–80.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto; named/cited studies and the Chen et al. taxonomy remain third-party work reported by these authors

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-011](#comments-bug-fixing-011), [comments-bug-fixing-013](#comments-bug-fixing-013)

```text
3.2 What Comments Matter
Code comments can be aimed at documenting different aspects,
such as design rationale, pre-conditions/post-conditions, and im-
plementation details [69]. According to a study by Chenet al.[ 9]
comments can have six different intents, and they can be used to
documentwhatthe method does,whyit does it (i.e.,the design
rationale),howthe method is implemented, what is its intendedus-
age, whatpropertiescharacterize it (e.g.,pre- or post-conditions),
orotheraspects. We report in Table 1 a complete description of
each category with examples. Muet al.[ 44] recently observed that
over 66% of comments in top-starred Java repositories are multi-
intent,i.e.,they document multiple aspects of the code within a
single comment. This suggests that developers often feel the need
to capture various dimensions of a method behavior or purpose in
their comments. We conjecture that comments addressing all the
above-mentioned intents, except forother, can enhance the effec-
tiveness of ABF models. Comments categorized asotherprimarily
represent noise and do not contribute meaningful information about
the code (see the example in Table 1). Therefore, we assume that
comments with this intent play a minimal role in aiding bug fixing.
To better explain why we theorize this, let us consider the fol-
lowing example. There is a method namedprocessCSV that reads
a CSV file and processes each row to compute the mean of the nu-
merical value contained in the 𝑖-th column, where 𝑖 is a parameter.
The method is supposed to count empty cells as 0, but it throws
an exception instead since it reads an empty string which is not a
number. Without comments, the model might attempt to fix the
method by adding a check to skip empty strings entirely. However,
this would not resolve the issue but merely change the nature of the
bug, as the intended behavior of counting empty cells as 0 would
still not be achieved.
Aproperty-related comment could contain information about
the post-condition (e.g.,“the method returns a number”) that could
help the model understand where the issue is (i.e.,it throws an
exception). Comments documentingwhatthe method is supposed
to do (e.g.,“computes the mean of the values in the i-th column and
counts the empty cells as 0”) andhowthe method is implemented
(e.g.,“the method sums the values in the i-th column over the rows
and returns such a value divided by the number of rows”) may help
to clarify the intended functionality and find discrepancies between
the code and the expected behavior. A comment documentingwhy
the method is necessary (e.g.,“computes a robust mean of the val-
ues (for statistical calculations)”) might help to indicate the model
to handle edge-cases without missing values. Finally, a comment
documenting the expectedusage(e.g.,“the i value should refer to a
column that only contain numerical data or empty values”) could
help guiding the model to avoid performing unnecessary checks
(e.g.,if the cell contains non-numeric characters).
```

<a id="comments-bug-fixing-013"></a>
## comments-bug-fixing-013 — Research questions and dataset origin

Source: [physical PDF page 4](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=4); reading unit `p004`, lines 81–117.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto; named/cited studies and the Chen et al. taxonomy remain third-party work reported by these authors

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-012](#comments-bug-fixing-012), [comments-bug-fixing-014](#comments-bug-fixing-014)

```text
4 Empirical Study Design
Thegoalof our study is to validate our theory,i.e.,to determine
whether the presence of comments can improve the effectiveness of
LLMs in the ABF task. Thus, our study is steered by the following
Research Questions (RQs):
• RQ1:Does adding comment allow to improve the bug fixing
capabilities of LLMs?
•RQ 2:How important are the comments to the model?
4.1 Study Context
The context of the study consists of buggy Java methods paired with
their fixed versions. We mainly rely on the data released by Tufano
et al.[ 56]. In their work, the authors mined GitHub from March
2011 to October 2017 and collected bug-fixing commits through
matching patterns (e.g.,“fix bug”, “solve error”, etc.). In total, they
collected ∼10M of such commits. They filtered out commits that
(i) contained non-Java files, (ii) created new files, and (iii) involved
changes in more than five files. Thus, they reduced the number
of commits to 787,178. They associated eachfixedversion of the
method to its previous version (buggy). After removing comments
and annotations, they further abstracted the pairs by replacing
identifiers and literals with placeholders, preserving frequent id-
ioms (i.e.,frequent identifiers and literals). Finally, they filtered
the ⟨bug,fix⟩ pairs into two datasets based on the number of to-
kens, creatingBFP 𝑠𝑚𝑎𝑙𝑙 (58k instances with at most 50 tokens) and
BFP𝑚𝑒𝑑𝑖𝑢𝑚 (65k instances with at least 50 tokens, and at most 100
tokens). We selected this dataset because, among those publicly
available, it represents the most suitable and comprehensive option
for our study. First, it provides bug-fix pairs at themethod-to-method
level, offering a more realistic granularity of software changes than
single-hunkor snippet-based datasets commonly used in previous
work (e.g.,the dataset by Zhuet al.[ 70]). Second, such instances
cover a more recent and representative period (i.e.,2011–2017),
unlike older datasets such as those by Lutellieret al.[ 34] (pre-2010)
or Monperruset al.[ 43] (circa 2015). Finally, although the original
dataset was released as two separatesmallandmediumsubsets,
as we explain below, we merged and extended them into a single
renovated version to overcome their original limitations.
```

<a id="comments-bug-fixing-014"></a>
## comments-bug-fixing-014 — Dataset renovation rationale

Source: [physical PDF page 4](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=4); reading unit `p004`, lines 118–122.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-013](#comments-bug-fixing-013), [comments-bug-fixing-015](#comments-bug-fixing-015)

```text
Dataset Renovation.Despite the before-described datasets
have been extensively leveraged as benchmarks in several studies
that tackled ABF [3, 8, 14, 19, 23, 24, 39, 63, 65], they suffer from
some limitations. Because of the limited capabilities of the models
they used (i.e.,RNN-based) and because of the Out-of-Vocabulary
```

<a id="comments-bug-fixing-015"></a>
## comments-bug-fixing-015 — Table 2 and dataset renovation filters

Source: [physical PDF page 5](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=5); reading unit `p005`, lines 2–45.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-014](#comments-bug-fixing-014), [comments-bug-fixing-016](#comments-bug-fixing-016)

```text
Table 2: Comparing the old and renewed datasets in terms of
number of tokens and cyclomatic complexity (CC) for both
thebuggy(B) andfixed(F) parts of the instances.
Dataset # Tokens (B) # Tokens (F) CC (B) CC (F)
BFP𝑠𝑚𝑎𝑙𝑙 31.92 29.16 1.35 1.36
BFP𝑚𝑒𝑑𝑖𝑢𝑚 75.07 73.68 2.45 2.50
Renewed (Our) 101.29 108.36 3.22 3.49
(OOV) problem, the authors abstracted the identifiers of the in-
stances and partitioned the datasets based on token count.
To overcome such limitations, we re-build the dataset from the
raw source code. Starting with the ∼787k mined commits provided
in the replication package by Tufanoet al.[ 56], we first extract all
methods that underwent fix-related changes. Following the original
methodology, we use the GumTree Spoon AST Diff tool [16] to cal-
culate the number of edit actions (in terms of AST transformations).
We exclude methods with no edit actions —e.g.,those involving
only changes to comments — and those requiring more than one
hundred edit actions, as these are likely tangled commits involv-
ing changes beyond a simple bug fix. This step filters out 176,413
instances. Additionally, we identify and remove 87,819 duplicate in-
stances. We keep only instances from commits containing changes
focused on a single method. We do this to avoid cases in which
the fix requires edit action on more than a method. The model,
indeed, will see only a single method and will be asked to fix it.
This means that we exclude those bug-fixes for which the change in
a method does not completely fix the bug, ensuring a fair training
and evaluation process. We exclude ∼1.5M instances in this step.
Then, following the state-of-the-art pre-processing procedures, we
perform additional filtering steps. Specifically, we exclude instances
with commented-out code [52] (106,487), unusual sequences like
“____”[58] (13,245), and self-admitted technical debt, like TODO
or FIXME [35, 52, 58] (20,123). To avoid to confuse the model dur-
ing fine-tuning, we remove instances for which we have the same
“buggy” code and different “fixed” code, and vice-versa [62] (12,971).
Unlike Tufanoet al.[ 56], we do not abstract identifiers or literals,
preserving the source code in its original form. We exclude instances
with fewer than 10 tokens (trivial methods) and those exceeding
512 tokens, as the model cannot handle more than this number of
tokens. This filtering approach aligns with similar works [38, 57, 62].
As a result, our dataset includes larger instances compared to the
dataset by Tufanoet al.[ 56], which is limited to methods with a
maximum of 100 tokens, as shown in Table 2. After applying these
filters, we obtain a dataset comprising 116,372 bug-fix pairs, which
we refer to as𝐷 𝑏.
```

<a id="comments-bug-fixing-016"></a>
## comments-bug-fixing-016 — Generated-comment rationale and design

Source: [physical PDF page 5](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=5); reading unit `p005`, lines 46–86.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto; named/cited studies and the Chen et al. taxonomy remain third-party work reported by these authors

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-015](#comments-bug-fixing-015), [comments-bug-fixing-017](#comments-bug-fixing-017)

```text
Automatically Generating Comments.To validate our theory,
we require two datasets: one containing commented instances and
another with the same instances stripped of comments (see the ex-
perimental procedure for more details). A potential approach could
have been to use only the instances in 𝐷𝑏 that include developer-
written comments as the dataset with comments, and create the
dataset without comments by removing those comments. However,
we observed that only a small fraction of instances in 𝐷𝑏 contain
developer-written comments (approximately 20%). Moreover, many
of these comments are short or incomplete. For example, a method
namedformat, which formats and appends various types ofunits
to a string, is documented with the one-word commentFormatting.
As a result, relying solely on instances with sufficiently detailed
developer-written comments would have produced a dataset that
is both small and inconsistent. To address this, we adopted the
opposite approach: We retained only the code from the instances
in 𝐷𝑏 and used an automated methodology to generate comments,
creating the alternative dataset with comments through automated
comment generation.
As a preliminarily step, we removed all the developer-written
comments from the methods in 𝐷𝑏. Then, we relied on GPT-3.5
[6] to generate multi-intent comments for a method to document
with an in-context learning setting [ 6], similarly to Genget al.
[18]. The authors showed that providing examples in the prompts
helps the models to generate comments that address the different
aspects of the method (Section 3.2). We relied on GPT-3.5 to balance
the performance of GPT-based models with a manageable cost
and because Su and McMillan [ 53] found that it generates code
summaries that are preferred by developers even more than those
used as ’ground-truth’ in existing datasets. Based on our theory
reported in Section 3, we generate comments for such intents (i.e.,
what,how,why,usage, andproperty). We use a prompt template
with 2 examples (two-shot learning) that provides GPT-3.5 with
sufficient information to generate the comments. We explicitly ask
the model to generate a single sentence comment for each category
for two reasons. First, this choice aligns with code-summarization
research, in which the objective is, typically, to generate a single
sentence summary [ 2, 21, 52, 53]. Second, we want to avoid an
overly unrealistic scenario in which comments exceed code (which
would have happened for smaller methods if we did not impose this
constraint). The prompt template we adopted is reported below:
```

<a id="comments-bug-fixing-017"></a>
## comments-bug-fixing-017 — Prompt template and generation from fixed code

Source: [physical PDF page 5](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=5); reading unit `p005`, lines 87–118.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-016](#comments-bug-fixing-016), [comments-bug-fixing-018](#comments-bug-fixing-018)

```text
You are an expert software developer and you are great at writing
comments as requested. Your role is to write a single sentence
of comment for each one of the following categories: what,
why, how-it-is-done, how-to-use, property. Below you find some
examples:{example-1};{example-2}. Now write the comment
for the following Java method:{target-method}.
The two examples ({example-1} and{example-2}) are reported
in Fig. 2. We choose the two explicit examples of multi-intent com-
ment generation from the replication package of the work by Mu
et al.[ 44]. One of them is a trivial example (first one in Fig. 2),
while the second one is more complex (second one in Fig. 2) to
expose the model to different levels of challenge. The only part
of the whole prompt template that changes for each instance is
{target-method}. Given an instance ⟨𝑚buggy
𝑖 , 𝑚fixed
𝑖 ⟩ in 𝐷𝑏, we re-
place {target-method} with 𝑚fixed
𝑖 ,i.e.,thefixedversion of the
method. We generate comments for thefixedversion rather than for
thebuggyversion because the latter code does not completely meet
the requirements (by definition). The comments generated from it
might reflect such errors. The presence of wrong comments might
not allow us to test our theory. For each instance ⟨𝑚buggy
𝑖 , 𝑚fixed
𝑖 ⟩ in
𝐷𝑏, we define a comment-augmented alternative by pre-pending
the generating comments to both thebuggyandfixedversions,
leading to ⟨𝐶𝐺(𝑚 fixed
𝑖 ) +𝑚 buggy
𝑖 , 𝐶𝐺(𝑚 fixed
𝑖 ) +𝑚 fixed
𝑖 ⟩, where 𝐶𝐺 is
```

<a id="comments-bug-fixing-018"></a>
## comments-bug-fixing-018 — Practical limitation and manual comment validation

Source: [physical PDF page 6](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=6); reading unit `p006`, lines 2–36.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-017](#comments-bug-fixing-017), [comments-bug-fixing-019](#comments-bug-fixing-019)

```text
the comment generation methodology we previously defined. This
leads to the definition of our comment-augmented alternative of
𝐷𝑏, which we call 𝐷𝑐. We did not tune the prompt to optimize the
quality of the generated comments since proposing a comment
generation approach was beyond the scope of our work.
It is worth noting that using the fixed version of the code to
generate comments makes this methodology inapplicable as-is for
improving ABF in practical scenarios, as thefixedversion is ob-
viously not available beforehand. However, our objective is not
to propose a practical methodology for enhancing bug-fixing but
to validate our theory and determine whether comments play a
significant role in the first place.
Validating Generated Comments.We conducted a manual
analysis on a random sample including 400 instances to validate
the generated comments. Specifically, we evaluated thecoherence
[44], defined as whether a comment correctly reflects its intended
category (e.g.,what, why, how), and theadequacy[ 41], defined as
the extent to which the comment correctly describes those aspects
of the source code and does not make mistakes. Coherence is as-
sessed in a binary way (coherentornot coherent), while adequacy
is assessed on a 1 to 5 Likert scale. Two of the authors indepen-
dently performed such an analysis and discussed any disagreement
trying to reach consensus. As for adequacy, we considered two
independent evaluations as not in agreement if one of them was
positive (4 or 5) and the other one was negative (1 or 2). In the other
cases, we computed the overall adequacy as the mean of the two
assigned scores. In thecoherenceanalysis, the evaluators initially
agreed on 349 instances (87% agreement), while the remaining 51
were carefully reviewed and resolved in a meeting. In contrast, no
disagreements arose in theadequacyanalysis, for which we ob-
served a substantial agreement (Cohen’s𝜅 [12] = 0.72). We observed
that 93% of the analyzed comments are coherent with the related
comment category and that the median adequacy score assigned is
equal to 4. Therefore, we can claim that the generated comments
are sufficiently good for our experiment.
```

<a id="comments-bug-fixing-019"></a>
## comments-bug-fixing-019 — Dataset filtering and splits

Source: [physical PDF page 6](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=6); reading unit `p006`, lines 37–61.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-018](#comments-bug-fixing-018), [comments-bug-fixing-020](#comments-bug-fixing-020)

```text
Final Filtering and Splitting.The comment-augmented dataset
𝐷𝑐 naturally contains larger instances than𝐷𝑏 (it contains the same
code plus the generated comments). For this reason, some of the
instances in 𝐷𝑐 contain more than 512 tokens (the maximum our
model can handle). Thus, we remove from𝐷𝑐 the instances that con-
tain more than 512 tokens. We remove such instances also from𝐷𝑏,
ensuring that we still have the same methods in both the datasets.
In this step, we remove 6,163 instances from both datasets. We
also discarded from both the dataset all the instances for which
GPT-3.5 was not able to correctly generate the comments (110). We
identified such instances by automatically verifying, via regular
expressions, that the generated comments followed the expected
format, composed all the types (e.g., what:) followed by a sentence.
We found those instances by filtering out those that did not re-
spect the expected comments structure (i.e.,“what: what-comment”,
etc.). We randomly partition the instances in𝐷𝑏 into three sets (fine-
tuning Φ𝑏, test 𝑇𝑏, and validation 𝑉𝑏) following the 80-10-10 rule,
like most previous work did [5, 39, 40, 62]. We then split 𝐷𝑐 into
fine-tuning, test and validation sets (Φ𝑐, 𝑇𝑐, and 𝑉𝑐, respectively) by
making sure that each instance 𝑖𝑐 ∈𝐷 𝑐 was assigned to the same
type of set as 𝐷𝑏. For example, if an instance 𝑖𝑏 ∈𝐷 𝑏 was assigned
to the fine-tuning set Φ𝑏, its commented counterpart, 𝑖𝑐 ∈𝐷 𝑐 was
assigned to the fine-tuning set Φ𝑐. As a result, we reserved 93,098
pairs for the fine-tuning sets (Φ𝑏 and Φ𝑐), 11,637 for the test sets
(𝑇𝑏 and𝑇 𝑐), and 11,637 for for the validation (𝑉𝑏 and𝑉 𝑐).
```

<a id="comments-bug-fixing-020"></a>
## comments-bug-fixing-020 — Controlled experiment and model variants

Source: [physical PDF page 6](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=6); reading unit `p006`, lines 62–100.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-019](#comments-bug-fixing-019), [comments-bug-fixing-021](#comments-bug-fixing-021)

```text
4.2 Experimental Procedure
RQ1: Comments Impact.To answer RQ 1, we conduct acontrolled
experiment[ 67]. The experimentalobjectsare both (i) the fine-tuned
models, and (ii) the test sets with and without comments we pre-
viously defined. We identified several independent variables (IVs)
related to the model training and configuration that might affect the
dependent variables (DVs), which are related to the effectiveness
of the model. We manipulate some of them (thefactors,i.e.,the
variables for which we want to study the effect on the DVs). We
describe below in details the variables and the procedure we used
to conduct the experiment.
We use two LLMs in our experiment: CodeT5+ [64] and DeepSeek-
Coder [20]. As for CodeT5+, we employ the smallest variant with
220M parameters, using an encoder-decoder architecture suitable
for the bug-fixing task [5, 39, 56]. As for DeepSeek-Coder, we em-
ploy the smallest instruction variant with 1.3B parameters, which
features a decoder-only architecture. The first independent vari-
able (IV LLM) takes two values: CodeT5+ and DeepSeek-Coder. We
choose to leverage such models since (i) they are specifically pre-
trained to handle coding tasks, (ii) they have been extensively used
in previous work [ 7, 27, 63, 66], and (iii) they employ different
model architectures (i.e.,encoder-decoder and decoder-only). For
each LLM, we fine-tune two versions of the model using different
datasets: one of them (Φ𝑐) contains instances with the comments
generated with the previously explained procedure (IV Commentstrain
=Yes), and the other one ( Φ𝑏) contains the same instances without
any comment (IV Commentstrain =No). Formally, the independent vari-
able IV Commentstrain, which represents the presence of comments in
fine-tuning instances, is the firstfactorin our experiment, for which
we have the twotreatments,i.e., Yes(allthe code instances have a
comment) andNo(noneof the code instances has comments). We
call the models fine-tuned on the datasets 𝑀𝐶𝑇
Φ𝑐 , 𝑀𝐶𝑇
Φ𝑏
(CodeT5+),
and 𝑀𝐷𝑆
Φ𝑐 , 𝑀𝐷𝑆
Φ𝑏
(DeepSeek-Coder), respectively. The fine-tuning
```

<a id="comments-bug-fixing-021"></a>
## comments-bug-fixing-021 — Fine-tuning configuration and early stopping

Source: [physical PDF page 6](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=6); reading unit `p006`, lines 101–123.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-020](#comments-bug-fixing-020), [comments-bug-fixing-022](#comments-bug-fixing-022)

```text
process differs between the models. For CodeT5+ the number of
epochs is fixed to 50 ( IV Epochs = 50), the batch size is 12 ( IV BS =
12), the optimizer is AdamW (IV opt = AdamW), and the input and
output size is limited to a maximum of 512 tokens (IV input = IV output
= 512). For DeepSeek-Coder, the number of epochs is fixed to 10
(IV Epochs = 10), the batch size is 32 ( IV BS = 32), and the optimizer
is AdamW ( IV opt = AdamW). Differently from encoder-decoder
models, decoder-only models processes the input and generated
output tokens as a single continuous sequence during generation.
For this reason, we fixed a combined sequence length limit of 2048
tokens (IV max_length = 2048), ensuring that the total number of input
and output tokens does not exceed this value. We employ early
stopping (IV ES =Yes) to prevent overfitting [ 48]. Specifically, we
evaluate the models after each epoch on the respective validation
sets (𝑉𝑐 for 𝑀𝐶𝑇
Φ𝑐 and 𝑀𝐷𝑆
Φ𝑐 , and 𝑉𝑏 for 𝑀𝐶𝑇
Φ𝑏
and 𝑀𝐷𝑆
Φ𝑏
) and take the
best checkpoint before the accuracy decreases for five consecutive
epochs (patience).
```

<a id="comments-bug-fixing-022"></a>
## comments-bug-fixing-022 — Figure 2, test configurations, metrics and statistical tests

Source: [physical PDF page 7](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=7); reading unit `p007`, lines 2–37.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Figure code/comment specimens are image-only in the original and absent from pinned base text; physical page visually inspected. Supplemental transcription is being supplied separately for coordinator integration. Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-021](#comments-bug-fixing-021), [comments-bug-fixing-023](#comments-bug-fixing-023)

```text
Figure 2: The two examples we use for few-shot learning in our prompt.
We evaluate each fine-tuned model on both types of test sets to
study the impact of comments during both fine-tuning and infer-
ence. This corresponds to the independent variable IV Commentstest ,
which controls the presence of comments in the test instances
(Yes/No). Specifically,𝑀𝐶𝑇
Φ𝑏
and 𝑀𝐷𝑆
Φ𝑏
(trained without comments) are
tested on both 𝑇𝑏 (IV Commentstest =No) and 𝑇𝑐 (IV Commentstest =Yes), and
𝑀𝐶𝑇
Φ𝑐 and 𝑀𝐷𝑆
Φ𝑐 (trained with comments) are also tested on both 𝑇𝑏
and 𝑇𝑐. We use greedy decoding as decoding strategy,i.e.,the model
generates the token with the highest probability at each generation
step. We choose such a strategy rather than using sampling-based
decoding methods to study the actual models learned behaviours
during the fine-tuning process.
We consider twodependent variables: Exact Match (EM) and
CodeBLEU (CB). EM represents the number of the correct inferences
made by the model on the test set divided by the size of the test set.
CB [51] measures the similarity between the inference made by the
model and the expected generated code. Such a metric is a variation
of BLEU [47] specialized on the source code. While BLEU relies on
matching n-grams, CodeBLEU considers the syntax (through the
Abstract Syntax Tree) and its semantics (via data-flow).
In addition, we perform statistical tests to compare the differ-
ent training and inference configurations in terms of EM. We use
McNemar’s test [42] on paired test instances, along with the odds
ratio (OR) to measure the magnitude of the effect size. We reject
the null hypothesis (i.e.,no difference in effectiveness between two
configurations) if the 𝑝-value is lower than 0.05. To interpret the
magnitude of the effects, we categorize odds ratios according to
Cohen’s guidelines [4, 13]:very small(OR < 1.44),small(1 .44 ≤
OR<2.48),medium(2.48≤OR<4.27), andlarge(OR≥4.27).
```

<a id="comments-bug-fixing-023"></a>
## comments-bug-fixing-023 — SHAP interpretability procedure

Source: [physical PDF page 7](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=7); reading unit `p007`, lines 38–77.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-022](#comments-bug-fixing-022), [comments-bug-fixing-024](#comments-bug-fixing-024), [comments-bug-fixing-043](#comments-bug-fixing-043)

```text
RQ2: Comments Importance.To answer RQ2, we employ post-
hoc interpretability techniques to understand to what extent tokens
that are part of the comments are important in the inferences the
models 𝑀𝐶𝑇
Φ𝑐 and 𝑀𝐷𝑆
Φ𝑐 make. We use SHAP (SHapley Additive ex-
Planations) [33], a black-box model-agnostic method. As previously
explained, LLMs (and thus our models) generate one token at a time.
Given a token 𝑡𝑘 that the model has to generate from the given
context 𝜒𝑡𝑘 , related to the instance 𝑖𝑐 ∈𝑇 𝑐, SHAP assigns afeature
importancevalue 𝑓 to each token 𝑡∈𝜒 𝑡𝑘 . For our analyses, we use
the same methodology employed by Liuet al.[ 32],i.e.,we adopt
GradientExplainer to approximates SHAP values. More specifically,
for each instance of the test set ⟨𝑚buggy
𝑖 , 𝑚fixed
𝑖 ⟩ ∈𝑇 𝑐 that the model
correctly predicts, we compute the 𝑓 values of all the tokens in
𝑚buggy
𝑖 for each token that the model generates. We ignore the𝑓 val-
ues assigned to the tokens that the model progressively generates
since we are interested in the role of the input code. We normalize
the SHAP values so that their sum is equal to 1.
In a first analysis, we aimed to understand the importance given
to the comments as compared to the importance given to the source
code. For each instance 𝑖𝑐 ∈𝑇 𝑐, we partition the tokens in two sets:
tokens belonging to the comments (𝐶𝑖𝑐 ) and tokens belonging to
the source code (𝑆𝑖𝑐 ). We then estimate the importance of tokens in
the comments (𝐼Comments (𝑖𝑐 )) by summing the 𝑓 -values assigned to
the tokens in 𝐶𝑖𝑐 , and the importance of tokens in the code𝐼Code (𝑖𝑐 )
by summing the 𝑓 -values assigned to the tokens in 𝑆𝑖𝑐 . We report
the distribution of 𝐼Comments (𝑖𝑐 ) and 𝐼Code (𝑖𝑐 ) for all the instances. In
a second more fine-grained analysis, we aimed to understand what
is the importance assigned to the five categories of comments we
generated for each instance. To do this, for each instance 𝑖𝑐 ∈𝑇 𝑐,
we focused on the tokens belonging to the comments (𝐶𝑖𝑐 ) and nor-
malized the 𝑓 -values computed on them so that their sum is equal
to 1. We partitioned the tokens in five classes based on the specific
comment they belonged to (what,why,how,usage, andproperty).
We could easily do this because the comments were always gener-
ated in the same order with our prompt (e.g.,the first comment was
```

<a id="comments-bug-fixing-043"></a>
## comments-bug-fixing-043 — Figure 2: first few-shot example (visual transcription)

Source: [physical PDF page 7](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=7); reading unit `p007`, lines 79–89.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Manual visual transcription from original PDF physical page 7, pypdfium2 scale 2.6 render. Supplemental reading text appended after the extracted page text; consult the original figure for layout.

Transcription/context notes: Editor line numbers/UI omitted; indentation approximated from image.

Related: [comments-bug-fixing-023](#comments-bug-fixing-023), [comments-bug-fixing-044](#comments-bug-fixing-044)

```text
Code:
public int hashCode() {
    return value.hashCode();
}

Comment:
what: Generates a hash code.
why: Generates code for this object.
how: A method that generates a hash code based on the contents of the string representations.
usage: This method is used when this class is used as the code.
property: Return a hashcode for this text attribute.
```

<a id="comments-bug-fixing-044"></a>
## comments-bug-fixing-044 — Figure 2: second few-shot example (visual transcription)

Source: [physical PDF page 7](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=7); reading unit `p007`, lines 91–105.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Manual visual transcription from original PDF physical page 7, pypdfium2 scale 2.6 render. Supplemental reading text appended after the extracted page text; consult the original figure for layout.

Transcription/context notes: Editor line numbers/UI omitted; indentation approximated from image.

Related: [comments-bug-fixing-043](#comments-bug-fixing-043)

```text
Code:
<T> List<T> onFind(Class<T> modelClass, String[] columns, String[] conditions, String orderBy, String limit, boolean isEager) {
    BaseUtility.checkConditionsCorrect(conditions);
    List<T> dataList = query(modelClass, columns, getWhereClause(conditions), getWhereArgs(conditions), null, null,
                            orderBy, limit, getForeignKeyAssociations(modelClass.getName(), isEager));

    return dataList;
}

Comment:
what: Handles the native query of the given table.
why: The open interface for other classes in CRUD package to query the first record in a table.
how: Finds generic values by the conditions specified in the backwards conditions object, the where clause is the product of each of the type.
usage: Method modified just override here before executing your test cases.
property: Returns the order of the order specified.
```

<a id="comments-bug-fixing-024"></a>
## comments-bug-fixing-024 — Table 3 and interpretability procedure continued

Source: [physical PDF page 8](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=8); reading unit `p008`, lines 2–17.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-023](#comments-bug-fixing-023), [comments-bug-fixing-025](#comments-bug-fixing-025)

```text
Table 3: Comparison between the models trained and tested
with and without comments.
Models 𝑻𝒃 𝑻𝒄
EM CB EM CB
𝑀𝐶𝑇
Φ𝑏 (Comments= No) 3.26% 76.21% 3.73% 75.66%
𝑀𝐶𝑇
Φ𝑐 (Comments= Yes)2.78% 78.18% 9.80% 80.38%
𝑀𝐷𝑆
Φ𝑏 (Comments= No) 5.57% 77.72% 7.90% 86.40%
𝑀𝐷𝑆
Φ𝑐 (Comments= Yes)5.09% 77.37% 12.77% 81.01%
always aimed at explainingwhatthe method does). We computed
the importance for each of them, again, by summing the 𝑓 -values.
We report the distribution of 𝐼What (𝑖𝑐 ), 𝐼Why (𝑖𝑐 ), 𝐼How (𝑖𝑐 ), 𝐼Usage (𝑖𝑐 ),
and𝐼 Property (𝑖𝑐 )for all the instances.
```

<a id="comments-bug-fixing-025"></a>
## comments-bug-fixing-025 — RQ1: results without comments at inference

Source: [physical PDF page 8](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=8); reading unit `p008`, lines 18–63.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-024](#comments-bug-fixing-024), [comments-bug-fixing-026](#comments-bug-fixing-026)

```text
5 Empirical Study Results
We report the results of our empirical study and the answers to our
two RQs.
5.1 RQ 1: Comments Impact
The results obtained in terms of Exact Match (EM) and CodeBLEU
(CB) for the four fine-tuned models—𝑀𝐶𝑇
Φ𝑏
and 𝑀𝐷𝑆
Φ𝑏
(trained without
comments), and 𝑀𝐶𝑇
Φ𝑐 and 𝑀𝐷𝑆
Φ𝑐 (trained with comments)—evaluated
on the two test sets𝑇𝑏 (without comments) and𝑇𝑐 (with comments)
are summarized in Table 3. All differences discussed in the following
are statistically significant according to McNemar’s test (𝑝-value
< 0.05). This is due to the large size of the test set. Therefore, we
focus the discussion on the effect size, as measured by the odds
ratio (OR).
We start by analyzing the results on the test set𝑇𝑏, where no com-
ments are provided to the model at inference time. Under this set-
ting, the CodeT5+ model trained without comments (𝑀𝐶𝑇
Φ𝑏
) achieves
an EM of 3.26% and a CB of 76.21%. When trained with commented
instances (𝑀𝐶𝑇
Φ𝑐 ), the model reaches an EM of 2.78% and a slightly
higher CB of 78.18%. This difference, while statistically significant,
reports avery smalleffect size (OR = 0.72), indicating a negligible
practical impact. A similar trend is observed for DeepSeek-Coder:
the model without comments in training (𝑀𝐷𝑆
Φ𝑏
) achieves an EM of
5.57% and CB of 77.72%, while the model trained with comments
(𝑀𝐷𝑆
Φ𝑐 ) reports an EM of 5.09% and CB of 77.37%. Such a compar-
ison corresponds to avery smalleffect size (OR = 0.65). These
results indicate that, when comments are absent at test time, mod-
els trained with comments achieve slightly lower performance than
those trained without them. Surprisingly, this behavior suggests
that the presence of comments during training does not introduce
harmful biases but leads to only slightly weaker performance in
contexts lacking comments, likely because such models tend to rely
on contextual information that are absent at test time.
Training with comments does not significantly impact perfor-
mance in comments-free settings.
```

<a id="comments-bug-fixing-026"></a>
## comments-bug-fixing-026 — RQ1: results with comments at inference

Source: [physical PDF page 8](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=8); reading unit `p008`, lines 64–95.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-025](#comments-bug-fixing-025), [comments-bug-fixing-027](#comments-bug-fixing-027)

```text
When comments are included at test time (𝑇𝑐), both model fami-
lies benefit substantially. For CodeT5+, the non-commented variant
(𝑀𝐶𝑇
Φ𝑏
) increases its EM from 3.26% to 3.73% (OR = 1.44), showing
that comments in the input alone can provide marginal guidance
even without prior exposure. However, the most evident result
emerges for the model trained with comments (𝑀𝐶𝑇
Φ𝑐 ), whose EM
increase from 2.78% to 9.80% (i.e., ∼3× higher) and CB from 78.18%
to 80.38%, with alargeeffect size (OR = 6.86). A similar, and more
pronounced pattern appears for DeepSeek-Coder: 𝑀𝐷𝑆
Φ𝑏
improves
from 5.57% to 7.90% EM when tested on commented code (medium
effect size, OR = 3.42), while 𝑀𝐷𝑆
Φ𝑐 achieves the best overall results,
with an EM of 12.77% and CB of 81.01%, approximately ∼2× the
previous 5.09% with alargeeffect size (OR = 9.76).
These results highlight two main behaviors. First, models trained
without comments still benefit from comments at inference time,
fixing more bugs when contextual information is available. Sec-
ond, models trained with commentssignificantlybenefit from such
contextual information, reporting performance improvements of
approximately two to three times when comments are provided at
test time. In both model families, the combination of training and
testing with comments results in the largest performance, show-
ing that comments act as useful auxiliary signals that enhance the
models reasoning and code comprehension abilities.
Comments consistently improve model performance, regardless
of the training setup. The improvements are more evident when
the model is trained to also leverage such information.
```

<a id="comments-bug-fixing-027"></a>
## comments-bug-fixing-027 — RQ1 model comparisons and answer

Source: [physical PDF page 8](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=8); reading unit `p008`, lines 96–115.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-026](#comments-bug-fixing-026), [comments-bug-fixing-028](#comments-bug-fixing-028)

```text
Across all configurations, DeepSeek-Coder consistently outper-
forms CodeT5+, likely due to the larger number of parameters,
different architecture, and wider pre-training corpus. This confirms
that larger models generally possess stronger bug-fixing capabilities.
Interestingly, the positive effect of adding comments at inference
time, when models have not been trained with them, is more evi-
dent for the larger DeepSeek-Coder, suggesting that bigger models
can better exploit contextual information even without previous
exposure. On the other hand, when fine-tuning is performed also
with commented instances, the smaller CodeT5+ benefits the most,
showing a three times EM improvement when tested with com-
ments, compared to approximately two times improvements for
DeepSeek-Coder. This indicates that while larger models are natu-
rally more capable, smaller ones can close much of the gap when
guided by explicit contextual information such as comments.
Answer to RQ 1.Comments enhance LLM bug-fixing by pro-
viding contextual information that improves performance even
when available only at inference time. Training with comments
remains neutral in comment-free cases but highly beneficial
when comments are present during inference.
```

<a id="comments-bug-fixing-028"></a>
## comments-bug-fixing-028 — RQ2: code/comment attributions

Source: [physical PDF page 8](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=8); reading unit `p008`, lines 116–127.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Mathematical subscripts/superscripts and table layout may be flattened in extraction; preserve model, training and test definitions in linked context.

Related: [comments-bug-fixing-027](#comments-bug-fixing-027), [comments-bug-fixing-029](#comments-bug-fixing-029)

```text
5.2 RQ 2: Comments Importance
Fig. 3 illustrates the importance attributed by the models 𝑀𝐶𝑇
Φ𝑐 and
𝑀𝐷𝑆
Φ𝑐 to tokens belonging to code and comments for their respective
1,141 and 1,486 exact matches. We find that the models consistently
assign higher importance to code-related tokens (i.e.,those rep-
resenting the logic of the method) in nearly all instances, with
fewer than 100 exceptions for both models. However, the boxplot
distributions reveal distinct patterns: for 𝑀𝐶𝑇
Φ𝑐 , the importance is
nearly evenly distributed between code and comments, whereas
```

<a id="comments-bug-fixing-029"></a>
## comments-bug-fixing-029 — RQ2: comment-category attributions and conjectures

Source: [physical PDF page 9](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=9); reading unit `p009`, lines 2–42.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-028](#comments-bug-fixing-028), [comments-bug-fixing-030](#comments-bug-fixing-030)

```text
𝑀𝐷𝑆
Φ𝑐 assigns greater importance to code tokens while still recog-
nizing the value of comment tokens. This analysis, from a different
perspective, supports the findings from RQ1: Comments contribute
significantly to the fix generation process.
When we focus on the different comment categories (right part
of Fig. 3), we find that some comments are more important than
others. Both models give much higher importance to comments
describinghowthe implementation is done as compared to the
other categories. This is quite expected: Such comments document
some implementation details that might have been violated in the
buggyversion. Thus, the models are able to find the violation and
fix it thanks to them. Then, we find that the 𝑀𝐶𝑇
Φ𝑐 gives similar
importance to theproperty-related comments, the ones describing
the methodusage, and its design rationale (why). On the other
hand, it gives less importance to the comments aimed at describ-
ingwhatthe method does. We conjecture that this happens for
two reasons. First, there are generally other elements that help
the model graspwhatthe method is aimed to do (e.g.,the method
name or the identifiers). Such elements make such a comment less
relevant than others. Second, it is probably more rare that a bug
makes the method do something different from what is supposed
to do, so that a comment describing what the method does helps
the model fixing it. Regarding 𝑀𝐷𝑆
Φ𝑐 , we find that the model gives
lower importance attributions toproperty-related andusage-related
comments, while giving higher importance towhyandwhatcom-
ments categories. The models give contrasting importance towhat
comments. We conjecture that the different pre-training objectives
employed between the models may impact on such findings [20, 64].
In particular, the base DeepSeek-coder model was pre-trained using
a next-token prediction objective. For this reason, instances used
during pre-training might have included inputs that better align
with the high-level descriptions generally found inwhatcomments.
Answer to RQ2.Code comments are assigned significant impor-
tance by the models. The most important comments are those
documenting implementation details, while the least important
arewhatcomments for𝑀 𝐶𝑇
Φ𝑐 andpropertycomments for𝑀 𝐷𝑆
Φ𝑐 .
```

<a id="comments-bug-fixing-030"></a>
## comments-bug-fixing-030 — Discussion: incorrect-prediction example

Source: [physical PDF page 9](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=9); reading unit `p009`, lines 43–57.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-029](#comments-bug-fixing-029), [comments-bug-fixing-031](#comments-bug-fixing-031)

```text
6 Discussions and Implications
In this section, we discuss the lessons learned and implications for
future research based on the results of our controlled experiment.
6.1 Lessons Learned
Our results clearly show that comments are beneficial to improve
the effectiveness of LLMs in the ABF task. While this is true in
most cases, we found some instances for the generated comments
are not sufficiently detailed to fix the bug. In Fig. 4 we see an
interesting example. In the buggy version, the method attempted to
set an answer“id”in the“SaveAnswerEvent”object, which could
result in incomplete event data if an exception occurred during the
save operation. The fix removed such an assignment, ensuring the
event is posted without depending on the successful retrieval of
theid. However, the model predicted a candidate fix that set the
“answer”object in the event, leading to an analogous problem. It
```

<a id="comments-bug-fixing-031"></a>
## comments-bug-fixing-031 — Figure 3: attribution distributions

Source: [physical PDF page 9](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=9); reading unit `p009`, lines 58–98.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Boxplot labels/caption retained; plotted distributions are not numerically transcribed. Original physical page 9 was visually inspected.

Related: [comments-bug-fixing-030](#comments-bug-fixing-030), [comments-bug-fixing-032](#comments-bug-fixing-032)

```text
Comments Code
0
5
10
15
20
25
30
35
40
45
50
What Why How-it-is-done Usage Property
0.0
2.5
5.0
7.5
10.0
12.5
15.0
17.5
Code T5+
Deepseek-Coder
Comments Code
0
5
10
15
20
25
30
35
40
What Why How-it-is-done Usage Property
2
4
6
8
10
Figure 3: Importance distribution for comments and code
(left part) and comment intents (right part).
```

<a id="comments-bug-fixing-032"></a>
## comments-bug-fixing-032 — Incorrect and correct examples; completeness and correctness

Source: [physical PDF page 9](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=9); reading unit `p009`, lines 99–117.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-031](#comments-bug-fixing-031), [comments-bug-fixing-033](#comments-bug-fixing-033)

```text
probably did that because the input code contained a call to the
setAnswerId method and the model did not try to change much
the code structure. In addition, thehowcomment states“... and
catches any exceptions to set in the event. ”, which could mislead the
model. We tried to change the comment by removing such a part
of the comment, and this resulted in a correct fix.
On the other hand, there are cases in which generated comments
are sufficient to help the model generate the correct fix. As we
can see in Fig. 5, the method did not store theaggregationBuffer
in thehashMap. Theproperty-related comment most likely helped
fix this bug since it explicitly says that the methodensures that
an aggregation buffer is available for the specified grouping key,
property that is violated in the buggy version of the code. The
model without comments fails to correctly fix the method by us-
ing aggregationBufferFactory instead of storing the created
SpecificMutableRowin thehashMap.
Lesson Learned 1.Although comments can boost the perfor-
mance of automated bug-fixing models, their completeness and
correctness is key to fix bugs.
```

<a id="comments-bug-fixing-033"></a>
## comments-bug-fixing-033 — Removing implementation comments: motivation

Source: [physical PDF page 9](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=9); reading unit `p009`, lines 118–128.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-032](#comments-bug-fixing-032), [comments-bug-fixing-034](#comments-bug-fixing-034)

```text
In a real use-case scenario, however, it is unlikely that developers
provide comments for all the categories we studied. Most impor-
tantly, developers might be reticent to provide comments regarding
the implementation details because the such details might change
frequently, thus leading to inconsistencies between comments and
code and an increased effort. All the other categories of comments,
instead, might change less frequently. To test what would happen
in a more realistic context, we fine-tuned and evaluated 𝑀𝐶𝑇
Φ𝑐 ∗ on a
variation of the 𝐷𝑐 dataset (𝐷𝑐∗), from which we removed thehow
comments, and tested it on the corresponding test set 𝑇𝑐∗, where
```

<a id="comments-bug-fixing-034"></a>
## comments-bug-fixing-034 — Figures 4 and 5 and non-implementation-comment result

Source: [physical PDF page 10](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=10); reading unit `p010`, lines 2–15.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Transcription/context notes: Figure code/comment specimens are image-only in the original and absent from pinned base text; physical page visually inspected. Supplemental transcription is being supplied separately for coordinator integration.

Related: [comments-bug-fixing-033](#comments-bug-fixing-033), [comments-bug-fixing-035](#comments-bug-fixing-035)

```text
Figure 4: Example of wrong prediction.
Figure 5: Example of a𝑀 𝐶𝑇
Φ𝑐 correct fix, and𝑀 𝐶𝑇
Φ𝑏
wrong fix.
thehowcomments were also removed. Even without implemen-
tation details, we still observe a significant boost in terms of EM,
which is 91% higher than the baseline model ( 𝑀𝐶𝑇
Φ𝑏
on 𝑇𝑏), with
higher CodeBLEU. This result shows that even if not too detailed,
comments can help improving ABF.
Lesson Learned 2.Even non-implementation related com-
ments can help to improve the effectiveness of LLMs for ABF.
```

<a id="comments-bug-fixing-035"></a>
## comments-bug-fixing-035 — Comments generated from buggy code: negative result

Source: [physical PDF page 10](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=10); reading unit `p010`, lines 16–32.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-034](#comments-bug-fixing-034), [comments-bug-fixing-036](#comments-bug-fixing-036)

```text
We further explored what would happen if the comments were
instead generated from thebuggyversion of the code. This scenario
represents a realistic context, in which comments can be automati-
cally generated or manually written based on the available buggy
code. However, this settinginherentlyimplies incorrect comments,
since they document the buggy logic rather than the intended cor-
rect behavior. Thus, we tested the previously fine-tuned models on
a variant of the test set with comments generated from the buggy
code. As expected, all models performed the same or slightly worse
with buggy-generated comments. For instance, CodeT5+ saw small
EM drops (3.26% to 2.92%, 2.78% to 2.67%), with similar negligible
or negative trends for DeepSeek-Coder. These results confirm that
comments generated from buggy code do not provide useful guid-
ance and can even hinder models, since they reinforce incorrect
behaviors embedded in the buggy code.
Lesson Learned 3.Comments generated from buggy code do
not help and can mislead automated bug-fixing models.
```

<a id="comments-bug-fixing-036"></a>
## comments-bug-fixing-036 — Authors' implications for research, practice and tools

Source: [physical PDF page 10](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=10); reading unit `p010`, lines 33–56.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-035](#comments-bug-fixing-035), [comments-bug-fixing-037](#comments-bug-fixing-037)

```text
6.2 Implications
Our findings have several implication for both researchers and prac-
titioners. First, removing code comments from training instances is
a common practice in ABF research [56]. However, given the results
of our findings we suggest researchers to not remove comments
from training instances. Low-quality comments should be improved,
whenever possible. Moreover, researchers could devise approaches
to automatically generate high-quality comments that serve as ef-
fective contextual information, inferred from the broader project
context. For practitioners, our findings highlight the importance of
thoroughly documenting code to better leverage the capabilities of
LLMs for automating bug-fixing. While it is widely recognized that
code documentation improves maintainability, our results suggest
that its benefits extend beyond internal quality, positively impact-
ing external quality by enhancing the support developers receive
in the bug fixing process by LLMs. Although our study focused on
ABF, we conjecture that these findings may apply to other tasks as
well, which future research should aim to confirm or refute. Finally,
tool builders could develop features to identify comments lacking
sufficient detail (e.g.,those that fail to explain rationale, precondi-
tions, or postconditions) or of low quality (e.g.,inconsistent with
the code). Such tools could alert developers when attempting to use
LLMs to repair methods with inadequate comments and encourage
improvements, potentially supported by automated suggestions.
```

<a id="comments-bug-fixing-037"></a>
## comments-bug-fixing-037 — Construct-validity threats

Source: [physical PDF page 10](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=10); reading unit `p010`, lines 57–65.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-036](#comments-bug-fixing-036), [comments-bug-fixing-038](#comments-bug-fixing-038), [comments-bug-fixing-045](#comments-bug-fixing-045)

```text
7 Threats to Validity
Threats to construct validity. We started from the dataset pro-
vided by Tufanoet al.[ 56] to define the datasets we employ in our
study,i.e., 𝐷𝑏 and 𝐷𝑐. As the authors themselves acknowledged,
some instances might not represent actual bug-fixing instances or
the bug-fixing change might be in a method different from the one
in a given instance. To limit this threat, we used a stricter criterion
to select instances,i.e.,we only considered commits impacting a
single method. We defined 𝐷𝑐 leveraging GPT-3.5 to generate the
```

<a id="comments-bug-fixing-045"></a>
## comments-bug-fixing-045 — Figure 4: shared comments (visual transcription)

Source: [physical PDF page 10](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=10); reading unit `p010`, lines 67–71.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Manual visual transcription from original PDF physical page 10, pypdfium2 scale 2.6 render. Supplemental reading text appended after the extracted page text; consult the original figure for layout.

Transcription/context notes: Editor line numbers/UI omitted; indentation approximated from image.

Related: [comments-bug-fixing-037](#comments-bug-fixing-037), [comments-bug-fixing-046](#comments-bug-fixing-046)

```text
// what: Saves an answer object.
// why: Handles the saving of an answer object to the repository and posts an event.
// how: Creates a SaveAnswerEvent, attempts to save the answer to the repository, and catches any exceptions to set in the event.
// usage: Call this method to save an answer object and trigger related events.
// property: Posts a SaveAnswerEvent after saving the answer.
```

<a id="comments-bug-fixing-046"></a>
## comments-bug-fixing-046 — Figure 4: Buggy (visual transcription)

Source: [physical PDF page 10](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=10); reading unit `p010`, lines 73–82.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Manual visual transcription from original PDF physical page 10, pypdfium2 scale 2.6 render. Supplemental reading text appended after the extracted page text; consult the original figure for layout.

Transcription/context notes: Editor line numbers/UI omitted; indentation approximated from image.

Related: [comments-bug-fixing-045](#comments-bug-fixing-045), [comments-bug-fixing-047](#comments-bug-fixing-047)

```text
public void saveAnswer(Answer answer) {
    SaveAnswerEvent event = new SaveAnswerEvent();
    try {
        long id = repository.saveAnswer(answer);
        event.setAnswerId(id);
    } catch (Exception e) {
        event.setThrowable(e);
    }
    bus.post(event);
}
```

<a id="comments-bug-fixing-047"></a>
## comments-bug-fixing-047 — Figure 4: Fixed (oracle) (visual transcription)

Source: [physical PDF page 10](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=10); reading unit `p010`, lines 84–92.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Manual visual transcription from original PDF physical page 10, pypdfium2 scale 2.6 render. Supplemental reading text appended after the extracted page text; consult the original figure for layout.

Transcription/context notes: Editor line numbers/UI omitted; indentation approximated from image.

Related: [comments-bug-fixing-046](#comments-bug-fixing-046), [comments-bug-fixing-048](#comments-bug-fixing-048)

```text
public void saveAnswer(Answer answer) {
    SaveAnswerEvent event = new SaveAnswerEvent();
    try {
        repository.saveAnswer(answer);
    } catch (Exception e) {
        event.setThrowable(e);
    }
    bus.post(event);
}
```

<a id="comments-bug-fixing-048"></a>
## comments-bug-fixing-048 — Figure 4: Fixed (prediction) (visual transcription)

Source: [physical PDF page 10](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=10); reading unit `p010`, lines 94–103.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Manual visual transcription from original PDF physical page 10, pypdfium2 scale 2.6 render. Supplemental reading text appended after the extracted page text; consult the original figure for layout.

Transcription/context notes: Editor line numbers/UI omitted; indentation approximated from image.

Related: [comments-bug-fixing-047](#comments-bug-fixing-047), [comments-bug-fixing-049](#comments-bug-fixing-049)

```text
public void saveAnswer(Answer answer) {
    SaveAnswerEvent event = new SaveAnswerEvent();
    try {
        repository.saveAnswer(answer);
        event.setAnswer(answer);
    } catch (Exception e) {
        event.setThrowable(e);
    }
    bus.post(event);
}
```

<a id="comments-bug-fixing-049"></a>
## comments-bug-fixing-049 — Figure 5: shared comments (visual transcription)

Source: [physical PDF page 10](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=10); reading unit `p010`, lines 105–109.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Manual visual transcription from original PDF physical page 10, pypdfium2 scale 2.6 render. Supplemental reading text appended after the extracted page text; consult the original figure for layout.

Transcription/context notes: Editor line numbers/UI omitted; indentation approximated from image. The how line contains printed [...] and the usage line is clipped after [ in the original figure. No missing words are reconstructed. Body prose calls the ensures statement property-related, while the screenshot labels it why; both are retained as printed.

Related: [comments-bug-fixing-048](#comments-bug-fixing-048), [comments-bug-fixing-050](#comments-bug-fixing-050)

```text
// what: Retrieves the aggregation buffer based on the provided grouping key.
// why:Ensures that an aggregation buffer is available for the specified grouping key.
// how:Retrieves the aggregation buffer from a hashmap based on the grouping key [...]
// usage: Call this method to obtain the aggregation buffer for a specific grouping key [
// property: Returns the aggregation buffer associated with the provided grouping key.
```

<a id="comments-bug-fixing-050"></a>
## comments-bug-fixing-050 — Figure 5: Correct fix (visual transcription)

Source: [physical PDF page 10](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=10); reading unit `p010`, lines 111–119.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Manual visual transcription from original PDF physical page 10, pypdfium2 scale 2.6 render. Supplemental reading text appended after the extracted page text; consult the original figure for layout.

Transcription/context notes: Editor line numbers/UI omitted; indentation approximated from image. The hashMap.put line is the green added line.

Related: [comments-bug-fixing-049](#comments-bug-fixing-049), [comments-bug-fixing-051](#comments-bug-fixing-051)

```text
public MutableRow getAggregationBufferByKey(MutableRow groupingKey) {
    MutableRow aggregationBuffer = hashMap.get(groupingKey);
    if (aggregationBuffer == null) {
        aggregationBuffer = new SpecificMutableRow(aggregationBufferSchema);
        aggregationBuffer.copyFrom(emptyAggregationBuffer, aggregationBufferSchema);
        hashMap.put(groupingKey, aggregationBuffer);
    }
    return aggregationBuffer;
}
```

<a id="comments-bug-fixing-051"></a>
## comments-bug-fixing-051 — Figure 5: Wrong fix (visual transcription)

Source: [physical PDF page 10](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=10); reading unit `p010`, lines 121–129.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Manual visual transcription from original PDF physical page 10, pypdfium2 scale 2.6 render. Supplemental reading text appended after the extracted page text; consult the original figure for layout.

Transcription/context notes: Editor line numbers/UI omitted; indentation approximated from image. Diff removes aggregationBuffer = new SpecificMutableRow(aggregationBufferSchema); and adds the factory call plus hashMap.put. Do not infer a runnable project from this isolated specimen.

Related: [comments-bug-fixing-050](#comments-bug-fixing-050)

```text
public MutableRow getAggregationBufferByKey(MutableRow groupingKey) {
    MutableRow aggregationBuffer = hashMap.get(groupingKey);
    if (aggregationBuffer == null) {
        aggregationBuffer = aggregationBufferFactory.newSpecificMutableRow();
        aggregationBuffer.copyFrom(emptyAggregationBuffer, aggregationBufferSchema);
        hashMap.put(groupingKey, aggregationBuffer);
    }
    return aggregationBuffer;
}
```

<a id="comments-bug-fixing-038"></a>
## comments-bug-fixing-038 — Construct-validity threats continued

Source: [physical PDF page 11](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=11); reading unit `p011`, lines 2–17.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-037](#comments-bug-fixing-037), [comments-bug-fixing-039](#comments-bug-fixing-039)

```text
multi-intent comments. It is possible that some generated com-
ments are not appropriate for a given category (e.g., usage). Besides,
it is possible that such comments are not good enough. To limit
this threat, we conducted a manual analysis on random sample
including 400 generated comments. We evaluated thecoherenceto
the given category (coherentornot coherent) and theadequacyto
the source code (on a 1 to 5 Likert scale). Two of the authors inde-
pendently performed such an analysis. If any disagreement arose,
they would have discussed trying to reach a consensus. It is also
possible that some instances in our dataset appeared in the datasets
used to pre-train CodeT5+ and DeepSeek-Coder. We started from
the same pre-trained models to define the specialized bug-fixing
models trained with and without comments. If such an issue biased
the results, it did so for both the models. Thus, we believe that the
relativeresults (i.e.,the difference between the models) was not
affected by this possible issue whatsoever.
```

<a id="comments-bug-fixing-039"></a>
## comments-bug-fixing-039 — Internal-validity threats: metrics and attribution estimates

Source: [physical PDF page 11](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=11); reading unit `p011`, lines 18–48.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-038](#comments-bug-fixing-038), [comments-bug-fixing-040](#comments-bug-fixing-040)

```text
Threats to internal validity. We used EM and CB as dependent
variables of our experiment to measure the effectiveness of the mod-
els. EM is a lower bound of the actual bug-fixing capabilities of the
models we tested. A prediction that exactly matches the expected
output is surely a bug fix; on the other hand, a prediction not exactly
matching the excepted output is not necessarily a wrong fix as it
could contain a valid alternative patch. For example, if the expected
fix contains a call toCollections.isEmpty(list) while the pre-
dicted one contains list.isEmpty(), the latter is a valid bug fix
even if not exactly matching the expected one. Thus, it is possible
that theabsolutecapabilities of the models are actually higher. We
use CodeBLEU to measure the distance between the predicted se-
quence and the expected one. We used this as an estimate of the
effort a developer would make to transform an incorrect fix pro-
vided by the model into the correct fix. It is worth noting, however,
that a small number of tokens to change does not necessarily imply
that developers would make a smaller effort. Finally, we adopted a
state-of-the-art post-hoc interpretability methods [32, 33] to esti-
mate the importance given by the model to comments (in general)
and to different categories of comments (specifically). It is worth
noting that such an approach, like others available, only provide
estimates on the importance given by the model to single tokens.
Thus, it is possible that the importance that the model assigns to
comments and to different comment categories differs from the one
we report. It is worth noting, however, that when removing the
supposedly best category of comments according to our analysis
(i.e., howcomments) we obtain lower EM than the one obtained
when using all the comments (even if still higher than the one ob-
tained without comments). While this suggest that the reported
values are sufficiently reliable, further tests with single categories
of comments are required to confirm this result.
```

<a id="comments-bug-fixing-040"></a>
## comments-bug-fixing-040 — External-validity threats and GPT-4.1 supplementary result

Source: [physical PDF page 11](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=11); reading unit `p011`, lines 49–69.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-039](#comments-bug-fixing-039), [comments-bug-fixing-041](#comments-bug-fixing-041)

```text
Threats to external validity. The dataset by Tufanoet al.[ 56]
from which we built our dataset contains instances relatively old
and limited to the Java programming language. Our results might
not generalize to bug-fixing commits performed more recently
and on different programming languages. It is worth noting that
the dataset by Tufanoet al.has been used in recent work as well
[3, 8, 14, 19, 22–24, 30, 37, 39, 63, 65, 71]. Our results might not gen-
eralize to other models. To limit this threat, we tested our theory
on two models, CodeT5+ [64] and DeepSeek-Coder [20]. The first
representative of an encoder-decoder architecture and limited num-
ber of parameters (i.e.,220M), and the second one representative of
a decoder-only architecture with an higher number of parameters
(i.e.,1.3B). To further assess the generalizability of our findings, we
evaluated GPT-4.1 in a zero-shot setting on the same test sets with
and without comments, observing an increase in EM from 6.11%
(without comments) to 8.63% (with comments). This supplementary
result provides preliminary evidence that the positive impact of
comments on automated bug fixing extends to more recent and
larger LLMs. Still, we acknowledge that further empirical evidence
is needed to confirm this phenomenon on different models and
different configurations.
```

<a id="comments-bug-fixing-041"></a>
## comments-bug-fixing-041 — Conclusion and future work

Source: [physical PDF page 11](../../../ai-code-comments/2026-impact-of-code-comments-on-bug-fixing.pdf#page=11); reading unit `p011`, lines 70–89.

Attribution: Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino and Rocco Oliveto

Context: Paper section in source order; linked records retain cross-page definitions, experimental conditions and qualifications. Reported importance scores are the paper's measurements, not collection rankings.

Related: [comments-bug-fixing-040](#comments-bug-fixing-040)

```text
8 Conclusion
We conducted an empirical study to investigate the impact of com-
ments on the Automated Bug Fixing (ABF) task. We compared
models trained and tested on all combinations of bug-fix pairs with
and without automatically generated, multi-intent comments fo-
cusing on five intents (what,why,how,usage, andproperty).
Our results show that the presence of comments—whether pro-
vided during training, testing, or both—substantially improves the
effectiveness of large language models in fixing bugs, with accu-
racy improvements of up to three times compared to configurations
where comments are absent. When analyzing the importance of
the five categories of comments we took into account, we found
that comments that explainhowthe method is implemented are
the most important ones, while the ones related towhatand/or
propertythe method does are less relevant.
Future studies are needed to provide further empirical evidence
in support of our findings, also on other tasks (e.g.,vulnerability
fixing). Besides, it will be interesting to study to what extent the
comments provided by developers are sufficient to improve the
effectiveness in bug fixing.
```
