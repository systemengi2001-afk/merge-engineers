from __future__ import annotations
import argparse,json
from pathlib import Path

from jong_core.instant_analyzer import analyze_hand_instant
from jong_core.reference_oracle import (
    build_mahjong_cpp_request,call_mahjong_cpp,normalize_mahjong_cpp_response
)
from jong_core.benchmark import compare_case,summary_dict

def oracle_to_dict(oracle):
    return {
        'shanten':oracle.shanten,
        'best_by_ev':oracle.candidates[0].discard if oracle.candidates else None,
        'candidates':[
            {
                'discard':c.discard,
                'shanten':c.shanten,
                'ukeire_total':c.ukeire_total,
                'tenpai_probability':c.tenpai_probability,
                'win_probability':c.win_probability,
                'expected_points':c.expected_points,
            } for c in oracle.candidates
        ]
    }

def run_case(case,url):
    hand=case['hand']
    game_mode=case.get('game_mode','yonma')
    ruleset=case.get('ruleset')
    turn=int(case.get('turn',1))
    jong=analyze_hand_instant(
        hand,case.get('visible_tiles',[]),
        draws=max(1,min(6,turn)),
        game_mode=game_mode,ruleset=ruleset,
        nuki_count=int(case.get('nuki_count',0)),
    )
    payload=build_mahjong_cpp_request(
        hand=hand,game_mode=game_mode,
        round_wind=case.get('round_wind','1z'),
        seat_wind=case.get('seat_wind','2z'),
        dora_indicators=case.get('dora_indicators',[]),
        nuki_count=int(case.get('nuki_count',0)),
        visible_tiles=case.get('visible_tiles',[]),
    )
    raw=call_mahjong_cpp(url,payload)
    oracle=normalize_mahjong_cpp_response(raw,turn=turn)
    od=oracle_to_dict(oracle)
    return compare_case(case.get('id',hand),jong,od), od

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--url',required=True)
    ap.add_argument('--cases',required=True,help='JSON or JSONL benchmark cases')
    ap.add_argument('--out',default='benchmark-report.json')
    args=ap.parse_args()

    path=Path(args.cases)
    if path.suffix.lower()=='.jsonl':
        cases=[json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    else:
        data=json.loads(path.read_text())
        cases=data['cases'] if isinstance(data,dict) and 'cases' in data else data

    results=[]
    errors=[]
    oracle_results={}
    for case in cases:
        try:
            row,oracle=run_case(case,args.url)
            results.append(row)
            oracle_results[str(case.get('id',case.get('hand')))]=oracle
        except Exception as e:
            errors.append({'id':case.get('id',case.get('hand')),'error':str(e)})

    report=summary_dict(results)
    report['errors']=errors
    out_path=Path(args.out)
    out_path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    oracle_path=out_path.with_name(out_path.stem+'-oracle-results.json')
    oracle_path.write_text(json.dumps({'oracle_results':oracle_results},ensure_ascii=False,indent=2))
    print(json.dumps(report['summary'],ensure_ascii=False,indent=2))
    if errors:
        print(f"errors={len(errors)}")

if __name__=='__main__':
    main()
