from __future__ import annotations
from dataclasses import dataclass, asdict
import json
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError

from .tiles import parse_mpsz, format_tile

# mahjong-cpp uses 0..33 for normal tiles and 34..36 for red 5m/5p/5s.
RED_INDEX={'0m':34,'0p':35,'0s':36}


def _single_tile_to_oracle(token: str) -> int:
    if token in RED_INDEX:
        return RED_INDEX[token]
    c=parse_mpsz(token)
    if sum(c)!=1:
        raise ValueError(f'expected one tile: {token}')
    return next(i for i,n in enumerate(c) if n)


def _mpsz_to_oracle_tiles(hand: str) -> list[int]:
    out=[]
    digits=''
    for ch in hand:
        if ch.isdigit():
            digits += ch
            continue
        if ch not in 'mpsz':
            raise ValueError(f'invalid suit: {ch}')
        for d in digits:
            tok=d+ch
            out.append(_single_tile_to_oracle(tok))
        digits=''
    if digits:
        raise ValueError('dangling digits in mpsz')
    return out


def _oracle_tile_to_token(i: int) -> str:
    if i==34: return '0m'
    if i==35: return '0p'
    if i==36: return '0s'
    if i < 0: return ''
    return format_tile(i)


def build_wall(hand_tiles: list[int], dora_indicators: list[int], nuki_count: int=0,
               visible_tiles: list[int] | None=None, game_mode: int=0) -> list[int]:
    wall=[4]*37
    # red fives are distinct identities but share a physical copy with normal 5.
    # mahjong-cpp's protocol expects a 37-count wall. Use the common default of
    # one red copy per suit when red is enabled: normal five=3, red five=1.
    for normal,red in ((4,34),(13,35),(22,36)):
        wall[normal]=3; wall[red]=1
    if game_mode==1:
        # Sanma removes 2-8m.
        for i in range(1,8): wall[i]=0
    for i in hand_tiles + dora_indicators + list(visible_tiles or []):
        if wall[i] <= 0:
            raise ValueError(f'oracle wall underflow for tile {i}')
        wall[i]-=1
    if nuki_count:
        north=30
        wall[north]-=nuki_count
        if wall[north] < 0:
            raise ValueError('oracle wall underflow for north')
    return wall


def build_mahjong_cpp_request(*, hand: str, game_mode: str='yonma', round_wind: str='1z',
                              seat_wind: str='2z', dora_indicators: list[str] | None=None,
                              nuki_count: int=0, visible_tiles: list[str] | None=None,
                              enable_reddora: bool=True, enable_uradora: bool=True,
                              enable_shanten_down: bool=True, enable_tegawari: bool=True) -> dict:
    gm=0 if game_mode in ('yonma','4p') else 1
    hand_arr=_mpsz_to_oracle_tiles(hand)
    dora=[_single_tile_to_oracle(x) for x in (dora_indicators or [])]
    visible=[]
    for x in (visible_tiles or []):
        visible.extend(_mpsz_to_oracle_tiles(x))
    return {
        'game_mode':gm,
        'round_wind':_single_tile_to_oracle(round_wind),
        'seat_wind':_single_tile_to_oracle(seat_wind),
        'dora_indicators':dora,
        'hand':hand_arr,
        'melds':[],
        'nuki_count':int(nuki_count),
        'wall':build_wall(hand_arr,dora,nuki_count,visible,gm),
        'enable_reddora':bool(enable_reddora),
        'enable_uradora':bool(enable_uradora),
        'enable_shanten_down':bool(enable_shanten_down),
        'enable_tegawari':bool(enable_tegawari),
        'version':'jong-ai-oracle-v2.0',
    }

@dataclass(frozen=True)
class OracleCandidate:
    discard: str
    shanten: int
    ukeire_total: int
    tenpai_probability: float | None
    win_probability: float | None
    expected_points: float | None

@dataclass(frozen=True)
class OracleResult:
    shanten: int
    candidates: tuple[OracleCandidate,...]
    searched: int | None
    time_us: int | None
    source: str='mahjong-cpp-reference'


def normalize_mahjong_cpp_response(data: dict, *, turn: int=1) -> OracleResult:
    if not data.get('success'):
        raise ValueError(data.get('err_msg','mahjong-cpp oracle error'))
    idx=max(0,min(17,int(turn)-1))
    candidates=[]
    for s in data.get('stats',[]):
        tile=int(s.get('tile',-1))
        necessary=s.get('necessary_tiles',[]) or []
        uke=sum(int(x.get('count',0)) for x in necessary)
        ten=s.get('tenpai_prob') or []
        win=s.get('win_prob') or []
        exp=s.get('exp_score') or []
        candidates.append(OracleCandidate(
            discard=_oracle_tile_to_token(tile),
            shanten=int(s.get('shanten',99)),
            ukeire_total=uke,
            tenpai_probability=float(ten[idx]) if len(ten)>idx else None,
            win_probability=float(win[idx]) if len(win)>idx else None,
            expected_points=float(exp[idx]) if len(exp)>idx else None,
        ))
    candidates.sort(key=lambda c:(-(c.expected_points if c.expected_points is not None else -1),
                                  -(c.win_probability if c.win_probability is not None else -1),
                                  c.shanten,-c.ukeire_total,c.discard))
    sh=data.get('shanten',{})
    return OracleResult(
        shanten=int(sh.get('all',99)),
        candidates=tuple(candidates),
        searched=data.get('searched'),
        time_us=data.get('time'),
    )


def call_mahjong_cpp(url: str, payload: dict, timeout: float=20.0) -> dict:
    body=json.dumps(payload).encode('utf-8')
    req=urlrequest.Request(url, data=body, headers={'Content-Type':'application/json'}, method='POST')
    try:
        with urlrequest.urlopen(req,timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except (URLError,HTTPError,TimeoutError) as e:
        raise RuntimeError(f'mahjong-cpp oracle unavailable: {e}') from e


def compare_jong_to_oracle(jong: dict, oracle: OracleResult) -> dict:
    jmap={c['discard']:c for c in jong.get('candidates',[])}
    rows=[]
    for oc in oracle.candidates:
        jc=jmap.get(oc.discard)
        if not jc: continue
        rows.append({
            'discard':oc.discard,
            'jong':{
                'shanten':jc.get('shanten'),
                'ukeire_total':jc.get('ukeire_total'),
                'tenpai_probability':jc.get('tenpai_probability'),
                'win_probability':jc.get('win_probability'),
                'expected_points':jc.get('expected_points'),
            },
            'oracle':asdict(oc),
            'delta':{
                'ukeire_total':(jc.get('ukeire_total') or 0)-oc.ukeire_total,
                'tenpai_probability':None if oc.tenpai_probability is None or jc.get('tenpai_probability') is None else jc['tenpai_probability']-oc.tenpai_probability,
                'win_probability':None if oc.win_probability is None or jc.get('win_probability') is None else jc['win_probability']-oc.win_probability,
                'expected_points':None if oc.expected_points is None or jc.get('expected_points') is None else jc['expected_points']-oc.expected_points,
            }
        })
    return {
        'jong_best': jong.get('best_by_ev') or jong.get('best_by_probability') or jong.get('best_by_shanten_ukeire'),
        'oracle_best': oracle.candidates[0].discard if oracle.candidates else None,
        'best_match': bool(oracle.candidates) and (jong.get('best_by_ev') or jong.get('best_by_probability') or jong.get('best_by_shanten_ukeire'))==oracle.candidates[0].discard,
        'oracle_shanten':oracle.shanten,
        'rows':rows,
    }
