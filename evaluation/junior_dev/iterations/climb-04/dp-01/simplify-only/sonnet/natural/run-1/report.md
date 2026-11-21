## Review of dp-01 (simplify-only, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered into the newcomer layout: summary, terms, how it runs, flowchart, notes after the diagram, failure table, open questions last.
- Replaced the dense bullet-heavy 'Design summary' with a 3-sentence summary and a one-line-per-term glossary.
- Merged the separate Triggers, Where state lives, Staging, Atomic publish, Merge logic, Extract and High-water mark bullets into the glossary and the notes on steps, since the flowchart already shows them; removed duplicated statements of the same rule.
- Merged the 'Assumptions to confirm' section into 'Open questions' at the end; moved the reconciliation retry policy into the failure table as its own row.
- Folded the overlapping staleness-alert and watchdog statements into one short watchdog note.
- Removed the claim that the scheduler keeps the counter as separate prose from the retry text and kept it in one line under 'How it runs'.
- Trimmed the per-attempt timeout wording to a plain statement and listed the missing value as an open question.
- Kept the Mermaid diagram unchanged and kept every requirement and failure case.

### Holes
- None.
