"""The Junior-dev case set: write it from the case-writing workflow's output, load it, validate it.

Each case lives in cases/<id>/ and keeps what the author may see apart from what only the
graders may see:

    visible/brief.md            the request the author plans from
    visible/existing/...        files describing the existing system (some cases only)
    private/quiz.json           8-12 questions; "brief" items carry a fixed key, "design" items a key from the reference
    private/requirements.json   what any acceptable artifact must contain
    private/reference.md        a clear artifact that answers every item
    private/seeded-presentation.md   same information, badly presented
    private/seeded-implicit.md       same design, relationships left implicit
    private/meta.json           id, family, format, complexity, split, undecided points, checker notes

    python -m evaluation.junior_dev.cases write <workflow-output.json>
    python -m evaluation.junior_dev.cases validate
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path, PurePosixPath
import re
import sys

CASES = Path(__file__).resolve().parent / "cases"
SPLITS = {"dev", "heldout", "confirm"}


@dataclass
class Case:
    id: str
    family: str
    format: str
    complexity: str
    split: str
    brief: str
    existing: dict = field(default_factory=dict)
    quiz: list = field(default_factory=list)
    requirements: list = field(default_factory=list)
    reference: str = ""
    seeded_presentation: str = ""
    seeded_implicit: str = ""
    undecided: list = field(default_factory=list)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _safe_relative(raw: str) -> PurePosixPath:
    rel = PurePosixPath(raw.replace("\\", "/"))
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ValueError(f"existing file path must stay inside the case: {raw!r}")
    if rel.parts[0] != "existing":
        rel = PurePosixPath("existing", *rel.parts)
    return rel


def write(output_json: Path, split: str | None = None, root: Path = CASES) -> list[Path]:
    """Write every kept case from a junior-dev-cases workflow output (or its 'result')."""
    data = json.loads(Path(output_json).read_text(encoding="utf-8"))
    data = data.get("result", data)
    written = []
    for item in data["cases"]:
        slot, c = item["slot"], item["case"]
        files = [(_safe_relative(f["path"]), f["content"]) for f in c.get("existing_files", [])]
        base = Path(root) / slot["id"]
        _write(base / "visible" / "brief.md", c["brief"].rstrip() + "\n")
        for rel, content in files:
            _write(base / "visible" / Path(*rel.parts), content)
        _write(base / "private" / "quiz.json", json.dumps(c["quiz"], indent=1, ensure_ascii=False) + "\n")
        _write(base / "private" / "requirements.json", json.dumps(c["requirements"], indent=1, ensure_ascii=False) + "\n")
        _write(base / "private" / "reference.md", c["reference_artifact"].rstrip() + "\n")
        _write(base / "private" / "seeded-presentation.md", c["seeded_presentation"].rstrip() + "\n")
        _write(base / "private" / "seeded-implicit.md", c["seeded_implicit"].rstrip() + "\n")
        meta = {"id": slot["id"], "family": slot["family"], "format": slot["format"], "complexity": slot["complexity"],
                "split": split or slot["split"], "topic": slot.get("topic", ""), "undecided": c.get("undecided", []),
                "checker_notes": item.get("notes", []), "rewritten": item.get("rewritten", False)}
        _write(base / "private" / "meta.json", json.dumps(meta, indent=1, ensure_ascii=False) + "\n")
        written.append(base)
    return written


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def load(split: str | None = None, root: Path = CASES) -> list[Case]:
    out = []
    for base in sorted(p for p in Path(root).iterdir() if p.is_dir()) if Path(root).is_dir() else []:
        meta_path = base / "private" / "meta.json"
        if not meta_path.is_file():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if split and meta["split"] != split:
            continue
        visible = base / "visible"
        existing = {p.relative_to(visible).as_posix(): p.read_text(encoding="utf-8")
                    for p in sorted(visible.rglob("*")) if p.is_file() and p.name != "brief.md"}
        out.append(Case(id=meta["id"], family=meta["family"], format=meta["format"], complexity=meta["complexity"],
                        split=meta["split"], brief=_read(visible / "brief.md"), existing=existing,
                        quiz=json.loads(_read(base / "private" / "quiz.json") or "[]"),
                        requirements=json.loads(_read(base / "private" / "requirements.json") or "[]"),
                        reference=_read(base / "private" / "reference.md"),
                        seeded_presentation=_read(base / "private" / "seeded-presentation.md"),
                        seeded_implicit=_read(base / "private" / "seeded-implicit.md"),
                        undecided=meta.get("undecided", [])))
    return out


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip(" ?.")


def validate(root: Path = CASES) -> list[str]:
    problems, seen, families = [], set(), {}
    for c in load(root=root):
        if c.id in seen:
            problems.append(f"duplicate case id {c.id}")
        seen.add(c.id)
        if c.split not in SPLITS:
            problems.append(f"{c.id}: unknown split {c.split!r}")
        families.setdefault(c.family, set()).add(c.split)
        for name, text in (("brief", c.brief), ("reference", c.reference),
                           ("seeded-presentation", c.seeded_presentation), ("seeded-implicit", c.seeded_implicit)):
            if not text.strip():
                problems.append(f"{c.id}: {name} is empty")
        if not 8 <= len(c.quiz) <= 12:
            problems.append(f"{c.id}: quiz has {len(c.quiz)} items (needs 8-12)")
        ids = [q.get("id") for q in c.quiz]
        if len(set(ids)) != len(ids):
            problems.append(f"{c.id}: duplicate quiz ids")
        if sum(q.get("kind") == "design" for q in c.quiz) < 4:
            problems.append(f"{c.id}: fewer than 4 design items")
        brief = _norm(c.brief)
        for q in c.quiz:
            if q.get("kind") not in ("brief", "design"):
                problems.append(f"{c.id}: {q.get('id')} has kind {q.get('kind')!r}")
            if not str(q.get("key", "")).strip():
                problems.append(f"{c.id}: {q.get('id')} has no key")
            if _norm(q.get("question", "")) and _norm(q["question"]) in brief:
                problems.append(f"{c.id}: {q.get('id')} question appears in the brief")
        if not 4 <= len(c.requirements) <= 8:
            problems.append(f"{c.id}: {len(c.requirements)} requirements (needs 4-8)")
        if c.format.startswith("mermaid") and "```mermaid" not in c.reference:
            problems.append(f"{c.id}: format {c.format} but the reference has no mermaid block")
    for family, splits in families.items():
        if {"dev", "heldout"} <= splits:
            problems.append(f"family {family} is in both dev and heldout")
    return problems


def main(argv: list[str]) -> int:
    if argv[:1] == ["write"] and len(argv) == 2:
        for base in write(Path(argv[1])):
            print(base)
        argv = ["validate"]
    if argv[:1] == ["validate"]:
        problems = validate()
        for p in problems:
            print(p)
        print(f"{len(load())} cases, {len(problems)} problems")
        return 1 if problems else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
