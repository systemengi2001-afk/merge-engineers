from __future__ import annotations
import argparse,json
from pathlib import Path
from jong_core.improvement_gate import evaluate_improvement_gate, decision_dict

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--before',required=True)
    ap.add_argument('--after',required=True)
    ap.add_argument('--out',default='improvement-decision.json')
    ap.add_argument('--allow-accuracy-regression',type=float,default=0.0)
    ap.add_argument('--allow-probability-mae-regression',type=float,default=0.0)
    ap.add_argument('--allow-ukeire-mae-regression',type=float,default=0.0)
    ap.add_argument('--allow-ev-mae-regression',type=float,default=0.0)
    args=ap.parse_args()
    before=json.loads(Path(args.before).read_text())
    after=json.loads(Path(args.after).read_text())
    d=evaluate_improvement_gate(
        before,after,
        max_accuracy_regression=args.allow_accuracy_regression,
        max_probability_mae_regression=args.allow_probability_mae_regression,
        max_ukeire_mae_regression=args.allow_ukeire_mae_regression,
        max_ev_mae_regression=args.allow_ev_mae_regression,
    )
    payload=decision_dict(d)
    Path(args.out).write_text(json.dumps(payload,ensure_ascii=False,indent=2))
    print(json.dumps({'accepted':d.accepted,'reason':d.reason},ensure_ascii=False))

if __name__=='__main__': main()
