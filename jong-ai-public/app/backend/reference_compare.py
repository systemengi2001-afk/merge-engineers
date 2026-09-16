from __future__ import annotations
import argparse,json
from jong_core.instant_analyzer import analyze_hand_instant
from jong_core.reference_oracle import (
    build_mahjong_cpp_request,call_mahjong_cpp,normalize_mahjong_cpp_response,compare_jong_to_oracle
)

def main():
    ap=argparse.ArgumentParser(description='Compare JONG AI against external mahjong-cpp reference server')
    ap.add_argument('--url',required=True)
    ap.add_argument('--hand',required=True)
    ap.add_argument('--game-mode',default='yonma')
    ap.add_argument('--ruleset',default=None)
    ap.add_argument('--turn',type=int,default=1)
    ap.add_argument('--round-wind',default='1z')
    ap.add_argument('--seat-wind',default='2z')
    ap.add_argument('--dora',action='append',default=[])
    ap.add_argument('--nuki-count',type=int,default=0)
    args=ap.parse_args()
    jong=analyze_hand_instant(args.hand,draws=max(1,min(6,args.turn)),game_mode=args.game_mode,ruleset=args.ruleset,nuki_count=args.nuki_count)
    payload=build_mahjong_cpp_request(hand=args.hand,game_mode=args.game_mode,round_wind=args.round_wind,seat_wind=args.seat_wind,dora_indicators=args.dora,nuki_count=args.nuki_count)
    raw=call_mahjong_cpp(args.url,payload)
    oracle=normalize_mahjong_cpp_response(raw,turn=args.turn)
    print(json.dumps(compare_jong_to_oracle(jong,oracle),ensure_ascii=False,indent=2))

if __name__=='__main__': main()
