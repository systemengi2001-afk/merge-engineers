from __future__ import annotations
import argparse,json
from pathlib import Path
from jong_core.regression_runner import run_fixture_file

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('fixtures')
    ap.add_argument('--out',default='fixture-run.json')
    args=ap.parse_args()
    r=run_fixture_file(args.fixtures)
    Path(args.out).write_text(json.dumps(r,ensure_ascii=False,indent=2))
    print(json.dumps({'cases':r['cases'],'top1_accuracy':r['top1_accuracy'],'shanten_accuracy':r['shanten_accuracy']},ensure_ascii=False))

if __name__=='__main__': main()
