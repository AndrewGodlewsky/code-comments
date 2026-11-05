# Historical foundations for Code Comments

Research date: 2026-11-04. Scope: primary historical writing about program explanation, comments, design knowledge, and change. This is research input, not an adopted skill workflow.

**Working hypothesis:** selected comments could preserve knowledge at the places future agents edit, potentially reducing repeated discovery and some duplicated shared documentation. The historical material below supplies design arguments and counterarguments. It does not establish that comments improve LLM performance, help less capable models, or remain effective over successive automated edits. Those require direct evaluation.

## What was actually read

The investigation read selected primary passages, not whole books. University mirrors and archive transcriptions reproduce original works; hosting alone does not establish an authoritative edition. Search snippets were used for discovery, not as substitutes for the passages summarized below.

| Work | Access and reading scope |
|---|---|
| Kernighan and Plauger, *The Elements of Programming Style*, second edition, 1978 | Visually inspected the scanned copyright page and printed pp. 141 and 144 of chapter 8. The PDF was too large for the web reader and had no extractable text; its page images were read directly in memory. Other chapter pages were not reviewed. [Book scan](https://docenti.ing.unipi.it/~a009435/issw/extra/kp_elems_of_pgmng_sty.pdf). |
| D. L. Parnas, “On the Criteria To Be Used in Decomposing Systems into Modules,” December 1972 | Read the university-hosted transcription, especially changeability, comprehensibility, criteria, and the circular-shift refinement. The page identifies *Communications of the ACM* 15(12), pp. 1053–1058, and warns that the digitization may contain errors. [Primary-text transcription](https://www.cs.lafayette.edu/~gexia/cs301/resources/parnas.html). |
| Dijkstra, Lamport, Martin, Scholten, and Steffens, “On-the-fly garbage collection: an exercise in cooperation,” EWD520 | Read the archived manuscript transcription: introduction, preliminary investigations, and annotated marking algorithm. The manuscript itself is dated 20 October 1975; this note does not substitute the date of a later journal version. [EWD520](https://www.cs.utexas.edu/~EWD/transcriptions/EWD05xx/EWD520.html). |
| Donald E. Knuth, “Literate Programming” | Read sections A–B, selected program presentation, and the costs discussion in a 15-page preprint marked “submitted to THE COMPUTER JOURNAL.” Its page numbers are preprint pages, not journal pagination. The published article is 1984, 27(2), pp. 97–111. [Primary preprint](https://jpaulgibson.synology.me/~jpaulgibson/TSP/Teaching/Teaching-ReadingMaterial/Knuth84.pdf); [publisher bibliographic reference](https://academic.oup.com/comjnl/pages/65th-anniversary-perspective-af). |
| Peter Naur, “Programming as Theory Building,” 1985 | Read the original essay's introduction, cases, and knowledge discussion in a [retypeset copy](https://blog.chaoticgood.computer/assets/annotated-documents/naur1985programming.pdf), excluding editorial additions. The [scan](https://pages.cs.wisc.edu/~remzi/Naur.pdf) yielded no readable text. Publication: *Microprocessing and Microprogramming* 15, pp. 253–261, per [Naur's bibliography, item 27](https://www.eng.auburn.edu/~vagrawal/COURSE/READING/ARCH/naur_acm.pdf). |
| Rob Pike, “Notes on Programming in C,” 21 February 1989 | Read the comments, names, and complexity sections of the reproduced essay. [Primary-text reproduction](https://www.lysator.liu.se/c/pikestyle.html). |
| Brian W. Kernighan and Rob Pike, *The Practice of Programming*, 1999 | Read section 1.6, printed pp. 23–27. The university-hosted scan identifies its second printing as May 1999. [Book scan](https://www.professores.uff.br/diomarcesarlobao/wp-content/uploads/sites/85/2017/09/4kernighan.pdf#page=34). |
| Edsger W. Dijkstra, trip report, 20 May–14 June 1982, EWD826 | Read the paragraph about studying programs at the Austin laboratory and the explanation given for missing comments. [Archived report](https://www.cs.utexas.edu/~EWD/transcriptions/EWD08xx/EWD826.html). |

The 1992 *Literate Programming* anthology was checked bibliographically on Knuth's own page, but not read as a book. It contains revised and extended articles; claims here concern the preprint above. [Author's description](https://www-cs-faculty.stanford.edu/~knuth/lp.html).

## Source findings

### Elements: preserve explanatory information, not a second execution trace

On p. 141, Kernighan and Plauger favor clear structure while warning that parallel descriptions can diverge. They also value explanations of purpose, use, interactions, principles, and design pseudocode. They reject comment-density quotas. On p. 144, they explicitly treat a rounding-based explanation for an inconsistent threshold as a guess; justified unusual code needs explanation, while a poor algorithm needs correction. [Selected primary pages](https://docenti.ing.unipi.it/~a009435/issw/extra/kp_elems_of_pgmng_sty.pdf#page=154).

### Parnas: relationships need boundaries

Parnas compares decompositions of a keyword-in-context system by their effects on change, independent development, and understanding. His preferred modules contain decisions other modules need not know. He then criticizes his own interface for exposing an ordering that clients did not require: the extra specification unnecessarily restricts future implementations. This is an argument about architecture, not a direct comment-writing prescription. [Criteria and circular-shift refinement](https://www.cs.lafayette.edu/~gexia/cs301/resources/parnas.html).

### Dijkstra and colleagues: explain the argument that makes operations safe

EWD520 deliberately combines condensed design history with justification. A counterexample shows why a collector cannot simply observe an unconstrained mutator without additional cooperation. The presentation then develops invariants and places references to them inside the algorithm. Those annotations describe properties maintained across operations; they do not merely translate each statement into prose. The authors also limit their claims: they leave economic usefulness outside the paper's scope. [Introduction, preliminary investigations, and marking algorithm](https://www.cs.utexas.edu/~EWD/transcriptions/EWD05xx/EWD520.html).

### Knuth: explanation has an order of its own

Knuth organizes programs for human understanding, allowing concepts and their relationships to be introduced in an explanatory order. WEB produces executable and presentation forms from one source. He reports that added exposition paid back through reduced debugging effort, but presents this as personal experience and cautions against assuming universal applicability. Literate programming is consequently more than adding prose to an unchanged conventional source listing. [Preprint sections A–B and costs discussion, pp. 1–2 and 13](https://jpaulgibson.synology.me/~jpaulgibson/TSP/Teaching/Teaching-ReadingMaterial/Knuth84.pdf).

### Naur: possession of documents is not possession of understanding

Naur distinguishes text production from understanding domain correspondence, design justification, and change. His compiler case describes successors proposing awkward extensions despite extensive documentation; the original group could use existing facilities. Another case describes experienced maintainers using annotated source alongside accumulated knowledge. These are case-based philosophical arguments, not controlled measurements. [Original essay's knowledge discussions](https://blog.chaoticgood.computer/assets/annotated-documents/naur1985programming.pdf).

### Pike: restraint still permits orientation and data explanation

Pike distrusts comments that can become incorrect without compiler detection and prefers clearer code where possible. His exceptions matter: introductions to unusual or critical procedures, explanations of shared types and variables, and divisions within substantial computations. His preference for comments about central data structures is stronger than his preference for algorithm commentary. This is experienced judgment, not a universal prohibition. [“Comments” section](https://www.lysator.liu.se/c/pikestyle.html).

### Practice: useful summaries need not be exclusively about why

Kernighan and Pike permit comments that consolidate information scattered through source, summarize functions and global data, identify algorithm references, and explain adaptations. Their transform example combines provenance, representation, performance, and a reason for modification. They also distinguish correct-but-confusing prose from genuinely helpful explanation, and require comments to remain accurate after changes. Their advice supports selective summaries as well as rationale; it does not reduce to an absolute rule against describing behavior. [Section 1.6, pp. 23–27](https://www.professores.uff.br/diomarcesarlobao/wp-content/uploads/sites/85/2017/09/4kernighan.pdf#page=34).

### An explicit check against nostalgia

Dijkstra's 1982 report records an explanation for absent helpful comments: they would prevent the program fitting on a terminal screen. It is one reported incident, not evidence of general practice. It does show that historical programmers faced incentives to omit explanation; older code cannot be presumed better documented simply because these authors advocated careful explanation. [EWD826, Austin laboratory paragraph](https://www.cs.utexas.edu/~EWD/transcriptions/EWD08xx/EWD826.html).

## Tensions the skill should preserve

The following are interpretations for this project, not conclusions demonstrated for agents.

1. **Brevity versus reconstruction cost.** Rejecting line-by-line narration is compatible with retaining a compact account of a design. Comment quotas miss that distinction. [Elements, p. 141](https://docenti.ing.unipi.it/~a009435/issw/extra/kp_elems_of_pgmng_sty.pdf#page=154). A candidate criterion is whether the comment saves reconstruction of a consequential fact.
2. **Local proximity versus coherent explanation.** An inline note can be encountered during an edit; some explanations require a larger reading order. Knuth's design supports the latter, rather than proving that every document belongs inline. [Preprint sections A–B](https://jpaulgibson.synology.me/~jpaulgibson/TSP/Teaching/Teaching-ReadingMaterial/Knuth84.pdf). Replacing shared documentation should remain a separate hypothesis.
3. **Relationship visibility versus accidental coupling.** Explain obligations between components without teaching every caller to depend on hidden representations. This adapts Parnas's interface critique to documentation placement. [Circular-shift refinement](https://www.cs.lafayette.edu/~gexia/cs301/resources/parnas.html).
4. **Written rationale versus invented rationale.** A plausible story about an unusual constant is not historical evidence. The uncertainty in the Elements example is particularly relevant to an agent asked to explain unfamiliar code. [Elements, p. 144](https://docenti.ing.unipi.it/~a009435/issw/extra/kp_elems_of_pgmng_sty.pdf#page=157).
5. **Knowledge retention versus guaranteed transfer.** Naur challenges the assumption that comprehensive text automatically transfers the capacity to modify a system well. [Compiler case](https://blog.chaoticgood.computer/assets/annotated-documents/naur1985programming.pdf). For Code Comments, retaining facts and improving subsequent decisions are distinct outcomes to measure.

## Candidate taxonomy to test

These categories are our synthesis. They are prompts for identifying missing knowledge, not mandatory comment templates. A particular location may need no comment.

| Candidate | Reader question | Historical connection | Proposed placement |
|---|---|---|---|
| Decision and alternative | Why this approach, and what rules out an attractive replacement? | Condensed design history and counterexample in [EWD520](https://www.cs.utexas.edu/~EWD/transcriptions/EWD05xx/EWD520.html). | At the consequential choice; longer deliberation elsewhere. |
| Invariant and preservation | What must stay true across these operations? | Algorithm annotations in [EWD520](https://www.cs.utexas.edu/~EWD/transcriptions/EWD05xx/EWD520.html). | At the operation boundary that could violate it. |
| Domain correspondence | What real-world distinction does this representation preserve? | Naur's account of programmer understanding in [the original essay](https://blog.chaoticgood.computer/assets/annotated-documents/naur1985programming.pdf). | With the representation or conversion. |
| Ownership and lifetime | Who may change or retain this data, and for how long? | Our extension of Pike's emphasis on [central data definitions](https://www.lysator.liu.se/c/pikestyle.html). | At the type, field, or ownership transition. |
| Contract and relationship | What does another component rely on here? | Our application of [Parnas's information-hiding argument](https://www.cs.lafayette.edu/~gexia/cs301/resources/parnas.html). | Where the obligation is defined; avoid repeating private machinery in callers. |
| Orientation | Which larger activity is this block part of? | Pike's introductions to [critical procedures and substantial computations](https://www.lysator.liu.se/c/pikestyle.html). | At a meaningful reading boundary. |
| Provenance and adaptation | Which algorithm or standard is this, and how does this version differ? | The transform example in [Practice, p. 24](https://www.professores.uff.br/diomarcesarlobao/wp-content/uploads/sites/85/2017/09/4kernighan.pdf#page=35). | At the implementation with a precise reference. |
| Compatibility and removal condition | Why does this workaround exist, and when can it disappear? | Our proposed category for successive edits; the historical sources here do not validate this particular format. | Beside the workaround, with verified affected versions or an issue reference. |

## Original examples and counterexamples

All code and situations below are invented for this note. They are not quotations, facts about this repository, or claims about a named service. Their comments would require verification before being used in real code.

### Preserve the reason for an ordering constraint

```ts
// Persist the token before acknowledging: redelivery must reuse the same token.
await saveToken(job.id, token);
await acknowledge(job);
```

The first line explains why reversing two individually clear operations changes the protocol. “Save token, then acknowledge” would add little. A test may exercise redelivery; the comment makes the relevant constraint discoverable during a local edit.

### Distinguish representation from domain meaning

```ts
// null means the sensor was never read; zero is a recorded measurement.
type Reading = number | null;
```

The type exposes the available values. The comment supplies the domain distinction a future simplification must preserve. If that distinction already has a canonical nearby declaration, another copy may be unnecessary.

### Make a boundary obligation discoverable

```ts
// The verifier hashes these exact bytes; normalization belongs after verification.
const payload = await readRawBody(request);
await verifySignature(payload);
```

This explains a relationship without copying the verifier's algorithm. A useful evaluation would ask a later agent to add parsing and observe whether it preserves the byte boundary.

### Do not turn inference into history

```ts
const retryDelayMs = 750;
// Bad addition: "Matches the server's rate-limit reset window."
```

Without supporting evidence, the new sentence manufactures an explanation. Even if it sounds credible, it can discourage investigation of an actual defect. A research result that the reason could not be established belongs in the agent's report; it should not quietly become durable code knowledge.

## Implications to investigate before choosing a workflow

These are proposed research questions and experimental choices, not established benefits or implementation decisions.

- **Unit of value:** score each addition by a specific future decision it helps, rather than its length, category coverage, or stylistic polish. Include examples where the correct action is to add nothing.
- **Evidence available to the writer:** compare comments written from code alone with comments grounded in tests, callers, issue history, and an author's explanation. Track unsupported causal claims separately from accurate descriptions of current behavior.
- **Document replacement:** compare inline-only, shared-document-only, and linked hybrid conditions containing equivalent information. Separate information duplication from useful local reminders. Measure whether a reader can still find the global explanation.
- **Successive edits:** introduce changes that invalidate some comments. Observe whether the next agent updates, removes, ignores, or obeys the stale text. Include a misleading comment condition so a method cannot win merely by adding confident prose.
- **Model capability:** test several capability levels on the same tasks. An improvement for one model does not demonstrate that a smaller model can safely replace a stronger one.
- **Contract inflation:** watch whether an implementation detail described in prose becomes an assumed public guarantee during later edits. This is a project-specific failure mode suggested by the distinction between internal facts and external obligations.
- **Truth versus readability:** assess factual support, successful edits, regression avoidance, and time or tokens independently. An attractive explanation can still support the wrong change.

## Unresolved questions and limits

The primary material leaves open the right granularity of knowledge for an agent, the point at which a local summary becomes redundant, the cost of keeping comments synchronized, and whether inline placement measurably improves retrieval over ordinary repository search. It also does not establish how much historical reasoning should survive once its constraints disappear.

This is a deliberately selective historical sample. It concentrates on influential English-language programming texts and papers, and cannot establish how representative their advice was. Primary access does not make expert opinion controlled evidence. The Naur copy warrants additional comparison with the original scan before quoting exact wording; no direct quotation from it is used here. No claim depends on reading an entire book or on unseen chapters.

The useful research direction is therefore a testable distinction: preserve verified knowledge that changes a future editing decision, while measuring the costs of stale, duplicated, misplaced, and invented explanations. Whether that becomes a reliable cross-tool skill remains to be demonstrated.

The [proposed evaluation protocol](evaluation-protocol.md) is the canonical draft
for testing these ideas; the candidate categories above are research inputs.
