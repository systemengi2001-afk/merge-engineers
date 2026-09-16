from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path

def run(cmd):
    print('+',' '.join(cmd))
    subprocess.run(cmd,check=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--url',required=True)
    ap.add_argument('--count',type=int,default=1000)
    ap.add_argument('--ruleset',default='yonma_standard')
    ap.add_argument('--seed',type=int,default=20260914)
    ap.add_argument('--workdir',default='benchmark-runs/latest')
    ap.add_argument('--fixture-limit',type=int,default=100)
    args=ap.parse_args()

    if not (1 <= args.count <= 10000):
        raise SystemExit('--count must be between 1 and 10000')

    wd=Path(args.workdir); wd.mkdir(parents=True,exist_ok=True)
    cases=wd/'cases.jsonl'
    report=wd/'report.json'
    triage=wd/'triage.json'

    run([sys.executable,'backend/generate_benchmark_cases.py',
         '--count',str(args.count),'--ruleset',args.ruleset,
         '--seed',str(args.seed),'--out',str(cases)])
    run([sys.executable,'backend/benchmark_suite.py',
         '--url',args.url,'--cases',str(cases),'--out',str(report)])
    run([sys.executable,'backend/triage_benchmark.py',
         str(report),'--out',str(triage)])

    # benchmark_suite v2.4 also writes oracle snapshots adjacent to report
    oracle=report.with_name(report.stem+'-oracle-results.json')
    fixtures=wd/'oracle-regressions.json'
    if oracle.exists():
        run([sys.executable,'backend/build_regression_fixtures.py',
             '--cases',str(cases),'--triage',str(triage),
             '--oracle-results',str(oracle),'--out',str(fixtures),
             '--limit',str(args.fixture_limit)])
    print(json.dumps({
        'cases':str(cases),'report':str(report),'triage':str(triage),
        'fixtures':str(fixtures) if fixtures.exists() else None
    },ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
