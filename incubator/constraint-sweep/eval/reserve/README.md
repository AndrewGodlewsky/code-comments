# Reserve cases

Cases designed for this eval but not in it. The harness reads only `eval/cases/`, so
nothing here is run, self-tested or leak-checked.

## mirrored-column-order

The original point-of-edit control: add a currency column after amount, where a JSON
layout in `ingest/layout.json` must mirror `COLUMNS`, and the pointer to it sits in the
edited file's docstring. It was replaced on 2026-11-11, before any run, by
`positional-columns-in-sql-pointer`. A control with a different task (a JSON layout
rather than SQL) mixes task difficulty with where the context lives, so it cannot
answer ADR 0001's question cleanly. The eval keeps seven cases, so this one moved here.

Layout: `case/` was `eval/cases/mirrored-column-order/`, `reference/` was
`eval/references/mirrored-column-order/` and `hidden/` was
`eval/hidden/mirrored-column-order/`. Its checks are kept as `RESERVE_CHECKS` in
`eval/grade.py`. Before restoring it, add a check that files it only read stay
byte-identical, as the other cases now have, then run `self-test`.
