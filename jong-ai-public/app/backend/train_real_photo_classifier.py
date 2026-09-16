from pathlib import Path
import json,sys
from PIL import Image
sys.path.insert(0,str(Path(__file__).parent))
from jong_core.vision.roi import segment_bottom_hand_tiles_and_draw,extract_normalized_tile_rois
from jong_core.vision.trained_classifier import train_model,_features
ROOT=Path(__file__).parents[1]; labels=json.loads((ROOT/'vision_dataset/real_photo_labels.v6.0.json').read_text())
samples=[]
for stem,labs in labels.items():
 im=Image.open(ROOT/'vision_dataset/raw'/f'{stem}.jpeg').convert('RGB')
 n=extract_normalized_tile_rois(im,segment_bottom_hand_tiles_and_draw(im))
 assert n and len(n['all_rois'])==14
 samples += list(zip(n['all_rois'],labs))
train_model(samples,ROOT/'models/tile_classifier_v6.0.pkl')
print('trained',len(samples),'real-photo ROIs')
