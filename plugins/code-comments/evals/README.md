# Activation evals

These cases measure whether Claude Code loads the `code-comments` skill on its own,
without being told to. The [hygiene eval](../../../evaluation/hygiene/README.md) tells
the model to read the skill, so it cannot answer this. See #20.

Each case runs a headless Claude Code session with the plugin installed, in a small
scaffolded repository (`fixture/`) that has comments. A case passes its activation
grader when the session calls the Skill tool with `code-comments` (should load) or
never calls it (should not load). A second grader checks that the task itself was done.

| Case | Request | Expect |
| --- | --- | --- |
| `load-add-retry-param` | Add a `max_retries` argument to `push()` | load |
| `load-comment-refresh` | Tidy the out-of-date comments in `ledger/sync.py` | load |
| `load-fix-double-discount` | Fix a coupon discount applied twice | load |
| `load-rename-calc` | Rename `calc` to `compute_total` and update callers | load |
| `load-review-pricing` | Review `ledger/pricing.py`, change nothing yet | load |
| `load-ticket-batch-limit` | Cap batches at 5 invoices, per ticket PAY-212 | load |
| `skip-ask-return-value` | What does `push()` return? | not load |
| `skip-explain-comment` | Explain the comment above `TAX_RATE` | not load |
| `skip-find-callers` | Which files import `fetch_with_retry`? | not load |
| `skip-release-note` | Write a customer release note, in the reply | not load |

## Run them

```
claude plugin eval plugins/code-comments --runs 3 --ablation none --scaffold \
  --trust-plugin --allow-tools Edit Write --no-publish --model haiku \
  --max-cost-usd 3 --json <path outside the repository>
```

Raw results land in `evals/results/`, which git ignores. Copy summaries here by hand.

## Results, 2026-11-09

Claude Code 2.1.319, three runs per case, with the `with` arm only, because the skill
cannot load without the plugin.

| Model | Recall (loaded when it should) | Specificity (stayed out when it should) | Task done | Cost |
| --- | --- | --- | --- | --- |
| Haiku | 0 of 18 runs | 12 of 12 runs | 30 of 30 | $0.07 |
| Sonnet | 3 of 18 runs | 12 of 12 runs | 30 of 30 | $0.99 |

Smoke runs beforehand cost about $0.01, so the total was about $1.07. Per-run grades,
turns and costs are in `results-2026-11-09.json`.

- **The skill almost never loads on its own.** Haiku never loaded it. Sonnet loaded
  it only for the request that is about comments (`load-comment-refresh`, three of
  three), and never for a fix, rename, review, new parameter or ticket-driven change.
- **It stays out of requests it should stay out of.** No model loaded it for a
  question, an explanation, a search or a release note.
- **The tasks were done anyway.** Every run made the change or gave the answer, so a
  missed load cost nothing on these small tasks. It does mean that, in ordinary use,
  the measured benefit of the skill in the hygiene eval is not reached unless someone
  asks for the skill.

Read these with care:

- Three runs per case on a handful of short requests, in one tiny repository.
- The sessions ran with the user's other plugins and Claude Code's built-in skills
  available, which compete for the same choice.
- Bash was not allowed, because the Windows sandbox was unavailable, so there is no
  shell or git near-miss case. Sessions ran as child sessions of another Claude Code
  session.
- Specificity was easy to get while the skill rarely loads at all; it would need
  re-testing after any change that raises recall.

Changing the skill's description to raise recall is a separate step, and it must be
tested again against both sides of this eval.
