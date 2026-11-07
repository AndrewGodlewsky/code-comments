"""Verify citations in the skill distillation: passage ids exist and quotes are verbatim.

python scripts/check_distillation.py [files...]   (default: docs/skill/distillation/*.md and docs/skill/principles.md)

A citation is a markdown link followed on the same line by a double-quoted quote:
  [planning-and-coding-012](../../research/.../passages.md#planning-and-coding-012) — supports — "quoted text" — evidence: ...
For a `passages.md#<id>` link, the quote must appear inside that passage's block.
For any other repository file, it must appear somewhere in that file. Whitespace,
curly quotes and dashes are normalized; "..." splits a quote into ordered fragments.
"""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[(?P<label>[^\]]+)\]\((?P<target>[^)\s]+)\)(?P<rest>[^\n]*)")
QUOTE = re.compile(r"[\"“](?P<quote>.+)[\"”]\s*(?:—|-|$)")
ANCHOR = re.compile(r'<a id="(?P<id>[^"]+)"></a>')
TRANSLATE = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "—": "-", "–": "-", "…": "..."})


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(TRANSLATE)).strip().lower()


def passage_blocks(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    marks = list(ANCHOR.finditer(text))
    return {
        mark["id"]: text[mark.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        for i, mark in enumerate(marks)
    }


def contains_in_order(haystack: str, quote: str) -> bool:
    position = 0
    for fragment in (part.strip() for part in normalize(quote).split("...")):
        if not fragment:
            continue
        found = haystack.find(fragment, position)
        if found < 0:
            return False
        position = found + len(fragment)
    return True


def check(files: list[Path]) -> tuple[int, list[str]]:
    cache: dict[Path, tuple[dict[str, str], str]] = {}
    problems, checked = [], 0
    for file in files:
        for number, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
            for link in LINK.finditer(line):
                target = link["target"]
                if target.startswith(("http://", "https://", "#")):
                    continue
                path_part, _, anchor = target.partition("#")
                path = (file.parent / path_part).resolve()
                where = f"{file.relative_to(ROOT).as_posix()}:{number}"
                quote_match = QUOTE.search(link["rest"])
                if not path.is_file():
                    problems.append(f"{where}: link target does not exist: {target}")
                    continue
                if path not in cache:
                    blocks = passage_blocks(path) if path.name == "passages.md" else {}
                    cache[path] = (blocks, normalize(path.read_text(encoding="utf-8")))
                blocks, whole = cache[path]
                if path.name == "passages.md" and anchor:
                    if anchor not in blocks:
                        problems.append(f"{where}: passage id not found: {anchor}")
                        continue
                    haystack = normalize(blocks[anchor])
                else:
                    haystack = whole
                if quote_match is None:
                    continue  # a plain link, not a quoted citation
                checked += 1
                if not contains_in_order(haystack, quote_match["quote"]):
                    problems.append(f"{where}: quote not found verbatim in {target}: \"{quote_match['quote'][:80]}\"")
    return checked, problems


def main(argv: list[str]) -> int:
    files = [Path(a).resolve() for a in argv] or sorted((ROOT / "docs/skill/distillation").glob("*.md"))
    principles = ROOT / "docs/skill/principles.md"
    if not argv and principles.is_file():
        files.append(principles)
    checked, problems = check(files)
    for problem in problems:
        print(problem)
    print(f"{checked} quoted citations checked in {len(files)} files; {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
