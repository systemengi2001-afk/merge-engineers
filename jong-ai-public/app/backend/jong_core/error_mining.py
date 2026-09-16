from __future__ import annotations
from dataclasses import dataclass, asdict
from statistics import mean
from typing import Iterable

@dataclass(frozen=True)
class ErrorFlag:
    case_id: str
    severity: float
    reasons: tuple[str,...]
    jong_best: str | None
    oracle_best: str | None
    max_ev_error: float | None
    max_win_error: float | None
    max_tenpai_error: float | None
    max_ukeire_error: float | None

def _max_or_none(values):
    vals=[float(x) for x in values if x is not None]
    return max(vals) if vals else None

def mine_case(case: dict,
              *,
              ev_threshold: float=500.0,
              win_threshold: float=0.05,
              tenpai_threshold: float=0.05,
              ukeire_threshold: float=2.0) -> ErrorFlag:
    reasons=[]
    if not case.get('top1_match',False):
        reasons.append('top1_mismatch')

    ev=_max_or_none(case.get('ev_abs_errors',[]))
    win=_max_or_none(case.get('win_abs_errors',[]))
    ten=_max_or_none(case.get('tenpai_abs_errors',[]))
    uke=_max_or_none(case.get('ukeire_abs_errors',[]))

    if ev is not None and ev >= ev_threshold:
        reasons.append('high_ev_error')
    if win is not None and win >= win_threshold:
        reasons.append('high_win_error')
    if ten is not None and ten >= tenpai_threshold:
        reasons.append('high_tenpai_error')
    if uke is not None and uke >= ukeire_threshold:
        reasons.append('high_ukeire_error')
    if case.get('shanten_match') is False:
        reasons.append('shanten_mismatch')

    severity=0.0
    severity += 5.0 if 'shanten_mismatch' in reasons else 0.0
    severity += 4.0 if 'top1_mismatch' in reasons else 0.0
    severity += min(4.0,(ev or 0.0)/max(ev_threshold,1.0))
    severity += min(3.0,(win or 0.0)/max(win_threshold,1e-9))
    severity += min(3.0,(ten or 0.0)/max(tenpai_threshold,1e-9))
    severity += min(2.0,(uke or 0.0)/max(ukeire_threshold,1e-9))

    return ErrorFlag(
        case_id=str(case.get('case_id','unknown')),
        severity=round(severity,3),
        reasons=tuple(reasons),
        jong_best=case.get('jong_best'),
        oracle_best=case.get('oracle_best'),
        max_ev_error=ev,
        max_win_error=win,
        max_tenpai_error=ten,
        max_ukeire_error=uke,
    )

def mine_report(report: dict, **thresholds) -> dict:
    flags=[mine_case(c,**thresholds) for c in report.get('cases',[])]
    flagged=[f for f in flags if f.reasons]
    flagged.sort(key=lambda f:(-f.severity,f.case_id))

    reason_counts={}
    for f in flagged:
        for r in f.reasons:
            reason_counts[r]=reason_counts.get(r,0)+1

    return {
        'cases_total':len(flags),
        'cases_flagged':len(flagged),
        'flag_rate':(len(flagged)/len(flags) if flags else 0.0),
        'reason_counts':reason_counts,
        'priority_cases':[asdict(f) for f in flagged],
    }
