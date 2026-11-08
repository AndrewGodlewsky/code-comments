---
description: Find comments and docstrings that name code which no longer exists, in your uncommitted changes
argument-hint: "[base revision, default HEAD]"
---

Run the stale-reference lint over the changes in this repository, then deal with
what it reports.

1. Find the repository root with `git rev-parse --show-toplevel`. Use the base
   revision `$ARGUMENTS` if one was given, otherwise `HEAD`.
2. Run:

   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/stale_refs.py" "<repository root>" --diff <base>
   ```

   This reports only references that the changes made new. It needs Python 3.10 or
   newer and nothing else. Exit status 0 means clean, 1 means findings, 2 means a
   usage or git error. If this is not a git repository, run it on the project root
   without `--diff`, and look only at findings in files you changed.
3. For each finding, open the comment and decide:
   - **Stale:** the comment names something that was renamed or removed. Correct the
     comment so it describes the current code, or delete it if it only restated
     code.
   - **False positive:** the name is real but outside what the lint can see (a
     third-party name, a placeholder, prose that happens to look like a name).
     Leave the comment alone and say so in your report. Add `stale-refs: ignore` to
     the comment only if the user wants the finding silenced for good.
4. Report what you changed and which findings you left, with the reason for each.

The lint is a heuristic. It catches names that no longer exist; it cannot tell
whether a comment's claim about behaviour is still true. That still needs reading.
