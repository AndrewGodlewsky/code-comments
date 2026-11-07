---
name: project-docs
description: Keep the project's documentation folder accurate and useful while you change code. Use whenever you edit, fix or refactor source code, so the next agent or developer can understand what each part does, why, and what it affects without reconstructing it.
---

# Project documentation

This project keeps an AI-maintained documentation folder alongside the code. The
next agent to work here starts a fresh session. It has the code, but not this
conversation or the ticket you read. The documentation is how what you learned
reaches it, so treat updating it as part of every change, not an afterthought.

## Layout

- `AGENTS.md` at the repository root: a short index, under 200 lines. It lists every
  document in `docs/`, says what each covers, and maps documents to the source files
  they describe. Read it first; update it when you add, rename or retire a document.
- `docs/ARCHITECTURE.md`: how the modules fit together, data flow, and cross-module
  relationships ("changing X affects Y").
- `docs/<area>.md`: one document per module or subsystem. Each covers what it does,
  the contracts callers rely on, the constraints and invariants it must keep, the
  non-obvious reasons it is built this way, and what else depends on it.

Create any of these that do not exist yet.

## On every change

1. **Before editing,** read `AGENTS.md` and the documents for the code you will touch.
   Treat their claims as claims to check against the code.
2. **While editing,** note what the task evidence (ticket, review, incident note)
   tells you that the code alone cannot show: the reasons, constraints, external
   behaviour, and rejected alternatives worth knowing.
3. **Before finishing,** update every document your change affects in the same
   change. That includes the area document, the architecture document if a
   relationship changed, and the `AGENTS.md` index. Correct or delete anything your
   change made false. Record the new knowledge from step 2 in the right document.
4. **Write only what the evidence supports.** Never invent a reason, a history or an
   issue number. If something matters but you cannot verify why, say so in your final
   message instead of guessing in the docs.

Keep code comments as you normally would. The documentation folder is where
explanation lives in this project.
