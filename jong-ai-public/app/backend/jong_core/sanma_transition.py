from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache

from .shanten import calculate_shanten
from .scoring import ScoreConfig, score_closed_hand

NORTH_INDEX = 30

@dataclass(frozen=True)
class SanmaEVResult:
    draws: int
    tenpai_probability: float
    win_probability: float
    expected_points: float
    average_win_points: float
    expected_future_nuki: float
    expected_future_north_kept: float
    north_policy: str
    model: str = 'sanma_optimal_north_policy_dp_v3.0'


def _draw_distribution(seen: tuple[int,...], allowed: tuple[int,...]):
    live=[(i,4-seen[i]) for i in allowed if seen[i] < 4]
    total=sum(n for _,n in live)
    if total <= 0:
        return []
    return [(i,n/total) for i,n in live]


def _clone_score_config(score_config: ScoreConfig, nuki_bonus: int) -> ScoreConfig:
    return ScoreConfig(
        dealer=score_config.dealer,
        round_wind=score_config.round_wind,
        seat_wind=score_config.seat_wind,
        riichi=score_config.riichi,
        tsumo=score_config.tsumo,
        dora_indicators=score_config.dora_indicators,
        red_dora_count=score_config.red_dora_count,
        players=score_config.players,
        tsumo_loss=score_config.tsumo_loss,
        nuki_dora_count=score_config.nuki_dora_count+nuki_bonus,
        chip_count=score_config.chip_count,
        chip_value_points=score_config.chip_value_points,
    )


def estimate_sanma_auto_nuki_ev(
    counts13: list[int],
    visible_counts: list[int],
    draws: int,
    score_config: ScoreConfig,
    allowed_tiles: set[int],
    *,
    auto_nuki: bool=True,
    north_policy: str='optimal',
) -> SanmaEVResult:
    """Finite-horizon self-draw EV with state-dependent north handling.

    `draws` counts ordinary turn opportunities.

    north_policy:
      - "optimal": compare keeping North in the hand vs extracting it and taking
        an immediate replacement draw; choose the branch with the higher
        (EV, win probability, tenpai probability).
      - "always_nuki": legacy behavior.
      - "keep": never extract a future North.

    `auto_nuki=False` is retained for backwards compatibility and behaves like
    north_policy="keep".
    """
    if draws < 0:
        raise ValueError('draws must be >= 0')
    if north_policy not in {'optimal','always_nuki','keep'}:
        raise ValueError('north_policy must be optimal, always_nuki, or keep')
    if not auto_nuki:
        north_policy='keep'

    allowed=tuple(sorted(allowed_tiles))

    @lru_cache(maxsize=None)
    def dp(hand: tuple[int,...], seen: tuple[int,...], turns_left: int, nuki_bonus: int):
        sh=int(calculate_shanten(hand)['shanten'])
        already_tenpai=sh <= 0
        if turns_left <= 0:
            return (0.0,1.0 if already_tenpai else 0.0,0.0,0.0,0.0)
        dist=_draw_distribution(seen,allowed)
        if not dist:
            return (0.0,1.0 if already_tenpai else 0.0,0.0,0.0,0.0)

        def process_kept_draw(tile: int, s2: tuple[int,...]):
            h14=list(hand); h14[tile]+=1
            if int(calculate_shanten(h14)['shanten']) < 0:
                cfg=_clone_score_config(score_config,nuki_bonus)
                scored=score_closed_hand(h14,cfg,winning_tile=tile)
                return (1.0,1.0,float(scored.points),0.0,1.0 if tile==NORTH_INDEX else 0.0)

            best=None
            for d in allowed:
                if h14[d] == 0:
                    continue
                h13=h14.copy(); h13[d]-=1
                w2,t2,e2,n2,k2=dp(tuple(h13),s2,turns_left-1,nuki_bonus)
                if int(calculate_shanten(h13)['shanten']) <= 0:
                    t2=1.0
                key=(e2,w2,t2)
                if best is None or key > best[0]:
                    best=(key,w2,t2,e2,n2,k2)
            if best is None:
                return (0.0,0.0,0.0,0.0,1.0 if tile==NORTH_INDEX else 0.0)
            _,w,t,e,n,k=best
            if tile==NORTH_INDEX:
                k += 1.0
            return (w,t,e,n,k)

        pwin=pten=ev=enuki=ekept=0.0
        for tile,p in dist:
            s2=list(seen); s2[tile]+=1
            s2t=tuple(s2)

            if tile == NORTH_INDEX:
                keep_branch=process_kept_draw(tile,s2t)

                if north_policy == 'keep':
                    chosen=keep_branch
                else:
                    # Nuki removes the North and immediately draws a replacement.
                    # It does not consume another ordinary turn.
                    nw,nt,ne,nn,nk=dp(hand,s2t,turns_left,nuki_bonus+1)
                    nuki_branch=(nw,nt,ne,1.0+nn,nk)

                    if north_policy == 'always_nuki':
                        chosen=nuki_branch
                    else:
                        keep_key=(keep_branch[2],keep_branch[0],keep_branch[1])
                        nuki_key=(nuki_branch[2],nuki_branch[0],nuki_branch[1])
                        chosen=nuki_branch if nuki_key >= keep_key else keep_branch

                w,t,e,n,k=chosen
            else:
                w,t,e,n,k=process_kept_draw(tile,s2t)

            pwin += p*w
            pten += p*t
            ev += p*e
            enuki += p*n
            ekept += p*k

        if already_tenpai:
            pten=1.0
        return pwin,pten,ev,enuki,ekept

    w,t,e,n,k=dp(tuple(counts13),tuple(visible_counts),draws,0)
    avg=e/w if w>0 else 0.0
    return SanmaEVResult(
        draws=draws,
        tenpai_probability=max(0,min(1,t)),
        win_probability=max(0,min(1,w)),
        expected_points=e,
        average_win_points=avg,
        expected_future_nuki=n,
        expected_future_north_kept=k,
        north_policy=north_policy,
    )
