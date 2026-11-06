# Extract author context about code comments

Use this workflow when adding books, papers, essays or manual editions to the
comment-context collection. It extracts source material for later judgment; it
does not design the Code Comments skill or rank authors' advice.

## Output contract

The collection lives in `docs/research/comment-context/`:

- `sources.json`: stable source IDs, titles/authors, exact input paths and SHA-256
  hashes, available edition/extent, extraction method and limitations.
- `text/<source-id>.json`: generated reading units with stable unit IDs, original
  source locations and numbered text lines. Treat these as derived reading aids;
  originals own the content. Keep OCR/transcription limits explicit.
- `sources/<source-id>/records.json`: canonical passage selections, in source
  order. Each record has `id`, `unit`, inclusive one-based `start_line`/`end_line`,
  `heading`, `attribution`, `context`, and `notes`. Heading/context are neutral
  navigation, not findings or recommendations. Notes carry uncertainty, quoted
  voices and cross-page dependencies. Each selected span is preserved verbatim
  from the pinned reading text; the renderer supplies its text, not the agent.
- `sources/<source-id>/coverage.json`: unit-by-unit reading/search/visual coverage,
  terms used, explicit scope exclusions, unresolved gaps and reviewer checks.
- `sources/<source-id>/passages.md`: generated human view of the records, with
  original-file and reading-unit locations. Edit records rather than this view.
- `README.md`: source index and instructions for finding material. No ranked
  shortlist, synthesized conclusion or recommended comment policy.

Keep original source bytes unchanged. A changed edition/hash gets an explicit
catalog revision and re-extraction; old line ranges must not silently point into
new text. Stable IDs must not be reused for different passages. Related or
repeated statements can remain separate when their context differs.

## Inclusion rule

Capture every located passage about writing, reading, changing, omitting,
generating or misusing code comments. Include praise, criticism, exceptions,
uncertainty, maintenance/staleness, redundant/misleading comments, commented-out
code, documentation comments, contracts, rationale, intent, code examples,
literate programming and explanations of code through other representations.
Keep adjacent discussion of self-explanatory code, naming, tests and external
documentation when it explains an author's position on code explanation.

For a paper whose subject is comments, include its methods, interventions,
examples, results, null/negative results, qualifications, related-work positions,
threats and appendices needed to understand those claims. Preserve table headers,
units, baselines and denominators with results. Do not select only conclusions.
Include code-comment specimens and syntax rules even if no opinion accompanies
them. Label diagrams, pseudocode or external documentation as such; never turn an
adjacent representation into a claim that the author advocated inline comments.

Do not filter by importance, novelty, agreement with project intuition, apparent
quality or whether a passage supports a positive outcome. Relevance to this
defined subject is the selection boundary. Preserve counterarguments in the
same record or explicitly connected neighboring records. Attribute a reported
third-party position to that party, not automatically to the source author.

## Procedure

1. Inventory the actual local primary files before delegating. Hash every input;
   distinguish full work, available extract, machine transcript, duplicate,
   secondary summary and unavailable original. A local summary is not a substitute
   for a missing paper. List missing works without inventing their content.
2. Prepare reading units for every available page/chapter/cue, including front
   matter, appendices, footnotes and indexes. Retain original-page mapping. Check
   for empty/garbled extraction, two-column ordering, tables and image-only pages;
   render/OCR or inspect them visually. Record tool/method and unresolved defects.
   Generated text is not a certified transcription.
3. Record issue/branch ownership and bounded assignments before dispatch. Give
   each fresh-context agent this workflow, its source IDs, exact output paths,
   scope and limits. The coordinator owns Git/index/catalog changes. Agents write
   only their assigned records/coverage files and report when safe to checkpoint.
4. Traverse every available unit in order. Use broad lexical searches as a second
   pass: comment, annotation, remark, documentation, explanation, rationale,
   intent, reader, readability, clarity, maintain, obsolete, redundant, misleading,
   literate, self-documenting, specification and relevant language syntax. Expand
   terms from the author's vocabulary. A keyword hit count is not full coverage.
5. Read each candidate's surrounding section, examples, footnotes and related
   passages. Select enough contiguous lines to retain premises, qualifications
   and opposing views. Split only at intelligible boundaries; use connected
   records for cross-page content. Prefer retaining context over compressing it.
6. Write records and coverage. Record every unit's actual status (`read`,
   `searched`, `visual`, `unreadable`, or `pending`), what was checked, and why an
   apparent hit was excluded (for example, publication metadata or an unrelated
   use of "comment"). A searched-only unit remains searched-only. Never describe
   a partial extract, transcript, OCR sweep or sampled audit as exhaustive reading
   of the original published work. Record uncertainties rather than resolving
   them with outside knowledge.
7. Render the human views and run deterministic checks for source hashes,
   source/unit IDs, bounded line spans, unique record IDs and coverage accounting.
   These checks establish traceability, not semantic completeness.
8. Assign an independent agent to check fidelity and omissions against originals,
   including negative/mixed passages, low-hit units, tables and extraction gaps.
   Record the scope of its audit and fix findings without turning the review into
   an evaluation of which authors are right. Preserve unresolved gaps in the index.
9. Commit/push coherent source batches and the updated index. Before handoff,
   reconcile all tracked/untracked deliverables using the repository Git workflow.
   Report which available material was covered and exactly what remains uncertain.

## Reuse prompt

> Follow `docs/workflows/extract-comment-context.md` for these newly added local
> sources: <paths>. Inventory and pin the inputs, reuse the existing collection
> structure, and delegate disjoint source sets. Extract all located comment-related
> positions and context without ranking or recommendations. Preserve source
> locations and coverage limits, run the checks, independently audit omissions,
> and commit/push the results. Leave existing source records unchanged unless their
> input version changed or a documented omission/correction is being addressed.
