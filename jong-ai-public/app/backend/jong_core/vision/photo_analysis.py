from __future__ import annotations
from pathlib import Path
from PIL import Image
from .roi import segment_bottom_hand_tiles_and_draw,extract_normalized_tile_rois
from .tile_classifier import classify_normalized_hand
from .trained_classifier import SklearnTileClassifier

def _compact(labels):
    groups={s:[] for s in 'mpsz'}
    for t in labels:
        if t=='UNKNOWN': raise ValueError('unknown tile')
        groups[t[1]].append(t[0])
    return ''.join(''.join(groups[s])+s for s in 'mpsz' if groups[s])

def analyze_photo_fail_closed(image_path, model_path, *, validated_tile_accuracy=None, required_accuracy=0.98, min_confidence=0.90, ruleset='osaka_sanma'):
    """Photo -> ROI -> trained classifier -> 14 codes -> instant analysis, with a model-quality gate.

    Recognition may run below the quality threshold for measurement, but EV is never
    returned unless the independently supplied held-out accuracy meets the release gate.
    """
    im=Image.open(image_path).convert('RGB')
    seg=segment_bottom_hand_tiles_and_draw(im)
    norm=extract_normalized_tile_rois(im,seg)
    if norm is None: return {'status':'review','stage':'segmentation','analysis':None}
    classified=classify_normalized_hand(norm,SklearnTileClassifier(model_path),min_confidence=min_confidence)
    labels=list(classified.hand_tiles)+[classified.draw_tile]
    out={'status':'review','stage':'classification','tiles':labels,'mean_confidence':classified.mean_confidence,'warnings':list(classified.warnings),'analysis':None}
    if classified.needs_review: return out
    if validated_tile_accuracy is None or validated_tile_accuracy < required_accuracy:
        out['warnings'].append(f'model held-out accuracy below release gate {required_accuracy:.3f}')
        return out
    from ..instant_analyzer import analyze_hand_instant
    hand=_compact(labels); out['hand_code']=hand
    out['analysis']=analyze_hand_instant(hand,ruleset=ruleset); out['status']='ok'; out['stage']='analysis'
    return out
