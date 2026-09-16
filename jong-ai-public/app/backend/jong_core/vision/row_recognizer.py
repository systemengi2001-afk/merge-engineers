from __future__ import annotations
from pathlib import Path
from statistics import mean
from PIL import Image
from .roi import detect_bottom_hand_band, segment_bottom_hand_tiles_and_draw, extract_normalized_tile_rois
from .trained_classifier import SklearnTileClassifier
from .schema import Detection, RecognitionResult
from .labels import normalize_label


def tiles_to_mpsz(labels):
    groups={s:[] for s in 'mpsz'}
    for raw in labels:
        t=normalize_label(raw)
        if t=='UNKNOWN' or len(t)!=2 or t[1] not in groups: return None
        groups[t[1]].append(t[0])
    return ''.join(''.join(groups[s])+s for s in 'mpsz' if groups[s])


def recognize_bottom_row(image_path, model_path, auto_accept_confidence=0.90):
    """Review-first recognizer for real-table bottom rows.

    Geometry must produce exactly 14 ROIs. The legacy v6.0 classifier is allowed to
    provide correction suggestions, but low confidence never reaches EV analysis.
    """
    im=Image.open(image_path).convert('RGB')
    band=detect_bottom_hand_band(im)
    seg=segment_bottom_hand_tiles_and_draw(im,band_box=band)
    rois=extract_normalized_tile_rois(im,seg) if seg else None
    if rois is None:
        return RecognitionResult((),None,0.0,True,('could not safely segment 14 tiles',),'row_hog_svm_v6.30')
    clf=SklearnTileClassifier(model_path)
    preds=[clf.predict(r) for r in rois['all_rois']]
    boxes=rois['source_boxes']; W,H=im.size
    det=[]
    for p,b in zip(preds,boxes):
        x0,y0,x1,y1=b
        det.append(Detection(normalize_label(p.tile),float(p.confidence),(x0/W,y0/H,x1/W,y1/H)))
    conf=float(mean(d.confidence for d in det)) if det else 0.0
    hand=tiles_to_mpsz([d.tile for d in det])
    # Never auto-accept a row unless every tile clears the gate. This intentionally
    # keeps the current low-accuracy classifier in correction-assist mode.
    safe=hand is not None and all(d.confidence>=auto_accept_confidence for d in det)
    warnings=[]
    if not safe: warnings.append('tile identity confidence below commercial auto-accept gate; confirm/correct all 14 tiles')
    if seg.get('needs_review'): warnings.append('14th tile was contiguous; draw position assumed from rightmost slot')
    return RecognitionResult(tuple(det),hand,conf,not safe,tuple(warnings),clf.name)
