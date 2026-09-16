from __future__ import annotations

from dataclasses import dataclass
from math import ceil

TERMINALS = {0,8,9,17,18,26}
HONORS = set(range(27,34))
WINDS = {27,28,29,30}
DRAGONS = {31,32,33}
YAOCHU = TERMINALS | HONORS

@dataclass(frozen=True)
class ScoreConfig:
    dealer: bool = False
    round_wind: int = 27
    seat_wind: int = 28
    riichi: bool = True
    tsumo: bool = True
    dora_indicators: tuple[int, ...] = ()
    red_dora_count: int = 0
    players: int = 4
    tsumo_loss: bool = False
    nuki_dora_count: int = 0
    chip_count: int = 0
    chip_value_points: int = 0

@dataclass(frozen=True)
class ScoreResult:
    points: int
    han: int
    fu: int
    yaku: tuple[str, ...]
    dora: int
    yakuman: bool = False
    model: str = "closed_hand_score_beta_v1.6"
    base_points: int = 0
    bonus_points: int = 0

def _is_terminal_or_honor(i: int) -> bool:
    return i in YAOCHU

def _dora_from_indicator(ind: int) -> int:
    if ind < 27:
        base = (ind // 9) * 9
        rank = ind % 9
        return base + ((rank + 1) % 9)
    if 27 <= ind <= 30:
        return 27 + ((ind - 27 + 1) % 4)
    return 31 + ((ind - 31 + 1) % 3)

def _count_dora(counts: tuple[int,...], indicators: tuple[int,...]) -> int:
    return sum(counts[_dora_from_indicator(ind)] for ind in indicators)

def _ceil100(x: int) -> int:
    return ((x + 99)//100)*100

def _points_from_han_fu(han: int, fu: int, dealer: bool, tsumo: bool, players: int = 4, tsumo_loss: bool = False) -> int:
    if han <= 0:
        return 0
    if han >= 13: base = 8000
    elif han >= 11: base = 6000
    elif han >= 8: base = 4000
    elif han >= 6: base = 3000
    else:
        base = fu * (2 ** (han + 2))
        if han >= 5 or base >= 2000:
            base = 2000
    if tsumo:
        if players == 3 and tsumo_loss:
            # Tsumo-loss sanma keeps four-player per-opponent payments and simply
            # has one fewer payer. Dealer: two children each pay 2*base.
            # Non-dealer: dealer pays 2*base, other child pays base.
            if dealer:
                return _ceil100(base*2) * 2
            return _ceil100(base*2) + _ceil100(base)
        if dealer:
            return _ceil100(base*2) * (players-1)
        # For non-tsumo-loss sanma we use equalized total equivalent to yonma total.
        if players == 3:
            return _ceil100(base*2) + _ceil100(base)*2
        return _ceil100(base*2) + _ceil100(base)*2
    return _ceil100(base * (6 if dealer else 4))


def _with_bonus(base_points: int, cfg: ScoreConfig) -> tuple[int,int]:
    bonus=max(0,int(cfg.chip_count))*max(0,int(cfg.chip_value_points))
    return base_points + bonus, bonus

def _is_kokushi(c):
    req=(0,8,9,17,18,26,27,28,29,30,31,32,33)
    return sum(c)==14 and all(c[i]>=1 for i in req) and sum(c[i]>=2 for i in req)==1

def _is_chiitoi(c):
    return sum(c)==14 and sum(x==2 for x in c)==7

def _meld_dfs(arr,start,pair,melds):
    i=start
    while i<34 and arr[i]==0: i+=1
    if i==34:
        if len(melds)==4: yield pair,tuple(melds)
        return
    if len(melds)>=4: return
    if arr[i]>=3:
        arr[i]-=3; melds.append(("triplet",i))
        yield from _meld_dfs(arr,i,pair,melds)
        melds.pop(); arr[i]+=3
    if i<27 and i%9<=6 and arr[i+1] and arr[i+2]:
        arr[i]-=1;arr[i+1]-=1;arr[i+2]-=1;melds.append(("sequence",i))
        yield from _meld_dfs(arr,i,pair,melds)
        melds.pop();arr[i]+=1;arr[i+1]+=1;arr[i+2]+=1

def _decompositions(c):
    arr=list(c)
    for pair in range(34):
        if arr[pair]<2: continue
        arr[pair]-=2
        yield from _meld_dfs(arr,0,pair,[])
        arr[pair]+=2

def _wait_fu_options(pair, melds, winning_tile):
    """Return possible (wait_fu, wait_name) interpretations for the winning tile."""
    opts=[]
    if winning_tile is None:
        return [(0,"unknown")]
    if pair == winning_tile:
        opts.append((2,"tanki"))
    for kind,start in melds:
        if kind=="triplet" and start==winning_tile:
            opts.append((0,"shanpon"))
        elif kind=="sequence" and start <= winning_tile <= start+2:
            pos=winning_tile-start
            rank=start%9
            if pos==1:
                opts.append((2,"kanchan"))
            elif rank==0 and pos==2:
                opts.append((2,"penchan"))
            elif rank==6 and pos==0:
                opts.append((2,"penchan"))
            else:
                opts.append((0,"ryanmen"))
    return opts or [(0,"unknown")]

def _sequence_starts(melds):
    return [i for k,i in melds if k=="sequence"]

def _triplets(melds):
    return [i for k,i in melds if k=="triplet"]

def _yakuman_for_standard(c,pair,melds):
    trips=_triplets(melds)
    out=[]
    if len(trips)==4:
        out.append("suuankou")
    if DRAGONS.issubset(set(trips)):
        out.append("daisangen")
    if all(i in HONORS for i,n in enumerate(c) if n):
        out.append("tsuuiisou")
    if all(i in TERMINALS for i,n in enumerate(c) if n):
        out.append("chinroutou")
    return out

def _normal_yaku(c,pair,melds,cfg,wait_name):
    yaku=[]
    han=0
    seqs=_sequence_starts(melds)
    trips=_triplets(melds)

    if cfg.riichi:
        han+=1; yaku.append("riichi")
    if cfg.tsumo:
        han+=1; yaku.append("menzen_tsumo")
    if all(i not in YAOCHU for i,n in enumerate(c) if n):
        han+=1; yaku.append("tanyao")

    value_pair = pair in DRAGONS or pair==cfg.round_wind or pair==cfg.seat_wind
    if len(seqs)==4 and not value_pair and wait_name=="ryanmen":
        han+=1; yaku.append("pinfu")

    dupseq=sum(v//2 for v in {s:seqs.count(s) for s in set(seqs)}.values())
    if dupseq>=2:
        han+=3; yaku.append("ryanpeikou")
    elif dupseq==1:
        han+=1; yaku.append("iipeikou")

    for t in trips:
        if t in DRAGONS:
            han+=1; yaku.append("yakuhai_dragon")
        if t==cfg.round_wind:
            han+=1; yaku.append("yakuhai_round_wind")
        if t==cfg.seat_wind:
            han+=1; yaku.append("yakuhai_seat_wind")

    if len(trips)==4:
        han+=2; yaku.append("toitoi")
    if len(trips)>=3:
        han+=2; yaku.append("sanankou")

    # sanshoku doujun
    for r in range(7):
        if all(base+r in seqs for base in (0,9,18)):
            han+=2; yaku.append("sanshoku_doujun"); break

    # ittsuu
    for base in (0,9,18):
        if all(base+x in seqs for x in (0,3,6)):
            han+=2; yaku.append("ittsuu"); break

    # sanshoku doukou
    for r in range(9):
        if all(base+r in trips for base in (0,9,18)):
            han+=2; yaku.append("sanshoku_doukou"); break

    # shousangen
    dragon_trips=sum(t in DRAGONS for t in trips)
    if dragon_trips==2 and pair in DRAGONS:
        han+=2; yaku.append("shousangen")

    # honroutou
    if all(i in YAOCHU for i,n in enumerate(c) if n):
        han+=2; yaku.append("honroutou")

    # chanta / junchan
    groups=[("pair",pair),*melds]
    def group_has_terminal_or_honor(g):
        kind,x=g
        if kind in ("pair","triplet"):
            return x in YAOCHU
        ranks={x%9,(x+1)%9,(x+2)%9}
        return 0 in ranks or 8 in ranks
    if all(group_has_terminal_or_honor(g) for g in groups):
        has_honor=any(i in HONORS for i,n in enumerate(c) if n)
        has_seq=bool(seqs)
        if has_seq:
            if has_honor:
                han+=2; yaku.append("chanta")
            else:
                han+=3; yaku.append("junchan")

    suits={i//9 for i,n in enumerate(c[:27]) if n}
    has_honors=any(c[i] for i in HONORS)
    if len(suits)==1:
        if has_honors:
            han+=3; yaku.append("honitsu")
        else:
            han+=6; yaku.append("chinitsu")
    return han,yaku

def score_closed_hand(counts, cfg: ScoreConfig, winning_tile: int | None = None) -> ScoreResult:
    c=tuple(counts)
    if sum(c)!=14:
        raise ValueError("scoring requires exactly 14 tiles")
    dora=_count_dora(c,cfg.dora_indicators)+cfg.red_dora_count+cfg.nuki_dora_count

    if _is_kokushi(c):
        base_pts=_points_from_han_fu(13,0,cfg.dealer,cfg.tsumo,cfg.players,cfg.tsumo_loss)
        pts,bonus=_with_bonus(base_pts,cfg)
        return ScoreResult(pts,13,0,("kokushi_musou",),dora,True,base_points=base_pts,bonus_points=bonus)

    if _is_chiitoi(c):
        y=["chiitoitsu"]; han=2
        if cfg.riichi: han+=1;y.append("riichi")
        if cfg.tsumo: han+=1;y.append("menzen_tsumo")
        if all(i not in YAOCHU for i,n in enumerate(c) if n):
            han+=1;y.append("tanyao")
        suits={i//9 for i,n in enumerate(c[:27]) if n}
        has_honors=any(c[i] for i in HONORS)
        if len(suits)==1:
            if has_honors: han+=3;y.append("honitsu")
            else: han+=6;y.append("chinitsu")
        han+=dora
        base_pts=_points_from_han_fu(han,25,cfg.dealer,cfg.tsumo,cfg.players,cfg.tsumo_loss)
        pts,bonus=_with_bonus(base_pts,cfg)
        return ScoreResult(pts,han,25,tuple(y),dora,base_points=base_pts,bonus_points=bonus)

    best=None
    for pair,melds in _decompositions(c):
        yakuman=_yakuman_for_standard(c,pair,melds)
        if yakuman:
            mult=len(yakuman)
            base_pts=_points_from_han_fu(13,0,cfg.dealer,cfg.tsumo,cfg.players,cfg.tsumo_loss)*mult
            pts,bonus=_with_bonus(base_pts,cfg)
            cand=ScoreResult(pts,13*mult,0,tuple(yakuman),dora,True,base_points=base_pts,bonus_points=bonus)
            if best is None or cand.points>best.points: best=cand
            continue

        trips=_triplets(melds)
        for wait_fu,wait_name in _wait_fu_options(pair,melds,winning_tile):
            han,yaku=_normal_yaku(c,pair,melds,cfg,wait_name)
            # Dora are bonus han only after at least one yaku exists.
            if han<=0:
                continue
            han_total=han+dora

            pinfu="pinfu" in yaku
            if pinfu and cfg.tsumo:
                fu=20
            else:
                fu=20
                if cfg.tsumo:
                    fu+=2
                elif True:  # closed ron, reserved for future cfg.tsumo=False use
                    fu+=10
                if pair in DRAGONS: fu+=2
                if pair==cfg.round_wind: fu+=2
                if pair==cfg.seat_wind: fu+=2
                for t in trips:
                    fu += 8 if t in YAOCHU else 4  # concealed triplet
                fu += wait_fu
                fu=int(ceil(fu/10)*10)
                if fu==20 and not cfg.tsumo:
                    fu=30

            base_pts=_points_from_han_fu(han_total,fu,cfg.dealer,cfg.tsumo,cfg.players,cfg.tsumo_loss)
            pts,bonus=_with_bonus(base_pts,cfg)
            cand=ScoreResult(pts,han_total,fu,tuple(yaku),dora,base_points=base_pts,bonus_points=bonus)
            if best is None or (cand.points,cand.han,cand.fu)>(best.points,best.han,best.fu):
                best=cand

    return best or ScoreResult(0,0,0,tuple(),dora,base_points=0,bonus_points=0)
