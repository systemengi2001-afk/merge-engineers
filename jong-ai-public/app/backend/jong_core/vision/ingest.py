from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import json, shutil
from PIL import Image
from .roi import detect_bottom_hand_band, split_bottom_hand_and_draw

@dataclass(frozen=True)
class IngestResult:
    source: str
    sample_id: str
    status: str
    sha256: str
    width: int
    height: int
    raw_image: str | None
    candidate_roi: str | None
    benchmark_eligible: bool = False


def _digest(path: Path) -> str:
    h=sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def _known_hashes(root: Path) -> dict[str,str]:
    out={}
    for p in (root/'raw').glob('*') if (root/'raw').is_dir() else []:
        if p.is_file(): out[_digest(p)] = p.name
    return out


def ingest_unverified_photos(dataset_dir: str|Path, photos: list[str|Path], source: str='user_upload', roi_y=(0.62,0.84)) -> dict:
    """Safely ingest real photos without promoting them into the verified benchmark.

    Exact duplicates are rejected by SHA-256. New photos get a conservative bottom-seat
    candidate ROI for later manual labelling, but no expected tiles and therefore cannot
    enter the commercial accuracy manifest until a separate verified label is created.
    """
    root=Path(dataset_dir); raw=root/'raw'; crops=root/'crops'; pending=root/'pending'
    for d in (raw,crops,pending): d.mkdir(parents=True, exist_ok=True)
    known=_known_hashes(root); results=[]
    for src0 in photos:
        src=Path(src0); digest=_digest(src)
        with Image.open(src) as im:
            w,h=im.size
            if digest in known:
                results.append(IngestResult(str(src), known[digest].rsplit('.',1)[0], 'duplicate', digest,w,h,None,None))
                continue
            sample_id=f"real_{digest[:12]}"
            ext=(src.suffix or '.jpg').lower(); dst=raw/f'{sample_id}{ext}'
            shutil.copy2(src,dst)
            fixed=(0,max(0,min(h,int(h*roi_y[0]))),w,max(1,min(h,int(h*roi_y[1]))))
            adaptive=detect_bottom_hand_band(im)
            box=adaptive or fixed
            split=split_bottom_hand_and_draw(im, box)
            y0,y1=box[1],box[3]
            crop=im.crop(box); crop_path=crops/f'{sample_id}.bottom_candidate.png'; crop.save(crop_path)
            meta={
                'id':sample_id,'image':f'../raw/{dst.name}','source':source,'sha256':digest,
                'width':w,'height':h,'candidate_roi_box_pixels':list(box),
                'candidate_roi_method':'adaptive_white_row_v1' if adaptive else 'fixed_fallback',
                'candidate_roi_image':f'../crops/{crop_path.name}',
                'hand_draw_split': ({'hand_box_pixels':list(split['hand_box']), 'draw_box_pixels':list(split['draw_box']) if split.get('draw_box') else None, 'separation_confident':bool(split.get('separation_confident',False))} if split else None),
                'manual_label_verified':False,'benchmark_eligible':False,
                'notes':'Unverified real photo. Candidate ROI only; must not enter accuracy benchmark before manual ground-truth verification.'
            }
            (pending/f'{sample_id}.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
            known[digest]=dst.name
            results.append(IngestResult(str(src),sample_id,'ingested',digest,w,h,str(dst),str(crop_path)))
    report={'photos_seen':len(results),'ingested':sum(r.status=='ingested' for r in results),'duplicates':sum(r.status=='duplicate' for r in results),'benchmark_promotions':0,'results':[asdict(r) for r in results]}
    return report
