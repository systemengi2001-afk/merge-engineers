from __future__ import annotations
import argparse,json
from pathlib import Path
from jong_core.diagnostics import diagnose_report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('report_json')
    ap.add_argument('--out',default='benchmark-diagnostics.json')
    ap.add_argument('--ukeire-threshold',type=float,default=2.0)
    ap.add_argument('--probability-threshold',type=float,default=0.05)
    ap.add_argument('--ev-threshold',type=float,default=500.0)
    args=ap.parse_args()
    report=json.loads(Path(args.report_json).read_text())
    out=diagnose_report(
        report,
        ukeire_threshold=args.ukeire_threshold,
        probability_threshold=args.probability_threshold,
        ev_threshold=args.ev_threshold,
    )
    Path(args.out).write_text(json.dumps(out,ensure_ascii=False,indent=2))
    print(json.dumps(out['primary_layer_counts'],ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
