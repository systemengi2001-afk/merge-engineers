from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from .shanten import calculate_shanten
from .scoring import ScoreConfig, score_closed_hand
from .dora_rules import FIVE_INDEXES, AkaDoraProfile

@dataclass(frozen=True)
class EVResult:
    draws:int; tenpai_probability:float; win_probability:float; expected_points:float; average_win_points:float
    model:str='self_draw_dual_metric_score_ev_dora_aware_v6.10'

def _draw_distribution(seen,allowed):
    live=[(i,4-seen[i]) for i in allowed if seen[i]<4]; total=sum(n for _,n in live)
    return [] if total<=0 else [(i,n/total) for i,n in live]

def estimate_score_ev(counts13:list[int], visible_counts:list[int], draws:int, score_config:ScoreConfig,
                      allowed_tiles:set[int]|None=None, red_hand_counts:tuple[int,int,int]=(0,0,0),
                      red_visible_counts:tuple[int,int,int]=(0,0,0), aka_profile:AkaDoraProfile|None=None)->EVResult:
    if draws<0: raise ValueError('draws must be >= 0')
    allowed=tuple(sorted(allowed_tiles if allowed_tiles is not None else range(34)))
    supply=aka_profile.red_supply if aka_profile else (0,0,0)

    @lru_cache(maxsize=None)
    def shanten_cached(hand):
        return int(calculate_shanten(hand)['shanten'])

    @lru_cache(maxsize=None)
    def dp(hand,seen,reds,seen_reds,left):
        sh=shanten_cached(hand); already=sh<=0
        if left==0: return 0.0,1.0 if already else 0.0,0.0
        dist=_draw_distribution(seen,allowed)
        if not dist: return 0.0,1.0 if already else 0.0,0.0
        pwin=pten=ev=0.0
        for tile,p_tile in dist:
            variants=[(False,1.0)]
            if tile in FIVE_INDEXES:
                si=FIVE_INDEXES.index(tile); remaining=4-seen[tile]
                red_left=min(max(0,supply[si]-seen_reds[si]),remaining)
                variants=[]
                if red_left: variants.append((True,red_left/remaining))
                if remaining-red_left: variants.append((False,(remaining-red_left)/remaining))
            for is_red,p_kind in variants:
                p=p_tile*p_kind; h14=list(hand); h14[tile]+=1; s2=list(seen); s2[tile]+=1
                r2=list(reds); sr2=list(seen_reds)
                if is_red:
                    si=FIVE_INDEXES.index(tile); r2[si]+=1; sr2[si]+=1
                if shanten_cached(tuple(h14))<0:
                    cfg=ScoreConfig(**{**score_config.__dict__,'red_dora_count':sum(r2)})
                    scored=score_closed_hand(h14,cfg,winning_tile=tile); w,t,e=1.0,1.0,float(scored.points)
                else:
                    # v6.7: shortest-path pruning.  For point-EV search we do not
                    # intentionally step backwards in shanten.  This mirrors the
                    # useful/unnecessary-tile graph idea used by high-speed solitaire
                    # EV engines and makes multi-draw dora-aware search practical.
                    discard_states=[]
                    min_shanten=None
                    for d in range(34):
                        if h14[d]==0: continue
                        h13=h14.copy(); h13[d]-=1
                        ds=shanten_cached(tuple(h13))
                        if min_shanten is None or ds<min_shanten:
                            min_shanten=ds; discard_states=[(d,h13)]
                        elif ds==min_shanten:
                            discard_states.append((d,h13))
                    best=None
                    for d,h13 in discard_states:
                        rd=list(r2)
                        if d in FIVE_INDEXES:
                            si=FIVE_INDEXES.index(d); normal=h14[d]-r2[si]
                            if normal<=0 and rd[si]>0: rd[si]-=1
                        w2,t2,e2=dp(tuple(h13),tuple(s2),tuple(rd),tuple(sr2),left-1)
                        if min_shanten<=0: t2=1.0
                        # v6.9: expected points is the primary continuation objective.
                        # e2 already combines eventual win probability with the scored value of
                        # each winning branch, including ordinary/aka dora.  Win/tenpai probability
                        # remain tie-breakers so equally-valued lines prefer the easier hand.
                        cand=(e2,w2,t2)
                        if best is None or cand>best[0]: best=(cand,w2,t2,e2)
                    _,w,t,e=best
                pwin+=p*w; pten+=p*t; ev+=p*e
        if already: pten=1.0
        return pwin,pten,ev
    w,t,e=dp(tuple(counts13),tuple(visible_counts),tuple(red_hand_counts),tuple(red_visible_counts),draws)
    return EVResult(draws,max(0,min(1,t)),max(0,min(1,w)),e,e/w if w>0 else 0.0)
