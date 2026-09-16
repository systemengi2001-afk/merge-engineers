from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable

LAYER_TARGETS={
    'shanten':{
        'modules':['jong_core/shanten.py'],
        'functions':['calculate_shanten'],
        'test_focus':'known shanten fixtures across standard/chiitoi/kokushi and sanma legal tile sets',
    },
    'ukeire':{
        'modules':['jong_core/analyzer.py'],
        'functions':['ukeire_for_13','analyze_counts'],
        'test_focus':'candidate effective tiles and live remaining counts',
    },
    'probability':{
        'modules':['jong_core/ev.py','jong_core/sanma_transition.py'],
        'functions':['estimate_probabilities','estimate_sanma_auto_nuki_ev'],
        'test_focus':'finite-horizon draw/discard transitions and wall depletion',
    },
    'scoring_ev':{
        'modules':['jong_core/scoring.py','jong_core/ev_score.py','jong_core/open_scoring.py'],
        'functions':['score_closed_hand','estimate_score_ev','score_open_hand'],
        'test_focus':'han/fu/payment/expected-score fixtures',
    },
    'ranking':{
        'modules':['jong_core/analyzer.py','jong_core/instant_analyzer.py'],
        'functions':['analyze_hand','analyze_hand_instant'],
        'test_focus':'stable candidate ordering and tie-break rules',
    },
}

@dataclass(frozen=True)
class ImprovementPlan:
    case_id: str
    primary_layer: str
    priority: int
    target_modules: tuple[str,...]
    target_functions: tuple[str,...]
    recommended_change: str
    regression_test: str
    acceptance_criteria: tuple[str,...]

def plan_from_diagnostic(diagnostic: dict) -> ImprovementPlan:
    layer=diagnostic.get('primary_layer','none')
    cid=str(diagnostic.get('case_id','unknown'))
    cfg=LAYER_TARGETS.get(layer,{'modules':[],'functions':[],'test_focus':'monitor only'})
    actions={
        'shanten':'Compare decomposition/state recursion against oracle fixture and fix the earliest structural divergence.',
        'ukeire':'Recompute every effective tile and live-copy count from the same visible-wall state used by the oracle.',
        'probability':'Inspect draw distribution, hand-change branches, turn consumption and wall depletion; fix transition semantics before tuning constants.',
        'scoring_ev':'Separate scoring mismatch from win-rate mismatch, then correct yaku/fu/payment or expected-score aggregation.',
        'ranking':'Keep candidate metrics unchanged and correct only the ordering/tie-break policy.',
        'none':'No code change. Keep the case as a regression monitor.',
    }
    priority={'shanten':1,'ukeire':2,'probability':3,'scoring_ev':4,'ranking':5,'none':9}.get(layer,8)
    criteria=(
        'target fixture matches oracle top1 or documented equivalent tie',
        'upstream metrics do not regress',
        'full unit test suite passes',
    ) if layer!='none' else ('fixture remains within benchmark thresholds',)
    return ImprovementPlan(
        case_id=cid,
        primary_layer=layer,
        priority=priority,
        target_modules=tuple(cfg['modules']),
        target_functions=tuple(cfg['functions']),
        recommended_change=actions.get(layer,'Manual investigation required.'),
        regression_test=f"Add/keep fixture {cid}: {cfg['test_focus']}.",
        acceptance_criteria=criteria,
    )

def build_improvement_queue(diagnostics: dict, *, limit: int=100) -> dict:
    plans=[plan_from_diagnostic(d) for d in diagnostics.get('diagnostics',[])]
    plans=[p for p in plans if p.primary_layer!='none']
    plans.sort(key=lambda p:(p.priority,p.case_id))
    plans=plans[:limit]
    counts={}
    for p in plans:
        counts[p.primary_layer]=counts.get(p.primary_layer,0)+1
    return {
        'plans':len(plans),
        'layer_counts':counts,
        'queue':[asdict(p) for p in plans],
    }

def compare_benchmark_summaries(before: dict, after: dict) -> dict:
    b=before.get('summary',before)
    a=after.get('summary',after)
    fields=[
        'top1_accuracy','top3_accuracy','shanten_accuracy',
        'mae_ukeire','mae_tenpai_probability','mae_win_probability','mae_expected_points'
    ]
    out={}
    for f in fields:
        bv=b.get(f); av=a.get(f)
        if bv is None or av is None:
            out[f]={'before':bv,'after':av,'delta':None,'improved':None}
            continue
        delta=float(av)-float(bv)
        higher_is_better=f.endswith('accuracy')
        improved=(delta>0) if higher_is_better else (delta<0)
        out[f]={'before':bv,'after':av,'delta':delta,'improved':improved}
    return out
