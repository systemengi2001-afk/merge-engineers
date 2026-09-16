from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable

from .tiles import parse_mpsz, format_tile, total_tiles
from .shanten import calculate_shanten, normal_shanten_with_open_melds
from .analyzer import ukeire_for_13
from .ev_instant import estimate_instant
from .open_hand import OpenMeld, analyze_open_yaku_routes
from .rules import get_ruleset, validate_counts_for_rules
from .visible_state import build_visible_state
from .kan_decision import _expected_kandora_han


@dataclass(frozen=True)
class SelfKanActionResult:
    action: str
    tile: str | None
    legal: bool
    reason: str
    discard: str | None
    shanten: int
    ukeire_total: int
    tenpai_probability: float
    win_probability: float
    expected_points: float
    rinshan_win_probability: float
    expected_kandora_han: float
    model: str = 'self_kan_decision_v3.3'


def _counts_text(counts: list[int]) -> str:
    return ''.join(format_tile(i)*n for i,n in enumerate(counts) if n)


def _open_ukeire(
    concealed_counts: list[int],
    visible_counts: list[int],
    *,
    meld_count: int,
    allowed_tiles: set[int] | frozenset[int],
) -> tuple[int,int]:
    sh=normal_shanten_with_open_melds(concealed_counts,meld_count)
    uke=0
    for i in allowed_tiles:
        remaining=4-visible_counts[i]
        if remaining <= 0:
            continue
        concealed_counts[i]+=1
        nxt=normal_shanten_with_open_melds(concealed_counts,meld_count)
        concealed_counts[i]-=1
        if nxt < sh:
            uke += remaining
    return sh,uke


def _best_discard_state(
    counts14: list[int],
    visible_counts: list[int],
    *,
    meld_count: int,
    allowed_tiles: set[int] | frozenset[int],
    draws: int,
    total_live: int,
    average_win_points: float,
) -> tuple[int,int,int,object] | None:
    best=None
    for d in allowed_tiles:
        if counts14[d] <= 0:
            continue
        post=counts14.copy()
        post[d]-=1
        if meld_count:
            sh,uke=_open_ukeire(
                post,visible_counts,
                meld_count=meld_count,
                allowed_tiles=allowed_tiles,
            )
        else:
            sh,_,tiles=ukeire_for_13(post,visible_counts,allowed_tiles)
            uke=sum(x.remaining for x in tiles)
        est=estimate_instant(
            sh,uke,draws,total_live,
            average_win_points_hint=average_win_points,
        )
        key=(est.expected_points,est.win_probability,est.tenpai_probability,-sh,uke)
        if best is None or key > best[0]:
            best=(key,d,sh,uke,est)
    if best is None:
        return None
    _,d,sh,uke,est=best
    return d,sh,uke,est


def _visible_with_existing_melds(
    counts: list[int],
    profile,
    melds: tuple[OpenMeld,...],
    visible_tiles: Iterable[str],
    dora_indicators: Iterable[str],
    nuki_count: int,
):
    extra=list(visible_tiles)
    for m in melds:
        extra.extend([m.tile]*(4 if m.kind=='kan' else 3))
    return build_visible_state(
        counts,profile,
        visible_tiles=extra,
        dora_indicators=dora_indicators,
        nuki_count=nuki_count,
    )


def _all_committed_counts(concealed: list[int], melds: tuple[OpenMeld,...]) -> list[int]:
    c=concealed.copy()
    for m in melds:
        c[m.tile_index()] += 4 if m.kind=='kan' else 3
    return c


def _rinshan_branch(
    after_kan_concealed: list[int],
    melds_after: tuple[OpenMeld,...],
    visible_before_rinshan: list[int],
    *,
    profile,
    draws: int,
    average_win_points: float,
) -> tuple[float,float,float,float,str | None,int,int,float]:
    """Return EV/win/tenpai/rinshan-win/best-discard/shanten/ukeire/expected-kandora."""
    all_counts=_all_committed_counts(after_kan_concealed,melds_after)
    expected_kandora=_expected_kandora_han(
        all_counts,visible_before_rinshan,set(profile.allowed_tiles)
    )
    avg_points=average_win_points*min(4.0,2.0**expected_kandora)

    live=[(i,max(0,4-visible_before_rinshan[i]))
          for i in profile.allowed_tiles if visible_before_rinshan[i] < 4]
    total=sum(n for _,n in live)
    if total <= 0:
        sh=normal_shanten_with_open_melds(after_kan_concealed,len(melds_after))
        return 0.0,0.0,1.0 if sh<=0 else 0.0,0.0,None,sh,0,expected_kandora

    ev=win=ten=rinshan=0.0
    representative=None

    for tile,n in live:
        p=n/total
        h=after_kan_concealed.copy()
        h[tile]+=1
        seen=visible_before_rinshan.copy()
        seen[tile]+=1

        sh14=normal_shanten_with_open_melds(h,len(melds_after))
        if sh14 < 0:
            # Exact yaku/closed-kan handling is deferred; use the same calibrated
            # average-points layer for immediate rinshan completion.
            ev += p*avg_points
            win += p
            ten += p
            rinshan += p
            continue

        best=_best_discard_state(
            h,seen,
            meld_count=len(melds_after),
            allowed_tiles=profile.allowed_tiles,
            draws=draws,
            total_live=max(0,total-1),
            average_win_points=avg_points,
        )
        if best is None:
            continue
        d,sh,uke,est=best
        ev += p*est.expected_points
        win += p*est.win_probability
        ten += p*est.tenpai_probability
        candidate=(est.expected_points,d,sh,uke)
        if representative is None or candidate[0] > representative[0]:
            representative=candidate

    if representative:
        _,d,sh,uke=representative
        discard=format_tile(d)
    else:
        discard=None
        sh=normal_shanten_with_open_melds(after_kan_concealed,len(melds_after))
        uke=0

    return (
        ev,
        max(0.0,min(1.0,win)),
        max(0.0,min(1.0,ten)),
        max(0.0,min(1.0,rinshan)),
        discard,sh,uke,expected_kandora
    )


def evaluate_self_kan_decision(
    concealed_hand: str,
    *,
    existing_melds: Iterable[OpenMeld]=(),
    ruleset: str='osaka_sanma_v1',
    round_wind: str='1z',
    seat_wind: str='2z',
    visible_tiles: Iterable[str]=(),
    dora_indicators: Iterable[str]=(),
    nuki_count: int=0,
    draws: int=3,
    average_win_points_closed: float=5200.0,
    average_win_points_open: float=3900.0,
) -> dict:
    """Compare normal discard vs available ankan / kakan options on own turn."""
    if draws < 1:
        raise ValueError('draws must be >= 1')

    profile=get_ruleset(ruleset,None)
    melds=tuple(existing_melds)
    counts=parse_mpsz(concealed_hand)
    validate_counts_for_rules(counts,profile)

    expected_concealed=14-3*len(melds)
    if total_tiles(counts) != expected_concealed:
        raise ValueError(
            f'concealed hand must contain {expected_concealed} tiles on own turn '
            f'with {len(melds)} meld(s); got {total_tiles(counts)}'
        )

    state=_visible_with_existing_melds(
        counts,profile,melds,visible_tiles,dora_indicators,nuki_count
    )
    visible=list(state.counts)

    baseline=_best_discard_state(
        counts,visible,
        meld_count=len(melds),
        allowed_tiles=profile.allowed_tiles,
        draws=draws,
        total_live=state.live_total,
        average_win_points=(average_win_points_open if melds else average_win_points_closed),
    )
    if baseline is None:
        raise ValueError('no legal discard')
    d,sh,uke,est=baseline
    actions=[SelfKanActionResult(
        action='discard',tile=None,legal=True,reason='カンせず通常打牌',
        discard=format_tile(d),shanten=sh,ukeire_total=uke,
        tenpai_probability=est.tenpai_probability,
        win_probability=est.win_probability,
        expected_points=est.expected_points,
        rinshan_win_probability=0.0,expected_kandora_han=0.0,
    )]

    # ANKAN: any four identical concealed tiles. Ankan does not open a closed hand,
    # but structurally it consumes one meld slot. Menzen-yaku preservation and
    # riichi-after-ankan restrictions are explicitly deferred.
    for tile in profile.allowed_tiles:
        if counts[tile] != 4:
            continue
        after=counts.copy()
        after[tile]-=4
        melds_after=melds+(OpenMeld('kan',format_tile(tile)),)

        # The four tiles are already included in visible state via concealed hand;
        # no extra visible increment is needed before the rinshan draw.
        ev,w,t,rw,discard,sh2,uke2,kd=_rinshan_branch(
            after,melds_after,visible,
            profile=profile,draws=draws,
            average_win_points=(average_win_points_open if melds else average_win_points_closed),
        )
        actions.append(SelfKanActionResult(
            action='ankan',tile=format_tile(tile),legal=True,
            reason='暗槓可能',
            discard=discard,shanten=sh2,ukeire_total=uke2,
            tenpai_probability=t,win_probability=w,expected_points=ev,
            rinshan_win_probability=rw,expected_kandora_han=kd,
        ))

    # KAKAN: existing pon + fourth concealed tile.
    for idx,m in enumerate(melds):
        if m.kind!='pon':
            continue
        tile=m.tile_index()
        if counts[tile] <= 0:
            continue

        after=counts.copy()
        after[tile]-=1
        melds_after=list(melds)
        melds_after[idx]=OpenMeld('kan',m.tile)
        melds_after=tuple(melds_after)

        # Existing pon should already have a legal yaku route in Osaka complete-first.
        # Re-check the resulting committed melds conservatively.
        legal=True
        reason='加槓可能'
        if profile.complete_first:
            routes=analyze_open_yaku_routes(
                _counts_text(after),
                melds_after,
                round_wind=round_wind,
                seat_wind=seat_wind,
            )
            legal=routes.legal_complete_first
            reason=routes.reason

        if not legal:
            actions.append(SelfKanActionResult(
                action='kakan',tile=m.tile,legal=False,reason=reason,
                discard=None,shanten=99,ukeire_total=0,
                tenpai_probability=0.0,win_probability=0.0,expected_points=0.0,
                rinshan_win_probability=0.0,expected_kandora_han=0.0,
            ))
            continue

        ev,w,t,rw,discard,sh2,uke2,kd=_rinshan_branch(
            after,melds_after,visible,
            profile=profile,draws=draws,
            average_win_points=average_win_points_open,
        )
        actions.append(SelfKanActionResult(
            action='kakan',tile=m.tile,legal=True,reason=reason,
            discard=discard,shanten=sh2,ukeire_total=uke2,
            tenpai_probability=t,win_probability=w,expected_points=ev,
            rinshan_win_probability=rw,expected_kandora_han=kd,
        ))

    legal=[a for a in actions if a.legal]
    legal.sort(key=lambda a:(
        -a.expected_points,-a.win_probability,-a.tenpai_probability,
        a.shanten,-a.ukeire_total,a.action,a.tile or ''
    ))
    best=legal[0]

    return {
        'ruleset':profile.public_dict(),
        'draws':draws,
        'recommended_action':best.action,
        'recommended_tile':best.tile,
        'recommended_discard':best.discard,
        'actions':[asdict(a) for a in actions],
        'notice':(
            'v3.3 compares normal discard / ankan / kakan. '
            'Rinshan draw and expected kandora are modeled. '
            'Riichi-after-ankan restrictions, chankan risk, exact dead-wall order, '
            'and exact menzen scoring with closed kan are not yet included.'
        ),
    }
