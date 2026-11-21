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

**Measured results** ([report](../../docs/junior-dev/report-2026-11-21.md), #52, 16 fresh
cases):
- **Against SelfReview** ("reread it and make it clear for a newcomer"), which costs about a
  fifteenth as much: Junior-dev is not clearer.
- **On thin drafts written by Haiku,** the questions add what the draft left out: +9.9
  comprehension points over the same rewrite without questions.
- **Against Opus alone:** plans from Haiku or Sonnet with Junior-dev are judged clearer than
  Opus's first draft, but with the default Sonnet junior the loop costs more than Opus.
- **On GitHub Copilot:** it triggered on 16 of 16 plan prompts and 0 of 12 routine ones, and
  every loop ran to a teach-back.

## Install

### GitHub Copilot (the intended platform)

With the [Copilot CLI](https://docs.github.com/copilot/how-tos/set-up/install-copilot-cli)
(`npm install -g @github/copilot`):

```
copilot plugin marketplace add AndrewGodlewsky/code-comments
copilot plugin install junior-dev@code-comments
```

This installs it at user level, so it is on in every project. VS Code (1.120 or newer) picks up
plugins the Copilot CLI installed; you can also add it under Agent Customizations > Plugins >
User. Run `copilot plugin update --all` after a new release.

The helper script lives in the plugin's folder, outside your project, so the first time it
runs Copilot asks you to allow it. Allow it once for the plugin's folder.

You need Python 3.10 or newer, the Copilot CLI signed in (or a `gh` login, which the helper
borrows), and a Copilot plan that includes Claude Sonnet 5.5 or Haiku 5.5. Each junior turn
is a short Copilot CLI call and uses Copilot AI credits.

Hooks in VS Code are still in preview. The cloud coding agent cannot install user-level
plugins, and JetBrains is untested.

### Claude Code

```
/plugin marketplace add AndrewGodlewsky/code-comments
/plugin install junior-dev@code-comments
```

You need Python 3.10 or newer, and the `claude` command on your PATH, logged in.

### Which model runs the junior

The helper uses the `claude` command if it is installed, and the Copilot CLI otherwise. Set
`JUNIOR_DEV_BACKEND=copilot` or `claude` to choose. The junior runs on Sonnet 5.5 by default.

## What the junior can see

The helper script `scripts/junior.py` runs every junior turn as an isolated session, from an
empty temporary folder, with the prompt sent on stdin:

```text
claude -p --safe-mode --tools "" --system-prompt-file <junior prompt> --json-schema ...
copilot -s --no-custom-instructions --disable-builtin-mcps --no-ask-user --available-tools=__none__ --model claude-sonnet-5.5
```

The junior gets two things:

- the file's current text;
- the questions and answers from this loop.

It does not get:

- your conversation;
- your code;
- your `CLAUDE.md`;
- tools, plugins or MCP servers.

The one thing still in its context is the host's own system prompt and environment block:
Claude Code's (a temporary folder path, the platform, the date and its budget), or the Copilot
CLI's. See the [spike](../../docs/junior-dev/spike-2026-11-12.md) and the
[Copilot assessment](../../docs/junior-dev/copilot-compat-2026-11-19.md).

The loop's state is kept in a `.junior-dev/` folder in the project, which ignores itself in
git.

## Limits

- Text artifacts only: plan and spec documents, and Mermaid or ASCII diagrams. Images and
  Figma files are not supported.
- The loop runs only at the top level of a session. A subagent that writes a plan cannot run
  it.
- The junior's answers come from the author, and the junior cannot check them. The author
  is told to mark anything it cannot defend as `unknown` rather than invent a reason.
