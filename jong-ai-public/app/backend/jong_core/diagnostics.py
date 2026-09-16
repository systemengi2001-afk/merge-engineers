from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable

@dataclass(frozen=True)
class Diagnostic:
    case_id: str
    primary_layer: str
    contributing_layers: tuple[str,...]
    confidence: float
    rationale: tuple[str,...]
    recommended_action: str
    jong_best: str | None
    oracle_best: str | None

def diagnose_case(case: dict,
                  *,
                  ukeire_threshold: float=2.0,
                  probability_threshold: float=0.05,
                  ev_threshold: float=500.0) -> Diagnostic:
    reasons=[]
    layers=[]

    shanten_match=case.get('shanten_match')
    max_uke=max(case.get('ukeire_abs_errors') or [0.0])
    max_win=max(case.get('win_abs_errors') or [0.0])
    max_ten=max(case.get('tenpai_abs_errors') or [0.0])
    max_ev=max(case.get('ev_abs_errors') or [0.0])
    top1_match=case.get('top1_match',False)

    if shanten_match is False:
        layers.append('shanten')
        reasons.append('シャンテン数が基準計算と不一致')
    if max_uke >= ukeire_threshold:
        layers.append('ukeire')
        reasons.append(f'受け入れ最大誤差 {max_uke:.1f} 枚')
    if max(max_win,max_ten) >= probability_threshold:
        layers.append('probability')
        reasons.append(
            f'確率誤差が大きい（和了率 {max_win:.3f}, 聴牌率 {max_ten:.3f}）'
        )
    if max_ev >= ev_threshold:
        layers.append('scoring_ev')
        reasons.append(f'期待値最大誤差 {max_ev:.1f} pt')
    if not top1_match:
        layers.append('ranking')
        reasons.append('推奨打牌Top1が不一致')

    # Dependency-aware root cause priority.
    if 'shanten' in layers:
        primary='shanten'
        action='シャンテン計算を最優先で修正し、その後受け入れ・確率・EVを再計算'
        confidence=0.98
    elif 'ukeire' in layers:
        primary='ukeire'
        action='有効牌列挙と残枚数計算を修正し、確率層の入力を正す'
        confidence=0.92
    elif 'probability' in layers:
        primary='probability'
        action='ツモ遷移・手変わり・残り山分布の確率モデルを改善'
        confidence=0.86
    elif 'scoring_ev' in layers:
        primary='scoring_ev'
        action='点数計算・和了時平均打点・EV集約ロジックを検証'
        confidence=0.82
    elif 'ranking' in layers:
        primary='ranking'
        action='候補順位のタイブレークと評価関数を検証'
        confidence=0.72
    else:
        primary='none'
        action='基準内。回帰監視のみ継続'
        confidence=0.95
        reasons.append('主要指標は閾値内')

    return Diagnostic(
        case_id=str(case.get('case_id','unknown')),
        primary_layer=primary,
        contributing_layers=tuple(dict.fromkeys(layers)),
        confidence=confidence,
        rationale=tuple(reasons),
        recommended_action=action,
        jong_best=case.get('jong_best'),
        oracle_best=case.get('oracle_best'),
    )

def diagnose_report(report: dict, **kwargs) -> dict:
    rows=[diagnose_case(c,**kwargs) for c in report.get('cases',[])]
    counts={}
    for r in rows:
        counts[r.primary_layer]=counts.get(r.primary_layer,0)+1
    priority_order={'shanten':0,'ukeire':1,'probability':2,'scoring_ev':3,'ranking':4,'none':9}
    rows.sort(key=lambda r:(priority_order.get(r.primary_layer,8),-r.confidence,r.case_id))
    return {
        'cases':len(rows),
        'primary_layer_counts':counts,
        'diagnostics':[asdict(r) for r in rows],
    }
