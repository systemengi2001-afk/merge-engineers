from __future__ import annotations
from dataclasses import dataclass, asdict
from functools import lru_cache
from typing import Iterable

from .match_state_ev import MatchState, evaluate_match_state_ev
from .defense_ev import OpponentThreat


@dataclass(frozen=True)
class RolloutCandidate:
    discard: str
    immediate_match_utility: float
    rollout_match_utility: float
    horizon_rounds: int
    expected_score_delta: float
    terminal_probability: float
    model: str = 'future_match_rollout_v3.9'


def _rank(scores: tuple[int,...], self_index: int) -> int:
    order=sorted(range(len(scores)),key=lambda i:(-scores[i],i))
    return order.index(self_index)+1


def _terminal_utility(scores: tuple[int,...], self_index: int) -> float:
    n=len(scores)
    if n<=1:
        return 1.0
    return (n-_rank(scores,self_index))/(n-1)


def _generic_future_probs(scores: tuple[int,...], self_index: int, dealer_index: int):
    """Small deterministic prior for future-hand outcome rollout.

    This is intentionally generic and only used after the current hand, where
    detailed tile-state information is unavailable. It avoids a fixed placement
    multiplier and instead propagates actual score-table branches.
    """
    rank=_rank(scores,self_index)
    p_self=0.28
    p_deal=0.16
    p_other=0.36
    p_draw=0.20

    if self_index==dealer_index:
        p_self += 0.04
        p_other -= 0.02
        p_deal -= 0.01
        p_draw -= 0.01

    if rank==1:
        p_deal -= 0.02
        p_self -= 0.02
        p_draw += 0.03
        p_other += 0.01
    elif rank==len(scores):
        p_self += 0.03
        p_deal += 0.02
        p_draw -= 0.02
        p_other -= 0.03

    vals=[max(0.01,x) for x in (p_self,p_deal,p_other,p_draw)]
    s=sum(vals)
    return tuple(x/s for x in vals)


def _apply_delta(scores: tuple[int,...], self_index: int, delta: int, target: int | None=None):
    out=[float(x) for x in scores]
    out[self_index]+=delta
    others=[i for i in range(len(scores)) if i!=self_index]

    if delta >= 0:
        if others:
            each=delta/len(others)
            for i in others:
                out[i]-=each
    else:
        loss=-delta
        if target is None or target==self_index:
            target=others[0]
        out[target]+=loss
    return tuple(round(x) for x in out)


def _other_win(scores: tuple[int,...], self_index: int, dealer_index: int, points: int=5000):
    out=list(scores)
    others=[i for i in range(len(scores)) if i!=self_index]
    target=dealer_index if dealer_index in others else others[0]
    payer=next(i for i in others if i!=target) if len(others)>1 else self_index
    out[target]+=points
    out[payer]-=points
    return tuple(out)


@lru_cache(maxsize=None)
def _future_value(
    scores: tuple[int,...],
    self_index: int,
    dealer_index: int,
    round_index: int,
    total_rounds: int,
    horizon: int,
) -> float:
    if horizon<=0 or round_index>=total_rounds:
        return _terminal_utility(scores,self_index)

    p_self,p_deal,p_other,p_draw=_generic_future_probs(scores,self_index,dealer_index)

    # Generic future hand score swings. These are deliberately modest priors and
    # only substitute for missing future tile-state information.
    self_gain=6500 if self_index==dealer_index else 5200
    deal_loss=7000
    other_gain=5000

    self_scores=_apply_delta(scores,self_index,self_gain)
    deal_target=dealer_index if dealer_index!=self_index else (self_index+1)%len(scores)
    deal_scores=_apply_delta(scores,self_index,-deal_loss,target=deal_target)
    other_scores=_other_win(scores,self_index,dealer_index,other_gain)
    draw_scores=scores

    # Dealer continuation on own win; otherwise rotate.
    self_next_dealer=dealer_index if self_index==dealer_index else (dealer_index+1)%len(scores)
    self_next_round=round_index if self_index==dealer_index else round_index+1

    next_dealer=(dealer_index+1)%len(scores)
    normal_next_round=round_index+1

    v_self=_future_value(
        self_scores,self_index,self_next_dealer,self_next_round,total_rounds,horizon-1
    )
    v_deal=_future_value(
        deal_scores,self_index,next_dealer,normal_next_round,total_rounds,horizon-1
    )
    v_other=_future_value(
        other_scores,self_index,next_dealer,normal_next_round,total_rounds,horizon-1
    )

    # Exhaustive draw: own dealer gets a modest continuation chance.
    if self_index==dealer_index:
        v_draw=(
            0.55*_future_value(draw_scores,self_index,dealer_index,round_index,total_rounds,horizon-1)
            +0.45*_future_value(draw_scores,self_index,next_dealer,normal_next_round,total_rounds,horizon-1)
        )
    else:
        v_draw=_future_value(
            draw_scores,self_index,next_dealer,normal_next_round,total_rounds,horizon-1
        )

    return p_self*v_self+p_deal*v_deal+p_other*v_other+p_draw*v_draw


def _approx_current_branch_scores(match: MatchState, candidate: dict):
    """Reconstruct current branch score tables from v3.8 candidate summaries."""
    scores=match.scores
    me=match.self_index
    n=len(scores)

    expected_delta=float(candidate.get('expected_score_delta',0.0))
    terminal=float(candidate.get('terminal_probability',0.0))

    # v3.8 does not expose branch score tables yet. v3.9 uses the current expected
    # score delta as a common branch anchor, then future rollout begins from there.
    # This keeps current-hand evaluation exact to the existing engine and moves the
    # approximation boundary strictly into future unknown hands.
    out=[float(x) for x in scores]
    out[me]+=expected_delta
    others=[i for i in range(n) if i!=me]
    if others:
        each=expected_delta/len(others)
        for i in others:
            out[i]-=each
    return tuple(round(x) for x in out),terminal


def evaluate_future_match_rollout(
    hand: str,
    *,
    threats: Iterable[OpponentThreat],
    match: MatchState,
    visible_tiles: Iterable[str]=(),
    dora_indicators: Iterable[str]=(),
    draws: int=3,
    game_mode: str='sanma',
    ruleset: str='osaka_sanma_v1',
    nuki_count: int=0,
    future_rounds: int=2,
) -> dict:
    if future_rounds < 0 or future_rounds > 4:
        raise ValueError('future_rounds must be 0..4')

    base=evaluate_match_state_ev(
        hand,
        threats=threats,
        match=match,
        visible_tiles=visible_tiles,
        dora_indicators=dora_indicators,
        draws=draws,
        game_mode=game_mode,
        ruleset=ruleset,
        nuki_count=nuki_count,
    )

    rows=[]
    for c in base['candidates']:
        anchored_scores,terminal_prob=_approx_current_branch_scores(match,c)
        immediate=float(c['expected_match_utility'])

        if future_rounds==0 or terminal_prob>=0.999:
            rollout=immediate
        else:
            next_dealer=(match.dealer_index+1)%len(match.scores)
            next_round=min(match.total_rounds,match.round_index+1)
            future=_future_value(
                anchored_scores,
                match.self_index,
                next_dealer,
                next_round,
                match.total_rounds,
                future_rounds,
            )
            rollout=terminal_prob*immediate+(1-terminal_prob)*future

        rows.append(RolloutCandidate(
            discard=c['discard'],
            immediate_match_utility=immediate,
            rollout_match_utility=rollout,
            horizon_rounds=future_rounds,
            expected_score_delta=float(c['expected_score_delta']),
            terminal_probability=terminal_prob,
        ))

    rows.sort(key=lambda x:(-x.rollout_match_utility,-x.immediate_match_utility,-x.expected_score_delta,x.discard))
    best=rows[0] if rows else None

    return {
        'match_state':asdict(match),
        'future_rounds':future_rounds,
        'recommended_discard':best.discard if best else None,
        'recommended_action':'maximize_future_match_ev' if best else None,
        'candidates':[asdict(x) for x in rows],
        'notice':(
            'v3.9 rolls score tables forward into future rounds instead of using a fixed '
            'placement multiplier. Current-hand EV still comes from v3.8; future unknown '
            'hands use a generic deterministic outcome prior until real log calibration lands.'
        ),
    }
