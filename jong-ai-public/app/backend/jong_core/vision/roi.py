from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class NormalizedROI:
    x1: float; y1: float; x2: float; y2: float
    def validate(self):
        vals=(self.x1,self.y1,self.x2,self.y2)
        if not all(0.0 <= v <= 1.0 for v in vals): raise ValueError("ROI coordinates must be normalized 0..1")
        if self.x1 >= self.x2 or self.y1 >= self.y2: raise ValueError("invalid ROI")

SEAT_ROIS={
    "bottom": NormalizedROI(0.00,0.64,1.00,0.82),
    "top": NormalizedROI(0.00,0.18,1.00,0.36),
    "left": NormalizedROI(0.00,0.18,0.22,0.82),
    "right": NormalizedROI(0.78,0.18,1.00,0.82),
}

def extract_seat_hand_roi(image_path: str | Path, seat: str="bottom", output_path: str | Path | None=None):
    from PIL import Image
    if seat not in SEAT_ROIS: raise ValueError(f"seat must be one of {sorted(SEAT_ROIS)}")
    roi=SEAT_ROIS[seat]; roi.validate()
    img=Image.open(image_path).convert("RGB"); w,h=img.size
    box=(round(roi.x1*w),round(roi.y1*h),round(roi.x2*w),round(roi.y2*h))
    crop=img.crop(box)
    if seat=="top": crop=crop.rotate(180,expand=True)
    elif seat=="left": crop=crop.rotate(270,expand=True)
    elif seat=="right": crop=crop.rotate(90,expand=True)
    if output_path is not None:
        Path(output_path).parent.mkdir(parents=True,exist_ok=True); crop.save(output_path)
    return crop,box


def detect_bottom_hand_band(image, search_y=(0.42, 0.78), band_height=0.05, pad_y=0.025):
    """Estimate the bottom player's face-up hand band from image evidence.

    Uses a low-saturation/bright projection only to localize the row; it does not
    classify tiles. Returns None when the image has too little structure, allowing
    callers to retain the conservative fixed ROI.
    """
    import numpy as np
    arr=np.asarray(image.convert("RGB"), dtype=np.int16)
    h,w=arr.shape[:2]
    y0=max(0,min(h-1,round(search_y[0]*h))); y1=max(y0+1,min(h,round(search_y[1]*h)))
    region=arr[y0:y1]
    mx=region.max(axis=2); mn=region.min(axis=2); mean=region.mean(axis=2)
    whiteish=(mean >= 140) & ((mx-mn) <= 85)
    density=float(whiteish.mean())
    if density < 0.01 or density > 0.80:
        return None
    projection=whiteish.sum(axis=1).astype(float)
    # Phone screenshots often contain a solid-white caption/UI panel below the table.
    # Such rows are not tile evidence and previously pulled the detector away from the
    # actual hand. Suppress near-full-width white rows before the vertical search.
    projection[projection >= 0.88*w] = 0.0
    k=max(12, min(len(projection), round(band_height*h)))
    if len(projection) < k: return None
    scores=np.convolve(projection, np.ones(k), mode="valid")
    idx=int(scores.argmax())
    # Require enough horizontally distributed bright material to avoid locking onto noise.
    if scores[idx] < 0.12*w*k: return None
    top=max(0, y0+idx-round(pad_y*h)); bottom=min(h, y0+idx+k+round(pad_y*h))
    return (0, top, w, bottom)


def split_bottom_hand_and_draw(image, band_box=None, min_column_density=0.18, gap_factor=1.8):
    """Split a localized bottom face-up row into the main hand and detached draw tile.

    Geometry-only heuristic: no tile identities are inferred. A draw tile is reported
    only when the rightmost bright run is separated by a gap materially larger than
    normal within-hand spacing. Otherwise draw_box is None (safe ambiguity).
    """
    import numpy as np
    if band_box is None:
        band_box=detect_bottom_hand_band(image)
    if band_box is None: return None
    arr=np.asarray(image.convert('RGB'),dtype=np.int16)
    x0,y0,x1,y1=band_box; reg=arr[y0:y1,x0:x1]
    mx=reg.max(axis=2); mn=reg.min(axis=2); mean=reg.mean(axis=2)
    mask=(mean>=140)&((mx-mn)<=95)
    active=mask.mean(axis=0)>=min_column_density
    # bridge tiny dark seams inside a tile, but not inter-tile gaps
    k=max(1, round((y1-y0)*0.02))
    if k>1: active=np.convolve(active.astype(int),np.ones(k,dtype=int),mode='same')>0
    runs=[]; start=None
    for i,v in enumerate(active):
        if v and start is None: start=i
        elif not v and start is not None:
            if i-start>=max(3,round((y1-y0)*0.12)): runs.append((start,i))
            start=None
    if start is not None and len(active)-start>=3: runs.append((start,len(active)))
    if len(runs)<2: return {'band_box':band_box,'hand_box':band_box,'draw_box':None,'separation_confident':False}
    gaps=[runs[i+1][0]-runs[i][1] for i in range(len(runs)-1)]
    import statistics
    baseline=statistics.median(gaps[:-1]) if len(gaps)>1 else 1
    last_gap=gaps[-1]
    widths=[b-a for a,b in runs]
    tile_w=statistics.median(widths)
    detached=(last_gap>=max(8, gap_factor*max(1,baseline), 0.35*tile_w))
    if not detached:
        return {'band_box':band_box,'hand_box':(x0+runs[0][0],y0,x0+runs[-1][1],y1),'draw_box':None,'separation_confident':False}
    pad=max(2,round(tile_w*0.08))
    hand=(max(0,x0+runs[0][0]-pad),y0,min(image.width,x0+runs[-2][1]+pad),y1)
    draw=(max(0,x0+runs[-1][0]-pad),y0,min(image.width,x0+runs[-1][1]+pad),y1)
    return {'band_box':band_box,'hand_box':hand,'draw_box':draw,'separation_confident':True,'gap_pixels':last_gap}


def segment_hand_tile_boxes(image, hand_box, expected_count=13, edge_pad_ratio=0.015):
    """Split a localized horizontal concealed hand into per-tile boxes.

    This stage deliberately uses geometry only. It requires an expected tile count and
    refuses implausibly narrow regions instead of fabricating classifications. The
    equal-pitch split is stable for tightly packed real-table rows and provides the
    classifier with deterministic ROIs; identity recognition remains a separate stage.
    """
    if hand_box is None or expected_count < 1:
        return None
    x0,y0,x1,y1=map(int,hand_box); width=x1-x0; height=y1-y0
    if width <= 0 or height <= 0: return None
    pitch=width/float(expected_count)
    # A tile seen face-on should not be vanishingly thin relative to row height.
    if pitch < max(4.0, 0.18*height): return None
    pad=max(0, round(pitch*edge_pad_ratio))
    boxes=[]
    for i in range(expected_count):
        a=round(x0+i*pitch)+pad; b=round(x0+(i+1)*pitch)-pad
        if b<=a: return None
        boxes.append((a,y0,b,y1))
    return boxes


def segment_bottom_hand_tiles_and_draw(image, band_box=None, expected_hand_count=13):
    """End-to-end geometry stage: hand/draw split plus 13 individual hand ROIs.

    Returns no tile boxes when draw separation or hand segmentation is unsafe. The draw
    ROI is kept separate so downstream classification cannot accidentally merge it into
    the concealed-hand sequence.
    """
    split=split_bottom_hand_and_draw(image, band_box)
    if not split:
        return {'split':split,'hand_tile_boxes':None,'draw_tile_box':None,'segmentation_confident':False}
    if not split.get('separation_confident') or split.get('draw_box') is None:
        # Real-table photos frequently have the 14th drawn tile flush with the hand.
        # Preserve fail-closed identity recognition, but allow deterministic 14-slot
        # geometry so the classifier/correction UI can still inspect every tile.
        contiguous=segment_hand_tile_boxes(image,split.get('hand_box'),expected_hand_count+1)
        if contiguous is None or len(contiguous) != expected_hand_count+1:
            return {'split':split,'hand_tile_boxes':None,'draw_tile_box':None,'segmentation_confident':False}
        split=dict(split); split['contiguous_draw_assumed']=True
        return {'split':split,'hand_tile_boxes':contiguous[:-1],'draw_tile_box':contiguous[-1],
                'segmentation_confident':True,'needs_review':True}
    boxes=segment_hand_tile_boxes(image,split['hand_box'],expected_hand_count)
    return {'split':split,'hand_tile_boxes':boxes,'draw_tile_box':split['draw_box'],
            'segmentation_confident':boxes is not None and len(boxes)==expected_hand_count}


def extract_normalized_tile_rois(image, segmentation, output_size=(64, 96), inner_pad_ratio=0.04):
    """Create classifier-ready RGB crops for 13 concealed tiles + detached draw.

    The function is deliberately identity-agnostic. Each geometry box is clipped to
    image bounds, lightly inset to reduce neighbouring-tile leakage, and resized to a
    common portrait tensor size. Unsafe/empty boxes fail closed with None.
    """
    from PIL import Image
    if not segmentation or not segmentation.get('segmentation_confident'):
        return None
    boxes=list(segmentation.get('hand_tile_boxes') or [])
    draw=segmentation.get('draw_tile_box')
    if len(boxes) != 13 or draw is None:
        return None
    all_boxes=boxes+[draw]
    out=[]
    W,H=image.size
    ow,oh=map(int,output_size)
    if ow < 8 or oh < 8: raise ValueError('output_size is too small')
    for box in all_boxes:
        x0,y0,x1,y1=map(int,box)
        x0=max(0,min(W,x0)); x1=max(0,min(W,x1)); y0=max(0,min(H,y0)); y1=max(0,min(H,y1))
        bw=x1-x0; bh=y1-y0
        if bw < 4 or bh < 4: return None
        px=round(bw*inner_pad_ratio); py=round(bh*inner_pad_ratio)
        a,b,c,d=x0+px,y0+py,x1-px,y1-py
        if c-a < 3 or d-b < 3: return None
        crop=image.crop((a,b,c,d)).convert('RGB').resize((ow,oh),Image.Resampling.LANCZOS)
        out.append(crop)
    return {'hand_rois':out[:13], 'draw_roi':out[13], 'all_rois':out,
            'output_size':(ow,oh), 'source_boxes':tuple(all_boxes)}


def save_normalized_tile_rois(image, segmentation, output_dir, stem, output_size=(64,96)):
    """Persist normalized ROIs with deterministic names for labeling/training."""
    from pathlib import Path
    normalized=extract_normalized_tile_rois(image,segmentation,output_size=output_size)
    if normalized is None: return None
    root=Path(output_dir); root.mkdir(parents=True,exist_ok=True)
    paths=[]
    for i,crop in enumerate(normalized['hand_rois'],1):
        p=root/f'{stem}.hand_{i:02d}.png'; crop.save(p); paths.append(str(p))
    p=root/f'{stem}.draw.png'; normalized['draw_roi'].save(p); paths.append(str(p))
    return paths
