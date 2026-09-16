from __future__ import annotations
from dataclasses import dataclass, asdict
from statistics import mean
from typing import Iterable

@dataclass(frozen=True)
class BenchmarkCaseResult:
    case_id: str
    top1_match: bool
    top3_match: bool
    shanten_match: bool | None
    ukeire_abs_errors: tuple[float,...]
    tenpai_abs_errors: tuple[float,...]
    win_abs_errors: tuple[float,...]
    ev_abs_errors: tuple[float,...]
    compared_candidates: int
    jong_best: str | None
    oracle_best: str | None

@dataclass(frozen=True)
class BenchmarkSummary:
    cases: int
    top1_accuracy: float
    top3_accuracy: float
    shanten_accuracy: float | None
    mean_compared_candidates: float
    mae_ukeire: float | None
    mae_tenpai_probability: float | None
    mae_win_probability: float | None
    mae_expected_points: float | None

def _mae(values: list[float]) -> float | None:
    return mean(values) if values else None

def compare_case(case_id: str, jong: dict, oracle: dict) -> BenchmarkCaseResult:
    jcands=jong.get('candidates') or []
    ocands=oracle.get('candidates') or []
    jmap={c.get('discard'):c for c in jcands if c.get('discard')}
    omap={c.get('discard'):c for c in ocands if c.get('discard')}

    jbest=(jong.get('best_by_ev') or jong.get('best_by_probability')
           or jong.get('best_by_shanten_ukeire')
           or (jcands[0].get('discard') if jcands else None))
    obest=(oracle.get('best_by_ev') or oracle.get('best_by_probability')
           or oracle.get('best_by_shanten_ukeire')
           or (ocands[0].get('discard') if ocands else None))
    oracle_top3=[c.get('discard') for c in ocands[:3] if c.get('discard')]

    jsh=jong.get('shanten')
    if jsh is None and isinstance(jong.get('current'),dict):
        jsh=jong['current'].get('shanten')
    osh=oracle.get('shanten')
    if isinstance(osh,dict):
        osh=osh.get('all')
    sh_match=None if jsh is None or osh is None else int(jsh)==int(osh)

    uke=[]; ten=[]; win=[]; ev=[]
    for d in sorted(set(jmap)&set(omap)):
        j=jmap[d]; o=omap[d]
        if j.get('ukeire_total') is not None and o.get('ukeire_total') is not None:
            uke.append(abs(float(j['ukeire_total'])-float(o['ukeire_total'])))
        if j.get('tenpai_probability') is not None and o.get('tenpai_probability') is not None:
            ten.append(abs(float(j['tenpai_probability'])-float(o['tenpai_probability'])))
        if j.get('win_probability') is not None and o.get('win_probability') is not None:
            win.append(abs(float(j['win_probability'])-float(o['win_probability'])))
        if j.get('expected_points') is not None and o.get('expected_points') is not None:
            ev.append(abs(float(j['expected_points'])-float(o['expected_points'])))

    return BenchmarkCaseResult(
        case_id=case_id,
        top1_match=(jbest is not None and jbest==obest),
        top3_match=(jbest is not None and jbest in oracle_top3),
        shanten_match=sh_match,
        ukeire_abs_errors=tuple(uke),
        tenpai_abs_errors=tuple(ten),
        win_abs_errors=tuple(win),
        ev_abs_errors=tuple(ev),
        compared_candidates=len(set(jmap)&set(omap)),
        jong_best=jbest,
        oracle_best=obest,
    )

def summarize(results: Iterable[BenchmarkCaseResult]) -> BenchmarkSummary:
    rows=list(results)
    if not rows:
        return BenchmarkSummary(0,0.0,0.0,None,0.0,None,None,None,None)
    sh=[r.shanten_match for r in rows if r.shanten_match is not None]
    uke=[x for r in rows for x in r.ukeire_abs_errors]
    ten=[x for r in rows for x in r.tenpai_abs_errors]
    win=[x for r in rows for x in r.win_abs_errors]
    ev=[x for r in rows for x in r.ev_abs_errors]
    return BenchmarkSummary(
        cases=len(rows),
        top1_accuracy=mean(1.0 if r.top1_match else 0.0 for r in rows),
        top3_accuracy=mean(1.0 if r.top3_match else 0.0 for r in rows),
        shanten_accuracy=(mean(1.0 if x else 0.0 for x in sh) if sh else None),
        mean_compared_candidates=mean(r.compared_candidates for r in rows),
        mae_ukeire=_mae(uke),
        mae_tenpai_probability=_mae(ten),
        mae_win_probability=_mae(win),
        mae_expected_points=_mae(ev),
    )

def summary_dict(results: Iterable[BenchmarkCaseResult]) -> dict:
    rows=list(results)
    return {
        'summary':asdict(summarize(rows)),
        'cases':[asdict(r) for r in rows],
    }
