"""v6.38 confidence-safe real-table retraining + promotion evaluation.
Does not overwrite production model unless the held-out gate passes.
"""
from pathlib import Path
import argparse,json,shutil,sys
from PIL import Image
sys.path.insert(0,str(Path(__file__).parent))
from jong_core.vision.supervised_crops import audit_labeled_crop_sessions,deterministic_group_split
from jong_core.vision.model_promotion import load_session_samples,evaluate_classifier,promotion_decision
from jong_core.vision.trained_classifier import train_model,SklearnTileClassifier
p=argparse.ArgumentParser(); p.add_argument('training_dir'); p.add_argument('--baseline',required=True); p.add_argument('--candidate',default='models/tile_classifier_candidate.pkl'); p.add_argument('--promote-to'); p.add_argument('--report',default='vision-promotion-report.json'); a=p.parse_args()
audit=audit_labeled_crop_sessions(a.training_dir); split=deterministic_group_split(audit)
report={'audit':{k:audit[k] for k in ('accepted_sessions','rejected_sessions','tiles','class_counts')},'split':{k:split[k] for k in split if k not in ('train','holdout')}}
if not split['evaluation_ready']:
 report['decision']={'promote':False,'reason':split['reason']}; Path(a.report).write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2)); raise SystemExit(2)
train=load_session_samples(split['train']); holdout=load_session_samples(split['holdout'])
train_model([(Image.open(path).convert('RGB'),label) for path,label,_ in train],a.candidate)
candidate=evaluate_classifier(SklearnTileClassifier(a.candidate),holdout); baseline=evaluate_classifier(SklearnTileClassifier(a.baseline),holdout)
decision=promotion_decision(candidate,baseline); report.update({'train_tiles':len(train),'holdout_tiles':len(holdout),'baseline':baseline,'candidate':candidate,'decision':decision})
if decision['promote'] and a.promote_to: shutil.copy2(a.candidate,a.promote_to); report['promoted_to']=a.promote_to
Path(a.report).write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2)); raise SystemExit(0 if decision['promote'] else 3)
