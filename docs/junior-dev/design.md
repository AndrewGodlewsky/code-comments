# Junior-dev: design

Status: draft for the user's approval, 2026-11-12. Tracking issue:
[#52](https://github.com/AndrewGodlewsky/code-comments/issues/52). The decisions marked
**user** come from the design interview on 2026-11-12. The ones marked **our call** were
made by the designing agent, and the user can overturn them. The evidence review is in
[research-2026-11-12.md](research-2026-11-12.md), with finding ids such as L7 or M2.

## Why this exists

The user and the people they work with often write plans, specs and diagrams with
cheaper models (Haiku 5.5, Sonnet 5.5) to save tokens. Those models tend to produce
artifacts that are less detailed, less thought through and harder to understand than a
stronger model's, especially for architecture. **user**

Junior-dev is meant to raise the quality of those artifacts. When an agent finishes a
plan or diagram, a separate subagent reads only that artifact and plays a junior
developer: smart and technical, but with no experience in this stack or this software.
It asks the author rounds of questions about whatever it does not understand: how a
part works, why it is this way, what happens next. The author has to explain every step.
After each round, the author asks itself whether that part could be simpler, cleaner,
clearer or shown a better way, and edits the artifact if so. **user**

**Quality means clarity.** The user's definition: the best plans and diagrams are simple
and laid out cleanly, step by step, so that someone smart and technical who does not know
the project or the stack can read them quickly and understand what is going on. Better
does not mean longer or shorter. The test is whether a capable reader without the context
understands the artifact. **user**

**This is a hypothesis.** The user wants to know whether the idea is useful. The evidence
review found the premise supported: LLM architecture diagrams get the relationships
between components far more wrong than the components themselves (A1). It found the
mechanism untested, and some evidence that weaker models make poorer use of the
information they get (L7). Positive, null and negative results are all useful, and the
final report must be able to show any of them.

## What it is not

- **Not a correctness checker.** The junior never judges whether the plan is right and
  cannot check facts. It applies pressure by asking about the logic. **user**
- **Not adversarial and not a critic.** It asks; it does not grade or argue. **user**
- **Not plan mode.** It runs on artifacts that get written, not on Claude Code's plan-mode
  approval step. **user**

## Goals

1. A Claude Code plugin, `junior-dev`, that runs this questioning loop on a plan or
   diagram once it has been created, without the user having to ask.
2. Evidence, with Haiku 5.5 and Sonnet 5.5 as the main authors (and some Opus 5.5), of
   whether it makes artifacts clearer, what it costs, and which variant of it works best.
   The user wants many variations benchmarked and a recommendation from the data. **user**
3. A skill whose text has been hill-climbed against that eval.

## Non-goals

- Visual diagrams (Figma, FigJam, images, HTML) in this version. Text artifacts only:
  plan and spec documents, step plans, Mermaid diagrams, ASCII diagrams. **our call,
  user agreed**
- A build-and-test evaluation of code written from the plans. The user defined success
  as clarity. **user**
- Older models. Only the 5.5 family is used. **user**
- Any change to the `code-comments` plugin, or to #50's incubator work.

## Anti-goals: failures even if it technically works

- The artifact gets longer without getting clearer.
- The author invents reasons to satisfy the junior. An author who cannot defend a
  decision must say so instead (see Behaviour, step 4). **user**
- Clarifying the artifact changes or drops what it was meant to do.
- The loop stops partway through to ask the user something. **user**
- The junior sees anything besides the artifact. **user**
- A benefit is reported without the cost comparison. The user's motive is saving
  tokens, so "Haiku plus Junior-dev" has to be compared on cost with simply using a
  stronger model. **our call**

## Behaviour

1. **Trigger.** It runs when a plan, diagram or similar artifact is created. **user**
   Two mechanisms are built and measured against each other: the skill description
   alone, and plugin hooks. The data decides which ships (see Evaluation, layer 2).
   **user** The research gives reason to doubt the description alone: in this repo, Haiku
   loaded the code-comments skill in 0 of 18 runs where it should have (M1), and plugin
   hooks fire whether or not a skill loads (M2).
2. **Input to the junior.** The artifact text and nothing else: no repository, no
   conversation, no task description and no tools. The artifact has to carry its full
   intent on its own. **user** It also omits any wording such as "this plan is complete"
   (A4). **our call**
3. **Questions.** The junior asks batches of questions, in rounds, about what it does not
   understand, as a junior developer would. Each question points to the step, node or
   edge it is about. **user** (the pointing is **our call**). The junior's exact procedure
   is a variable in the eval. One candidate traces a request from start to finish and
   asks, for each step, what triggers it, what data moves, who owns the state and what
   happens on failure (A1, L6, L11).
4. **Answers.** The author answers every question. It must be able to defend each
   decision with a reason. If it has no reason, or is not sure, it writes that down
   rather than inventing one. **user** It may check the repository or its own context
   before answering, which the research found to be the strongest lever (L1, L7). The
   junior still never sees those sources. **our call**
5. **Revise.** After each round, the author decides for each question whether the
   artifact needs to change: simplify a part, make it cleaner or clearer, restructure
   it, or show the information differently. For a diagram that can mean fewer or
   different nodes, a different diagram type, or a split. **user** Anything learned has
   to end up in the artifact, not just in the answers, because the final check reads only
   the artifact. **our call**
6. **Finish line: teach-back.** When the junior has no more questions, a junior explains
   the system back, step by step and in its own words. The explanation has to be correct.
   If it is not, the artifact is still too unclear or too complicated at that point. The
   author revises it, and the questioning continues. **user** The teach-back comes from a
   fresh junior that reads only the revised artifact, because the original junior learned
   from the conversation (user accepted this). The user also asked for a few teach-back
   styles to be benchmarked. **user**
7. **Safety cap.** About 6 rounds at most, so that cost cannot run away. The eval measures
   how much each round adds and sets the final number. **user**
8. **Report to the user.** At the end the user gets two lists: what changed and why, and
   the holes, meaning the questions the author could not answer or is unsure about. The
   loop never pauses to ask the user. **user**

## Plugin layout

Everything for Junior-dev is kept apart from the code-comments material. **user agreed**

```text
plugins/junior-dev/           what gets installed
  .claude-plugin/plugin.json
  skills/junior-dev/SKILL.md  the loop, for the main agent
  agents/junior-dev.md        the junior subagent: minimal tools, model chosen by the eval
  hooks/hooks.json, scripts/  only if hooks win the trigger comparison
  evals/                      activation cases for `claude plugin eval`
  README.md
evaluation/junior-dev/        cases, graders, run scripts, iteration results
docs/junior-dev/              research, this design, the evidence report
```

The plugin is listed in the root `.claude-plugin/marketplace.json` next to `code-comments`.

**Mechanics to confirm with a spike before relying on them** (M2 and the open questions in
the research):

- whether a plugin subagent can have no tools at all (leaving `tools` out gives it every tool);
- whether a subagent can be resumed with `SendMessage` under `claude -p`, or each round needs
  a fresh subagent given the transcript so far;
- what a PostToolUse hook receives for Write and Edit (the field names);
- whether plugin hooks fire under `claude -p --plugin-dir` (they do not under `--bare`);
- how a Stop hook can find out which files were written (its input does not list them, so a
  PostToolUse hook may need to record them in a marker file).

## Evaluation

### Cases

Opus 5.5 generates the cases, varied across the board. **user** They range from complex
architecture layouts to simple diagrams of how user credentials are stored and handled,
with several kinds of plan and diagram and more than one variation of each. **user** Our
call on the spread, for 18 to 24 cases:

- architecture: multi-service, event-driven, multi-region;
- migrations and refactors;
- data pipelines;
- authentication, sessions and secret handling (several simple ones);
- deployment and infrastructure layouts;
- small feature plans;
- formats: prose step plans, checklists, Mermaid flowcharts, sequence, state and ER
  diagrams, and ASCII diagrams.

Each case has:

- **a brief**, which the author sees: the request, plus any requirements, constraints or
  description of the existing system;
- **a hidden quiz** of 8 to 12 questions about how the system works, which the author and
  the skill never see. Two kinds of question:
  - questions the brief settles, graded against a fixed key;
  - questions about the author's own design choices, graded against the author's own
    answers. The author records those answers, with full context, before any reader sees
    the artifact. A valid design that differs from the case writer's design is therefore
    not penalised. **our call**
- **an optional starting artifact**, for the seeded mode below.

Three modes:

- **Natural:** the author writes the artifact from the brief. This is the real use.
- **Seeded:** the author starts from a given artifact that is correct but unclear. This
  isolates the questioning step.
- **Null:** the starting artifact is already clear, so little should change.

A few briefs leave one point deliberately undecided, to test whether the author reports it
as a hole or invents an answer.

The cases are split about 60/40 into a development set and a held-out set, with each case
family kept on one side. **our call**

### Measures

- **Primary: reader comprehension.** Fresh reader agents, given only the final artifact,
  answer the quiz. Their model and prompt differ from the junior's, so the skill is not
  being trained to the test. Score: the share of items answered correctly, averaged
  over at least two readers (Haiku and Sonnet). An answer of "not stated" counts as wrong.
  **our call**, implementing the user's test.
- **Secondary: blind clarity comparison.** A judge sees two artifacts for the same brief,
  without knowing which arm produced either. It is asked which one a capable newcomer would
  understand faster and more correctly. It is told explicitly that length is not a merit,
  and each pair is run in both orders (E1).
- **Honesty:** for the deliberately undecided points, whether the report lists them as holes
  or the artifact invents an answer.
- **Guardrails:**
  - What the brief requires is still in the artifact.
  - Null cases do not get worse.
  - Diagrams still parse (Mermaid is checked mechanically).
- **Cost and length:** tokens per run, and words, nodes and edges per artifact, reported but
  not scored. The headline comparison puts them next to clarity.

The research recommends a judge from a non-Claude model family (E1). None is available
here, so the main measure is per-item quiz grading with mechanical checks where possible.
The readers are blind to the arm and use several Claude models. The user will be offered
10 to 20 blinded before/after pairs to rate, as a check on the judge.

**The graders are tested before any paid run:**

- The case's reference artifact scores high.
- A seeded unclear artifact scores lower.
- Padding earns nothing.
- Information given only in chat, and not in the artifact, earns nothing.

### Arms

- **NoReview:** the artifact as first written.
- **SelfReview:** the author rereads and revises for clarity, with the same token budget
  as Junior.
- **JuniorPrompt:** a one-line instruction in the original request to write it so a junior
  new to the stack could follow it.
- **Critic:** a generic reviewer that sees only the artifact.
- **Junior:** the treatment, in variants.
  - teach-back style: none, the same junior, a fresh junior;
  - the junior's model: Haiku, Sonnet or Opus;
  - the round cap: 2, 4 or 6;
  - the batch size;
  - the question procedure: free, or structured as a trace.
- **JuniorFull:** the junior also sees the brief. This tests whether isolation matters.
- **Reference points:** Sonnet alone and Opus alone (NoReview), for the cost-versus-clarity
  comparison with Haiku plus Junior.

The comparisons that decide the question are:

- Junior against SelfReview and JuniorPrompt: is it the loop, or just the instruction?
- Junior against Critic: does the junior framing matter?
- Junior against JuniorFull: does isolation matter?
- Haiku or Sonnet plus Junior against Opus alone: on clarity, and on cost.

Beating NoReview alone proves nothing (L7, L12).

### Two layers of runs

1. **The method tournament.** It runs inside this session, on the user's subscription. A
   workflow script plays the loop, with each role an agent on a set model. This compares
   the variants and controls cheaply and is where the hill climb happens: change one thing
   per iteration, run 3 times per arm per case, read the transcripts, keep a change only if
   Junior minus SelfReview improves and no guardrail gets worse, and check against the
   held-out set at milestones. **user** approved subscription use.
2. **Plugin runs.** Headless `claude -p` with the plugin installed, on the user's
   subscription, **capped at $10 in total**, with a pilot of about $1 to $2 first to measure
   the cost per run. **user** They measure two things:
   - **Activation:** description alone against hooks, on prompts that should and should not
     trigger it, with Haiku and Sonnet. `claude plugin eval` is used where it fits.
   - **Fidelity:** whether a Haiku or Sonnet main agent actually carries out the loop as the
     skill describes. That means the junior got only the artifact, the rounds happened, the
     teach-back ran, and the report lists the changes and the holes. Graded from the
     transcripts.

Actual cost is reported against the estimate, as `intent.md` requires.

### Analysis

Each case runs 3 times per arm. Differences are compared within each case, and confidence
intervals are bootstrapped over cases. This is fixed in advance. **our call**

- The primary comparison is Junior minus SelfReview on reader comprehension, for each
  author model.
- A gain of 10 points or more in comprehension counts as worth having.
- With 18 to 24 cases, only effects of roughly 15 points can be detected reliably (E2).
  The report says so.

### Keeping the test honest

- The agents that write the cases and quizzes never see the skill.
- The agents that write or climb the skill never see the quizzes or keys. They get only
  scores and the junior transcripts.
- A lint check, modelled on `scripts/lint_skills.py`, fails if the skill copies an
  8-word run from the eval text.

## Deliverables

- the plugin, listed in the marketplace;
- the eval harness, cases and graders, with their self-tests in the test suite;
- the iteration results;
- an evidence report per model: what improved, what did not, the cost, and a recommended
  default configuration;
- `intent.md`, `architecture.md`, `README.md` and the research index updated to point to
  Junior-dev.

## Left to the builder

- the exact rule that decides whether a written file is a plan or diagram;
- the wording of the junior's procedure and of the skill;
- the format of the final report;
- the quiz size within 8 to 12;
- the harness code, reusing `evaluation/skill_eval/` and the skill-creator iteration layout
  where they fit.
