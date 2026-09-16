from __future__ import annotations

from dataclasses import dataclass, asdict
from functools import lru_cache
from math import prod

from .shanten import calculate_shanten
from .tiles import format_tile

@dataclass
class ProbabilityResult:
    draws: int
    tenpai_probability: float
    win_probability: float
    model: str

def _draw_distribution(visible: tuple[int, ...], allowed: tuple[int, ...]) -> list[tuple[int, float]]:
    remaining = [(i, 4 - visible[i]) for i in allowed if visible[i] < 4]
    total = sum(n for _, n in remaining)
    if total <= 0:
        return []
    return [(i, n / total) for i, n in remaining]

def estimate_probabilities(
    counts13: list[int],
    visible_counts: list[int],
    draws: int,
    allowed_tiles: set[int] | None = None,
) -> ProbabilityResult:
    """Exact finite-horizon draw/discard DP under a self-draw model.

    Assumptions for v0.2:
    - Opponents, calls and ron are not modeled.
    - After every non-winning draw, the discard is chosen to maximize
      (win probability, then tenpai probability) over the remaining horizon.
    - Visible counts are removed from the live wall.
    - Drawing a tile removes that physical copy from the live wall even if
      the tile is later discarded.
    """
    if draws < 0:
        raise ValueError("draws must be >= 0")
    allowed = tuple(sorted(allowed_tiles if allowed_tiles is not None else range(34)))
    base_visible = tuple(visible_counts)

    @lru_cache(maxsize=None)
    def dp(hand: tuple[int, ...], seen: tuple[int, ...], left: int) -> tuple[float, float]:
        sh = int(calculate_shanten(hand)["shanten"])
        already_tenpai = sh <= 0
        if sh < 0:
            return 1.0, 1.0
        if left == 0:
            return (0.0, 1.0 if already_tenpai else 0.0)

        dist = _draw_distribution(seen, allowed)
        if not dist:
            return (0.0, 1.0 if already_tenpai else 0.0)

        p_win = 0.0
        p_tenpai = 0.0
        for tile, p in dist:
            h14 = list(hand); h14[tile] += 1
            s2 = list(seen); s2[tile] += 1
            draw_sh = int(calculate_shanten(h14)["shanten"])
            if draw_sh < 0:
                w, t = 1.0, 1.0
            else:
                best = (-1.0, -1.0)
                for d in range(34):
                    if h14[d] == 0:
                        continue
                    h13 = h14.copy(); h13[d] -= 1
                    w2, t2 = dp(tuple(h13), tuple(s2), left - 1)
                    # Reaching tenpai at this decision point counts as tenpai success.
                    now_t = int(calculate_shanten(h13)["shanten"]) <= 0
                    candidate = (w2, max(t2, 1.0 if now_t else 0.0))
                    if candidate > best:
                        best = candidate
                w, t = best
            p_win += p * w
            p_tenpai += p * t

        if already_tenpai:
            p_tenpai = 1.0
        return p_win, p_tenpai

    w, t = dp(tuple(counts13), base_visible, draws)
    return ProbabilityResult(
        draws=draws,
        tenpai_probability=max(0.0, min(1.0, t)),
        win_probability=max(0.0, min(1.0, w)),
        model="self_draw_optimal_discard_dp_v0.2",
    )
