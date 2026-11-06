# Testing the Effect of Code Documentation on Large Language Model Code Understanding: source passages

Generated from records.json and the pinned reading text. No ranking or recommendation is implied.

Extent: `local_paper`. Text SHA-256: `8b2ca832c655da72143a472197366423b1b09afe6d024b3cc7634f09d4bbb0a4`.

[Selections](records.json) · [Coverage and gaps](coverage.json) · [Collection index](../../README.md)

- Figures 2?5 on physical pages 4?5 were visually inspected; pinned text contains captions/axis labels but not bar-height data. Consult original figures for graphical values.
- Figure 1 on physical page 3 loses code indentation in pinned text; visual original is required for syntactic layout.

<a id="documentation-llm-understanding-001"></a>
## documentation-llm-understanding-001 — Abstract

Source: [physical PDF page 1](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=1); reading unit `p001`, lines 8–22.

Attribution: William Macke and Michael Doyle

Context: Paper section in source order; linked records preserve continuation and experimental context.

Related: [documentation-llm-understanding-002](#documentation-llm-understanding-002)

```text
Abstract
Large Language Models (LLMs) have demon-
strated impressive abilities in recent years with
regards to code generation and understanding.
However, little work has investigated how doc-
umentation and other code properties affect an
LLM’s ability to understand and generate code
or documentation. We present an empirical
analysis of how underlying properties of code
or documentation can affect an LLM’s capabil-
ities. We show that providing an LLM with "in-
correct" documentation can greatly hinder code
understanding, while incomplete or missing
documentation does not seem to significantly
affect an LLM’s ability to understand code.
```

<a id="documentation-llm-understanding-002"></a>
## documentation-llm-understanding-002 — Introduction: code understanding tasks

Source: [physical PDF page 1](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=1); reading unit `p001`, lines 23–44.

Attribution: William Macke and Michael Doyle; cited authors retain their explicitly named positions, including Pritchard on understanding in section 3

Context: Paper section in source order; linked records preserve continuation and experimental context.

Related: [documentation-llm-understanding-001](#documentation-llm-understanding-001), [documentation-llm-understanding-003](#documentation-llm-understanding-003)

```text
1 Introduction
Recently, Large Language Models (LLMs) have ap-
proached or pushed the state of the art for multiple
natural language processing (NLP) tasks and bench-
marks such as machine translation (MT) (Moslem
et al., 2023; Jiao et al., 2023), human evaluation of
MT (Kocmi and Federmann, 2023), sentence com-
pletion, and question answering (OpenAI, 2023).
The same can be said for some programming lan-
guage processing (PLP) tasks, such as code gen-
eration (OpenAI, 2023) and code translation (Pan
et al., 2023), but other tasks, such as code summa-
rization, have proven to be difficult for LLMs (Sun
et al., 2023). These tasks requiring code under-
standing pose challenges distinct from those faced
in natural language. As an example, a unique chal-
lenge in PLP is the rigidity of syntax and semantic
precision required in generation or translation that
is not required to the same degree in NLP. Solving
these problems, or at least improving their solu-
tions, has the potential to greatly increase produc-
tivity and satisfaction in software development, as
```

<a id="documentation-llm-understanding-003"></a>
## documentation-llm-understanding-003 — Introduction: documentation hypothesis

Source: [physical PDF page 1](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=1); reading unit `p001`, lines 48–72.

Attribution: William Macke and Michael Doyle; cited authors retain their explicitly named positions, including Pritchard on understanding in section 3

Context: Paper section in source order; linked records preserve continuation and experimental context.

Related: [documentation-llm-understanding-002](#documentation-llm-understanding-002), [documentation-llm-understanding-004](#documentation-llm-understanding-004)

```text
has already been shown with the use of GitHub
Copilot (Kalliamvakou, 2022).
While several works have shown the importance
of applying effective prompting strategies for PLP
with LLMs (Le et al., 2023; Wang et al., 2022;
Shinn et al., 2023), very little work has investigated
how the reliability of the documentation at input
can affect an LLM’s performance. In this work,
we provide a preliminary empirical analysis of how
documentation quality can influence this ability.
We hypothesize that correct code documentation
will improve an LLM’s code understanding, and
that its understanding will decrease as the preva-
lence and accuracy of the documentation is de-
creased. To the authors’ knowledge this is the first
work to consider code documentation reliability for
this problem.
The rest of the paper is organized as follows:
First we discuss other works and how they relate to
our study. Then we present experimental analysis
and results. Our experiments provide a basic anal-
ysis of how an LLM’s code understanding perfor-
mance degrades along with documentation quality
and quantity, and we end with a discussion and
analysis of the results.
```

<a id="documentation-llm-understanding-004"></a>
## documentation-llm-understanding-004 — Related work: static analysis and language models

Source: [physical PDF page 1](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=1); reading unit `p001`, lines 73–86.

Attribution: William Macke and Michael Doyle; cited authors retain their explicitly named positions, including Pritchard on understanding in section 3

Context: Paper section in source order; linked records preserve continuation and experimental context.

Related: [documentation-llm-understanding-003](#documentation-llm-understanding-003), [documentation-llm-understanding-005](#documentation-llm-understanding-005)

```text
2 Related Works
Code analysis is a very well-studied problem. Tra-
ditional compilers and syntax-tree parsers are com-
monly used to perform code analysis (Moor et al.,
2007; Lenarduzzi et al., 2020) or extract code met-
rics (McCabe, 1976; Timóteo et al., 2008; Agni-
hotri and Chug). However, these tools lack an
LLM’s ability to process natural language, and
therefore are incapable of extracting semantic un-
derstanding or considering code documentation.
Since LLMs have become widely available, many
works have also attempted to leverage language
models to analyze code. Several works have sought
to create LLMs designed for code understanding
```

<a id="documentation-llm-understanding-005"></a>
## documentation-llm-understanding-005 — Related work: code-analysis evaluations

Source: [physical PDF page 2](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=2); reading unit `p002`, lines 1–28.

Attribution: William Macke and Michael Doyle; cited authors retain their explicitly named positions, including Pritchard on understanding in section 3

Context: Paper section in source order; linked records preserve continuation and experimental context.

Related: [documentation-llm-understanding-004](#documentation-llm-understanding-004), [documentation-llm-understanding-006](#documentation-llm-understanding-006)

```text
tasks such as code generation, code completion,
program repair, and code translation (Xia et al.,
2022; Wang et al., 2023b; Bui et al., 2023). Unlike
these works, instead of developing new tools we
provide a rigorous analysis of where and how ex-
isting tools can best be leveraged. Our work also
introduces other means of determining code under-
standing than the benchmarks developed in Lu et al.
(2021).
Other works provided empirical analyses of ex-
isting models’ abilities to analyze code. Xu et al.
(2022) present an analysis of the performance of
various LLMs on different code benchmarks, and
introduce a new LLM. Ma et al. (2023) present an
empirical analysis of using GPT to generate syntax
trees, call graph and other syntactic and semantic
representations of code. They conclude that GPT
has approximately the same abilities as an abstract
syntax tree (AST) parser. Similarly Palacio et al.
(2023) introduce a framework called ASTxplainer
that uses questions about an AST as an evaluation
criteria for LLMs. Leinonen et al. (2023) provide
an empirical study comparing human generated
explanations with those generated by GPT. All of
these works are focused on evaluating an LLMs
performance in general and, unlike this work, none
investigate how code content or documentation can
effect an LLM’s understanding.
```

<a id="documentation-llm-understanding-006"></a>
## documentation-llm-understanding-006 — Defining code understanding

Source: [physical PDF page 2](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=2); reading unit `p002`, lines 29–61.

Attribution: William Macke and Michael Doyle; cited authors retain their explicitly named positions, including Pritchard on understanding in section 3

Context: Paper section in source order; linked records preserve continuation and experimental context.

Related: [documentation-llm-understanding-005](#documentation-llm-understanding-005), [documentation-llm-understanding-007](#documentation-llm-understanding-007)

```text
3 LLM Code Understanding
It has been argued that understanding is merely
the “knowledge of causes” (Pritchard, 2014), but
one can see that this is an incomplete definition of
what it means to truly understand something and
that “a proper explanatory grip on how cause and
effect are related” (Pritchard, 2016) is required for
true understanding. Nevertheless, the knowledge of
causes is at least a crucial early step in developing
a complete understanding of a topic.
If this is the basic definition we are using for
our basis of determining understanding, then to
truly assess whether a piece of code is understood
by a person or a language model, then the subject
must display knowledge of the cause and effect
relationship of the code. Or, to put more simply,
the subject should be able to answer the question,
“What does this piece of code do?”
Past work has attempted to test an LLM’s ability
to answer this question through code translation by
measuring errors in the target language (Pan et al.,
2023); through code summarization by measur-
ing differences in BLEU, METEOR, or ROUGE-L
scores between an LLM-generated summarization
and the reference summarization (Sun et al., 2023);
and through the generation of unit tests by mea-
suring statement and branch coverage across vari-
ous JavaScript libraries (Schäfer et al., 2023). Our
approach for testing an LLM’s understanding of
source code is most closely related to the latter-
most method, but differs by not improving upon
the initial attempt at unit test generation iteratively
if the tests fail.
```

<a id="documentation-llm-understanding-007"></a>
## documentation-llm-understanding-007 — Input-output prediction and documentation

Source: [physical PDF page 2](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=2); reading unit `p002`, lines 62–88.

Attribution: William Macke and Michael Doyle

Context: Paper section in source order; linked records preserve continuation and experimental context.

Related: [documentation-llm-understanding-006](#documentation-llm-understanding-006), [documentation-llm-understanding-008](#documentation-llm-understanding-008)

```text
In many cases, a program can be represented as
a mapping from inputs into outputs (Solar-Lezama,
2009). For example, the program square(n) can
be described with square(1) = 1 ,square(2) =
4,... etc. Unsurprisingly then, how well an indi-
vidual can predict input-output pairs can serve as
a very useful surrogate metric for how well an in-
dividual understands a piece of code. After all,
someone cannot truly understand software with-
out being able to predict the software’s behavior.
Module documentation, function docstrings, inline
code comments, and variable names provide hints
or detailed descriptions of what the user can expect
of these input-output pairs, and often allow human
users to better predict that behavior.
Modern unit test frameworks provide both a for-
mal language for describing input-output pairs and
an easily automated method of checking an LLM’s
output. In order to measure an LLM’s ability to
generate these input-output pairs, we therefore task
the LLM with generating unit tests for a piece of
software while varying the quality or quantity of
the documentation at input, as well as other code
properties. We then measure the percent of unit
tests that pass vs the number that fail or produce
an error as the percent of correctly predicted input-
output pairs.
```

<a id="documentation-llm-understanding-008"></a>
## documentation-llm-understanding-008 — Experimental setup and test outcome definitions

Source: [physical PDF page 2](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=2); reading unit `p002`, lines 89–100.

Attribution: William Macke and Michael Doyle

Context: Paper section in source order; linked records preserve continuation and experimental context.

Related: [documentation-llm-understanding-007](#documentation-llm-understanding-007), [documentation-llm-understanding-009](#documentation-llm-understanding-009)

```text
4 Experimental Setup
In the following section we describe our experi-
mental process for testing an LLM’s ability to un-
derstand code well enough to produce successful
unit tests. In particular, we present an experimental
setup for testing the generation of unit tests under
varying initial documentation conditions.
To test an LLM’s ability to understand a piece of
software, we task the language model to generate
unit tests. We then run the unit tests and record
each test as 1 of 3 results: Runtime Error, where
a unit test crashed before it could finish running;
```

<a id="documentation-llm-understanding-009"></a>
## documentation-llm-understanding-009 — Experimental setup: outcomes, dataset and postprocessing

Source: [physical PDF page 3](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=3); reading unit `p003`, lines 1–21.

Attribution: William Macke and Michael Doyle

Context: Paper section in source order; linked records preserve continuation and experimental context.

Related: [documentation-llm-understanding-008](#documentation-llm-understanding-008), [documentation-llm-understanding-010](#documentation-llm-understanding-010)

```text
Failure, where a unit test ran but failed to pass;
and Success, where a unit test ran and successfully
passed. All LLMs used their default parameters
during experiments.
We use all 164 HumanEval (Chen et al., 2021)
ground truth solutions as our basis for generating
unit tests. 1 We chose HumanEval both for its
common use as an LLM benchmark for code un-
derstanding (Hong et al., 2023; Zelikman et al.,
2023; Wang et al., 2023a) (although intended for
text-to-code generation), and for its wide variety of
self encapsulated functions that can be easily run
within unit test frameworks. We perform several
post processing steps on the LLM generated code
to ensure it can run automatically. First, we remove
all import statements that result in an error (the
LLM will commonly import hallucinated modules
as it was not provided the original module names
at input). Second, we append the LLM’s code to a
file with the HumanEval function to ensure the unit
test has access to all code pieces required to run.
```

<a id="documentation-llm-understanding-010"></a>
## documentation-llm-understanding-010 — Documentation and naming interventions

Source: [physical PDF page 3](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=3); reading unit `p003`, lines 22–49.

Attribution: William Macke and Michael Doyle

Context: Paper section in source order; linked records preserve continuation and experimental context.

Related: [documentation-llm-understanding-009](#documentation-llm-understanding-009), [documentation-llm-understanding-011](#documentation-llm-understanding-011)

```text
We generate several automatic variations of each
function in the HumanEval dataset. Base File ,
which includes only the ground truth solution for a
HumanEval function with no docstring comments.
Comments, which is the base file but includes any
comments and the docstring provided for the Hu-
manEval function. The docstrings for HumanEval
functions typically contain a description of the func-
tion along with a few execution examples. Ran-
dom Comments which has the base file but with
a random comment or docstring from a different
HumanEval function, Animal Variable Names ,
which is the base file but with all variable and
(non-external) function names replaced with an-
imals (e.g. Bird, Cat, Dog etc.), and Random
Variable Names which is the base file but with all
variable and function names replaced with random
strings. For instance, a variableformat_str might be
changed to eMbafsd. In addition, we also investigate
how removing random portions of the docstrings,
line-by-line, can effect performance. Each line was
kept with uniform random probability. We evalu-
ate unit tests generated from 10%, 25%, 50% and
75% of the original docstrings remaining. To avoid
any infinite loops generated by the LLM, all tests
would automatically fail after taking more than 10
seconds to run. Figure 1 shows an example of a
function from the Comments category.
```

<a id="documentation-llm-understanding-011"></a>
## documentation-llm-understanding-011 — HumanEval example and coverage check

Source: [physical PDF page 3](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=3); reading unit `p003`, lines 50–73.

Attribution: William Macke and Michael Doyle

Context: Paper section in source order; linked records preserve continuation and experimental context.

Transcription/context notes: The reading text interposes a figure within prose; consult the physical page for layout and continue the surrounding sentence across the figure. Figure 1 is a code/docstring specimen; extraction loses Python indentation and inserts a footnote before the specimen.

Related: [documentation-llm-understanding-010](#documentation-llm-understanding-010), [documentation-llm-understanding-012](#documentation-llm-understanding-012)

```text
In order to determine that the LLMs are not gen-
1Available for use under the MIT license here.
def monotonic ( l : list ) :
""" Return True is list elements
are monotonically increasing
or decreasing .
>>> monotonic ([1 , 2 , 4 , 20])
True
>>> monotonic ([1 , 20 , 4 , 10])
False
>>> monotonic ([4 , 1 , 0 , -10])
True
"""
if l == sorted ( l ) or \
l == sorted (l , reverse = True ) :
return True
return False
Figure 1: Example HumanEval reference implementa-
tion with docstring.
erating trivial tests, we also conduct an analysis of
how much of the source code is executed by the
generated unit tests. We use line coverage, or the
percent of lines in the source code that are executed
by the unit tests, as our metric for this analysis.
```

<a id="documentation-llm-understanding-012"></a>
## documentation-llm-understanding-012 — Results: runtime errors, random comments and variable names

Source: [physical PDF page 3](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=3); reading unit `p003`, lines 74–100.

Attribution: William Macke and Michael Doyle

Context: Paper section in source order; linked records preserve continuation and experimental context.

Related: [documentation-llm-understanding-011](#documentation-llm-understanding-011), [documentation-llm-understanding-013](#documentation-llm-understanding-013)

```text
5 Results
Figure 2 shows the results of GPT-3.5 ( gpt-3.5-
turbo) and GPT-4 generating unit tests on the varia-
tions of the HumanEval dataset discussed above. 2
There are several key things to note from these re-
sults. First the number of runtime errors produced
by GPT-3.5 is much greater than those produced
by GPT-4, as is consistent with many results for
similar code understanding tasks (OpenAI, 2023).
A manual examination of the generated test cases
shows that GPT-3.5 often generated simple assert
statements rather than using pytest, and many of
the runtime errors were caused by assert statements
failing. Second, we note that the random comments
scenario performs worse than any other scenario
on both GPT-3.5 and 4 (only 22.1% and 68.1%
successes respectively) as shown in Figure 2, con-
firming our hypothesis that incorrect documenta-
tion can hurt an LLM’s understanding of a piece
of code. A statistical bootstrap shows that ran-
dom comments have a higher proportion of runtime
errors and failed tests than any other version of
the code by a statistically significant margin with
α= 0.05. Thirdly, we note that changing the code
content (via variable names), had a relatively mi-
nor effect on the LLM’s code understanding when
compared with the base file. A bootstrap shows
```

<a id="documentation-llm-understanding-013"></a>
## documentation-llm-understanding-013 — Results: names, comments and partial comments

Source: [physical PDF page 4](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=4); reading unit `p004`, lines 1–29.

Attribution: William Macke and Michael Doyle

Context: Paper section in source order; linked records preserve continuation and experimental context.

Related: [documentation-llm-understanding-012](#documentation-llm-understanding-012), [documentation-llm-understanding-014](#documentation-llm-understanding-014)

```text
that changing variables to random names did not
impact the proportion of errors and failed tests by
a statistically significant margin, but changing the
variables to animals did cause a statistically signifi-
cant change (albeit a small one of 44.7% to 40.6%
successes for GPT-3.5 and 78.5% to 76.6% for
GPT-4). Finally, having comments did notsignifi-
cantly increase the LLM’s ability to understand the
code. Again a bootstrap confirms the proportion of
errors and failed tests did not change between the
base file with/without comments by a statistically
significant margin.
As mentioned above, we also conducted exper-
iments to determine how partial comments might
affect an LLM’s ability to understand code. Fig-
ure 3 shows these results. GPT-3.5 shows that
providing partial comments causes an initial spike
in the number of errors, before declining as the per-
centage of comments kept increases. GPT-4 does
not show the same pattern, however a bootstrap
shows that having the full amount of comments
gave fewer errors over when the proportion of kept
comments was 10%, 25% and 50% by statistically
significant margin. As shown in the figure, these
changes were relatively minor. No other compar-
isons were statistically significant for GPT-4. We
therefore cannot currently conclude whether or not
partial comments can significantly hurt an LLM’s
code understanding based on the current evidence.
```

<a id="documentation-llm-understanding-014"></a>
## documentation-llm-understanding-014 — Results: line coverage and exceptions

Source: [physical PDF page 4](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=4); reading unit `p004`, lines 30–52.

Attribution: William Macke and Michael Doyle

Context: Paper section in source order; linked records preserve continuation and experimental context.

Related: [documentation-llm-understanding-013](#documentation-llm-understanding-013), [documentation-llm-understanding-015](#documentation-llm-understanding-015)

```text
Finally, we conducted an analysis of line cover-
age by unit tests to prevent the possibility of the
LLM producing trivial tests to gain a higher suc-
cess rate. This is shown in Figures 4 and 5. First, it
is worth noting that the results with random com-
ments had lower average code coverage than all
other methods by a statistically significant margin.
Second, we note that for both GPT-3.5 and GPT-4,
code with comments generated a higher average
line coverage than all other methods by a statis-
tically significant margin. Thirdly, we note that
modifying the variables names of the code largely
did not have a statistically significant effect. The
one exception was the animal names category gen-
erated by GPT-3.5, which had an average amount of
line coverage that was significantly lower than the
line coverage of unit tests generated from the base-
line, as seen in Figure 4. Finally, partial docstrings
mostly did not have a statistically significant effect
on the average amount of line coverage. There was
one exception when 10% of the docstring was kept
for GPT-3.5, which did worse than the baseline by
a statistically significant margin.
```

<a id="documentation-llm-understanding-015"></a>
## documentation-llm-understanding-015 — Figures 2 and 3: failure and error proportions

Source: [physical PDF page 4](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=4); reading unit `p004`, lines 53–86.

Attribution: William Macke and Michael Doyle

Context: Paper section in source order; linked records preserve continuation and experimental context.

Transcription/context notes: Plot labels/captions are retained, but bar heights are not numerical transcriptions; see the original figures on this physical page.

Related: [documentation-llm-understanding-014](#documentation-llm-understanding-014), [documentation-llm-understanding-016](#documentation-llm-understanding-016)

```text
Base FileComments
Random Comments
Animal NamesRandom Names
0.0
0.2
0.4
0.6
0.8
GPT-3.5
Base FileComments
Random Comments
Animal NamesRandom Names
GPT-4
T est Failures
Runtime Errors
Figure 2: Proportion of runtime errors or failed tests that
happen with GPT-3.5 (left) and GPT-4 (right) generating
unit tests on modified versions of HumanEval code.
0 0.1 0.25 0.5 0.75 1
Proportion Docstring Kept
0.0
0.2
0.4
0.6
GPT-3.5
0 0.1 0.25 0.5 0.75 1
Proportion Docstring Kept
GPT-4
T est Failures
Runtime Errors
Figure 3: Proportion of runtime errors or failed tests that
happen with GPT-3.5 (left) and GPT-4 (right) generating
unit tests on different proportions of docstring lines kept
on HumanEval code.
```

<a id="documentation-llm-understanding-016"></a>
## documentation-llm-understanding-016 — Test counts and conclusions

Source: [physical PDF page 4](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=4); reading unit `p004`, lines 87–110.

Attribution: William Macke and Michael Doyle

Context: Paper section in source order; linked records preserve continuation and experimental context.

Related: [documentation-llm-understanding-015](#documentation-llm-understanding-015), [documentation-llm-understanding-017](#documentation-llm-understanding-017)

```text
We also provide the number of unit tests gen-
erated by models for various conditions. Table 1
shows the number of test cases created by GPT-3.5
and GPT-4 for each of the file categories mentioned
above. Table 2 shows the number of tests generated
by GPT-3.5 and GPT-4 with various portions of the
HumanEval docstring lines dropped.
6 Conclusions and Discussion
In this paper, we introduce the effect of code docu-
mentation on LLM code understanding and show
in our initial experiments that the relative preva-
lence of documentation has little to no significant
effect on an LLM’s understanding as we have de-
fined it. This is a little complicated by the fact that
we found no significant difference in the amount of
successful unit tests but did see a significant differ-
ence in the code coverage of those unit tests. Even
when comparing commented code to code without
comments and all of the variable names changed
to random characters, we find little to no signif-
icant difference in the LLM’s ability to generate
successful unit tests. So, although more of the code
with comments is being covered by the unit tests
than the code without, this does not improve the
```

<a id="documentation-llm-understanding-017"></a>
## documentation-llm-understanding-017 — Tables 1 and 2 and Figure 4

Source: [physical PDF page 5](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=5); reading unit `p005`, lines 1–24.

Attribution: William Macke and Michael Doyle

Context: Paper section in source order; linked records preserve continuation and experimental context.

Transcription/context notes: Plot labels/captions are retained, but bar heights are not numerical transcriptions; see the original figures on this physical page.

Related: [documentation-llm-understanding-016](#documentation-llm-understanding-016), [documentation-llm-understanding-018](#documentation-llm-understanding-018)

```text
Model Basefile Comments Random Comments Random Names Animal Names
GPT-3.5 1323 883 892 1464 1482
GPT-4 3832 3295 2324 3725 3589
Table 1: Number of tests generated by models under variations of HumanEval files.
Model p = 0 p = 0.1 p = 0.25 p = 0.50 p = 0.75 p = 1
GPT-3.5 1323 958 929 893 908 883
GPT-4 3832 3596 3446 3198 3335 3295
Table 2: Number of tests generated by models with proportions of dropped comment lines within HumanEval files.
Base FileComments
Random Comments
Animal NamesRandom Names
0
20
40
60
80Unit T est Line Coverage
GPT-3.5
Base FileComments
Random Comments
Animal NamesRandom Names
GPT-4
Figure 4: Average percent of line coverage with GPT-
3.5 (left) and GPT-4 (right) generating unit tests on
modified versions of HumanEval code.
```

<a id="documentation-llm-understanding-018"></a>
## documentation-llm-understanding-018 — Discussion: coverage, success and possible explanations

Source: [physical PDF page 5](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=5); reading unit `p005`, lines 25–43.

Attribution: William Macke and Michael Doyle

Context: Paper section in source order; linked records preserve continuation and experimental context.

Related: [documentation-llm-understanding-017](#documentation-llm-understanding-017), [documentation-llm-understanding-019](#documentation-llm-understanding-019)

```text
overall unit test success rate. This suggests that
the LLM is better at understanding the different
execution paths of the code, but this may make the
creation of a successful unit test more difficult. Al-
ternatively, we do show that incorrect comments do
significantly affect an LLM’s ability to understand
a piece of code.
It is possible that in much of the training data
used to train the OpenAI models tested in this study,
the code did not contain many comments or doc-
umentation. As such, it may be possible that a
model’s ability to utilize comments is dependent
on how much of this documentation is in the train-
ing data, and other non-OpenAI LLM’s may make
better or worse use of the information provided. It
is also possible that correct comments do not add
much information as it would be relevant to the
creation of unit tests, but incorrect comments still
confuse the LLMs.
```

<a id="documentation-llm-understanding-019"></a>
## documentation-llm-understanding-019 — Limitations and Figure 5

Source: [physical PDF page 5](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=5); reading unit `p005`, lines 44–64.

Attribution: William Macke and Michael Doyle

Context: Paper section in source order; linked records preserve continuation and experimental context.

Transcription/context notes: The reading text interposes a figure within prose; consult the physical page for layout and continue the surrounding sentence across the figure. Plot labels/captions are retained, but bar heights are not numerical transcriptions; see the original figures on this physical page.

Related: [documentation-llm-understanding-018](#documentation-llm-understanding-018), [documentation-llm-understanding-020](#documentation-llm-understanding-020)

```text
7 Limitations
While we do introduce a new research question
to the space of LLM code understanding, we rec-
ognize that this is a limited test that is missing a
broader comparison study between programming
languages, models, prompting techniques, hyper-
parameters, and input documentation modification,
0 0.1 0.25 0.5 0.75 1
Proportion Docstring Kept
0
20
40
60
80Unit T est Line Coverage
GPT-3.5
0 0.1 0.25 0.5 0.75 1
Proportion Docstring Kept
GPT-4
Figure 5: Average percent of line coverage with GPT-3.5
(left) and GPT-4 (right) generating unit tests on different
proportions of docstring lines kept on HumanEval code.
```

<a id="documentation-llm-understanding-020"></a>
## documentation-llm-understanding-020 — Limitations continued and future work

Source: [physical PDF page 5](../../../ai-code-comments/2024-code-documentation-and-llm-understanding.pdf#page=5); reading unit `p005`, lines 65–88.

Attribution: William Macke and Michael Doyle

Context: Paper section in source order; linked records preserve continuation and experimental context.

Related: [documentation-llm-understanding-019](#documentation-llm-understanding-019)

```text
and that this paper represents merely an introduc-
tion to the idea of documentation’s effects on LLM
code understanding. In addition, since OpenAI’s
training data is not publicly available, there is a
small but real possibility that the training data may
contain the HumanEval dataset, in which case these
results would be invalid.
In future work, we believe that more comprehen-
sive tests should be done by including examples of
more complex code and documentation (such as
that found in ClassEval (Du et al., 2023)). These
tests could be evaluated while simultaneously see-
ing the affect of and controlling for code complex-
ity using metrics such as cyclomatic complexity
or maintainability index (McCabe, 1976; Coleman
et al., 1994). We also recommend evaluating unit
test success rate while controlling for code cover-
age to properly isolate and determine good success
metrics.
Finally, this same research question could be
evaluated using code summarization as the code
understanding task, because it still measures how
well the LLM attempts to answer “What does this
piece of code do?”
```
