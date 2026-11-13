# junior-dev

A Claude Code plugin for making an agent's plans and diagrams clearer. When the agent writes
a plan, spec or diagram file, a junior developer who sees only that file asks the agent
rounds of questions. The junior is smart and technical, but new to the project and the
stack. The agent answers, flags any decision it cannot defend, and makes the file simpler
and clearer. The loop ends when a fresh junior, reading only the file, can explain it back
correctly, or when the round cap is reached. The user then gets a short report of what
changed and which questions are still open.

It is not a correctness checker and not a critic. The junior cannot check facts. It asks
how things work and why, the way a new team member would. The bet is that having to explain
every step to someone without the context exposes the parts of a plan that are unclear,
incomplete or more complicated than they need to be.

**Status: under evaluation.** This plugin is being measured, mostly with Haiku 5.5 and
Sonnet 5.5 as the authors, in
[#52](https://github.com/AndrewGodlewsky/code-comments/issues/52). Until those results are in,
it makes no claim that it improves anything. The design is in
[docs/junior-dev/design.md](../../docs/junior-dev/design.md).

## Install

In Claude Code:

```
/plugin marketplace add AndrewGodlewsky/code-comments
/plugin install junior-dev@code-comments
```

You need Python 3.10 or newer, and the `claude` command on your PATH, logged in. Each junior
turn is its own short `claude -p` session, billed to your account or subscription like any
other Claude Code use.

## What the junior can see

The helper script `scripts/junior.py` runs every junior turn as an isolated session:

```text
claude -p --safe-mode --tools "" --system-prompt-file <junior prompt> --json-schema ...
```

It runs from an empty temporary folder, with the prompt sent on stdin.

The junior gets two things:

- the file's current text;
- the questions and answers from this loop.

It does not get:

- your conversation;
- your code;
- your `CLAUDE.md`;
- tools, plugins or MCP servers.

The one thing still in its context is Claude Code's generic environment block: a temporary
folder path, the platform, the date and its budget. See the
[spike](../../docs/junior-dev/spike-2026-11-12.md).

The loop's state is kept in a `.junior-dev/` folder in the project, which ignores itself in
git.

## Limits

- Text artifacts only: plan and spec documents, and Mermaid or ASCII diagrams. Images and
  Figma files are not supported.
- The loop runs only at the top level of a session. A subagent that writes a plan cannot run
  it.
- The junior's answers come from the author, and the junior cannot check them. The author
  is told to mark anything it cannot defend as `unknown` rather than invent a reason.
