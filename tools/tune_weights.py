#!/usr/bin/env python3
import json, itertools, pathlib, numpy as np
from collections import defaultdict

EV = pathlib.Path("data/events.jsonl")
OUT = pathlib.Path("bot/scoring/weights.json")

# class names we care about
CLASSES = ["quiet", "speech", "tv_music", "white_noise"]

def load_labeled_events(path):
    by_sid = defaultdict(list)
    for line in open(path, "r", encoding="utf-8"):
        e = json.loads(line)
        by_sid[e["session_id"]].append(e)
    samples = []
    for sid, es in by_sid.items():
        va = next((x for x in es if x.get("event") == "voice_analyzed"), None)
        tg = next((x for x in es if x.get("event") == "tag_voice"), None)
        if va and tg and tg.get("labels"):
            samples.append((sid, va["features"], va["score"], tg["labels"][0]))
    return samples

def norm_level_dbfs(db):
    # map [-60..0] dBFS to [0..1]
    return float(np.clip((db + 60.0) / 60.0, 0.0, 1.0))

def score_from_features(f, w):
    # w = (w_vad, w_flux, w_centroid, w_level, w_steady_bonus)
    lvl = norm_level_dbfs(f["level_dbfs"])
    vad = f["vad_fraction"]; flux = f["flux_norm"]; cen = f["centroid_norm"]
    steady_bonus = (1.0 - flux) if (-40.0 <= f["level_dbfs"] <= -25.0) else 0.0
    s = 100.0 - w[0]*vad - w[1]*flux - w[2]*cen - w[3]*lvl + w[4]*steady_bonus
    return float(np.clip(s, 0.0, 100.0))

def objective(samples, w):
    # maximize (quiet - speech) + (speech - tv_music) + 0.3*(white_noise - speech)
    by = {k: [] for k in CLASSES}
    for _, feats, _, tag in samples:
        by[tag].append(score_from_features(feats, w))
    means = {k: (np.mean(v) if v else None) for k, v in by.items()}
    if any(means[k] is None for k in ["quiet", "speech", "tv_music"]):
        return -1e9, means
    margin = (means["quiet"] - means["speech"]) + (means["speech"] - means["tv_music"])
    wn_bonus = 0 if means["white_noise"] is None else (means["white_noise"] - means["speech"])
    return margin + 0.3*wn_bonus, means

def grid_search(samples):
    grid = [10, 15, 20, 25, 30, 35]
    best_v, best_w, best_m = -1e9, None, None
    for w in itertools.product(grid, repeat=5):
        v, m = objective(samples, w)
        if v > best_v:
            best_v, best_w, best_m = v, w, m
    return best_w, best_m, best_v

if __name__ == "__main__":
    samples = load_labeled_events(EV)
    if not samples:
        print("No labeled samples yet. Use /tag to label recent clips.")
        exit(0)

    w, means, val = grid_search(samples)
    print("Best weights:", w)
    print("Class means:", {k: (round(v,1) if v is not None else None) for k,v in means.items()})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump({
        "w1_vad": w[0], "w2_flux": w[1], "w3_centroid": w[2],
        "w4_level": w[3], "w5_steady_bonus": w[4]
    }, open(OUT, "w"), indent=2)
    print("Wrote", OUT) 