from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

from .tiles import parse_mpsz, format_tile
from .rules import RuleProfile, validate_counts_for_rules

NORTH_INDEX=30

@dataclass(frozen=True)
class VisibleState:
    counts: tuple[int,...]
    live_total: int
    source_counts: dict[str,int]

def build_visible_state(
    hand_counts: list[int],
    profile: RuleProfile,
    *,
    visible_tiles: Iterable[str]=(),
    dora_indicators: Iterable[str]=(),
    nuki_count: int=0,
) -> VisibleState:
    if nuki_count < 0 or nuki_count > 4:
        raise ValueError('nuki_count must be 0..4')

    counts=hand_counts.copy()
    source_counts={
        'hand':sum(hand_counts),
        'visible_tiles':0,
        'dora_indicators':0,
        'nuki':nuki_count,
    }

    def add_tokens(tokens, source):
        for token in tokens:
            c=parse_mpsz(token)
            source_counts[source]+=sum(c)
            for i,n in enumerate(c):
                counts[i]+=n
                if counts[i] > 4:
                    raise ValueError(
                        f'visible count exceeds four for {format_tile(i)} '
                        f'after adding {source}'
                    )

    add_tokens(visible_tiles,'visible_tiles')
    add_tokens(dora_indicators,'dora_indicators')

    if nuki_count:
        counts[NORTH_INDEX]+=nuki_count
        if counts[NORTH_INDEX] > 4:
            raise ValueError('north visible count exceeds four after nuki')

    validate_counts_for_rules(counts,profile)
    live_total=sum(max(0,4-counts[i]) for i in profile.allowed_tiles)
    return VisibleState(tuple(counts),live_total,source_counts)
