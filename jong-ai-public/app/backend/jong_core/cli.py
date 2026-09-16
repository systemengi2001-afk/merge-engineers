from __future__ import annotations

import argparse
import json
from .analyzer import analyze_hand


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("hand", help="MPSZ hand, e.g. 123456m123p45677s")
    p.add_argument("--visible", nargs="*", default=[], help="additional visible tiles")
    args = p.parse_args()
    print(json.dumps(analyze_hand(args.hand, args.visible), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
