from __future__ import annotations
import random

from .rules import get_ruleset
from .tiles import format_tile

def counts_to_mpsz(counts: list[int]) -> str:
    parts=[]
    for base,suit in ((0,'m'),(9,'p'),(18,'s'),(27,'z')):
        digits=[]
        end=34 if suit=='z' else base+9
        for i in range(base,end):
            digits.extend([str((i-base)+1)]*counts[i])
        if digits:
            parts.append(''.join(digits)+suit)
    return ''.join(parts)

def generate_random_hand(*, ruleset: str='yonma_standard', tiles: int=14, seed: int | None=None) -> str:
    if tiles not in (13,14):
        raise ValueError('tiles must be 13 or 14')
    rng=random.Random(seed)
    profile=get_ruleset(ruleset,None)
    wall=[]
    for i in sorted(profile.allowed_tiles):
        wall.extend([i]*4)
    rng.shuffle(wall)
    counts=[0]*34
    for i in wall[:tiles]:
        counts[i]+=1
    return counts_to_mpsz(counts)

def generate_cases(count: int, *, ruleset: str='yonma_standard', seed: int=20260914,
                   turn_min: int=1, turn_max: int=18) -> list[dict]:
    if count < 1:
        return []
    rng=random.Random(seed)
    profile=get_ruleset(ruleset,None)
    game_mode='yonma' if profile.players==4 else 'sanma'
    out=[]
    for n in range(count):
        hand=generate_random_hand(ruleset=ruleset,tiles=14,seed=rng.randrange(1<<30))
        out.append({
            'id':f'{ruleset}-{n+1:05d}',
            'hand':hand,
            'game_mode':game_mode,
            'ruleset':ruleset,
            'turn':rng.randint(turn_min,turn_max),
            'round_wind':'1z',
            'seat_wind':'2z',
            'dora_indicators':[],
            'visible_tiles':[],
            'nuki_count':0,
        })
    return out
