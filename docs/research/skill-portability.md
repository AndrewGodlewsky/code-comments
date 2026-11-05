# Code Comments: skill distribution and portability

Researched 2026-11-04. This is compatibility research, not an implemented or tested skill. Official documentation was checked against the installed Orca and GitHub CLI where relevant. No dependencies, skills, or app changes were installed. Packaging suggestions below are provisional: they do not settle whether inline comments improve lower-capability models or remain useful through long sequences of edits, nor whether they should replace some shared documentation. Those effectiveness questions must be investigated before committing to a workflow.

**Provisional packaging direction, if experiments justify a skill:** maintain one portable `skills/code-comments/SKILL.md`, distribute its complete directory, and document destination paths for each agent. Treat Orca as a host for a selected coding agent. Consider small repository instruction adapters when users want the workflow considered on every coding task; do not advertise automatic skill selection as guaranteed execution.

## Portable package

The Agent Skills specification requires a directory containing `SKILL.md`, with YAML frontmatter and a Markdown body. Use machine name `code-comments` and human title **Code Comments**. The name must match its directory, use lowercase letters/numbers/hyphens, stay within 64 characters, and avoid leading, trailing, or consecutive hyphens. A nonempty description, at most 1,024 characters, must state purpose and activation conditions. Supporting files are optional; references should use relative paths. Keep the core under 500 lines. These are format constraints, not a guarantee that every host implements every extension. [Agent Skills specification](https://agentskills.io/specification)

Recommended source layout:

```text
skills/
  code-comments/
    SKILL.md
    references/          # Only if the workflow needs supporting detail
README.md                # Installation, invocation, supported surfaces
LICENSE                  # Choose explicitly before public distribution
docs/research/           # Evidence and design notes, outside the installed skill
```

Use only `name` and `description` initially, plus a Markdown heading. The actual description should follow the agreed behavior specification. Avoid host-specific commands, absolute machine paths, permission grants, shell assumptions, hooks, and subagent configuration in the portable core. A workflow that only reads and edits source comments can initially be instruction-only. This is a design recommendation, not a restriction in the standard.

A versioned download should contain `code-comments/SKILL.md` and every supporting file that it references. A repository clone is also sufficient as a source, but cloning this repository alone does not install its skills in other projects. Prefer copies for the documented Windows baseline; symlink-based installation adds environment requirements and deserves separate verification.

## Discovery and invocation by agent

| Target | Recommended project destination | Recommended personal destination | Explicit invocation |
| --- | --- | --- | --- |
| Codex | `.agents/skills/code-comments/SKILL.md` | `~/.agents/skills/code-comments/SKILL.md` | `$code-comments`; inspect `/skills` |
| Claude Code | `.claude/skills/code-comments/SKILL.md` | `~/.claude/skills/code-comments/SKILL.md` | `/code-comments` at the beginning of a prompt |
| GitHub Copilot | `.agents/skills/code-comments/SKILL.md`, or `.github/skills/code-comments/SKILL.md` for a GitHub-oriented layout | `~/.agents/skills/code-comments/SKILL.md` or `~/.copilot/skills/code-comments/SKILL.md` | VS Code supports `/code-comments`; other surfaces require their own verification |
| Orca with Codex | Codex destination above | Codex destination above | Codex skill selection through Orca |
| Orca with Claude Code | Claude destination above | Claude destination above | Claude skill selection through Orca |

**Codex:** local discovery walks `.agents/skills` from the working directory toward the repository root; personal skills use `~/.agents/skills`. It initially exposes metadata and loads the full instructions when selected. Description matching enables implicit selection. Changes are detected automatically; restart if discovery does not refresh. `$skill-installer` can download a skill from another repository. OpenAI currently recommends plugins for reusable public distribution, but standalone local skills remain supported; a plugin wrapper is an optional delivery channel, not a prerequisite for this portable package. [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills)

**Claude Code:** the table describes local sessions. Personal/project filesystem skills do not automatically become skills in every Claude cloud or Cowork session; those surfaces have account-based routes. Plugins are another distribution option and introduce namespaced invocation such as `/plugin-name:code-comments`. By default, both users and Claude can invoke a skill. `disable-model-invocation: true` prevents automatic activation; `user-invocable: false` prevents direct user invocation. Neither is appropriate for the proposed general-purpose baseline. Claude-specific dynamic shell injection and fork configuration should not enter the portable core. [Claude Code: Skills](https://code.claude.com/docs/en/skills)

**Copilot:** official documentation currently lists cloud agent, code review, CLI, app, and VS Code agent mode. It accepts `.github/skills`, `.claude/skills`, and `.agents/skills` in repositories; personal options are in the table. This does not establish support in every Copilot editor feature or inline completion. Skills are selected using the request and description. GitHub recommends ordinary custom instructions for guidance applicable to nearly every task. Code review has additional discovery guidance, so validate that surface separately. [GitHub: Adding agent skills](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills)

VS Code specifically documents slash invocation, a fresh-session discovery check, and a separate automatic-selection test. Its documentation explicitly distinguishes installation/discovery from guaranteed selection. Do not extrapolate the VS Code slash parser to every Copilot client. [VS Code: Use Agent Skills](https://code.visualstudio.com/docs/agent-customization/agent-skills#verify-a-skill)

### Available installer routes

The installed `gh` is version `2.90.0`. Its read-only `gh skill install --help` confirms remote repository and local directory installation, `--agent`, `--scope`, `--dir`, and `--pin`. It discovers `skills/*/SKILL.md`, which is why the proposed source layout is useful. It also injects provenance into frontmatter, so installed files need not be byte-identical to source. [Installed GitHub CLI](<C:/Program Files/GitHub CLI/gh.exe>); [official installation documentation](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills#managing-skills-with-github-cli)

Example commands **after the skill has been implemented and published**:

```powershell
gh skill install AndrewGodlewsky/code-comments code-comments --agent codex --scope project
gh skill install AndrewGodlewsky/code-comments code-comments --agent claude-code --scope project
gh skill install AndrewGodlewsky/code-comments code-comments --agent github-copilot --scope project
```

Codex and Copilot resolve to the same project destination in this CLI, so do not install duplicate copies there. Pick the applicable command; add `--pin <published-tag-or-SHA>` for reproducibility. Do not run these against the current repository yet: the researched package does not exist.

There is a real documentation/version distinction for **personal Codex installation**: current OpenAI documentation recommends `~/.agents/skills`, while the installed `gh` help and bundled Codex installer use `~/.codex/skills`. Document the shared path as the portable manual destination and verify whichever path an installer actually uses. The bundled installer accepts an explicit destination. This research did not test loading a newly installed skill from either path. [Local Codex installer instructions](C:/Users/godle/.codex/skills/.system/skill-installer/SKILL.md)

## Orca evidence and boundaries

The installed Orca compiled package reports version `1.4.249`, commit `fff61ecbacae6ff390d57bb9e54cd4d0e4fd3087`. These findings are local build evidence, not a promise covering every Orca release. [Installed package metadata](C:/Users/godle/AppData/Local/Programs/orca/resources/app.asar.unpacked/out/package.json)

Orca has real skill discovery and chat-picker support. Its native chat profiles assign Codex a `$` prefix and `codex` source owner, and Claude a `/` prefix and `claude` source owner. Visibility checks match shared or agent-owned roots, and can use skills reported by the running session. Consequently, Orca displaying a skill and the underlying agent actually loading it are separate observations. [Agent profiles](C:/Users/godle/AppData/Local/Programs/orca/resources/app.asar.unpacked/out/shared/native-chat/native-chat-agent-profiles.js), [skill visibility](C:/Users/godle/AppData/Local/Programs/orca/resources/app.asar.unpacked/out/shared/native-chat/input/native-chat-skill-visibility.js)

The version-matched CLI guide supports launching selected agents in chat or terminal surfaces. `orca skills install --help` describes installation of **bundled Orca skills**, copying into `.agents/skills` and linking agent-specific roots. It is not evidence that `orca skills install code-comments` can download an arbitrary external package. The command handler confirms it uses the bundled registry. [Orca CLI discovery skill](C:/Users/godle/.agents/skills/orca-cli/SKILL.md), [installed CLI handlers](C:/Users/godle/AppData/Local/Programs/orca/resources/app.asar.unpacked/out/cli/handlers/skills.js)

Minimal supported claim: **install Code Comments for the selected Codex or Claude Code runtime, then invoke it in that runtime through Orca**. Keep Windows/WSL/remote-host destinations aligned with where that runtime runs. No custom Orca installer or native independent skill-execution contract was established here. Orca's provider list includes Copilot for installation placement; that alone does not establish a native Copilot chat invocation path. [Provider placement table](C:/Users/godle/AppData/Local/Programs/orca/resources/app.asar.unpacked/out/shared/skill-install-providers.js)

## Reusable skill versus persistent instruction adapter

The skill should own the reusable workflow. Optional repository adapters should establish when the repository wants it applied and where it is installed. Keep existing instruction files and add a short, clearly scoped paragraph; never replace an unrelated `AGENTS.md` or `CLAUDE.md` during installation.

| Adapter | Verified discovery rule and implication |
| --- | --- |
| `AGENTS.md` for Codex | Read before work, with global guidance and a project-root-to-working-directory chain. `AGENTS.override.md` takes precedence at a directory; the default combined budget is 32 KiB. A short adapter is more dependable than assuming a skill description will always match. [OpenAI: AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md#how-codex-discovers-guidance) |
| `CLAUDE.md` for Claude Code | Modern Claude Code also supports `AGENTS.md` starting in v2.1.277, but by default only when no applicable `CLAUDE.md`, `.claude/CLAUDE.md`, or `CLAUDE.local.md` takes its place. The documented compatibility route is `@AGENTS.md` in `CLAUDE.md`. A prose link asking Claude to read another file is conditional, while an import loads it. Settings and older versions can change this behavior. [Claude Code: Memory](https://code.claude.com/docs/en/memory#agentsmd) |
| `.github/copilot-instructions.md` | Repository instructions automatically provide context on supported surfaces, but available formats vary by client. GitHub explicitly warns that the model may not follow instructions identically every time. [GitHub: Custom instructions](https://docs.github.com/en/copilot/concepts/prompting-and-context/custom-instructions) |

“Always available,” “loaded every session,” and “enforced after every change” are different claims. A persistent adapter can request a final comment review, but remains model guidance. A hook can deterministically run a configured command at a supported lifecycle event; its actual checks, event coverage, configuration, and failure handling determine enforcement. Claude documents shell hooks for this purpose, separately from skills. A prose reminder printed by a hook still requires model compliance. [Claude Code: Hooks](https://code.claude.com/docs/en/hooks-guide)

**Provisional implementation boundary:** if research supports proceeding, an instruction-only skill and optional adapters are the smallest package to evaluate. Only consider host-specific hooks or CI checks after defining an objective property worth enforcing. Detecting a required marker or running a formatter is mechanically testable; deciding whether a comment accurately explains intent still requires judgment. Do not claim a single portable `SKILL.md` guarantees comments on every coding action.

## Validation matrix before claiming support

All rows below are proposed checks, **not passed integration tests**. Research verified documentation and local read-only help/source only.

| Surface | Discovery check | Invocation/behavior check |
| --- | --- | --- |
| Codex CLI or IDE | Fresh session in a temporary repo; `/skills` lists the intended source path once | Explicit `$code-comments`, then a separate relevant request without its name; observe actual file loading and result |
| Claude Code local | Skill appears in `/` menu from the intended `.claude/skills` location | Explicit `/code-comments`; separate implicit request; check user/project same-name collisions |
| Copilot in VS Code | Correct agent harness and workspace; skill appears in menu | Explicit slash run, then independent implicit test; inspect tool activity |
| Copilot CLI/app/cloud agent | Verify discovery in each named surface; cloud receives committed repository files | Use that surface's supported invocation; inspect skill loading instead of assuming VS Code behavior |
| Copilot code review | Commit the selected repository skill destination to a test repository | Review a deliberately relevant change; confirm use before advertising review support |
| Orca with Codex/Claude | Correct runtime, host, and source directory; picker/session exposes skill | Invoke through each selected agent; inspect loading and output in both advertised chat/terminal routes |
| Persistent adapters | Verify effective instructions in a new session, including nested-directory and override cases | Run a task without naming the skill; confirm the requested final review occurred |
| Installation lifecycle | Clean download, full supporting files, existing destination, version pin, user/project scope | No overwritten local instructions; no duplicate discovery; update/removal affects only the installed package |

Use fixtures that exercise the final Code Comments specification: relevant editing, unrelated work, existing useful comments, conflicting local instructions, and unavailable supporting resources. Record exact host versions and distinguish a successful explicit invocation from empirical automatic-selection reliability. Re-run only affected checks when packaging, descriptions, or host integrations change.
