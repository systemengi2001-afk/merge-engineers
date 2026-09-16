from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class Detection:
    tile: str
    confidence: float
    bbox: tuple[float, float, float, float]
    class_id: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass(frozen=True)
class RecognitionResult:
    tiles: tuple[Detection, ...]
    hand_mpsz: str | None
    confidence: float
    needs_review: bool
    warnings: tuple[str, ...]
    model: str
    diagnostics: tuple[dict, ...] = ()

    def to_dict(self) -> dict:
        return {
            "tiles": [t.to_dict() for t in self.tiles],
            "hand_mpsz": self.hand_mpsz,
            "confidence": self.confidence,
            "needs_review": self.needs_review,
            "warnings": list(self.warnings),
            "model": self.model,
            "diagnostics": list(self.diagnostics),
        }
