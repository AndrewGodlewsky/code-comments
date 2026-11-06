# Comment Context Extraction Implementation Plan

**Goal:** Preserve local authors' comment-related context without evaluative synthesis.
**Architecture:** Pinned catalog and derived reading units; canonical source-ordered
line-span records; generated Markdown and mechanical validation.
**Tech stack:** Python standard library for storage/render/checks; existing local
PDF/HTML extraction and rendering tools for reading aids.
**Spec:** [design](../specs/2026-11-06-comment-context-design.md).

1. Checkpoint workflow/design; independent builder check against user scope.
2. Inventory/hash 13 primary works and the unavailable full-text item. Prepare
   all reading units, resolving image-only pages with local visual/OCR work.
3. Delegate disjoint source sets under #14; root handles extraction-tooling and
   remaining sources. Agents read units, preserve passage spans and record actual
   coverage. Checkpoint finished batches without waiting for the whole collection.
4. Implement/test small catalog/span/coverage validation and Markdown rendering.
   Link workflow/index from repository discovery documents; keep source bytes intact.
5. Independent source-fidelity and omission audit, fix findings, render/check,
   push, then normal separate review/integration/cleanup/audit closeout. Preserve
   unfinished #7/#8 and unrelated workspaces. No paid/model experiment is run.
