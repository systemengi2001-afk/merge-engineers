"""Commercial-safety registry for external Mahjong AI references.

JONG AI uses public ideas and separately obtained outputs only where project policy
allows it.  This module is intentionally metadata/policy code: it does not import,
copy, or bundle external AI implementations, model weights, or proprietary reports.

The policy values are conservative engineering defaults, not legal advice.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

UsePolicy = Literal[
    "external_output_review_required",
    "blocked_without_permission",
    "concept_only",
]


@dataclass(frozen=True)
class AIReference:
    key: str
    name: str
    kind: str
    public_ideas: tuple[str, ...]
    license_or_terms: str
    commercial_training_policy: UsePolicy
    reason: str
    source_url: str

    def to_dict(self) -> dict:
        return asdict(self)


# Major, well-documented Riichi/Japanese-mahjong AI references.  The list is
# deliberately extensible; "major" is not claimed to mean literally exhaustive.
REFERENCES: dict[str, AIReference] = {
    "mortal": AIReference(
        key="mortal",
        name="Mortal",
        kind="deep-reinforcement-learning AI",
        public_ideas=(
            "deep reinforcement learning",
            "fast simulator + neural inference",
            "action-value / rank-value oriented review",
            "mjai-compatible external engine boundary",
        ),
        license_or_terms="AGPL-3.0-or-later code; model-weight distribution is separate",
        commercial_training_policy="external_output_review_required",
        reason=(
            "Do not bundle or copy Mortal code/weights into the commercial JONG core. "
            "Only separately produced teacher outputs may enter the distillation boundary, "
            "after provenance/terms review."
        ),
        source_url="https://github.com/Equim-chan/Mortal",
    ),
    "akochan": AIReference(
        key="akochan",
        name="Akochan",
        kind="search/expected-value Mahjong AI",
        public_ideas=(
            "explicit expected-value evaluation",
            "offense/defense decomposition",
            "draw / exhaustive-draw outcome modelling",
            "auditable hand-crafted search components",
        ),
        license_or_terms="custom terms; commercial use requires creator permission",
        commercial_training_policy="blocked_without_permission",
        reason="Commercial use/output reuse is not enabled by the published terms without permission.",
        source_url="https://github.com/critter-mj/akochan",
    ),
    "naga": AIReference(
        key="naga",
        name="NAGA",
        kind="proprietary neural Mahjong AI / review service",
        public_ideas=(
            "multiple policy/personality views",
            "candidate-action distribution for review",
            "discard/call/riichi review on one analysis surface",
            "disagreement as a useful review signal",
        ),
        license_or_terms="proprietary service terms",
        commercial_training_policy="concept_only",
        reason=(
            "NAGA's published service guidance prohibits using analysis results to develop "
            "competing products; JONG therefore must not ingest NAGA reports/scores as training data."
        ),
        source_url="https://naga.dmv.nico/naga_report/top/",
    ),
    "suphx": AIReference(
        key="suphx",
        name="Suphx",
        kind="research deep-reinforcement-learning AI",
        public_ideas=(
            "global reward prediction",
            "oracle guiding during training",
            "run-time policy adaptation",
            "self-play reinforcement learning",
        ),
        license_or_terms="published research; no JONG-bundled implementation/weights",
        commercial_training_policy="concept_only",
        reason="Use the published research concepts, not an unavailable/proprietary implementation.",
        source_url="https://www.microsoft.com/en-us/research/project/suphx-mastering-mahjong-with-deep-reinforcement-learning/",
    ),
    "kanachan": AIReference(
        key="kanachan",
        name="Kanachan",
        kind="Riichi Mahjong AI framework",
        public_ideas=(
            "tokenized end-to-end state representation",
            "transformer-scale representation learning",
            "curriculum fine-tuning across objectives",
            "annotation-vs-simulation consistency tests",
        ),
        license_or_terms="repository has no root license file observed during v6.4 review",
        commercial_training_policy="concept_only",
        reason="No explicit reusable license was observed; use architecture/testing ideas only.",
        source_url="https://github.com/Cryolite/kanachan",
    ),
    "bakuuchi": AIReference(
        key="bakuuchi",
        name="爆打 (Bakuuchi)",
        kind="historically notable strong Riichi AI",
        public_ideas=(
            "supervised policy learning from strong play",
            "opponent-danger estimation",
            "separate tactical prediction components",
        ),
        license_or_terms="research/reference only in JONG registry",
        commercial_training_policy="concept_only",
        reason="Historical reference; no external implementation or outputs are bundled by JONG.",
        source_url="https://arxiv.org/abs/1904.07491",
    ),
    "meowjong": AIReference(
        key="meowjong",
        name="Meowjong",
        kind="academic three-player Mahjong deep-RL AI",
        public_ideas=(
            "sanma-specific observable-state encoding",
            "separate discard/pon/kan/kita/riichi action heads",
            "supervised pretraining followed by self-play policy-gradient improvement",
        ),
        license_or_terms="published research/reference; implementation rights not assumed",
        commercial_training_policy="concept_only",
        reason="Use the published sanma architecture/training ideas without assuming code/model reuse rights.",
        source_url="https://arxiv.org/abs/2202.12847",
    ),
    "luckyj": AIReference(
        key="luckyj",
        name="LuckyJ",
        kind="strong self-play Mahjong AI",
        public_ideas=(
            "self-play policy improvement",
            "placement-aware table judgement",
            "re-evaluating push/fold as table conditions change",
        ),
        license_or_terms="public descriptions/reference; no JONG-bundled implementation/weights",
        commercial_training_policy="concept_only",
        reason="Use publicly described strategy concepts only unless a separately licensed interface is obtained.",
        source_url="https://honvl.github.io/LuckyJ/",
    ),
    "maka": AIReference(
        key="maka",
        name="MAKA",
        kind="proprietary Mahjong Soul review AI",
        public_ideas=("strong-policy replay review", "platform-specific calibration"),
        license_or_terms="proprietary service",
        commercial_training_policy="concept_only",
        reason="No model/code/output ingestion into JONG without explicit rights.",
        source_url="https://riichi.wiki/AI",
    ),
    "bigcoach": AIReference(
        key="bigcoach",
        name="BigCoach",
        kind="strong four-player/sanma review AI",
        public_ideas=("separate sanma calibration", "review-oriented action comparison"),
        license_or_terms="external service/reference",
        commercial_training_policy="concept_only",
        reason="Use public high-level concepts only; no external reports or weights are bundled.",
        source_url="https://riichi.wiki/AI",
    ),
}


def get_reference(key: str) -> AIReference:
    try:
        return REFERENCES[key.strip().lower()]
    except KeyError as exc:
        raise ValueError(f"unknown external AI reference: {key}") from exc


def assert_teacher_ingestion_allowed(source: str, *, commercial: bool = True) -> AIReference:
    """Validate whether an external source may enter JONG's teacher-data boundary.

    In commercial mode this is intentionally conservative.  Passing this check is
    a JONG engineering policy decision, not a legal warranty.
    """
    ref = get_reference(source)
    if not commercial:
        return ref
    if ref.commercial_training_policy != "external_output_review_required":
        raise PermissionError(
            f"{ref.name} is {ref.commercial_training_policy} for commercial teacher ingestion: {ref.reason}"
        )
    return ref


def reference_catalog() -> list[dict]:
    return [REFERENCES[k].to_dict() for k in sorted(REFERENCES)]


def reference_coverage() -> dict[str, dict]:
    """Map public ideas to JONG-owned implementations or explicit future work."""
    return {
        "mortal": {"status": "implemented", "jong_modules": ["mortal_distillation", "multi_teacher"]},
        "akochan": {"status": "implemented-independent", "jong_modules": ["ev", "defense_ev", "round_outcome_sim"]},
        "naga": {"status": "implemented-independent", "jong_modules": ["multi_teacher"], "note": "disagreement/consensus only; no NAGA output ingestion"},
        "suphx": {"status": "partial", "jong_modules": ["placement_utility", "future_match_rollout"], "next": "oracle-guided training labels + runtime adaptation"},
        "kanachan": {"status": "partial", "jong_modules": ["regression_factory", "benchmark"], "next": "formal staged training curriculum"},
        "bakuuchi": {"status": "partial", "jong_modules": ["defense_learning"], "next": "opponent wait/value auxiliary heads"},
        "meowjong": {"status": "partial", "jong_modules": ["sanma_transition", "multi_teacher"], "next": "train separate full-action sanma heads"},
        "luckyj": {"status": "planned", "jong_modules": [], "next": "first-party self-play policy improvement"},
        "maka": {"status": "concept-only", "jong_modules": []},
        "bigcoach": {"status": "concept-only", "jong_modules": ["sanma_transition"]},
    }
