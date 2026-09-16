"""Commercial-safe multi-teacher aggregation for JONG AI.

The useful lesson from strong Mahjong AIs is not to blindly copy one engine.  This
module records provenance, normalizes probability opinions, measures disagreement,
and can abstain when teachers conflict.  It intentionally never calls an external
service by itself.

v6.4 supports an arbitrary legal action set, so the same consensus layer can later
cover discard, chi/pon/kan, riichi, kita/nuki, win and pass -- not only push/fold.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Mapping, Sequence

from .ai_reference_registry import assert_teacher_ingestion_allowed
from .mortal_distillation import ACTIONS


@dataclass(frozen=True)
class TeacherOpinion:
    source: str
    probabilities: Mapping[str, float]
    weight: float = 1.0
    provenance: str | None = None


def _normalize_probabilities(raw: Mapping[str, float], legal_actions: Sequence[str]) -> dict[str, float]:
    actions = tuple(legal_actions)
    if not actions or len(set(actions)) != len(actions):
        raise ValueError("legal_actions must be a non-empty unique sequence")
    unexpected = set(raw) - set(actions)
    if unexpected:
        raise ValueError(f"teacher opinion contains actions outside legal mask: {sorted(unexpected)}")
    vals = {a: float(raw.get(a, 0.0)) for a in actions}
    if any((not math.isfinite(v)) or v < 0 for v in vals.values()):
        raise ValueError("teacher probabilities must be finite and non-negative")
    total = sum(vals.values())
    if total <= 0:
        raise ValueError("teacher probabilities must have positive mass")
    return {a: vals[a] / total for a in actions}


def _normalized_entropy(p: Mapping[str, float]) -> float:
    if len(p) <= 1:
        return 0.0
    h = -sum(v * math.log(v) for v in p.values() if v > 0)
    return h / math.log(len(p))


def aggregate_action_opinions(
    opinions: Iterable[TeacherOpinion],
    legal_actions: Sequence[str],
    *,
    commercial: bool = True,
    max_disagreement: float = 0.34,
) -> dict:
    """Fuse external opinions over an explicit legal-action mask.

    `disagreement` is weighted total-variation distance from each teacher to the
    consensus (0=identical, 1=maximally opposed). High-disagreement positions are
    retained for review but marked unusable for automatic distillation.
    """
    if not 0 <= max_disagreement <= 1:
        raise ValueError("max_disagreement must be in [0,1]")
    actions = tuple(legal_actions)
    if not actions or len(set(actions)) != len(actions):
        raise ValueError("legal_actions must be a non-empty unique sequence")
    rows = list(opinions)
    if not rows:
        raise ValueError("at least one teacher opinion is required")

    checked = []
    for op in rows:
        assert_teacher_ingestion_allowed(op.source, commercial=commercial)
        if not math.isfinite(float(op.weight)) or op.weight <= 0:
            raise ValueError("teacher weight must be finite and > 0")
        checked.append((op, _normalize_probabilities(op.probabilities, actions)))

    weight_sum = sum(float(op.weight) for op, _ in checked)
    consensus = {
        a: sum(float(op.weight) * p[a] for op, p in checked) / weight_sum
        for a in actions
    }
    disagreement = sum(
        float(op.weight) * (0.5 * sum(abs(p[a] - consensus[a]) for a in actions))
        for op, p in checked
    ) / weight_sum
    action = max(actions, key=consensus.get)
    confidence = consensus[action]
    return {
        "teacher_action": action,
        "teacher_probabilities": consensus,
        "legal_actions": list(actions),
        "confidence": confidence,
        "entropy": _normalized_entropy(consensus),
        "disagreement": disagreement,
        "usable_for_training": disagreement <= max_disagreement,
        "sources": [op.source for op, _ in checked],
        "provenance": [op.provenance for op, _ in checked if op.provenance],
        "policy_note": "External opinions were aggregated behind JONG's commercial-use gate; source code/weights are not bundled.",
    }


def aggregate_teacher_opinions(
    opinions: Iterable[TeacherOpinion],
    *,
    commercial: bool = True,
    max_disagreement: float = 0.34,
) -> dict:
    """Backward-compatible push/fold consensus wrapper."""
    return aggregate_action_opinions(
        opinions, ACTIONS, commercial=commercial, max_disagreement=max_disagreement
    )


def build_distillation_row(
    state: Mapping,
    opinions: Iterable[TeacherOpinion],
    *,
    commercial: bool = True,
    max_disagreement: float = 0.34,
) -> dict:
    fused = aggregate_teacher_opinions(
        opinions, commercial=commercial, max_disagreement=max_disagreement
    )
    return {
        "state": dict(state),
        "teacher_action": fused["teacher_action"],
        "teacher_probabilities": fused["teacher_probabilities"],
        "teacher_meta": {
            "confidence": fused["confidence"],
            "entropy": fused["entropy"],
            "disagreement": fused["disagreement"],
            "usable_for_training": fused["usable_for_training"],
            "sources": fused["sources"],
            "provenance": fused["provenance"],
        },
    }


def filter_trainable_rows(rows: Iterable[dict]) -> tuple[list[dict], list[dict]]:
    """Split consensus rows into train/review queues without silently discarding conflicts."""
    train, review = [], []
    for row in rows:
        meta = row.get("teacher_meta") or {}
        (train if meta.get("usable_for_training", False) else review).append(row)
    return train, review
