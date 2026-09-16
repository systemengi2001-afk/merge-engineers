from __future__ import annotations
import argparse,json
from pathlib import Path
from jong_core.case_generator import generate_cases

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--count',type=int,default=1000)
    ap.add_argument('--ruleset',default='yonma_standard')
    ap.add_argument('--seed',type=int,default=20260914)
    ap.add_argument('--out',default='generated-cases.jsonl')
    args=ap.parse_args()
    cases=generate_cases(args.count,ruleset=args.ruleset,seed=args.seed)
    p=Path(args.out)
    p.write_text('\n'.join(json.dumps(c,ensure_ascii=False) for c in cases)+'\n',encoding='utf-8')
    print(f'wrote {len(cases)} cases to {p}')

if __name__=='__main__': main()
