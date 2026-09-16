from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Mapping

ACCURACY_FIELDS=('top1_accuracy','top3_accuracy','shanten_accuracy')
ERROR_FIELDS=('mae_ukeire','mae_tenpai_probability','mae_win_probability','mae_expected_points')

@dataclass(frozen=True)
class GateMetric:
    metric: str
    before: float | None
    after: float | None
    delta: float | None
    improved: bool | None
    regressed: bool | None

@dataclass(frozen=True)
class GateDecision:
    accepted: bool
    reason: str
    metrics: tuple[GateMetric,...]
    improvements: int
    regressions: int

def _summary(x: Mapping) -> Mapping:
    return x.get('summary',x)

def evaluate_improvement_gate(
    before: Mapping,
    after: Mapping,
    *,
    max_accuracy_regression: float=0.0,
    max_probability_mae_regression: float=0.0,
    max_ukeire_mae_regression: float=0.0,
    max_ev_mae_regression: float=0.0,
    require_any_improvement: bool=True,
) -> GateDecision:
    b=_summary(before); a=_summary(after)
    rows=[]
    improvements=0
    regressions=0

    for field in ACCURACY_FIELDS + ERROR_FIELDS:
        bv=b.get(field); av=a.get(field)
        if bv is None or av is None:
            rows.append(GateMetric(field,bv,av,None,None,None))
            continue
        bv=float(bv); av=float(av)
        delta=av-bv
        higher_is_better=field in ACCURACY_FIELDS
        if higher_is_better:
            improved=delta>0
            allowed=max_accuracy_regression
            regressed=delta < -allowed
        else:
            improved=delta<0
            if field=='mae_expected_points':
                allowed=max_ev_mae_regression
            elif field=='mae_ukeire':
                allowed=max_ukeire_mae_regression
            else:
                allowed=max_probability_mae_regression
            regressed=delta > allowed
        improvements += int(improved)
        regressions += int(regressed)
        rows.append(GateMetric(field,bv,av,delta,improved,regressed))

    if regressions:
        accepted=False
        reason=f'rejected: {regressions} benchmark metric(s) regressed beyond tolerance'
    elif require_any_improvement and improvements==0:
        accepted=False
        reason='rejected: no benchmark metric improved'
    else:
        accepted=True
        reason=f'accepted: {improvements} metric(s) improved and no metric exceeded regression tolerance'

    return GateDecision(accepted,reason,tuple(rows),improvements,regressions)

def decision_dict(decision: GateDecision) -> dict:
    return asdict(decision)
