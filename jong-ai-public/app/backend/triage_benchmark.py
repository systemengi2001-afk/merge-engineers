from __future__ import annotations
import argparse,json
from pathlib import Path
from jong_core.error_mining import mine_report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('report_json')
    ap.add_argument('--out',default='benchmark-triage.json')
    ap.add_argument('--ev-threshold',type=float,default=500.0)
    ap.add_argument('--win-threshold',type=float,default=0.05)
    ap.add_argument('--tenpai-threshold',type=float,default=0.05)
    ap.add_argument('--ukeire-threshold',type=float,default=2.0)
    args=ap.parse_args()

    report=json.loads(Path(args.report_json).read_text())
    triage=mine_report(
        report,
        ev_threshold=args.ev_threshold,
        win_threshold=args.win_threshold,
        tenpai_threshold=args.tenpai_threshold,
        ukeire_threshold=args.ukeire_threshold,
    )
    Path(args.out).write_text(json.dumps(triage,ensure_ascii=False,indent=2))
    print(json.dumps({
        'cases_total':triage['cases_total'],
        'cases_flagged':triage['cases_flagged'],
        'flag_rate':triage['flag_rate'],
        'reason_counts':triage['reason_counts'],
    },ensure_ascii=False,indent=2))

if __name__=='__main__': main()
