from __future__ import annotations
import argparse, json
from pathlib import Path
from jong_core.vision.ingest import ingest_unverified_photos

def main():
    ap=argparse.ArgumentParser(description='Ingest real JONG AI photos safely as unverified vision samples')
    ap.add_argument('photos', nargs='+'); ap.add_argument('--dataset', default='../vision_dataset'); ap.add_argument('--source', default='user_upload'); ap.add_argument('--report', default='vision-ingest-report.json')
    a=ap.parse_args(); r=ingest_unverified_photos(a.dataset,a.photos,a.source); Path(a.report).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps({k:r[k] for k in ('photos_seen','ingested','duplicates','benchmark_promotions')},indent=2))
if __name__=='__main__': main()
