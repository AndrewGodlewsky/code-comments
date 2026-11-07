# Distillation: Historical practice (1947-1986)

Sources read:

- `planning-and-coding/passages.md` (Goldstine and von Neumann, 1947; ~73k words of OCR). Read in full: the preface (001-002), chapter 7 method sections on dynamic coding, assertion and substitution boxes, coding stages and the explanatory column (003-007, 014-025, 161), the explanatory-column omission and "no further comments" transcriptions (162, 163), correcting and changing coded sequences (043-045), the Volume II introductory remark and the integration-method choice (072-076), the start of the 10.9 change example (114-115), and chapter 12 on subroutine assumptions, conventions, deviations and reuse (138-147, 157-160). Skimmed by heading and keyword search: the remaining worked examples (026-042, 046-071, 077-113, 116-137, 148-156), which are mostly mathematics, storage tables and OCR-damaged code columns.
- `fortran-1956/passages.md` (IBM 704 manual): all 8 passages, in full.
- `literate-programming/passages.md` (Knuth, 1984 preprint): all 15 passages. Read 001-005 and 008-015 in full, 006-007 at a skim (index and WEB source specimens).
- `rational-design-process/passages.md` (Parnas and Clements, 1986): all 12 passages, in full (011-012 are references).
- `docs/research/historical-comment-design.md` (synthesis report): in full. Cited only for interpretation; primary passages are preferred.
- `docs/research/comment-context/README.md`: scope and limits sections for these four sources.

Evidence note. Nothing in this group is empirical. Parnas and Clements, and Knuth, give expert opinion backed by their own project experience. Knuth calls his claims personal and warns readers to discount them. Goldstine and von Neumann prescribe a method and demonstrate it on worked examples. The FORTRAN manual records practice in specimens. Their "explanation" lives mostly **outside** executable text: in flow diagrams, assertion boxes, parallel explanatory columns, separate design documents, manual prose and woven typeset documents. Each transfer to inline comments edited by AI agents is a hypothesis.

## Candidate principles

### HIS-01 — Explain intent and rationale that the code cannot show
- **Principle:** When you write or change code whose form depends on a decision, record why it takes that form. Do not record only what it does; the reason is what a later editor cannot recover from the code.
- **Kind:** what
- **Sources:**
  - [rational-design-process-001](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-001) — supports — "They make a long sequence of design decisions with no clear statement of why they do things the way they do. Their rationale is rarely explained." — evidence: expert-opinion
  - [rational-design-process-007](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-007) — supports — "This document is designed to allow an efficient review of the design before the coding begins and to explain the intent behind the code" — evidence: expert-opinion
  - [literate-programming-001](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-001) — supports — "concentrate rather on explaining to human beings what we want a computer to do." — evidence: expert-opinion
  - [literate-programming-003](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-003) — supports — "The comments motivate and explain noteworthy features of the program text." — evidence: historical-practice
- **Conditions / limits:** Parnas puts intent in a separate *module design document*, not in code comments. Knuth's commentary is WEB prose woven into a typeset document, not ordinary inline comments. Both support recording intent. Neither supports putting it inline.
- **Tension:** HIS-05. Parnas wants intent written once, in documents, and the code kept free of redundant comments.
- **Testable as:** capture / recall (required rationale present in owner scope).

### HIS-02 — At a consequential choice, record the rejected alternative and why it lost
- **Principle:** When an attractive alternative was considered and rejected, say briefly at the choice what it was and why it lost. Include non-technical reasons when they decided it. A later editor may otherwise "improve" the code back to the rejected option.
- **Kind:** what
- **Sources:**
  - [rational-design-process-010](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-010) — supports — "recording all of the design alternatives that we considered and rejected. For each, we explain why it was considered and why it was finally rejected." — evidence: expert-opinion
  - [planning-and-coding-075](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-075) — supports — "the first method is about ... We will nevertheless code this Probletn according to the second method, because this offers a good opportunity to exemplify" — evidence: historical-practice
  - [literate-programming-003](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-003) — supports — "How should table p be represented? ... we could build an array of integers in which the kth entry is the kth prime number." — evidence: historical-practice
  - [literate-programming-005](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-005) — supports — "so that it will not be necessary to resort to a goto statement. (We are following Dijkstra,2 not Knuth.3)" — evidence: historical-practice
  - [historical-comment-design.md, "Candidate taxonomy to test"](../../research/historical-comment-design.md#candidate-taxonomy-to-test) — qualifies — "At the consequential choice; longer deliberation elsewhere." — evidence: expert-opinion
- **Conditions / limits:** Parnas records *all* alternatives, in external documents. Inline, that would be noise, so keep only the alternative a future editor would plausibly reach for. The von Neumann example matters because the choice was made against efficiency, for teaching. Without the note, a reader would "fix" it. Record an alternative only when the evidence shows it was really considered (HIS-12).
- **Tension:** HIS-03 (present a rationalized design) and HIS-07 (omit what the reader does not need). Parnas resolves the first: the rejected-alternatives record is his one stated exception to idealized documentation.
- **Testable as:** capture / recall and bad_claims (an invented "we considered X" counts as unsupported rationale).

### HIS-03 — Explain the design as it stands; leave the story of how it was found out
- **Principle:** Write the explanation as the account a reader needs of the current design. Do not narrate the path you took, or the earlier versions (for example "previously this used X, now Y", or "after debugging we found"). When a change alters the design, rewrite the explanation as if the new design had been the original.
- **Kind:** maintain
- **Sources:**
  - [rational-design-process-010](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-010) — supports — "Those who read the softwa re documentation want to unders tand the programs, not to relive their discovery." — evidence: expert-opinion
  - [rational-design-process-008](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-008) — supports — "If a change invalidates a design document, it and all subsequent design documents must be faked to look as if the change had been the original design." — evidence: expert-opinion
  - [rational-design-process-002](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-002) — supports — "what he wishes he had done, not what actually did happen." — evidence: expert-opinion
  - [literate-programming-011](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-011) — qualifies — "the decisions that Dijkstra made as he composed the original program2 appear in the WEB documentation in the same order." — evidence: historical-practice
- **Conditions / limits:** Rejected alternatives are the exception (HIS-02). Knuth keeps the *order of composition* because it is a good expository order, not a changelog. Version control now holds the chronology, which neither author had. That strengthens the case for keeping history out of comments. Parnas's "faking" assumes a reviewed, disciplined documentation process.
- **Tension:** HIS-02. Also Knuth, who treats composition order as a good reading order.
- **Testable as:** maintain / bad_claims (stale "previously..." text) and noise_lines (appended amendment notes instead of revision).

### HIS-04 — In the same edit, change every explanation the edit makes false
- **Principle:** Treat maintenance as redesign. When you change behaviour, find and revise every comment and cross-reference the change invalidates, including ones away from the edited lines. Do not leave correcting them for later.
- **Kind:** maintain
- **Sources:**
  - [rational-design-process-008](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-008) — supports — "Maintenance is just redesign and redevelopment." — evidence: expert-opinion
  - [rational-design-process-008](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-008) — supports — "If a change is made, all documentation that is invalidated must be changed." — evidence: expert-opinion
  - [planning-and-coding-045](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-045) — supports — "any refererres to 6 (which does not happen to be the case here), they have to be replaced by references to 36." — evidence: historical-practice
  - [rational-design-process-006](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-006) — qualifies — "If it is kept up-to-date, this document, which records our initial design decisions, will be useful as long as the software is used." — evidence: expert-opinion
  - [literate-programming-013](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-013) — qualifies — "it is therefore customary to work with hardcopy documentation that is slightly obsolete" — evidence: historical-practice
- **Conditions / limits:** The von Neumann case concerns machine addresses, not prose. It transfers as an analogy: when something moves, its references must follow. Knuth shows that even a single-source system tolerated stale *derived* output. Only the source was kept current.
- **Tension:** none found. All sources agree. Their mechanisms differ (documents, coded references, source).
- **Testable as:** maintain / bad_claims and preserved; audit / bad_claims.

### HIS-05 — Do not restate what the code or an owning document already says
- **Principle:** Before adding a comment, check whether the fact already has one authoritative home: the code itself, or a document the comment would duplicate. Duplicated facts drift apart and raise maintenance cost.
- **Kind:** avoid
- **Sources:**
  - [rational-design-process-008](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-008) — supports — "The code should not include comments that are redundant with the documentation that has already been written." — evidence: expert-opinion
  - [rational-design-process-009](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-009) — supports — "There must be one, and only one, place for every fact that will be in the document." — evidence: expert-opinion
  - [rational-design-process-009](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-009) — supports — "Certain facts are repeated in many different sections." — evidence: expert-opinion
  - [literate-programming-002](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-002) — qualifies — "its documentation are both generated from the same source, so they are consistent with each other." — evidence: expert-opinion
- **Conditions / limits:** Parnas assumes a complete, reviewed external documentation set. Where none exists, which is the project's motivating case, the comment may be the only home. Knuth avoids drift by deriving documentation and code from one source, not by removing explanation.
- **Tension:** HIS-18 and the product hypothesis in `intent.md`, which aims to replace some shared documents with inline explanation. Parnas would put the fact in the document and keep it out of the code.
- **Testable as:** restrain / noise_lines; maintain / bad_claims (duplicated text left stale).

### HIS-06 — Do not narrate execution step by step
- **Principle:** Do not write comments that walk through what each statement does in execution order. Explain what the reader cannot get by reading the statements.
- **Kind:** avoid
- **Sources:**
  - [rational-design-process-008](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-008) — supports — "writing describes the system in the order that things will happen when it runs." — evidence: expert-opinion
  - [rational-design-process-009](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-009) — supports — "Lots of words are used to say what could be said by a single programming language statement, a formula or a diagram." — evidence: expert-opinion
  - [planning-and-coding-163](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-163) — supports — "The actual coding obtains from this without a need for further comments." — evidence: historical-practice
  - [planning-and-coding-161](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-161) — opposes — "It is advisable to parallel it with another, explanatory, column, which shows for each order the effect of the substitution that it causes." — evidence: historical-practice
  - [fortran-1956-005](../../research/comment-context/sources/fortran-1956/passages.md#fortran-1956-005) — qualifies — "Next the DO statement sets I to 2 and creates a loop starting with the IF and ending with the CONTINUE." — evidence: historical-practice
- **Conditions / limits:** The von Neumann per-order explanatory column is real counter-practice. It served unreadable, self-modifying machine code. They dropped it once the final code was fixed (planning-and-coding-162). It does **not transfer** to readable high-level code. The FORTRAN narration is manual prose for learners, not source comments.
- **Tension:** planning-and-coding-161 (per-instruction explanation) against Parnas. It resolves by medium and audience, not by principle.
- **Testable as:** restrain / noise_lines; capture / noise_lines.

### HIS-07 — Leave out what the reader can easily keep in mind
- **Principle:** Explain only what would strain a capable reader to reconstruct or remember. Leave out what is evident from adjacent code. Where a property is not obvious, give at least an indication of why it holds.
- **Kind:** when
- **Sources:**
  - [planning-and-coding-020](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-020) — supports — "wi II not impose a real strain on the reader, due to the annunt of impl icitly given rrøterial that he rust rerrerr,ber." — evidence: expert-opinion
  - [planning-and-coding-161](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-161) — supports — "hence they require no explanation." — evidence: historical-practice
  - [planning-and-coding-020](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-020) — supports — "if this derronstration is not canpletely obvious, then it is desirable to give indicat ions as to its nature" — evidence: expert-opinion
  - [literate-programming-012](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-012) — supports — "so that a reader can grasp what is happening without being overwhelmed with detail" — evidence: expert-opinion
- **Conditions / limits:** The von Neumann criterion governs omissions in flow-diagram storage fields (OCR text; the meaning is clear from context). Applying it to comments is an analogy. "Capable reader" needs calibration for agents: a model may hold more context than a human but lacks the project's tacit knowledge (HIS-17).
- **Tension:** HIS-17 (the newcomer needs the major decisions spelled out). Knuth's heavy commentary (HIS-21) sits at the other end.
- **Testable as:** restrain / noise_lines; capture / recall (whether the threshold is set too high).

### HIS-08 — State an invariant or assumption where the code depends on it
- **Principle:** When correctness depends on a relation that holds at a particular point (a loop invariant, an ordering, a bound), state it at that point. Put it on the variable or line that relies on it.
- **Kind:** where
- **Sources:**
  - [literate-programming-005](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-005) — supports — "square ← p[ord] ∗ p[ord]; { at this point ord ≤ k }" — evidence: historical-practice
  - [literate-programming-005](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-005) — supports — "For 2 ≤ n < ord, mult [n] is an odd multiple of pn such that mult [n] < j + 2pn." — evidence: historical-practice
  - [literate-programming-004](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-004) — supports — "j: integer; { all primes ≤ j are in table p }" — evidence: historical-practice
  - [planning-and-coding-019](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-019) — supports — "it ind icates only that certain relat ions are atto-rat ical ly fulfi led whenever C gets to the region which it occupies." — evidence: expert-opinion
  - [planning-and-coding-021](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-021) — supports — "are purely explaratory, and require no coding" — evidence: expert-opinion
- **Conditions / limits:** The von Neumann assertion boxes are diagram elements, not text in the code (README scope note). Knuth's variable comments are the closest specimen to modern inline comments in this group. Where an assertion or type can carry the property in code, that may be the better home. These sources do not weigh that choice.
- **Tension:** none found.
- **Testable as:** capture / recall and misplaced (invariant explained away from its owner).

### HIS-09 — For a long justification, point to the argument instead of reproducing it
- **Principle:** When the argument behind a property is long or external (a theorem, a specification, a design record), state the property locally and name where the argument lives.
- **Kind:** where
- **Sources:**
  - [planning-and-coding-020](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-020) — supports — "sorp reference to the place where the proof can be found ney be made" — evidence: expert-opinion
  - [literate-programming-005](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-005) — supports — "Advanced books on number theory come to our rescue by showing that much more is true" — evidence: historical-practice
  - [historical-comment-design.md, "Tensions the skill should preserve"](../../research/historical-comment-design.md#tensions-the-skill-should-preserve) — qualifies — "An inline note can be encountered during an edit; some explanations require a larger reading order." — evidence: expert-opinion
- **Conditions / limits:** The reference must be stable and must exist. An agent should not cite a document or proof it has not seen (HIS-12).
- **Tension:** HIS-18 (keep explanation in the source). Pointing outward re-creates the separate-document problem the product targets.
- **Testable as:** capture / misplaced (whether the local statement survives when the detail is external); otherwise not covered by comment-edit.

### HIS-10 — Explain the behaviour that actually runs, not the form written in the source
- **Principle:** Where what executes differs from what the text shows (generated, substituted, overridden or configured behaviour), attach the explanation to the effective behaviour. Say what actually controls execution.
- **Kind:** where
- **Sources:**
  - [planning-and-coding-161](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-161) — supports — "is clearly the one which will actually control the functioning of the machine, and it is the one to which the explanation should be attached." — evidence: expert-opinion
  - [planning-and-coding-006](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-006) — supports — "is not the orig inal ( init appear-arce of that sequence, but rather its funct ioning and cont inued changing" — evidence: expert-opinion
- **Conditions / limits:** **Weak transfer.** The source case is self-modifying machine code, which is rare today. It might extend to code generation, decorators, monkeypatching or configuration overrides, but these sources do not test that. Kept as a low-confidence candidate.
- **Tension:** none found.
- **Testable as:** not covered by comment-edit unless a case plants an override.

### HIS-11 — Record input and environment assumptions, with the condition that breaks them
- **Principle:** When code relies on an assumption about its inputs, environment or usage (ordering, typical distribution, format, caller conventions), state it. Where the evidence shows it, also state when the assumption stops holding.
- **Kind:** what
- **Sources:**
  - [fortran-1956-005](../../research/comment-context/sources/fortran-1956/passages.md#fortran-1956-005) — supports — "The programmer anticipates that BIGA will usually be greater than A(I), a plausible guess if the A(1) are randomly arranged but not if they tend to increase with increasing I." — evidence: historical-practice
  - [fortran-1956-004](../../research/comment-context/sources/fortran-1956/passages.md#fortran-1956-004) — supports — "that the indexing of the loop bringing in A will work correctly, since the indexing parameter N occurs earlier in the list." — evidence: historical-practice
  - [planning-and-coding-138](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-138) — supports — "it led fro-n certain unambiguously stated assumptions to a clearly" — evidence: expert-opinion
  - [planning-and-coding-144](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-144) — supports — "coded in confomity with the (not a priori necessary) conventions" — evidence: expert-opinion
- **Conditions / limits:** In the FORTRAN manual, these assumptions appear in the manual's prose, not in the program's comment cards, which state only the purpose (fortran-1956-007). The source therefore shows the kind of knowledge worth keeping, not inline placement.
- **Tension:** none found.
- **Testable as:** capture / recall.

### HIS-12 — Do not present inference as fact: hedge what you cannot verify, or leave it out
- **Principle:** If the evidence does not establish a reason, do not write one as fact. Either mark it as an inference with a hedge the reader can see, or leave it out and report the gap. If a needed fact is genuinely unknown, say so where it belongs rather than fill the gap.
- **Kind:** agent
- **Sources:**
  - [fortran-1956-005](../../research/comment-context/sources/fortran-1956/passages.md#fortran-1956-005) — supports — "Notice that an extra column is allotted to BIGA to allow for the decimal point, which was presumably omitted in the data input." — evidence: historical-practice
  - [rational-design-process-010](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-010) — supports — "If a piece of informatio n is unavailable, that fact is noted in the part of the document where the informa tion should go" — evidence: expert-opinion
  - [historical-comment-design.md, "Do not turn inference into history"](../../research/historical-comment-design.md#do-not-turn-inference-into-history) — supports — "Without supporting evidence, the new sentence manufactures an explanation." — evidence: expert-opinion
- **Conditions / limits:** The historical authors explained their *own* code. An agent explaining someone else's code faces a fabrication risk these authors did not face. The synthesis example is invented for illustration. Writing "unknown" markers inline can become noise; reporting the gap outside the code may be better (see Conflicts).
- **Tension:** HIS-01 and HIS-02 push toward writing rationale. This principle restricts it to evidence.
- **Testable as:** capture / bad_claims (planted plausible-but-unsupported rationale).

### HIS-13 — Flag where the code departs from the design, the convention or the expected pattern
- **Principle:** When the implementation departs from the evident design, a local convention or the pattern a reader expects (an extra step, a nonstandard control path, a broken convention), say so where it happens and why. Readers predict from the pattern, so an unflagged departure is where they go wrong.
- **Kind:** when
- **Sources:**
  - [planning-and-coding-147](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-147) — supports — "not shown in the flow diagram, will appear in our coding." — evidence: historical-practice
  - [planning-and-coding-146](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-146) — supports — "we will encounter deviations and cornplications which should be ccmnented" — evidence: expert-opinion
  - [literate-programming-012](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-012) — supports — "the name of a section should explicitly mention any nonstandard control structures, even though its data structures can often be left implied." — evidence: expert-opinion
  - [planning-and-coding-144](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-144) — qualifies — "seem necessary to discuss at this place possible deviations frcxn these conventions" — evidence: expert-opinion
- **Conditions / limits:** The von Neumann deviations are from a flow diagram that sits beside the code. The modern analogue is a departure from a documented design or sibling code. They also skip some deviations they judge simple. Knuth's advice concerns WEB section names, which play the role of comments.
- **Tension:** HIS-07 (a trivial departure may not need a note).
- **Testable as:** capture / recall; restrain / noise_lines when the departure is trivial.

### HIS-14 — Keep interface comments to what callers may rely on
- **Principle:** In comments on an interface (signature, docstring, public type), state what callers may depend on and nothing about the implementation they must not. Put implementation rationale inside the implementation.
- **Kind:** what
- **Sources:**
  - [rational-design-process-007](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-007) — supports — "An interface specification for a module contains just enough information for the programmer of another module to use its" — evidence: expert-opinion
  - [rational-design-process-005](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-005) — supports — "(1) Every statement should be valid for all acceptable products; none should depend on implementation decisions." — evidence: expert-opinion
  - [historical-comment-design.md, "Tensions the skill should preserve"](../../research/historical-comment-design.md#tensions-the-skill-should-preserve) — supports — "Explain obligations between components without teaching every caller to depend on hidden representations." — evidence: expert-opinion
- **Conditions / limits:** The quote from rational-design-process-005 is about requirements documents. Applying it to interface comments is an analogy that Parnas's interface-specification passage supports. Parnas wrote formal specifications, not docstrings.
- **Tension:** HIS-11 (assumptions callers must meet do belong at the interface). This candidate excludes only implementation details.
- **Testable as:** capture / misplaced (rationale put at the interface instead of its owner).

### HIS-15 — Mark what must not change, and why
- **Principle:** When code contains a constraint that a plausible future change could break (a required order, a fixed format, a coupling), state the constraint and what depends on it. Then a future editor knows what must stay and what may change.
- **Kind:** what
- **Sources:**
  - [rational-design-process-010](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-010) — supports — "is used in describing what must be changed and what cannot be changed" — evidence: expert-opinion
  - [rational-design-process-006](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-006) — supports — "Programmers should not have to decide which changes are most likely." — evidence: expert-opinion
  - [fortran-1956-004](../../research/comment-context/sources/fortran-1956/passages.md#fortran-1956-004) — supports — "that the indexing of the loop bringing in A will work correctly, since the indexing parameter N occurs earlier in the list." — evidence: historical-practice
- **Conditions / limits:** Parnas means a requirements document's "likely changes" section, not inline notes. The FORTRAN ordering note is manual prose. The idea is consistent across the sources, but its placement in code comments is untested.
- **Tension:** HIS-07 (do not warn about what any reader would see).
- **Testable as:** capture / recall; downstream it would show as preserved constraints after later edits, which comment-edit does not measure.

### HIS-16 — Organize the explanation around the reader's question, not the writer's train of thought
- **Principle:** In a block or module comment, put each fact where a reader who needs it will look, phrased as the answer to their question. Do not record thoughts in the order they occurred to you.
- **Kind:** where
- **Sources:**
  - [rational-design-process-008](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-008) — supports — "subsequent readers cannot find the information that they seek." — evidence: expert-opinion
  - [rational-design-process-009](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-009) — supports — "Each document is designed by stating the questions that it must answer" — evidence: expert-opinion
  - [literate-programming-011](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-011) — qualifies — "task is to state those parts and those relationships, in whatever order is best for human comprehension" — evidence: expert-opinion
  - [literate-programming-011](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-011) — opposes — "programs in a “stream of consciousness” order." — evidence: expert-opinion
- **Conditions / limits:** Inline comments are placed by the code they annotate, so this mostly governs longer module, type or function headers. Knuth's "stream of consciousness" means the order of composition, which he considers a good reading order. Parnas means the order thoughts struck the writer. The disagreement is partly about words.
- **Tension:** Parnas (structured reference) against Knuth (expository narrative). See Conflicts.
- **Testable as:** capture / misplaced; otherwise not covered by comment-edit.

### HIS-17 — Write for a newcomer: record the major decisions insiders take for granted
- **Principle:** Assume the next reader is a capable newcomer with no memory of this work, as a fresh agent session is. Record the major decisions and the meaning of key names, not only the small details you fear forgetting.
- **Kind:** agent
- **Sources:**
  - [rational-design-process-009](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-009) — supports — "They document the small details that they think they will forget." — evidence: expert-opinion
  - [rational-design-process-009](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-009) — supports — "Unfortunately, the result is a document useful to people who know the system well but impenetrable for newcomers." — evidence: expert-opinion
  - [rational-design-process-009](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-009) — supports — "When new programmers join the project they do not have to depend completely on the old staff for their information." — evidence: expert-opinion
  - [literate-programming-001](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-001) — supports — "explains what each variable means" — evidence: expert-opinion
- **Conditions / limits:** "Myopia" describes documentation written late by long-time staff. An agent finishing a task is in a similar position: it has just built context that the next session will lack. That analogy is untested. Parnas offers no direct evidence of newcomer benefit; he cites a single A-7E document still in use.
- **Tension:** HIS-07 (the omission threshold depends on what the reader already knows).
- **Testable as:** capture / recall; the downstream newcomer effect is not covered by comment-edit.

### HIS-18 — Keep the explanation in the source that people edit, because separate copies lag
- **Principle:** Put explanation that must stay accurate in the artifact editors actually change, the source. Derived or separate descriptions fall behind it.
- **Kind:** where
- **Sources:**
  - [literate-programming-013](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-013) — supports — "it is therefore customary to work with hardcopy documentation that is slightly obsolete" — evidence: historical-practice
  - [literate-programming-002](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-002) — supports — "its documentation are both generated from the same source, so they are consistent with each other." — evidence: expert-opinion
  - [fortran-1956-003](../../research/comment-context/sources/fortran-1956/passages.md#fortran-1956-003) — supports — "Such cards may therefore be used to carry comments which will appear when the deck is listed." — evidence: historical-practice
  - [rational-design-process-008](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-008) — opposes — "The code should not include comments that are redundant with the documentation that has already been written." — evidence: expert-opinion
  - [historical-comment-design.md, "Knuth: explanation has an order of its own"](../../research/historical-comment-design.md#knuth-explanation-has-an-order-of-its-own) — qualifies — "Literate programming is consequently more than adding prose to an unchanged conventional source listing." — evidence: expert-opinion
- **Conditions / limits:** Knuth's single source is a WEB file that tooling weaves and tangles, and the paper says this is not the same as commenting Pascal (literate-programming-011, "even if the latter program is well commented"). Whether ordinary inline comments get the same benefit is exactly what the placement pilot must test.
- **Tension:** HIS-05 and Parnas generally, who put explanation in reviewed external documents.
- **Testable as:** not covered by comment-edit. This is the placement question for the pilot (#9).

### HIS-19 — Explain a constant by where it comes from and what it is tied to
- **Principle:** When a literal value comes from a derivation, a measurement or another value, state that source or link. Do not only restate the name. A later editor can then tell whether changing one value requires changing another.
- **Kind:** what
- **Sources:**
  - [literate-programming-005](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-005) — supports — "It turns out that ord never exceeds 30 when m = 1000." — evidence: historical-practice
  - [literate-programming-003](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-003) — supports — "so that the ﬁrst 1000 primes will appear on ﬁve pages" — evidence: historical-practice
  - [fortran-1956-005](../../research/comment-context/sources/fortran-1956/passages.md#fortran-1956-005) — supports — "Notice that an extra column is allotted to BIGA to allow for the decimal point, which was presumably omitted in the data input." — evidence: historical-practice
  - [literate-programming-003](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-003) — qualifies — "rr = 50; { this many rows will be on each page in" — evidence: historical-practice
- **Conditions / limits:** Knuth's inline constant comments (`{ this many rows... }`) mostly restate meaning, standing in for short Pascal names. The derivations sit in the surrounding commentary. Today a descriptive name may replace the restatement. The derivation still needs words.
- **Tension:** HIS-05 (a restating comment is redundant when the name already says it).
- **Testable as:** capture / recall; restrain / noise_lines for restating comments.

### HIS-20 — Add a purpose line to a substantial unit only when its name does not already say it
- **Principle:** A one-line statement of a unit's purpose was the oldest comment form. Add one to a substantial unit only when its name and signature do not already convey the purpose. Write it declaratively.
- **Kind:** when
- **Sources:**
  - [fortran-1956-007](../../research/comment-context/sources/fortran-1956/passages.md#fortran-1956-007) — supports — "PROGRAM FOR FINDING THE LARGEST VALUE" — evidence: historical-practice
  - [literate-programming-012](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-012) — supports — "I give a declarative commentary at the beginning of a section" — evidence: expert-opinion
  - [planning-and-coding-163](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-163) — qualifies — "The actual coding obtains from this without a need for further comments." — evidence: historical-practice
- **Conditions / limits:** **Partial transfer.** In 1956, FORTRAN names were limited to six characters, so a purpose card did work that a modern function name does. Copied into code with good names, it becomes noise.
- **Tension:** HIS-05 and HIS-06.
- **Testable as:** restrain / noise_lines.

### HIS-21 — If you cannot write down why, investigate before shipping
- **Principle:** Use writing the explanation as a check on the change. If you cannot state why the code is correct or why it takes its form, investigate before shipping. Do not paper over the gap with vague prose.
- **Kind:** agent
- **Sources:**
  - [literate-programming-013](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-013) — supports — "extra time I spend in preparing additional commentary is regained because the debugging time is reduced." — evidence: expert-opinion
  - [literate-programming-013](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-013) — supports — "because I’m in “expository mode”" — evidence: expert-opinion
  - [rational-design-process-010](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-010) — supports — "The documentation is our medium of design and no design decisions are considered to be made until their incorporation into the documents." — evidence: expert-opinion
  - [literate-programming-001](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-001) — qualifies — "must warn the reader to discount much of what I shall say as the ravings of a fanatic" — evidence: expert-opinion
  - [literate-programming-014](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-014) — qualifies — "whenever I have encountered a problem with WEB, I’ve simply changed the system; other users of WEB cannot operate under the same ground rules." — evidence: expert-opinion
- **Conditions / limits:** Knuth's evidence is self-report from one expert, and he flags the bias himself. Whether writing explanations improves an LLM's own edits is an open empirical question, not shown here.
- **Tension:** HIS-12. Writing the reason can tempt invention; the check only works if an unknown is reported, not filled in.
- **Testable as:** not covered by comment-edit. It would need a downstream correctness measure (#19).

## Conflicts and open questions

- **External documents versus inline explanation.** Parnas and Clements want rationale in reviewed external documents and redundant comments kept out of code (rational-design-process-008). Knuth wants code and explanation in one source to stay consistent (literate-programming-002), but says ordinary well-commented Pascal is still worse (literate-programming-011). The product hypothesis sits between them. Test it as a variant axis: inline only, document only, or a linked hybrid.
- **"Stream of consciousness" ordering.** Parnas condemns it as unfindable (rational-design-process-008). Knuth praises WEB for allowing it (literate-programming-011). They mean different things: the writer's train of thought versus the order of composition, as an expository order. For inline comments the question is mostly moot; for long headers it is open.
- **Per-instruction explanation.** Von Neumann prescribes a parallel explanatory column for every order (planning-and-coding-161). Parnas rejects "stream of execution" writing. Von Neumann drops the column once the code is final (planning-and-coding-162), and says some coding follows "without a need for further comments" (planning-and-coding-163). The resolution appears to be readability of the medium. Self-modifying machine code needed narration; high-level code does not. Machine-code-style narration does not transfer.
- **Rationalized design versus recorded history.** Parnas wants a design presented as if derived rationally (rational-design-process-010), yet records every rejected alternative. Knuth keeps the composition order (literate-programming-011). Open for the skill: how much "why we did not do X" belongs in a comment, and how much belongs in the commit message or an ADR. Version control now holds chronology, which none of these authors had.
- **How much to explain.** Von Neumann's omission rule is "no real strain on the reader" (planning-and-coding-020). Knuth writes extensive commentary and says the cost pays for itself (literate-programming-013). Parnas wants dense, formal, non-repetitive documents (rational-design-process-009). The right threshold for an agent reader (HIS-07 versus HIS-17) is unresolved and should be a variant axis tested against `noise_lines` and `recall`.
- **Recording unknowns.** Parnas writes "information unavailable" into the slot where it belongs (rational-design-process-010). For agents, inline "unknown" markers may be noise or invite later invention. The alternative is to report gaps outside the code (synthesis, "Do not turn inference into history"). Untested.
- **Evidence quality.** No source here is empirical. Knuth explicitly discounts his own enthusiasm (literate-programming-001, 014–015) and limits WEB to a subset of programmers who "like to write and to explain what they are doing" (literate-programming-015). The synthesis's nostalgia check notes that historical code was not necessarily better documented than modern code. Treat every candidate here as a hypothesis.

## Notable anti-patterns and worked examples

- **Good, invariant at the point of reliance:** `square ← p[ord] ∗ p[ord]; { at this point ord ≤ k }` and `j: integer; { all primes ≤ j are in table p }` ([literate-programming-005](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-005), [literate-programming-004](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-004)). Short, about state rather than the operation, and placed where a careless edit would break it.
- **Good, alternative and choice stated together:** Knuth's §4 weighs a boolean sieve array against an array of primes and picks one ([literate-programming-003](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-003)). "(We are following Dijkstra,2 not Knuth.3)" records provenance and a deliberate style choice ([literate-programming-005](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-005)).
- **Good, non-obvious reason against efficiency:** von Neumann codes the less efficient integration method "because this offers a good opportunity to exemplify" a technique ([planning-and-coding-075](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-075)). Without the note, a later editor would "optimize" it away. Similar cases exist in modern code: compatibility or readability chosen over speed.
- **Good, assumption with its failure condition:** the FORTRAN frequency guess holds "if the A(1) are randomly arranged but not if they tend to increase" ([fortran-1956-005](../../research/comment-context/sources/fortran-1956/passages.md#fortran-1956-005)).
- **Good, hedged inference:** "which was presumably omitted in the data input" ([fortran-1956-005](../../research/comment-context/sources/fortran-1956/passages.md#fortran-1956-005)). The uncertainty is visible to the reader.
- **Mixed, purpose card:** `C PROGRAM FOR FINDING THE LARGEST VALUE / C ATTAINED BY A SET OF NUMBERS` ([fortran-1956-007](../../research/comment-context/sources/fortran-1956/passages.md#fortran-1956-007)). Useful in 1956. It duplicates a modern function name like `largest_value(a)`.
- **Bad, stream-of-execution narration:** prose that walks the reader through the order of execution ([rational-design-process-008](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-008)). The FORTRAN manual's loop walkthrough ([fortran-1956-005](../../research/comment-context/sources/fortran-1956/passages.md#fortran-1956-005)) is fine in a tutorial and is noise as a code comment.
- **Bad, myopic documentation:** details the author fears forgetting, with the major decisions left implicit ([rational-design-process-009](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-009)).
- **Bad, comments redundant with existing documentation:** they raise maintenance cost and make inconsistency more likely ([rational-design-process-008](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-008)).
- **Bad, invented rationale (synthesis, illustrative):** adding "Matches the server's rate-limit reset window." to an unexplained `retryDelayMs = 750` without evidence ([historical-comment-design.md, "Do not turn inference into history"](../../research/historical-comment-design.md#do-not-turn-inference-into-history)).
- **Does not transfer:** column-bound comment cards and keypunch conventions ([fortran-1956-003](../../research/comment-context/sources/fortran-1956/passages.md#fortran-1956-003)); the parallel explanatory column and explanation of substituted orders for self-modifying code ([planning-and-coding-161](../../research/comment-context/sources/planning-and-coding/passages.md#planning-and-coding-161)); flow-diagram assertion boxes as a separate artifact; WEB weaving and tangling, and typeset hardcopy ([literate-programming-002](../../research/comment-context/sources/literate-programming/passages.md#literate-programming-002)). Parnas's typed term brackets and dictionaries do not transfer either ([rational-design-process-010](../../research/comment-context/sources/rational-design-process/passages.md#rational-design-process-010)). The *ideas* behind them (explain effects, state invariants, keep one source, define terms) may transfer; the mechanisms do not.
