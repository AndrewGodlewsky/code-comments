# junior-dev on GitHub Copilot: compatibility assessment

Date: 2026-11-19. This report uses only the verified research supplied with the task. Where a verdict corrected a claim, the correction is applied. Claims marked wrong or unverifiable are dropped or listed as gaps. Nothing was run on a Copilot surface. Citations in brackets point to section 6. Statements marked "suggestion" or "inference" are mine, not documented facts.

**Summary.**
- **Copilot CLI is the best target.** It reads the plugin's existing files where they are: `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json`, `skills/` and `hooks/hooks.json` [S7]. Its hook contract also matches what the plugin needs: `PostToolUse` can return `additionalContext`, and `Stop` can return `decision: "block"` with `stop_hook_active` in its input [S12].
- **VS Code works the same way, but its hooks are in preview.** VS Code's default Copilot harness uses the same hook runtime and format as the CLI [V9], and it picks up plugins that the CLI installed [V8]. Agent hooks in VS Code are still in preview [V9].
- **The coding agent cannot take a user-level plugin**, and JetBrains is mostly unknown.
- **Four things have to change:**
  - the output shape of `hooks.py`;
  - how `hooks.py` reads the path of the file that was written;
  - how the agent finds `junior.py`, because no Copilot surface documents `${CLAUDE_PLUGIN_ROOT}` in skill text;
  - a Copilot backend for `junior.py`, because the `claude -p` isolation flags have no exact Copilot equivalent.

## 1. Compatibility table

| What the plugin needs | VS Code agent mode (Copilot harness) | Copilot CLI | Copilot coding agent (cloud) | JetBrains |
|---|---|---|---|---|
| Install once at user level | **yes**. A plugin can be installed at User scope from the Agent Customizations editor. VS Code 1.120+ also picks up plugins installed with `copilot plugin install`, and it detects the Claude format from `.claude-plugin/plugin.json` [V6][V7][V8] | **yes**. `copilot plugin marketplace add AndrewGodlewsky/code-comments`, then `copilot plugin install junior-dev@code-comments`. The plugin installs to `~/.copilot/installed-plugins/`, and there is no project-scope flag [S7][S9][S10] | **no**. There are no user-level plugins or hooks. Personal skills reach cloud-sandbox sessions only through `.copilot/skills` in a dotfiles repo, and not in Actions-based sessions. Hooks come only from the repo's `.github/hooks/*.json` [S1][S12] | **unknown**. User-level skills exist (plugin 1.20.0 fixed them on Windows). How plugins install was not researched [J1] |
| The skill loads and the agent follows it | **yes**. GA since 1.109. It loads automatically from its description or by `/junior-dev:junior-dev` [V1][V2] | **yes**. Automatically by description, or with `/SKILL-NAME` [S5] | **yes**. Copilot picks a skill from the prompt and the skill's description. Skills come from repo folders [S3][S1] | **yes**. GA in plugin 1.10.0 (2026-05-29), although GitHub's matrix and cheat sheet still say preview. Limited in Split Mode / Remote Development (1.21.0). Folders and fields are undocumented [B5][J1][S6][S2] |
| The bundled helper script runs | **partly**. Bundled scripts "can run tools", but the docs don't name the tool. Nothing documents that `${CLAUDE_PLUGIN_ROOT}` resolves in skill text [V2] | **partly**. Scripts run through the shell or bash tool. Copilot asks permission unless `allowed-tools` pre-approves the tool. The plugin-root variables are documented only for hook processes [S4][C1] | **partly**. Cloud sandboxes have Bash and support skill scripts (GA on paid plans). No source says Python is installed [B10] | **unknown** |
| Auto-trigger after the agent writes a plan or diagram | **partly (preview)**. VS Code finds `hooks/hooks.json` for Claude-format plugins. `PostToolUse` with a top-level `additionalContext` is the shared format, and hooks are in preview [V6][V9][V3] | **partly**. Plugin `hooks/hooks.json` loads, and `PostToolUse` can return `additionalContext` (GA since 2026-02-25). Two problems: the key that holds the written file's path inside `tool_input` is undocumented, and on Windows hook commands run through PowerShell [S7][S12][B3][C2] | **partly**. Only a repo-level `.github/hooks/*.json` on the default branch, and only `bash` or `command` entries are honored [S14][S12] | **unknown**. JetBrains says agent hooks are GA, but the format and events were not researched [B5] |
| A reminder or block before the agent finishes | **yes (preview)**. A `Stop`/`agentStop` hook can return `decision: "block"` with a `reason`, and the input includes `stop_hook_active` [S12][V3][V9] | **yes**. Same contract. After 8 consecutive blocks the CLI ends the turn anyway [S12][C1] | **partly**. `agentStop` fires and can block, but each forced turn counts against the job timeout. Repo-level only [S12] | **unknown** |
| An isolated junior model call that sees only the file | **partly**. VS Code has no blind call of its own: subagents get context supplied by the parent and share the workspace, `code chat` returns no output, and the LM API works only inside an extension. The helper can start its own `copilot`, `claude` or SDK process [V13][V16][V15] | **partly**. Prompt mode, run from an empty temp folder with the hardening flags, keeps out the conversation, the repo and instruction files. The CLI's own system prompt remains, and removing every tool relies on an undocumented value [S5][C7][C8] | **unknown**. No documented binary or credential exists for a nested call in the sandbox. The hooks environment does not set `GITHUB_TOKEN` [S12] | **unknown**. The same subprocess route would work if the agent can run commands |
| Claude Haiku and Sonnet models | **yes**. Sonnet 5.5 and Haiku 5.5 are included on Pro, Pro+, Max, Business and Enterprise. Free and Student plans get Auto only [S23] | **yes**. `--model claude-sonnet-5.5` (the default) or `--model claude-haiku-5.5` [S5] | **yes**. Sonnet 5.5 and Haiku 5.5 can be selected [B8][B9] | **yes**. Both are listed for JetBrains [S23] |

The trigger rates in the brief were measured only in Claude Code: without hooks, Sonnet 0/5 and Haiku 6/8; with hooks, 5/5 and 8/8. They have not been measured on any Copilot surface.

## 2. What carries over unchanged

- **The marketplace file.** Both the CLI and VS Code search `.claude-plugin/marketplace.json` [S7][V18]. Its fields fit Copilot's required set: `name`, `owner.name`, relative `source` entries and an optional `metadata.description` [S7]. The install id stays `junior-dev@code-comments`, because it comes from the marketplace's `name` field and not from the repo name [S9].
- **The plugin manifest.** `.claude-plugin/plugin.json` is a legacy-format location for the CLI [S7] and the Claude-format manifest for VS Code [V6]. Only `name` is required, and it must be "Kebab-case plugin name (letters, numbers, and hyphens only)". `junior-dev` meets that rule. Every other field the file uses is a documented optional field [S7].
- **The skill.**
  - `skills/<name>/SKILL.md` is the default skills folder for legacy plugins [S7].
  - The frontmatter (`name` and `description`) is the common core on every surface [S4][V2].
  - The name already meets VS Code's stricter rule: lowercase letters, numbers and hyphens, matching the folder. That rule matters because "Names with invalid characters cause the skill to silently fail to load" [V2].
  - Every surface loads skills automatically from their description [S3][S5][V2][B5].
- **The prompt files.** `references/*.md` stay where they are. `junior.py` reads them by path.
- **The hook file's location and syntax.**
  - The CLI reads `hooks/hooks.json` for legacy plugins, and VS Code reads it for Claude-format plugins [S7][V6].
  - The CLI accepts PascalCase event names, Claude's nested `{matcher, hooks: [...]}` groups and an optional `type` field (1.0.6). It also accepts a file with no `version` (1.0.5) [C1].
  - PascalCase events get snake_case payloads with `hook_event_name`, `session_id`, `cwd`, `tool_name` and `tool_input` [S12]. These are the names `hooks.py` already reads.
- **The Stop logic.**
  - `{"decision": "block", "reason": "..."}` is the documented Copilot shape, and the `reason` becomes the next prompt. "The output field names (decision, reason, modifiedResponse) are the same for both the camelCase and VS Code compatible configs" [S12].
  - `stop_hook_active` arrives in the input, so the plugin's existing loop guard keeps working [S12][C1].
  - Stop fires when a turn ends, not when the session ends, as in Claude Code [V3].
- **How the hooks behave.** `hooks.py` always exits 0, writes one JSON object to stdout, and sends diagnostics to stderr. This matches Copilot's rule that "It can return one final JSON output object on standard output (stdout). Keep ordinary diagnostic text on standard error (stderr)" [V9][S12].
- **The project folder.** CLI plugin hooks receive `CLAUDE_PROJECT_DIR` (1.0.12) [C1], and every payload includes `cwd` as a fallback [S12].
- **Host-independent parts.** `classify.py`, the `.junior-dev/` state folder, the loop text in `SKILL.md`, both prompts and the `JUNIOR_DEV_NESTED` guard need no change.

## 3. What must change, file by file

### `.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json`
No change is required. Do not add a root `plugin.json`, a `.plugin/plugin.json` or a `.github/plugin/plugin.json`, for three reasons:
- The CLI checks those locations before `.claude-plugin/plugin.json` [S7].
- VS Code checks them in a different order, so the two surfaces could end up reading different manifests [V6].
- A root manifest in the Agent Plugins format takes precedence on both surfaces [S7][V6]. Agent Plugins 1.0 also moves hooks to `com.github.copilot/hooks/hooks.json` [S8], and VS Code gives that format no generic plugin-root token for hooks [V6].

Since CLI 1.0.106, `copilot plugin install` reports any manifest field it ignored. Watch for that report on the first install [C1].

### `hooks/hooks.json`
1. **Widen the matcher** to `Write|Edit|MultiEdit|create|edit|str_replace_editor|apply_patch`.
   - Copilot's file-writing tools are `create`, `edit`, `str_replace_editor` and `apply_patch` [S12].
   - The mapping to Claude names (create to Write; the other three to Edit) is documented only for PascalCase `PreToolUse` [S12]. Claude-style `PostToolUse` matchers such as `Edit|Write` are honored only according to the changelog (CLI 1.0.63) [C1].
   - Matchers are regexes "compiled as `^(?:PATTERN)$`" [S12].
   - `apply_patch` can also create files (1.0.106) [C1].
   - Inference: the extra names do no harm in Claude Code.
2. **Add per-shell commands next to `command`.**
   - It is unconfirmed whether the CLI substitutes `${CLAUDE_PLUGIN_ROOT}` inside command strings. The CLI does set `CLAUDE_PLUGIN_ROOT` as an environment variable (1.0.26), but only the changelog says so [C1].
   - On Windows, hook commands run through PowerShell (issue #4001, still open) [C2]. In PowerShell, `${CLAUDE_PLUGIN_ROOT}` is a PowerShell variable, not an environment variable.
   - A command entry may carry `bash`, `powershell`, and `command` as the "cross-platform fallback" [S12].
   - VS Code substitutes `${CLAUDE_PLUGIN_ROOT}` itself for Claude-format plugins [V6].

   ```json
   {"type": "command",
    "command": "python \"${CLAUDE_PLUGIN_ROOT}/scripts/hooks.py\" post-write",
    "bash": "python \"$CLAUDE_PLUGIN_ROOT/scripts/hooks.py\" post-write",
    "powershell": "python \"$env:CLAUDE_PLUGIN_ROOT/scripts/hooks.py\" post-write"}
   ```
   Use the same pattern for `stop`. Untested: whether Claude Code accepts the extra `bash` and `powershell` keys, and whether the CLI honors them inside a nested Claude-style group.
3. **Keep the PascalCase `PostToolUse` and `Stop` names.** They select the snake_case payload that `hooks.py` already reads [S12]. Native camelCase events (`postToolUse`, `agentStop`) would send `toolName` and `toolArgs` instead.

### `scripts/hooks.py`
1. **Change the post-write output on Copilot.** Return a top-level `{"additionalContext": "..."}` instead of `hookSpecificOutput`. Copilot appends it to the tool result on the same turn, with a 10 KB cap across hooks [S12]. VS Code's migration guide says "accepting a PascalCase input alias does not establish support for every Local `hookSpecificOutput` field. Emit the documented Copilot output" [V3]. Keep `hookSpecificOutput` for Claude Code. Copilot can be told apart by its payload: it sends `tool_result` (or `toolResult` in camelCase), while Claude Code sends `tool_response` [S12][V3].
2. **Read the path robustly in `_target`.**
   - Accept `tool_input` (or camelCase `toolArgs`) as an object or as a JSON string. The tutorial says camelCase `toolArgs` "is a JSON string" [S15]. For PascalCase `PostToolUse`, whether `tool_input` is parsed is undocumented; the "parsed from JSON string when possible" note covers only `PreToolUse` [S12].
   - Read `file_path` (Claude) or `path` (Copilot). The evidence for `path` is thin: a docs example that has since been removed read `.toolArgs | .path` for `edit` [S16]; issue #4626 (unofficial) shows `create` requiring `path` and `file_text` [C6]; issue #3254 shows `edit` using `old_str` and `new_str` [C5].
   - Suggestion: `apply_patch` arguments are undocumented. When no path can be read, fall back to scanning for plan or diagram files changed since the last hook run.
3. **Filter on the tool name in code as well as in the matcher.** VS Code warns that across harnesses "tool names and arguments can change" [V9].
4. **Put the absolute path of `junior.py` (built from `HERE`) into both the reminder text and the Stop `reason`.** The agent can then run the helper without `${CLAUDE_PLUGIN_ROOT}`.
5. **Keep using JSON, not exit codes.** On Copilot, exit 2 is only a warning for `agentStop` [S12]. The current code already uses JSON.

### `skills/junior-dev/SKILL.md`
1. **Replace `${CLAUDE_PLUGIN_ROOT}/scripts/junior.py` in every command.** No Copilot surface documents substituting that token in skill text. The plugin-root variables are documented only for hook processes [C1][S12]. Define the helper path once:
   - the path given in the junior-dev hook message;
   - in Claude Code, `${CLAUDE_PLUGIN_ROOT}/scripts/junior.py`;
   - otherwise, `scripts/junior.py` in the plugin folder that contains this skill.
2. **Recommended: move `scripts/` into `skills/junior-dev/scripts/` and link to it** with `[junior.py](scripts/junior.py)`. When a skill is invoked, the CLI and the cloud agent make every file in the skill folder available [S3][S4]. VS Code loads a bundled file only when the instructions reference it: "If a file isn't referenced in the instructions, it won't be loaded" [V2]. After the move, update `REFERENCES` in `junior.py` (to `HERE.parent / "references"`), the paths in `hooks.json` and the README.
3. **Do not add `hooks:` frontmatter.** No surface documents skill-level hooks. VS Code's validator flags unknown attributes as "not supported by VS Code skills" [S12][V2][V4].
4. **Leave `allowed-tools` out by default.** The CLI honors it, but "Pre-approving `shell` or `bash` removes the confirmation step for running terminal commands" [S4]. VS Code flags it as unsupported [V4].

### `scripts/junior.py`
Add `--backend copilot|claude` and keep the current `claude` path as it is. Each `claude -p` flag maps to Copilot CLI as follows:

| Today (`claude -p`) | Copilot CLI equivalent | Status |
|---|---|---|
| Prompt on stdin | Pipe the prompt on stdin and do **not** pass `-p`: "Piped input is ignored if you also provide a prompt with the `-p` or `--prompt` option" [S17] | Documented. Whether `-s` applies to piped input is not stated |
| `--safe-mode` | `--no-custom-instructions --disable-builtin-mcps --disable-mcp-server computer-use --no-ask-user`. Do not pass `--trust-folder`. Set `COPILOT_HOME` to an empty temp folder: it "replaces the entire `~/.copilot` path", which removes user settings, skills, agents, installed plugins and user-level instructions [S5][S11][S18] | Documented. How far `--no-custom-instructions` reaches over user-level files is not stated |
| `--tools ""` | `--available-tools=__none__` gave 0 tools on 1.0.105. An untested alternative is `--available-tools=view --excluded-tools=view`, because since 1.0.106 an excluded tool is removed even when the allowlist names it. An empty `--available-tools=` sent all 21 tools [C7][C1] | Undocumented. #5306 closed 2026-11-14 with no fix named |
| `--system-prompt-file` | No flag for Copilot-hosted models (`systemMessage` exists only for bring-your-own-key models). Put the prompt file's text at the start of the stdin message instead. The CLI's coding-agent system prompt still applies [S5][S11][C8] | Gap |
| `--json-schema`, `--output-format json` | Use `-s` ("Output only the agent response"), ask for JSON in the message, and validate it with the existing parsers. `--output-format json` emits JSONL, and its record schema in prompt mode is undocumented [S5][C1] | Partly |
| `--no-session-persistence` | No equivalent. Session state lands under the temp `COPILOT_HOME` and is deleted with it [C7][S11] | Workaround |
| `--max-budget-usd 0.25` | `--max-ai-credits 30`: $0.30, the minimum allowed, a soft limit, public preview [S21] | Preview |
| `--model sonnet` | `--model claude-sonnet-5.5` or `claude-haiku-5.5` [S5] | GA |
| Empty temp working folder | Same, but it must sit outside any git checkout, because instruction discovery walks up to the repo root [S18] | Documented |

Other changes:
- **Auth.** With `COPILOT_HOME` moved, pass `COPILOT_GITHUB_TOKEN` or `GH_TOKEN`. Fine-grained PATs with the "Copilot Requests" permission work, and so do OAuth tokens from the Copilot CLI app or `gh`; classic `ghp_` tokens do not [S5]. Whether a stored login survives a moved `COPILOT_HOME` is unknown.
- **`_structured`.** With `-s`, stdout is the reply itself, so accept a bare JSON object that carries `questions` or `explanation`. Retry once if it fails to parse.
- **`_cost`.** Copilot output has no `total_cost_usd`, so report the cost as not available.
- **Launcher fallback.** If `copilot` is missing, use `gh copilot`, which forwards flags to the CLI [B12].
- **Self-check before the first turn.** Run `copilot instruction list` (CLI 1.0.85) with the same working folder and environment, and refuse to continue if it lists any source [C1]. Once per install, confirm that the session's events show zero tools, using the method from #5306 [C7].
- **Docstring.** Update it; the CLI backend keeps the plugin "Standard library only".

### `README.md`
Add a Copilot section covering:
- the CLI install commands, or `/plugin install junior-dev@code-comments` inside a session [S10];
- that VS Code needs no further step after a CLI install (1.120+) [V8], or offers Agent Customizations > Plugins > `+` next to User [V7];
- requirements: Python 3.10+, Copilot CLI on PATH, a token, and a plan that includes Sonnet 5.5 or Haiku 5.5 [S23];
- that installed plugins are cached, so users should run `copilot plugin update --all` after a release [S8][S7];
- to install from the marketplace, not straight from the repo or a path, because those installs print a deprecation warning (1.0.108) [C1].

### Optional repo-level files for the coding agent (not user level)
- Add `.github/skills/junior-dev/` and a native-format `.github/hooks/junior-dev.json` on the default branch [S14][S12], for example `{"version": 1, "hooks": {"postToolUse": [{"type": "command", "matcher": "create|edit|str_replace_editor|apply_patch", "bash": "python3 .github/skills/junior-dev/scripts/hooks.py post-write"}], "agentStop": [{"type": "command", "bash": "python3 .github/skills/junior-dev/scripts/hooks.py stop"}]}}`.
- That file sends camelCase payloads (`toolName`, `toolArgs`).
- This is only worth doing once a junior backend has been shown to work in the sandbox.

## 4. How to run the isolated junior on each surface

The junior is a separate process that `junior.py` starts. It never uses the host agent's session. So on any machine where the agent can run a shell command, any backend installed there will work.

| Backend | Isolation | Status | Needs |
|---|---|---|---|
| **Copilot CLI prompt mode** (the flags in section 3) | Keeps out the conversation, repo files and instruction files. Tools are removed only through an undocumented value. The CLI's system prompt and environment context remain [C8][S11] | CLI GA [B3]. The tool-removal trick is undocumented [C7] | `copilot` on PATH, a token, a Copilot plan |
| **Copilot SDK v2, `mode: "empty"`** | The blindest documented route. "`Empty` disables ambient tools and optional CLI behavior by default" [K2]. `tools.availableTools: []` "Exposes no tools" [K2]. `systemMessage` can replace the prompt, or customize mode can `remove` the `environment_context` and `custom_instructions` sections [K1][S26]. `skipCustomInstructions` defaults to true in empty mode [K3] | SDK GA [K4]. v2.0.1 shipped 2026-11-18. `responseSchema` is in preview [K1]. Empty mode needs `runtime.baseDirectory` or `sessionFs` [K3]. The Python API names are unverified, because the research read the Node docs | `pip install microsoft-copilot-sdk` [K4], which ends "standard library only"; a Copilot plan |
| **`claude -p`** (today) | Strongest of the measured setups | Works as it does now | Claude Code login and Anthropic billing |
| Not usable | VS Code subagents get "the task and context supplied through delegation" and share the workspace [V13]. `code chat` only opens a chat [V16]. The LM API is extension-only, needs consent and "doesn't support the use of system messages" [V15]. GitHub Models is retired [S27]. CLI `--agent` still receives repo instructions [S19] | | |

Per surface:
- **Copilot CLI:** the CLI backend.
- **VS Code agent mode:** the same subprocess route. VS Code needs the separate Copilot CLI (or `gh copilot`) or the SDK. Whether VS Code puts a `copilot` binary on PATH is unknown.
- **Coding agent:** no backend is confirmed. The skill should report that no junior is available and stop.
- **JetBrains:** the same as VS Code if its agent can run commands, which is unknown.

**Best default: the Copilot CLI backend with `claude-sonnet-5.5`**, prompt on stdin, the hardening flags above, and optionally `--max-ai-credits 30`.
- **Why:** it needs nothing beyond a Copilot user's own setup, it is GA, and it adds no Python dependency.
- **Keep `--backend claude`** for Claude Code users and for anyone who wants the measured isolation.
- **Re-run the comprehension eval on the Copilot backend before making it the default.** The junior now also sees the CLI's system prompt [C8], so results measured with `claude -p` may not carry over. If that prompt measurably changes the junior's questions, move to the SDK backend.
- **Cost:** Sonnet 5.5 costs $2.00 per million input tokens and $10.00 per million output tokens. Haiku 5.5 costs $0.10 and $0.50 up to 100K input tokens [S24]. One credit is $0.01 [S21]. So 10K input tokens cost 2 credits on Sonnet and 0.1 credit on Haiku. Tool definitions left in add about 10,439 tokens per call [C7].

## 5. Risks and open questions

**Preview or experimental:**
- VS Code agent hooks are in preview [V9]. GitHub also calls the VS Code hooks experience public preview [S13].
- `--max-ai-credits` is in public preview [S21].
- SDK structured output is in preview [K1].
- `chat.plugins.marketplaces` and `chat.pluginLocations` are Experimental [V6].
- VS Code cloud sessions are experimental, and local hook files are not copied to them [V9].
- The Claude session target toggle in VS Code is Experimental [V10].
- GitHub's feature matrix is itself in preview, and its JetBrains entry looks stale [S6].
- JetBrains skills are limited in Split Mode / Remote Development, with no fix in 1.21.1 [J1].
- Agent Plugins 1.1.0, which adds portable root `hooks.json`, is still a working draft [P1].

**Undocumented behavior the port relies on (test these first):**
1. Which key holds the file path in `PostToolUse` `tool_input` for `create`, `edit` and `apply_patch` [S12][S16][C5][C6].
2. Matching Claude tool names in `PostToolUse` (changelog only) [C1].
3. Whether the CLI substitutes `${CLAUDE_PLUGIN_ROOT}` in hook command strings. The plugin-root variables appear only in the changelog [C1][S12].
4. Windows: hook commands run through PowerShell (#4001), and `||` / `&&` break there (#4399). Both issues are open [C2][C3].
5. Whether `copilot` prompt mode really gets zero tools (#5306 closed without a named fix; #4596 still open) [C7][C8]. Also whether piped stdin works together with `-s`, and what the JSONL schema is [S17][C1].
6. Whether moving `COPILOT_HOME` keeps a stored login. Whether Claude Code tolerates the `bash`/`powershell` keys and the top-level `description` key that Copilot sees.
7. Whether VS Code runs a CLI-installed Claude-format plugin's hooks exactly as the CLI does. VS Code says "Sharing a hook file location does not establish runtime compatibility" [V9].
8. Issue #4520 (open): a standalone `.github/hooks` `postToolUse` hook never fires under `copilot -p`. This affects only repo-level hook files [C4].

**Plans and cost:**
- Free and Student plans get "models through auto model selection only", so the junior's model cannot be pinned. How the CLI handles `--model` on those plans is unknown [S23].
- Legacy annual Pro and Pro+ plans "will not receive access to new models". They keep Haiku 4.5 and the retired Sonnet 4.6 [S25][S23]. The model should therefore be configurable.
- Business and Enterprise admins control which models are enabled, and extra usage is on by default [S23][S28].
- An organization can allow only managed hooks with `ChatAllowManagedHooksOnly` [V17].
- Every junior turn spends AI credits [S20][B4].

**Behavior:**
- Triggering is unmeasured on Copilot, where Auto and Fusion may route the host agent to other models [S23]. Re-run the activation eval on both the CLI and VS Code.
- A user who also copies the skill into `~/.copilot/skills` gets that copy, because it outranks the plugin's skill [S5][S7].
- Hooks from every source run, so a repo-level copy plus the plugin would show two reminders [S12][V9].

**Surface gaps:**
- **Coding agent:** there is no user-level route. Unknowns: the junior backend, whether Python is present, whether Actions-based sessions read `.claude/skills`, and whether the plugin keys in repo settings, which "are also read by Copilot in the cloud" [S11], also load plugin hooks. The hooks reference says "The sandbox does not ship with ... installed plugins" [S12].
- **JetBrains:** skill folders, frontmatter fields, slash invocation, the hook format and plugin install are all undocumented.
- **VS Code Local harness:** it "will be removed in February 2027" [V10]. Do not target its `hookSpecificOutput` or exit-2 behavior [V12].
- **VS Code Claude session target:** whether it loads Claude Code plugins unchanged is unknown. The docs say only that it uses "Claude project configuration" [V10].

**Conflicts between docs:**
- The concepts page says `postToolUse` fires "whether successful or failed". The reference (newer) says "After each tool completes successfully" [S13][S12].
- The hooks reference names only the CLI and the cloud agent as hook surfaces, while the concepts page adds VS Code and the app [S12][S13].
- The CLI's own how-to says skill names "must be lowercase, using hyphens for spaces", while the CLI reference allows looser names [S4][S5].

## 6. Sources

GitHub docs. Pages are undated unless a date is given, and all were fetched on 2026-11-19.
- [S1] https://docs.github.com/en/copilot/concepts/agents/about-agent-skills (undated)
- [S2] https://docs.github.com/en/copilot/reference/customization-cheat-sheet (undated)
- [S3] https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills (undated)
- [S4] https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills (undated)
- [S5] https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference (last commit 2026-11-17)
- [S6] https://docs.github.com/en/copilot/reference/copilot-feature-matrix (undated; public preview)
- [S7] https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference (2026-10-28)
- [S8] https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-creating (2026-10-28)
- [S9] https://docs.github.com/en/copilot/reference/plugin-and-marketplace-reference (2026-10-28)
- [S10] https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-finding-installing (2026-10-28)
- [S11] https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference (2026-11-13)
- [S12] https://docs.github.com/en/copilot/reference/hooks-reference (2026-11-09)
- [S13] https://docs.github.com/en/copilot/concepts/customizations/hooks (2026-10-20)
- [S14] https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/use-hooks (2026-10-05)
- [S15] https://docs.github.com/en/copilot/tutorials/copilot-cli-hooks (2026-10-26)
- [S16] https://github.com/github/docs/blob/6b0477b8816c70d798f332a215ece56a3fb615e6/content/copilot/reference/hooks-configuration.md (page removed 2026-05-12)
- [S17] https://docs.github.com/en/copilot/how-tos/copilot-cli/automate-copilot-cli/run-cli-programmatically (2026-11-10)
- [S18] https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions (2026-10-19)
- [S19] https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli (2026-11-18)
- [S20] https://docs.github.com/en/copilot/concepts/agents/copilot-cli/about-copilot-cli (2026-10-05)
- [S21] https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/set-session-limit (2026-09-16)
- [S23] https://docs.github.com/en/copilot/reference/ai-models/supported-models (undated)
- [S24] https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing (undated)
- [S25] https://docs.github.com/en/copilot/reference/copilot-billing/request-based-billing-legacy/model-multipliers-for-annual-plans (undated)
- [S26] https://docs.github.com/en/copilot/how-tos/copilot-sdk/getting-started (2026-09-09)
- [S27] https://docs.github.com/en/rest/models/inference (fetched 2026-11-19; says the service was retired on 2026-07-30)
- [S28] https://docs.github.com/en/copilot/concepts/billing-and-usage/organizations-and-enterprises/billing (undated)

GitHub blog changelog:
- [B3] https://github.blog/changelog/2026-02-25-github-copilot-cli-is-now-generally-available/ (2026-02-25)
- [B4] https://github.blog/changelog/2026/04/27/github-copilot-is-moving-to-usage-based-billing/ (2026-04-27)
- [B5] https://github.blog/changelog/2026-06-02-introducing-copilot-cli-and-agentic-capabilities-enhancements-in-jetbrains-ides/ (2026-06-02)
- [B8] https://github.blog/changelog/2026-09-28-claude-sonnet-5-5-in-github-copilot/ (2026-09-28)
- [B9] https://github.blog/changelog/2026-10-07-claude-haiku-5-5-in-github-copilot/ (2026-10-07)
- [B10] https://github.blog/changelog/2026-10-28-work-from-anywhere-with-a-new-connected-copilot-cloud-experience/ (2026-10-28)
- [B12] https://github.blog/changelog/2026-01-21-install-and-use-github-copilot-cli-directly-from-the-github-cli/ (2026-01-21)

github/copilot-cli repository:
- [C1] https://github.com/github/copilot-cli/blob/main/changelog.md (through 1.0.114, 2026-11-18; versions cited inline)
- [C2] https://github.com/github/copilot-cli/issues/4001 (open; opened 2026-07-01, updated 2026-10-26)
- [C3] https://github.com/github/copilot-cli/issues/4399 (open; 2026-08-07)
- [C4] https://github.com/github/copilot-cli/issues/4520 (open; updated 2026-09-08)
- [C5] https://github.com/github/copilot-cli/issues/3254 (open; 2026-05-12)
- [C6] https://github.com/github/copilot-cli/issues/4626 (closed; 2026-08-26; unofficial evidence)
- [C7] https://github.com/github/copilot-cli/issues/5306 (opened 2026-10-30; closed 2026-11-14)
- [C8] https://github.com/github/copilot-cli/issues/4596 (open; updated 2026-11-15)

VS Code:
- [V1] https://code.visualstudio.com/updates/v1_109 (2026-02-04)
- [V2] https://code.visualstudio.com/docs/agent-customization/agent-skills (2026-11-18)
- [V3] https://code.visualstudio.com/docs/agent-customization/migrate-customizations (2026-11-18)
- [V4] https://github.com/microsoft/vscode/blob/main/src/vs/workbench/contrib/chat/common/promptSyntax/languageProviders/promptValidator.ts (main, fetched 2026-11-19; last commit to the file 2026-11-13)
- [V6] https://code.visualstudio.com/docs/agents/reference/agent-plugin-reference (2026-11-18)
- [V7] https://code.visualstudio.com/docs/agent-customization/agent-plugins (2026-11-18)
- [V8] https://code.visualstudio.com/updates/v1_120 (2026-05-13)
- [V9] https://code.visualstudio.com/docs/agent-customization/hooks (2026-11-18; content last edited 2026-11-17)
- [V10] https://code.visualstudio.com/docs/agents/run/agent-harnesses (2026-11-18)
- [V12] https://code.visualstudio.com/docs/agents/reference/hooks-reference (Local harness reference, 2026-11-18)
- [V13] https://code.visualstudio.com/docs/agents/run/subagents (2026-11-18)
- [V15] https://code.visualstudio.com/api/extension-guides/ai/language-model (2026-11-18)
- [V16] https://code.visualstudio.com/docs/configure/command-line (2026-11-18)
- [V17] https://code.visualstudio.com/docs/enterprise/manage-ai-settings (2026-11-18)
- [V18] https://github.com/microsoft/vscode/blob/main/src/vs/workbench/contrib/chat/common/plugins/pluginMarketplaceService.ts (last commit 2026-11-17)

Copilot SDK (the repository now redirects to microsoft/copilot-sdk):
- [K1] https://github.com/github/copilot-sdk/blob/main/nodejs/README.md (2026-11-17)
- [K2] https://github.com/github/copilot-sdk/blob/main/docs/v2-breaking-changes.md (2026-11-18)
- [K3] https://github.com/github/copilot-sdk/blob/v2.0.1/nodejs/src/types.ts (v2.0.1, 2026-11-18)
- [K4] https://github.com/github/copilot-sdk/blob/main/README.md (fetched 2026-11-19)

JetBrains:
- [J1] https://plugins.jetbrains.com/plugin/17718-github-copilot/versions (1.21.0 dated 2026-11-06; 1.21.1 dated 2026-11-16)

Spec:
- [P1] https://github.com/agentplugins/agent-plugins-spec/blob/main/spec/1.0.0.md (1.0.0 published 2026-08-06; the 1.1.0 working draft in the same repo was last committed 2026-11-06)

Plugin files read for this report (local, unchanged):
- `C:\Users\godle\orca\workspaces\code-comments\whiting\plugins\junior-dev\hooks\hooks.json`
- `C:\Users\godle\orca\workspaces\code-comments\whiting\plugins\junior-dev\scripts\hooks.py`
- `C:\Users\godle\orca\workspaces\code-comments\whiting\plugins\junior-dev\scripts\junior.py`
- `C:\Users\godle\orca\workspaces\code-comments\whiting\plugins\junior-dev\skills\junior-dev\SKILL.md`
- `C:\Users\godle\orca\workspaces\code-comments\whiting\plugins\junior-dev\.claude-plugin\plugin.json`
- `C:\Users\godle\orca\workspaces\code-comments\whiting\.claude-plugin\marketplace.json`
