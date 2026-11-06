# code-comments

Code Comments is a planned portable agent skill for preserving useful knowledge
beside the code it explains. Target tools are Orca, Codex, Claude Code, and GitHub
Copilot.

The project has completed an initial research review and begun an offline
evaluation foundation. Read [intent.md](intent.md) for the user's
goals and hypotheses, and [architecture.md](architecture.md) for the current
structure, proposed boundaries, and open decisions.

Start with the [research index](docs/research/README.md) for historical sources,
empirical studies, the proposed evaluation protocol, and portability findings.
For a review of the problem, existing systems, and benchmark options, read the
[deep-dive synthesis](docs/research/deep-dive-summary.md).

The [product roadmap](docs/roadmap.md) links the remaining GitHub issues and
dependencies. The first [offline fixture audit](docs/evaluation/README.md) is
executable; model trials and the portable skill are still future work.

## Reading list

Local copies of books and papers used for comments research live under `docs/books` and `docs/papers`. [docs/reading-list-access.md](docs/reading-list-access.md) lists every title on the reading list and how to get the ones that are not in this repo.

### In this repo

**Books** (`docs/books`):

- *The Pragmatic Programmer* by David Thomas and Andrew Hunt (machine transcript; edition and transcription accuracy unverified)
- *Software Engineering at Google* by Titus Winters, Tom Manshreck, and Hyrum Wright (full HTML edition; open `docs/books/software-engineering-at-google/toc.html`)
- *A Philosophy of Software Design* by John Ousterhout (author-posted extract only, not the full book)

**Papers and essays** (`docs/papers`):

- Herman Goldstine and John von Neumann, *Planning and Coding of Problems for an Electronic Computing Instrument* (1947-48)
- IBM, *FORTRAN Programmer's Reference Manual* for the IBM 704 (1956)
- David Parnas and Paul Clements, *A Rational Design Process: How and Why to Fake It* (1986)
- Donald Knuth, *Literate Programming* (1984)
- Martin Fowler, *Code As Documentation* (2005) and *Beck Design Rules* (2015)

### Not downloaded here

These titles are still on the reading list. The access guide has the borrow, sample, or purchase links.

- Free to read online, but not saved here: Jef Raskin, *Comments Are More Important than Code* (2005); Ted Tenny (1985 and 1988); Woodfield, Dunsmore, and Shen (1981)
- Borrow with a free Internet Archive or Open Library account: Weinberg, *The Psychology of Computer Programming*; Kernighan and Plauger, *The Elements of Programming Style*; Ledgard, *Programming Proverbs* / *Pascal with Style*; Kernighan and Pike, *The Practice of Programming*; Brooks, *The Mythical Man-Month*
- Official samples or excerpts only: Fowler, *Refactoring*; Martin, *Clean Code*; Evans, *Domain-Driven Design*; Reilly, *The Staff Engineer's Path*; McConnell, *Code Complete*; Skelton and Pais, *Team Topologies*
- Purchase or library only: Feathers, *Working Effectively with Legacy Code*; Fournier, *The Manager's Path*; Patterson et al., *Crucial Conversations*

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
stable checkpoints automatically and coordinate ownership. A task is complete only
after independent review, verified remote `main` integration, issue reconciliation,
cleanup, and a separate agent's final audit. [Task tracking](docs/agents/task-tracking.md)
keeps branch assignments and closeout evidence in GitHub across sessions. Primary
checkouts and other agents' active work are preserved.

Use `research` to gather evidence first. When ready to settle the design, use
`ask-matt` to choose a workflow or `grill-with-docs` to work through the decisions.

## Development setup

Shared editor settings live in `.editorconfig`. Text files use LF, with CRLF for
Windows batch scripts. Local `.env` files are ignored; example environment files
can be committed.

Python 3.12+ is sufficient for the offline tools; no packages need installing:

```text
python -m unittest discover -s tests -v
python -m evaluation.offline audit
```

See the [offline tool guide](docs/evaluation/README.md) for equivalent-context
exports and their limits. There is no isolated model runner or implemented skill.
The user currently authorizes offline work only; no model experiments have run.
