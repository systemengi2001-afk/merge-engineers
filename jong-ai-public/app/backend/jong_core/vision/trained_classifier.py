from __future__ import annotations
import pickle
from pathlib import Path
import numpy as np
from PIL import Image
from .tile_classifier import TileClassifier, TilePrediction


def _features(roi):
    import cv2
    if isinstance(roi, Image.Image): im=np.asarray(roi.convert('RGB'))
    else: im=np.asarray(roi)
    im=cv2.resize(im,(64,96),interpolation=cv2.INTER_AREA)
    gray=cv2.cvtColor(im,cv2.COLOR_RGB2GRAY)
    hog=cv2.HOGDescriptor((64,96),(16,16),(8,8),(8,8),9)
    h=hog.compute(gray).reshape(-1)
    # colour histogram helps distinguish red-five / red bamboo while HOG carries identity.
    hsv=cv2.cvtColor(im,cv2.COLOR_RGB2HSV)
    hist=[]
    for c,bins,rng in [(0,12,(0,180)),(1,8,(0,256))]:
        x=cv2.calcHist([hsv],[c],None,[bins],list(rng)).reshape(-1); x=x/(x.sum()+1e-9); hist.extend(x)
    return np.concatenate([h,np.asarray(hist,dtype=np.float32)]).astype(np.float32)

class SklearnTileClassifier(TileClassifier):
    name='sklearn_hog_svm_v6.0'
    def __init__(self, model_path):
        with open(model_path,'rb') as f: self.bundle=pickle.load(f)
    def predict(self, roi):
        x=_features(roi).reshape(1,-1); model=self.bundle['model']
        p=model.predict_proba(x)[0]; j=int(np.argmax(p))
        return TilePrediction(str(model.classes_[j]),float(p[j]))

def train_model(samples, output_path):
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    X=np.stack([_features(im) for im,_ in samples]); y=np.asarray([lab for _,lab in samples])
    model=make_pipeline(StandardScaler(),LogisticRegression(max_iter=3000,C=2.0,class_weight='balanced'))
    model.fit(X,y)
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    with open(output_path,'wb') as f: pickle.dump({'model':model,'feature':'hog+hsv','version':'6.0'},f)
    return model
