from __future__ import annotations
from collections import Counter
from pathlib import Path
import math
from PIL import Image


def load_session_samples(sessions):
    """Load ordered crop/label pairs from already-audited sessions."""
    out=[]
    for session in sessions:
        crops=session.get('crops',[]); labels=session.get('labels',[])
        if len(crops)!=14 or len(labels)!=14:
            raise ValueError('audited session must contain 14 crops and 14 labels')
        out.extend((Path(p),lab,session['session_id']) for p,lab in zip(crops,labels))
    return out


def _expected_calibration_error(rows, bins=10):
    """Top-label ECE; lower is better. Keeps the review threshold honest."""
    if not rows: return None
    total=len(rows); ece=0.0
    for i in range(bins):
        lo=i/bins; hi=(i+1)/bins
        bucket=[r for r in rows if lo <= r[0] <= hi if (i==bins-1 or r[0] < hi)]
        if not bucket: continue
        mean_conf=sum(r[0] for r in bucket)/len(bucket)
        accuracy=sum(1 for _,ok in bucket if ok)/len(bucket)
        ece += len(bucket)/total*abs(mean_conf-accuracy)
    return ece


def _wilson_upper(errors, total, z=1.96):
    """One-sided conservative upper bound for an observed error rate."""
    if total <= 0: return None
    p=errors/total; z2=z*z; denom=1+z2/total
    center=p+z2/(2*total)
    radius=z*math.sqrt((p*(1-p)+z2/(4*total))/total)
    return (center+radius)/denom


def evaluate_classifier(classifier, samples, *, high_confidence_threshold=.90):
    """Evaluate on held-out, human-corrected crops including confidence safety."""
    total=0; correct=0; by_class=Counter(); class_correct=Counter(); confidences=[]; calibration=[]
    high_conf_total=0; high_conf_errors=0; session_totals=Counter(); session_correct=Counter()
    # Commercial evaluation can contain thousands of crops. Prefer a classifier's
    # batch path when available so promotion checks do not pay per-image model
    # invocation overhead; retain predict() compatibility for existing models.
    sample_list=list(samples)
    images=[Image.open(path).convert('RGB') for path,_,_ in sample_list]
    if hasattr(classifier, 'predict_batch'):
        predictions=list(classifier.predict_batch(images))
        if len(predictions) != len(sample_list):
            raise ValueError('predict_batch must return exactly one prediction per sample')
    else:
        predictions=[classifier.predict(img) for img in images]
    for (path,label,_sid),pred in zip(sample_list,predictions):
        confidence=float(pred.confidence); ok=pred.tile==label
        total += 1; by_class[label] += 1; session_totals[_sid] += 1; confidences.append(confidence); calibration.append((confidence,ok))
        if confidence >= high_confidence_threshold:
            high_conf_total += 1
            if not ok: high_conf_errors += 1
        if ok:
            correct += 1; class_correct[label] += 1; session_correct[_sid] += 1
    session_accuracy={sid:session_correct[sid]/n for sid,n in session_totals.items()}
    per_class={k: class_correct[k]/n for k,n in sorted(by_class.items())}
    return {'total':total,'correct':correct,'accuracy':correct/total if total else None,
            'mean_confidence':sum(confidences)/total if total else None,
            'expected_calibration_error':_expected_calibration_error(calibration),
            'high_confidence_threshold':high_confidence_threshold,
            'high_confidence_total':high_conf_total,'high_confidence_errors':high_conf_errors,
            'high_confidence_error_rate':high_conf_errors/high_conf_total if high_conf_total else 0.0,
            'high_confidence_error_upper_95':_wilson_upper(high_conf_errors,high_conf_total),
            'safe_auto_accept_rate':(high_conf_total-high_conf_errors)/total if total else 0.0,
            'perfect_session_rate':(sum(1 for v in session_accuracy.values() if v == 1.0)/len(session_accuracy) if session_accuracy else None),
            'worst_session_accuracy':(min(session_accuracy.values()) if session_accuracy else None),
            'session_count':len(session_accuracy),'per_class_accuracy':per_class}


def promotion_decision(candidate, baseline, *, min_holdout_tiles=28, min_accuracy_gain=.01,
                       max_class_regression=.10, max_ece_regression=.02,
                       max_high_confidence_error_rate=.05, max_auto_accept_regression=.05,
                       min_high_confidence_tiles=20, max_high_confidence_error_upper_95=.20,
                       max_perfect_session_regression=.05, max_worst_session_regression=.15):
    """Fail closed: accuracy gains cannot buy unsafe confidence or excessive review burden."""
    if candidate.get('total',0) < min_holdout_tiles or baseline.get('total',0) != candidate.get('total',0):
        return {'promote':False,'reason':'insufficient_or_mismatched_holdout'}
    ca=candidate.get('accuracy'); ba=baseline.get('accuracy')
    if ca is None or ba is None or ca < ba + min_accuracy_gain:
        return {'promote':False,'reason':'overall_accuracy_gain_below_gate'}
    common=set(candidate.get('per_class_accuracy',{})) & set(baseline.get('per_class_accuracy',{}))
    regressions={k:baseline['per_class_accuracy'][k]-candidate['per_class_accuracy'][k] for k in common
                 if baseline['per_class_accuracy'][k]-candidate['per_class_accuracy'][k] > max_class_regression}
    if regressions:
        return {'promote':False,'reason':'per_class_regression','regressions':regressions}
    ce=candidate.get('expected_calibration_error'); be=baseline.get('expected_calibration_error')
    if ce is not None and be is not None and ce > be + max_ece_regression:
        return {'promote':False,'reason':'confidence_calibration_regression','candidate_ece':ce,'baseline_ece':be}
    required=('expected_calibration_error','high_confidence_error_rate','safe_auto_accept_rate',
              'high_confidence_total','high_confidence_error_upper_95','perfect_session_rate',
              'worst_session_accuracy','session_count')
    if any(candidate.get(k) is None or baseline.get(k) is None for k in required):
        return {'promote':False,'reason':'missing_confidence_safety_evidence'}
    if candidate['high_confidence_total'] < min_high_confidence_tiles:
        return {'promote':False,'reason':'insufficient_high_confidence_evidence',
                'high_confidence_total':candidate['high_confidence_total']}
    upper=candidate['high_confidence_error_upper_95']
    if upper > max_high_confidence_error_upper_95:
        return {'promote':False,'reason':'high_confidence_error_uncertainty_too_high',
                'high_confidence_error_upper_95':upper}
    if candidate['session_count'] != baseline['session_count'] or candidate['session_count'] < 2:
        return {'promote':False,'reason':'insufficient_or_mismatched_session_evidence'}
    if candidate['perfect_session_rate'] + max_perfect_session_regression < baseline['perfect_session_rate']:
        return {'promote':False,'reason':'perfect_session_regression',
                'candidate_perfect_session_rate':candidate['perfect_session_rate'],
                'baseline_perfect_session_rate':baseline['perfect_session_rate']}
    if candidate['worst_session_accuracy'] + max_worst_session_regression < baseline['worst_session_accuracy']:
        return {'promote':False,'reason':'worst_session_regression',
                'candidate_worst_session_accuracy':candidate['worst_session_accuracy'],
                'baseline_worst_session_accuracy':baseline['worst_session_accuracy']}
    hcer=candidate['high_confidence_error_rate']
    if hcer > max_high_confidence_error_rate:
        return {'promote':False,'reason':'unsafe_high_confidence_errors','high_confidence_error_rate':hcer}
    candidate_accept=candidate['safe_auto_accept_rate']; baseline_accept=baseline['safe_auto_accept_rate']
    if candidate_accept + max_auto_accept_regression < baseline_accept:
        return {'promote':False,'reason':'review_burden_regression',
                'candidate_safe_auto_accept_rate':candidate_accept,'baseline_safe_auto_accept_rate':baseline_accept}
    return {'promote':True,'reason':'heldout_gate_passed','accuracy_gain':ca-ba}
