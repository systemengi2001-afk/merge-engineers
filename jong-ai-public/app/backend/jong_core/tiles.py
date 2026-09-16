from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

SUITS = "mpsz"
HONOR_NAMES = ["1z", "2z", "3z", "4z", "5z", "6z", "7z"]

class TileParseError(ValueError):
    pass


def tile_index(suit: str, rank: int) -> int:
    if suit not in SUITS:
        raise TileParseError(f"unknown suit: {suit}")
    if suit == "z":
        if not 1 <= rank <= 7:
            raise TileParseError("honor rank must be 1..7")
        return 27 + rank - 1
    if rank == 0:
        rank = 5
    if not 1 <= rank <= 9:
        raise TileParseError("suited rank must be 0..9 (0 = red five)")
    offset = {"m": 0, "p": 9, "s": 18}[suit]
    return offset + rank - 1


def format_tile(index: int) -> str:
    if not 0 <= index < 34:
        raise ValueError(index)
    if index < 9:
        return f"{index + 1}m"
    if index < 18:
        return f"{index - 8}p"
    if index < 27:
        return f"{index - 17}s"
    return f"{index - 26}z"


def parse_mpsz(text: str) -> list[int]:
    """Parse compact MPSZ text into a 34-count array.

    Examples:
        123m405p77z
        0m means red 5m and is normalized to 5m for calculation.
    """
    text = text.strip().replace(" ", "")
    # r5s is the product-facing explicit red-five syntax; normalize identity to 5s
    # for 34-type structural calculation while dora_rules retains the red attribute.
    import re
    text = re.sub(r"r5([mps])", r"5\1", text, flags=re.I)
    if not text:
        raise TileParseError("empty hand")
    counts = [0] * 34
    digits: list[str] = []
    for ch in text:
        if ch.isdigit():
            digits.append(ch)
            continue
        if ch not in SUITS:
            raise TileParseError(f"invalid character: {ch}")
        if not digits:
            raise TileParseError(f"missing digits before suit {ch}")
        for d in digits:
            rank = int(d)
            if ch == "z" and rank == 0:
                raise TileParseError("red honor does not exist")
            idx = tile_index(ch, rank)
            counts[idx] += 1
            if counts[idx] > 4:
                raise TileParseError(f"more than four copies of {format_tile(idx)}")
        digits.clear()
    if digits:
        raise TileParseError("trailing digits without suit")
    return counts


def counts_to_tiles(counts: Iterable[int]) -> list[str]:
    out: list[str] = []
    for i, n in enumerate(counts):
        out.extend([format_tile(i)] * n)
    return out


def total_tiles(counts: Iterable[int]) -> int:
    return sum(counts)
