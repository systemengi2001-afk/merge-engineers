from __future__ import annotations
from dataclasses import dataclass
from .schema import RecognitionResult
from .labels import normalize_label

@dataclass(frozen=True)
class CorrectionTile:
    index: int
    detected: str
    corrected: str
    confidence: float

def correction_payload(result: RecognitionResult) -> dict:
    return {
        "hand_mpsz": result.hand_mpsz,
        "needs_review": result.needs_review,
        "tiles": [
            {
                "index": i,
                "detected": t.tile,
                "confidence": t.confidence,
                "bbox": list(t.bbox),
                "suggested": normalize_label(t.tile),
            }
            for i,t in enumerate(result.tiles)
        ],
        "warnings": list(result.warnings),
    }

def validate_corrected_hand_mpsz(hand: str, *, expected_tiles: int = 14) -> str:
    """Fail closed before corrected photo input reaches EV analysis.

    Requires exactly ``expected_tiles`` physical tiles and rejects impossible
    fifth copies (red five and normal five share the same physical rank).
    Returns the original hand string when valid so API callers can use it inline.
    """
    from ..tiles import parse_mpsz
    try:
        counts = parse_mpsz(hand)
    except Exception as e:
        raise ValueError(f"invalid corrected hand: {e}") from e
    total = sum(counts)
    if total != expected_tiles:
        raise ValueError(f"corrected photo hand must contain exactly {expected_tiles} tiles; got {total}")
    impossible = [i for i, n in enumerate(counts) if n > 4]
    if impossible:
        raise ValueError("corrected photo hand exceeds physical four-copy tile limit")
    return hand

def correction_tile_delta(original: str, corrected: str) -> dict:
    """Return order-independent physical tile deltas for supervised-data triage.

    This deliberately does not pretend to align image crops to labels: compact mpsz
    hands lose tile position.  It is safe metadata for prioritising classes and for
    deciding which corrections need crop-level review later.
    """
    from ..tiles import parse_mpsz, counts_to_tiles
    a = parse_mpsz(original)
    b = parse_mpsz(corrected)
    if sum(a) != sum(b):
        raise ValueError("original and corrected hands must contain the same tile count")
    removed = [max(0, x-y) for x,y in zip(a,b)]
    added = [max(0, y-x) for x,y in zip(a,b)]
    return {
        "removed": counts_to_tiles(removed),
        "added": counts_to_tiles(added),
        "changed_tiles": sum(removed),
    }
