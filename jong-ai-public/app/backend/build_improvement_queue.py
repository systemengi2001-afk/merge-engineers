from __future__ import annotations
import argparse,json
from pathlib import Path
from jong_core.improvement_planner import build_improvement_queue, compare_benchmark_summaries

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--diagnostics',required=True)
    ap.add_argument('--out',default='improvement-queue.json')
    ap.add_argument('--limit',type=int,default=100)
    ap.add_argument('--before')
    ap.add_argument('--after')
    args=ap.parse_args()

    diagnostics=json.loads(Path(args.diagnostics).read_text())
    queue=build_improvement_queue(diagnostics,limit=args.limit)
    if args.before and args.after:
        before=json.loads(Path(args.before).read_text())
        after=json.loads(Path(args.after).read_text())
        queue['benchmark_delta']=compare_benchmark_summaries(before,after)
    Path(args.out).write_text(json.dumps(queue,ensure_ascii=False,indent=2))
    print(json.dumps({'plans':queue['plans'],'layer_counts':queue['layer_counts']},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
