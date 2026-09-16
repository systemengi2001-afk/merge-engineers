from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable

from .tiles import parse_mpsz
from .instant_analyzer import analyze_hand_instant
from .rules import get_ruleset
from .scoring import _dora_from_indicator


@dataclass(frozen=True)
class OpponentThreat:
    player: int
    riichi: bool
    discards: tuple[str,...]
    estimated_hand_value: float = 8000.0
    riichi_discard_index: int | None = None
    # Parallel to discards. True=tedashi, False=tsumogiri, omitted=unknown.
    tedashi_flags: tuple[bool | None,...] = ()


@dataclass(frozen=True)
class DefenseCandidate:
    discard: str
    attack_ev: float
    deal_in_probability: float
    expected_deal_in_loss: float
    practical_ev: float
    defense_class: str
    rationale: tuple[str,...]


def _single_index(token: str) -> int:
    c=parse_mpsz(token)
    if sum(c)!=1:
        raise ValueError(f'expected one tile: {token}')
    return next(i for i,n in enumerate(c) if n)


def _is_suji(tile: int, discards: set[int]) -> bool:
    if tile >= 27:
        return False
    base=(tile//9)*9
    r=tile%9
    partners={
        0:{3}, 1:{4}, 2:{5},
        3:{0,6}, 4:{1,7}, 5:{2,8},
        6:{3}, 7:{4}, 8:{5},
    }[r]
    return any(base+p in discards for p in partners)


def _matagi_factor(tile: int, threat: OpponentThreat) -> tuple[float,str | None]:
    """Raise risk around late tedashi tiles near/at riichi declaration."""
    if tile >= 27 or not threat.discards:
        return 1.0,None

    flags=threat.tedashi_flags
    ri=threat.riichi_discard_index
    # Look at last 3 pre-riichi/riichi discards when available.
    end=(ri if ri is not None else len(threat.discards)-1)
    start=max(0,end-2)
    target=tile
    base=(target//9)*9
    rank=target%9

    for idx in range(start,min(end+1,len(threat.discards))):
        if flags and idx < len(flags) and flags[idx] is False:
            continue
        d=_single_index(threat.discards[idx])
        if d>=27 or d//9 != target//9:
            continue
        dr=d%9
        # Matagi-adjacent pattern: discard 3-7 can increase risk of neighboring
        # ryanmen waits around it. This is deliberately conservative.
        if abs(rank-dr) in (1,2) and 2 <= dr <= 6:
            return 1.18,'またぎ筋'
    return 1.0,None


def _riichi_timing_factor(threat: OpponentThreat) -> tuple[float,str | None]:
    if not threat.riichi:
        return 1.0,None
    idx=threat.riichi_discard_index
    if idx is None:
        idx=max(0,len(threat.discards)-1)
    turn=idx+1
    if turn <= 5:
        return 1.12,'早いリーチ'
    if turn >= 12:
        return 0.92,'遅いリーチ'
    return 1.0,None


def _visible_counts_for_defense(
    hand: str,
    visible_tiles: Iterable[str],
    dora_indicators: Iterable[str],
    threats: Iterable[OpponentThreat],
) -> list[int]:
    counts=parse_mpsz(hand)
    for token in visible_tiles:
        c=parse_mpsz(token)
        for i,n in enumerate(c):
            counts[i]+=n
    for token in dora_indicators:
        c=parse_mpsz(token)
        for i,n in enumerate(c):
            counts[i]+=n
    for th in threats:
        for token in th.discards:
            c=parse_mpsz(token)
            for i,n in enumerate(c):
                counts[i]+=n
    return counts


def _wall_factor(tile: int, visible: list[int]) -> tuple[float,list[str]]:
    """Apply wall / one-chance reductions to sequence-wait risk."""
    if tile >= 27:
        # honor itself becomes safer as copies become visible
        if visible[tile] >= 3:
            return 0.45,['字牌3枚見え']
        if visible[tile] >= 2:
            return 0.70,['字牌2枚見え']
        return 1.0,[]

    base=(tile//9)*9
    r=tile%9
    adjacent=[]
    for off in (-2,-1,1,2):
        x=r+off
        if 0 <= x <= 8:
            adjacent.append(base+x)

    four=sum(visible[x] >= 4 for x in adjacent)
    three=sum(visible[x] == 3 for x in adjacent)
    if four:
        return 0.55,['壁']
    if three:
        return 0.78,['ワンチャンス']
    return 1.0,[]


def _dora_targets(
    dora_indicators: Iterable[str],
    allowed_tiles: set[int] | frozenset[int],
) -> set[int]:
    out=set()
    for token in dora_indicators:
        ind=_single_index(token)
        if ind == 0 and 1 not in allowed_tiles:
            out.add(8)
        elif ind == 8 and 1 not in allowed_tiles:
            out.add(0)
        else:
            out.add(_dora_from_indicator(ind))
    return out


def _dora_risk_factor(tile: int, dora_targets: set[int]) -> tuple[float,list[str]]:
    if tile in dora_targets:
        return 1.25,['ドラ']
    if tile >= 27:
        return 1.0,[]
    for d in dora_targets:
        if d<27 and d//9==tile//9 and abs((d%9)-(tile%9))==1:
            return 1.10,['ドラそば']
    return 1.0,[]


def _risk_vs_one(
    tile: int,
    threat: OpponentThreat,
    *,
    visible_counts: list[int] | None=None,
    dora_targets: set[int] | None=None,
) -> tuple[float,list[str]]:
    ds={_single_index(x) for x in threat.discards}
    reasons=[]

    if tile in ds:
        return 0.0,['現物']

    if not threat.riichi:
        base=0.015 if tile>=27 else 0.02
        reasons.append('非リーチ字牌' if tile>=27 else '非リーチ')
    elif _is_suji(tile,ds):
        reasons.append('筋')
        base=0.035
    elif tile >= 27:
        reasons.append('字牌')
        base=0.045
    else:
        rank=tile%9
        if rank in (0,8):
            reasons.append('端牌'); base=0.055
        elif rank in (1,7):
            reasons.append('2/8'); base=0.075
        else:
            reasons.append('中張牌'); base=0.10

    if visible_counts is not None:
        factor,rs=_wall_factor(tile,visible_counts)
        base*=factor
        reasons.extend(rs)

    mf,mr=_matagi_factor(tile,threat)
    base*=mf
    if mr:
        reasons.append(mr)

    tf,tr=_riichi_timing_factor(threat)
    base*=tf
    if tr:
        reasons.append(tr)

    if dora_targets:
        df,dr=_dora_risk_factor(tile,dora_targets)
        base*=df
        reasons.extend(dr)

    return max(0.0,min(0.35,base)),reasons


def _combine_independent_risks(risks: list[float]) -> float:
    survive=1.0
    for r in risks:
        survive *= max(0.0,min(1.0,1.0-r))
    return 1.0-survive


def evaluate_defense_ev(
    hand: str,
    *,
    threats: Iterable[OpponentThreat],
    visible_tiles: Iterable[str]=(),
    dora_indicators: Iterable[str]=(),
    draws: int=3,
    game_mode: str='sanma',
    ruleset: str='osaka_sanma_v1',
    nuki_count: int=0,
    risk_calibrator=None,
) -> dict:
    profile=get_ruleset(ruleset,game_mode)
    threats=tuple(threats)
    visible_tiles=tuple(visible_tiles)
    dora_indicators=tuple(dora_indicators)

    attack=analyze_hand_instant(
        hand,
        visible_tiles=visible_tiles,
        draws=draws,
        game_mode=game_mode,
        ruleset=ruleset,
        nuki_count=nuki_count,
        dora_indicators=dora_indicators,
    )

    defense_visible=_visible_counts_for_defense(
        hand,visible_tiles,dora_indicators,threats
    )
    dora_targets=_dora_targets(dora_indicators,profile.allowed_tiles)

    rows=[]
    for c in attack.get('candidates',[]):
        tile=_single_index(c['discard'])
        risks=[]
        rationale=[]
        raw_weighted_loss=0.0
        risk_weight_sum=0.0
        for th in threats:
            r,rs=_risk_vs_one(
                tile,th,
                visible_counts=defense_visible,
                dora_targets=dora_targets,
            )
            if risk_calibrator is not None:
                r=float(risk_calibrator.predict(r))
                r=max(0.0,min(1.0,r))
            risks.append(r)
            rationale.extend(f'P{th.player}:{x}' for x in rs)
            raw_weighted_loss += r*float(th.estimated_hand_value)
            risk_weight_sum += r

        deal=_combine_independent_risks(risks)
        # v6.19: deal-in events against multiple opponents are mutually exclusive for
        # a single discard.  Summing r_i * loss_i double-counted overlapping risk.
        # Keep the existing independent-union approximation for P(any deal-in), then
        # condition the loss severity on the relative per-opponent risks.  This makes
        # expected loss internally consistent and guarantees it cannot exceed the
        # largest configured opponent hand value merely because several threats exist.
        conditional_loss=(raw_weighted_loss/risk_weight_sum) if risk_weight_sum else 0.0
        weighted_loss=deal*conditional_loss
        attack_ev=float(c.get('expected_points',0.0))
        practical=attack_ev-weighted_loss

        if deal <= 0.01:
            cls='betaori_safe'
        elif deal <= 0.05:
            cls='safe'
        elif practical > 0:
            cls='push'
        else:
            cls='fold_or_turn'

        rows.append(DefenseCandidate(
            discard=c['discard'],
            attack_ev=attack_ev,
            deal_in_probability=deal,
            expected_deal_in_loss=weighted_loss,
            practical_ev=practical,
            defense_class=cls,
            rationale=tuple(rationale),
        ))

    rows.sort(key=lambda x:(-x.practical_ev,x.deal_in_probability,-x.attack_ev,x.discard))
    best=rows[0] if rows else None

    if not best:
        action=None
    elif best.defense_class=='push':
        action='push'
    elif best.defense_class=='betaori_safe':
        action='betaori'
    else:
        action='turn_or_fold'

    return {
        'ruleset':profile.public_dict(),
        'recommended_discard':best.discard if best else None,
        'recommended_action':action,
        'candidates':[asdict(x) for x in rows],
        'notice':(
            'v3.5 defense EV includes genbutsu, suji, wall, one-chance, '
            'matagi-suji, riichi timing, tedashi/tsumogiri hints, and dora-neighborhood risk. '
            'v6.19 also removes multi-opponent overlap double-counting from expected deal-in loss. ' +
            ('A supplied defense calibrator is applied to per-opponent heuristic risks before EV aggregation.'
             if risk_calibrator is not None else
             'The risk values are calibrated heuristics, not yet a learned deal-in model.')
        ),
        'risk_model': {
            'type': 'binned_calibrator' if risk_calibrator is not None else 'raw_heuristic',
            'version': getattr(risk_calibrator,'version',None) if risk_calibrator is not None else None,
            'ruleset': getattr(risk_calibrator,'ruleset',None) if risk_calibrator is not None else profile.id,
            'total_samples': getattr(risk_calibrator,'total_samples',None) if risk_calibrator is not None else None,
            'verified_only': getattr(risk_calibrator,'verified_only',None) if risk_calibrator is not None else None,
        },
    }
