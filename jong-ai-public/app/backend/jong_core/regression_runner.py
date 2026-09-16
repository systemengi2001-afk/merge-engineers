from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json

from .instant_analyzer import analyze_hand_instant

@dataclass(frozen=True)
class FixtureResult:
    case_id: str
    expected_best: str | None
    actual_best: str | None
    expected_shanten: int | None
    actual_shanten: int | None
    top1_match: bool
    shanten_match: bool | None

def run_fixture(fixture: dict) -> FixtureResult:
    result=analyze_hand_instant(
        fixture['hand'],
        draws=max(1,min(6,int(fixture.get('turn',1)))),
        game_mode=fixture.get('game_mode','yonma'),
        ruleset=fixture.get('ruleset'),
    )
    actual_best=(
        result.get('best_by_ev')
        or result.get('best_by_probability')
        or result.get('best_by_shanten_ukeire')
        or ((result.get('candidates') or [{}])[0].get('discard'))
    )
    expected_best=fixture.get('expected_oracle_best')
    expected_shanten=fixture.get('expected_oracle_shanten')
    actual_shanten=result.get('current',{}).get('shanten')
    if actual_shanten is None:
        actual_shanten=result.get('shanten')
    return FixtureResult(
        case_id=str(fixture.get('case_id','unknown')),
        expected_best=expected_best,
        actual_best=actual_best,
        expected_shanten=expected_shanten,
        actual_shanten=actual_shanten,
        top1_match=(expected_best is not None and actual_best==expected_best),
        shanten_match=(None if expected_shanten is None or actual_shanten is None else int(expected_shanten)==int(actual_shanten)),
    )

def run_fixture_file(path: str | Path) -> dict:
    data=json.loads(Path(path).read_text())
    fixtures=data.get('fixtures',data)
    rows=[run_fixture(x) for x in fixtures]
    n=len(rows)
    top1=sum(r.top1_match for r in rows)/n if n else 0.0
    sh=[r.shanten_match for r in rows if r.shanten_match is not None]
    return {
        'cases':n,
        'top1_accuracy':top1,
        'shanten_accuracy':(sum(bool(x) for x in sh)/len(sh) if sh else None),
        'results':[asdict(r) for r in rows],
    }
