---
name: junior-dev
description: Use right after you write or substantially rewrite a plan, spec, design, architecture or diagram file (Markdown plans, Mermaid or ASCII diagrams), before you act on it, hand it on or report it done. A junior developer who sees only that file asks you rounds of questions until a fresh junior can explain it back correctly. You answer each question, defend or flag every decision, and make the file simpler and clearer. Ends with a report of what changed and the holes that remain.
---

# Junior-dev

A plan or diagram is clear when someone smart and technical, who does not know this project
or this stack, can read it and explain how it works. This skill tests that directly. A
junior developer reads only your file and asks you about whatever they do not understand.
You answer, and you change the file wherever their questions show it is unclear,
incomplete or more complicated than it needs to be.

The junior never sees your conversation, the code or your answers' sources. The helper
script controls what the junior sees, so always go through it.

## When to run it

- You have just written or substantially rewritten a plan, spec, design or architecture
  document, or a text diagram. Run it before you implement the plan, hand it to anyone or
  report it done.
- A junior-dev hook reminder names a file.

Skip it for tiny files, such as a five-line checklist, and for files you did not create or
substantially change in this session.

## The loop

Run every command from the project root. If `python` is not found, use `python3`. Keep the
quotes: paths may contain spaces. `<state>` is the folder that `start` prints.

1. **Start.**

   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/junior.py" start "<file>"
   ```

2. **Ask.** This prints the junior's questions as `Q<n> (about: ...): ...`.

   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/junior.py" ask "<state>"
   ```

3. **Fix only what is wrong or missing, for now.** Each question shows you where a newcomer
   got stuck. You will rewrite the whole file once, at step 6, with every question in front
   of you, so do not restructure it yet. During the rounds:
   - If a question shows that part of the plan is actually wrong, fix it in the file.
   - If the main flow is missing something a reader needs, add it in one short line at the
     step it belongs to.
   - If it is a "what happens if this fails" question, decide the simplest handling the brief
     allows. Do not add a new mechanism, such as a lock, lease, retry queue or takeover rule,
     unless the brief requires it.
   - Otherwise, answer it in your answers file and leave the file alone.
4. **Write your answers** to `<state>/answers.md`, with one line per question in exactly
   this form:
   - `Q<n> [checked]: <answer>` when you verified it in the code, the docs or the files.
   - `Q<n> [decided]: <answer and the reason>` when it is a design decision you made and can
     defend.
   - `Q<n> [unknown]: <what is not known>` when you do not know, or have no reason you can
     defend. Say so plainly. **Never invent a reason.** If it matters to the plan, add one
     short line for it under an "Open questions" heading at the end of the file, instead of
     guessing.

   After the answers, add one line per change you made: `Changed: <what changed and why>`.
   Then submit, and go back to step 2:

   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/junior.py" answer "<state>" "<state>/answers.md"
   ```

5. **Stop asking** when `ask` prints `NO MORE QUESTIONS` or `ROUND CAP REACHED`.
6. **Rewrite the file once, for a newcomer.** Read every question the junior asked, and your
   answers, in `<state>/state.json` or your answers files. Each question is a place where a
   newcomer got stuck. Rewrite the whole file so that a newcomer would not need to ask
   anything about the main flow. Keep its intent and everything the main flow needs.
   - A question about what a name, tool or term means: define it in one plain line in the
     terms, even when it is a standard part of this stack.
   - A question about why a part is there: give the reason in one short clause, where that
     part appears.
   - A question about a step: answer it in that step.
   - A question about a detail the plan does not need yet, such as an exact format, a library
     choice or a rare edge case: leave it out. Your answer stays in the report.
   - Cut what a reader does not need to follow the main flow, merge rules that say the same
     thing, and replace several mechanisms with one simple one wherever the brief allows.

   Lay it out in this order:
   1. One short paragraph: what this is, how the main flow goes from start to finish, and
      why it is shaped that way. If it changes an existing system, first say in a sentence
      or two how that system works today.
   2. The terms a newcomer needs, each defined in one line, in plain words.
   3. The steps, numbered, in the order they happen. For each step say what starts it, what
      it does, which part keeps its data, and what it does when it goes wrong.
   4. What happens when things fail, at each step or in one table.
   5. The open questions, at the end.

   Keep how the system runs apart from how you build or roll it out, in separate sections.
   Write plainly: short sentences, one idea each. Write each step so it stands alone, and
   avoid codes such as R3 or Q7 that send the reader elsewhere to look things up. Aim to
   keep the file within about one and a half times its first length; a longer file is not a
   clearer one. A diagram keeps its diagram form: put the summary and the terms just before
   it, and the notes just after it.

   If `ask` printed `ROUND CAP REACHED`, go on to step 8 after this rewrite.
7. **Teach-back.** A fresh junior that sees only the rewritten file explains it back:

   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/junior.py" teachback "<state>"
   ```

   Compare that explanation with what you intended, for the main flow and its main failure
   cases. Judge the explanation, not its list of gaps: a gap about a detail the plan does not
   need to decide is not a misreading. Do not add it to the file.
   - If the explanation gets a step of the main flow wrong, leaves one out, or cannot explain
     one, the file is still unclear at that point. Fix the file there, simply, write the
     misreadings to `<state>/notes.md`, run this, then go back to step 2:

     ```
     python "${CLAUDE_PLUGIN_ROOT}/scripts/junior.py" verdict "<state>" wrong --notes "<state>/notes.md"
     ```

   - If it is right, run this:

     ```
     python "${CLAUDE_PLUGIN_ROOT}/scripts/junior.py" verdict "<state>" correct
     ```

   The file the junior explained correctly is the file you hand on. Do not rewrite it again
   after a correct teach-back.
8. **Report.**

   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/junior.py" report "<state>"
   ```

9. **Tell the user.** Give them the report: what changed and why, what you cut or merged,
   and the holes, meaning the questions you could not answer or are unsure about. Keep it
   short.

## Rules

- Never stop the loop to ask the user anything. Unknowns go into the report.
- Do not argue with the junior. What a reader needs to follow the main flow goes in the
  file, because the teach-back reads only the file.
- Keep the plan's intent. Clarifying must not quietly change what the plan does. When a
  question reveals a real problem and you change the plan, record it as `Changed:`.
- Send the junior nothing yourself. The helper decides what it sees.
