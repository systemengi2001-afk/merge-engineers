from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable

from .tiles import parse_mpsz, format_tile, total_tiles
from .shanten import calculate_shanten, normal_shanten_with_open_melds
from .analyzer import ukeire_for_13
from .ev_instant import estimate_instant
from .open_hand import OpenMeld, check_osaka_call_from_hand
from .rules import get_ruleset, validate_counts_for_rules
from .visible_state import build_visible_state
from .kan_decision import evaluate_daiminkan


@dataclass(frozen=True)
class CallActionResult:
    action: str
    legal: bool
    reason: str
    discard: str | None
    shanten: int
    ukeire_total: int
    tenpai_probability: float
    win_probability: float
    expected_points: float
    model: str


def _single_index(token: str) -> int:
    c=parse_mpsz(token)
    if sum(c)!=1:
        raise ValueError(f'expected one tile: {token}')
    return next(i for i,n in enumerate(c) if n)


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


def _closed_pass_metrics(
    counts13: list[int],
    visible_counts: list[int],
    *,
    allowed_tiles: set[int] | frozenset[int],
    draws: int,
    total_live: int,
    avg_points: float,
) -> CallActionResult:
    sh,_,uke=ukeire_for_13(counts13.copy(),visible_counts,allowed_tiles)
    uke_total=sum(x.remaining for x in uke)
    est=estimate_instant(sh,uke_total,draws,total_live,average_win_points_hint=avg_points)
    return CallActionResult(
        action='pass',legal=True,reason='鳴かずに進行',
        discard=None,shanten=sh,ukeire_total=uke_total,
        tenpai_probability=est.tenpai_probability,
        win_probability=est.win_probability,
        expected_points=est.expected_points,
        model='call_decision_instant_v3.1',
    )


def evaluate_pon_decision(
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
    average_win_points_closed: float=5200.0,
    average_win_points_open: float=3900.0,
) -> dict:
    """Compare pass vs legal pon using the same fast finite-horizon model.

    This v3.1 implementation intentionally evaluates PON only. Kan remains
    excluded until replacement draw / kandora semantics are modeled explicitly.
    """
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

    # The opponent discard becomes visible for both branches.
    visible_after_offer=visible.copy()
    visible_after_offer[offered]+=1
    if visible_after_offer[offered] > 4:
        raise ValueError('offered tile exceeds four visible copies')
    total_live=max(0,state.live_total-1)

    pass_result=_closed_pass_metrics(
        counts,visible_after_offer,
        allowed_tiles=profile.allowed_tiles,
        draws=draws,
        total_live=total_live,
        avg_points=average_win_points_closed,
    )

    actions=[pass_result]

    if counts[offered] < 2:
        actions.append(CallActionResult(
            action='pon',legal=False,reason='ポンに必要な同牌2枚が手牌にない',
            discard=None,shanten=99,ukeire_total=0,
            tenpai_probability=0.0,win_probability=0.0,expected_points=0.0,
            model='call_decision_instant_v3.1',
        ))
    else:
        after_call=counts.copy()
        after_call[offered]-=2
        new_meld=OpenMeld('pon',offered_tile)
        melds_after=melds+(new_meld,)

        # Before discard after pon, concealed hand has 11-3*k tiles.
        # Evaluate every legal discard and retain the best EV.
        best=None
        best_legality=None
        for d in profile.allowed_tiles:
            if after_call[d] <= 0:
                continue
            post=after_call.copy()
            post[d]-=1

            # Complete-first legality is evaluated on the post-call concealed hand.
            # MPSZ serialization for legality only needs tile identities.
            parts=[]
            for i,n in enumerate(post):
                parts.extend([format_tile(i)]*n)
            # compact parser accepts repeated suited tokens separately as well.
            concealed_after=''.join(parts)
            legality=check_osaka_call_from_hand(
                concealed_after,
                call_type='pon',
                called_tile=offered_tile,
                melds_after_call=melds_after,
                round_wind=round_wind,
                seat_wind=seat_wind,
            ) if profile.complete_first else {
                'legal':True,'reason':'合法','guaranteed_yaku':[],'possible_routes':[]
            }
            if not legality['legal']:
                best_legality=legality
                continue

            sh,uke=_open_ukeire(
                post,visible_after_offer,
                open_meld_count=len(melds_after),
                allowed_tiles=profile.allowed_tiles,
            )
            est=estimate_instant(
                sh,uke,draws,total_live,
                average_win_points_hint=average_win_points_open,
            )
            key=(est.expected_points,est.win_probability,est.tenpai_probability,-sh,uke)
            if best is None or key > best[0]:
                best=(key,d,sh,uke,est,legality)

        if best is None:
            reason=(best_legality or {}).get('reason','完全先付けまたは手牌条件により合法なポン後打牌なし')
            actions.append(CallActionResult(
                action='pon',legal=False,reason=reason,
                discard=None,shanten=99,ukeire_total=0,
                tenpai_probability=0.0,win_probability=0.0,expected_points=0.0,
                model='call_decision_instant_v3.1',
            ))
        else:
            _,d,sh,uke,est,legality=best
            actions.append(CallActionResult(
                action='pon',legal=True,reason=legality['reason'],
                discard=format_tile(d),shanten=sh,ukeire_total=uke,
                tenpai_probability=est.tenpai_probability,
                win_probability=est.win_probability,
                expected_points=est.expected_points,
                model='call_decision_instant_v3.1',
            ))

    legal=[a for a in actions if a.legal]
    legal.sort(key=lambda a:(-a.expected_points,-a.win_probability,-a.tenpai_probability,a.shanten,-a.ukeire_total,a.action))
    recommended=legal[0] if legal else pass_result

    return {
        'ruleset':profile.public_dict(),
        'offered_tile':offered_tile,
        'draws':draws,
        'recommended_action':recommended.action,
        'recommended_discard':recommended.discard,
        'actions':[asdict(a) for a in actions],
        'notice':(
            'v3.1 compares pass vs PON with a shared fast horizon model. '
            'Open-hand average points are still a configurable heuristic; '
            'kan, defense, ron risk and opponent actions are not yet included.'
        ),
    }


def evaluate_call_decision(
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
    average_win_points_closed: float=5200.0,
    average_win_points_open: float=3900.0,
) -> dict:
    """Compare pass, pon and daiminkan on the same state/horizon."""
    melds=tuple(existing_melds)
    pon_bundle=evaluate_pon_decision(
        concealed_hand,
        offered_tile,
        existing_melds=melds,
        ruleset=ruleset,
        round_wind=round_wind,
        seat_wind=seat_wind,
        visible_tiles=visible_tiles,
        dora_indicators=dora_indicators,
        nuki_count=nuki_count,
        draws=draws,
        average_win_points_closed=average_win_points_closed,
        average_win_points_open=average_win_points_open,
    )
    kan=evaluate_daiminkan(
        concealed_hand,
        offered_tile,
        existing_melds=melds,
        ruleset=ruleset,
        round_wind=round_wind,
        seat_wind=seat_wind,
        visible_tiles=visible_tiles,
        dora_indicators=dora_indicators,
        nuki_count=nuki_count,
        draws=draws,
        average_win_points_open=average_win_points_open,
    )

    actions=list(pon_bundle['actions'])
    actions.append(asdict(kan))

    legal=[x for x in actions if x.get('legal')]
    legal.sort(key=lambda x:(
        -float(x.get('expected_points',0.0)),
        -float(x.get('win_probability',0.0)),
        -float(x.get('tenpai_probability',0.0)),
        int(x.get('shanten',99)),
        -int(x.get('ukeire_total',0)),
        x.get('action',''),
    ))
    best=legal[0] if legal else next(x for x in actions if x['action']=='pass')

    return {
        'ruleset':pon_bundle['ruleset'],
        'offered_tile':offered_tile,
        'draws':draws,
        'recommended_action':best['action'],
        'recommended_discard':best.get('discard'),
        'actions':actions,
        'notice':(
            'v3.2 compares pass / pon / daiminkan. Daiminkan includes an immediate '
            'rinshan draw and an expected kandora uplift. The hidden kandora indicator '
            'is modeled probabilistically; defense, opponent actions and exact dead-wall '
            'composition remain outside this fast decision layer.'
        ),
    }
