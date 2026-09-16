from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable

from .round_outcome_sim import evaluate_round_outcomes
from .placement_utility import PlacementState
from .defense_ev import OpponentThreat
from .rules import get_ruleset


@dataclass(frozen=True)
class MatchState:
    scores: tuple[int,...]
    self_index: int
    dealer_index: int
    round_index: int
    total_rounds: int
    honba: int = 0
    riichi_sticks: int = 0
    agari_yame: bool = True
    target_return_points: int | None = None


@dataclass(frozen=True)
class MatchCandidate:
    discard: str
    expected_match_utility: float
    expected_score_delta: float
    current_rank_utility: float
    terminal_probability: float
    next_round_probability: float
    rationale: tuple[str,...]
    model: str = 'match_state_ev_v3.8'


def _rank(scores: tuple[int,...], self_index: int) -> int:
    order=sorted(range(len(scores)),key=lambda i:(-scores[i],i))
    return order.index(self_index)+1


def _rank_utility(scores: tuple[int,...], self_index: int) -> float:
    n=len(scores)
    if n<=1:
        return 1.0
    rank=_rank(scores,self_index)
    return (n-rank)/(n-1)


def _apply_win_bonus(
    scores: tuple[int,...],
    self_index: int,
    base_gain: float,
    *,
    honba: int,
    riichi_sticks: int,
) -> tuple[int,...]:
    out=[float(x) for x in scores]
    # Approximate: winner receives all sticks and total honba bonus.
    bonus=riichi_sticks*1000 + honba*300
    total_gain=max(0.0,base_gain)+bonus
    out[self_index]+=total_gain
    opponents=[i for i in range(len(scores)) if i!=self_index]
    if opponents:
        # riichi sticks are already outside player scores in real play; to keep this
        # layer total-stable enough for ranking comparison, only redistribute base/honba.
        redist=max(0.0,base_gain)+honba*300
        each=redist/len(opponents)
        for i in opponents:
            out[i]-=each
    return tuple(round(x) for x in out)


def _apply_deal_in(
    scores: tuple[int,...],
    self_index: int,
    loss: float,
    threats: tuple[OpponentThreat,...],
    *,
    honba: int,
) -> tuple[int,...]:
    out=[float(x) for x in scores]
    total=max(0.0,loss)+honba*300
    out[self_index]-=total
    valid=[t for t in threats if 0 <= t.player < len(scores) and t.player != self_index]
    target=max(valid,key=lambda t:t.estimated_hand_value).player if valid else next(
        i for i in range(len(scores)) if i!=self_index
    )
    out[target]+=total
    return tuple(round(x) for x in out)


def _is_terminal_after_win(
    state: MatchState,
    scores_after: tuple[int,...],
) -> bool:
    is_last_round=state.round_index >= state.total_rounds-1
    if not is_last_round:
        return False

    rank=_rank(scores_after,state.self_index)
    if state.agari_yame and state.self_index==state.dealer_index and rank==1:
        return True

    # Otherwise last scheduled round ends after a non-dealer win or when dealer
    # continuation is not invoked by agari-yame. This is a simplified end rule.
    return state.self_index != state.dealer_index


def _next_state_utility(
    scores_after: tuple[int,...],
    self_index: int,
    dealer_index: int,
    round_index: int,
    total_rounds: int,
) -> float:
    base=_rank_utility(scores_after,self_index)
    remaining=max(0,total_rounds-round_index-1)
    if remaining<=0:
        return base

    # Small future optionality bonus for being close to the next rank boundary.
    me=scores_after[self_index]
    ordered=sorted(scores_after,reverse=True)
    rank=_rank(scores_after,self_index)
    gap=0
    if rank>1:
        higher=sorted(s for i,s in enumerate(scores_after) if i!=self_index and s>me)
        gap=min(higher)-me if higher else 0
    optionality=max(0.0,0.08-min(0.08,gap/100000.0))
    if self_index==dealer_index:
        optionality+=0.02
    return max(0.0,min(1.0,base+optionality))


def evaluate_match_state_ev(
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
) -> dict:
    profile=get_ruleset(ruleset,game_mode)
    threats=tuple(threats)

    if len(match.scores)!=profile.players:
        raise ValueError('score count must match ruleset player count')
    if not 0 <= match.self_index < profile.players:
        raise ValueError('self_index out of range')
    if not 0 <= match.dealer_index < profile.players:
        raise ValueError('dealer_index out of range')
    if match.honba < 0 or match.riichi_sticks < 0:
        raise ValueError('honba and riichi_sticks must be >= 0')

    placement=PlacementState(
        scores=match.scores,
        self_index=match.self_index,
        round_index=match.round_index,
        total_rounds=match.total_rounds,
        dealer_index=match.dealer_index,
    )
    round_eval=evaluate_round_outcomes(
        hand,
        threats=threats,
        placement=placement,
        visible_tiles=visible_tiles,
        dora_indicators=dora_indicators,
        draws=draws,
        game_mode=game_mode,
        ruleset=ruleset,
        nuki_count=nuki_count,
    )

    current_u=_rank_utility(match.scores,match.self_index)
    rows=[]

    for c in round_eval['candidates']:
        pwin=float(c['win_probability'])
        pdeal=float(c['deal_in_probability'])
        pdraw=float(c['draw_probability'])
        win_gain=float(c['conditional_win_points'])
        deal_loss=float(c['conditional_deal_in_loss'])

        win_scores=_apply_win_bonus(
            match.scores,match.self_index,win_gain,
            honba=match.honba,
            riichi_sticks=match.riichi_sticks,
        )
        deal_scores=_apply_deal_in(
            match.scores,match.self_index,deal_loss,threats,
            honba=match.honba,
        )

        # Exhaustive draw uses the score delta already estimated in v3.7.
        draw_delta=float(c['expected_score_delta']) - (
            pwin*win_gain - pdeal*deal_loss
        )
        draw_delta=(draw_delta/pdraw) if pdraw>1e-9 else 0.0
        draw_scores=list(match.scores)
        draw_scores[match.self_index]+=round(draw_delta)
        draw_scores=tuple(draw_scores)

        terminal_win=_is_terminal_after_win(match,win_scores)
        uw=_rank_utility(win_scores,match.self_index) if terminal_win else _next_state_utility(
            win_scores,match.self_index,
            match.dealer_index if match.self_index==match.dealer_index else (match.dealer_index+1)%profile.players,
            match.round_index if match.self_index==match.dealer_index else match.round_index+1,
            match.total_rounds,
        )

        # Deal-in by self never preserves own dealer continuation in this simplified layer.
        next_dealer=(match.dealer_index+1)%profile.players
        ul=_next_state_utility(
            deal_scores,match.self_index,next_dealer,match.round_index+1,match.total_rounds
        )

        # Draw: dealer continuation probability is approximated by own dealer + tenpai branch.
        if match.self_index==match.dealer_index and float(c['draw_rank_utility']) >= current_u:
            draw_dealer=match.dealer_index
            draw_round=match.round_index
        else:
            draw_dealer=next_dealer
            draw_round=match.round_index+1
        ud=_next_state_utility(
            draw_scores,match.self_index,draw_dealer,draw_round,match.total_rounds
        )

        expected=pwin*uw+pdeal*ul+pdraw*ud
        terminal_prob=pwin if terminal_win else 0.0
        next_prob=1.0-terminal_prob

        rows.append(MatchCandidate(
            discard=c['discard'],
            expected_match_utility=expected,
            expected_score_delta=float(c['expected_score_delta']) + pwin*(match.riichi_sticks*1000 + match.honba*300) - pdeal*(match.honba*300),
            current_rank_utility=current_u,
            terminal_probability=terminal_prob,
            next_round_probability=next_prob,
            rationale=(
                f'本場:{match.honba}',
                f'供託:{match.riichi_sticks}',
                f'局:{match.round_index+1}/{match.total_rounds}',
                '親' if match.self_index==match.dealer_index else '子',
            ),
        ))

    rows.sort(key=lambda x:(-x.expected_match_utility,-x.expected_score_delta,x.discard))
    best=rows[0] if rows else None

    return {
        'match_state':asdict(match),
        'current_rank':_rank(match.scores,match.self_index),
        'recommended_discard':best.discard if best else None,
        'recommended_action':'maximize_match_ev' if best else None,
        'candidates':[asdict(x) for x in rows],
        'notice':(
            'v3.8 adds honba, riichi sticks, dealer continuation and last-round '
            'termination logic. Future-round utility is still heuristic and does not yet '
            'simulate full future hands or venue-specific end conditions.'
        ),
    }
