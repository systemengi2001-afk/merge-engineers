from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

from .tiles import parse_mpsz, format_tile

DRAGONS={31,32,33}
WINDS={27,28,29,30}
HONORS=set(range(27,34))

@dataclass(frozen=True)
class OpenMeld:
    kind: str  # pon / kan
    tile: str

    def tile_index(self) -> int:
        c=parse_mpsz(self.tile)
        if sum(c)!=1:
            raise ValueError(f"meld tile must identify one tile: {self.tile}")
        return next(i for i,n in enumerate(c) if n)

@dataclass(frozen=True)
class YakuRouteResult:
    guaranteed_yaku: tuple[str,...]
    possible_routes: tuple[str,...]
    legal_complete_first: bool
    reason: str

def _single_index(token: str) -> int:
    c=parse_mpsz(token)
    if sum(c)!=1:
        raise ValueError(f"expected one tile: {token}")
    return next(i for i,n in enumerate(c) if n)

def analyze_open_yaku_routes(
    concealed_hand: str,
    melds: Iterable[OpenMeld],
    *,
    round_wind: str='1z',
    seat_wind: str='2z',
) -> YakuRouteResult:
    counts=parse_mpsz(concealed_hand)
    melds=tuple(melds)
    for m in melds:
        if m.kind not in {'pon','kan'}:
            raise ValueError(f"unsupported open meld kind: {m.kind}")

    round_i=_single_index(round_wind)
    seat_i=_single_index(seat_wind)

    guaranteed=[]
    possible=[]

    meld_idxs=[m.tile_index() for m in melds]

    # A completed open triplet/kan of a value tile guarantees at least one yaku.
    for i in meld_idxs:
        if i in DRAGONS:
            guaranteed.append('yakuhai_dragon')
        if i==round_i:
            guaranteed.append('yakuhai_round_wind')
        if i==seat_i:
            guaranteed.append('yakuhai_seat_wind')

    # Suit-route analysis. These are possible routes, not automatically guaranteed.
    suited=[i for i,n in enumerate(counts[:27]) if n]
    suited.extend(i for i in meld_idxs if i < 27)
    suits={i//9 for i in suited}
    has_honor=any(counts[i] for i in HONORS) or any(i in HONORS for i in meld_idxs)
    if len(suits)==1 and suits:
        if has_honor:
            possible.append('honitsu')
        else:
            possible.append('chinitsu')

    # Toitoi route remains possible only while all current open melds are triplet-like.
    if all(m.kind in {'pon','kan'} for m in melds):
        possible.append('toitoi')

    # Honroutou route is possible if every currently committed tile is terminal/honor.
    terminals={0,8,9,17,18,26}
    committed=[i for i,n in enumerate(counts) for _ in range(n)] + meld_idxs
    if committed and all(i in terminals or i in HONORS for i in committed):
        possible.append('honroutou')

    # Complete-first gate: only yaku already guaranteed at call time are accepted.
    guaranteed=tuple(dict.fromkeys(guaranteed))
    possible=tuple(dict.fromkeys(possible))
    if guaranteed:
        return YakuRouteResult(
            guaranteed, possible, True,
            '鳴いた時点で役が確定: ' + ', '.join(guaranteed)
        )
    return YakuRouteResult(
        guaranteed, possible, False,
        '完全先付け: 現時点で確定役なし'
        + (('（候補: '+', '.join(possible)+'）') if possible else '')
    )

def check_osaka_call_from_hand(
    concealed_hand_after_call: str,
    *,
    call_type: str,
    called_tile: str,
    melds_after_call: Iterable[OpenMeld],
    round_wind: str='1z',
    seat_wind: str='2z',
) -> dict:
    if call_type == 'chi':
        return {
            'legal': False,
            'reason': '大阪三麻ではチー不可',
            'guaranteed_yaku': [],
            'possible_routes': [],
        }
    if call_type not in {'pon','kan'}:
        return {
            'legal': False,
            'reason': '未対応の鳴き種別',
            'guaranteed_yaku': [],
            'possible_routes': [],
        }

    # Validate called tile.
    _single_index(called_tile)
    result=analyze_open_yaku_routes(
        concealed_hand_after_call,
        tuple(melds_after_call),
        round_wind=round_wind,
        seat_wind=seat_wind,
    )
    return {
        'legal': result.legal_complete_first,
        'reason': result.reason,
        'guaranteed_yaku': list(result.guaranteed_yaku),
        'possible_routes': list(result.possible_routes),
    }
