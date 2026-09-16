from __future__ import annotations
import argparse,json
from pathlib import Path

def pct(x):
    return "-" if x is None else f"{x*100:.1f}%"

def num(x,d=3):
    return "-" if x is None else f"{x:.{d}f}"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('report_json')
    ap.add_argument('--out',default='benchmark-report.md')
    args=ap.parse_args()
    data=json.loads(Path(args.report_json).read_text())
    s=data['summary']
    lines=[
        '# JONG AI Benchmark Report','',
        f"- Cases: {s['cases']}",
        f"- Top1 accuracy: {pct(s['top1_accuracy'])}",
        f"- Top3 accuracy: {pct(s['top3_accuracy'])}",
        f"- Shanten accuracy: {pct(s['shanten_accuracy'])}",
        f"- Mean compared candidates: {num(s['mean_compared_candidates'],2)}",
        f"- MAE ukeire: {num(s['mae_ukeire'],2)}",
        f"- MAE tenpai probability: {num(s['mae_tenpai_probability'])}",
        f"- MAE win probability: {num(s['mae_win_probability'])}",
        f"- MAE expected points: {num(s['mae_expected_points'],1)} pt",
        '',
        '## Cases','',
        '| Case | JONG | Oracle | Top1 | Top3 |',
        '|---|---|---|---:|---:|',
    ]
    for c in data.get('cases',[]):
        lines.append(f"| {c['case_id']} | {c.get('jong_best') or '-'} | {c.get('oracle_best') or '-'} | {'✓' if c['top1_match'] else '×'} | {'✓' if c['top3_match'] else '×'} |")
    if data.get('errors'):
        lines += ['', '## Errors', '']
        for e in data['errors']:
            lines.append(f"- {e['id']}: {e['error']}")
    Path(args.out).write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__': main()
