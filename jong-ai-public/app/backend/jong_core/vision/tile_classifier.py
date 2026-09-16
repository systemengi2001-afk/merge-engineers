from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from statistics import mean
from typing import Sequence
from .labels import normalize_label

@dataclass(frozen=True)
class TilePrediction:
    tile: str
    confidence: float
    def __post_init__(self):
        object.__setattr__(self, 'tile', normalize_label(self.tile))
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError('confidence must be in 0..1')

@dataclass(frozen=True)
class ClassifiedHand:
    hand_tiles: tuple[str,...]
    draw_tile: str | None
    confidences: tuple[float,...]
    needs_review: bool
    warnings: tuple[str,...]
    mean_confidence: float

class TileClassifier(ABC):
    name='tile_classifier'
    @abstractmethod
    def predict(self, roi) -> TilePrediction:
        raise NotImplementedError

class MockTileClassifier(TileClassifier):
    """Deterministic test adapter; never selected automatically in production."""
    name='mock_tile_classifier_v5.9'
    def __init__(self, predictions: Sequence[TilePrediction]):
        self._pred=list(predictions); self._i=0
    def predict(self, roi):
        if self._i >= len(self._pred): raise RuntimeError('mock predictions exhausted')
        p=self._pred[self._i]; self._i+=1; return p

def classify_normalized_hand(normalized, classifier: TileClassifier, min_confidence: float=0.90) -> ClassifiedHand:
    """Classify v5.8 normalized 13+draw ROIs, failing closed on uncertainty.

    This is the first identity-classification boundary in the real-photo pipeline.
    It deliberately does not fabricate labels when geometry is absent, confidence is
    low, a label is unknown, or the resulting 14 tiles violate the four-copy rule.
    """
    if normalized is None or len(normalized.get('hand_rois') or []) != 13 or normalized.get('draw_roi') is None:
        raise ValueError('classifier requires confident normalized 13+draw ROIs')
    rois=list(normalized['hand_rois'])+[normalized['draw_roi']]
    preds=[classifier.predict(x) for x in rois]
    labels=[p.tile for p in preds]; conf=[float(p.confidence) for p in preds]
    warnings=[]
    low=[i for i,c in enumerate(conf) if c < min_confidence]
    if low: warnings.append(f'{len(low)} tile classification(s) below confidence threshold {min_confidence:.2f}')
    unknown=[i for i,x in enumerate(labels) if x=='UNKNOWN']
    if unknown: warnings.append(f'{len(unknown)} tile classification(s) are UNKNOWN')
    counts={}
    for x in labels:
        if x=='UNKNOWN': continue
        physical=('5'+x[1]) if x[0]=='0' else x
        counts[physical]=counts.get(physical,0)+1
    impossible=sorted(x for x,n in counts.items() if n>4)
    if impossible: warnings.append('physical copy limit exceeded: '+', '.join(impossible))
    return ClassifiedHand(tuple(labels[:13]), labels[13], tuple(conf), bool(warnings), tuple(warnings), mean(conf))
