"""Lint Code Comments skill variants for format, portability, traceability and case leakage.

python scripts/lint_skills.py            # lint every variant in skill-variants/variants.json
python scripts/lint_skills.py <dir>...   # lint specific skill directories (format, portability, leakage)

Rules (see docs/skill/README.md):
- Agent Skills format: SKILL.md with YAML frontmatter; name == directory name, lowercase
  letters/digits/single hyphens, <= 64 chars; description 1..1024 chars; body <= 500 lines.
- Portability: only relative links, resolving inside the skill directory; no absolute
  machine paths; no host-specific shell injection or tool grants in the portable core.
- Traceability: every principle id a variant lists exists in docs/skill/principles.md.
- Leakage: no 8-word run of an eval case (visible or private text) appears in a variant.
"""

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ROOT / "skill-variants"
PRINCIPLES = ROOT / "docs/skill/principles.md"
# Case text a skill must not copy: the skill eval, plus the hygiene eval's cases and references.
CASES = (
    ROOT / "evaluation/skill_eval/cases",
    ROOT / "evaluation/hygiene/cases",
    ROOT / "evaluation/hygiene/references",
)
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata"}
NON_PORTABLE = [
    (re.compile(r"[A-Za-z]:\\\\?[A-Za-z]"), "absolute Windows path"),
    (re.compile(r"(?<![\w.])(/Users/|/home/|~/)"), "absolute or home-relative path"),
    (re.compile(r"!`"), "host-specific dynamic shell injection"),
    (re.compile(r"^allowed-tools\s*:", re.M), "host-specific tool grant"),
]
SHINGLE = 8


def frontmatter(text: str) -> tuple[dict[str, str], str, list[str]]:
    problems: list[str] = []
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", text, re.S)
    if not match:
        return {}, text, ["missing YAML frontmatter delimited by ---"]
    fields: dict[str, str] = {}
    key = None
    for line in match[1].splitlines():
        if re.match(r"^[A-Za-z_-]+\s*:", line):
            key, _, value = line.partition(":")
            key = key.strip()
            fields[key] = value.strip()
        elif key and line.startswith((" ", "\t")):
            fields[key] = (fields[key] + " " + line.strip()).strip()
        elif line.strip():
            problems.append(f"unparseable frontmatter line: {line!r}")
    for key, value in fields.items():
        if value[:1] in "\"'" and value[-1:] == value[:1]:
            fields[key] = value[1:-1]
        if value in (">", "|", ">-", "|-"):
            problems.append(f"{key}: use a plain or quoted single-line value")
    return fields, match[2], problems


def lint_skill(directory: Path) -> list[str]:
    problems: list[str] = []
    skill = directory / "SKILL.md"
    if not skill.is_file():
        return [f"{directory}: missing SKILL.md"]
    text = skill.read_text(encoding="utf-8")
    fields, body, problems = frontmatter(text)
    name = fields.get("name", "")
    if not NAME.match(name) or len(name) > 64:
        problems.append(f"name {name!r} must be lowercase letters/digits/single hyphens, <= 64 chars")
    if name != directory.name:
        problems.append(f"name {name!r} must equal directory name {directory.name!r}")
    description = fields.get("description", "")
    if not 1 <= len(description) <= 1024:
        problems.append(f"description must be 1..1024 characters (has {len(description)})")
    unknown = set(fields) - ALLOWED_KEYS
    if unknown:
        problems.append(f"non-portable frontmatter keys: {sorted(unknown)}")
    if len(body.splitlines()) > 500:
        problems.append(f"body has {len(body.splitlines())} lines (max 500)")
    for path in sorted(p for p in directory.rglob("*") if p.is_file() and p.suffix == ".md"):
        content = path.read_text(encoding="utf-8")
        for pattern, label in NON_PORTABLE:
            if pattern.search(content):
                problems.append(f"{path.relative_to(directory).as_posix()}: {label}")
        for target in re.findall(r"\]\(([^)\s]+)\)", content):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            resolved = (path.parent / target.split("#")[0]).resolve()
            if not resolved.is_file() or directory.resolve() not in resolved.parents:
                problems.append(f"{path.relative_to(directory).as_posix()}: link {target} must resolve inside the skill")
    return [f"{directory.parent.name}/{directory.name}: {p}" for p in problems]


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def case_shingles() -> set[tuple[str, ...]]:
    shingles: set[tuple[str, ...]] = set()
    for path in (p for cases in CASES for p in cases.rglob("*")):
        if path.is_file() and path.suffix in (".md", ".py", ".json"):
            words = _words(path.read_text(encoding="utf-8"))
            shingles.update(tuple(words[i:i + SHINGLE]) for i in range(len(words) - SHINGLE + 1))
    return shingles


def leaked(directory: Path, shingles: set[tuple[str, ...]]) -> list[str]:
    hits = []
    for path in directory.rglob("*.md"):
        words = _words(path.read_text(encoding="utf-8"))
        for i in range(len(words) - SHINGLE + 1):
            if tuple(words[i:i + SHINGLE]) in shingles:
                hits.append(f"{path.relative_to(directory).as_posix()}: shares eval case text near \"{' '.join(words[i:i + SHINGLE])}\"")
                break
    return hits


def principle_ids() -> set[str]:
    if not PRINCIPLES.is_file():
        return set()
    return set(re.findall(r"^#{2,4} (P-\d+)\b", PRINCIPLES.read_text(encoding="utf-8"), re.M))


def lint_registry() -> list[str]:
    registry = json.loads((VARIANTS / "variants.json").read_text(encoding="utf-8"))
    known = principle_ids()
    shingles = case_shingles()
    problems: list[str] = []
    seen = set()
    for variant in registry["variants"]:
        vid = variant["id"]
        if vid in seen:
            problems.append(f"{vid}: duplicate variant id")
        seen.add(vid)
        for field in ("hypothesis", "axes", "principles"):
            if field not in variant:
                problems.append(f"{vid}: missing {field}")
        missing = [p for p in variant.get("principles", []) if p not in known]
        if missing:
            problems.append(f"{vid}: principle ids not in docs/skill/principles.md: {missing}")
        if variant.get("control"):
            continue
        directory = VARIANTS / vid / "code-comments"
        problems += lint_skill(directory)
        problems += [f"{vid}: {hit}" for hit in leaked(directory, shingles)]
        if directory.is_dir():
            mentioned = set(re.findall(r"\bP-\d+\b", "".join(p.read_text(encoding="utf-8") for p in directory.rglob("*.md"))))
            stray = sorted(mentioned - known)
            if stray:
                problems.append(f"{vid}: skill text cites unknown principle ids {stray}")
    for directory in VARIANTS.iterdir():
        if directory.is_dir() and directory.name not in seen:
            problems.append(f"{directory.name}: variant directory not registered in variants.json")
    return problems


def main(argv: list[str]) -> int:
    if argv:
        shingles = case_shingles()
        problems = [p for d in argv for p in lint_skill(Path(d).resolve()) + leaked(Path(d).resolve(), shingles)]
    else:
        problems = lint_registry()
    for problem in problems:
        print(problem)
    print(f"{len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
