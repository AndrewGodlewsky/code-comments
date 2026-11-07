# Distillation: Industry practice (Google, Fowler, Beck, existing tools)

Sources read:

- `software-engineering-at-google/passages.md`: read in full for ch01-001/002, ch02, ch03-001 to ch03-008, all of ch08, ch09, ch10 (the documentation chapter, every passage), ch11-002/003, ch12-001, ch12-005, ch12-009, ch12-010, ch13-003, ch14-001/002, ch15 (all), ch16-001, ch17 (all), ch19 (all), ch20 (all), ch21 (all), ch22 (all), ch23 (all) and ch25-001. Headings only, or skimmed, for ch03-009 to ch07-004 (the readability process and study), the remaining ch12/ch13 test specimens, ch14-003/004 and ch18. That is about 60% of the passages file and every passage on comments or documentation.
- `code-as-documentation/passages.md` (Fowler 2005): all 4 passages.
- `beck-design-rules/passages.md` (Fowler reporting Beck, 2015): all 5 passages.
- `docs/research/related-systems-and-researchers.md` (secondary synthesis): read in full.
- `docs/research/comment-context/README.md`: the Scope and unresolved source limits section for these three sources.

Source limits that apply throughout:

- *Software Engineering at Google* describes one very large monorepo. It has strong tooling (Code Search, Critique, Tricorder, g3doc) and mandatory style guides.
- The Documentation Philosophy section of ch10 calls itself "personal opinion."
- The book's figures are linearized text, so code indentation is approximate.
- Fowler and Beck are short essays of expert opinion. Fowler says outright that "code as documentation" does not mean code comments.
- The related-systems report is a selective, non-systematic web review. The only LLM experiments it reports are small (Keep the Why: 20 sessions, one fixture) or concern memory rather than comments (MemUse).

## Candidate principles

### IND-01 — Make the code state the intent first; comment only what it cannot say
- **Principle:** Before writing a comment, check whether a clearer name, type, call or structure would make the intent visible at the point of use. If it would, make that change (when it is in scope) instead of writing a comment. Write the comment only for what the code still cannot express.
- **Kind:** when
- **Sources:**
  - [beck-design-rules-002](../../research/comment-context/sources/beck-design-rules/passages.md#beck-design-rules-002) — supports — "the key to enabling understanding is to express your intention in the code, so that your readers can understand what your purpose was when writing it." — evidence: expert-opinion
  - [software-engineering-at-google-ch08-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch08-002) — supports — "we also require that engineers leave explicit evidence of intended behavior in their code." — evidence: historical-practice
  - [software-engineering-at-google-ch08-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch08-002) — supports — "We aim for local reasoning, where the goal is clear understanding of what’s happening at the call site without needing to find and reference other code" — evidence: historical-practice
  - [code-as-documentation-001](../../research/comment-context/sources/code-as-documentation/passages.md#code-as-documentation-001) — qualifies — "Such a principle is not saying that code is the only documentation." — evidence: expert-opinion
  - [related-systems-and-researchers.md § 6. Aider and Sourcegraph: derive navigable context from code](../../research/related-systems-and-researchers.md#6-aider-and-sourcegraph-derive-navigable-context-from-code) — supports — "both systems separate finding relationships from preserving reasons absent from code." — evidence: historical-practice
- **Conditions / limits:** The Google example (`std::unique_ptr` replacing an ownership comment) depends on a language feature and a mandatory rule. An agent may not be authorized to rename public APIs or restructure code outside the task, so "fix the code instead" is limited by task scope. Fowler warns that code "is no more inherently clear" than other documentation (code-as-documentation-002). Code-as-documentation is a goal, not a property code already has.
- **Tension:** IND-10 (Google requires comments on every public function and class, even when the code is clear). A strong reading can also suppress the rationale comments that IND-04 wants.
- **Testable as:** restrain / noise_lines (no restating comments). Code restructuring itself is not covered by comment-edit.

### IND-02 — Use implementation comments to justify non-obvious choices, explain tricky parts and flag important ones
- **Principle:** Inside a function body, write comments that justify a non-obvious choice, explain a tricky piece of logic, or point out a line a future editor must not miss. Do not narrate what each statement does.
- **Kind:** what
- **Sources:**
  - [software-engineering-at-google-ch08-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch08-002) — supports — "Implementation comments (the comments interspersed throughout the code itself) justify or highlight non-obvious choices, explain tricky bits, and underscore important parts of the code." — evidence: historical-practice
  - [software-engineering-at-google-ch10-001](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-001) — supports — "Tricks in code should be avoided, in any case, but good comments help out a great deal when you’re staring at code you wrote two years ago" — evidence: expert-opinion
  - [software-engineering-at-google-ch09-004](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch09-004) — supports — "When writing a public API, you generally don’t want to leak implementation details, but by all means do so within the actual implementation, where you should comment liberally." — evidence: expert-opinion
- **Conditions / limits:** "Comment liberally" comes from a code-review chapter written for human authors and is not calibrated against noise. "Non-obvious" depends on the reader (see IND-17).
- **Tension:** "comment liberally" (ch09-004) conflicts with IND-01, IND-20 and the restrain family.
- **Testable as:** capture / recall (required non-obvious facts) together with restrain / noise_lines.

### IND-03 — Always explain the known places where intent is invisible
- **Principle:** When code contains a deliberate switch fall-through, an empty or swallowing catch block, a deliberate no-op, or dense metaprogramming, add a short comment saying it is intentional and why.
- **Kind:** when
- **Sources:**
  - [software-engineering-at-google-ch08-004](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch08-004) — supports — "specific cases that must include in-code documentation—cases in which intent is not always obvious, such as fall-through in switch statements, empty exception catch blocks, and template metaprogramming." — evidence: historical-practice
  - [software-engineering-at-google-ch08-007](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch08-007) — supports — "“It is very rarely correct to do nothing in response to a caught exception.”" — evidence: historical-practice
  - [software-engineering-at-google-ch12-009](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch12-009) — qualifies — "catch(BannedUserException ignored) {}" — evidence: historical-practice (an empty catch whose variable name carries the intent instead of a comment)
- **Conditions / limits:** The list comes from Google's C++ and Java style guides. Other languages have their own idioms (for example a `# noqa` reason, an explicit `pass`, or `_ =`). An intent-revealing name such as `ignored` can replace the comment, but it does not say *why* the exception is safe to ignore.
- **Tension:** none found.
- **Testable as:** capture / recall (a case with an intentional swallow or fall-through whose evidence holds the reason).

### IND-04 — Record why the code takes its present form
- **Principle:** If the evidence for a change gives a reason the code looks the way it does (a constraint, an incident, a rejected alternative or a trade-off), put that reason in a comment in the scope it governs. A future editor could not recover it from the code.
- **Kind:** what
- **Sources:**
  - [software-engineering-at-google-ch10-001](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-001) — supports — "Why did we implement this code in this manner?" — evidence: expert-opinion
  - [software-engineering-at-google-ch10-004](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-004) — supports — "people leave projects, and sometimes it’s safer to be methodical about exactly why you wrote this code the way you did." — evidence: expert-opinion
  - [software-engineering-at-google-ch03-006](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch03-006) — supports — "implementation comments transmit knowledge across time: you’re writing these comments expressly for the sake of future readers (including Future You!)." — evidence: expert-opinion
  - [software-engineering-at-google-ch17-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch17-002) — supports — "About 16% of Code Searches try to answer the question of why a certain piece of code was added, or why it behaves in a certain way." — evidence: empirical-human (Google search-log intents, cited study; not about comments directly)
  - [related-systems-and-researchers.md § 1. RepoAgent: maintenance of generated repository documentation](../../research/related-systems-and-researchers.md#1-repoagent-maintenance-of-generated-repository-documentation) — supports — "Neither successful automation nor a preferred description guarantees recovery of undocumented historical rationale." — evidence: expert-opinion (secondary synthesis)
- **Conditions / limits:** Record only reasons the evidence supports. The sources assume a human author who knows the reason, and they say nothing about inventing one. For an agent, an invented plausible reason is worse than none (bad_claims). The 16% figure measures what engineers searched for, not whether comments answered it.
- **Tension:** IND-09. Google wants design decisions kept out of API docs and placed in design docs (ch10-013).
- **Testable as:** capture / recall, with bad_claims for invented rationale.

### IND-05 — Name the conditions a decision depends on, so a future editor can tell when it has expired
- **Principle:** When you record a reason, include the conditions it rests on (a version, a limit, a downstream consumer, a measured cost). A later editor can then see that the conditions changed and the decision should be revisited, instead of treating it as permanent.
- **Kind:** maintain
- **Sources:**
  - [software-engineering-at-google-ch08-005](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch08-005) — supports — "With influencing factors clearly noted, we are able to identify when changes related to one or more of these factors warrant reevaluating the rule." — evidence: historical-practice
  - [software-engineering-at-google-ch08-005](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch08-005) — supports — "Documenting the reasoning behind a given decision gives us the advantage of being able to recognize when things need to change." — evidence: historical-practice
  - [software-engineering-at-google-ch03-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch03-002) — supports — "understanding the rationale behind a given guideline allows authors to make informed decisions about when the guideline shouldn’t apply or whether the guideline needs updating." — evidence: expert-opinion
- **Conditions / limits:** The evidence concerns style-guide rules (the CamelCase and two-space-indent cases), not code comments. Applying it to inline rationale is an extrapolation.
- **Tension:** Naming conditions makes comments longer (noise budget, IND-24).
- **Testable as:** maintain / bad_claims and recall (a case where a change removes the stated condition, so the agent must revise or delete the rationale). Downstream confirmation tests whether later agents notice.

### IND-06 — Respect Chesterton's fence: find the reason before removing unusual code, and write it down once found
- **Principle:** Before simplifying or deleting code that looks unnecessary, look for its reason in comments, tests, history and the task evidence. If you keep the code after doubting it, or the evidence shows why it exists, write that reason beside it. The next agent should not have to repeat the investigation or "fix" it.
- **Kind:** agent
- **Sources:**
  - [software-engineering-at-google-ch03-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch03-002) — supports — "before removing or changing something, first understand why it’s there." — evidence: expert-opinion
  - [software-engineering-at-google-ch03-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch03-002) — supports — "If it does, go ahead and make it; if it doesn’t, document your reasoning for future readers." — evidence: expert-opinion
  - [software-engineering-at-google-ch03-001](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch03-001) — supports — "mindlessly copying patterns or code without understanding their purpose, often under the assumption that said code is needed for unknown reasons." — evidence: expert-opinion (defines "parroting"; the same passage defines "haunted graveyards")
  - [related-systems-and-researchers.md § 10. Keep the Why: a directly relevant existing rationale skill](../../research/related-systems-and-researchers.md#10-keep-the-why-a-directly-relevant-existing-rationale-skill) — supports — "Seven of ten controls offered an already-rejected change as an option, versus none with recorded rationale." — evidence: empirical-llm (20 sessions, one fixture, external context file rather than inline comment)
  - [related-systems-and-researchers.md § 10. Keep the Why: a directly relevant existing rationale skill](../../research/related-systems-and-researchers.md#10-keep-the-why-a-directly-relevant-existing-rationale-skill) — qualifies — "**Neither arm broke the wrapper.**" — evidence: empirical-llm
- **Conditions / limits:** The Keep the Why result varies whether rationale was available, not where it was placed. Neither arm broke the code, so the measured effect is on proposals, not on correctness. One fixture with one model.
- **Tension:** IND-19 (where the rationale should live). The Keep the Why approach stores it outside the code.
- **Testable as:** capture / recall, with downstream confirmation (a fresh agent does not reintroduce the rejected change). Partly outside comment-edit.

### IND-07 — Update comments in the same edit as the code they describe
- **Principle:** Any edit that changes behavior, a contract or a constraint must also update every comment and docstring in the edited scope that describes it. Treat a contradicting comment as a defect of the change, not a follow-up task.
- **Kind:** maintain
- **Sources:**
  - [software-engineering-at-google-ch03-006](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch03-006) — supports — "they need to be actively maintained or they can quickly become out of date, as anyone who has ever read a comment that directly contradicts the code can attest." — evidence: expert-opinion
  - [software-engineering-at-google-ch10-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-002) — supports — "Now, engineers could update the code and its associated documentation in the same change (a practice for which we’re still trying to improve adoption)." — evidence: historical-practice
  - [software-engineering-at-google-ch25-001](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch25-001) — supports — "both documentation and tribal knowledge have a tendency to deteriorate over time" — evidence: expert-opinion
  - [related-systems-and-researchers.md § 11. Doxygen: one authored source, several presentations](../../research/related-systems-and-researchers.md#11-doxygen-one-authored-source-several-presentations) — qualifies — "Regenerating presentations from source comments eliminates manual synchronization between those presentations, although authors must still update incorrect comments." — evidence: historical-practice
- **Conditions / limits:** Google admits that same-change updating is still not widely adopted even with docs next to the code. Proximity alone did not guarantee freshness. Comments outside the edited scope (callers, other files) are harder for an agent to find.
- **Tension:** none found among these sources. In the grader, correcting costs noise lines while deleting is free (skill-evals known limitation).
- **Testable as:** maintain / bad_claims (stale facts remain) and preserved (still-valid comments kept).

### IND-08 — Delete or explicitly retire false explanation; never leave stale text that looks authoritative
- **Principle:** When a comment, docstring or referenced doc no longer holds and you cannot fully correct it, remove it, or mark it obsolete and point to the current source. Silence is worse than a "no longer true" note.
- **Kind:** maintain
- **Sources:**
  - [software-engineering-at-google-ch10-014](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-014) — supports — "when a document no longer serves any purpose, either remove it or identify it as obsolete (and, if available, indicate where to go for new information)." — evidence: historical-practice
  - [software-engineering-at-google-ch10-014](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-014) — supports — "Even for unowned documents, someone adding a note that “This no longer works!” is more helpful than saying nothing and leaving something that seems authoritative but no longer works." — evidence: expert-opinion
  - [software-engineering-at-google-ch10-016](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-016) — supports — "When we deprecated GooWiki, we found that around 90% of the documents had no views or updates in the previous few months." — evidence: empirical-human (internal count, wiki pages rather than comments)
  - [software-engineering-at-google-ch03-005](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch03-005) — supports — "if you find a mistake or omission in the documentation, fix it!" — evidence: expert-opinion
- **Conditions / limits:** The passages are about standalone documents. Their "freshness date" metadata (ch10-014) suits files, not inline comments. Do not carry it over as dated comments in code.
- **Tension:** "Mark obsolete" adds lines (noise). For inline comments, deletion or correction is usually better than an obsolete marker.
- **Testable as:** maintain and audit / bad_claims.

### IND-09 — Keep caller-facing contracts separate from maintainer rationale
- **Principle:** In a public docstring or header comment, describe what callers may rely on: behavior, inputs, outputs, errors and side effects. Put design reasoning and implementation detail inside the implementation, near the code it explains, or in a design document.
- **Kind:** where
- **Sources:**
  - [software-engineering-at-google-ch10-004](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-004) — supports — "API comments don’t need to discuss implementation details or design decisions and can’t assume a user is as versed in the API as the author." — evidence: expert-opinion
  - [software-engineering-at-google-ch10-003](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-003) — supports — "Such reasonings belong more appropriately in specific documents (design documents) or, at best, within the implementation details of code hidden behind an interface." — evidence: expert-opinion
  - [software-engineering-at-google-ch10-013](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-013) — supports — "one mistake engineers often make is adding design decisions or implementation details to an API document." — evidence: expert-opinion
  - [software-engineering-at-google-ch09-004](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch09-004) — qualifies — "When writing a public API, you generally don’t want to leak implementation details, but by all means do so within the actual implementation, where you should comment liberally." — evidence: expert-opinion
- **Conditions / limits:** Google's API readers are often external customers. In a small private codebase, the caller and the maintainer may be the same agent. ch10-003 ranks inline implementation comments as "at best" the second choice, after design documents.
- **Tension:** The project hypothesis (inline over separate documents) conflicts with Google's preference for design documents as the home of rationale. See Conflicts.
- **Testable as:** capture / misplaced (a fact stated in the wrong scope, such as rationale in the public docstring instead of beside the constrained code).

### IND-10 — When writing API reference comments, lead with what the code does and write integrated prose
- **Principle:** When a public symbol or file needs a reference comment, begin with what it does and returns, using an active verb. Fold parameters, return value and error cases into one or two sentences instead of boilerplate `Returns:` and `Throws:` sections. A file comment states the file's purpose, main use cases and audience.
- **Kind:** what
- **Sources:**
  - [software-engineering-at-google-ch10-006](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-006) — supports — "It is often clearer to present such information in a single prose comment that’s not broken up into artificial section boundaries:" — evidence: historical-practice
  - [software-engineering-at-google-ch10-006](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-006) — supports — "Adding explicit boilerplate sections would make the comment more verbose and ... repetitive, but ... no clearer (and arguably less clear)." — evidence: expert-opinion
  - [software-engineering-at-google-ch10-005](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-005) — supports — "Any API that cannot be succinctly described in the first paragraph or two is usually the sign of an API that is not well thought out." — evidence: expert-opinion
  - [software-engineering-at-google-ch10-003](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-003) — supports — "Provide overviews or introductions (at the top of a file, for example) that explain the purpose of the code they are looking at." — evidence: expert-opinion
- **Conditions / limits:** Google *requires* file, class and function comments on almost all public code. That mandate fits a large shared codebase with external API consumers. Here, take the form of the comment, not the mandate. Projects whose docstring conventions require `Args:` and `Returns:` sections (for example Google's own Python guide, linked from ch08-009) override this advice.
- **Tension:** The mandate conflicts with IND-01 and with restrain. Adding a docstring to every touched function would fail noise budgets.
- **Testable as:** restrain / noise_lines (no boilerplate sections or docstrings added just for coverage). Format is otherwise not covered by comment-edit.

### IND-11 — State each fact once and point to it rather than copy it
- **Principle:** Do not restate in a comment what the code, a type, a test or another comment already says. When two places need the same fact, choose the owner and have the other point to it.
- **Kind:** avoid
- **Sources:**
  - [beck-design-rules-002](../../research/comment-context/sources/beck-design-rules/passages.md#beck-design-rules-002) — supports — "everything should be said “Once and only Once.”" — evidence: expert-opinion
  - [software-engineering-at-google-ch10-004](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-004) — supports — "(As it should; reference documentation should be single-sourced as much as possible.)" — evidence: historical-practice
  - [software-engineering-at-google-ch10-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-002) — supports — "determine the primary source and consolidate other associated documents into that primary source (or deprecate the duplicates)." — evidence: historical-practice
  - [software-engineering-at-google-ch10-012](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-012) — opposes — "But in documentation, redundancy is often useful." — evidence: expert-opinion (self-described personal opinion)
  - [beck-design-rules-003](../../research/comment-context/sources/beck-design-rules/passages.md#beck-design-rules-003) — qualifies — "In the rare case they are in conflict (in tests are the only examples I can recall), empathy wins over some strictly technical metric." — evidence: expert-opinion
- **Conditions / limits:** Beck's rule concerns duplicated *logic*, and applying it to prose is an extension. ch10-012 permits redundancy *within* one document (a summary up front, detail later), not copying between code and comment. ch12-009 (DAMP) allows duplication in tests for clarity.
- **Tension:** IND-12 (conceptual documents deliberately duplicate reference material). The project's aim of replacing some external docs with inline comments is itself a single-sourcing move.
- **Testable as:** restrain / noise_lines (restating comments). Cross-file duplication is not covered by comment-edit.

### IND-12 — Leave explanations that span modules to a conceptual document and link to it from the code
- **Principle:** Put the explanation in a comment when it belongs to one scope you can name. When it describes how several modules or APIs work together and no single code location owns it, keep it in (or create) a separate concept document. The code links to that document instead of repeating it.
- **Kind:** where
- **Sources:**
  - [software-engineering-at-google-ch10-009](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-009) — supports — "If comments are the unit tests of documentation, conceptual documents are the integration tests." — evidence: expert-opinion
  - [software-engineering-at-google-ch10-009](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-009) — supports — "The only logical place to document such complex behavior is through a separate conceptual document." — evidence: expert-opinion
  - [software-engineering-at-google-ch10-009](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-009) — qualifies — "Often this leads to duplication of some information, but with a purpose: to promote clarity." — evidence: expert-opinion
  - [software-engineering-at-google-ch03-005](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch03-005) — supports — "the documentation is predictably located right next to the source code, as opposed to off in an (unfindable) document or webpage somewhere." — evidence: historical-practice
- **Conditions / limits:** This directly bounds the product hypothesis (which documents can inline comments replace?). Google also says a file comment may hold a "conceptual" explanation when the API surface is broad. Google keeps conceptual documents next to the source (g3doc), not in a remote wiki.
- **Tension:** IND-11 and the project's single-source aim. The skill must decide whether to *create* separate documents at all. Under restrain, probably not.
- **Testable as:** capture / misplaced (a cross-module fact forced into one function's comment). Mostly not covered by comment-edit, so it belongs to the placement pilot.

### IND-13 — Let a test, type, annotation or linked-change check carry any claim that can be checked mechanically
- **Principle:** When a claim about behavior, or a "these must change together" constraint, can be stated as a test, a type, a language annotation or a lint directive, prefer that. Its staleness is detected automatically. Keep prose for the reason, which no check can verify.
- **Kind:** where
- **Sources:**
  - [software-engineering-at-google-ch11-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch11-002) — supports — "Clear, focused tests that exercise one behavior at a time function as executable documentation." — evidence: expert-opinion
  - [software-engineering-at-google-ch20-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch20-002) — supports — "IfThisThenThat allows developers to specify that portions of two different files must be changed in tandem (and warns if they are not)." — evidence: historical-practice
  - [software-engineering-at-google-ch13-003](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch13-003) — supports — "they will see an error directing them to use a more suitable test strategy, such as a real implementation or a fake." — evidence: historical-practice
  - [related-systems-and-researchers.md § 12. Python doctest: executable examples as maintained knowledge](../../research/related-systems-and-researchers.md#12-python-doctest-executable-examples-as-maintained-knowledge) — supports — "Before inventing a prose validator, consider whether an existing executable example or acceptance test can own the behavioral claim." — evidence: expert-opinion (secondary synthesis)
  - [related-systems-and-researchers.md § 12. Python doctest: executable examples as maintained knowledge](../../research/related-systems-and-researchers.md#12-python-doctest-executable-examples-as-maintained-knowledge) — qualifies — "An unchecked rationale sentence remains unchecked even when its neighboring example passes." — evidence: expert-opinion
- **Conditions / limits:** Tests document what is implemented, not necessarily what was intended (ch14-002 makes this point about unit tests). Adding tests or annotations is a code change and is out of scope for a comment-only `audit` request. IfThisThenThat and @DoNotMock are Google-internal tools.
- **Tension:** The restrain family. Adding a test the user did not request is collateral change.
- **Testable as:** Not covered by comment-edit (graded on comments). Possibly as capture / behavior if the hidden checks include tests.

### IND-14 — Mark a deprecation with the language's annotation and name the replacement
- **Principle:** When code becomes deprecated, use the language's machine-readable mechanism (`@deprecated`, `[[deprecated]]`, `warnings.warn(DeprecationWarning)`) and give a message the caller can act on: what to use instead, and when it will be removed if known. A prose "don't use this" comment alone does not migrate anyone.
- **Kind:** what
- **Sources:**
  - [software-engineering-at-google-ch15-003](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch15-003) — supports — "Any deprecation warning issued to a user needs to have two properties: actionability and relevance." — evidence: historical-practice
  - [software-engineering-at-google-ch15-004](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch15-004) — supports — "These annotations give control over messaging to the teams that own the deprecated system, while at the same time automatically alerting the change author." — evidence: historical-practice
  - [software-engineering-at-google-ch08-007](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch08-007) — supports — "surfacing both the warning and the suggested fix in-place, the problem of having new usages of deprecated APIs disappeared almost overnight." — evidence: historical-practice (anecdotal report, with tooling)
  - [software-engineering-at-google-ch15-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch15-002) — qualifies — "It is often tempting to simply put a deprecation warning on an old system and walk away without any further effort." — evidence: historical-practice
  - [software-engineering-at-google-ch15-003](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch15-003) — qualifies — "It’s important to resist the urge to put deprecation warnings on everything possible." — evidence: historical-practice
- **Conditions / limits:** Google's results depend on Tricorder and ErrorProne, which surface warnings only on changed lines. Without that tooling, annotations are weaker. A warning "rarely lead[s] to migration of existing systems" (ch15-003).
- **Tension:** Within ch15-003, Google is "very liberal with marking old functions as deprecated" yet warns against warnings everywhere. The tooling resolves this, and a plain repo lacks it.
- **Testable as:** capture / recall (a deprecation case whose evidence names the replacement). Not in the current seed families.

### IND-15 — Do not disable code by commenting it out; tie temporary states to a tracked issue
- **Principle:** Do not leave commented-out code or tests behind. Delete the code (version control keeps it), or disable it through the framework's skip or flag mechanism with an issue ID and a reason. Give a temporary-state comment (TODO, workaround, disabled test) a tracking reference so it can be found and cleaned up.
- **Kind:** avoid
- **Sources:**
  - [software-engineering-at-google-ch23-003](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch23-003) — supports — "The team could easily disable tests by commenting them out, but that would make the failures too easy to forget about." — evidence: historical-practice (one team case study)
  - [software-engineering-at-google-ch23-003](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch23-003) — supports — "When bug tags from disabled tests began to accumulate and were not updated, the team automated their cleanup." — evidence: historical-practice
  - [software-engineering-at-google-ch17-001](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch17-001) — supports — "or a bug ID in a comment to the corresponding bug report." — evidence: historical-practice
  - [software-engineering-at-google-ch15-001](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch15-001) — supports — "Even code that has been removed can be found again" — evidence: historical-practice
- **Conditions / limits:** **Gap:** none of the three sources gives a TODO format or ownership rule. Google's style-guide comment rules are only cited by URL (ch08-009) and were not extracted. Even tracked tags piled up until cleanup was automated, so a tracked TODO is not self-maintaining. Agents often lack an issue tracker. Do not invent issue IDs.
- **Tension:** none found in these sources. Other groups' sources may prescribe TODO formats.
- **Testable as:** restrain / noise_lines (no commented-out code or untracked TODOs added). Audit / bad_claims if a stale TODO describes work that is already done.

### IND-16 — Separate what callers are promised from what merely happens to be true, and know that a comment cannot stop dependence
- **Principle:** When a contract comment covers ordering, timing, format or other observable behavior, say explicitly whether it is guaranteed. Expect callers to depend on anything they can observe regardless. Before changing such behavior, treat existing comments marked "unspecified" as weak protection and look for real dependents.
- **Kind:** what
- **Sources:**
  - [software-engineering-at-google-ch21-003](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch21-003) — supports — "This is part of why we think projects should publish clear statements of intent with respect to compatibility, usage, and breaking changes." — evidence: expert-opinion
  - [software-engineering-at-google-ch01-001](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch01-001) — qualifies — "we cannot assume perfect adherence to published contracts or best practices." — evidence: historical-practice
  - [software-engineering-at-google-ch21-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch21-002) — qualifies — "What if the documentation said “This may change in the future”?" — evidence: historical-practice
  - [software-engineering-at-google-ch14-001](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch14-001) — qualifies — "the effective user contract applies to all visible behaviors, not just a stated contract." — evidence: expert-opinion
  - [software-engineering-at-google-ch21-004](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch21-004) — qualifies — "naming like this doesn’t fully solve the problem of users reaching in to access private APIs." — evidence: historical-practice
- **Conditions / limits:** Hyrum's Law is stated for APIs with many users. For a private module with one caller, an explicit contract comment is cheap and mostly effective. The guarantee comment helps the *owner* decide on a change more than it constrains users.
- **Tension:** IND-01 (prefer access control or types to prohibitive names and comments). ch21-004 explicitly prefers language access control.
- **Testable as:** maintain / bad_claims (a change alters ordering while a comment still promises it). Capture / recall for a stated guarantee.

### IND-17 — Write for a future reader who lacks your context, especially a fresh agent session
- **Principle:** Write each comment for a reader who has the code but not your conversation, ticket, or reasons for the choices you made. Spell out the constraint itself, not "as discussed" or "per the ticket", and do not assume knowledge that exists only in this session.
- **Kind:** agent
- **Sources:**
  - [software-engineering-at-google-ch10-003](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-003) — supports — "One of the most important mistakes that engineers make when writing documentation is to write only for themselves." — evidence: expert-opinion
  - [software-engineering-at-google-ch08-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch08-002) — supports — "We’d rather the code be tedious to type than difficult to read." — evidence: historical-practice
  - [beck-design-rules-003](../../research/comment-context/sources/beck-design-rules/passages.md#beck-design-rules-003) — supports — "it reminds us that when writing code we should always be thinking of the reader." — evidence: expert-opinion
  - [software-engineering-at-google-ch10-015](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-015) — supports — "For any piece of code that you expect to live more than a few months, the extra cycles you put in documenting that code will not only help others" — evidence: expert-opinion
- **Conditions / limits:** The sources address human teams with turnover. The "fresh agent session" framing is this project's extrapolation (see intent.md). It is plausible but untested. An external link (issue ID) is fine as a pointer *in addition to* the stated constraint.
- **Tension:** Writing for a reader with no context pushes toward longer comments (IND-24, noise).
- **Testable as:** capture / recall (anchor phrases must state the fact, not reference it). Downstream confirmation.

### IND-18 — Treat a "why?" question as a request to restructure the code or add a comment
- **Principle:** If a reviewer, the user or the task evidence asks why something is done a certain way, or a decision is made during the conversation, the answer belongs in the code. Make the code clearer or add a comment in the governing scope, beyond answering in chat or a PR thread.
- **Kind:** when
- **Sources:**
  - [software-engineering-at-google-ch09-004](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch09-004) — supports — "If a reviewer does not understand why you did something, even if it is correct, it is a good indicator that such code needs better structure or better comments" — evidence: expert-opinion
  - [software-engineering-at-google-ch09-004](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch09-004) — supports — "If, during the code review process, a new decision is reached, update the change description, or add appropriate comments within the implementation." — evidence: historical-practice
  - [software-engineering-at-google-ch09-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch09-002) — supports — "it does mean that you might need to explain it more clearly." — evidence: expert-opinion
  - [code-as-documentation-003](../../research/comment-context/sources/code-as-documentation/passages.md#code-as-documentation-003) — supports — "there's nothing more important to clear code than getting feedback from others about what is or isn't easy to understand." — evidence: expert-opinion
- **Conditions / limits:** ch09-004 offers the change description as an alternative home. Commit messages are legitimate for history, but an agent editing later rarely reads them (IND-19). Not every question signals a lasting gap. Some are about the diff only.
- **Tension:** IND-19 and the Google preference for design documents.
- **Testable as:** capture / recall (a case whose evidence includes a reviewer question or a decision reached in discussion).

### IND-19 — Do not leave rationale a future editor needs only in commit messages, review threads or chat
- **Principle:** History tools record why a change happened, but they are a fallback for when inline comments are missing. If the next editor of this code needs the reason to avoid breaking it, put the reason beside the code. Leave narrative about the change itself (what changed, the bug number) to the commit or PR.
- **Kind:** where
- **Sources:**
  - [software-engineering-at-google-ch19-001](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch19-001) — supports — "following some technical decisions that are explained in code review interactions (e.g., when inline comments are lacking)." — evidence: historical-practice
  - [software-engineering-at-google-ch17-005](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch17-005) — supports — "given the rate of commits for machine-generated changes, naive “blame” tracking has less value than it does in more change-averse ecosystems." — evidence: historical-practice
  - [software-engineering-at-google-ch09-003](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch09-003) — opposes — "Moreover, because each change becomes part of the codebase, code review acts as a historical record." — evidence: historical-practice
  - [software-engineering-at-google-ch20-003](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch20-003) — supports — "Improving the message produced by an analysis provides an explanation of what is wrong, why, and how to fix it exactly at the point where that is most relevant" — evidence: historical-practice (an analogy about placing explanation where it is needed)
- **Conditions / limits:** Google's history is easy to reach through Code Search and Critique, and most repos and agents have nothing comparable. The machine-generated-change caveat carries over directly to agent-heavy repos. The boundary between "rationale the code needs" and "change narrative" is a judgment call, and the eval must state it per case.
- **Tension:** ch09-003 and ch19-003 treat review history as a valid explanation store. Keep the Why uses an external context directory.
- **Testable as:** capture / recall (the fact must be in a source comment, not only in the agent's final message). Downstream confirmation.

### IND-20 — Do not add placeholder or boilerplate comments
- **Principle:** Never add comments that only name the construct ("Sample class", "Constructor", "Getter for x") or docstrings that only restate the signature. If you cannot say something the code does not already say, add nothing.
- **Kind:** avoid
- **Sources:**
  - [software-engineering-at-google-ch20-004](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch20-004) — supports — "// Sample method" — evidence: historical-practice (a specimen added in a figure's diff. The source makes no comment-quality judgment, so calling it an anti-pattern is our interpretation.)
  - [software-engineering-at-google-ch10-006](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-006) — supports — "Adding explicit boilerplate sections would make the comment more verbose and ... repetitive, but ... no clearer (and arguably less clear)." — evidence: expert-opinion
  - [software-engineering-at-google-ch10-013](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-013) — supports — "Often, less is more." — evidence: expert-opinion
  - [software-engineering-at-google-ch10-005](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-005) — opposes — "All public classes (and structs) at Google must contain a class comment describing the class/struct, important methods of that class, and the purpose of the class." — evidence: historical-practice
- **Conditions / limits:** Google's mandate exists, but it asks for substantive content (purpose, important methods), not placeholders. Generated-code conventions and linters that require docstrings may force a minimal comment. Follow the repository's own rules there.
- **Tension:** IND-10's mandatory-comment practice.
- **Testable as:** restrain / noise_lines. The `spam` adapter in the self-test is the extreme case.

### IND-21 — Leave valid comments alone; make no cosmetic changes to comments
- **Principle:** When refreshing or touching code, keep still-accurate comments word for word. Do not rewrite them for style, spelling variants or your own phrasing. Change a comment only when it is false, misleading or missing a needed fact.
- **Kind:** avoid
- **Sources:**
  - [software-engineering-at-google-ch22-004](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch22-004) — supports — "we do not want the resulting tools to be used as a mechanism to fight over the proper spelling of “gray” or “grey” in comments." — evidence: historical-practice
  - [software-engineering-at-google-ch22-004](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch22-004) — supports — "or extremely low-value, such as changing spelling from British English to American English, or vice versa." — evidence: historical-practice
  - [software-engineering-at-google-ch22-001](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch22-001) — supports — "Occasionally, this group might suggest that a cleanup just isn’t worth it: for example, cleaning up a common typo without any way of preventing recurrence." — evidence: historical-practice
  - [software-engineering-at-google-ch03-005](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch03-005) — qualifies — "if you find a mistake or omission in the documentation, fix it!" — evidence: expert-opinion
- **Conditions / limits:** The Google passages concern large-scale automated changes, where review cost is multiplied across many owners. For a single agent edit, the cost is reviewer attention and diff noise. Fixing a typo that changes meaning (for example an identifier name in a comment) is a correctness fix, not cosmetic.
- **Tension:** ch03-005 encourages fixing even typos in docs.
- **Testable as:** audit / preserved (protected comments intact) and noise_lines (reworded unchanged comments count as new lines, per the grader limitation).

### IND-22 — Match the local comment conventions so readers can scan
- **Principle:** Follow the comment and docstring form already used in the file, then the module, then the project, in that order. Readers scanning for an answer rely on consistent placement and phrasing. Do not import your own house style.
- **Kind:** where
- **Sources:**
  - [software-engineering-at-google-ch10-003](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-003) — supports — "you will want to have your comments follow a similar format so that readers can quickly scan a reference and see whether they find what they are looking for." — evidence: expert-opinion
  - [software-engineering-at-google-ch08-003](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch08-003) — supports — "“Be consistent” starts locally, where the norms within a given file precede those of a given team" — evidence: historical-practice
  - [code-as-documentation-004](../../research/comment-context/sources/code-as-documentation/passages.md#code-as-documentation-004) — supports — "A professional programmer is prepared to bend her personal style to reflect the needs of the team." — evidence: expert-opinion
- **Conditions / limits:** Local consistency does not justify copying a bad local habit, such as restating comments or commented-out code. ch08-003 also notes that external community standards can outweigh internal ones over time.
- **Tension:** IND-20 when the local convention is boilerplate.
- **Testable as:** not covered by comment-edit (anchor grading ignores form).

### IND-23 — In tests, let names and structure explain; comment only complex scenarios
- **Principle:** Let test names and given/when/then layout carry the explanation. Add section comments only when a test is complex enough that its stages are not obvious, and leave trivial tests uncommented. Comment *why* a test value or helper default was chosen when that is not evident.
- **Kind:** when
- **Sources:**
  - [software-engineering-at-google-ch12-005](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch12-005) — supports — "This level of description isn’t always necessary in trivial tests, and it’s usually sufficient to omit the comments and rely on whitespace to make the sections clear." — evidence: historical-practice
  - [software-engineering-at-google-ch12-005](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch12-005) — supports — "However, explicit comments can make more sophisticated tests easier to understand." — evidence: historical-practice
  - [software-engineering-at-google-ch12-009](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch12-009) — qualifies — "A little bit of duplication is OK in tests so long as that duplication makes the test simpler and clearer." — evidence: expert-opinion
  - [software-engineering-at-google-ch12-010](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch12-010) — supports — "it can be difficult to understand why a particular value was chosen for a test." — evidence: expert-opinion
- **Conditions / limits:** These are Java and Python unit-test examples. Frameworks such as Cucumber build the structure into the test itself.
- **Tension:** none found.
- **Testable as:** restrain / noise_lines when the task adds a simple test.

### IND-24 — Do not treat more documentation, or better documentation scores, as more useful
- **Principle:** Aim for the shortest comment that does its job for the next editor. Completeness and polish trade off against clarity, and the main tools that generate documentation report quality or preference scores, not better later edits.
- **Kind:** agent
- **Sources:**
  - [software-engineering-at-google-ch10-013](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-013) — supports — "If you try to document every possible use case of an API, you might end up with an incomprehensible mess." — evidence: expert-opinion
  - [related-systems-and-researchers.md § 1. RepoAgent: maintenance of generated repository documentation](../../research/related-systems-and-researchers.md#1-repoagent-maintenance-of-generated-repository-documentation) — supports — "These are documentation preferences, not subsequent repair outcomes or long-term drift measurements." — evidence: expert-opinion (secondary synthesis of empirical-llm work)
  - [related-systems-and-researchers.md § 2. DocAgent: repository-aware inline docstring generation](../../research/related-systems-and-researchers.md#2-docagent-repository-aware-inline-docstring-generation) — supports — "inline docstrings are not equivalent to selective decision rationale." — evidence: expert-opinion (secondary synthesis)
  - [related-systems-and-researchers.md § 9. MemUse: delivered memory may never influence useful work](../../research/related-systems-and-researchers.md#9-memuse-delivered-memory-may-never-influence-useful-work) — supports — "Resolve-rate differences remain within 0.4 percentage points, all reported 95% intervals include zero, and episode costs rise 8.8–293.2%." — evidence: empirical-llm (memory stores, not comments; 500 SWE-bench tasks)
  - [software-engineering-at-google-ch10-001](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-001) — opposes — "(In fact, most of the documentation an engineer at Google writes comes in the form of code comments.)" — evidence: historical-practice (volume of comments is normal at Google, with no outcome measure attached)
- **Conditions / limits:** MemUse concerns retrieved memory, not inline comments, and is used here only as a warning that context delivered to an agent may go unused. There is no direct evidence on comment volume and agent outcomes in this group's sources.
- **Tension:** IND-17 and IND-05 both push toward more words per comment.
- **Testable as:** restrain / noise_lines. Downstream confirmation for usefulness.

## Conflicts and open questions

- **Code as documentation vs. mandatory comments.** Fowler and Beck make code the primary carrier of intent, and say "reveals intention" is a property of the code itself (beck-design-rules-002, code-as-documentation-001). Google mandates file, class and function comments on nearly all public code (ch10-005, ch10-006). A skill following the Google mandate fails restrain, and one following Fowler alone may miss capture. Variant to test: "comment only what code cannot say" against "every new public symbol gets a contract docstring".
- **Where rationale belongs.** Google places design decisions in design documents and out of API docs, with inline implementation comments "at best" (ch10-003, ch10-013). ch09-004 says "comment liberally" in implementations, and ch03-002 says "document your reasoning for future readers" without naming where. Review history is also treated as a legitimate store (ch09-003, ch19-003). Keep the Why stores rationale in external context files. The project hypothesis prefers inline. These sources do not resolve this. It is the placement pilot's question.
- **Duplication.** Beck's "Once and only Once" and Google's single-sourced reference docs (ch10-004) conflict with "in documentation, redundancy is often useful" (ch10-012), with purposeful duplication in conceptual docs (ch10-009), and with DAMP tests (ch12-009). Beck himself concedes that "empathy wins" in tests (beck-design-rules-003). The skill needs a rule for what may be repeated: probably summary-then-detail within one comment is acceptable, while restating code in prose is not.
- **Deprecation warnings: liberal or sparing.** ch15-003 says Google is "very liberal with marking old functions as deprecated" and also says to "resist the urge to put deprecation warnings on everything possible". The tooling (warnings on changed lines only) reconciles the two at Google. Without such tooling, the right default is open.
- **Delete vs. mark obsolete.** ch10-014 allows either for documents. For inline comments, the grader makes deletion free and correction cost noise lines, which could teach the skill to delete rationale that should have been corrected. Budgets must leave room for a correction (a known limitation in skill-evals).
- **Do contract comments protect anything?** ch21-003 says to publish intent even if it is ignored. ch21-002 and ch01-001 show that published statements do not prevent dependence. The value of "unspecified; may change" comments to a *maintainer* agent, and not just to callers, is untested.
- **TODO conventions are a gap.** None of these sources specifies a TODO format, owner or expiry. ch23-003 shows that even tracked disable tags pile up without automated cleanup. Look to other groups' sources, or treat it as a design decision.
- **Freshness metadata.** Google's freshness dates and owners (ch10-014) work for files with automated reminders. Whether a per-comment equivalent would help or just add noise for agents is open. These sources do not suggest it.
- **Evidence base.** Almost everything here is expert opinion or one company's practice. The only empirical LLM evidence is Keep the Why (one fixture, 20 sessions, rationale availability not placement) and MemUse (memory, not comments, null result). There is no direct test of inline comments' effect on agent edits.

## Notable anti-patterns and worked examples

- **Making the code carry the intent instead of a comment** ([ch08-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch08-002)). `void TakeFoo(Foo* arg);` needs the comment "may or may not assume ownership", while `void TakeFoo(std::unique_ptr<Foo> arg);` with `TakeFoo(std::move(my_foo))` shows the transfer at every call site. A good example for IND-01.
- **Clearer call over comment** ([ch20-001](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch20-001)). Replace an ambiguous `contains` with `containsValue` even when the behavior is correct.
- **Integrated-prose function comment** ([ch10-006](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-006)). "Creates a new record for a customer with the given name and address, and returns the record ID, or throws `DuplicateEntryError`…", preferred over `Returns:` and `Throws:` boilerplate.
- **File comment stating purpose and audience** ([ch10-005](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-005)). The `str_cat.h` header names the functions and explains that `AlphaNum` exists to avoid copies. It is a "why this type exists" sentence inside a reference comment.
- **Placeholder comments** ([ch20-004](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch20-004)). `/** Sample class */` and `// Sample method` added in a diff. Treat as a negative example (our interpretation; the book does not judge them).
- **Given/when/then comments where they earn their place** ([ch12-005](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch12-005)). They are used in the multi-stage `shouldTimeOutConnections` test, and the book says to omit them in trivial tests.
- **Explaining a helper's defaults** ([ch12-010](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch12-010)). "A helper method wraps a constructor by defining arbitrary defaults for each of its parameters." The comment says the defaults are *arbitrary*, a fact the code cannot show.
- **Intent the tooling enforces, with a replacement** ([ch13-003](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch13-003), [ch15-004](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch15-004)). `@DoNotMock("Use SimpleQuery.create() instead of mocking.")` and `@deprecated` annotations put the "what to do instead" message where tooling surfaces it.
- **Commented-out tests vs. tracked disablement** ([ch23-003](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch23-003)). Commenting out made failures "too easy to forget". Tagging with a bug ID, plus automated cleanup, kept the suite clean.
- **Prohibitive names do not stop dependence** ([ch21-002](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch21-002)). Even `ForInternalUseByLibBaseOnlyDoNotTouchThisIReallyMeanIt` and "This may change in the future" do not stop callers from depending on behavior. Shows the limits of contract comments.
- **Stale-document notice** ([ch10-014](../../research/comment-context/sources/software-engineering-at-google/passages.md#software-engineering-at-google-ch10-014)). A "This no longer works!" note beats silent authoritative text. The freshness metadata block is a document-level mechanism, not an inline comment pattern.
- **Rejected change re-proposed without rationale** ([related-systems-and-researchers.md § 10. Keep the Why](../../research/related-systems-and-researchers.md#10-keep-the-why-a-directly-relevant-existing-rationale-skill)). In a retry-wrapper fixture, 7 of 10 sessions without recorded rationale offered an already-rejected change. A candidate shape for a `capture` or downstream case.
