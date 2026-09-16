from __future__ import annotations
from collections import Counter
from pathlib import Path
import hashlib, json

VALID_SUITS={"m","p","s","z"}
def _valid_tile(t):
    return isinstance(t,str) and len(t)==2 and t[1] in VALID_SUITS and ((t[1]=='z' and t[0] in '1234567') or (t[1]!='z' and t[0] in '0123456789'))

def audit_labeled_crop_sessions(root: str|Path) -> dict:
    """Audit v6.34 crop-label sessions before they are allowed into training.

    A session is atomic: one bad/missing crop excludes all 14 labels. This avoids
    silently shifting positional labels, which would poison a small vision corpus.
    """
    root=Path(root); labeled=root/'labeled'; accepted=[]; rejected=[]
    for d in sorted(labeled.iterdir()) if labeled.is_dir() else []:
        if not d.is_dir(): continue
        errors=[]; mp=d/'manifest.json'
        try: meta=json.loads(mp.read_text(encoding='utf-8'))
        except Exception as e: meta={}; errors.append(f'invalid manifest: {e}')
        labels=meta.get('corrected_tiles')
        if not isinstance(labels,list) or len(labels)!=14: errors.append('corrected_tiles must contain exactly 14 ordered labels')
        elif any(not _valid_tile(x) for x in labels): errors.append('invalid corrected tile label')
        crops=[d/f'{i:02d}.jpg' for i in range(14)]
        if any(not p.is_file() or p.stat().st_size==0 for p in crops): errors.append('all 14 non-empty ordered crops are required')
        row={'session_id':d.name,'errors':errors}
        if errors: rejected.append(row); continue
        accepted.append({'session_id':d.name,'labels':labels,'crops':[str(p.resolve()) for p in crops]})
    counts=Counter(x for s in accepted for x in s['labels'])
    return {'accepted_sessions':len(accepted),'rejected_sessions':len(rejected),'tiles':14*len(accepted),'class_counts':dict(sorted(counts.items())),'sessions':accepted,'rejected':rejected}

def deterministic_group_split(audit: dict, *, holdout_fraction: float=.2) -> dict:
    """Split by correction session, never by tile crop, preventing same-photo leakage."""
    if not 0 < holdout_fraction < 1: raise ValueError('holdout_fraction must be between 0 and 1')
    sessions=list(audit.get('sessions',[]))
    ranked=sorted(sessions,key=lambda s: hashlib.sha256(s['session_id'].encode()).hexdigest())
    if len(ranked)<2: return {'train':ranked,'holdout':[],'evaluation_ready':False,'reason':'need at least 2 independent sessions'}
    n=max(1,round(len(ranked)*holdout_fraction)); n=min(n,len(ranked)-1)
    holdout=ranked[:n]; train=ranked[n:]
    return {'train':train,'holdout':holdout,'evaluation_ready':True,'split_unit':'correction_session','leakage_safe':True}
