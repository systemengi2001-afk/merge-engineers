from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable

from .tiles import parse_mpsz, format_tile, total_tiles
from .shanten import normal_shanten_with_open_melds
from .ev_instant import estimate_instant
from .open_hand import OpenMeld, check_osaka_call_from_hand
from .open_scoring import score_open_hand
from .scoring import ScoreConfig, _dora_from_indicator
from .rules import get_ruleset, validate_counts_for_rules
from .visible_state import build_visible_state


@dataclass(frozen=True)
class KanActionResult:
    action: str
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
    model: str


def _single_index(token: str) -> int:
    c=parse_mpsz(token)
    if sum(c)!=1:
        raise ValueError(f'expected one tile: {token}')
    return next(i for i,n in enumerate(c) if n)


def _counts_text(counts: list[int]) -> str:
    return ''.join(format_tile(i)*n for i,n in enumerate(counts) if n)


def _open_ukeire(
    concealed_counts: list[int],
    visible_counts: list[int],
    *,
    open_meld_count: int,
    allowed_tiles: set[int] | frozenset[int],
) -> tuple[int,int]:
    sh=normal_shanten_with_open_melds(concealed_counts,open_meld_count)
    uke=0
    for i in allowed_tiles:
        remaining=4-visible_counts[i]
        if remaining <= 0:
            continue
        concealed_counts[i]+=1
        nxt=normal_shanten_with_open_melds(concealed_counts,open_meld_count)
        concealed_counts[i]-=1
        if nxt < sh:
            uke += remaining
    return sh,uke


def _dora_target_for_rules(ind: int, allowed_tiles: set[int] | frozenset[int]) -> int:
    # Sanma removes 2m-8m. In that tile universe the two remaining manzu
    # terminals cycle 1m <-> 9m for dora-indicator purposes.
    if ind == 0 and 1 not in allowed_tiles:
        return 8
    if ind == 8 and 1 not in allowed_tiles:
        return 0
    return _dora_from_indicator(ind)


def _expected_kandora_han(
    all_hand_counts: list[int],
    visible_counts: list[int],
    allowed_tiles: set[int] | frozenset[int],
) -> float:
    """Approximate expected additional dora count from one new kan indicator.

    The actual dead-wall composition is hidden. v3.2 models the next indicator
    as uniformly sampled from unseen physical tile copies in the ruleset.
    """
    weighted=0.0
    total=0
    for ind in allowed_tiles:
        unseen=max(0,4-visible_counts[ind])
        if unseen <= 0:
            continue
        total += unseen
        target=_dora_target_for_rules(ind,allowed_tiles)
        weighted += unseen * all_hand_counts[target]
    return (weighted/total) if total else 0.0


def evaluate_daiminkan(
    concealed_hand: str,
    offered_tile: str,
    *,
    existing_melds: Iterable[OpenMeld]=(),
    ruleset: str='osaka_sanma_v1',
    round_wind: str='1z',
    seat_wind: str='2z',
    visible_tiles: Iterable[str]=(),
    dora_indicators: Iterable[str]=(),
    nuki_count: int=0,
    draws: int=3,
    average_win_points_open: float=3900.0,
) -> KanActionResult:
    if draws < 1:
        raise ValueError('draws must be >= 1')

    profile=get_ruleset(ruleset,None)
    melds=tuple(existing_melds)
    counts=parse_mpsz(concealed_hand)
    validate_counts_for_rules(counts,profile)
    if total_tiles(counts) != 13 - 3*len(melds):
        raise ValueError('concealed hand count is inconsistent with existing melds')

    offered=_single_index(offered_tile)
    if offered not in profile.allowed_tiles:
        raise ValueError('offered tile is not used by this ruleset')
    if counts[offered] < 3:
        return KanActionResult(
            action='daiminkan',legal=False,
            reason='大明槓に必要な同牌3枚が手牌にない',
            discard=None,shanten=99,ukeire_total=0,
            tenpai_probability=0.0,win_probability=0.0,expected_points=0.0,
            rinshan_win_probability=0.0,expected_kandora_han=0.0,
            model='daiminkan_rinshan_ev_v3.2',
        )

    meld_visible=list(visible_tiles)
    for m in melds:
        copies=4 if m.kind=='kan' else 3
        meld_visible.extend([m.tile]*copies)

    state=build_visible_state(
        counts,profile,
        visible_tiles=meld_visible,
        dora_indicators=dora_indicators,
        nuki_count=nuki_count,
    )
    visible=list(state.counts)
    visible[offered]+=1
    if visible[offered] > 4:
        raise ValueError('offered tile exceeds four visible copies')

    after_call=counts.copy()
    after_call[offered]-=3
    melds_after=melds+(OpenMeld('kan',offered_tile),)

    legality=check_osaka_call_from_hand(
        _counts_text(after_call),
        call_type='kan',
        called_tile=offered_tile,
        melds_after_call=melds_after,
        round_wind=round_wind,
        seat_wind=seat_wind,
    ) if profile.complete_first else {
        'legal':True,'reason':'合法','guaranteed_yaku':[],'possible_routes':[]
    }
    if not legality['legal']:
        return KanActionResult(
            action='daiminkan',legal=False,reason=legality['reason'],
            discard=None,shanten=99,ukeire_total=0,
            tenpai_probability=0.0,win_probability=0.0,expected_points=0.0,
            rinshan_win_probability=0.0,expected_kandora_han=0.0,
            model='daiminkan_rinshan_ev_v3.2',
        )

    # Include physical tiles committed to open melds for expected kandora.
    all_counts=after_call.copy()
    for m in melds_after:
        all_counts[m.tile_index()] += 4 if m.kind=='kan' else 3

    expected_kandora=_expected_kandora_han(
        all_counts,visible,set(profile.allowed_tiles)
    )
    kandora_multiplier=min(4.0,2.0**expected_kandora)
    avg_points_hint=average_win_points_open*kandora_multiplier

    live=[(i,max(0,4-visible[i])) for i in profile.allowed_tiles if visible[i] < 4]
    total_live=sum(n for _,n in live)
    if total_live <= 0:
        return KanActionResult(
            action='daiminkan',legal=True,reason=legality['reason'],
            discard=None,
            shanten=normal_shanten_with_open_melds(after_call,len(melds_after)),
            ukeire_total=0,tenpai_probability=0.0,win_probability=0.0,
            expected_points=0.0,rinshan_win_probability=0.0,
            expected_kandora_han=expected_kandora,
            model='daiminkan_rinshan_ev_v3.2',
        )

    cfg=ScoreConfig(
        dealer=False,
        round_wind=_single_index(round_wind),
        seat_wind=_single_index(seat_wind),
        riichi=False,
        tsumo=True,
        dora_indicators=tuple(_single_index(x) for x in dora_indicators),
        players=profile.players,
        tsumo_loss=profile.tsumo_loss,
        nuki_dora_count=nuki_count*profile.nuki_dora_han,
    )

    expected_points=0.0
    win_probability=0.0
    tenpai_probability=0.0
    rinshan_win_probability=0.0
    best_summary=None

    for tile,n in live:
        p=n/total_live
        hand_after_draw=after_call.copy()
        hand_after_draw[tile]+=1
        visible2=visible.copy()
        visible2[tile]+=1

        sh_after=normal_shanten_with_open_melds(hand_after_draw,len(melds_after))
        if sh_after < 0:
            score=score_open_hand(
                _counts_text(hand_after_draw),
                melds_after,
                cfg,
                winning_tile=format_tile(tile),
                open_tanyao=profile.open_tanyao,
            )
            pts=float(score.points)
            # If the current scorer cannot represent the extra unknown kandora
            # directly, apply the expected-indicator multiplier as the fast layer.
            pts=max(pts,avg_points_hint)
            expected_points += p*pts
            win_probability += p
            tenpai_probability += p
            rinshan_win_probability += p
            continue

        best=None
        for d in profile.allowed_tiles:
            if hand_after_draw[d] <= 0:
                continue
            post=hand_after_draw.copy()
            post[d]-=1
            sh,uke=_open_ukeire(
                post,visible2,
                open_meld_count=len(melds_after),
                allowed_tiles=profile.allowed_tiles,
            )
            remaining_live=max(0,total_live-1)
            est=estimate_instant(
                sh,uke,draws,remaining_live,
                average_win_points_hint=avg_points_hint,
            )
            key=(est.expected_points,est.win_probability,est.tenpai_probability,-sh,uke)
            if best is None or key > best[0]:
                best=(key,d,sh,uke,est)

        if best is None:
            continue
        _,d,sh,uke,est=best
        expected_points += p*est.expected_points
        win_probability += p*est.win_probability
        tenpai_probability += p*est.tenpai_probability
        summary=(est.expected_points,d,sh,uke)
        if best_summary is None or summary[0] > best_summary[0]:
            best_summary=summary

    discard=format_tile(best_summary[1]) if best_summary else None
    shanten=best_summary[2] if best_summary else -1
    ukeire=best_summary[3] if best_summary else 0

    return KanActionResult(
        action='daiminkan',
        legal=True,
        reason=legality['reason'],
        discard=discard,
        shanten=shanten,
        ukeire_total=ukeire,
        tenpai_probability=max(0.0,min(1.0,tenpai_probability)),
        win_probability=max(0.0,min(1.0,win_probability)),
        expected_points=expected_points,
        rinshan_win_probability=max(0.0,min(1.0,rinshan_win_probability)),
        expected_kandora_han=expected_kandora,
        model='daiminkan_rinshan_ev_v3.2',
    )
