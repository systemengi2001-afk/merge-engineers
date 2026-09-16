from __future__ import annotations
from dataclasses import asdict
import os

from .instant_analyzer import analyze_hand_instant
from .reference_oracle import (
    build_mahjong_cpp_request, call_mahjong_cpp,
    normalize_mahjong_cpp_response,
)

def analyze_oracle_first(
    *,
    hand: str,
    game_mode: str='yonma',
    ruleset: str | None=None,
    round_wind: str='1z',
    seat_wind: str='2z',
    dora_indicators: list[str] | None=None,
    visible_tiles: list[str] | None=None,
    nuki_count: int=0,
    turn: int=1,
    oracle_url: str | None=None,
    strict_oracle: bool=False,
) -> dict:
    """Use mahjong-cpp as the primary calculator for standard yonma/sanma.

    Osaka-sanma remains JONG-native because local rules are not equivalent to the
    generic sanma reference model. If the oracle is unavailable and strict mode
    is off, fall back to JONG's instant analyzer.
    """
    is_osaka = (ruleset == 'osaka_sanma_v1')
    url = oracle_url or os.getenv('JONG_MAHJONG_CPP_URL')

    if not is_osaka and url:
        payload=build_mahjong_cpp_request(
            hand=hand,
            game_mode=game_mode,
            round_wind=round_wind,
            seat_wind=seat_wind,
            dora_indicators=dora_indicators or [],
            nuki_count=nuki_count,
            visible_tiles=visible_tiles or [],
        )
        try:
            raw=call_mahjong_cpp(url,payload)
            oracle=normalize_mahjong_cpp_response(raw,turn=turn)
            candidates=[asdict(c) for c in oracle.candidates]
            return {
                'source':'mahjong-cpp',
                'source_role':'primary',
                'fallback_used':False,
                'shanten':oracle.shanten,
                'best_by_ev':candidates[0]['discard'] if candidates else None,
                'candidates':candidates,
                'oracle_meta':{
                    'searched':oracle.searched,
                    'time_us':oracle.time_us,
                },
            }
        except Exception as e:
            if strict_oracle:
                raise
            fallback_reason=str(e)
    else:
        fallback_reason = (
            'osaka_sanma_requires_jong_native_rules'
            if is_osaka else
            'oracle_not_configured'
        )

    if strict_oracle and not is_osaka:
        raise RuntimeError(f'mahjong-cpp oracle unavailable: {fallback_reason}')

    result=analyze_hand_instant(
        hand,
        visible_tiles or [],
        draws=max(1,min(6,turn)),
        game_mode=game_mode,
        ruleset=ruleset,
        nuki_count=nuki_count,
        dora_indicators=dora_indicators or [],
    )
    result['source']='jong-native'
    result['source_role']='fallback' if not is_osaka else 'primary-osaka-extension'
    result['fallback_used']=not is_osaka
    result['fallback_reason']=fallback_reason
    return result
