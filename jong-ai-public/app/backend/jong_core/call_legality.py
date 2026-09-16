from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class CallContext:
    ruleset_id: str
    call_type: str  # chi / pon / kan
    completes_yaku_route: bool
    has_guaranteed_yaku_after_call: bool
    claimed_tile: str | None = None

@dataclass(frozen=True)
class CallLegality:
    legal: bool
    reason: str


def check_call_legality(ctx: CallContext) -> CallLegality:
    if ctx.ruleset_id == 'osaka_sanma_v1':
        if ctx.call_type == 'chi':
            return CallLegality(False,'大阪三麻ではチー不可')
        if ctx.call_type not in {'pon','kan'}:
            return CallLegality(False,'未対応の鳴き種別')
        # Conservative complete-first gate: do not allow an open call unless the
        # resulting route already guarantees a valid yaku. This intentionally errs
        # on the side of rejecting ambiguous calls until full yaku-route search lands.
        if not (ctx.has_guaranteed_yaku_after_call or ctx.completes_yaku_route):
            return CallLegality(False,'完全先付け: 鳴き後の役が確定していない')
        return CallLegality(True,'合法')
    if ctx.call_type not in {'chi','pon','kan'}:
        return CallLegality(False,'未対応の鳴き種別')
    return CallLegality(True,'合法')
