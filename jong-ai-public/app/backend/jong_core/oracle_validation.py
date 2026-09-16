from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable
from urllib.parse import urlparse
import socket
import time

from .instant_analyzer import analyze_hand_instant
from .reference_oracle import (
    build_mahjong_cpp_request,
    call_mahjong_cpp,
    normalize_mahjong_cpp_response,
    compare_jong_to_oracle,
)

@dataclass(frozen=True)
class OracleValidationCase:
    case_id: str
    hand: str
    game_mode: str='yonma'
    ruleset: str|None=None
    round_wind: str='1z'
    seat_wind: str='2z'
    dora_indicators: tuple[str,...]=()
    visible_tiles: tuple[str,...]=()
    nuki_count: int=0
    turn: int=1

@dataclass(frozen=True)
class OracleProbe:
    url: str
    reachable: bool
    latency_ms: float|None
    response_success: bool|None
    response_keys: tuple[str,...]
    error_kind: str|None
    error: str|None

def _classify_error(exc: Exception) -> str:
    msg=str(exc).lower()
    if 'name or service not known' in msg or 'temporary failure in name resolution' in msg or 'resolve' in msg:
        return 'dns'
    if 'timed out' in msg or 'timeout' in msg:
        return 'timeout'
    if 'connection refused' in msg:
        return 'connection_refused'
    if 'http error' in msg:
        return 'http'
    if 'json' in msg:
        return 'invalid_json'
    return 'transport_or_protocol'

def validate_mahjong_cpp_schema(data: dict) -> dict:
    errors=[]
    if not isinstance(data,dict):
        return {'valid':False,'errors':['response must be a JSON object']}
    if 'success' not in data:
        errors.append('missing success')
    if data.get('success'):
        if 'shanten' not in data or not isinstance(data.get('shanten'),dict):
            errors.append('missing/invalid shanten')
        if 'stats' not in data or not isinstance(data.get('stats'),list):
            errors.append('missing/invalid stats')
        else:
            for idx,s in enumerate(data['stats'][:20]):
                if not isinstance(s,dict):
                    errors.append(f'stats[{idx}] is not object'); continue
                for k in ('tile','shanten','necessary_tiles','tenpai_prob','win_prob','exp_score'):
                    if k not in s:
                        errors.append(f'stats[{idx}] missing {k}')
    elif 'err_msg' not in data:
        errors.append('failure response missing err_msg')
    return {'valid':not errors,'errors':errors}

def probe_mahjong_cpp(url: str, payload: dict, timeout: float=3.0) -> OracleProbe:
    started=time.perf_counter()
    try:
        data=call_mahjong_cpp(url,payload,timeout=timeout)
        latency=(time.perf_counter()-started)*1000.0
        schema=validate_mahjong_cpp_schema(data)
        if not schema['valid']:
            return OracleProbe(
                url=url,reachable=True,latency_ms=latency,
                response_success=data.get('success'),
                response_keys=tuple(sorted(data.keys())),
                error_kind='schema',
                error='; '.join(schema['errors']),
            )
        return OracleProbe(
            url=url,reachable=True,latency_ms=latency,
            response_success=bool(data.get('success')),
            response_keys=tuple(sorted(data.keys())),
            error_kind=None,error=None,
        )
    except Exception as e:
        latency=(time.perf_counter()-started)*1000.0
        return OracleProbe(
            url=url,reachable=False,latency_ms=latency,
            response_success=None,response_keys=(),
            error_kind=_classify_error(e),error=str(e),
        )

def validate_live_cases(
    url: str,
    cases: Iterable[OracleValidationCase],
    *,
    timeout: float=20.0,
    instant_draws: int=2,
) -> dict:
    cases=tuple(cases)
    results=[]
    for case in cases:
        payload=build_mahjong_cpp_request(
            hand=case.hand,
            game_mode=case.game_mode,
            round_wind=case.round_wind,
            seat_wind=case.seat_wind,
            dora_indicators=list(case.dora_indicators),
            nuki_count=case.nuki_count,
            visible_tiles=list(case.visible_tiles),
        )
        raw=call_mahjong_cpp(url,payload,timeout=timeout)
        schema=validate_mahjong_cpp_schema(raw)
        if not schema['valid']:
            raise ValueError(f"{case.case_id}: invalid mahjong-cpp schema: {schema['errors']}")
        oracle=normalize_mahjong_cpp_response(raw,turn=case.turn)
        jong=analyze_hand_instant(
            case.hand,
            visible_tiles=case.visible_tiles,
            draws=instant_draws,
            game_mode=case.game_mode,
            ruleset=case.ruleset,
            nuki_count=case.nuki_count,
            dora_indicators=case.dora_indicators,
        )
        cmp=compare_jong_to_oracle(jong,oracle)
        results.append({
            'case_id':case.case_id,
            'request':payload,
            'oracle_meta':{
                'shanten':oracle.shanten,
                'searched':oracle.searched,
                'time_us':oracle.time_us,
            },
            'comparison':cmp,
        })

    best_matches=sum(1 for r in results if r['comparison']['best_match'])
    comparable_rows=sum(len(r['comparison']['rows']) for r in results)
    abs_ev=[]; abs_win=[]; abs_ten=[]; abs_uke=[]
    for r in results:
        for row in r['comparison']['rows']:
            d=row['delta']
            if d['expected_points'] is not None: abs_ev.append(abs(d['expected_points']))
            if d['win_probability'] is not None: abs_win.append(abs(d['win_probability']))
            if d['tenpai_probability'] is not None: abs_ten.append(abs(d['tenpai_probability']))
            if d['ukeire_total'] is not None: abs_uke.append(abs(d['ukeire_total']))

    def avg(xs):
        return sum(xs)/len(xs) if xs else None

    return {
        'oracle_url':url,
        'cases':len(results),
        'best_match_rate':best_matches/len(results) if results else None,
        'comparable_rows':comparable_rows,
        'mae_expected_points':avg(abs_ev),
        'mae_win_probability':avg(abs_win),
        'mae_tenpai_probability':avg(abs_ten),
        'mae_ukeire_total':avg(abs_uke),
        'results':results,
        'validated_live':True,
    }
