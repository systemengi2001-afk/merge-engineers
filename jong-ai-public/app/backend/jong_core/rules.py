from __future__ import annotations
from dataclasses import dataclass, asdict

# Internal tile indexes: 0..8=m, 9..17=p, 18..26=s, 27..33=z
YONMA_TILES=frozenset(range(34))
SANMA_TILES=frozenset({0,8,*range(9,34)})
SANMA_REMOVED_MANZU=frozenset(range(1,8))

@dataclass(frozen=True)
class RuleProfile:
    id: str
    players: int
    allowed_tiles: frozenset[int]
    chi_allowed: bool
    open_tanyao: bool
    north_nuki: bool
    complete_first: bool
    tsumo_loss: bool
    start_points: int
    return_points: int
    noten_penalty_total: int
    nuki_dora_han: int = 0
    notes: tuple[str,...]=()

    def public_dict(self) -> dict:
        d=asdict(self)
        d['allowed_tiles']=sorted(self.allowed_tiles)
        d['tile_types']=len(self.allowed_tiles)
        d['physical_tiles']=len(self.allowed_tiles)*4
        return d

PROFILES={
    'yonma_standard': RuleProfile(
        id='yonma_standard', players=4, allowed_tiles=YONMA_TILES,
        chi_allowed=True, open_tanyao=True, north_nuki=False,
        complete_first=False, tsumo_loss=False,
        start_points=25000, return_points=30000, noten_penalty_total=3000, nuki_dora_han=0,
        notes=('Baseline riichi profile; house-rule options remain configurable later.',),
    ),
    'sanma_standard': RuleProfile(
        id='sanma_standard', players=3, allowed_tiles=SANMA_TILES,
        chi_allowed=False, open_tanyao=True, north_nuki=True,
        complete_first=False, tsumo_loss=True,
        start_points=35000, return_points=40000, noten_penalty_total=2000, nuki_dora_han=1,
        notes=('Generic sanma baseline; exact platform/venue scoring varies.',),
    ),
    'osaka_sanma_v1': RuleProfile(
        id='osaka_sanma_v1', players=3, allowed_tiles=SANMA_TILES,
        chi_allowed=False, open_tanyao=False, north_nuki=True,
        complete_first=True, tsumo_loss=True,
        start_points=35000, return_points=40000, noten_penalty_total=1000, nuki_dora_han=1,
        notes=(
            'Initial Osaka-sanma profile for JONG AI.',
            'No 2-8 manzu, no chi, north nuki, no open tanyao, complete-first.',
            'Scoring/EV enforcement for open-hand legality, nuki value, chips and venue-specific payments is still incremental.',
        ),
    ),
}

def get_ruleset(ruleset: str | None=None, game_mode: str | None=None) -> RuleProfile:
    if ruleset:
        if ruleset not in PROFILES:
            raise ValueError(f'unknown ruleset: {ruleset}')
        return PROFILES[ruleset]
    if game_mode in (None,'yonma','4p'):
        return PROFILES['yonma_standard']
    if game_mode in ('sanma','3p'):
        return PROFILES['sanma_standard']
    if game_mode in ('osaka_sanma','osaka'):
        return PROFILES['osaka_sanma_v1']
    raise ValueError(f'unknown game_mode: {game_mode}')

def validate_counts_for_rules(counts: list[int], profile: RuleProfile) -> None:
    illegal=[i for i,n in enumerate(counts) if n and i not in profile.allowed_tiles]
    if illegal:
        from .tiles import format_tile
        names=', '.join(format_tile(i) for i in illegal)
        raise ValueError(f'{profile.id} does not use tile(s): {names}')
