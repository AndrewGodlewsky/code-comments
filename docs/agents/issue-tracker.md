# Issue tracker: GitHub

Issues and specs live in `AndrewGodlewsky/code-comments`. Use the `gh` CLI for
tracker operations. Run commands from this clone; when outside it, add
`--repo AndrewGodlewsky/code-comments` to `gh issue` commands.

Before the first issue creation of a session, verify the target with
`gh repo view --json nameWithOwner`. File work in this repo, not the upstream
repository that distributes the skills.

## Conventions

- **Create**: `gh issue create --title "..." --body-file <path>`.
- **Read**: `gh issue view <number> --json number,title,body,labels,comments`.
- **List**: `gh issue list --state open --limit 100 --json number,title,body,labels,assignees`.
  Use `--label` and `--state` filters as appropriate; retrieve additional results
  when the limit is reached.
- **Edit the body**: `gh issue edit <number> --body-file <path>`.
- **Comment**: `gh issue comment <number> --body-file <path>`.
- **Labels**: `gh issue edit <number> --add-label "..."` or `--remove-label "..."`.
- **Close**: post the explanation as a separate comment, then
  `gh issue close <number>`. This preserves the explanation even if the issue
  was already closed.

For multiline issue bodies, comments, and PR descriptions, write the exact text
as UTF-8 to a temporary file and pass `--body-file`. Preserve actual newlines.

## Parent issues and blockers

Use GitHub's native sub-issues and issue dependencies. The following API commands
also work with CLI versions that lack dedicated sub-issue and dependency flags.
Database IDs below are numeric `.id` values, not issue numbers or node IDs.

- **Find an issue's database ID**:
  `gh api repos/AndrewGodlewsky/code-comments/issues/<number> --jq .id`.
- **Attach a child to a parent**:
  `gh api --method POST repos/AndrewGodlewsky/code-comments/issues/<parent>/sub_issues -F sub_issue_id=<child-db-id>`.
- **List children**:
  `gh api --paginate repos/AndrewGodlewsky/code-comments/issues/<parent>/sub_issues`.
- **Add a blocker to a child**:
  `gh api --method POST repos/AndrewGodlewsky/code-comments/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`.
- **Count open blockers**:
  `gh api repos/AndrewGodlewsky/code-comments/issues/<number> --jq .issue_dependencies_summary.blocked_by`.

Where native relationships are unavailable, put `Part of #<parent>` and
`Blocked by: #<number>, #<number>` at the top of the child body, and maintain a
task list linking children in the parent body. A ticket is startable only when
all its blockers are closed. If dependency information is unavailable, inspect
the recorded blockers rather than treating missing data as zero.

## Pull requests as a triage surface

**PRs as a request surface: no.**

If this is later changed to `yes`, use `gh pr view`, `gh pr diff`, `gh pr comment`,
`gh pr edit`, and `gh pr close` for external PR requests. Read both the PR body
and its comments; `gh pr view <number> --comments` alone can omit the body.
GitHub shares issue and PR numbers: resolve an ambiguous number with
`gh pr view <number>`, falling back to `gh issue view <number>`.

## Skill operations

When a skill says **publish to the issue tracker**, create a GitHub issue.
When it says **fetch the relevant ticket**, read the issue and its comments.

## Wayfinding operations

- **Map**: one issue labelled `wayfinder:map` containing Notes, Decisions-so-far,
  and Fog. Create this label if missing when first using wayfinding.
- **Child ticket**: attach a sub-issue to the map, labelled `wayfinder:<type>`
  (`research`, `prototype`, `grilling`, or `task`). Create the required labels
  if missing. Use the parent/task-list fallback above if necessary.
- **Blocking**: record and inspect native dependencies as described above.
- **Frontier**: list the map's open children, exclude tickets with open blockers
  or an assignee, and select the first remaining ticket in map order.
- **Claim**: `gh issue edit <number> --add-assignee "@me"`, the session's first write.
- **Resolve**: comment with the answer, close the child, then update the map's
  Decisions-so-far with a short summary and link. Preserve existing map content.
