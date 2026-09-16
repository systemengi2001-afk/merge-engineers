from __future__ import annotations

from dataclasses import dataclass, asdict
from collections import Counter, defaultdict
from pathlib import Path
import json

from .pipeline import VisionPipeline


@dataclass(frozen=True)
class EvalSample:
    image: str
    expected_tiles: tuple[str, ...]


def _normalized_multiset(tokens):
    return Counter(tokens)


def evaluate_samples(pipeline: VisionPipeline, samples: list[EvalSample]) -> dict:
    """Evaluate commercial hand-recognition quality.

    Metrics prioritize whole-hand usability:
    - exact_hand_rate: all 13/14 tiles correct as a multiset
    - review_rate: pipeline asks user for correction
    - mean_corrections: minimum multiset edits needed per hand
    - tile_accuracy: multiset-level tile correctness
    - confusion_by_expected: expected tile -> predicted mismatches
    """
    total_hands = len(samples)
    exact = 0
    review = 0
    total_expected_tiles = 0
    total_correct_tiles = 0
    correction_counts = []
    wrong_hands = 0
    escaped_wrong_hands = 0
    reviewed_wrong_hands = 0
    confusion = defaultdict(Counter)
    per_sample = []

    for s in samples:
        result = pipeline.recognize_hand(s.image)
        predicted = [t.tile for t in result.tiles]
        exp = list(s.expected_tiles)

        ec = _normalized_multiset(exp)
        pc = _normalized_multiset(predicted)
        correct = sum((ec & pc).values())
        missing = list((ec - pc).elements())
        extra = list((pc - ec).elements())
        corrections = max(len(missing), len(extra))

        is_exact = ec == pc and len(exp) == len(predicted)
        exact += int(is_exact)
        review += int(result.needs_review)
        if not is_exact:
            wrong_hands += 1
            if result.needs_review:
                reviewed_wrong_hands += 1
            else:
                escaped_wrong_hands += 1
        total_expected_tiles += len(exp)
        total_correct_tiles += correct
        correction_counts.append(corrections)

        # Approximate confusion accounting: pair sorted missing/extra items.
        for e, p in zip(sorted(missing), sorted(extra)):
            confusion[e][p] += 1
        for e in sorted(missing[len(extra):]):
            confusion[e]["<missed>"] += 1
        for p in sorted(extra[len(missing):]):
            confusion["<extra>"][p] += 1

        per_sample.append({
            "image": s.image,
            "exact": is_exact,
            "needs_review": result.needs_review,
            "confidence": result.confidence,
            "expected_count": len(exp),
            "predicted_count": len(predicted),
            "correct_tiles": correct,
            "corrections": corrections,
            "warnings": list(result.warnings),
            "predicted": predicted,
            "expected": exp,
        })

    return {
        "hands": total_hands,
        "exact_hand_rate": (exact / total_hands) if total_hands else 0.0,
        "review_rate": (review / total_hands) if total_hands else 0.0,
        "mean_corrections": (sum(correction_counts) / total_hands) if total_hands else 0.0,
        "tile_accuracy": (total_correct_tiles / total_expected_tiles) if total_expected_tiles else 0.0,
        # Safety-critical selective-prediction metrics. A wrong hand that is not
        # sent to review can silently poison downstream EV/strategy output.
        "wrong_hands": wrong_hands,
        "escaped_wrong_hands": escaped_wrong_hands,
        "false_accept_rate": (escaped_wrong_hands / total_hands) if total_hands else 0.0,
        "error_review_recall": (reviewed_wrong_hands / wrong_hands) if wrong_hands else 1.0,
        "confusion_by_expected": {k: dict(v) for k, v in confusion.items()},
        "samples": per_sample,
    }


def load_manifest(path: str | Path) -> list[EvalSample]:
    """Manifest JSON format:
    [{"image":"photos/001.jpg","expected_tiles":["1m","2m",...]}]
    """
    path = Path(path)
    data = json.loads(path.read_text())
    out=[]
    for row in data:
        image = Path(row["image"])
        if not image.is_absolute():
            image = path.parent / image
        out.append(EvalSample(str(image), tuple(row["expected_tiles"])))
    return out


def commercial_readiness(report: dict, *, min_exact_hand_rate: float = 0.98,
                         min_tile_accuracy: float = 0.995,
                         max_review_rate: float = 0.15,
                         max_mean_corrections: float = 0.10,
                         max_false_accept_rate: float = 0.01,
                         min_error_review_recall: float = 0.95,
                         min_hands: int = 100) -> dict:
    """Gate release claims using measured, whole-hand recognition quality.

    This intentionally refuses to call a model production-ready from a tiny
    fixture set. Thresholds are configurable; defaults are conservative product
    targets, not claims that the bundled model reaches them.
    """
    checks = {
        "sample_size": int(report.get("hands", 0)) >= min_hands,
        "exact_hand_rate": float(report.get("exact_hand_rate", 0.0)) >= min_exact_hand_rate,
        "tile_accuracy": float(report.get("tile_accuracy", 0.0)) >= min_tile_accuracy,
        "review_rate": float(report.get("review_rate", 1.0)) <= max_review_rate,
        "mean_corrections": float(report.get("mean_corrections", float("inf"))) <= max_mean_corrections,
        "false_accept_rate": float(report.get("false_accept_rate", 1.0)) <= max_false_accept_rate,
        "error_review_recall": float(report.get("error_review_recall", 0.0)) >= min_error_review_recall,
    }
    return {
        "commercial_ready": all(checks.values()),
        "checks": checks,
        "thresholds": {
            "min_hands": min_hands,
            "min_exact_hand_rate": min_exact_hand_rate,
            "min_tile_accuracy": min_tile_accuracy,
            "max_review_rate": max_review_rate,
            "max_mean_corrections": max_mean_corrections,
            "max_false_accept_rate": max_false_accept_rate,
            "min_error_review_recall": min_error_review_recall,
        },
        "measured": {
            k: report.get(k) for k in (
                "hands", "exact_hand_rate", "tile_accuracy", "review_rate", "mean_corrections",
                "false_accept_rate", "error_review_recall"
            )
        },
    }


def select_review_threshold(report: dict, *, max_false_accept_rate: float = 0.01,
                            max_review_rate: float = 0.15,
                            candidates: list[float] | None = None) -> dict:
    """Select a confidence review threshold from measured sample outcomes.

    Existing pipeline review decisions are always preserved. The candidate
    threshold can only add reviews for low-confidence hands; it never suppresses
    a safety warning. Selection first enforces silent-error and review-volume
    limits, then prefers the lowest review rate / threshold.
    """
    samples = list(report.get("samples") or [])
    if candidates is None:
        candidates = [round(x / 100, 2) for x in range(50, 100)]
    rows = []
    n = len(samples)
    for threshold in sorted(set(float(x) for x in candidates)):
        reviewed = 0
        escaped_wrong = 0
        accepted_correct = 0
        for s in samples:
            is_review = bool(s.get("needs_review")) or float(s.get("confidence", 0.0)) < threshold
            reviewed += int(is_review)
            if not bool(s.get("exact")) and not is_review:
                escaped_wrong += 1
            if bool(s.get("exact")) and not is_review:
                accepted_correct += 1
        review_rate = reviewed / n if n else 0.0
        far = escaped_wrong / n if n else 0.0
        rows.append({
            "threshold": threshold,
            "review_rate": review_rate,
            "false_accept_rate": far,
            "accepted_correct_rate": accepted_correct / n if n else 0.0,
            "eligible": n > 0 and far <= max_false_accept_rate and review_rate <= max_review_rate,
        })
    eligible = [r for r in rows if r["eligible"]]
    best = max(eligible, key=lambda r: (r["accepted_correct_rate"], -r["review_rate"], -r["threshold"])) if eligible else None
    return {
        "selected_threshold": best["threshold"] if best else None,
        "eligible": best is not None,
        "constraints": {"max_false_accept_rate": max_false_accept_rate, "max_review_rate": max_review_rate},
        "selected_metrics": best,
        "candidates": rows,
        "evidence_hands": n,
    }
