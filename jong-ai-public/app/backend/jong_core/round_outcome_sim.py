from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable

from .defense_ev import (
    OpponentThreat,
    _single_index,
    _risk_vs_one,
    _combine_independent_risks,
    _visible_counts_for_defense,
    _dora_targets,
)
from .instant_analyzer import analyze_hand_instant
from .placement_utility import PlacementState
from .rules import get_ruleset


@dataclass(frozen=True)
class OutcomeUtility:
    discard: str
    win_probability: float
    deal_in_probability: float
    draw_probability: float
    conditional_win_points: float
    conditional_deal_in_loss: float
    expected_score_delta: float
    expected_rank_utility: float
    win_rank_utility: float
    deal_in_rank_utility: float
    draw_rank_utility: float
    model: str = 'round_outcome_sim_v3.7'


def _rank(scores: tuple[int,...], self_index: int) -> int:
    order=sorted(range(len(scores)),key=lambda i:(-scores[i],i))
    return order.index(self_index)+1


def _rank_utility(scores: tuple[int,...], self_index: int) -> float:
    """Smooth placement utility: rank reward plus score-margin tie breaker."""
    n=len(scores)
    rank=_rank(scores,self_index)
    if n <= 1:
        return 1.0
    rank_part=(n-rank)/(n-1)

    me=scores[self_index]
    others=[s for i,s in enumerate(scores) if i!=self_index]
    nearest=min((abs(me-s) for s in others),default=0)
    signed_margin=0.0
    if rank==1 and others:
        signed_margin=me-max(others)
    elif rank==n and others:
        signed_margin=me-min(others)
    elif others:
        higher=[s for s in others if s>me]
        lower=[s for s in others if s<me]
        up=(min(higher)-me) if higher else 0
        down=(me-max(lower)) if lower else 0
        signed_margin=down-up

    # Margin contributes only a bounded tie-breaker.
    margin_part=max(-0.12,min(0.12,signed_margin/100000.0))
    return max(0.0,min(1.0,rank_part+margin_part))


def _transfer_win(
    scores: tuple[int,...],
    self_index: int,
    gain: float,
    threat_players: tuple[int,...],
) -> tuple[int,...]:
    """Approximate own win transfer while preserving total points."""
    out=[float(x) for x in scores]
    gain=max(0.0,gain)
    out[self_index]+=gain
    opponents=[i for i in range(len(scores)) if i!=self_index]
    if opponents:
        each=gain/len(opponents)
        for i in opponents:
            out[i]-=each
    return tuple(round(x) for x in out)


def _transfer_deal_in(
    scores: tuple[int,...],
    self_index: int,
    loss: float,
    threats: tuple[OpponentThreat,...],
) -> tuple[int,...]:
    out=[float(x) for x in scores]
    loss=max(0.0,loss)
    out[self_index]-=loss

    # Give the loss to the most dangerous/high-value threat when known.
    valid=[t for t in threats if 0 <= t.player < len(scores) and t.player != self_index]
    if valid:
        target=max(valid,key=lambda t:t.estimated_hand_value).player
    else:
        target=next(i for i in range(len(scores)) if i!=self_index)
    out[target]+=loss
    return tuple(round(x) for x in out)


def _draw_delta(
    tenpai_probability: float,
    players: int,
    noten_penalty_total: int,
) -> float:
    """Expected own point delta at exhaustive draw.

    Approximation:
    - if tenpai, gain the full pool when assumed sole tenpai;
    - if noten, pay an equal share to opponents.
    Weighted by the model's own tenpai probability.
    """
    if players <= 1 or noten_penalty_total <= 0:
        return 0.0
    gain_if_tenpai=float(noten_penalty_total)
    loss_if_noten=float(noten_penalty_total)/(players-1)
    p=max(0.0,min(1.0,tenpai_probability))
    return p*gain_if_tenpai-(1-p)*loss_if_noten


def _apply_draw_delta(
    scores: tuple[int,...],
    self_index: int,
    delta: float,
) -> tuple[int,...]:
    out=[float(x) for x in scores]
    out[self_index]+=delta
    opponents=[i for i in range(len(scores)) if i!=self_index]
    if opponents:
        each=-delta/len(opponents)
        for i in opponents:
            out[i]+=each
    return tuple(round(x) for x in out)


def evaluate_round_outcomes(
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
    profile=get_ruleset(ruleset,game_mode)
    threats=tuple(threats)
    visible_tiles=tuple(visible_tiles)
    dora_indicators=tuple(dora_indicators)

    if len(placement.scores) != profile.players:
        raise ValueError('score count must match ruleset player count')
    if not 0 <= placement.self_index < len(placement.scores):
        raise ValueError('self_index out of range')

    attack=analyze_hand_instant(
        hand,
        visible_tiles=visible_tiles,
        draws=draws,
        game_mode=game_mode,
        ruleset=ruleset,
        nuki_count=nuki_count,
        dora_indicators=dora_indicators,
    )

    defense_visible=_visible_counts_for_defense(
        hand,visible_tiles,dora_indicators,threats
    )
    dora_targets=_dora_targets(dora_indicators,profile.allowed_tiles)

    rows=[]
    for c in attack.get('candidates',[]):
        tile=_single_index(c['discard'])

        risks=[]
        weighted_loss=0.0
        for th in threats:
            r,_=_risk_vs_one(
                tile,th,
                visible_counts=defense_visible,
                dora_targets=dora_targets,
            )
            risks.append(r)
            weighted_loss += r*float(th.estimated_hand_value)

        deal=_combine_independent_risks(risks)
        pwin=max(0.0,min(1.0,float(c.get('win_probability',0.0))))
        # Keep outcome probabilities coherent. Deal-in is treated as competing
        # with own win inside the horizon.
        deal=min(deal,max(0.0,1.0-pwin))
        pdraw=max(0.0,1.0-pwin-deal)

        attack_ev=max(0.0,float(c.get('expected_points',0.0)))
        conditional_win=(attack_ev/pwin) if pwin>1e-9 else 0.0
        conditional_loss=(weighted_loss/deal) if deal>1e-9 else 0.0

        draw_delta=_draw_delta(
            float(c.get('tenpai_probability',0.0)),
            profile.players,
            profile.noten_penalty_total,
        )

        win_scores=_transfer_win(
            placement.scores,placement.self_index,conditional_win,
            tuple(t.player for t in threats),
        )
        loss_scores=_transfer_deal_in(
            placement.scores,placement.self_index,conditional_loss,threats
        )
        draw_scores=_apply_draw_delta(
            placement.scores,placement.self_index,draw_delta
        )

        uw=_rank_utility(win_scores,placement.self_index)
        ul=_rank_utility(loss_scores,placement.self_index)
        ud=_rank_utility(draw_scores,placement.self_index)

        expected_u=pwin*uw+deal*ul+pdraw*ud
        expected_delta=(
            pwin*conditional_win
            -deal*conditional_loss
            +pdraw*draw_delta
        )

        rows.append(OutcomeUtility(
            discard=c['discard'],
            win_probability=pwin,
            deal_in_probability=deal,
            draw_probability=pdraw,
            conditional_win_points=conditional_win,
            conditional_deal_in_loss=conditional_loss,
            expected_score_delta=expected_delta,
            expected_rank_utility=expected_u,
            win_rank_utility=uw,
            deal_in_rank_utility=ul,
            draw_rank_utility=ud,
        ))

    rows.sort(key=lambda x:(-x.expected_rank_utility,-x.expected_score_delta,x.deal_in_probability,x.discard))
    best=rows[0] if rows else None

    return {
        'placement_state': asdict(placement),
        'current_rank': _rank(placement.scores,placement.self_index),
        'current_rank_utility': _rank_utility(placement.scores,placement.self_index),
        'recommended_discard': best.discard if best else None,
        'recommended_action': 'maximize_round_rank_ev' if best else None,
        'candidates':[asdict(x) for x in rows],
        'notice':(
            'v3.7 simulates win / deal-in / exhaustive-draw branches and evaluates '
            'the resulting score table. Opponent payment splits, draw-tenpai composition, '
            'honba/kyotaku and future-hand transitions are still approximations.'
        ),
    }
