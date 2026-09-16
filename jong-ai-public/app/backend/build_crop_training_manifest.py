from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).parent))
from jong_core.vision.supervised_crops import audit_labeled_crop_sessions,deterministic_group_split
p=argparse.ArgumentParser(); p.add_argument('training_dir'); p.add_argument('--output',default='crop-training-manifest.json'); p.add_argument('--holdout',type=float,default=.2); a=p.parse_args()
audit=audit_labeled_crop_sessions(a.training_dir); split=deterministic_group_split(audit,holdout_fraction=a.holdout)
out={'audit':{k:v for k,v in audit.items() if k!='sessions'},'split':split,'limitations':['Labels come from user correction UI and are not independently double-annotated.','Held-out accuracy must be reported only after enough independent real-table sessions/classes exist.']}
Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'accepted_sessions':audit['accepted_sessions'],'tiles':audit['tiles'],'evaluation_ready':split['evaluation_ready']},ensure_ascii=False))
