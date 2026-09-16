from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json

@dataclass(frozen=True)
class RegressionFixture:
    case_id: str
    hand: str
    game_mode: str
    ruleset: str | None
    turn: int
    expected_oracle_best: str | None
    expected_oracle_shanten: int | None
    expected_oracle_top3: tuple[str,...]
    source_reasons: tuple[str,...]
    severity: float

def build_fixture(case_input: dict, triage_case: dict, oracle_case: dict) -> RegressionFixture:
    ocands=oracle_case.get('candidates') or []
    osh=oracle_case.get('shanten')
    if isinstance(osh,dict):
        osh=osh.get('all')
    return RegressionFixture(
        case_id=str(case_input.get('id') or triage_case.get('case_id') or case_input.get('hand')),
        hand=case_input['hand'],
        game_mode=case_input.get('game_mode','yonma'),
        ruleset=case_input.get('ruleset'),
        turn=int(case_input.get('turn',1)),
        expected_oracle_best=(
            oracle_case.get('best_by_ev')
            or oracle_case.get('best_by_probability')
            or oracle_case.get('best_by_shanten_ukeire')
            or (ocands[0].get('discard') if ocands else None)
        ),
        expected_oracle_shanten=(None if osh is None else int(osh)),
        expected_oracle_top3=tuple(
            c.get('discard') for c in ocands[:3] if c.get('discard')
        ),
        source_reasons=tuple(triage_case.get('reasons',[])),
        severity=float(triage_case.get('severity',0.0)),
    )

def select_priority_fixtures(
    *,
    cases_by_id: dict[str,dict],
    triage: dict,
    oracle_results_by_id: dict[str,dict],
    limit: int=100,
    min_severity: float=4.0,
) -> list[RegressionFixture]:
    out=[]
    for row in triage.get('priority_cases',[]):
        if float(row.get('severity',0)) < min_severity:
            continue
        cid=str(row.get('case_id'))
        case=cases_by_id.get(cid)
        oracle=oracle_results_by_id.get(cid)
        if not case or not oracle:
            continue
        out.append(build_fixture(case,row,oracle))
        if len(out)>=limit:
            break
    return out

def write_fixture_json(path: str | Path, fixtures: list[RegressionFixture]) -> None:
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(
        {'fixtures':[asdict(x) for x in fixtures]},
        ensure_ascii=False,indent=2
    ),encoding='utf-8')
