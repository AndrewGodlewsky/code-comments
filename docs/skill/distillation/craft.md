# Distillation: Craft of what to write and where (Pragmatic Programmer, Ousterhout)

Sources read:
- `pragmatic-programmer/passages.md`: all 63 selected passages skimmed by heading and context line. A keyword sweep ("comment", "document", "assum", "stale", "out of date", "out of step") ran over the whole file. The comment-relevant passages were read in full: 003-012, 014, 016, 018-027, 030, 034, 037-039, 041-043, 047, 049, 050, 055 and 060. The source is a machine audio transcript of the second-edition audiobook. Wording, speaker attribution and spoken code are unverified, and transcript errors are kept in the quotes.
- `philosophy-of-software-design/passages.md`: all 11 passages (001-011) read in full. This is a discontinuous 20-page OCR extract (printed pages 39-49, 76, 99-100, 171-174). **Most of Ousterhout's comment chapters are not local.** That includes the chapters on comments describing things not obvious from the code, interface versus implementation comments, and comment-first design. Only the end of "Why Write Comments? The Four Excuses" (12.5-12.6) and the "Decide What Matters" chapter are present. Claims about those absent chapters are not cited here.
- `docs/research/comment-context/README.md`, the scope and limits section for both sources.

Quote note: all 93 citations were checked against their passage blocks after whitespace normalisation. Sixteen Ousterhout quotes cross OCR line breaks (newline replaced by a space), so a citation checker must collapse whitespace. No quote crosses an OCR end-of-line hyphen or a transcript timestamp marker.

## Candidate principles

### CRA-01 — Comment why, purpose and goal; do not narrate how
- **Principle:** Outside API documentation, write comments that explain why the code does something, what it is for and what goal it serves. Do not paraphrase what the statements already show.
- **Kind:** what
- **Sources:**
  - [pragmatic-programmer-004](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "So restrict your non-API commenting to discussing why something is done, its purpose, and its goal." — evidence: expert-opinion
  - [pragmatic-programmer-004](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "The code already shows how it is done, so commenting on this is redundant and is a violation of the dry principle." — evidence: expert-opinion
  - [pragmatic-programmer-047](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-047) — supports — "deduct percent is what it does and not why it does it." — evidence: expert-opinion
  - [philosophy-of-software-design-007](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-007) — qualifies — "I agree that good software design can reduce the need for comments (particularly those in method bodies)." — evidence: expert-opinion
- **Conditions / limits:** API and interface comments are explicitly excluded from the restriction, so they may describe behaviour (see CRA-05). "How" is sometimes not obvious, for example in a clever algorithm or a non-obvious ordering. Neither local source explicitly covers that case, and Ousterhout's chapter on implementation comments is not in the extract.
- **Tension:** CRA-05 and CRA-07. Interface comments necessarily describe *what* a routine does.
- **Testable as:** restrain / noise_lines (restating comments); capture / recall (the why is present).

### CRA-02 — Record trade-offs, decisions and rejected alternatives at the code
- **Principle:** When the evidence shows an engineering trade-off, a decision under uncertainty or a discarded alternative, record it in a comment at the code it shaped. That includes "I chose not to do X because Y". Code cannot express this information, and there is no better home for it.
- **Kind:** what
- **Sources:**
  - [pragmatic-programmer-004](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "Commenting source code gives you the perfect opportunity to document those elusive bits of a project that can't be documented anywhere else." — evidence: expert-opinion
  - [pragmatic-programmer-004](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "Engineering trade-offs, why decisions were made, what other alternatives were discarded, and so on." — evidence: expert-opinion
  - [pragmatic-programmer-005](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-005) — supports — "when you make decisions, document those decisions somehow, write them in your day book or make a note in the code." — evidence: expert-opinion
  - [philosophy-of-software-design-007](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-007) — supports — "this information can't be represented in code today" — evidence: expert-opinion
  - [pragmatic-programmer-020](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-020) — qualifies — "Use paper, not a file or a wiki." — evidence: expert-opinion
- **Conditions / limits:** The skill can only record what the evidence (task, issue, diff discussion) supports. An agent that invents a plausible rationale violates the spirit of this principle. Pragmatic Programmer also routes some decision notes to a personal daybook rather than the code. Those are learning notes for the author, not shared knowledge.
- **Tension:** CRA-11, because decision comments that quote volatile specifics go stale. CRA-22, which asks whether some knowledge belongs outside the code.
- **Testable as:** capture / recall; capture / bad_claims (invented rationale planted as rejected).

### CRA-03 — Do not comment every declaration mechanically
- **Principle:** Do not add a comment to every function, field, type or statement by rule. Each mechanical comment is a second copy that must be updated with every change.
- **Kind:** avoid
- **Sources:**
  - [pragmatic-programmer-004](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "this doesn't mean we agree with the folks who say that every function, data structure, type declaration, etc. needs its own comment." — evidence: expert-opinion
  - [pragmatic-programmer-004](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "This kind of mechanical comment writing actually makes it more difficult to maintain code. Now there are two things to update when you make a change." — evidence: expert-opinion
  - [pragmatic-programmer-006](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-006) — supports — "Somehow the myth was born that you should comment all your functions." — evidence: expert-opinion
  - [philosophy-of-software-design-005](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-005) — qualifies — "More functions means more interfaces to document and learn." — evidence: expert-opinion
- **Conditions / limits:** Ousterhout's aside assumes that each interface carries documentation as a cost. The two sources may differ on how many interfaces deserve a comment (see Conflicts). The style of the host codebase, such as required docstrings or linters, may override this.
- **Tension:** CRA-05 (comment exported functions); Ousterhout's implied "every interface is documented".
- **Testable as:** restrain / noise_lines; the `spam` adapter is the canonical violation.

### CRA-04 — Ask what the comment adds; if it only compensates for poor names, prefer the name
- **Principle:** Before writing a comment that restates logic, ask what it adds beyond the code. If the task allows code changes, a clearer name or parameter type can sometimes carry the meaning instead. A name cannot carry rationale, so the remaining why still belongs in a comment.
- **Kind:** avoid
- **Sources:**
  - [pragmatic-programmer-006](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-006) — supports — "Ask yourself what the comment adds to the code." — evidence: expert-opinion
  - [pragmatic-programmer-006](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-006) — supports — "From our point of view, it simply compensates for some bad naming and layout." — evidence: expert-opinion
  - [pragmatic-programmer-006](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-006) — supports — "The name says what it does. And if someone needs details, they're laid out in the source. That's dry." — evidence: expert-opinion
  - [philosophy-of-software-design-007](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-007) — opposes — "Even with all these words, names like this are cryptic" — evidence: expert-opinion
- **Conditions / limits:** Renaming is a code change. It is forbidden in `audit` cases, and in other families it can be scope creep or break callers. Ousterhout's objection is aimed at Martin's extract-method-and-name approach, not at Pragmatic Programmer. Ousterhout reports the Martin quotation second-hand.
- **Tension:** Direct conflict between the "names replace comments" and "comments carry more than names" positions (see Conflicts). CRA-17.
- **Testable as:** restrain / noise_lines; audit / behavior (renaming breaks the AST-equality check).

### CRA-05 — Put interface comments on modules and exported entry points
- **Principle:** Give modules and exported functions a short interface comment that tells a caller what they need to use them without reading the body. Put the most important facts where they are most likely to be seen.
- **Kind:** where
- **Sources:**
  - [pragmatic-programmer-004](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "we recommend adding comments to modules and exported functions to give other developers a leg up." — evidence: expert-opinion
  - [philosophy-of-software-design-007](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-007) — supports — "instead of reading the entire body of a method, a developer can read a short interface comment to get all the information they need in order to invoke the method." — evidence: expert-opinion
  - [philosophy-of-software-design-010](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-010) — supports — "important things should appear in places where they are more likely to be seen, such as interface documentation, names, or parameters to heavily used methods." — evidence: expert-opinion
- **Conditions / limits:** For an agent this is about placement, not a mandate to add docstrings to every public function. Combine it with CRA-03 and CRA-16. Neither source tests whether agents actually read interface comments before calling.
- **Tension:** CRA-03 on how many interfaces to cover; restrain cases may involve public functions with nothing non-obvious to say.
- **Testable as:** capture / misplaced (fact placed in the wrong scope); capture / recall.

### CRA-06 — Separate what callers need from what implementers need
- **Principle:** In an interface comment, state only what matters to callers. Put implementation-only facts inside the implementation. Do not let an abstraction hide something callers actually need, such as exactly which characters a delete removes.
- **Kind:** where
- **Sources:**
  - [philosophy-of-software-design-008](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-008) — supports — "The interface of a module reflects what matters to users of that module; things that don't matter to the module's users should be hidden in the implementation," — evidence: expert-opinion
  - [philosophy-of-software-design-003](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-003) — supports — "One of the most important elements of software design is determining who needs to know what, and when." — evidence: expert-opinion
  - [philosophy-of-software-design-003](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-003) — supports — "Putting the method in the text class just makes it harder for user interface developers to get the information they need." — evidence: expert-opinion
  - [pragmatic-programmer-038](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-038) — supports — "hiding implementation behind small, well-documented interfaces can all help." — evidence: expert-opinion
- **Conditions / limits:** The local extract shows this as an interface design principle (the text-editor example), not as explicit comment-placement advice. Ousterhout's dedicated interface versus implementation comment chapter is absent. Transferring it to comments is an inference.
- **Tension:** none found.
- **Testable as:** capture / misplaced (an owner-scope fact explained only at the call site or module header).

### CRA-07 — State the contract, including what is not promised
- **Principle:** When a routine has preconditions, postconditions or invariants that the language does not enforce, state them in the interface comment. Say what the routine does *not* promise, and who is responsible for checking the inputs.
- **Kind:** what
- **Sources:**
  - [pragmatic-programmer-021](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-021) — supports — "Even without automatic checking, you can put the contract in the code as comments or in the unit tests and still get a very real benefit." — evidence: expert-opinion
  - [pragmatic-programmer-021](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-021) — supports — "or, more importantly, what it doesn't promise to deliver, before you write the code is a huge leap forward in writing better software." — evidence: expert-opinion
  - [pragmatic-programmer-022](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-022) — supports — "By expressing the domain of the square root function in its precondition, you shift the burden of correctness to the caller, where it belongs." — evidence: expert-opinion
  - [pragmatic-programmer-021](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-021) — qualifies — "While documenting these assumptions is a great start, you can get much greater benefit by having the compiler check your contract for you." — evidence: expert-opinion
- **Conditions / limits:** Prefer an assertion, guard, type or test where one can express the contract (CRA-18). The comment is the fallback, or the explanation of the check. Design by Contract comes from the Eiffel tradition, and the "not promised" emphasis is the authors' own.
- **Tension:** CRA-18 (executable over prose); CRA-03 (contracts on every routine would be mechanical).
- **Testable as:** capture / recall; maintain / bad_claims (a contract comment left false after a signature or behaviour change).

### CRA-08 — Write down assumptions, especially reliance on undocumented behaviour
- **Principle:** When code relies on behaviour that a dependency does not document, or on an assumption not established as fact, write the assumption down at the point of reliance. When a bug turns out to come from a wrong assumption, leave the corrected understanding where the next editor will meet it.
- **Kind:** what
- **Sources:**
  - [pragmatic-programmer-038](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-038) — supports — "For routines you call, rely only on documented behavior. If you can't, for whatever reason, then document your assumption well." — evidence: expert-opinion
  - [pragmatic-programmer-038](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-038) — supports — "But these assumptions are rarely documented and are often in conflict between different developers." — evidence: expert-opinion
  - [pragmatic-programmer-018](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-018) — supports — "If one person misunderstands, then it's possible many people do." — evidence: expert-opinion
  - [pragmatic-programmer-038](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-038) — qualifies — "Write an assertion to test your assumptions. If your assertion is right, you have improved the documentation in your code." — evidence: expert-opinion
  - [pragmatic-programmer-043](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-043) — qualifies — "So I now do write tests on code shared with others or that relies on the peculiarities of external dependencies." — evidence: expert-opinion
- **Conditions / limits:** In 018 the authors recommend discussing the problem with the whole team, not writing a comment. Applying that to comments is an inference for agents, which have no team channel across sessions. Tests and assertions are offered as alternative carriers.
- **Tension:** CRA-18 (put it in an assertion or test instead).
- **Testable as:** capture / recall (bug-fix cases whose evidence contains a dependency quirk).

### CRA-09 — Distinguish fixed invariants from changeable policy, and comment them differently
- **Principle:** State a semantic invariant clearly and briefly where it governs the code, for example "error in favour of the consumer". Treat changeable policy, such as fee amounts or thresholds, as data. Do not repeat its current values in prose.
- **Kind:** what
- **Sources:**
  - [pragmatic-programmer-022](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-022) — supports — "Be sure not to confuse requirements that are fixed, inviolate laws with those that are merely policies that might change with a new management regime." — evidence: expert-opinion
  - [pragmatic-programmer-022](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-022) — supports — "Try to state it clearly and unambiguously. For example, in the debit card example, we might write, error in favor of the consumer." — evidence: historical-practice
  - [pragmatic-programmer-049](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-049) — supports — "You must capture the underlying semantic invariance as requirements and document the specific or current work practices as policy." — evidence: expert-opinion
  - [philosophy-of-software-design-009](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-009) — supports — "once you know an invariant for a variable or structure, you can predict how that variable or structure will behave in many different situations." — evidence: expert-opinion
- **Conditions / limits:** The sources discuss invariants in requirements documents and whiteboards ("a big note on the common whiteboard"), not specifically in comments. The debit-card switch is a single recalled project. "Semantic invariance" is transcribed as heard.
- **Tension:** CRA-11 (both push volatile values out of comments).
- **Testable as:** capture / recall; maintain / bad_claims (policy numbers in comments made false by a change).

### CRA-10 — Make hidden coupling, ownership and conventions explicit
- **Principle:** When correctness depends on something the code does not show locally, prefer to make it visible in structure. Examples are which routine closes a resource, a lock everyone must take, or a shared variable two functions rely on. Where a convention remains, state it at every place a maintainer would change it.
- **Kind:** what
- **Sources:**
  - [pragmatic-programmer-026](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-026) — supports — "However, you need to make it explicit for each, and implement your decision consistently." — evidence: expert-opinion
  - [pragmatic-programmer-026](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-026) — supports — "That shared variable doesn't even appear in the update customer routine." — evidence: expert-opinion
  - [pragmatic-programmer-034](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-034) — qualifies — "Probably the most significant is that it only works because everyone who accesses the pie case agrees on the convention of using the semaphore." — evidence: expert-opinion
  - [pragmatic-programmer-027](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-027) — supports — "That's a lot of implicit knowledge. But worse, that's a lot of things that cannot change in the future if this code is to continue to work." — evidence: expert-opinion
- **Conditions / limits:** The authors' remedy is always refactoring (balanced open and close, transactional APIs, tell-don't-ask), not commenting. A comment is the agent's fallback when the task does not authorise restructuring. Read these passages as a catalogue of facts worth explaining, not as advice to comment them.
- **Tension:** CRA-18 (fix it in code); scope discipline in `capture` cases.
- **Testable as:** capture / recall (ownership and ordering constraints); capture / misplaced.

### CRA-11 — Do not copy volatile specifics into comments
- **Principle:** Do not restate in a comment the specific numbers, rule tables, exception lists or call sequences that the code already contains. When they change, the comment silently becomes false.
- **Kind:** avoid
- **Sources:**
  - [pragmatic-programmer-006](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-006) — supports — "The intent of this function is given twice. Once in the comment and again in the code. The customer changes a fee and we have to update both." — evidence: expert-opinion
  - [pragmatic-programmer-006](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-006) — supports — "Given time, we can pretty much guarantee the comment and the code will get out of step." — evidence: expert-opinion
  - [pragmatic-programmer-006](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-006) — supports — "It isn't a question of whether you'll remember, it's a question of when you'll forget." — evidence: expert-opinion
  - [pragmatic-programmer-023](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-023) — supports — "If the writer of that method adds another exception, our code is subtly out of date." — evidence: expert-opinion
- **Conditions / limits:** Passage 023 is about verbose error-handling code, not prose. It is cited as an analogue: enumerating another module's details couples you to them. The "guarantee" of drift is the authors' assertion, not a measurement.
- **Tension:** CRA-02 and CRA-07. A rationale or contract sometimes has to name a specific value, for example "must stay below the 30 s gateway timeout". Write the reason and point to the constant rather than copying it.
- **Testable as:** maintain / bad_claims; restrain / noise_lines.

### CRA-12 — Give each fact one authoritative home; duplication is about knowledge, not text
- **Principle:** If a fact is already explained elsewhere, do not explain it again. That covers another comment, the owning function's docstring and a generated spec. Put it in the scope that owns it and refer to it from other places. Two similar-looking comments on code that only coincidentally matches are not duplication.
- **Kind:** where
- **Sources:**
  - [pragmatic-programmer-006](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-006) — supports — "every piece of knowledge must have a single, unambiguous, authoritative representation within a system." — evidence: expert-opinion
  - [pragmatic-programmer-006](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-006) — supports — "Do you have to change code and documentation, or a database schema and a structure that holds it? If so, your code isn't dry." — evidence: expert-opinion
  - [pragmatic-programmer-006](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-006) — qualifies — "The code is the same, but the knowledge they represent is different." — evidence: expert-opinion
  - [pragmatic-programmer-019](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-019) — supports — "That would mean we're duplicating code, virtually guaranteeing that we'd forget to update an example when the corresponding program was changed." — evidence: historical-practice
  - [philosophy-of-software-design-010](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-010) — opposes — "Another way to emphasize is with repetition: key ideas appear over and over again." — evidence: expert-opinion
- **Conditions / limits:** Passage 019 concerns book production (generated code listings), not inline comments. Ousterhout treats deliberate repetition of key ideas as a way to emphasise them, which is in tension with strict DRY for documentation. Repeating a pointer ("see X") differs from repeating the fact.
- **Tension:** Ousterhout's emphasis by repetition versus DRY; CRA-05 (caller-side visibility).
- **Testable as:** capture / misplaced; maintain / bad_claims (an unrevised duplicate copy left stale).

### CRA-13 — Fix a comment the moment it stops being true; a misleading one is worse than none
- **Principle:** Treat every change as maintenance. When an edit makes a comment, docstring or name false, correct it in the same change rather than leaving it for later. A misleading explanation does more harm than a missing one.
- **Kind:** maintain
- **Sources:**
  - [pragmatic-programmer-047](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-047) — supports — "You can quickly descend into a nightmare much worse than meaningless names, misleading names." — evidence: expert-opinion
  - [pragmatic-programmer-047](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-047) — supports — "When you see a name that no longer expresses the intent or is misleading or confusing," — evidence: expert-opinion
  - [pragmatic-programmer-039](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-039) — supports — "Outdated knowledge. Things change, requirements drift, and your knowledge of the problem increases. Code needs to keep up." — evidence: expert-opinion
  - [pragmatic-programmer-006](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-006) — supports — "Programmers are constantly in maintenance mode." — evidence: expert-opinion
  - [pragmatic-programmer-003](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-003) — supports — "Fix each one as soon as it is discovered." — evidence: expert-opinion
- **Conditions / limits:** Passage 047 is about names. Extending "misleading is worse than meaningless" to comments is an inference, though a direct one. "Broken windows" is an analogy to contested criminology research that the authors report without data. This principle concerns only comments made false by the change or found false. It does not license rewriting comments that are still valid.
- **Tension:** Preserving still-valid comments, which the `preserved` metric protects.
- **Testable as:** maintain / bad_claims; audit / bad_claims; maintain / preserved (do not over-correct).

### CRA-14 — Write the intent first, in one sentence
- **Principle:** Before writing a non-trivial piece of code, write one sentence stating what it should accomplish or what you want to learn. If you cannot name or describe it clearly, take that as a design signal and do not paper over it.
- **Kind:** when
- **Sources:**
  - [pragmatic-programmer-037](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-037) — supports — "In your empty editor buffer, create a comment describing in one sentence what you want to learn or do." — evidence: expert-opinion
  - [pragmatic-programmer-047](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-047) — supports — "Often we find ourselves realizing that what we were about to do made no sense, all because we couldn't come up with an appropriate name." — evidence: expert-opinion
  - [philosophy-of-software-design-006](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-006) — supports — "They will also discuss how to integrate documentation-writing into the design process so that it improves the design of your software." — evidence: expert-opinion
  - [pragmatic-programmer-037](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-037) — qualifies — "Delete all the prototype code, throw away the sticky note" — evidence: expert-opinion
- **Conditions / limits:** In 037 the comment belongs to a disposable prototype used to beat blank-page paralysis, and it is thrown away. Ousterhout's comment-first chapter is only forward-referenced in the extract, so its content is not available here. Whether intent-first comments survive into production code is not addressed.
- **Tension:** CRA-19 (prototype comments should be minimal).
- **Testable as:** not covered by comment-edit (process, not output).

### CRA-15 — Write for an editor who has forgotten everything
- **Principle:** Write explanations for a future editor who lacks the original designer's context, including yourself weeks later or a fresh agent session. Give them what they need to change the code safely. Point out what is relevant to a change so they do not have to reconstruct it from the code.
- **Kind:** agent
- **Sources:**
  - [philosophy-of-software-design-006](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-006) — supports — "you will have forgotten many of the details of the original design." — evidence: expert-opinion
  - [philosophy-of-software-design-006](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-006) — supports — "Without adequate documentation, developers may have to read large amounts of code to reconstruct what was in the designer's mind." — evidence: expert-opinion
  - [philosophy-of-software-design-006](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-006) — supports — "Good documentation can clarify dependencies, and it fills in gaps" — evidence: expert-opinion
  - [pragmatic-programmer-004](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "We write code which communicates our intentions to a machine and documents our thinking for future generations of developers." — evidence: expert-opinion
- **Conditions / limits:** Ousterhout says documentation helps with cognitive load and unknown unknowns, but not with change amplification. That is expert opinion about human developers. Whether LLM agents benefit in the same way is the project's open hypothesis, not something these sources show.
- **Tension:** CRA-16 (selectivity); restrain cases.
- **Testable as:** capture / recall.

### CRA-16 — Decide what matters and comment that; do not treat everything as important
- **Principle:** Spend comment budget on the few facts with the most leverage, such as invariants, constraints and non-obvious dependencies. Lead with the key concept and tie details back to it. Marking too much as important hides what matters.
- **Kind:** what
- **Sources:**
  - [philosophy-of-software-design-010](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-010) — supports — "When this happens, unimportant things clutter up the design, adding complexity and increasing cognitive load." — evidence: expert-opinion
  - [philosophy-of-software-design-010](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-010) — supports — "This mistake leads to situations where important information is hidden" — evidence: expert-opinion
  - [philosophy-of-software-design-011](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-011) — supports — "the best way to make a document easy to read is to identify a few key concepts at the beginning" — evidence: expert-opinion
  - [pragmatic-programmer-004](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "You're communicating only if you're conveying what you mean to convey." — evidence: expert-opinion
- **Conditions / limits:** Ousterhout's "Decide What Matters" chapter is about design, and he extends it to technical writing only briefly (21.5). Its use for comment selection is an inference. Both failure modes are named: too much (noise) and too little (hidden information).
- **Tension:** CRA-15 versus CRA-03. This principle is the arbiter between them.
- **Testable as:** restrain / noise_lines; capture / recall.

### CRA-17 — Do not avoid a needed comment to look "clean"
- **Principle:** When the evidence holds knowledge that code cannot express, write the comment. Do not treat comments as failures to minimise, and do not omit a needed explanation because self-documenting code is fashionable.
- **Kind:** when
- **Sources:**
  - [philosophy-of-software-design-006](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-006) — opposes — "Comments are always failures." — evidence: expert-opinion
  - [philosophy-of-software-design-007](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-007) — supports — "Well-written comments are not failures." — evidence: expert-opinion
  - [philosophy-of-software-design-007](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-007) — supports — "I worry that Martin's philosophy encourages a bad attitude in programmers, where they avoid comments so as not to seem like failures." — evidence: expert-opinion
  - [pragmatic-programmer-060](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-060) — supports — "People should see your name on a piece of code and expect it to be solid, well-written, tested, and documented." — evidence: expert-opinion
- **Conditions / limits:** The opposing quotation is Martin's *Clean Code* as quoted by Ousterhout. Martin's book is not in the local corpus. Ousterhout concedes that good design reduces the need for comments in method bodies.
- **Tension:** CRA-04 and CRA-03. This is the "how much to comment" axis.
- **Testable as:** capture / recall (a never-comment skill fails `capture`).

### CRA-18 — Prefer an executable carrier where one exists; comment what it cannot hold
- **Principle:** If a type, assertion, guard clause, test or automated script can express and check a constraint, use it, or keep the one that exists. Reserve prose for the rationale and context such checks cannot carry.
- **Kind:** where
- **Sources:**
  - [pragmatic-programmer-047](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-047) — supports — "Using a type documents what the function expects." — evidence: expert-opinion
  - [pragmatic-programmer-043](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-043) — supports — "The tests are also a way of communicating with other developers." — evidence: expert-opinion
  - [pragmatic-programmer-055](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-055) — supports — "Manual procedures leave consistency up to chance." — evidence: expert-opinion
  - [philosophy-of-software-design-007](../../research/comment-context/sources/philosophy-of-software-design/passages.md#philosophy-of-software-design-007) — qualifies — "Code and comments are each well-suited to the things they represent" — evidence: expert-opinion
- **Conditions / limits:** Adding assertions or types is a behaviour or code change. It is not allowed in `audit` and may exceed scope elsewhere. Passage 055 is about build and release procedures, not comments. This principle sets the boundary, and it is not a reason to delete rationale comments next to a check.
- **Tension:** CRA-07, CRA-08 and CRA-10 (comment versus check); CRA-17.
- **Testable as:** partly not covered by comment-edit; restrain / noise_lines (prose that restates an existing assertion or type).

### CRA-19 — Match comment effort to the code's lifespan, and label disposable code
- **Principle:** Throwaway experiments need little commentary. Code headed for production, including early skeletons, needs the same explanation as any production code. If you leave stubbed, temporary or prototype code, say clearly that it is incomplete and must not be relied on.
- **Kind:** when
- **Sources:**
  - [pragmatic-programmer-011](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-011) — supports — "Prototype code shouldn't have much in the way of comments or documentation, although you may produce reams of documentation as a result of your experience with the prototype." — evidence: expert-opinion
  - [pragmatic-programmer-010](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-010) — supports — "It contains all the error checking, structuring, documentation, and self-checking that any piece of production code has." — evidence: expert-opinion
  - [pragmatic-programmer-012](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-012) — supports — "You must make it very clear that this code is disposable, incomplete, and unable to be completed." — evidence: expert-opinion
- **Conditions / limits:** Passage 012 is about telling stakeholders, not about code comments. The lessons from a prototype ("reams of documentation") belong somewhere durable, but the source does not say where. Agents rarely know a file's intended lifespan unless the task states it.
- **Tension:** CRA-14.
- **Testable as:** not covered by comment-edit.

### CRA-20 — Do not leave commented-out code as a silent fix
- **Principle:** If you must disable broken code temporarily, mark it as a deliberate, temporary measure with the reason. Prefer removing dead code, because version control keeps the history.
- **Kind:** avoid
- **Sources:**
  - [pragmatic-programmer-003](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-003) — opposes — "Perhaps you can comment out the offending code or display a not implemented message, or substitute dummy data instead." — evidence: expert-opinion
  - [pragmatic-programmer-003](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-003) — qualifies — "Take some action to prevent further damage and to show that you're on top of the situation." — evidence: expert-opinion
  - [pragmatic-programmer-016](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-016) — supports — "Version control systems keep track of every change you make in your source code and documentation." — evidence: expert-opinion
- **Conditions / limits:** Pragmatic Programmer endorses commenting out code as "boarding up" a broken window, a stopgap that signals awareness. The principle as worded is my synthesis that combines it with the version-control passage, not the authors' rule. Empirical LLM work elsewhere in the corpus (comment-traps) is relevant but outside this group and should be weighed in the ledger.
- **Tension:** Direct tension between "board it up by commenting out" and "remove; VCS remembers" (see Conflicts).
- **Testable as:** restrain / noise_lines (commented-out code counts as new comment lines); not directly covered otherwise.

### CRA-21 — Use the project's vocabulary consistently in comments
- **Principle:** Write comments in the domain's and project's established terms. Use the same word for the same thing everywhere, and do not introduce synonyms for existing concepts.
- **Kind:** what
- **Sources:**
  - [pragmatic-programmer-047](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-047) — supports — "It's important that everyone on the team knows what these words mean and that they use them consistently." — evidence: expert-opinion
  - [pragmatic-programmer-049](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-049) — supports — "It's hard to succeed on a project if users and developers call the same thing by different names" — evidence: expert-opinion
  - [pragmatic-programmer-013](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-013) — supports — "We always try to write code using the vocabulary of the application domain," — evidence: expert-opinion
  - [pragmatic-programmer-054](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-054) — supports — "No two look the same and each uses different terminology." — evidence: expert-opinion
- **Conditions / limits:** The sources address names, glossaries and team documents. Applying them to comment prose is an inference. They recommend a separate shared glossary, which this repository already keeps in `GLOSSARY.md`.
- **Tension:** none found.
- **Testable as:** not covered directly. The anchor-group grader may reward the canonical term incidentally.

### CRA-22 — Build explanation into the code; keep it beside what it explains
- **Principle:** Treat explanation as part of the code change, not a later documentation task. Keep it beside the code it describes, so readers find it and editors update it in the same edit.
- **Kind:** where
- **Sources:**
  - [pragmatic-programmer-004](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "Pragmatic programmers embrace documentation as an integral part of the overall development process." — evidence: expert-opinion
  - [pragmatic-programmer-004](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "And by keeping documentation close at hand in the code itself." — evidence: expert-opinion
  - [pragmatic-programmer-004](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-004) — supports — "And keep code and documentation together." — evidence: expert-opinion
  - [pragmatic-programmer-007](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-007) — qualifies — "look for tools that let you specify the API in some kind of neutral format. These tools will typically generate documentation," — evidence: expert-opinion
  - [pragmatic-programmer-049](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-049) — qualifies — "This implies that the glossary needs to be widely accessible a good argument for online documentation." — evidence: expert-opinion
- **Conditions / limits:** The same authors keep a glossary, API specifications, requirements notes and daybooks outside the code. "Together" is a default for code-level knowledge, not a rule that all documentation becomes comments. This matches the selective replacement framing in `intent.md`.
- **Tension:** CRA-12 (a single authoritative home can be a generated spec, not a comment).
- **Testable as:** capture / misplaced; capture / recall.

### CRA-23 — When code looks strange, look for what drove it before changing it
- **Principle:** When existing code does something oddly, look for the reason first: a nearby comment, an assumption or a constraint. Keep any rationale you find. If you discover the driver and it is not written down, record it.
- **Kind:** maintain
- **Sources:**
  - [pragmatic-programmer-037](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-037) — supports — "When you spot things done in a way that seems strange, jot it down." — evidence: expert-opinion
  - [pragmatic-programmer-037](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-037) — supports — "If you can see what drove them to write code that way, you may find that the job of understanding it becomes a lot easier." — evidence: expert-opinion
  - [pragmatic-programmer-038](../../research/comment-context/sources/pragmatic-programmer/passages.md#pragmatic-programmer-038) — qualifies — "Don't let existing code dictate future code. All code can be replaced if it is no longer appropriate." — evidence: expert-opinion
- **Conditions / limits:** The source describes note-taking for understanding, not commenting. Passage 038 warns against treating existing code as sacrosanct. Preserving a rationale is not the same as preserving the code.
- **Tension:** CRA-13 (fixing stale comments versus over-correcting valid ones).
- **Testable as:** maintain / preserved; audit / preserved.

## Conflicts and open questions

- **Names versus comments.** Pragmatic Programmer (006) holds that a comment restating a fee schedule "simply compensates for some bad naming and layout" and should be replaced by well-named code. Ousterhout (007) argues that long descriptive names are "cryptic and provide less information than a well-written comment", and that comments carry information code cannot. The two are not fully opposed. Pragmatic Programmer still wants why/purpose comments (004), and Ousterhout's target is Martin. They do disagree on whether *what-a-block-does* comments in bodies are worthwhile. Variant axis: allow "what this block accomplishes" comments versus why-only.
- **Breadth of interface documentation.** Pragmatic Programmer says to comment "modules and exported functions" but not "every function, data structure, type declaration". Ousterhout's "more functions means more interfaces to document" assumes that every interface is documented. The extract lacks his interface-comment chapter, so his actual threshold is unknown locally. Variant axis: docstrings on all public entry points versus only non-obvious ones. The restrain family will penalise the former.
- **Prose versus executable checks.** Pragmatic Programmer repeatedly ranks assertions, contracts, types and tests above prose (021, 038, 043, 047). Ousterhout says comment information "can't be represented in code today" and doubts that capturing it in code would be an improvement. For the skill, which output should an agent produce when the evidence holds a constraint? `audit` forbids code changes, so the answer may need to vary by family.
- **Emphasis by repetition versus DRY.** Ousterhout lists repetition of key ideas as a way to emphasise what matters (010). Pragmatic Programmer treats repeated knowledge in docs as a maintenance trap (006). Open question: should a constraint be restated at call sites (higher discoverability) or only at its owner (one place to update)? This bears directly on the `misplaced` metric and the placement pilot (#9).
- **Commented-out code.** Pragmatic Programmer (003) endorses commenting out offending code as a temporary board-up. The same authors' "version control everything" (016) and the empirical LLM work on defective commented-out code elsewhere in the corpus point the other way. The ledger should settle this with the empirical sources, not with Pragmatic Programmer alone.
- **In code or elsewhere.** "Keep code and documentation together" (004) sits beside recommendations for paper daybooks (020), a shared glossary (049), central API specifications that generate documentation (007, 035) and requirements notes (049). Neither source supplies the boundary of what moves into comments. It remains the project's core open question.
- **Second-hand opposition.** The strongest anti-comment voice in this group (Martin: "Comments are always failures") reaches us only as quoted by its critic. Weight it accordingly, or add the primary source.
- **Evidence strength.** Every citation in this group is expert opinion or recalled practice. Neither book offers empirical data on comment effectiveness, and neither addresses LLM agents. Where these principles conflict with empirical LLM findings from other groups, the latter should win on agent behaviour.

## Notable anti-patterns and worked examples

- **Bad: comment that restates a fee schedule** (pragmatic-programmer-006). A block comment "Calculate the fees for this account. Each return check costs$20. If the account is in overdraft for more than three days, charge$10 for each day..." sits above code that does exactly the same. "The customer changes a fee and we have to update both." This is a canonical `maintain` and `restrain` trap.
- **Good (per Pragmatic Programmer): names carry the what** (pragmatic-programmer-006). `calculate_account_fees(account)` with `fees = 20 * account.return_check_count`, reading "as if it was a little story". The authors also note that the 20 should move to configuration. That is policy, not invariant (CRA-09).
- **Bad: a name standing in for a comment** (philosophy-of-software-design-007). `isLeastRelevantMultipleOfNextLargerPrimeFactor`. The OCR splits it as "i sLeastRe1 evantMu1 ti pl eOfNextLargerPri meFactor". This is Ousterhout's counterexample to replacing comments with extracted method names.
- **Good: a decision note template** (pragmatic-programmer-005). "I chose not to make this easy to change because..." records a deliberate trade-off so the future self can audit it.
- **Good: a one-line semantic invariant** (pragmatic-programmer-022). "error in favor of the consumer" for a debit-card switch: a short, unambiguous constraint that guides many error-recovery paths.
- **Bad then good: an intent-free signature** (pragmatic-programmer-047). `deductPercent(double amount)` becomes `applyDiscount(Percentage discount)`. The type documents the 0-100 versus 0.0-1.0 ambiguity, and the name gives intent rather than mechanism.
- **Bad: misleading name after drift** (pragmatic-programmer-047). A routine called "get data really writes data to an archive file". This is the model case for "misleading is worse than meaningless" (CRA-13).
- **Hidden coupling worth explaining** (pragmatic-programmer-026). `read_customer` opens a file that `write_customer` closes through a shared instance variable. A maintainer adds a conditional, skips `write_customer`, and production fails with too many open files. The authors' fix is structural, but if structure cannot change, this ownership fact is exactly what a comment must carry.
- **Convention-only safety** (pragmatic-programmer-034). A semaphore protocol works "only ... because everyone who accesses the pie case agrees on the convention". It is fragile, and the authors move it into the API.
- **False abstraction** (philosophy-of-software-design-003). A `backspace` method hides which characters are deleted, yet callers must know. Developers then read the implementation anyway. This is an interface that hides what matters (CRA-06).
- **Coincidence, not duplication** (pragmatic-programmer-006). `validate_age` and `validate_quantity` share a body but represent different knowledge. Merging them, or their comments, would be wrong.
- **Localised, deliberate DRY violation** (pragmatic-programmer-006). Caching a derived `length` in `Line` for performance: "The trick is to localize the impact." A cache like this is a classic place for a short why comment.
- **Prototype intent comment** (pragmatic-programmer-037). In the empty buffer, one sentence saying what you want to learn or do, deleted with the prototype.
