# Author context about code comments

This collection preserves located passages and their surrounding context from local books, papers, essays and manuals. It does not rank positions or recommend a commenting policy. Read the original for page layout and figures.

Use [the extraction workflow](../../workflows/extract-comment-context.md) for new sources or corrections. The [catalog](sources.json) pins original files, available extent and derived text. Each source links to exact passage selections and unit-by-unit coverage. A completed text traversal is not proof of exhaustive semantic recall or a certified transcription.

From the repository root: `python -B scripts/comment_context.py check` validates hashes, spans, coverage and generated views. Use `render` after edits; `--source ID` checks/renders one source. During extraction, `--allow-pending` permits explicitly unfinished units and missing source batches.

| Available source | Extent | Passages | Reading units | Audit entries |
| --- | --- | ---: | --- | ---: |
| [The Pragmatic Programmer](sources/pragmatic-programmer/passages.md) | machine_transcript | 63 | [14 read](sources/pragmatic-programmer/coverage.json) | 0 |
| [Software Engineering at Google](sources/software-engineering-at-google/passages.md) | local_html_book | 81 | [19 pending, 16 read](sources/software-engineering-at-google/coverage.json) | 0 |
| [A Philosophy of Software Design, second-edition extract](sources/philosophy-of-software-design/passages.md) | available_extract | 11 | [20 read](sources/philosophy-of-software-design/coverage.json) | 0 |
| Planning and Coding of Problems for an Electronic Computing Instrument | local_scanned_volume | 0 | Pending | 0 |
| FORTRAN Programmer's Reference Manual, IBM 704 | local_manual | 0 | Pending | 0 |
| Literate Programming | local_paper | 0 | Pending | 0 |
| [A Rational Design Process: How and Why to Fake It](sources/rational-design-process/passages.md) | local_paper | 12 | [12 read](sources/rational-design-process/coverage.json) | 0 |
| [Code As Documentation](sources/code-as-documentation/passages.md) | local_essay | 4 | [1 read](sources/code-as-documentation/coverage.json) | 0 |
| [Beck Design Rules](sources/beck-design-rules/passages.md) | local_essay | 5 | [1 read](sources/beck-design-rules/coverage.json) | 0 |
| [Testing the Effect of Code Documentation on Large Language Model Code Understanding](sources/documentation-llm-understanding/passages.md) | local_paper | 20 | [7 read](sources/documentation-llm-understanding/coverage.json) | 0 |
| [Comment Traps: How Defective Commented-out Code Augment Defects in AI-Assisted Code Generation](sources/comment-traps/passages.md) | local_paper | 36 | [21 read](sources/comment-traps/coverage.json) | 0 |
| [On the Impact of Code Comments for Automated Bug-Fixing: An Empirical Study](sources/comments-bug-fixing/passages.md) | local_paper | 41 | [13 read](sources/comments-bug-fixing/coverage.json) | 0 |
| [Talking to Itself While Coding](sources/talking-while-coding/passages.md) | local_paper | 70 | [25 read](sources/talking-while-coding/coverage.json) | 0 |
| When Comments Mislead | Original unavailable | — | No primary text | — |

## Scope and unresolved source limits

### The Pragmatic Programmer

- Available file is a machine-generated audio transcript. Edition, completeness, speaker attribution and transcription accuracy are not independently verified; timestamps are retained.
- All 1342 available normalized transcript lines were read; this is coverage of the local machine transcript, not exhaustive reading or verification of the published book.
- Machine recognition may omit, repeat or mishear speech; original audio was not checked. Proper names, language names, mathematical statements and spoken code may be corrupted. No wording was silently corrected.
- Audiobook code/diagram adaptation and author dialogue differ from a printed book; exact wording, syntax, speaker identity and edition remain unverified. Cue timestamps are audio windows, not word-level locations.
- At 05:17:26 printed code and diagrams are explicitly omitted, at 06:09:48 printed housekeeping code is skipped, and the 08:09:32 Stroop visual cannot be shown. Their actual printed contents are not reconstructed.
- At 01:39:52 the validation example begins mid-sentence. At 08:54:42?08:56:25 the manifesto discussion refers to four values while only two are explicitly enumerated. These apparent omissions are retained, not repaired from memory.

### Software Engineering at Google

- Local HTML files preserve source text; images require separate inspection. One inherited email-deobfuscation script is absent.
- Extraction in progress: pending units, second-pass search, and relevant original-image inspection remain.

### A Philosophy of Software Design, second-edition extract

- Only the 20-page local extract is available, not the full book. PDF has no extractable text layer; reading text uses local OCR and requires visual verification.
- This is a discontinuous 20-page extract: printed pages 39?49, 76, 99?100 and 171?174 plus title/copyright. Most of the book, including earlier pages of Why Write Comments, is not local.
- All available OCR units read; only physical pages 15?16 visually checked during extraction. OCR contains code-identifier and punctuation defects; selected blocks preserve them with caveats.

### Planning and Coding of Problems for an Electronic Computing Instrument

- Historical scan with an existing OCR/text layer; sparse and diagram pages require visual inspection. Local volume extent is the scope, not the entire historical publication series.

### FORTRAN Programmer's Reference Manual, IBM 704

- Historical scan/text layer; layouts, card columns and specimen comments need visual verification.

### A Rational Design Process: How and Why to Fake It

- Derived text preserves extraction spacing defects; no reconstruction of author wording from secondary summaries.

### Code As Documentation

- Archived HTML retains original-site assets/navigation not fully mirrored.
- Missing external site assets do not supply additional essay text in the local HTML.

### Beck Design Rules

- Archived HTML retains missing website assets and two unavailable images; source text remains local.
- Local HTML references missing Kent Beck portrait and sketch assets. The text contains the four rules and attributed discussion; missing sketch image content cannot be checked locally.

### Testing the Effect of Code Documentation on Large Language Model Code Understanding

- Figures 2?5 on physical pages 4?5 were visually inspected; pinned text contains captions/axis labels but not bar-height data. Consult original figures for graphical values.
- Figure 1 on physical page 3 loses code indentation in pinned text; visual original is required for syntactic layout.

### Comment Traps: How Defective Commented-out Code Augment Defects in AI-Assisted Code Generation

- Image-only code specimens in Figures 1 (p2), 3 (p6), 4 (p7) and 8 (p13) are not transcribed by the pinned reading text. Original pages were visually inspected; captions and full surrounding methodological discussion are selected.
- Figure 2 (p5) methodology graphic, Figures 5?6 (pp11?12) bars, Figure 7 (p13) radar charts and Figure 9 (p17) line plot are visually inspected but graphic labels/values are not fully transcribed. Consult original pages.
- Algorithm 1 (p14) extraction flattens indentation and math spacing.

### On the Impact of Code Comments for Automated Bug-Fixing: An Empirical Study

- Figures 1 (p2), 2 (p7), 4 and 5 (p10) are visually inspected code/comment specimens absent from pinned base text; supplemental transcription pending coordinator integration.
- Figure 3 (p9) distribution plots are visually inspected but plotted data are not transcribed numerically.
- Math/model notation in prose and Table 3 is flattened by extraction; consult originals for subscripts and superscripts.

### Talking to Itself While Coding

- Figure 2 on physical page 9 is concatenated/garbled in base text; visual inspection complete and supplemental transcription pending integration.
- Tables 4 (p8), 16 and 17 (p24) contain concatenated numeric fields in base extraction. Original tables were visually checked; use original column layout.
- Bold table emphasis, superscripts and indentation are not preserved by the base extraction. Prompts retain source-rendered typography rather than runnable code-fence syntax.

### When Comments Mislead

- Only a secondary brief/availability note is local; no primary-author passage extraction.

## Reading and maintenance

Passage blocks reproduce the selected derived text verbatim, including OCR/transcript defects. Neutral labels and attribution are navigational metadata. Related-record links preserve continuations and qualifications. Inspect `records.json` for exact inclusive line ranges and `coverage.json` for searches, exclusions and audit scope.

The historical and empirical synthesis elsewhere in this repository is a separate layer. Secondary briefs, chat notes, duplicate renderings and reading-list summaries are not counted as additional primary works. Missing originals are cataloged without invented author passages.
