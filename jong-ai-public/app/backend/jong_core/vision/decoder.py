from __future__ import annotations
import numpy as np


def _iou(a, b):
    x1=max(a[0],b[0]); y1=max(a[1],b[1]); x2=min(a[2],b[2]); y2=min(a[3],b[3])
    inter=max(0.0,x2-x1)*max(0.0,y2-y1)
    aa=max(0.0,a[2]-a[0])*max(0.0,a[3]-a[1])
    bb=max(0.0,b[2]-b[0])*max(0.0,b[3]-b[1])
    den=aa+bb-inter
    return inter/den if den>0 else 0.0


def make_ultralytics_decoder(labels: list[str], conf_threshold: float=0.25, iou_threshold: float=0.45):
    """Decode common Ultralytics YOLOv8/v11 detection ONNX output.

    Supports [1, 4+nc, N] and [1, N, 4+nc] raw detection tensors.
    Coordinates are expected as xywh in letterboxed input pixels.
    """
    def decode(outputs, meta):
        if not outputs:
            return []
        arr=np.asarray(outputs[0])
        if arr.ndim==3:
            arr=arr[0]
        if arr.ndim!=2:
            raise ValueError(f"unsupported YOLO output rank/shape: {arr.shape}")
        expected=4+len(labels)
        if arr.shape[0]==expected:
            arr=arr.T
        elif arr.shape[1]!=expected:
            raise ValueError(f"expected feature dimension {expected}, got {arr.shape}")

        candidates=[]
        for row in arr:
            xywh=row[:4]
            scores=row[4:]
            cid=int(np.argmax(scores))
            conf=float(scores[cid])
            if conf < conf_threshold:
                continue
            cx,cy,w,h=(float(x) for x in xywh)
            box=[cx-w/2, cy-h/2, cx+w/2, cy+h/2]
            candidates.append((conf,cid,box))

        candidates.sort(reverse=True, key=lambda x:x[0])
        kept=[]
        for cand in candidates:
            conf,cid,box=cand
            if any(kcid==cid and _iou(box,kbox)>iou_threshold for _,kcid,kbox in kept):
                continue
            kept.append(cand)

        scale=meta['scale']; px,py=meta['pad']; ow,oh=meta['original_size']
        out=[]
        for conf,cid,box in kept:
            x1=(box[0]-px)/scale; y1=(box[1]-py)/scale
            x2=(box[2]-px)/scale; y2=(box[3]-py)/scale
            x1=max(0,min(ow,x1));x2=max(0,min(ow,x2));y1=max(0,min(oh,y1));y2=max(0,min(oh,y2))
            out.append({'label':labels[cid],'confidence':conf,'bbox':[x1,y1,x2,y2],'class_id':cid})
        return out
    return decode
