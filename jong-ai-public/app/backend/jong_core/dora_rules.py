"""Dora/red-five rule primitives for JONG mathematical EV.

Tile identity stays explicit for aka dora even though shanten uses 34-type counts.
"""
from __future__ import annotations
from dataclasses import dataclass

FIVE_INDEXES=(4,13,22)

@dataclass(frozen=True)
class AkaDoraProfile:
    id: str
    red_supply: tuple[int,int,int]  # physical red copies of 5m,5p,5s

PROFILES={
    "none": AkaDoraProfile("none",(0,0,0)),
    "one_each": AkaDoraProfile("one_each",(1,1,1)),
    # Osaka-style option requested for sanma: every physical five in the live tile set is red.
    "sanma_all_fives": AkaDoraProfile("sanma_all_fives",(0,4,4)),
}

def get_aka_profile(profile: str, players: int, red_supply: tuple[int,int,int] | None = None) -> AkaDoraProfile:
    if red_supply is not None:
        if len(red_supply) != 3 or any((not isinstance(x, int)) or x < 0 or x > 4 for x in red_supply):
            raise ValueError("red_supply must be three integers in 0..4 for 5m/5p/5s")
        if players == 3 and red_supply[0] != 0:
            raise ValueError("sanma red_supply must have 0 red 5m because 5m is not in the tile set")
        return AkaDoraProfile("custom", tuple(red_supply))
    if profile not in PROFILES: raise ValueError(f"unknown aka profile: {profile}")
    p=PROFILES[profile]
    if profile=="sanma_all_fives" and players!=3:
        raise ValueError("sanma_all_fives requires three-player mode")
    return p

def red_counts_from_mpsz(text: str) -> tuple[int,int,int]:
    """Count explicit red fives. Accepts legacy 0s and product syntax r5s."""
    import re
    compact=text.strip().replace(" ","")
    out=[0,0,0]
    # Product syntax: r5m/r5p/r5s. Strip before compact MPSZ scan.
    for suit in "mps":
        pat=re.compile(r"r5"+suit, re.I)
        hits=len(pat.findall(compact)); out["mps".index(suit)]+=hits
        compact=pat.sub("",compact)
    digits=[]
    for ch in compact:
        if ch.isdigit(): digits.append(ch); continue
        if ch in "mps":
            si="mps".index(ch); out[si]+=sum(d=="0" for d in digits)
        digits=[]
    return tuple(out)

def validate_red_hand(counts: list[int], red_counts: tuple[int,int,int], p: AkaDoraProfile) -> None:
    for si,idx in enumerate(FIVE_INDEXES):
        if red_counts[si] > counts[idx]: raise ValueError("red five count exceeds five count")
        if red_counts[si] > p.red_supply[si]: raise ValueError(f"hand contains more red fives than profile {p.id}")
        if p.id=="sanma_all_fives" and counts[idx] != red_counts[si]:
            if idx in (13,22): raise ValueError("sanma_all_fives requires every 5p/5s to be red; write them as 0p/0s")

def red_after_best_discard(tile_index:int, counts_before:list[int], reds:tuple[int,int,int]) -> tuple[int,int,int]:
    """Discard a non-red five first when both identities exist; preserves valuable aka tile."""
    out=list(reds)
    if tile_index in FIVE_INDEXES:
        si=FIVE_INDEXES.index(tile_index)
        normal=counts_before[tile_index]-reds[si]
        if normal<=0 and out[si]>0: out[si]-=1
    return tuple(out)


def validate_visible_reds(red_visible_counts: tuple[int,int,int], p: AkaDoraProfile) -> None:
    """Reject physically impossible aka visibility before EV calculation."""
    for si, n in enumerate(red_visible_counts):
        if n < 0 or n > p.red_supply[si]:
            suit = "mps"[si]
            raise ValueError(f"visible red 5{suit} count exceeds rule supply ({n}>{p.red_supply[si]})")

def red_normal_remaining_for_five(tile_index:int, visible_total:int, visible_red:int, p:AkaDoraProfile) -> tuple[int,int]:
    """Return live red/normal copies for a five, consistent with the physical rule supply."""
    if tile_index not in FIVE_INDEXES:
        return (0, max(0, 4-visible_total))
    si=FIVE_INDEXES.index(tile_index)
    red_left=max(0, p.red_supply[si]-visible_red)
    total_left=max(0, 4-visible_total)
    red_left=min(red_left,total_left)
    return red_left, total_left-red_left
