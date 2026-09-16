from __future__ import annotations

from functools import lru_cache
from typing import Sequence

TERMINAL_HONORS = (0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32, 33)


def chiitoitsu_shanten(counts: Sequence[int]) -> int:
    pairs = sum(1 for n in counts if n >= 2)
    unique = sum(1 for n in counts if n > 0)
    return 6 - pairs + max(0, 7 - unique)


def kokushi_shanten(counts: Sequence[int]) -> int:
    unique = sum(1 for i in TERMINAL_HONORS if counts[i] > 0)
    pair = any(counts[i] >= 2 for i in TERMINAL_HONORS)
    return 13 - unique - (1 if pair else 0)


def normal_shanten(counts: Sequence[int]) -> int:
    """Exact shanten for a closed standard hand using DFS decomposition.

    Returns -1 for a completed standard hand, 0 for tenpai.
    Suitable for MVP correctness; later may be replaced with a table-driven Rust implementation.
    """
    tiles = tuple(counts)

    @lru_cache(maxsize=None)
    def dfs(state: tuple[int, ...], idx: int, melds: int, taatsu: int, pair: int) -> int:
        # skip zeros
        while idx < 34 and state[idx] == 0:
            idx += 1
        if idx >= 34:
            t = min(taatsu, 4 - melds)
            return 8 - melds * 2 - t - pair

        best = 8
        arr = list(state)

        # discard isolated tile from decomposition search
        arr[idx] -= 1
        best = min(best, dfs(tuple(arr), idx, melds, taatsu, pair))
        arr[idx] += 1

        # triplet
        if arr[idx] >= 3 and melds < 4:
            arr[idx] -= 3
            best = min(best, dfs(tuple(arr), idx, melds + 1, taatsu, pair))
            arr[idx] += 3

        # sequence
        if idx < 27 and idx % 9 <= 6 and arr[idx + 1] and arr[idx + 2] and melds < 4:
            arr[idx] -= 1; arr[idx + 1] -= 1; arr[idx + 2] -= 1
            best = min(best, dfs(tuple(arr), idx, melds + 1, taatsu, pair))
            arr[idx] += 1; arr[idx + 1] += 1; arr[idx + 2] += 1

        # pair as head
        if arr[idx] >= 2 and pair == 0:
            arr[idx] -= 2
            best = min(best, dfs(tuple(arr), idx, melds, taatsu, 1))
            arr[idx] += 2

        if taatsu < 4:
            # pair as taatsu
            if arr[idx] >= 2:
                arr[idx] -= 2
                best = min(best, dfs(tuple(arr), idx, melds, taatsu + 1, pair))
                arr[idx] += 2

            # ryanmen/penchan shape
            if idx < 27 and idx % 9 <= 7 and arr[idx + 1]:
                arr[idx] -= 1; arr[idx + 1] -= 1
                best = min(best, dfs(tuple(arr), idx, melds, taatsu + 1, pair))
                arr[idx] += 1; arr[idx + 1] += 1

            # kanchan shape
            if idx < 27 and idx % 9 <= 6 and arr[idx + 2]:
                arr[idx] -= 1; arr[idx + 2] -= 1
                best = min(best, dfs(tuple(arr), idx, melds, taatsu + 1, pair))
                arr[idx] += 1; arr[idx + 2] += 1

        return best

    return dfs(tiles, 0, 0, 0, 0)


def calculate_shanten(counts: Sequence[int]) -> dict[str, int | str]:
    normal = normal_shanten(counts)
    chiitoi = chiitoitsu_shanten(counts)
    kokushi = kokushi_shanten(counts)
    values = {"normal": normal, "chiitoitsu": chiitoi, "kokushi": kokushi}
    kind = min(values, key=values.get)
    return {
        "shanten": values[kind],
        "best_type": kind,
        **values,
    }


def normal_shanten_with_open_melds(counts: Sequence[int], open_meld_count: int) -> int:
    """Standard-hand shanten with a fixed number of already completed open melds.

    Chiitoitsu and kokushi are intentionally excluded once the hand is open.
    `counts` contains only concealed tiles. An open pon/chi/kan contributes one
    completed meld regardless of its physical tile count.
    """
    if not 0 <= open_meld_count <= 4:
        raise ValueError("open_meld_count must be 0..4")
    tiles = tuple(counts)

    @lru_cache(maxsize=None)
    def dfs(state: tuple[int, ...], idx: int, melds: int, taatsu: int, pair: int) -> int:
        while idx < 34 and state[idx] == 0:
            idx += 1
        if idx >= 34:
            t = min(taatsu, 4 - melds)
            return 8 - melds * 2 - t - pair

        best = 8
        arr = list(state)

        arr[idx] -= 1
        best = min(best, dfs(tuple(arr), idx, melds, taatsu, pair))
        arr[idx] += 1

        if arr[idx] >= 3 and melds < 4:
            arr[idx] -= 3
            best = min(best, dfs(tuple(arr), idx, melds + 1, taatsu, pair))
            arr[idx] += 3

        if idx < 27 and idx % 9 <= 6 and arr[idx + 1] and arr[idx + 2] and melds < 4:
            arr[idx] -= 1; arr[idx + 1] -= 1; arr[idx + 2] -= 1
            best = min(best, dfs(tuple(arr), idx, melds + 1, taatsu, pair))
            arr[idx] += 1; arr[idx + 1] += 1; arr[idx + 2] += 1

        if arr[idx] >= 2 and pair == 0:
            arr[idx] -= 2
            best = min(best, dfs(tuple(arr), idx, melds, taatsu, 1))
            arr[idx] += 2

        if taatsu < 4 - open_meld_count:
            if arr[idx] >= 2:
                arr[idx] -= 2
                best = min(best, dfs(tuple(arr), idx, melds, taatsu + 1, pair))
                arr[idx] += 2

            if idx < 27 and idx % 9 <= 7 and arr[idx + 1]:
                arr[idx] -= 1; arr[idx + 1] -= 1
                best = min(best, dfs(tuple(arr), idx, melds, taatsu + 1, pair))
                arr[idx] += 1; arr[idx + 1] += 1

            if idx < 27 and idx % 9 <= 6 and arr[idx + 2]:
                arr[idx] -= 1; arr[idx + 2] -= 1
                best = min(best, dfs(tuple(arr), idx, melds, taatsu + 1, pair))
                arr[idx] += 1; arr[idx + 2] += 1

        return best

    return dfs(tiles, 0, open_meld_count, 0, 0)
