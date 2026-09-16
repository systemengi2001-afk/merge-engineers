from pathlib import Path
import json,sys,tempfile
from PIL import Image
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from jong_core.vision.roi import segment_bottom_hand_tiles_and_draw,extract_normalized_tile_rois
from jong_core.vision.trained_classifier import train_model,SklearnTileClassifier
ROOT=Path(__file__).parents[1]; gt=json.loads((ROOT/'vision_dataset/real_photo_labels.v6.0.json').read_text())
data={}
for stem,labs in gt.items():
 im=Image.open(ROOT/'vision_dataset/raw'/f'{stem}.jpeg').convert('RGB'); n=extract_normalized_tile_rois(im,segment_bottom_hand_tiles_and_draw(im)); data[stem]=(n['all_rois'],labs)
# Leakage-resistant leave-one-photo-out; unseen classes are counted wrong, not skipped.
rows=[]; correct=0; total=0
for hold in data:
 samples=[]
 for stem,(rois,labs) in data.items():
  if stem!=hold: samples += list(zip(rois,labs))
 with tempfile.NamedTemporaryFile(suffix='.pkl') as f:
  train_model(samples,f.name); clf=SklearnTileClassifier(f.name)
  preds=[clf.predict(x).tile for x in data[hold][0]]; labs=data[hold][1]
 c=sum(a==b for a,b in zip(preds,labs)); correct+=c; total+=len(labs)
 rows.append({'photo':hold,'correct':c,'total':len(labs),'accuracy':c/len(labs),'predictions':preds,'ground_truth':labs})
report={'protocol':'leave-one-photo-out cross-validation; each held-out photo excluded from training','photos':len(data),'tiles':total,'correct':correct,'tile_accuracy':correct/total,'rows':rows,'limitations':['Only four manually transcribed photos / 56 tile ROIs.','Some tile identities occur in only one photo and are therefore impossible for a closed-set held-out fold to learn.','Labels are manually transcribed from the supplied photos and have not been independently double-annotated.','This result is not a commercial-quality accuracy claim.']}
(ROOT/'real-photo-classifier-eval.v6.0.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:report[k] for k in ['photos','tiles','correct','tile_accuracy']},indent=2));
for r in rows: print(r['photo'],r['correct'],'/14',round(r['accuracy'],3))
