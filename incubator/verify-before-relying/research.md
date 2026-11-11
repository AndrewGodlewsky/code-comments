# verify-before-relying: research

Ideation candidate C2 ([candidates](../ideation/2026-11-11-candidates.json)). The coordinator of #50
narrowed it to comments, docstrings and docs that new code depends on; instruction files are out
of scope. Anything not quoted from a source is our interpretation. A rule with no source is
labelled a hypothesis.

## Question

New code sometimes depends on what a comment, docstring or doc says existing code does: units,
rounding, ordering, return shape, error behaviour. Should the agent check the claim against the
implementation and tests first, build on what the code really does, and settle a conflict by the
kind of claim? A description loses to the code. A requirement or outside fact is kept and
reported. And does writing this down beat the bare model, a one-line reminder, and the shipped
skill's "Treat existing comments as claims" line?

## Sources

All accessed 2026-11-11. Web sources were opened and their quotes checked on the page.

**Agents and models misled by prose**
- **S1.** Xu and Wu, *Stale Instruction Files Override the Code in Coding Agents: A One-Sentence
  Fix*, [arXiv 2610.30571v1](https://arxiv.org/html/2610.30571v1). Claude Code (Sonnet 5.5) and
  Codex. Quotes:
  - "Without the sentence, 90.1% of the agents’ choices followed the stale file." "Claude Code
    pointed out the conflict in 79 of 80 runs and still followed the file." "Codex CLI rewrote the
    existing code to match the file in 20 of 80 runs," and "the project's own tests then failed
    in 17 of them."
  - The fix: "When a repository’s documentation and its existing code disagree, follow the
    conventions used in the existing code," "and in your final reply point out each inconsistency
    you found between the documentation and the code." It "raised the share of choices that
    follow the code from 4.2% to 91.4%".
  - The authors' explanation: "the instruction file reaches the model as an instruction and the
    code as tool output". Only auto-loaded files were studied.
- **S2.** Lam et al., *CodeCrash* v3, [arXiv 2504.14119v3](https://arxiv.org/html/2504.14119v3).
  Quotes: "models often shortcut reasoning by over-relying on NL cues"; the hint perturbation
  gives "high-level incorrect hints about program outputs". Table 1, misleading hints, relative
  change (Crux / LCB): Claude 3.5 Haiku −27.5% / −53.3%; Claude 3.5 Sonnet −14.4% / −43.4%.
- **S3.** Xia et al., *When Comments Mislead* (ASE 2026). Abstract only, with no numbers
  ([abstract page](https://conf.researchr.org/details/ase-2026/ase-2026-research-track/29/When-Comments-Mislead-An-Empirical-Study-of-Outdated-Comments-in-LLM-Based-Code-Comp)).
  Quote: outdated comments "can bias generated code toward historical implementations,".
- **S4.** Huang et al., *Comment Traps*, [arXiv 2512.20334v2](https://arxiv.org/html/2512.20334v2).
  Quotes: "Even with explicit instructions to ignore the defective CO code, the reduction in
  defects does not exceed 21.84 percent." "AI coding assistants do not merely replicate defective
  CO code verbatim; rather, they exhibit reasoning capabilities."
- **S5.** Macke and Doyle (2024), [passages](../../docs/research/comment-context/sources/documentation-llm-understanding/passages.md).
  Their "incorrect" documentation is a random docstring: "the random comments scenario performs
  worse than any other scenario on both GPT-3.5 and 4". Vitale et al. (2026),
  [passages](../../docs/research/comment-context/sources/comments-bug-fixing/passages.md):
  "Comments generated from buggy code do not help and can mislead automated bug-fixing models."
- **S6.** Sharma et al., *Towards Understanding Sycophancy in Language Models*, [arXiv 2310.13548v4](https://arxiv.org/html/2310.13548v4),
  §3.4 "AI Assistant Responses Sometimes Mimic User Mistakes". Quote: "We find the AI assistants
  frequently provide responses that incorrectly attribute the poem to the poet suggested by the
  user".
- **S7.** Vasilopoulos, *Codified Context*, [arXiv 2602.20478](https://arxiv.org/html/2602.20478)
  (a practitioner report). Quote: a stale spec caused "the agent to wire damage calculations
  through a deprecated path."

**Checking claims, and prior art**
- **S8.** Kang, Milliken and Yoo, [arXiv 2406.14836](https://arxiv.org/abs/2406.14836). Of
  existing consistency detectors: "we perform experiments demonstrating they have no
  statistically significant relationship with comment accuracy". Running tests generated from the
  comment "has a robust statistical relationship with comment accuracy".
- **S9.** Kiecker et al., *CASCADE* (to appear at FSE 2026), [arXiv 2604.19400](https://arxiv.org/abs/2604.19400).
  Quotes: "false positives carry serious consequences: wasting developer time and discouraging
  practical adoption." Its dataset holds "71 inconsistent and 814 consistent code-documentation
  pairs".
- **S10.** Existing checkers. [`doctest`](https://docs.python.org/3/library/doctest.html): "To
  check that a module’s docstrings are up-to-date by verifying that all interactive examples still
  work as documented." Ruff [DOC502](https://docs.astral.sh/ruff/rules/docstring-extraneous-exception/)
  (preview): "Checks for function docstrings that state that exceptions could be raised even
  though they are not directly raised in the function body." Panthaplackel et al., AAAI 2021
  ([arXiv 2010.01625](https://arxiv.org/abs/2010.01625)): "we aim to detect whether a comment
  becomes inconsistent as a result of changes to the corresponding body of code,". Claude Code's
  [memory docs](https://code.claude.com/docs/en/memory): `/doctor prompt-audit` looks for
  instruction "files that contradict each other".

**Which side is right**
- **S11.** C4RLLaMA discussion, [comment-context-deep-dive.md](../../docs/research/comment-context-deep-dive.md)
  line 107. Quote: "nor can code consistency alone decide whether code violated the requirement or
  the comment became obsolete. That choice needs an independent statement of intended behavior."
- **S12.** *Software Engineering at Google*, passage ch11-002
  ([passages](../../docs/research/comment-context/sources/software-engineering-at-google/passages.md)).
  Quote: "If you want to know what the code does in a particular case, look at the test for that
  case."
- **S13.** *The Pragmatic Programmer*, passage 038, from an unverified machine transcript
  ([passages](../../docs/research/comment-context/sources/pragmatic-programmer/passages.md)). Quotes:
  "For routines you call, rely only on documented behavior. If you can't, for whatever reason,
  then document your assumption well." "Don't guess. Actually try it."
- **S14.** [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119): MUST "mean that the definition is
  an absolute requirement of the specification." [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174):
  "The words have the meanings specified herein only when they are in all capitals."
- **S15.** Python [`decimal`](https://docs.python.org/3/library/decimal.html): the default context
  has "Context.rounding=ROUND_HALF_EVEN", and for quantize "if neither argument is given the
  rounding mode of the current thread's context is used."

**Repository evidence and nearby skills**
- **S16.** The [shipped skill](../../plugins/code-comments/skills/code-comments/SKILL.md): "Treat
  existing comments as claims. Check them against the code, tests and task." "Take the intended
  contract from evidence of intent, not from the code being fixed." It keeps an outside fact "as
  written", and says "Leave valid comments word for word."
- **S17.** [principles.md](../../docs/skill/principles.md) P-21 is grade D: "no study tests whether
  an instruction to verify reduces the harm". [inline-only-tradeoffs.md](../../docs/skill/inline-only-tradeoffs.md)
  C4 plans to "Record whether the reader followed a stale claim, noticed the conflict, or checked
  the code". Its drift steps are still future work in [the seq-smoke report](../../docs/evaluation/report-2026-11-07-seq-smoke.md)
  (line 67).
- **S18.** Hygiene iteration 5, `change-contradicts-comment/*/run-*/grading.json`, recounted here.
  The true Geoway quota comment was kept in 5 of 5 no-skill runs, 5 of 5 skill runs and 2 of 5
  reminder runs. All 15 replies flagged the conflict. [hygiene-skill.md](../../docs/skill/hygiene-skill.md):
  "Without the skill, both models already fix renames and simple stale clauses, leave accurate
  comments alone".
- **S19.** [report-2026-11-07.md](../../docs/evaluation/report-2026-11-07.md): the tournament's
  stale-docstring cases were comment-only fixes ("A docstring says the method returns None and
  matches case-sensitively; the code raises and ignores case."). Sonnet's control passed 0.87 of
  audit cases.
- **S20.** [Hygiene README](../../evaluation/hygiene/README.md): "Subagents inherit the worktree's
  project instructions." In round 1, "weaker models given the skill rewrote valid comments."
  Iteration-5 benchmark.md: "one Haiku with_skill run also read an AGENTS.md outside its
  repository"; some runs "wrote scratch files outside their outputs folder".
- **S21.** Installed skills (local plugin cache): superpowers `verification-before-completion`,
  "NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE"; `karpathy-guidelines`, "State your
  assumptions explicitly. If uncertain, ask."

## Findings

Observations only. Interpretation follows in the next sections.

1. **Wrong prose in context harms code reasoning** (S2, S5), usually more for weaker models; S3
   and S7 show only the direction. These studies were single prompts on older models, with the
   wrong text injected or random.
2. **Noticing a conflict did not stop agents following the prose.** In an agent harness with this
   model family, a stale instruction file beat the code 90.1% of the time, even though Claude Code
   flagged the conflict in 79 of 80 runs (S1). The authors blame the channel; comments arrive as
   tool output.
3. **Telling a model to ignore bad context removed at most 21.84% of the harm** (S4).
4. **Running code tracks comment accuracy; static detectors do not** (S8). CASCADE also runs code,
   and it treats false alarms as the main cost. In its data, consistent pairs outnumber
   inconsistent ones more than 11 to 1 (S9).
5. **Which side is right needs evidence of intent** (S11). Practitioners treat tests as the record
   of what code does (S12). The Pragmatic Programmer says to rely only on documented behaviour
   (S13), the opposite of "build on what the code does".
6. **Assistants repeat a user's false premise.** The evidence is 2023 assistants answering about
   poems, not code (S6).
7. **Decimal's default rounding is half-even** (S15). A hand-written `quantize(Decimal("0.01"))`
   is therefore half-even without anyone choosing it.
8. **No repository eval has scored new code built on a stale claim.** Stale docstrings were fixed
   only in comment-only passes (S19). P-21 is untested, and C4's measure never ran (S17).
9. **A "fix what is false" reminder deleted a true outside fact in 3 of 5 runs.** The bare model
   kept it in 5 of 5 and flagged the conflict every time (S18).
10. **Eval subagents can see an AGENTS.md from outside the fixture** (S20).

**Prior art, and how this skill differs.** Checkers and detectors (S8, S9, S10) check comments in
bulk or at commit time and report mismatches. This skill acts when the agent's own new code is
about to rely on a claim, changes what gets built, and stores nothing. Xu and Wu's sentence (S1)
says "code wins" for everything; this skill sorts claims by kind, so a requirement or outside fact
survives (S11, S18). verification-before-completion (S21) checks the agent's own claims of
success, not the claims it reads. The shipped skill (S16) has the core lines, aimed at comments
the agent's change makes false. It never says to check a claim before building on it, to follow a
helper into its body, or to correct the user's premise.

## What this means for the skill's rules

The skill is instructions only. Each rule is traced to a source or labelled a hypothesis.

1. **Check only what the new code relies on.** That means units, rounding, ordering, return
   shape, values on failure, raised errors, and what a named helper does. Wrong claims about
   outputs mislead most (S2), and most claims are true, so checking everything costs (S9). The
   list itself is a hypothesis.
2. **Check the body, not the description.** Follow helpers into other files and read the tests
   that call them (S12). If it is still unclear, run a throwaway probe that leaves no files (S13;
   S8 and S9 favour running code; S20 records stray files).
3. **Name the action, not caution.** Noticing did not change behaviour (S1), and "ignore it" did
   little (S4). Say: build on what the code does, as its tests pin it. That this beats a general
   warning is a hypothesis.
4. **Classify the claim before settling a conflict.** A description states what this code does
   ("returns", "comes back 50 per page"). A requirement says must, never or required, or cites a
   policy, law or ticket (S14). An outside fact is about an external party, such as a vendor quota.
   Deciding needs evidence of intent (S11). Treating lowercase "must" as a requirement goes beyond
   RFC 8174, so that part is a hypothesis.
5. **A description loses to the code.** Build on the code and correct the false text in place
   (S16). Never rewrite working code to match the text: Codex did, and broke tests in 17 of 20
   such runs (S1). This is ADR 0001 reason 1.
6. **A requirement or outside fact keeps its words** (S18). Change the code to meet it only when
   the task is about that behaviour; otherwise report the conflict. A test that pins behaviour
   shows intent, so leave a pinned helper alone and meet the new requirement beside it (S12).
7. **Unpinned behaviour may be accidental** (S13). If the code is the only evidence, build on it
   and state the assumption in the reply. Hypothesis.
8. **If the user's request repeats a false claim,** deliver what the user plainly wants and say
   first that the premise is wrong, with file:line (S6, S1). That this transfers to code is a
   hypothesis.
9. **Trust a true claim.** Leave it word for word. Add no defensive conversion and no confirmation
   question, and never call it stale (S9, S16, S20). karpathy-guidelines' "If uncertain, ask" (S21)
   pulls the other way, but a claim that checks out is not uncertain.
10. **Report each false claim** with file:line and what the code really does (S1). Add no comment
    beyond the correction (S16).

## What this means for the eval

**Likely bare-model failures (hypotheses until the gate runs)**
- `request-quotes-stale-docstring`: the false claim arrives as the user's premise, through the
  instruction channel (S1, S6). This is the likeliest case to separate the arms.
- `helper-docstring-lies`: when the request names `round_cents`, a literal agent calls it and fails
  half-up. "Follow the code" pushes the same way, because the code rounds half-even.
- `docs-sync-keeps-requirements`: "bring it in line with the code" invites rewriting the privacy
  rule and the quota. The reminder over-applied in S18, so expect it to fail here. The shipped
  skill's outside-fact line may tie.

**Likely already handled**
- Trusting a true comment (S18). The true twins guard against paranoia; they will not show a gain.
- Flagging a conflict in the reply (S1, S18). Reply keywords will barely separate the arms, so
  weight the hidden tests.
- `stale-cents-comment` may sit at ceiling, because hygiene prompts list every input file,
  including the test. Let the gate decide whether to move the evidence.

**Design notes**
- **Gate first.** Run `without_skill` on Haiku and Sonnet before anything else. A case every bare
  run passes cannot discriminate.
- **Core checks are hidden tests** on the new code: the fee turns `Decimal("10.00")` into
  `Decimal("10.30")`; the CLI, run as a subprocess, exits 2 with "invalid date" on stderr; the
  invoice total of `[Decimal("0.125")]` is `Decimal("0.13")`.
- **Preservation:** each true or requirement sentence stays byte-identical, and `same_code` holds
  for the helper and the model.
- **True twins:** the claim's file stays byte-identical, the new code has no `/ 100` or `Decimal(`
  conversion, and the reply makes no "stale" claim (a low-weight heuristic).
- **`helper-docstring-lies`:** record whether `invoice_total` calls `round_cents`. That separates
  trusting the docstring from not knowing quantize's default (S15).
- **S1's pattern:** score apart any run that flags the false claim but still fails the hidden test.
- **Clean-up:** add a `new_files` check for probe leftovers, and drop instruction-file cases (S20).
- **The two extra cases, both true twins:**
  - `helper-docstring-true`: `round_cents` really is half-up, and the request names it. Trap:
    bypassing it, or rewording its docstring.
  - `request-quotes-true-docstring`: `parse_date` really returns None. Trap: a dead
    `try/except ValueError`, or calling the docstring wrong.
- **Held out:** both request-quote cases, so the held-out set tests an unseen channel in both
  directions.
- **Reminder** (`arms.json`): "If a comment, docstring or doc disagrees with the code, follow the
  code and tell me about the conflict." It is close to S1's measured sentence.
- **Shipped-skill arm:** it decides whether this is a skill or a #21/#48 variant. Report a tie.

## Counterevidence and limits

- **Headroom may be small.** S1 blames the instruction channel, and docstrings arrive as tool
  output. Its one sentence reached 91.4%, so the reminder may tie.
- **The evidence is dated or indirect.** S2 and S5 are single prompts on 2024-era models with no
  tests to hand. Reasoning models were mostly robust (S2), assistants reason rather than copy (S4),
  and S6 is 2023 assistants on poems.
- **Building on code can be programming by coincidence** (S13). Rule 7 reports the risk; it does
  not remove it.
- **False alarms dominate** when most claims are true (S9). A verify rule can breed paranoia.
- **Sorting claims by modal verbs is a heuristic** (S14). Real docs mix description and requirement
  in one sentence.
- **Costs:** verifying spends tokens (P-21's stated condition). The hygiene skill added about 6%
  (hygiene-skill.md).
- **Activation:** the shipped skill loaded on its own in 0 of 18 Haiku and 3 of 18 Sonnet runs
  (hygiene-skill.md). Requests rarely say "check the docstring", and this eval forces the read.
- **No performance claim** follows from any of this: small cases, few runs, one model family.

## Open questions

1. With tools and tests at hand, do Sonnet 5.5 and Haiku 5.5 build on a stale docstring at all
   (the gate)? Does the shipped skill's "Treat existing comments as claims" line already fix it?
2. When no test or request decides, should the agent build on the code and report, or ask first?
3. Is the probe rule worth its cost? Count the runs where a probe changed the outcome. A
   DOC502-style checker (S10) stays deferred until transcripts show misses it would catch.
4. Should the agent correct a false docstring it was not asked to touch, or only report it? The
   coordinator says correct it. The grader should pass both and score them apart.
