from __future__ import annotations
from dataclasses import dataclass
from math import ceil
from typing import Iterable

from .tiles import parse_mpsz
from .open_hand import OpenMeld
from .scoring import (
    DRAGONS, HONORS, TERMINALS, YAOCHU,
    ScoreConfig, ScoreResult, _count_dora, _ceil100,
    _points_from_han_fu, _with_bonus,
)

@dataclass(frozen=True)
class OpenScoreInput:
    concealed_complete_hand: str
    melds: tuple[OpenMeld, ...]
    winning_tile: str | None = None

def _single_index(token: str | None) -> int | None:
    if token is None:
        return None
    c=parse_mpsz(token)
    if sum(c)!=1:
        raise ValueError(f"expected one tile: {token}")
    return next(i for i,n in enumerate(c) if n)

def _is_terminal_or_honor(i: int) -> bool:
    return i in YAOCHU

def _all_tiles(concealed: list[int], melds: tuple[OpenMeld,...]) -> list[int]:
    c=concealed.copy()
    for m in melds:
        i=m.tile_index()
        c[i] += 3 if m.kind=='pon' else 4
    return c

def _concealed_decompositions(counts: list[int], meld_slots: int):
    """Decompose concealed part into pair + remaining closed melds.

    The number of needed concealed melds is 4 - open meld count.
    """
    needed=4-meld_slots
    arr=counts.copy()

    def dfs(a,start,pair,melds):
        i=start
        while i<34 and a[i]==0:
            i+=1
        if i==34:
            if pair is not None and len(melds)==needed:
                yield pair,tuple(melds)
            return
        if len(melds)>needed:
            return
        if pair is None and a[i]>=2:
            a[i]-=2
            yield from dfs(a,i,i,melds)
            a[i]+=2
        if len(melds)<needed and a[i]>=3:
            a[i]-=3; melds.append(('triplet',i))
            yield from dfs(a,i,pair,melds)
            melds.pop(); a[i]+=3
        if len(melds)<needed and i<27 and i%9<=6 and a[i+1] and a[i+2]:
            a[i]-=1;a[i+1]-=1;a[i+2]-=1
            melds.append(('sequence',i))
            yield from dfs(a,i,pair,melds)
            melds.pop()
            a[i]+=1;a[i+1]+=1;a[i+2]+=1

    yield from dfs(arr,0,None,[])

def _wait_fu(pair, closed_melds, winning_tile):
    if winning_tile is None:
        return [(0,'unknown')]
    out=[]
    if pair==winning_tile:
        out.append((2,'tanki'))
    for kind,start in closed_melds:
        if kind=='triplet' and start==winning_tile:
            out.append((0,'shanpon'))
        elif kind=='sequence' and start<=winning_tile<=start+2:
            pos=winning_tile-start
            rank=start%9
            if pos==1:
                out.append((2,'kanchan'))
            elif rank==0 and pos==2:
                out.append((2,'penchan'))
            elif rank==6 and pos==0:
                out.append((2,'penchan'))
            else:
                out.append((0,'ryanmen'))
    return out or [(0,'unknown')]

def _open_yaku(all_counts, pair, closed_melds, open_melds, cfg, wait_name, open_tanyao):
    """Subset of open-hand yaku with correct open reductions where applicable."""
    yaku=[]
    han=0

    open_trips=[m.tile_index() for m in open_melds]
    closed_trips=[i for k,i in closed_melds if k=='triplet']
    trips=open_trips+closed_trips
    seqs=[i for k,i in closed_melds if k=='sequence']

    # yakuhai
    for t in trips:
        if t in DRAGONS:
            han+=1; yaku.append('yakuhai_dragon')
        if t==cfg.round_wind:
            han+=1; yaku.append('yakuhai_round_wind')
        if t==cfg.seat_wind:
            han+=1; yaku.append('yakuhai_seat_wind')

    # tanyao only if profile allows it; caller controls via cfg.open_tanyao if present
    if open_tanyao and all(i not in YAOCHU for i,n in enumerate(all_counts) if n):
        han+=1; yaku.append('tanyao')

    if len(trips)==4:
        han+=2; yaku.append('toitoi')

    # sanshoku doukou
    for r in range(9):
        if all(base+r in trips for base in (0,9,18)):
            han+=2; yaku.append('sanshoku_doukou'); break

    dragon_trips=sum(t in DRAGONS for t in trips)
    if dragon_trips==2 and pair in DRAGONS:
        han+=2; yaku.append('shousangen')

    # honroutou
    if all(i in YAOCHU for i,n in enumerate(all_counts) if n):
        han+=2; yaku.append('honroutou')

    # flushes (reduced when open)
    suits={i//9 for i,n in enumerate(all_counts[:27]) if n}
    has_honors=any(all_counts[i] for i in HONORS)
    if len(suits)==1:
        if has_honors:
            han+=2; yaku.append('honitsu')
        else:
            han+=5; yaku.append('chinitsu')

    # Chanta/Junchan: open values reduced by 1.
    groups=[('pair',pair),*closed_melds]
    groups += [('triplet',m.tile_index()) for m in open_melds]
    def has_term_or_honor(g):
        kind,x=g
        if kind in ('pair','triplet'):
            return x in YAOCHU
        ranks={x%9,(x+1)%9,(x+2)%9}
        return 0 in ranks or 8 in ranks
    if groups and all(has_term_or_honor(g) for g in groups):
        has_honor=any(i in HONORS for i,n in enumerate(all_counts) if n)
        has_seq=any(k=='sequence' for k,_ in closed_melds)
        if has_seq:
            if has_honor:
                han+=1; yaku.append('chanta')
            else:
                han+=2; yaku.append('junchan')

    # ittsuu/sanshoku doujun can only be completed by closed sequences in this
    # representation because chi is not supported in Osaka sanma.
    for base in (0,9,18):
        if all(base+x in seqs for x in (0,3,6)):
            han+=1; yaku.append('ittsuu'); break
    for r in range(7):
        if all(base+r in seqs for base in (0,9,18)):
            han+=1; yaku.append('sanshoku_doujun'); break

    return han,yaku

def score_open_hand(
    concealed_complete_hand: str,
    melds: Iterable[OpenMeld],
    cfg: ScoreConfig,
    *,
    winning_tile: str | None=None,
    open_tanyao: bool=True,
) -> ScoreResult:
    melds=tuple(melds)
    if not melds:
        raise ValueError('open scoring requires at least one meld')
    if len(melds)>4:
        raise ValueError('too many melds')
    for m in melds:
        if m.kind not in {'pon','kan'}:
            raise ValueError('open scoring currently supports pon/kan only')

    concealed=parse_mpsz(concealed_complete_hand)
    expected=14 - 3*len(melds)
    if sum(concealed)!=expected:
        raise ValueError(
            f'concealed tile count must be {expected} with {len(melds)} open meld(s); got {sum(concealed)}'
        )

    all_counts=_all_tiles(concealed,melds)
    win_i=_single_index(winning_tile)
    dora=_count_dora(tuple(all_counts),cfg.dora_indicators)+cfg.red_dora_count+cfg.nuki_dora_count

    best=None
    for pair,closed_melds in _concealed_decompositions(concealed,len(melds)):
        for wait_fu,wait_name in _wait_fu(pair,closed_melds,win_i):
            han,yaku=_open_yaku(all_counts,pair,closed_melds,melds,cfg,wait_name,open_tanyao)
            if han<=0:
                continue
            han_total=han+dora

            fu=20
            # Open ron minimum and tsumo handling.
            if cfg.tsumo:
                fu+=2
            if pair in DRAGONS: fu+=2
            if pair==cfg.round_wind: fu+=2
            if pair==cfg.seat_wind: fu+=2

            # Closed triplets are concealed; open pon/kan use open fu.
            for k,t in closed_melds:
                if k=='triplet':
                    fu += 8 if t in YAOCHU else 4
            for m in melds:
                t=m.tile_index()
                if m.kind=='pon':
                    fu += 4 if t in YAOCHU else 2
                else:  # open kan
                    fu += 16 if t in YAOCHU else 8
            fu += wait_fu
            fu=int(ceil(fu/10)*10)
            if fu==20:
                fu=30

            base_pts=_points_from_han_fu(
                han_total,fu,cfg.dealer,cfg.tsumo,cfg.players,cfg.tsumo_loss
            )
            pts,bonus=_with_bonus(base_pts,cfg)
            cand=ScoreResult(
                pts,han_total,fu,tuple(yaku),dora,
                base_points=base_pts,bonus_points=bonus,
                model='open_hand_score_v1.9'
            )
            if best is None or (cand.points,cand.han,cand.fu)>(best.points,best.han,best.fu):
                best=cand

    return best or ScoreResult(
        0,0,0,tuple(),dora,base_points=0,bonus_points=0,
        model='open_hand_score_v1.9'
    )
