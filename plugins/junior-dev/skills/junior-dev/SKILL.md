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

3. **Revise the file first, and make it simpler, not longer.** Each question shows you
   where a newcomer got stuck. For each one, ask yourself:
   - Was the answer already there? Then that part is hard to find or hard to read. Make it
     plainer or move it where a reader would look. Do not say it twice.
   - Does a reader need the answer to follow the main flow? Then put it in, at the step it
     belongs to, and cut something less important if you can.
   - Is it a detail the plan does not need yet, such as an exact format, a library choice
     or a rare edge case? Then answer it in your answers file only, and leave it out of the
     file.
   - Is it a "what happens if this fails" question? Give the simplest handling the brief
     allows. Do not add a new mechanism, such as a lock, lease, retry queue or takeover rule,
     unless the brief requires it.
   - Could this part be simpler: fewer steps, fewer parts, plainer names? Would another
     structure show it better, such as numbered steps, a table, a sequence diagram instead of
     a flowchart, or one diagram split in two?

   Keep the file short. Aim to keep it within about one and a half times its first length.
   A longer file is not a clearer one. What a reader needs to follow the main flow has to be
   in the file itself, because the final check reads only the file. If a question shows that
   part of the plan is actually wrong, fix it.
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
5. **Submit**, then go back to step 2.

   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/junior.py" answer "<state>" "<state>/answers.md"
   ```

6. **Teach-back.** When `ask` prints `NO MORE QUESTIONS`, a fresh junior that sees only the
   file explains it back:

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

7. **Simplify once more.** When the loop has finished, or `ask` prints `ROUND CAP REACHED`,
   read the whole file once, as a newcomer would, and make it simpler. Keep its intent and
   everything the main flow needs.
   - Cut what a reader does not need to follow the main flow.
   - Merge rules or notes that say the same thing.
   - Replace several mechanisms with one simple one wherever the brief allows.
   - Lay it out for a newcomer, in this order:
     1. Two or three sentences on what this is and how the main flow goes.
     2. The few terms a newcomer needs, each defined in one line.
     3. The steps, numbered, in the order they happen.
     4. What happens when things fail, at each step or in one table.
     5. The open questions, at the end.
   - Write each step so it stands alone. Avoid codes such as R3 or Q7 that send the reader
     elsewhere to look things up.

   A diagram keeps its diagram form. Put the summary and the terms just before it, and the
   notes just after it.

   When you tell the user (step 9), mention what you cut or merged.
8. **Report.**

   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/junior.py" report "<state>"
   ```

9. **Tell the user.** Give them the report: what changed and why, and the holes, meaning the
   questions you could not answer or are unsure about. Keep it short.

## Rules

- Never stop the loop to ask the user anything. Unknowns go into the report.
- Do not argue with the junior, and do not leave an explanation only in your answers. Fix the
  file.
- Keep the plan's intent. Clarifying must not quietly change what the plan does. When a
  question reveals a real problem and you change the plan, record it as `Changed:`.
- Send the junior nothing yourself. The helper decides what it sees.
