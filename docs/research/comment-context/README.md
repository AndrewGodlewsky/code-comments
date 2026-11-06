# Author context about code comments

This collection preserves located passages and their surrounding context from local books, papers, essays and manuals. It does not rank positions or recommend a commenting policy. Read the original for page layout and figures.

Use [the extraction workflow](../../workflows/extract-comment-context.md) for new sources or corrections. The [catalog](sources.json) pins original files, available extent and derived text. Each source links to exact passage selections and unit-by-unit coverage. A completed text traversal is not proof of exhaustive semantic recall or a certified transcription.

From the repository root: `python -B scripts/comment_context.py check` validates hashes, spans, coverage and generated views. Use `render` after edits; `--source ID` checks/renders one source. During extraction, `--allow-pending` permits explicitly unfinished units and missing source batches.

| Available source | Extent | Passages | Reading units | Audit entries |
| --- | --- | ---: | --- | ---: |
| [The Pragmatic Programmer](sources/pragmatic-programmer/passages.md) | machine_transcript | 63 | [14 read](sources/pragmatic-programmer/coverage.json) | 1 |
| [Software Engineering at Google](sources/software-engineering-at-google/passages.md) | local_html_book | 118 | [35 read](sources/software-engineering-at-google/coverage.json) | 1 |
| [A Philosophy of Software Design, second-edition extract](sources/philosophy-of-software-design/passages.md) | available_extract | 11 | [20 read](sources/philosophy-of-software-design/coverage.json) | 1 |
| [Planning and Coding of Problems for an Electronic Computing Instrument](sources/planning-and-coding/passages.md) | local_scanned_part_ii_volumes_1_to_3 | 163 | [194 read](sources/planning-and-coding/coverage.json) | 0 |
| [FORTRAN Programmer's Reference Manual, IBM 704](sources/fortran-1956/passages.md) | local_manual | 8 | [54 read](sources/fortran-1956/coverage.json) | 0 |
| [Literate Programming](sources/literate-programming/passages.md) | local_paper | 15 | [15 read](sources/literate-programming/coverage.json) | 1 |
| [A Rational Design Process: How and Why to Fake It](sources/rational-design-process/passages.md) | local_paper | 12 | [12 read](sources/rational-design-process/coverage.json) | 1 |
| [Code As Documentation](sources/code-as-documentation/passages.md) | local_essay | 4 | [1 read](sources/code-as-documentation/coverage.json) | 1 |
| [Beck Design Rules](sources/beck-design-rules/passages.md) | local_essay | 5 | [1 read](sources/beck-design-rules/coverage.json) | 1 |
| [Testing the Effect of Code Documentation on Large Language Model Code Understanding](sources/documentation-llm-understanding/passages.md) | local_paper | 20 | [7 read](sources/documentation-llm-understanding/coverage.json) | 0 |
| [Comment Traps: How Defective Commented-out Code Augment Defects in AI-Assisted Code Generation](sources/comment-traps/passages.md) | local_paper | 49 | [21 read](sources/comment-traps/coverage.json) | 0 |
| [On the Impact of Code Comments for Automated Bug-Fixing: An Empirical Study](sources/comments-bug-fixing/passages.md) | local_paper | 51 | [13 read](sources/comments-bug-fixing/coverage.json) | 0 |
| [Talking to Itself While Coding: What Makes Comments Help Code Generation?](sources/talking-while-coding/passages.md) | local_paper | 81 | [25 read](sources/talking-while-coding/coverage.json) | 0 |
| When Comments Mislead | Original unavailable | — | No primary text | — |

## Scope and unresolved source limits

### The Pragmatic Programmer

- Available file is a machine-generated audio transcript. Edition, completeness, speaker attribution and transcription accuracy are not independently verified; timestamps are retained.
- All 1342 available normalized transcript lines were read; this is coverage of the local machine transcript, not exhaustive reading or verification of the published book.
- Machine recognition may omit, repeat or mishear speech; original audio was not checked. Proper names, language names, mathematical statements and spoken code may be corrupted. No wording was silently corrected.
- Audiobook code/diagram adaptation and author dialogue differ from a printed book; exact wording, syntax, speaker identity and edition remain unverified. Cue timestamps are audio windows, not word-level locations.
- At 05:17:26 printed code and diagrams are explicitly omitted, at 06:09:48 printed housekeeping code is skipped, and the 08:09:32 Stroop visual cannot be shown. Their actual printed contents are not reconstructed.
- At 01:39:52 the validation example begins mid-sentence. At 08:54:42-08:56:25 the manifesto discussion refers to four values while only two are explicitly enumerated. These apparent omissions are retained, not repaired from memory.

### Software Engineering at Google

- Local HTML files preserve source text; images require separate inspection. One inherited email-deobfuscation script is absent.
- The reading text linearizes HTML inline markup, table cells and lists and does not preserve every code indentation or table column. Original HTML remains the authority; structural checks covered the two ch07 tables and preformatted specimens in ch08/ch10/ch12/ch18, not every page rendered in a browser.
- Figure 17-4 has a horizontally clipped query. Its visible portion and embedded code are supplemented; absent text is not reconstructed. Figure 20-1 supplement omits UI controls and the naming-warning regular expression, distinguishing the human review comment from source comments.
- Figures 23-4 and 23-5 were visually inspected as context for tracked test disablement, but graph curves remain in the original images; no data values were inferred or fully transcribed.
- Independent fidelity/omission audit has not yet been performed by a separate agent.

### A Philosophy of Software Design, second-edition extract

- Only the 20-page local extract is available, not the full book. PDF has no extractable text layer; reading text uses local OCR and requires visual verification.
- This is a discontinuous 20-page extract: printed pages 39-49, 76, 99-100 and 171-174 plus title/copyright. Most of the book, including earlier pages of Why Write Comments, is not local.
- All available OCR units read; only physical pages 15-16 visually checked during extraction. OCR contains code-identifier and punctuation defects; selected blocks preserve them with caveats.

### Planning and Coding of Problems for an Electronic Computing Instrument

- Historical scan with an existing OCR/text layer; sparse and diagram pages require visual inspection. Local volume extent is the scope, not the entire historical publication series.
- Combined Part II, Volumes 1-3 as confirmed by local title page; dual embedded-text and supplemental Windows OCR views. OCR does not reliably reconstruct mathematical/diagram layout.
- All194 physical pages were traversed visually; this is not a certified transcription. Windows OCR loses or reorders some prose and does not preserve complete diagram topology, coding/explanatory-column alignment or mathematical notation. Consult the original physical page for these representations.
- The available scan binds Part II Volumes I-III. References to future Chapters13-14/VolumeIV and other report parts do not make those absent works available here.

### FORTRAN Programmer's Reference Manual, IBM 704

- Historical scan/text layer; layouts, card columns and specimen comments need visual verification.
- Physical pages 9 and 48 code sheets are now transcribed in supplemental spans; alignment, faint characters and handwritten/source anomalies retain explicit notes. No certified transcription of other manual formulas is claimed.
- Reading text has OCR defects in mathematical notation, code and table alignment. Relevant comment rules/specimens were visually inspected; this is full sequential traversal of the available 54-page manual, not a certified transcription of every formula.

### Literate Programming

- Local 15-page manuscript bears submitted to THE COMPUTER JOURNAL and Received September 1983; source filename labels 1984. Physical page locations here refer to this local version, not a different publication layout.
- Text extraction does not preserve underlining, indentation, mathematical scripts or figure layout. Figures 1-4 and quoted voices checked visually; source pages remain authoritative.

### A Rational Design Process: How and Why to Fake It

- Derived text preserves extraction spacing defects; no reconstruction of author wording from secondary summaries.

### Code As Documentation

- Archived HTML retains original-site assets/navigation not fully mirrored.
- Missing external site assets do not supply additional essay text in the local HTML.

### Beck Design Rules

- Archived HTML retains missing website assets and two unavailable images; source text remains local.
- Local HTML references missing Kent Beck portrait and sketch assets. The text contains the four rules and attributed discussion; missing sketch image content cannot be checked locally.

### Testing the Effect of Code Documentation on Large Language Model Code Understanding

- Figures 2-5 on physical pages 4-5 were visually inspected; pinned text contains captions/axis labels but not bar-height data. Consult original figures for graphical values.
- Figure 1 on physical page 3 loses code indentation in pinned text; visual original is required for syntactic layout.

### Comment Traps: How Defective Commented-out Code Augment Defects in AI-Assisted Code Generation

- Code specimens and graphic labels are now visually transcribed in supplemental spans. Indentation and spacing are approximate; generated-block highlighting and UI details are recorded in notes rather than encoded as code.
- Exact plotted bar/radar/line coordinates are not inferred from pixels. Numerical tables and author interpretations remain in base records; consult Figures 5-7 and 9 for graphical values.
- Algorithm 1 (physical p14) text flattens indentation and math spacing.

### On the Impact of Code Comments for Automated Bug-Fixing: An Empirical Study

- Figures 1, 2, 4 and 5 now have supplemental visual transcriptions. Source screenshot clipping and ellipses remain explicit; original figure owns indentation and highlighting.
- A code-versus-prose category-label discrepancy is preserved in Figure 5 supplement notes; no author intent inferred.

### Talking to Itself While Coding: What Makes Comments Help Code Generation?

- Figure 2 variants and separated Tables 4, 16 and 17 now have supplemental visual transcriptions. Indentation is approximate, and bold/asterisk presentation is described in notes.
- Exact plotted coordinates are not inferred; consult original graphics. Base two-column extraction still has formula spacing and occasional concatenated fields, with supplemental tables provided where inspected.

### When Comments Mislead

- Only a secondary brief/availability note is local; no primary-author passage extraction.

## Reading and maintenance

Passage blocks reproduce the selected derived text verbatim, including OCR/transcript defects. Neutral labels and attribution are navigational metadata. Related-record links preserve continuations and qualifications. Inspect `records.json` for exact inclusive line ranges and `coverage.json` for searches, exclusions and audit scope.

The historical and empirical synthesis elsewhere in this repository is a separate layer. Secondary briefs, chat notes, duplicate renderings and reading-list summaries are not counted as additional primary works. Missing originals are cataloged without invented author passages.
