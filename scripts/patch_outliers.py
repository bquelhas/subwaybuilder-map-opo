"""Remove pontos isolados >50km do AMP + reconstroi demand_data."""
import json, gzip
from collections import defaultdict

IN_PATH  = r'D:\porto-subway-builder\data\demand_data_v4.json.gz'
OUT_PATH = r'D:\porto-subway-builder\data\demand_data_v4_clean.json.gz'

# BBox geral conservadora para AMP+norte
LON_MIN, LAT_MIN = -8.95, 40.83
LON_MAX, LAT_MAX = -8.05, 41.50

with gzip.open(IN_PATH,'rt',encoding='utf-8') as f: d = json.load(f)
points = d['points']; pops = d['pops']
print(f"input: {len(points):,} points, {len(pops):,} pops")

# Identificar pontos OUT (outliers fora da bbox)
out_ids = set()
for p in points:
    lon, lat = p['location']
    if not (LON_MIN <= lon <= LON_MAX and LAT_MIN <= lat <= LAT_MAX):
        out_ids.add(p['id'])
print(f"pontos fora bbox: {len(out_ids)}")

# Manter points dentro da bbox
points_keep = [p for p in points if p['id'] not in out_ids]
print(f"points apos filtro: {len(points_keep):,}")

# Filtrar pops que NAO referenciam ids removidos
pops_keep = [pop for pop in pops if pop['residenceId'] not in out_ids and pop['jobId'] not in out_ids]
print(f"pops apos filtro: {len(pops_keep):,}  (removidos: {len(pops)-len(pops_keep)})")

# Reconstruir popIds de cada point
idx = {p['id']: p for p in points_keep}
for p in points_keep: p['popIds'] = []
for pop in pops_keep:
    if pop['residenceId'] in idx: idx[pop['residenceId']]['popIds'].append(pop['id'])
    if pop['jobId']       in idx: idx[pop['jobId']]['popIds'].append(pop['id'])

# Re-aplicar validator fix: points.residents = sum(pops.size por residenceId)
rep = defaultdict(int)
for pop in pops_keep: rep[pop['residenceId']] += pop['size']
changed = 0
for p in points_keep:
    if p['residents'] > 0:
        new_val = rep.get(p['id'], 0)
        if new_val != p['residents']:
            p['residents'] = new_val; changed += 1

res_tot = sum(p['residents'] for p in points_keep)
pop_tot = sum(p['size'] for p in pops_keep)
print(f"ajustados residents em {changed} pontos")
print(f"residents total: {res_tot:,}, pops total pessoas: {pop_tot:,}, delta: {abs(res_tot-pop_tot)}")

# Gravar
with gzip.open(OUT_PATH,'wt',encoding='utf-8') as f:
    json.dump({"points": points_keep, "pops": pops_keep}, f)

import os
print(f"\nOK {OUT_PATH} ({os.path.getsize(OUT_PATH)/1e6:.2f} MB)")

# Verify: max nearest-neighbor distance
import math
import numpy as np
from scipy.spatial import cKDTree
locs = np.array([p['location'] for p in points_keep])
cos_lat = math.cos(math.radians(41.15))
pts_km = np.column_stack([locs[:,0]*111*cos_lat, locs[:,1]*111])
tree = cKDTree(pts_km)
d_, idxs = tree.query(pts_km, k=2)
nn = d_[:,1]
print(f"\nNN distance stats: max={nn.max():.2f}km, p99={np.percentile(nn,99):.2f}km, p95={np.percentile(nn,95):.2f}km")
top = np.argsort(nn)[-3:]
for i in top: print(f"  {points_keep[i]['id']}: NN = {nn[i]:.2f} km")
