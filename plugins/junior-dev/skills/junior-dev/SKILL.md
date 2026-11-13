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

3. **Revise the file first.** Go through each question and ask yourself:
   - Is the answer already in the file? If not, the file is missing it. Put it in.
   - Could this part be simpler: fewer steps, fewer parts, plainer names?
   - Does the file say what starts each step, what information moves, where the state
     lives and what happens when a step fails?
   - Would another structure show it better? For example a sequence diagram instead of a
     flowchart, a table, numbered steps, or splitting one diagram in two.

   Everything the junior had to ask about must end up in the file itself, because the final
   check reads only the file. Do not pad: a longer file is not a clearer one. If a question
   shows that part of the plan is actually wrong, fix it.
4. **Write your answers** to `<state>/answers.md`, with one line per question in exactly
   this form:
   - `Q<n> [checked]: <answer>` when you verified it in the code, the docs or the files.
   - `Q<n> [decided]: <answer and the reason>` when it is a design decision you made and can
     defend.
   - `Q<n> [unknown]: <what is not known>` when you do not know, or have no reason you can
     defend. Say so plainly. **Never invent a reason.** Mark the point in the file as an
     open question instead of guessing.

   After the answers, add one line per change you made: `Changed: <what changed and why>`.
5. **Submit**, then go back to step 2.

   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/junior.py" answer "<state>" "<state>/answers.md"
   ```

6. **Teach-back.** When `ask` prints `NO MORE QUESTIONS`, a fresh junior that sees only the
   file explains it back:

   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/junior.py" teachback "<state>"
   ```

   Compare that explanation with what you intended.
   - If any step is wrong, missing, or listed as something it could not explain, the file is
     still unclear at that point. Fix the file there, write the misreadings to
     `<state>/notes.md`, run this, then go back to step 2:

     ```
     python "${CLAUDE_PLUGIN_ROOT}/scripts/junior.py" verdict "<state>" wrong --notes "<state>/notes.md"
     ```

   - If it is right, run this:

     ```
     python "${CLAUDE_PLUGIN_ROOT}/scripts/junior.py" verdict "<state>" correct
     ```

7. **Report.** When the loop has finished, or `ask` prints `ROUND CAP REACHED`:

   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/junior.py" report "<state>"
   ```

8. **Tell the user.** Give them the report: what changed and why, and the holes, meaning the
   questions you could not answer or are unsure about. Keep it short.

## Rules

- Never stop the loop to ask the user anything. Unknowns go into the report.
- Do not argue with the junior, and do not leave an explanation only in your answers. Fix the
  file.
- Keep the plan's intent. Clarifying must not quietly change what the plan does. When a
  question reveals a real problem and you change the plan, record it as `Changed:`.
- Send the junior nothing yourself. The helper decides what it sees.
