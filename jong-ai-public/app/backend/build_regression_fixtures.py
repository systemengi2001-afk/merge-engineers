from __future__ import annotations
import argparse,json
from pathlib import Path
from jong_core.regression_factory import select_priority_fixtures, write_fixture_json

def _load_cases(path: str) -> dict[str,dict]:
    p=Path(path)
    if p.suffix.lower()=='.jsonl':
        rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    else:
        data=json.loads(p.read_text())
        rows=data.get('cases',data) if isinstance(data,dict) else data
    return {str(x.get('id',x.get('hand'))):x for x in rows}

def _load_oracle(path: str) -> dict[str,dict]:
    data=json.loads(Path(path).read_text())
    rows=data.get('oracle_results',data)
    if isinstance(rows,list):
        return {str(x['case_id']):x['oracle'] for x in rows}
    return {str(k):v for k,v in rows.items()}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--cases',required=True)
    ap.add_argument('--triage',required=True)
    ap.add_argument('--oracle-results',required=True)
    ap.add_argument('--out',default='tests/fixtures/oracle-regressions.json')
    ap.add_argument('--limit',type=int,default=100)
    ap.add_argument('--min-severity',type=float,default=4.0)
    args=ap.parse_args()

    cases=_load_cases(args.cases)
    triage=json.loads(Path(args.triage).read_text())
    oracle=_load_oracle(args.oracle_results)
    fixtures=select_priority_fixtures(
        cases_by_id=cases,
        triage=triage,
        oracle_results_by_id=oracle,
        limit=args.limit,
        min_severity=args.min_severity,
    )
    write_fixture_json(args.out,fixtures)
    print(json.dumps({'fixtures_written':len(fixtures),'out':args.out},ensure_ascii=False))

if __name__=='__main__':
    main()
