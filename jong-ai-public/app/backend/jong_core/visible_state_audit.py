from __future__ import annotations

from dataclasses import dataclass, asdict
import random
from typing import Iterable

from .tiles import parse_mpsz, format_tile
from .rules import get_ruleset
from .visible_state import build_visible_state, NORTH_INDEX
from .analyzer import analyze_hand
from .case_generator import counts_to_mpsz


@dataclass(frozen=True)
class VisibleAuditCase:
    case_id: str
    hand: str
    ruleset: str
    game_mode: str
    visible_tiles: tuple[str,...] = ()
    dora_indicators: tuple[str,...] = ()
    nuki_count: int = 0


@dataclass(frozen=True)
class AuditIssue:
    case_id: str
    code: str
    detail: str
    discard: str | None = None
    tile: str | None = None


def _single_index(token: str) -> int:
    c=parse_mpsz(token)
    if sum(c)!=1:
        raise ValueError(f'expected one tile: {token}')
    return next(i for i,n in enumerate(c) if n)


def audit_visible_case(case: VisibleAuditCase) -> dict:
    profile=get_ruleset(case.ruleset,case.game_mode)
    hand_counts=parse_mpsz(case.hand)
    state=build_visible_state(
        hand_counts,
        profile,
        visible_tiles=case.visible_tiles,
        dora_indicators=case.dora_indicators,
        nuki_count=case.nuki_count,
    )
    result=analyze_hand(
        case.hand,
        visible_tiles=case.visible_tiles,
        dora_indicators=case.dora_indicators,
        nuki_count=case.nuki_count,
        game_mode=case.game_mode,
        ruleset=case.ruleset,
    )

    issues=[]

    # Physical-copy invariant.
    for i,count in enumerate(state.counts):
        if count < 0 or count > 4:
            issues.append(AuditIssue(
                case.case_id,'VISIBLE_COPY_RANGE',
                f'{format_tile(i)} visible count={count}, expected 0..4',
                tile=format_tile(i),
            ))

    # Removed sanma manzu must never have live copies or appear in ukeire.
    removed=set(range(1,8)) - set(profile.allowed_tiles)
    for i in removed:
        if i in profile.allowed_tiles:
            continue
        if state.counts[i] != 0:
            issues.append(AuditIssue(
                case.case_id,'REMOVED_TILE_VISIBLE',
                f'{format_tile(i)} exists in sanma visible state',
                tile=format_tile(i),
            ))

    expected_live=sum(4-state.counts[i] for i in profile.allowed_tiles)
    if state.live_total != expected_live:
        issues.append(AuditIssue(
            case.case_id,'LIVE_TOTAL_MISMATCH',
            f'live_total={state.live_total}, recomputed={expected_live}',
        ))

    # Every reported ukeire tile must be legal and remaining must match 4-visible.
    candidates=result.get('candidates',[])
    if result.get('tile_count')==13:
        candidate_sets=[(None,result.get('ukeire',[]))]
    else:
        candidate_sets=[(c.get('discard'),c.get('ukeire',[])) for c in candidates]

    for discard,ukeire in candidate_sets:
        total=0
        seen=set()
        for row in ukeire:
            tile=row['tile']
            idx=_single_index(tile)
            rem=int(row['remaining'])
            total+=rem
            if idx not in profile.allowed_tiles:
                issues.append(AuditIssue(
                    case.case_id,'ILLEGAL_UKEIRE_TILE',
                    f'{tile} is not allowed by {profile.id}',
                    discard=discard,tile=tile,
                ))
            expected=4-state.counts[idx]
            if rem != expected:
                issues.append(AuditIssue(
                    case.case_id,'UKEIRE_REMAINING_MISMATCH',
                    f'{tile} remaining={rem}, expected={expected}',
                    discard=discard,tile=tile,
                ))
            if rem <= 0 or rem > 4:
                issues.append(AuditIssue(
                    case.case_id,'UKEIRE_REMAINING_RANGE',
                    f'{tile} remaining={rem}, expected 1..4',
                    discard=discard,tile=tile,
                ))
            if tile in seen:
                issues.append(AuditIssue(
                    case.case_id,'DUPLICATE_UKEIRE',
                    f'{tile} appears more than once',
                    discard=discard,tile=tile,
                ))
            seen.add(tile)

        if discard is None:
            reported=int(result.get('ukeire_total',0))
        else:
            c=next(x for x in candidates if x.get('discard')==discard)
            reported=int(c.get('ukeire_total',0))
        if reported != total:
            issues.append(AuditIssue(
                case.case_id,'UKEIRE_TOTAL_MISMATCH',
                f'ukeire_total={reported}, sum(remaining)={total}',
                discard=discard,
            ))

    # North nuki must reduce physical North availability exactly.
    north_without_nuki=parse_mpsz(case.hand)[NORTH_INDEX]
    for token in case.visible_tiles:
        north_without_nuki += parse_mpsz(token)[NORTH_INDEX]
    for token in case.dora_indicators:
        north_without_nuki += parse_mpsz(token)[NORTH_INDEX]
    expected_north=north_without_nuki+case.nuki_count
    if state.counts[NORTH_INDEX] != expected_north:
        issues.append(AuditIssue(
            case.case_id,'NUKI_NORTH_MISMATCH',
            f'north visible={state.counts[NORTH_INDEX]}, expected={expected_north}',
            tile='4z',
        ))

    return {
        'case_id':case.case_id,
        'ok':not issues,
        'issues':[asdict(x) for x in issues],
        'visible_state':{
            'counts':list(state.counts),
            'live_total':state.live_total,
            'source_counts':state.source_counts,
        },
        'candidate_count':len(candidates),
    }


def _draw_scenario(rng: random.Random, *, ruleset: str, case_id: str) -> VisibleAuditCase:
    profile=get_ruleset(ruleset,None)
    game_mode='yonma' if profile.players==4 else 'sanma'

    wall=[]
    for i in sorted(profile.allowed_tiles):
        wall.extend([i]*4)
    rng.shuffle(wall)

    hand_tiles=wall[:14]
    cursor=14

    # Add 0..10 ordinary visible tiles and 0..2 dora indicators without exceeding copies.
    visible_n=rng.randint(0,10)
    visible_idx=wall[cursor:cursor+visible_n]
    cursor+=visible_n

    dora_n=rng.randint(0,2)
    dora_idx=wall[cursor:cursor+dora_n]
    cursor+=dora_n

    counts=[0]*34
    for i in hand_tiles:
        counts[i]+=1

    visible=[format_tile(i) for i in visible_idx]
    dora=[format_tile(i) for i in dora_idx]

    nuki=0
    if profile.north_nuki:
        used_north=counts[NORTH_INDEX] + sum(1 for i in visible_idx if i==NORTH_INDEX) + sum(1 for i in dora_idx if i==NORTH_INDEX)
        nuki=rng.randint(0,max(0,4-used_north))

    return VisibleAuditCase(
        case_id=case_id,
        hand=counts_to_mpsz(counts),
        ruleset=profile.id,
        game_mode=game_mode,
        visible_tiles=tuple(visible),
        dora_indicators=tuple(dora),
        nuki_count=nuki,
    )


def generate_audit_cases(
    count: int=1000,
    *,
    rulesets: tuple[str,...]=('yonma_standard','sanma_standard','osaka_sanma_v1'),
    seed: int=20260915,
) -> list[VisibleAuditCase]:
    if count < 1 or count > 10000:
        raise ValueError('count must be 1..10000')
    if not rulesets:
        raise ValueError('rulesets must not be empty')
    rng=random.Random(seed)
    out=[]
    for i in range(count):
        ruleset=rulesets[i % len(rulesets)]
        out.append(_draw_scenario(
            rng,
            ruleset=ruleset,
            case_id=f'audit-{i+1:05d}-{ruleset}',
        ))
    return out


def run_visible_state_audit(
    count: int=1000,
    *,
    rulesets: tuple[str,...]=('yonma_standard','sanma_standard','osaka_sanma_v1'),
    seed: int=20260915,
) -> dict:
    cases=generate_audit_cases(count,rulesets=rulesets,seed=seed)
    rows=[]
    issue_counts={}
    ruleset_counts={}
    failed_by_ruleset={}
    for case in cases:
        row=audit_visible_case(case)
        rows.append(row)
        ruleset_counts[case.ruleset]=ruleset_counts.get(case.ruleset,0)+1
        if not row['ok']:
            failed_by_ruleset[case.ruleset]=failed_by_ruleset.get(case.ruleset,0)+1
        for issue in row['issues']:
            code=issue['code']
            issue_counts[code]=issue_counts.get(code,0)+1

    failed=sum(1 for x in rows if not x['ok'])
    return {
        'schema_version':'visible-state-audit-v4.3',
        'seed':seed,
        'cases':len(rows),
        'passed':len(rows)-failed,
        'failed':failed,
        'pass_rate':(len(rows)-failed)/len(rows) if rows else 0.0,
        'ruleset_counts':ruleset_counts,
        'failed_by_ruleset':failed_by_ruleset,
        'issue_counts':issue_counts,
        'failures':[x for x in rows if not x['ok']][:200],
    }
