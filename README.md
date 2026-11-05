# code-comments

Code Comments is a planned portable agent skill for preserving useful knowledge
beside the code it explains. Target tools are Orca, Codex, Claude Code, and GitHub
Copilot.

The project is in the research phase. Read [intent.md](intent.md) for the user's
goals and hypotheses, and [architecture.md](architecture.md) for the current
structure, proposed boundaries, and open decisions.

Start with the [research index](docs/research/README.md) for historical sources,
empirical studies, the proposed evaluation protocol, and portability findings.

## Agent workflow setup

[AGENTS.md](AGENTS.md) points agents to the repository configuration:

- [Issue tracker](docs/agents/issue-tracker.md): GitHub Issues in
  [AndrewGodlewsky/code-comments](https://github.com/AndrewGodlewsky/code-comments/issues).
- [Triage labels](docs/agents/triage-labels.md): Matt's five default triage roles.
- [Domain documentation](docs/agents/domain.md): a root glossary and `docs/adr/`,
  created as terms and decisions are resolved.

These files configure the installed skills; they do not install the skill package
on another machine. Edit `docs/agents/*.md` directly to adjust the conventions.

`CLAUDE.md` imports the common instructions, and
`.github/copilot-instructions.md` points Copilot to them. Agents capture durable
lessons and update the relevant context through the
[learning workflow](docs/agents/learning.md). Client loading and compliance still
need to be verified in each supported tool.

The [Git workflow](docs/agents/git-workflow.md) directs agents to commit and push
stable checkpoints automatically, coordinate ownership, and retire completed
branches and temporary worktrees once their work is safely preserved and integrated.

Use `research` to gather evidence first. When ready to settle the design, use
`ask-matt` to choose a workflow or `grill-with-docs` to work through the decisions.

## Development setup

Shared editor settings live in `.editorconfig`. Text files use LF, with CRLF for
Windows batch scripts. Local `.env` files are ignored; example environment files
can be committed.

There is currently no implemented skill or evaluation runner. The research phase
precedes packaging, workflow selection, and model experiments. Add verified
validation and evaluation commands here when those tools exist.
