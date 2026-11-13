"""Build in-session Workflow scripts for the Junior-dev tournament (#52).

A Workflow script has no file access, so each batch file embeds what its runs need: the cases
(with the graders' keys, which no agent is shown), the arms, and the prompt text read from the
plugin itself (SKILL.md, junior-prompt.md, teachback-prompt.md) and from prompts/. The
tournament therefore always runs the text that ships. Run a batch with
Workflow({scriptPath: <file>}), then collect.py its output file.

    python -m evaluation.junior_dev.build validation   # or: pilot (see named_batch)
"""

from __future__ import annotations

import importlib.util
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import sys

from . import arms as arms_mod
from .cases import CASES, load

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SKILL_DIR = ROOT / "plugins" / "junior-dev" / "skills" / "junior-dev"
REFS = SKILL_DIR / "references"
PROMPTS = HERE / "prompts"
TEMPLATES = HERE / "templates"
DRYRUN = HERE / "tools" / "dryrun.mjs"
BUILT = HERE / "built"

MAX_RUNS = 60          # a workflow may start at most 1000 agents; a Junior run uses about 15
MAX_BYTES = 450_000    # inline scripts are capped near 512 KB
MODES = {"natural", "seeded-presentation", "seeded-implicit", "null", "padded"}
READERS = [
    {"name": "haiku-low", "model": "haiku", "effort": "low", "short": True},   # the hurried weak reader
    {"name": "sonnet", "model": "sonnet", "effort": None, "short": False},
]
JUNIOR_PROMPT_LINE = ("Write it so that a junior developer who is new to this stack, and has not seen this brief, "
                      "could follow it.")
BRIEF_HEADER = "# The request the author was given\n\n"
FILLER = ("\n\n## General considerations\n\nThis design follows common good practice. Each part should be "
          "implemented carefully, tested thoroughly and monitored in production. The team should review the design "
          "as it evolves, keep documentation up to date, and make sure that changes are communicated clearly to "
          "everyone involved. Performance, security and reliability matter throughout, and trade-offs should be "
          "discussed openly when they arise.\n")
PROCEDURE_START, PROCEDURE_END = "How to work through it:", "Each round, ask"
BATCH_MARK = "between 3 and 8 questions"
TB_SCENARIO = "- Follow one concrete request, event or user action from the first step to the last.\n"


def _junior_module():
    spec = importlib.util.spec_from_file_location("junior_dev_helper_build", ROOT / "plugins" / "junior-dev" / "scripts" / "junior.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_prompts() -> dict:
    prompts = {"junior": (REFS / "junior-prompt.md").read_text(encoding="utf-8"),
               "teachback": (REFS / "teachback-prompt.md").read_text(encoding="utf-8"),
               "skill": (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")}
    for path in sorted(PROMPTS.glob("*.md")):
        prompts[path.stem] = path.read_text(encoding="utf-8").strip()
    return prompts


def junior_prompt_for(arm: arms_mod.Arm, base: dict) -> str:
    text = base["junior"]
    if arm.procedure == "free":
        start, end = text.find(PROCEDURE_START), text.find(PROCEDURE_END)
        if start < 0 or end < start:
            raise ValueError("junior-prompt.md lost the procedure markers that the 'free' variant needs")
        text = text[:start] + text[end:]
    if arm.batch != "3-8":
        if BATCH_MARK not in text:
            raise ValueError(f"junior-prompt.md lost the batch marker {BATCH_MARK!r}")
        low, high = arm.batch.split("-")
        text = text.replace(BATCH_MARK, f"between {low} and {high} questions")
    return text


def teachback_prompt_for(arm: arms_mod.Arm, base: dict) -> str:
    text = base["teachback"]
    if arm.teachback_form == "free":
        if TB_SCENARIO not in text:
            raise ValueError("teachback-prompt.md lost the scenario bullet that the 'free' variant removes")
        text = text.replace(TB_SCENARIO, "")
    return text


def framing() -> dict:
    j = _junior_module()
    return {"artifact_header": j.ARTIFACT_HEADER, "transcript_header": j.TRANSCRIPT_HEADER, "ask": j.ASK_INSTRUCTION,
            "teachback_header": j.TEACHBACK_HEADER, "teachback_instruction": j.TEACHBACK_INSTRUCTION,
            "brief_header": BRIEF_HEADER}


def _case_payload(case, mode: str) -> dict:
    return {"id": case.id, "format": case.format, "brief": case.brief, "existing": case.existing,
            "quiz": [{"id": q["id"], "kind": q["kind"], "question": q["question"], "key": q["key"]} for q in case.quiz],
            "requirements": case.requirements, "undecided": case.undecided,
            "start": {k: v for k, v in {"seeded-presentation": case.seeded_presentation,
                                        "seeded-implicit": case.seeded_implicit, "null": case.reference,
                                        "padded": case.reference.rstrip() + FILLER}.items() if k == mode}}


def _render(data: dict, label: str) -> str:
    meta = ("export const meta = {\n  name: 'junior-dev-tournament',\n"
            "  description: 'Junior-dev tournament batch: authors write or revise plans per arm, readers answer the hidden quiz',\n"
            "  phases: [{ title: 'Runs' }],\n}\n")
    return (meta + "// batch: " + label + "\nconst DATA = " + json.dumps(data, ensure_ascii=False) + "\n\n"
            + (TEMPLATES / "render.js").read_text(encoding="utf-8") + "\n"
            + (TEMPLATES / "tournament.js").read_text(encoding="utf-8"))


def build_batch(case_ids: list[str], arm_list: list, authors: list[str], reps: int, mode: str, out_dir: Path,
                label: str, cases_root: Path = CASES, grader_models: tuple = ("sonnet",)) -> list[Path]:
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}")
    names = [a.name for a in arm_list]
    if len(set(names)) != len(names):
        raise ValueError("arm names must be unique")
    for a in arm_list:
        if mode != "natural" and a.review == "prompt":
            raise ValueError("JuniorPrompt changes the original request, so it runs in natural mode only")
    if "none" in authors and any(a.review != "none" for a in arm_list) or ("none" in authors and mode == "natural"):
        raise ValueError("author 'none' is only for NoReview runs on a given artifact")
    by_id = {c.id: c for c in load(root=cases_root)}
    missing = [cid for cid in case_ids if cid not in by_id]
    if missing:
        raise ValueError(f"unknown cases: {missing}")
    prompts = load_prompts()
    arm_cfg = {}
    for a in arm_list:
        cfg = a.to_dict()
        cfg["junior_text"] = junior_prompt_for(a, prompts)
        cfg["teachback_text"] = teachback_prompt_for(a, prompts)
        arm_cfg[a.name] = cfg
    j = _junior_module()
    runs = [{"run_id": f"{cid}__{a.name}__{author}__{mode}__r{rep}", "case": cid, "arm": a.name, "author": author,
             "rep": rep, "mode": mode}
            for cid, a, author, rep in itertools.product(case_ids, arm_list, authors, range(1, reps + 1))]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    common = {"label": label, "skill_rev": arms_mod.skill_rev(prompts), "prompts": prompts, "framing": framing(),
              "schemas": {"questions": j.QUESTIONS_SCHEMA, "teachback": j.TEACHBACK_SCHEMA}, "readers": READERS,
              "grader_models": list(grader_models), "max_teachbacks": j.MAX_TEACHBACKS,
              "junior_prompt_line": JUNIOR_PROMPT_LINE}

    def emit(chunk: list[dict], index: int) -> list[Path]:
        used = sorted({r["case"] for r in chunk})
        data = dict(common, label=f"{label}-{index:02d}", cases={cid: _case_payload(by_id[cid], mode) for cid in used},
                    arms={n: arm_cfg[n] for n in sorted({r["arm"] for r in chunk})}, runs=chunk)
        text = _render(data, data["label"])
        if len(text.encode("utf-8")) >= MAX_BYTES and len(chunk) > 1:
            half = len(chunk) // 2
            return emit(chunk[:half], index * 10 + 1) + emit(chunk[half:], index * 10 + 2)
        path = out_dir / f"{data['label']}.js"
        path.write_text(text, encoding="utf-8", newline="\n")
        return [path]

    files = []
    for k in range(0, len(runs), MAX_RUNS):
        files += emit(runs[k:k + MAX_RUNS], k // MAX_RUNS + 1)
    return files


def build_judge_batch(iteration_dir: Path, pairs: list[tuple[str, str]], out_dir: Path, label: str,
                      judge_model: str = "sonnet") -> list[Path]:
    """Blind pairwise clarity judgments for every (case, author, mode, rep) where both arms of a pair ran.

    Each pair is judged in both orders; the judge sees only the two final artifacts."""
    import re as _re
    iteration_dir = Path(iteration_dir)
    finals = {}
    for run_json in iteration_dir.rglob("run.json"):
        run = json.loads(run_json.read_text(encoding="utf-8"))
        text = (run_json.parent / "artifact-final.md").read_text(encoding="utf-8")
        if text.strip():
            finals[(run["case"], run["arm"], run["author"], run["mode"], run["rep"])] = text
    items = []
    for arm_a, arm_b in pairs:
        for (case, arm, author, mode, rep), doc_a in sorted(finals.items()):
            if arm != arm_a or (case, arm_b, author, mode, rep) not in finals:
                continue
            doc_b = finals[(case, arm_b, author, mode, rep)]
            words = lambda s: len(_re.findall(r"\w+", s))
            pair_id = f"{case}__{arm_a}__vs__{arm_b}__{author}__{mode}__r{rep}"
            base = {"pair_id": pair_id, "case": case, "author": author, "mode": mode, "rep": rep, "arm_a": arm_a, "arm_b": arm_b}
            items.append(dict(base, order="ab", doc_a=doc_a, doc_b=doc_b, words_a=words(doc_a), words_b=words(doc_b)))
            items.append(dict(base, order="ba", doc_a=doc_b, doc_b=doc_a, words_a=words(doc_b), words_b=words(doc_a)))
    meta = ("export const meta = {\n  name: 'junior-dev-judge',\n"
            "  description: 'Junior-dev blind pairwise clarity judge: which of two documents a newcomer understands faster',\n"
            "  phases: [{ title: 'Judge' }],\n}\n")
    prompt = load_prompts()["judge"]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for k in range(0, len(items), 2 * MAX_RUNS):
        chunk = items[k:k + 2 * MAX_RUNS]
        data = {"label": f"{label}-{k // (2 * MAX_RUNS) + 1:02d}", "prompt": prompt, "judge_model": judge_model, "pairs": chunk}
        path = out_dir / f"{data['label']}.js"
        path.write_text(meta + "const DATA = " + json.dumps(data, ensure_ascii=False) + "\n\n"
                        + (TEMPLATES / "judge.js").read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
        files.append(path)
    return files


def embedded_data(path: Path) -> dict:
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("const DATA = "):
            return json.loads(line[len("const DATA = "):])
    raise ValueError(f"{path}: no embedded DATA")


def _node() -> str:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node is required for the dry run")
    return node


def dry_run(path: Path) -> dict:
    """Execute a built batch with stub agents (no model calls); returns {result, prompts}."""
    done = subprocess.run([_node(), str(DRYRUN), str(path)], capture_output=True, text=True, encoding="utf-8", timeout=300)
    if done.returncode != 0:
        raise RuntimeError(f"dry run failed: {done.stderr[-2000:]}")
    return json.loads(done.stdout)


def js_render(kind: str, artifact: str, transcript: list[dict]) -> str:
    """Render a junior or teach-back message with templates/render.js, for comparison with junior.py."""
    payload = json.dumps({"kind": kind, "artifact": artifact, "transcript": transcript, "framing": framing(),
                          "render": str(TEMPLATES / "render.js")}, ensure_ascii=False)
    done = subprocess.run([_node(), str(DRYRUN), "--render"], input=payload, capture_output=True, text=True,
                          encoding="utf-8", timeout=60)
    if done.returncode != 0:
        raise RuntimeError(f"render failed: {done.stderr[-2000:]}")
    return json.loads(done.stdout)["text"]


PILOT_CASES = ["auth-01", "ms-01", "mig-02", "feat-01"]   # one simple, one complex, one diagram-state, one with files


def named_batch(name: str) -> list[Path]:
    """The batches the plan runs by name; each writes its files under built/<name>/."""
    out = BUILT / name
    if name.startswith("validation"):
        ids = [c.id for c in load() if c.split in ("dev", "heldout")]
        none = [arms_mod.CONTROLS[0]]
        files = []
        for mode, graders in (("null", ("sonnet", "opus")), ("seeded-implicit", ("sonnet", "opus")),
                              ("seeded-presentation", ("sonnet",)), ("padded", ("sonnet",))):
            files += build_batch(ids, none, ["none"], 1, mode, out, f"{name}-{mode}", grader_models=graders)
        return files
    if name == "pilot":
        pilot_arms = [arms_mod.CONTROLS[0], arms_mod.CONTROLS[1], arms_mod.CONTROLS[3], arms_mod.DEFAULT_JUNIOR]
        return build_batch(PILOT_CASES, pilot_arms, ["haiku", "sonnet"], 1, "natural", out, "pilot")
    raise ValueError(f"unknown batch {name!r}")


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    for path in named_batch(argv[0]):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
