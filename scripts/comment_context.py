"""Validate pinned source selections and render their non-evaluative reading views."""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
COLLECTION = Path("docs/research/comment-context")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local_path(root, relative):
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), f"Path escapes repository: {relative}")
    return path


def validate_source(root, source, allow_pending=False):
    sid = source["id"]
    for entry in source["inputs"]:
        path = local_path(root, entry["path"])
        require(path.is_file(), f"{sid}: missing input {path}")
        require(path.stat().st_size == entry["bytes"] and sha256(path) == entry["sha256"],
                f"{sid}: original bytes changed: {path}")
    if source["text_path"] is None:
        require(source["unit_count"] == 0, f"{sid}: unavailable source has units")
        return None
    path = local_path(root, source["text_path"])
    digest = sha256(path)
    require(digest == source["text_sha256"], f"{sid}: derived text hash mismatch")
    text = read_json(path)
    require(text["schema_version"] == 1 and text["source_id"] == sid, f"{sid}: text identity")
    units = {unit["id"]: unit for unit in text["units"]}
    require(len(units) == len(text["units"]) == source["unit_count"], f"{sid}: unit count/duplicates")
    inputs = {entry["path"] for entry in source["inputs"]}
    for unit in units.values():
        require(unit["source_path"] in inputs, f"{sid}: unit has unpinned source")
        require(isinstance(unit["lines"], list) and all(isinstance(x, str) for x in unit["lines"]),
                f"{sid}: invalid reading lines")
    directory = root / COLLECTION / "sources" / sid
    paths = [directory / "records.json", directory / "coverage.json"]
    if allow_pending and not any(p.exists() for p in paths):
        return text, None, None
    records, coverage = [read_json(p) for p in paths]
    for artifact in (records, coverage):
        require(artifact["schema_version"] == 1 and artifact["source_id"] == sid,
                f"{sid}: selection/coverage identity")
        require(artifact["text_sha256"] == digest, f"{sid}: stale selection/coverage text hash")
    ids = [record["id"] for record in records["records"]]
    require(len(ids) == len(set(ids)), f"{sid}: duplicate record IDs")
    previous = (-1, -1)
    order = {unit: i for i, unit in enumerate(units)}
    for record in records["records"]:
        require(record["id"].startswith(sid + "-"), f"{sid}: unscoped record ID")
        require(record["unit"] in units, f"{sid}: unknown selected unit")
        start, end = record["start_line"], record["end_line"]
        require(type(start) is int and type(end) is int and
                1 <= start <= end <= len(units[record["unit"]]["lines"]),
                f"{record['id']}: invalid inclusive line span")
        position = (order[record["unit"]], start)
        require(position >= previous, f"{record['id']}: records not in source order")
        previous = position
        for key in ("heading", "attribution", "context", "notes"):
            require(isinstance(record[key], str), f"{record['id']}: {key} must be text")
        require(isinstance(record["related_record_ids"], list) and
                all(x in ids and x != record["id"] for x in record["related_record_ids"]),
                f"{record['id']}: invalid related record")
    covered = [unit["unit"] for unit in coverage["units"]]
    require(len(covered) == len(set(covered)) and set(covered) == set(units),
            f"{sid}: coverage must account for every unit exactly once")
    for unit in coverage["units"]:
        require(unit["reading_status"] in {"read", "partial", "unreadable", "pending"},
                f"{sid}: invalid reading status")
        require(isinstance(unit["checks"], list) and all(isinstance(x, str) for x in unit["checks"])
                and isinstance(unit["notes"], str), f"{sid}: invalid coverage notes/checks")
        if not allow_pending:
            require(unit["reading_status"] != "pending", f"{sid}: pending reading unit {unit['unit']}")
    for key in ("search_terms", "exclusions", "unresolved_gaps", "audit"):
        require(isinstance(coverage[key], list) and all(isinstance(x, str) for x in coverage[key]),
                f"{sid}: {key} must be a text array")
    return text, records, coverage


def link(destination, target):
    return quote(Path(os.path.relpath(target, destination.parent)).as_posix(), safe="/.-_")


def render_source(root, source, data):
    text, records, coverage = data
    destination = root / COLLECTION / "sources" / source["id"] / "passages.md"
    units = {unit["id"]: unit for unit in text["units"]}
    out = [f"# {source['title']}: source passages", "",
           "Generated from records.json and the pinned reading text. No ranking or recommendation is implied.", "",
           f"Extent: `{source['extent']}`. Text SHA-256: `{source['text_sha256']}`.", "",
           "[Selections](records.json) · [Coverage and gaps](coverage.json) · [Collection index](../../README.md)", ""]
    for limitation in source["limitations"] + coverage["unresolved_gaps"]:
        out.extend([f"- {limitation}"])
    out.append("")
    for record in records["records"]:
        unit = units[record["unit"]]
        original = link(destination, root / unit["source_path"])
        if unit["source_path"].lower().endswith(".pdf") and re.fullmatch(r"p\d+", unit["id"]):
            original += f"#page={int(unit['id'][1:])}"
        body = "\n".join(unit["lines"][record["start_line"] - 1:record["end_line"]])
        # A source may itself contain Markdown fences; do not let it escape its quotation.
        fence = "`" * max(3, 1 + max((len(m.group()) for m in re.finditer(r"`+", body)), default=0))
        out.extend([f"<a id=\"{record['id']}\"></a>", f"## {record['id']} — {record['heading']}", "",
                    f"Source: [{unit['location']}]({original}); reading unit `{unit['id']}`, "
                    f"lines {record['start_line']}–{record['end_line']}.", "",
                    f"Attribution: {record['attribution']}", "", f"Context: {record['context']}", ""])
        if record["notes"]:
            out.extend([f"Transcription/context notes: {record['notes']}", ""])
        if record["related_record_ids"]:
            out.extend(["Related: " + ", ".join(f"[{rid}](#{rid})" for rid in record["related_record_ids"]), ""])
        out.extend([fence + "text", body, fence, ""])
    return destination, "\n".join(out).rstrip() + "\n"


def render_index(root, sources, datasets):
    destination = root / COLLECTION / "README.md"
    out = ["# Author context about code comments", "",
           "This collection preserves located passages and their surrounding context from local books, papers, essays and manuals. "
           "It does not rank positions or recommend a commenting policy. Read the original for page layout and figures.", "",
           "Use [the extraction workflow](../../workflows/extract-comment-context.md) for new sources or corrections. "
           "The [catalog](sources.json) pins original files, available extent and derived text. "
           "Each source links to exact passage selections and unit-by-unit coverage. "
           "A completed text traversal is not proof of exhaustive semantic recall or a certified transcription.", "",
           "From the repository root: `python -B scripts/comment_context.py check` validates hashes, spans, coverage and generated views. "
           "Use `render` after edits; `--source ID` checks/renders one source. "
           "During extraction, `--allow-pending` permits explicitly unfinished units and missing source batches.", "",
           "| Available source | Extent | Passages | Reading units | Audit entries |", "| --- | --- | ---: | --- | ---: |"]
    for source, data in zip(sources, datasets):
        sid = source["id"]
        if data is None:
            out.append(f"| {source['title']} | Original unavailable | — | No primary text | — |")
        elif data[1] is None:
            out.append(f"| {source['title']} | {source['extent']} | 0 | Pending | 0 |")
        else:
            _, records, coverage = data
            counts = Counter(unit["reading_status"] for unit in coverage["units"])
            statuses = ", ".join(f"{n} {status}" for status, n in sorted(counts.items()))
            out.append(f"| [{source['title']}](sources/{sid}/passages.md) | {source['extent']} | "
                       f"{len(records['records'])} | [{statuses}](sources/{sid}/coverage.json) | {len(coverage['audit'])} |")
    out.extend(["", "## Scope and unresolved source limits", ""])
    for source, data in zip(sources, datasets):
        gaps = source["limitations"] + (data[2]["unresolved_gaps"] if data and data[2] else [])
        if gaps:
            out.extend([f"### {source['title']}", ""] + [f"- {gap}" for gap in dict.fromkeys(gaps)] + [""])
    out.extend(["## Reading and maintenance", "",
                "Passage blocks reproduce the selected derived text verbatim, including OCR/transcript defects. "
                "Neutral labels and attribution are navigational metadata. Related-record links preserve continuations and qualifications. "
                "Inspect `records.json` for exact inclusive line ranges and `coverage.json` for searches, exclusions and audit scope.", "",
                "The historical and empirical synthesis elsewhere in this repository is a separate layer. "
                "Secondary briefs, chat notes, duplicate renderings and reading-list summaries are not counted as additional primary works. "
                "Missing originals are cataloged without invented author passages.", ""])
    return destination, "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "render"])
    parser.add_argument("--source", help="Validate/render only this catalog source")
    parser.add_argument("--allow-pending", action="store_true")
    args = parser.parse_args()
    catalog = read_json(ROOT / COLLECTION / "sources.json")
    sources = catalog["sources"]
    require(catalog["schema_version"] == 1, "Unsupported catalog version")
    require(len({source['id'] for source in sources}) == len(sources), "Duplicate source IDs")
    if args.source:
        sources = [source for source in sources if source["id"] == args.source]
        require(sources, f"Unknown source {args.source}")
    datasets = [validate_source(ROOT, source, args.allow_pending) for source in sources]
    outputs = [render_source(ROOT, source, data) for source, data in zip(sources, datasets) if data and data[1]]
    if not args.source:
        outputs.append(render_index(ROOT, sources, datasets))
    for path, content in outputs:
        if args.command == "render":
            path.write_text(content, encoding="utf-8", newline="\n")
        else:
            require(path.is_file() and path.read_text(encoding="utf-8") == content,
                    f"Stale/missing generated view: {path}; run render")
    print(f"{args.command}: {len(sources)} sources validated; {len(outputs)} views "
          f"{'written' if args.command == 'render' else 'verified'}. "
          "Mechanical checks do not establish semantic completeness.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        raise SystemExit(f"comment-context: {error}")
