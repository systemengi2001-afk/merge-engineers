from __future__ import annotations
from dataclasses import dataclass
import math

from .shanten import calculate_shanten

@dataclass(frozen=True)
class InstantEVResult:
    tenpai_probability: float
    win_probability: float
    expected_points: float
    average_win_points: float
    model: str = "instant_heuristic_v1.2"


def _hypergeom_hit(total_live: int, outs: int, draws: int) -> float:
    if draws <= 0 or outs <= 0 or total_live <= 0:
        return 0.0
    outs=min(outs,total_live)
    miss=1.0
    for k in range(min(draws,total_live)):
        miss *= max(0.0,(total_live-outs-k)/(total_live-k))
    return max(0.0,min(1.0,1.0-miss))


def estimate_instant(shanten: int, ukeire_total: int, draws: int, total_live: int,
                     average_win_points_hint: float = 5200.0) -> InstantEVResult:
    # Product-facing fast estimate only. Precision engine replaces this asynchronously.
    if shanten <= 0:
        win=_hypergeom_hit(total_live, ukeire_total, draws)
        tenpai=1.0
    elif shanten == 1:
        tenpai=_hypergeom_hit(total_live, ukeire_total, draws)
        # Approximate chance to convert resulting tenpai to win in remaining horizon.
        win=tenpai * min(0.55, 0.11*max(0,draws-1))
    elif shanten == 2:
        p1=_hypergeom_hit(total_live, ukeire_total, draws)
        tenpai=p1 * min(0.45,0.09*max(0,draws-1))
        win=tenpai * min(0.35,0.07*max(0,draws-2))
    else:
        p1=_hypergeom_hit(total_live, ukeire_total, draws)
        tenpai=p1 * 0.12
        win=tenpai * 0.08
    ev=win*average_win_points_hint
    return InstantEVResult(tenpai,win,ev,average_win_points_hint)
