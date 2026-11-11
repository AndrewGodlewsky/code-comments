"""Shared eval harness for the incubator skills.

Every incubator skill uses the same layout, modelled on the hygiene eval
(``evaluation/hygiene/``):

    incubator/<skill>/skill/<skill>/SKILL.md      the installable skill (plus any scripts/)
    incubator/<skill>/eval/arms.json              {"reminder": "<one sentence>"}
    incubator/<skill>/eval/cases/<case>/          prompt.md, case.yaml, graders/NN-*.md, files/, place-files.sh
    incubator/<skill>/eval/references/<case>/     a hand-written good result (RESPONSE.md if the reply is graded)
    incubator/<skill>/eval/grade.py               CHECKS = {case: [check, ...]}, one check per grader file
    incubator/<skill>/eval/iterations/<name>/     run directories, grades and the benchmark

Commands:

    python incubator/harness.py self-test [SKILL ...]     references pass every check; inputs fail one
    python incubator/harness.py lint [SKILL ...]          skill format, portability, no copied case text
    python incubator/harness.py prepare SKILL --iteration NAME [--arms ...] [--runs N] [--cases ...] [--fresh]
                                        [--split all|train|held-out] [--first-run K]
    python incubator/harness.py grade SKILL --iteration NAME [--force]
    python incubator/harness.py summary SKILL NAME [NAME ...]
    python incubator/harness.py verify-reads SKILL --iteration NAME TRANSCRIPT_DIR [...]

``prepare`` copies the skill into the iteration (``skill-snapshot/``) so later edits do
not change what a run read, copies each case's ``files/`` into
``<case>/<arm>/run-K/outputs/``, and writes ``runs.json``: one entry per run, with the
exact prompt to give the agent that does the task. Arms: ``with_skill`` (read the
snapshot of this skill first), ``shipped_skill`` (read a snapshot of the shipped
code-comments skill first: does the new skill add anything it does not?), ``reminder``
(no skill; the request ends with the sentence in ``arms.json``) and ``without_skill``.

Each grader file's frontmatter may set ``focus``: ``core`` (the default), ``preservation``,
``restraint`` or ``reply``. The benchmark reports each focus separately, so a reply checked
by keyword does not hide inside the headline.

``grade`` writes each run's ``grading.json``, ``changes.diff`` and a copy of its reply
(``RESPONSE.md``), then ``benchmark.json`` and ``benchmark.md`` for the iteration. It
needs every listed run's ``outputs/``, which is gitignored, so it refuses on a clone. It
also refuses, unless ``--force``, when the case's ``files/`` or hidden tests differ from
the fingerprint ``prepare`` stored in ``runs.json``, or when ``grade.py``, ``gradelib.py``
or a grader file differs from the fingerprint in an existing ``benchmark.json``. A run
directory may hold ``overrides.json`` ({grader text: {passed, evidence}}) to record a
ruling on a heuristic check; the ruling and the check's own result both stay in the
evidence.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import importlib.util
import json
import re
import shutil
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import gradelib  # noqa: E402

ARMS = ("with_skill", "shipped_skill", "reminder", "without_skill")
SKILL_ARMS = ("with_skill", "shipped_skill")
# The shipped hygiene skill. Its arm asks whether the new skill adds anything the
# existing one does not already produce.
SHIPPED = ROOT / "plugins" / "code-comments" / "skills" / "code-comments"


# ------------------------------------------------------------------ discovery


def skills() -> list[str]:
    return sorted(p.name for p in HERE.iterdir() if (p / "eval" / "grade.py").is_file())


def skill_dir(skill: str) -> Path:
    path = HERE / skill / "skill" / skill
    if not (path / "SKILL.md").is_file():
        raise SystemExit(f"{skill}: no SKILL.md at {path}")
    return path


def eval_dir(skill: str) -> Path:
    return HERE / skill / "eval"


def load_checks(skill: str) -> dict:
    path = eval_dir(skill) / "grade.py"
    spec = importlib.util.spec_from_file_location(f"incubator_{skill.replace('-', '_')}_grade", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.CHECKS


def case_names(skill: str, split: str = "all") -> list[str]:
    """Case names, optionally only the training cases or only the held-out ones
    (``held_out: true`` in case.yaml)."""
    names = sorted(p.name for p in (eval_dir(skill) / "cases").iterdir() if p.is_dir())
    if split == "all":
        return names
    held = {n for n in names if is_held_out(skill, n)}
    return [n for n in names if (n in held) == (split == "held-out")]


def is_held_out(skill: str, case: str) -> bool:
    """``held_out: true`` (or yes) in case.yaml. Any other value than true, yes, false or
    no stops, so a typo cannot move a held-out case into training."""
    path = eval_dir(skill) / "cases" / case / "case.yaml"
    if not path.is_file():
        return False
    match = re.search(r"^held_out:\s*([^\s#]+)", gradelib.text(path), re.M)
    if match is None:
        return False
    value = match.group(1).lower()
    if value in ("true", "yes", "false", "no"):
        return value in ("true", "yes")
    raise SystemExit(f"{path}: held_out must be true or false, got {match.group(1)!r}")


def _frontmatter_split(body: str, where: str = "") -> tuple[str, str]:
    body = body.lstrip("﻿")
    if body.startswith("---"):
        parts = body.split("---", 2)
        if len(parts) < 3:
            raise SystemExit(f"{where or 'a file'}: frontmatter opens with --- but never closes")
        return parts[1], parts[2]
    return "", body


FOCUSES = ("core", "preservation", "restraint", "reply")


def graders(skill: str, case: str) -> list[dict]:
    """Each grader file's statement and its ``focus`` (core, preservation, restraint or
    reply; default core). Reply checks read the message to the user, usually by keyword,
    so they are reported apart from the checks on the repository. A focus outside these
    four stops, so a typo cannot move a check into Core."""
    items = []
    for path in sorted((eval_dir(skill) / "cases" / case / "graders").glob("*.md")):
        head, body = _frontmatter_split(gradelib.text(path), str(path))
        match = re.search(r"^focus:\s*(\S+)", head, re.M)
        focus = "core" if match is None else match.group(1).lower()
        if focus not in FOCUSES:
            raise SystemExit(f"{path}: focus {match.group(1)!r} is not one of {FOCUSES}")
        items.append({"text": body.strip(), "focus": focus})
    return items


def statements(skill: str, case: str) -> list[str]:
    return [g["text"] for g in graders(skill, case)]


def task(skill: str, case: str) -> str:
    path = eval_dir(skill) / "cases" / case / "prompt.md"
    return _frontmatter_split(gradelib.text(path), str(path))[1].strip()


# -------------------------------------------------------------------- grading


def load_overrides(skill: str, case: str, path: Path) -> tuple[dict, list[str]]:
    """Read one run's overrides.json. Return the rulings and a list of problems: keys that
    match no grader text in the case, and rulings whose ``passed`` is not a JSON boolean
    or whose ``evidence`` is not a string. A ruling whose grader was reworded would
    otherwise stop applying without notice."""
    try:
        data = json.loads(gradelib.text(path))
    except json.JSONDecodeError as error:
        return {}, [f"{path}: not valid JSON: {error}"]
    if not isinstance(data, dict):
        return {}, [f"{path}: not a JSON object"]
    texts = set(statements(skill, case))
    problems = []
    for key, ruling in data.items():
        if key not in texts:
            problems.append(f"{path}: ruling matches no grader text in {case}: {key[:80]!r}")
        if not isinstance(ruling, dict) or not isinstance(ruling.get("passed"), bool):
            problems.append(f"{path}: 'passed' must be a JSON true or false: {key[:80]!r}")
        elif not isinstance(ruling.get("evidence", ""), str):
            problems.append(f"{path}: 'evidence' must be a string: {key[:80]!r}")
    return data, problems


def grade(skill: str, out: Path, case: str, checks: dict, overrides: dict | None = None) -> dict:
    items, fns = graders(skill, case), checks[case]
    if len(items) != len(fns):
        raise SystemExit(f"{skill}/{case}: {len(items)} grader files but {len(fns)} checks")
    unknown = sorted(set(overrides or {}) - {item["text"] for item in items})
    if unknown:
        raise SystemExit(f"{skill}/{case}: rulings match no grader text: {[k[:80] for k in unknown]}")
    orig = eval_dir(skill) / "cases" / case / "files"
    expectations = []
    for item, check in zip(items, fns):
        text = item["text"]
        try:
            passed, evidence = check(out, orig)
        except Exception as error:  # a broken run must not stop the grading of the rest
            passed, evidence = False, f"check raised {type(error).__name__}: {error}"
        if overrides and text in overrides:
            ruling = overrides[text]
            if not isinstance(ruling.get("passed"), bool):
                raise SystemExit(f"{skill}/{case}: ruling 'passed' must be a JSON true or false: {text[:80]!r}")
            evidence = f"override: {ruling.get('evidence', '')} (check said {passed}: {evidence})"
            passed = ruling["passed"]
        expectations.append({"text": text, "focus": item["focus"], "passed": bool(passed), "evidence": evidence})
    n = sum(e["passed"] for e in expectations)
    total = len(expectations)
    return {"expectations": expectations,
            "summary": {"passed": n, "failed": total - n, "total": total,
                        "pass_rate": round(n / total, 4) if total else 0.0}}


def self_test(skill: str) -> list[str]:
    """References must pass every check; the untouched inputs must fail at least one.
    Every case's held_out value and every stored overrides.json must also be valid."""
    problems = []
    checks = load_checks(skill)
    cases = case_names(skill)
    if sorted(checks) != cases:
        problems.append(f"{skill}: cases {cases} but checks for {sorted(checks)}")
    iterations = eval_dir(skill) / "iterations"
    for path in sorted(iterations.rglob("overrides.json")) if iterations.is_dir() else []:
        case = path.relative_to(iterations).parts[1]
        if case not in cases:
            problems.append(f"{path}: case {case!r} is not a case of {skill}")
        else:
            problems += load_overrides(skill, case, path)[1]
    for case in cases:
        folder = eval_dir(skill) / "cases" / case
        try:
            is_held_out(skill, case)
        except SystemExit as error:
            problems.append(str(error))
        for needed in ("prompt.md", "case.yaml", "place-files.sh", "files", "graders"):
            if not (folder / needed).exists():
                problems.append(f"{skill}/{case}: missing {needed}")
        if case not in checks:
            continue
        if len(statements(skill, case)) != len(checks[case]):
            problems.append(f"{skill}/{case}: {len(statements(skill, case))} grader files but "
                            f"{len(checks[case])} checks")
            continue
        reference = eval_dir(skill) / "references" / case
        if not reference.is_dir():
            problems.append(f"{skill}/{case}: no reference")
            continue
        for item in grade(skill, reference, case, checks)["expectations"]:
            if not item["passed"]:
                problems.append(f"{skill}/{case}: reference fails {item['text']!r}: {item['evidence']}")
        if grade(skill, folder / "files", case, checks)["summary"]["failed"] == 0:
            problems.append(f"{skill}/{case}: the unchanged input passes every check")
    return problems


# ----------------------------------------------------------------------- lint


def lint(skill: str) -> list[str]:
    sys.path.insert(0, str(ROOT / "scripts"))
    import lint_skills  # noqa: E402  (the repository's own skill linter)

    directory = skill_dir(skill)
    problems = lint_skills.lint_skill(directory)
    shingles = lint_skills.case_shingles()
    for source in (eval_dir(s) / part for s in skills() for part in ("cases", "references")):
        for path in source.rglob("*"):
            if path.is_file() and path.suffix in (".md", ".py", ".json", ".ts", ".js"):
                words = lint_skills._words(gradelib.text(path))
                n = lint_skills.SHINGLE
                shingles.update(tuple(words[i:i + n]) for i in range(len(words) - n + 1))
    problems += [f"{skill}: {hit}" for hit in lint_skills.leaked(directory, shingles)]
    n = lint_skills.SHINGLE
    for script in sorted(p for p in directory.rglob("*.py") if "__pycache__" not in p.parts):
        rel = script.relative_to(directory).as_posix()
        source = gradelib.text(script)
        try:
            compile(source, str(script), "exec")
            tree = ast.parse(source)
        except SyntaxError as error:
            problems.append(f"{skill}: {rel} does not compile: {error}")
            continue
        # A skill-arm agent may read its scripts too. Check their comments, docstrings and
        # string literals for copied case text, but not their code, so that a shared code
        # idiom does not count as a copy.
        parts = gradelib.prose(script) + [node.value for node in ast.walk(tree)
                                          if isinstance(node, ast.Constant) and isinstance(node.value, str)]
        words = lint_skills._words("\n".join(parts))
        hit = next((words[i:i + n] for i in range(len(words) - n + 1) if tuple(words[i:i + n]) in shingles), None)
        if hit:
            problems.append(f"{skill}: {rel}: shares eval case text near \"{' '.join(hit)}\"")
    return problems


# -------------------------------------------------------------------- running


def subject_prompt(outputs: Path, request: str, arm: str, skill_md: Path, reminder: str) -> str:
    parts = [f"You are working in the repository at {outputs.as_posix()}"]
    exception = ""
    if arm in SKILL_ARMS:
        parts.append(f"Your first action must be to read {skill_md.as_posix()} in full. Then follow it.")
        exception = (", with one exception: reading the skill folder named above, and running any script "
                     "it tells you to run from that folder, is required and allowed even though it is "
                     "outside the repository")
    if arm == "reminder":
        request = f"{request}\n\n{reminder}"
    parts.append(f"The user's request:\n{request}")
    parts.append("This is a self-contained exercise. Work only inside that repository directory, using "
                 f"absolute paths. Do not read or change anything outside it{exception}, and do not use "
                 "git, GitHub or any task tracking. When finished, write the message you would send the "
                 "user to RESPONSE.md in that repository directory.")
    return "\n\n".join(parts)


def _skill_files(folder: Path) -> set[str]:
    """A skill folder's files, leaving out the bytecode a run may write when it runs a
    script from the snapshot."""
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def _snapshot(source: Path, iteration: Path) -> Path:
    target = iteration / "skill-snapshot" / source.name
    if target.exists():
        rels = _skill_files(source)
        same = rels == _skill_files(target) and all(
            gradelib.text(target / rel) == gradelib.text(source / rel) for rel in rels)
        if not same:
            raise SystemExit(f"{target} differs from the current skill; use a new iteration name")
        return target
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
    return target


def _hash_files(paths: dict[str, Path]) -> str:
    """sha256 over (name, bytes) pairs in name order. Line endings are normalised, so a
    checkout that turns LF into CRLF gives the same value."""
    digest = hashlib.sha256()
    for name in sorted(paths):
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(paths[name].read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return digest.hexdigest()


def _tree(folder: Path, prefix: str) -> dict[str, Path]:
    if not folder.is_dir():
        return {}
    return {f"{prefix}/{p.relative_to(folder).as_posix()}": p for p in folder.rglob("*")
            if p.is_file() and not any(part in gradelib.SKIP_DIRS for part in p.relative_to(folder).parts)}


def inputs_fingerprint(skill: str, case: str) -> str:
    """What a run starts from and is compared with: the case's files/ (copied into
    outputs/ and diffed against) and its hidden tests."""
    return _hash_files({**_tree(eval_dir(skill) / "cases" / case / "files", "files"),
                        **_tree(eval_dir(skill) / "hidden" / case, "hidden")})


def check_files(skill: str, cases: list[str]) -> dict[str, str]:
    """sha256 of each file that decides a grade: grade.py, gradelib.py and the graders of
    the given cases."""
    paths = {"gradelib.py": Path(gradelib.__file__), "eval/grade.py": eval_dir(skill) / "grade.py"}
    for case in cases:
        paths.update(_tree(eval_dir(skill) / "cases" / case / "graders", f"eval/cases/{case}/graders"))
    return {name: _hash_files({name: path}) for name, path in sorted(paths.items())}


def prepare(skill: str, iteration_name: str, arms: list[str], n_runs: int, cases: list[str] | None,
            fresh: bool, first_run: int = 1, split: str = "all") -> list[dict]:
    iteration = eval_dir(skill) / "iterations" / iteration_name
    iteration.mkdir(parents=True, exist_ok=True)
    reminder = json.loads(gradelib.text(eval_dir(skill) / "arms.json"))["reminder"]
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        raise SystemExit(f"unknown arms {unknown}; choose from {list(ARMS)}")
    skill_md = {}
    if "with_skill" in arms:
        skill_md["with_skill"] = (_snapshot(skill_dir(skill), iteration) / "SKILL.md").resolve()
    if "shipped_skill" in arms:
        skill_md["shipped_skill"] = (_snapshot(SHIPPED, iteration) / "SKILL.md").resolve()
    entries = []
    for case in cases or case_names(skill, split):
        source = eval_dir(skill) / "cases" / case / "files"
        (iteration / case).mkdir(exist_ok=True)
        meta = {"eval_name": case, "prompt": task(skill, case), "assertions": statements(skill, case)}
        (iteration / case / "eval_metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8", newline="\n")
        fingerprint = inputs_fingerprint(skill, case)
        for arm in arms:
            for k in range(first_run, first_run + n_runs):
                run = iteration / case / arm / f"run-{k}"
                outputs = run / "outputs"
                if outputs.exists():
                    if not fresh:
                        raise SystemExit(f"{outputs} exists; pass --fresh to replace it")
                    shutil.rmtree(run)
                shutil.copytree(source, outputs)
                prompt = subject_prompt(outputs.resolve(), task(skill, case), arm,
                                        skill_md.get(arm, Path()), reminder)
                (run / "prompt.txt").write_text(prompt + "\n", encoding="utf-8", newline="\n")
                entries.append({"id": f"{skill}/{iteration_name}/{case}/{arm}/run-{k}", "skill": skill,
                                "iteration": iteration_name, "case": case, "arm": arm, "run": k,
                                "outputs": outputs.resolve().as_posix(), "prompt": prompt,
                                "inputs_fingerprint": fingerprint})
    index = iteration / "runs.json"
    existing = json.loads(gradelib.text(index)) if index.is_file() else []
    keep = [e for e in existing if e["id"] not in {x["id"] for x in entries}]
    index.write_text(json.dumps(keep + entries, indent=2) + "\n", encoding="utf-8", newline="\n")
    return entries


def _diff(orig: Path, out: Path) -> str:
    rels = sorted({p.relative_to(orig).as_posix() for p in gradelib.files(orig, None)} |
                  {p.relative_to(out).as_posix() for p in gradelib.files(out, None)})
    chunks = []
    for rel in rels:
        a = gradelib.text(orig / rel).splitlines(keepends=True) if (orig / rel).is_file() else []
        b = gradelib.text(out / rel).splitlines(keepends=True) if (out / rel).is_file() else []
        if a != b:
            chunks += difflib.unified_diff(a, b, f"a/{rel}", f"b/{rel}")
    return "".join(line if line.endswith("\n") else line + "\n" for line in chunks)


def iteration_runs(iteration: Path):
    for case_dir in sorted(p for p in iteration.iterdir() if p.is_dir() and p.name != "skill-snapshot"):
        for arm_dir in sorted(p for p in case_dir.iterdir() if p.is_dir()):
            for run in sorted(arm_dir.glob("run-*"), key=lambda p: int(p.name.split("-")[1])):
                if (run / "outputs").is_dir():
                    yield case_dir.name, arm_dir.name, run


def _refusals(skill: str, iteration: Path) -> tuple[list[str], list[str], dict]:
    """Why this iteration must not be graded now: (hard stops, stops --force lifts, the
    current fingerprints). Nothing is written until both lists are empty."""
    index = iteration / "runs.json"
    if not index.is_file():
        return [f"{index} is missing; nothing records which runs this iteration holds"], [], {}
    entries = json.loads(gradelib.text(index))
    hard, soft = [], []
    missing = [e["id"] for e in entries
               if not (iteration / e["case"] / e["arm"] / f"run-{e['run']}" / "outputs").is_dir()]
    if missing:
        hard.append(f"{len(missing)} of {len(entries)} listed runs have no outputs/ folder, for example "
                    f"{missing[:3]}. outputs/ is gitignored and exists only where the runs were made, "
                    "so a clone cannot regrade; grading now would replace the recorded results.")
    if not entries:
        hard.append(f"{index} lists no runs")
    cases = sorted({e["case"] for e in entries})
    inputs = {case: inputs_fingerprint(skill, case) for case in cases}
    stale = sorted({e["case"] for e in entries if e.get("inputs_fingerprint") != inputs[e["case"]]})
    if stale:
        soft.append(f"the files/ or hidden tests of {stale} differ from those the runs started from (or "
                    "runs.json records no fingerprint), so the diff and checks would compare against "
                    "other files")
    current = {"checks": check_files(skill, cases), "inputs": inputs}
    bench = iteration / "benchmark.json"
    if bench.is_file():
        before = json.loads(gradelib.text(bench)).get("fingerprints", {}).get("checks")
        if before != current["checks"]:
            changed = sorted(k for k in set(before or {}) | set(current["checks"])
                             if (before or {}).get(k) != current["checks"].get(k))
            soft.append("benchmark.json was graded with other checks"
                        + (f" (changed: {changed})" if before else " (it records no fingerprint)"))
    return hard, soft, current


def grade_iteration(skill: str, iteration_name: str, force: bool = False) -> dict:
    """Grade every run listed in runs.json. Stops, writing nothing, when a listed run has
    no outputs/, and, unless force, when the case inputs or the checks differ from those
    the iteration was prepared or last graded with. A forced grade keeps the previous
    fingerprints in benchmark.json beside the new ones."""
    iteration = eval_dir(skill) / "iterations" / iteration_name
    hard, soft, fingerprints = _refusals(skill, iteration)
    if hard or (soft and not force):
        raise SystemExit(f"{skill}/{iteration_name}: not graded:\n- " + "\n- ".join(hard + soft)
                         + ("" if hard else "\nPass --force to grade anyway; the old fingerprints are kept."))
    checks = load_checks(skill)
    runs = list(iteration_runs(iteration))
    rulings, problems = {}, []
    for case in sorted({case for case, _, _ in runs}):
        if case not in checks:
            problems.append(f"{case}: grade.py has no checks for it")
        elif len(statements(skill, case)) != len(checks[case]):
            problems.append(f"{case}: {len(statements(skill, case))} grader files but {len(checks[case])} checks")
    for case, arm, run in runs:
        if (run / "overrides.json").is_file() and case in checks:
            rulings[run], found = load_overrides(skill, case, run / "overrides.json")
            problems += found
    if problems:
        raise SystemExit(f"{skill}/{iteration_name}: not graded:\n- " + "\n- ".join(problems))
    if soft:
        print(f"{skill}/{iteration_name}: graded with --force:\n- " + "\n- ".join(soft), file=sys.stderr)
    rows = []
    for case, arm, run in runs:
        out = run / "outputs"
        result = grade(skill, out, case, checks, rulings.get(run))
        result["replied"] = (out / "RESPONSE.md").is_file()
        (run / "grading.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
        (run / "changes.diff").write_text(_diff(eval_dir(skill) / "cases" / case / "files", out), encoding="utf-8", newline="\n")
        if result["replied"]:
            shutil.copyfile(out / "RESPONSE.md", run / "RESPONSE.md")
        by_focus = {f: [sum(e["passed"] for e in result["expectations"] if e["focus"] == f),
                        sum(1 for e in result["expectations"] if e["focus"] == f)] for f in FOCUSES}
        rows.append({"case": case, "arm": arm, "run": run.name, **result["summary"], "replied": result["replied"],
                     "by_focus": by_focus,
                     "failed_checks": [e["text"] for e in result["expectations"] if not e["passed"]]})
    benchmark = _benchmark(skill, iteration_name, rows)
    benchmark["fingerprints"] = fingerprints
    previous = iteration / "benchmark.json"
    old = json.loads(gradelib.text(previous)) if previous.is_file() else {}
    if soft:
        benchmark["forced"] = soft
        if previous.is_file():
            benchmark["previous_fingerprints"] = old.get("fingerprints")
    else:  # a plain regrade keeps the record of an earlier forced one
        benchmark.update({k: old[k] for k in ("forced", "previous_fingerprints") if k in old})
    (iteration / "benchmark.json").write_text(json.dumps(benchmark, indent=2) + "\n", encoding="utf-8", newline="\n")
    (iteration / "benchmark.md").write_text(_benchmark_md(benchmark), encoding="utf-8", newline="\n")
    return benchmark


def _benchmark(skill: str, iteration_name: str, rows: list[dict]) -> dict:
    arms = [a for a in ARMS if any(r["arm"] == a for r in rows)] + \
        sorted({r["arm"] for r in rows} - set(ARMS))
    by_arm = {}
    for arm in arms:
        rates = [r["pass_rate"] for r in rows if r["arm"] == arm]
        by_arm[arm] = {"runs": len(rates), "mean_pass_rate": round(statistics.mean(rates), 4) if rates else None,
                       "checks_passed": sum(r["passed"] for r in rows if r["arm"] == arm),
                       "checks_total": sum(r["total"] for r in rows if r["arm"] == arm),
                       "no_reply": sum(not r["replied"] for r in rows if r["arm"] == arm),
                       "by_focus": {f: [sum(r["by_focus"][f][0] for r in rows if r["arm"] == arm),
                                        sum(r["by_focus"][f][1] for r in rows if r["arm"] == arm)]
                                    for f in FOCUSES}}
    cases = sorted({r["case"] for r in rows})
    per_case = {case: {arm: [f"{r['passed']}/{r['total']}" for r in rows if r["case"] == case and r["arm"] == arm]
                       for arm in arms} for case in cases}
    per_check = {}
    for case in cases:
        for text in statements(skill, case):
            per_check[f"{case}: {text}"] = {
                arm: f"{sum(text not in r['failed_checks'] for r in rows if r['case'] == case and r['arm'] == arm)}"
                     f"/{sum(1 for r in rows if r['case'] == case and r['arm'] == arm)}"
                for arm in arms}
    return {"skill": skill, "iteration": iteration_name, "arms": by_arm, "per_case": per_case,
            "per_check": per_check, "runs": rows}


def _benchmark_md(b: dict) -> str:
    arms = list(b["arms"])
    lines = [f"# {b['skill']}: {b['iteration']}", "", "Pass rate is the mean of each run's share of checks passed.", "",
             "Core, preservation, restraint and reply are the checks passed with that `focus`, summed over runs. "
             "Reply checks read the message to the user, mostly by keyword.", "",
             "| Arm | Runs | Mean pass rate | Checks passed | Core | Preservation | Restraint | Reply | No reply |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for arm, s in b["arms"].items():
        rate = "n/a" if s["mean_pass_rate"] is None else f"{100 * s['mean_pass_rate']:.1f}%"
        focus = " | ".join(f"{p}/{t}" if t else "-" for p, t in (s["by_focus"][f] for f in FOCUSES))
        lines.append(f"| {arm} | {s['runs']} | {rate} | {s['checks_passed']}/{s['checks_total']} | {focus} "
                     f"| {s['no_reply']} |")
    lines += ["", "## Per case (checks passed per run)", "", "| Case | " + " | ".join(arms) + " |",
              "| --- |" + " --- |" * len(arms)]
    for case, cells in b["per_case"].items():
        lines.append(f"| `{case}` | " + " | ".join(", ".join(cells[a]) or "-" for a in arms) + " |")
    lines += ["", "## Per check (runs passing)", "", "| Check | " + " | ".join(arms) + " |",
              "| --- |" + " --- |" * len(arms)]
    for check, cells in b["per_check"].items():
        lines.append(f"| {check} | " + " | ".join(cells[a] for a in arms) + " |")
    return "\n".join(lines) + "\n"


def summary(skill: str, iteration_names: list[str]) -> str:
    lines = ["| Iteration | Arm | Runs | Mean pass rate | Checks passed |", "| --- | --- | --- | --- | --- |"]
    for name in iteration_names:
        path = eval_dir(skill) / "iterations" / name / "benchmark.json"
        b = json.loads(gradelib.text(path))
        for arm, s in b["arms"].items():
            rate = "n/a" if s["mean_pass_rate"] is None else f"{100 * s['mean_pass_rate']:.1f}%"
            lines.append(f"| {name} | {arm} | {s['runs']} | {rate} | {s['checks_passed']}/{s['checks_total']} |")
    return "\n".join(lines)


# ------------------------------------------------------------- read checking


def _norm(path: str) -> str:
    return path.replace("\\", "/").lower()


def verify_reads(skill: str, iteration_name: str, transcript_dirs: list[Path]) -> dict:
    """For every skill-arm run, find the agent transcript that did it and check that the
    agent read its own arm's snapshot SKILL.md before editing anything. A Read with a
    limit or offset still counts (an agent may read in chunks) but is listed in
    ``partial_reads``. Lines that are not JSON, such as the end of a transcript still
    being written, are counted, not fatal."""
    iteration = eval_dir(skill) / "iterations" / iteration_name
    entries = [e for e in json.loads(gradelib.text(iteration / "runs.json")) if e["arm"] in SKILL_ARMS]
    wanted = {_norm(e["outputs"]): e["id"] for e in entries}
    own = {}  # run id -> (the snapshot path its prompt named, that path below iterations/)
    for e in entries:
        named = re.search(r"Your first action must be to read (.+?) in full\.", e["prompt"])
        name = skill if e["arm"] == "with_skill" else SHIPPED.name
        own[e["id"]] = (_norm(named.group(1)) if named else None,
                        _norm(f"/iterations/{iteration_name}/skill-snapshot/{name}/SKILL.md"))
    found: dict[str, dict] = {}
    unparsable: dict[str, int] = {}
    for directory in transcript_dirs:
        for path in sorted(Path(directory).glob("agent-*.jsonl")):
            first, tools, seen, bad = None, [], set(), 0
            with path.open(encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        bad += 1
                        continue
                    message = event.get("message") if isinstance(event, dict) else None
                    if not isinstance(message, dict):
                        continue
                    content = message.get("content")
                    if first is None and event.get("type") == "user" and isinstance(content, str):
                        first = content
                    if isinstance(content, list):
                        # Transcripts also hold later copies of earlier messages, so count each call once.
                        for c in content:
                            if not isinstance(c, dict) or c.get("type") != "tool_use" \
                                    or (c.get("id") and c["id"] in seen):
                                continue
                            seen.add(c.get("id"))
                            tools.append(c)
            if bad:
                unparsable[path.name] = bad
            if not first:
                continue
            # The path runs to the end of its line, so a folder name with a space survives.
            match = re.search(r"You are working in the repository at ([^\n]+)", first.replace("\\", "/"))
            if not match or _norm(match.group(1).strip()) not in wanted:
                continue
            run_id = wanted[_norm(match.group(1).strip())]
            exact, suffix = own[run_id]
            read_at, partial = None, False
            for i, tool in enumerate(tools):
                inp = tool.get("input") if isinstance(tool.get("input"), dict) else {}
                target = _norm(str(inp.get("file_path", "")))
                if tool.get("name") == "Read" and (target == exact or target.endswith(suffix)):
                    read_at, partial = i, "limit" in inp or "offset" in inp
                    break
            edits = [i for i, t in enumerate(tools) if t.get("name") in ("Edit", "Write", "MultiEdit", "NotebookEdit")]
            read_first = read_at is not None and (not edits or read_at < edits[0])
            found[run_id] = {"transcript": path.name, "read_skill": read_at is not None,
                             "read_before_edit": read_first, "partial_read": partial,
                             "unparsable_lines": bad, "tool_calls": len(tools)}
    missing = sorted(set(wanted.values()) - set(found))
    return {"checked": len(found), "missing_transcripts": missing,
            "skipped_skill": sorted(r for r, v in found.items() if not v["read_before_edit"]),
            "partial_reads": sorted(r for r, v in found.items() if v["partial_read"]),
            "transcripts_with_unparsable_lines": unparsable, "runs": found}


# ----------------------------------------------------------------------- main


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("self-test"); p.add_argument("skills", nargs="*")
    p = sub.add_parser("lint"); p.add_argument("skills", nargs="*")
    p = sub.add_parser("prepare")
    p.add_argument("skill"); p.add_argument("--iteration", required=True)
    p.add_argument("--arms", default=",".join(ARMS)); p.add_argument("--runs", type=int, default=1)
    p.add_argument("--first-run", type=int, default=1)
    p.add_argument("--cases"); p.add_argument("--fresh", action="store_true")
    p.add_argument("--split", choices=("all", "train", "held-out"), default="all")
    p = sub.add_parser("grade"); p.add_argument("skill"); p.add_argument("--iteration", required=True)
    p.add_argument("--force", action="store_true",
                   help="grade although the case inputs or the checks changed since the runs were prepared or graded")
    p = sub.add_parser("summary"); p.add_argument("skill"); p.add_argument("iterations", nargs="+")
    p = sub.add_parser("verify-reads")
    p.add_argument("skill"); p.add_argument("--iteration", required=True); p.add_argument("transcripts", nargs="+")
    args = parser.parse_args(argv)

    if args.command in ("self-test", "lint"):
        problems = []
        for skill in args.skills or skills():
            problems += self_test(skill) if args.command == "self-test" else lint(skill)
        print("\n".join(problems) if problems else f"{args.command} ok")
        return 1 if problems else 0
    if args.command == "prepare":
        arms = [a for a in args.arms.split(",") if a]
        cases = args.cases.split(",") if args.cases else None
        entries = prepare(args.skill, args.iteration, arms, args.runs, cases, args.fresh, args.first_run,
                          args.split)
        print(json.dumps([{k: e[k] for k in ("id", "outputs")} for e in entries], indent=1))
        return 0
    if args.command == "grade":
        b = grade_iteration(args.skill, args.iteration, args.force)
        print(_benchmark_md(b))
        return 0
    if args.command == "summary":
        print(summary(args.skill, args.iterations))
        return 0
    if args.command == "verify-reads":
        print(json.dumps(verify_reads(args.skill, args.iteration, [Path(t) for t in args.transcripts]), indent=1))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
