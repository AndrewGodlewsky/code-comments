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
  `heading`, `attribution`, `context`, `notes`, and `related_record_ids`.
  The record file also pins `text_sha256`. Heading/context are neutral
  navigation, not findings or recommendations. Notes carry uncertainty, quoted
  voices and cross-page dependencies. Each selected span is preserved verbatim
  from the pinned reading text; the renderer supplies its text, not the agent.
- `sources/<source-id>/coverage.json`: unit-by-unit reading/search/visual coverage,
  terms used, explicit scope exclusions, unresolved gaps and reviewer checks.
  Pin `text_sha256` here too. Every reading unit appears exactly once, with
  `reading_status` (`read`, `partial`, `unreadable`, `pending`), cumulative `checks`
  (such as `search` and `visual`), and `notes`; these are not mutually exclusive.
- `sources/<source-id>/passages.md`: generated human view of the records, with
  original-file and reading-unit locations. Edit records rather than this view.
- `README.md`: source index and instructions for finding material. No ranked
  shortlist, synthesized conclusion or recommended comment policy.

Keep original source bytes unchanged. A changed edition/hash gets an explicit
catalog revision and re-extraction; old line ranges must not silently point into
new text. Stable IDs must not be reused for different passages. Related or
repeated statements can remain separate when their context differs.
Pin the derived text bytes as well as the originals: OCR/extraction updates can
invalidate spans even when the original files have not changed. Physical PDF
page numbers are mandatory; add printed-page labels when observed. HTML units
name their chapter/file, and transcript units retain cue timestamps. Untranscribed
figures retain original-page/image references and an explicit unresolved gap.

If a legible figure or scan is missing from extracted text, append its OCR or
manual transcription to that physical-page unit. Store its inclusive range,
`method` and `notes` in the unit's `supplements` array, then repin catalog,
records and coverage together. Preserve original extraction lines and check every
existing span before repinning. Label supplemental passage headings explicitly;
record approximate indentation, clipped source text and untranscribed graphics.
Do not infer numerical plot values from pixels or silently repair source errors.
Empty OCR results have no supplemental span and remain noted in page coverage.

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

## File shapes

`records.json` uses this shape (replace the example values):

```json
{
  "schema_version": 1,
  "source_id": "source-slug",
  "text_sha256": "hash of text/source-slug.json",
  "records": [
    {
      "id": "source-slug-001",
      "unit": "p001",
      "start_line": 1,
      "end_line": 12,
      "heading": "Source section or neutral passage label",
      "attribution": "Source author, quoted speaker, or explicitly uncertain voice",
      "context": "Non-evaluative placement and dependencies of this passage",
      "notes": "Transcription/layout limits or empty string",
      "related_record_ids": []
    }
  ]
}
```

`coverage.json` has `schema_version`, `source_id`, `text_sha256`, `search_terms`
(string array), `units` (one object per reading unit with `unit`, `reading_status`,
`checks` string array, and `notes`), `exclusions` and `unresolved_gaps` (string
arrays), and `audit` (string array, initially empty). A zero-record source still
needs a coverage file explaining its actual traversal and scope boundaries.

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
   literate, self-documenting/self documenting, self-explanatory, naming, identifier,
   docstring, prose, narrative, specification and relevant language syntax. Expand
   terms from the author's vocabulary. A keyword hit count is not full coverage.
5. Read each candidate's surrounding section, examples, footnotes and related
   passages. Select enough contiguous lines to retain premises, qualifications
   and opposing views. Split only at intelligible boundaries; use connected
   records for cross-page content. Prefer retaining context over compressing it.
6. Write records and coverage. Record every unit's actual reading status and
   cumulative checks, what was checked, and why an
   apparent hit was excluded (for example, publication metadata or an unrelated
   use of "comment"). A searched-only unit remains searched-only. Never describe
   a partial extract, transcript, OCR sweep or sampled audit as exhaustive reading
   of the original published work. Record uncertainties rather than resolving
   them with outside knowledge.
7. Render the human views and run deterministic checks for source hashes,
   source/unit IDs, bounded line spans, unique record IDs and coverage accounting.
   These checks establish traceability, not semantic completeness.
   Run `python -B scripts/comment_context.py render`, then
   `python -B scripts/comment_context.py check` from the repository root.
   Use `--source <id>` for one completed batch, or `--allow-pending` during work.
   The final check rejects pending units; partial/unreadable units remain explicit
   limitations rather than silently being called read. Tool regression checks are
   `python -B -m unittest discover -s tests -p test_comment_context.py`.
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
