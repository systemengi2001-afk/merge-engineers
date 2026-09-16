from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache

from .shanten import calculate_shanten
from .analyzer import ukeire_for_13
from .ev_instant import estimate_instant

@dataclass(frozen=True)
class TransitionInstantResult:
    tenpai_probability: float
    win_probability: float
    expected_points: float
    average_win_points: float
    first_draw_states: int
    model: str = "transition_aware_instant_v2.9"

def _live_total(visible: tuple[int,...], allowed: tuple[int,...]) -> int:
    return sum(max(0,4-visible[i]) for i in allowed)

def _best_after_draw(
    counts14: list[int],
    visible_after_draw: list[int],
    allowed: tuple[int,...],
    remaining_draws: int,
    average_win_points_hint: float,
) -> tuple[float,float]:
    """Choose a discard from the actual 14-tile state efficiently.

    First compute only shanten for every unique discard. Ukeire is calculated
    only for discards that achieve the minimum shanten, avoiding the previous
    O(discard × 34 effective-tile scans) for obviously inferior candidates.
    """
    structural=[]
    for d in range(34):
        if counts14[d] <= 0:
            continue
        hand13=counts14.copy()
        hand13[d]-=1
        sh=int(calculate_shanten(hand13)["shanten"])
        structural.append((sh,d,hand13))

    if not structural:
        return 0.0,0.0

    min_sh=min(x[0] for x in structural)
    best_struct=[x for x in structural if x[0]==min_sh]

    if remaining_draws <= 0:
        return 0.0, (1.0 if min_sh <= 0 else 0.0)

    live=_live_total(tuple(visible_after_draw),allowed)
    best=(-1.0,-1.0)
    for sh,d,hand13 in best_struct:
        _,_,uke=ukeire_for_13(hand13,visible_after_draw,allowed)
        uke_total=sum(x.remaining for x in uke)
        est=estimate_instant(
            sh,uke_total,remaining_draws,live,
            average_win_points_hint=average_win_points_hint,
        )
        score=(est.win_probability,est.tenpai_probability)
        if score > best:
            best=score
    return best

def estimate_transition_aware(
    counts13: list[int],
    visible_counts: list[int],
    draws: int,
    *,
    allowed_tiles: set[int] | frozenset[int] | None=None,
    average_win_points_hint: float=5200.0,
) -> TransitionInstantResult:
    if draws < 0:
        raise ValueError("draws must be >= 0")

    allowed=tuple(sorted(allowed_tiles if allowed_tiles is not None else range(34)))
    current=calculate_shanten(counts13)
    shanten=int(current["shanten"])

    if draws == 0:
        return TransitionInstantResult(
            tenpai_probability=1.0 if shanten <= 0 else 0.0,
            win_probability=0.0,
            expected_points=0.0,
            average_win_points=average_win_points_hint,
            first_draw_states=0,
        )

    total=_live_total(tuple(visible_counts),allowed)
    if total <= 0:
        return TransitionInstantResult(
            tenpai_probability=1.0 if shanten <= 0 else 0.0,
            win_probability=0.0,
            expected_points=0.0,
            average_win_points=average_win_points_hint,
            first_draw_states=0,
        )

    win_prob=0.0
    tenpai_prob=0.0
    states=0

    for tile in allowed:
        live=max(0,4-visible_counts[tile])
        if live <= 0:
            continue
        states += 1
        p=live/total

        hand14=counts13.copy()
        hand14[tile]+=1
        visible2=visible_counts.copy()
        visible2[tile]+=1

        post_draw_shanten=int(calculate_shanten(hand14)["shanten"])
        if post_draw_shanten == -1:
            win_prob += p
            tenpai_prob += p
            continue

        cont_win,cont_tenpai=_best_after_draw(
            hand14,visible2,allowed,draws-1,average_win_points_hint
        )
        win_prob += p*max(0.0,cont_win)
        tenpai_prob += p*max(0.0,cont_tenpai)

    win_prob=max(0.0,min(1.0,win_prob))
    tenpai_prob=max(win_prob,min(1.0,tenpai_prob))
    if abs(win_prob-1.0) < 1e-12:
        win_prob=1.0
    if abs(tenpai_prob-1.0) < 1e-12:
        tenpai_prob=1.0
    if abs(win_prob) < 1e-12:
        win_prob=0.0
    if abs(tenpai_prob) < 1e-12:
        tenpai_prob=0.0
    return TransitionInstantResult(
        tenpai_probability=tenpai_prob,
        win_probability=win_prob,
        expected_points=win_prob*average_win_points_hint,
        average_win_points=average_win_points_hint,
        first_draw_states=states,
    )
