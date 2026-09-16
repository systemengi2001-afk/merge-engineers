from __future__ import annotations
from dataclasses import dataclass, asdict
from statistics import median
from .schema import Detection

@dataclass(frozen=True)
class VisionIssue:
    stage: str
    code: str
    severity: str
    detection_indices: tuple[int, ...]
    detail: str
    def to_dict(self):
        d=asdict(self); d['detection_indices']=list(self.detection_indices); return d

def diagnose_detections(detections: list[Detection], min_confidence: float=.80) -> tuple[VisionIssue,...]:
    """Classify likely failure stage without pretending to know ground truth.

    detector_geometry = localization/duplicate problems; classifier = low confidence;
    semantic = physically impossible labels. These are diagnostics, not proof of cause.
    """
    issues=[]
    low=tuple(i for i,d in enumerate(detections) if d.confidence < min_confidence)
    if low:
        issues.append(VisionIssue('classifier','low_confidence','review',low,f'{len(low)} low-confidence detection(s)'))
    overlaps=[]
    for i,a in enumerate(detections):
        for j in range(i+1,len(detections)):
            b=detections[j]
            ix1=max(a.bbox[0],b.bbox[0]); iy1=max(a.bbox[1],b.bbox[1]); ix2=min(a.bbox[2],b.bbox[2]); iy2=min(a.bbox[3],b.bbox[3])
            inter=max(0.,ix2-ix1)*max(0.,iy2-iy1)
            aa=max(0.,a.bbox[2]-a.bbox[0])*max(0.,a.bbox[3]-a.bbox[1]); ab=max(0.,b.bbox[2]-b.bbox[0])*max(0.,b.bbox[3]-b.bbox[1])
            u=aa+ab-inter; iou=inter/u if u else 0.
            if iou >= .70: overlaps.extend((i,j))
    if overlaps:
        ids=tuple(sorted(set(overlaps)))
        issues.append(VisionIssue('detector_geometry','duplicate_overlap','block',ids,'strongly overlapping boxes'))
    if len(detections)>=5:
        ws=[max(0.,d.bbox[2]-d.bbox[0]) for d in detections]; hs=[max(0.,d.bbox[3]-d.bbox[1]) for d in detections]; ys=[(d.bbox[1]+d.bbox[3])/2 for d in detections]
        mw,mh,my=median(ws),median(hs),median(ys)
        size=tuple(i for i,(w,h) in enumerate(zip(ws,hs)) if mw>0 and mh>0 and (w<.55*mw or w>1.8*mw or h<.55*mh or h>1.8*mh))
        row=tuple(i for i,y in enumerate(ys) if mh>0 and abs(y-my)>.65*mh)
        if size: issues.append(VisionIssue('roi_or_detector','box_size_outlier','review',size,'box size differs strongly from hand median'))
        if row: issues.append(VisionIssue('roi_or_detector','row_outlier','review',row,'box center is far from hand row'))
    counts={}
    for i,d in enumerate(detections):
        t=d.tile
        if len(t)==2 and t!='UNKNOWN':
            p=('5'+t[1]) if t[0]=='0' else t; counts.setdefault(p,[]).append(i)
    bad=tuple(i for ids in counts.values() if len(ids)>4 for i in ids)
    if bad: issues.append(VisionIssue('semantic_validation','physical_copy_limit','block',tuple(sorted(bad)),'more than four physical copies recognized'))
    return tuple(issues)
