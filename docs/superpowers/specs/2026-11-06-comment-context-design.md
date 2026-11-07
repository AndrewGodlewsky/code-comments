# Comment context extraction design

The user wants all available authors' positions and surrounding context about
code commenting retained for a later reviewer, including positive, negative and
mixed material. This task creates a reusable repository workflow first, then uses
subagents to process the current local collection. It does not select good advice,
summarize the collection into a policy, or implement the Code Comments product.

The canonical procedure and file ownership live in
[the extraction workflow](../../workflows/extract-comment-context.md). The selected
structure uses a pinned source catalog, derived reading units, line-span passage
records, explicit coverage ledgers and generated human-readable views. This is a
coordinator's implementation choice under the user's requested workflow/structure;
no additional approval decision or external campaign is needed.

There are 13 available primary works: three books/available book forms, six
historical papers/manuals/essays, and four modern papers. The missing fifth modern
paper is cataloged as unavailable; its saved brief is secondary material. Existing
research reports, source-chat exports, screenshots and extracted-text duplicates
are provenance/context, not extra primary works to double-count.

Scope covers the actual local bytes. Ousterhout is a 20-page extract with no
searchable text layer, the Pragmatic Programmer file is an unverified machine
transcript, and old manuals contain scan/diagram pages. These require explicit
reading limits and visual checks. Local rendering/OCR is allowed; no model API
campaign, fresh literature search or purchase is part of this task.

Root owns catalog/tooling/navigation/Git. Agents intentionally share the task
checkout with non-overlapping source record directories; assignments are recorded
in #14 before dispatch. This avoids concurrent index or Git mutation. A fresh
independent reviewer checks the workflow/schema before extraction and another
review pass checks delivered fidelity/coverage before closeout.

Success means the available collection is accounted for, located material is
preserved with its attribution/context, coverage limits are visible, the workflow
is reusable, and all deliverables are checkpointed and reviewed. No claim of
mathematically complete semantic recall or verified book transcription is made.
