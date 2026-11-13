"""The tournament's arms: the controls, the default Junior-dev arm, and the factors screened.

Beating NoReview alone proves nothing (research L7, L12), so every Junior variant is read
against SelfReview (same budget, no junior), JuniorPrompt (the one-line instruction alone),
Critic (a reviewer instead of a questioner) and JuniorFull (a junior that also sees the brief).
See docs/junior-dev/design.md, "Arms".
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

REVIEWS = {"none", "self", "prompt", "critic", "junior", "junior_full", "simplify"}
MODELS = {"haiku", "sonnet", "opus"}


@dataclass(frozen=True)
class Arm:
    name: str
    review: str
    junior_model: str = "sonnet"
    rounds: int = 6
    batch: str = "3-8"
    teachback: str = "fresh"          # none | same | fresh
    teachback_form: str = "scenario"  # scenario (the shipped prompt) | free
    procedure: str = "trace"          # trace (the shipped prompt) | free
    self_passes: int = 3              # SelfReview's revision passes, matched to Junior's mean rounds after the pilot
    final_simplify: bool = True       # skill step 7 (climb iteration 2): one simplify pass after the loop
    skill_variant: str = ""           # a SKILL.md variant file to run instead of the shipped one (climb screening)
    # end: step 7 after the teach-back | before_teachback: rewrite (step 6, prompts/author_rewrite.md), then the
    # teach-back checks it. A simplify-only arm runs no loop; there the setting only picks the rewrite prompt.
    simplify_at: str = "end"

    def __post_init__(self):
        if self.review not in REVIEWS:
            raise ValueError(f"{self.name}: unknown review {self.review!r}")
        if self.simplify_at not in {"end", "before_teachback"}:
            raise ValueError(f"{self.name}: unknown simplify point {self.simplify_at!r}")
        if self.junior_model not in MODELS:
            raise ValueError(f"{self.name}: unknown junior model {self.junior_model!r}")
        if self.teachback not in {"none", "same", "fresh"} or self.teachback_form not in {"scenario", "free"}:
            raise ValueError(f"{self.name}: bad teach-back setting")
        if self.procedure not in {"trace", "free"} or self.rounds < 1 or self.self_passes < 1:
            raise ValueError(f"{self.name}: bad procedure or rounds")
        low, _, high = self.batch.partition("-")
        if not (low.isdigit() and high.isdigit() and 0 < int(low) <= int(high)):
            raise ValueError(f"{self.name}: batch must look like '3-8'")

    def to_dict(self) -> dict:
        return asdict(self)


CONTROLS = (
    Arm(name="no-review", review="none"),
    Arm(name="self-review", review="self"),
    Arm(name="junior-prompt", review="prompt"),
    Arm(name="critic", review="critic", rounds=3),
    Arm(name="junior-full", review="junior_full"),
)
DEFAULT_JUNIOR = Arm(name="junior", review="junior")


def skill_rev(prompts: dict) -> str:
    """A short hash of the shipped text the tournament runs (skill, junior and teach-back prompts)."""
    blob = json.dumps({k: prompts[k] for k in ("skill", "junior", "teachback")}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:10]
