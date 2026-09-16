from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable

from .defense_ev import evaluate_defense_ev, OpponentThreat

@dataclass(frozen=True)
class PlacementState:
    scores: tuple[int,...]
    self_index: int
    round_index: int = 0
    total_rounds: int = 8
    dealer_index: int | None = None

@dataclass(frozen=True)
class PlacementCandidate:
    discard: str
    practical_ev_points: float
    placement_multiplier: float
    placement_utility: float
    deal_in_probability: float
    rationale: tuple[str,...]


def _rank(scores: tuple[int,...], self_index: int) -> int:
    me=scores[self_index]
    # deterministic tie-break by seat index only for stable ordering
    ordered=sorted(range(len(scores)), key=lambda i:(-scores[i],i))
    return ordered.index(self_index)+1


def _score_gaps(scores: tuple[int,...], self_index: int) -> tuple[int|None,int|None]:
    me=scores[self_index]
    higher=sorted((s-me) for i,s in enumerate(scores) if i!=self_index and s>me)
    lower=sorted((me-s) for i,s in enumerate(scores) if i!=self_index and s<me)
    return (higher[0] if higher else None, lower[0] if lower else None)


def placement_multiplier(state: PlacementState) -> tuple[float,tuple[str,...]]:
    scores=state.scores
    if not 0 <= state.self_index < len(scores):
        raise ValueError('self_index out of range')
    if state.total_rounds <= 0:
        raise ValueError('total_rounds must be > 0')

    rank=_rank(scores,state.self_index)
    remaining=max(0,state.total_rounds-state.round_index-1)
    late_factor=1.0 + (1.0 - min(1.0, remaining/max(1,state.total_rounds))) * 0.55

    gap_up,gap_down=_score_gaps(scores,state.self_index)
    reasons=[f'{rank}位',f'残り{remaining}局']

    # Baseline by rank: leaders protect, trailers take more variance.
    if rank==1:
        mult=0.82
        reasons.append('トップ目で守備寄り')
        if gap_down is not None and gap_down >= 12000:
            mult*=0.88
            reasons.append('大差トップ')
    elif rank==len(scores):
        mult=1.22
        reasons.append('ラス目で攻撃寄り')
        if gap_up is not None and gap_up >= 8000:
            mult*=1.10
            reasons.append('着順上昇に打点必要')
    else:
        mult=1.0
        reasons.append('中間順位')

    # Late rounds amplify placement sensitivity.
    if rank==1:
        mult /= late_factor
    elif rank==len(scores):
        mult *= late_factor

    # Dealer has more continuation/upside; slightly favor aggression.
    if state.dealer_index is not None and state.dealer_index==state.self_index:
        mult*=1.08
        reasons.append('親番')

    return max(0.45,min(1.85,mult)),tuple(reasons)


def evaluate_placement_ev(
    hand: str,
    *,
    threats: Iterable[OpponentThreat],
    placement: PlacementState,
    visible_tiles: Iterable[str]=(),
    dora_indicators: Iterable[str]=(),
    draws: int=3,
    game_mode: str='sanma',
    ruleset: str='osaka_sanma_v1',
    nuki_count: int=0,
) -> dict:
    base=evaluate_defense_ev(
        hand,
        threats=threats,
        visible_tiles=visible_tiles,
        dora_indicators=dora_indicators,
        draws=draws,
        game_mode=game_mode,
        ruleset=ruleset,
        nuki_count=nuki_count,
    )

    mult,placement_reasons=placement_multiplier(placement)
    rows=[]
    for c in base['candidates']:
        practical=float(c['practical_ev'])
        attack=float(c['attack_ev'])
        loss=float(c['expected_deal_in_loss'])

        # Placement-adjusted utility:
        # - attack upside is scaled by placement multiplier
        # - deal-in loss is inversely scaled, so leaders are penalized harder
        adjusted_attack=attack*mult
        adjusted_loss=loss/max(0.35,mult)
        utility=adjusted_attack-adjusted_loss

        rows.append(PlacementCandidate(
            discard=c['discard'],
            practical_ev_points=practical,
            placement_multiplier=mult,
            placement_utility=utility,
            deal_in_probability=float(c['deal_in_probability']),
            rationale=tuple(c['rationale'])+placement_reasons,
        ))

    rows.sort(key=lambda x:(-x.placement_utility,x.deal_in_probability,-x.practical_ev_points,x.discard))
    best=rows[0] if rows else None

    if not best:
        action=None
    elif mult < 0.9 and best.deal_in_probability <= 0.05:
        action='protect_lead'
    elif mult > 1.15 and best.placement_utility > 0:
        action='push_for_placement'
    elif best.placement_utility > 0:
        action='balanced_push'
    else:
        action='fold_or_turn'

    return {
        'placement_state': asdict(placement),
        'current_rank': _rank(placement.scores,placement.self_index),
        'placement_multiplier': mult,
        'recommended_discard': best.discard if best else None,
        'recommended_action': action,
        'candidates': [asdict(x) for x in rows],
        'notice': (
            'v3.6 adds placement-sensitive utility on top of attack/defense EV. '
            'This is a deterministic heuristic utility layer, not yet a full match-point '
            'simulation or learned rank-EV model.'
        ),
    }
