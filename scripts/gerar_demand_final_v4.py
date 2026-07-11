"""
gerar_demand_final_v4.py — v0.2.0 do mapa Porto AMP

Diferencas vs v3 (v0.1.1):
- Drive-time mais granular: 5 buckets de distancia + factor densidade subsec
- Densidade > 8000 hab/km2: carros 30% mais lentos (centro historico Porto)
- Long-haul (>20km): mantem ~50 km/h efectivo (NAO reinfla CP)
- Validator fix INTEGRADO: points.residents = sum(pops.size por residenceId)
- Suporta input de polígonos PDM+COS via empregos_v4.gpkg (opcional)
"""
import geopandas as gpd
import pandas as pd
import numpy as np
import json, gzip, os
from collections import defaultdict
from scipy.spatial import cKDTree

BGRI_PATH    = r'D:\porto-subway-builder\data\INE\BGRI21_11A.gpkg'
POIS_PATH    = r'D:\porto-subway-builder\data\pois_emprego.gpkg'
LANDUSE_PATH = r'D:\porto-subway-builder\data\landuse_emprego.gpkg'
MANUAL_PATH  = r'D:\porto-subway-builder\data\pontos_manuais.json'
PDM_PATH     = r'D:\porto-subway-builder\data\pdm_porto_emp.gpkg'   # PASSO 4 - existe
COS_PATH     = r'D:\porto-subway-builder\data\cos2018_amp_emp.gpkg' # PASSO 3 - sera criado
OUTPUT_PATH  = r'D:\porto-subway-builder\data\demand_data_v4.json.gz'

POP_SIZE = 20
MAX_POPS = 60000
JOB_CAP  = 5000  # cap por ponto
MAX_DIST_KM = 40

# === Polarizacao (multiplica viajantes por municipio para emparelhar com empregos reais) ===
POLARIZACAO = {
    '1312':1.85,'1311':1.20,'1308':1.15,'0504':0.92,'0507':0.93,'1313':0.94,'1318':0.94,
    '1315':0.88,'1316':0.90,'1319':0.87,'1305':0.75,'1317':0.77,'1310':0.78,'1307':0.80,
    '1301':0.83,'1303':0.72,'1309':0.88
}
DEFAULT_POL = 0.85

# === Captive multiplier (zonas de baixa motorizacao, dependentes de TP) ===
# Codigos INE DTMN21 verificados pelos residentes BGRI21
CAPTIVE_MULT = {
    '1312': 1.80,  # Porto - core urbano denso
    '1317': 1.60,  # Vila Nova de Gaia - Linha D real e' a #1 do Metro
    '1308': 1.35,  # Matosinhos - urbano denso
    '1306': 1.20,  # Maia - misto, centro urbano
    '1304': 1.15,  # Gondomar
    '1315': 1.15,  # Valongo
    '0107': 1.15,  # Espinho
}
DEFAULT_CAPTIVE = 1.0

# === Pesos OSM (fallback) - usado quando nao temos PDM/COS ===
PESOS_OSM = {
    'hospital':2.5,'clinic':1.3,'university':2.2,'college':1.8,'school':1.4,
    'station':3.5,'halt':2.0,'bus_station':1.8,'ferry_terminal':2.0,
    'supermarket':0.9,'mall':1.3,'department_store':1.1,'hypermarket':1.0,
    'company':1.6,'government':1.8,'association':0.9,'estate_agent':0.7,'insurance':0.8,
    'attraction':0.4,'museum':0.3,'hotel':1.2,'hostel':0.6,'gallery':0.3,
    'industrial':0.9,'commercial':0.8,'retail':0.7,'office':1.4
}
DEFAULT_PESO_OSM = 0.8


def centroids_wgs84(g):
    c = g.to_crs(epsg=3763).geometry.centroid.to_crs(epsg=4326)
    return c.x.values, c.y.values

def get_peso_osm(row):
    for col in ['amenity','railway','tourism','shop','office','landuse']:
        v = row.get(col)
        if pd.notna(v) and str(v) in PESOS_OSM:
            return PESOS_OSM[str(v)]
    return DEFAULT_PESO_OSM

# === Drive-time realista (D7) ===
# Effective speeds aprox: 1km urbano denso = 7min; 25km auto-estrada = 28min
# Long-haul mantem competitividade do carro vs CP
TORTUOSIDADE = 1.30
PARKING_OVERHEAD = 1.15

def drive_seconds(dk_km, density_hab_per_km2=None):
    """Devolve (segundos, metros). dk_km e' distancia euclidiana origem->destino."""
    # Velocidade base por distancia (km/h)
    if dk_km < 2:    base = 18   # urbano denso, semaforos
    elif dk_km < 5:  base = 26   # urbano, estacionamento dificil
    elif dk_km < 10: base = 38   # peri-urbano, secundarias
    elif dk_km < 20: base = 55   # IC, VCI, secundarias rapidas
    else:            base = 80   # auto-estrada (A1/A28/A41) - mantem competitivo
    # Penalty por densidade da subseccao de origem (mais denso = mais lento no inicio)
    if density_hab_per_km2:
        if density_hab_per_km2 > 8000:
            base *= 0.7
        elif density_hab_per_km2 > 3000:
            base *= 0.85
        elif density_hab_per_km2 > 1000:
            base *= 0.95
    seconds = dk_km * TORTUOSIDADE / base * 3600 * PARKING_OVERHEAD
    meters  = dk_km * TORTUOSIDADE * 1000
    return round(seconds, 1), round(meters, 0)


# === 1. Residencias ===
print("[1/7] Residencias INE BGRI21...")
gdf = gpd.read_file(BGRI_PATH).to_crs(epsg=4326)
gdf = gdf[gdf['N_INDIVIDUOS'] > 0].copy().reset_index(drop=True)
gdf['lon'], gdf['lat'] = centroids_wgs84(gdf)
gdf['mun'] = gdf['DTMN21'].astype(str).str.zfill(4)
# densidade por subseccao em hab/km2
gdf['area_km2'] = gdf.to_crs(epsg=3763).geometry.area / 1e6
gdf['density'] = gdf['N_INDIVIDUOS'] / gdf['area_km2'].clip(lower=0.001)
print(f"  {len(gdf):,} subseccoes | {gdf['N_INDIVIDUOS'].sum():,} residentes")
print(f"  density p50={gdf['density'].quantile(0.50):.0f}  p90={gdf['density'].quantile(0.90):.0f}  p99={gdf['density'].quantile(0.99):.0f} hab/km2")


# === 2. Empregos por municipio (target total) ===
print("[2/7] Empregos por municipio (calibragem)...")
ms = gdf.groupby('mun').agg(
    pop_0_14=('N_INDIVIDUOS_0_14','sum'),
    pop_15_24=('N_INDIVIDUOS_15_24','sum'),
    pop_25_64=('N_INDIVIDUOS_25_64','sum'),
    pop_total=('N_INDIVIDUOS','sum'),
).reset_index()
ms['viajantes'] = ms['pop_25_64']*0.70 + ms['pop_0_14']*0.85 + ms['pop_15_24']*0.60
ms['pol'] = ms['mun'].map(POLARIZACAO).fillna(DEFAULT_POL)
ms['emp'] = (ms['viajantes'] * ms['pol']).round(0).astype(int)
mun_emp = dict(zip(ms['mun'], ms['emp']))
print(f"  Total AMP empregos modelados: {ms['emp'].sum():,}")


# === 3. Locais de emprego (combinar fontes) ===
print("[3/7] A combinar fontes de emprego (PDM + COS + OSM POIs + OSM landuse fallback)...")

job_records = []

# (a) PDM Porto (Porto município) — base poligonal
if os.path.exists(PDM_PATH):
    pdm = gpd.read_file(PDM_PATH, layer='pdm_emp').to_crs(epsg=4326)
    if 'lon' not in pdm.columns:
        pdm['lon'], pdm['lat'] = centroids_wgs84(pdm)
    if 'area_m2' not in pdm.columns:
        pdm['area_m2'] = pdm.to_crs(epsg=3763).geometry.area.fillna(100).clip(lower=100)
    pdm['peso'] = pdm['area_m2'] * pdm['peso_tipo']
    for _, r in pdm.iterrows():
        job_records.append({'lon': r['lon'], 'lat': r['lat'], 'area_m2': r['area_m2'],
                            'peso_tipo': r['peso_tipo'], 'peso': r['peso'], 'source': 'PDM'})
    print(f"  PDM Porto: {len(pdm)} poligonos")
else:
    print(f"  PDM nao encontrado em {PDM_PATH} - skip")

# (b) COS2018 fora do Porto município — base poligonal
if os.path.exists(COS_PATH):
    cos = gpd.read_file(COS_PATH).to_crs(epsg=4326)
    if 'lon' not in cos.columns:
        cos['lon'], cos['lat'] = centroids_wgs84(cos)
    if 'area_m2' not in cos.columns:
        cos['area_m2'] = cos.to_crs(epsg=3763).geometry.area.fillna(100).clip(lower=100)
    if 'peso_tipo' not in cos.columns:
        cos['peso_tipo'] = 1.0
    cos['peso'] = cos['area_m2'] * cos['peso_tipo']
    for _, r in cos.iterrows():
        job_records.append({'lon': r['lon'], 'lat': r['lat'], 'area_m2': r['area_m2'],
                            'peso_tipo': r['peso_tipo'], 'peso': r['peso'], 'source': 'COS'})
    print(f"  COS2018: {len(cos)} poligonos")
else:
    print(f"  COS nao encontrado em {COS_PATH} - usando OSM landuse como fallback fora do Porto")
    # OSM landuse fallback fora do Porto município (1312)
    if os.path.exists(LANDUSE_PATH):
        lu = gpd.read_file(LANDUSE_PATH).to_crs(epsg=4326)
        lu['lon'], lu['lat'] = centroids_wgs84(lu)
        lu['area_m2'] = lu.to_crs(epsg=3763).geometry.area.fillna(100).clip(lower=100)
        lu['peso_tipo'] = [get_peso_osm(r) for _, r in lu.iterrows()]
        lu['peso'] = lu['area_m2'] * lu['peso_tipo']
        # Filtrar para fora do Porto (centroide.lon, .lat fora do bbox apertado de Porto)
        # Approx: Porto município centro em -8.62, 41.16, raio ~6km
        d_porto = np.sqrt((lu['lon']+8.62)**2 + (lu['lat']-41.16)**2) * 111
        lu_fora = lu[d_porto > 7]  # fora de Porto município (~7km do centro)
        for _, r in lu_fora.iterrows():
            job_records.append({'lon': r['lon'], 'lat': r['lat'], 'area_m2': r['area_m2'],
                                'peso_tipo': r['peso_tipo'], 'peso': r['peso'], 'source': 'OSM_landuse'})
        print(f"  OSM landuse (fora Porto): {len(lu_fora)} poligonos")

# (c) OSM POIs — overlay de pontos (sempre)
if os.path.exists(POIS_PATH):
    pois = gpd.read_file(POIS_PATH).to_crs(epsg=4326)
    pois['lon'], pois['lat'] = centroids_wgs84(pois)
    pois['area_m2'] = pois.to_crs(epsg=3763).geometry.area.fillna(100).clip(lower=100)
    pois['peso_tipo'] = [get_peso_osm(r) for _, r in pois.iterrows()]
    pois['peso'] = pois['area_m2'] * pois['peso_tipo']
    for _, r in pois.iterrows():
        job_records.append({'lon': r['lon'], 'lat': r['lat'], 'area_m2': r['area_m2'],
                            'peso_tipo': r['peso_tipo'], 'peso': r['peso'], 'source': 'OSM_POI'})
    print(f"  OSM POIs: {len(pois)} pontos")

jobs = pd.DataFrame(job_records).dropna(subset=['lon','lat'])
print(f"  TOTAL: {len(jobs):,} locais ({jobs['source'].value_counts().to_dict()})")


# === 4. Distribuir empregos por municipio (cap iterativo) ===
print("[4/7] A distribuir empregos por municipio com cap iterativo...")
gdf_mun = gdf.dissolve(by='mun').reset_index()[['mun','geometry']].to_crs(epsg=4326)
jobs_geo = gpd.GeoDataFrame(jobs, geometry=gpd.points_from_xy(jobs.lon, jobs.lat), crs='EPSG:4326')
joined = gpd.sjoin(jobs_geo, gdf_mun.rename(columns={'mun':'mun_j'})[['mun_j','geometry']], how='left', predicate='within')
jobs['mun'] = joined['mun_j'].fillna('unknown').values
jobs['jobs'] = 0

def distribute_with_cap(grp, total, cap):
    if len(grp) == 0 or total <= 0: return None
    w = grp['peso'].values.astype(float)
    if w.sum() <= 0: return np.full(len(grp), max(1, total // max(1, len(grp))), dtype=int)
    n = len(grp); locked = np.zeros(n, dtype=bool); out = np.zeros(n, dtype=float)
    remaining = float(total)
    for _ in range(20):
        idx = ~locked
        if not idx.any(): break
        ws = w[idx].sum()
        if ws <= 0: break
        share = w[idx] / ws * remaining
        will_lock = share >= cap
        if will_lock.any():
            sub = np.where(idx)[0]
            for j, lk in zip(sub, will_lock):
                if lk:
                    out[j] = cap; locked[j] = True
            remaining = float(total) - out[locked].sum()
            if remaining <= 0: break
        else:
            out[np.where(idx)[0]] = share; break
    out = np.clip(np.round(out), 10, cap).astype(int)
    return out

for mun, grp_idx in jobs.groupby('mun').groups.items():
    grp = jobs.loc[grp_idx]
    tot = mun_emp.get(mun, 0)
    res = distribute_with_cap(grp, tot, JOB_CAP)
    if res is None:
        jobs.loc[grp_idx, 'jobs'] = 50
    else:
        jobs.loc[grp_idx, 'jobs'] = res
print(f"  total empregos atribuidos: {jobs['jobs'].sum():,}")
print(f"  pontos no cap (>={JOB_CAP}): {(jobs['jobs']>=JOB_CAP).sum()}")


# === 5. Construir points (residencial + emprego + manuais) ===
print("[5/7] Construir points...")
res_pts = [
    {"id": f"p_{r.BGRI2021}", "location": [round(r.lon,6), round(r.lat,6)],
     "jobs": 0, "residents": int(r.N_INDIVIDUOS), "popIds": []}
    for r in gdf.itertuples()
]
job_pts_auto = [
    {"id": f"j_{i:06d}", "location": [round(r.lon,6), round(r.lat,6)],
     "jobs": int(r.jobs), "residents": 0, "popIds": []}
    for i, (_, r) in enumerate(jobs.iterrows())
]
with open(MANUAL_PATH) as f: job_pts_manual = json.load(f)
job_pts = job_pts_auto + job_pts_manual
all_pts = res_pts + job_pts
pt_idx = {p['id']: p for p in all_pts}
print(f"  {len(res_pts):,} residenciais + {len(job_pts):,} emprego = {len(all_pts):,} total")


# === 6. Gerar pops O/D com drive-time densidade-aware + captive ===
print("[6/7] A gerar pops O/D com drive-time densidade-aware + captive...")
DEG2KM = 111.0
res_ll  = np.column_stack([gdf['lat'].values, gdf['lon'].values])
res_pop = gdf['N_INDIVIDUOS'].values
res_density = gdf['density'].values
res_mun_arr = gdf['mun'].values
res_ids = [f"p_{b}" for b in gdf['BGRI2021']]
job_ll = np.array([[j['location'][1], j['location'][0]] for j in job_pts])
job_j  = np.array([j['jobs'] for j in job_pts])
job_ids = [j['id'] for j in job_pts]
tree = cKDTree(job_ll * DEG2KM)

taxa = 0.55
captive_vec = np.array([CAPTIVE_MULT.get(m, DEFAULT_CAPTIVE) for m in res_mun_arr])
total_boost = float((res_pop * taxa * captive_vec).sum())
scale = min(1.0, MAX_POPS * POP_SIZE / total_boost)
print(f"  total viajantes (boost): {int(total_boost):,}  (sem boost: {int((res_pop*taxa).sum()):,})")
print(f"  scale: {scale:.4f}")

pops = []
rng = np.random.default_rng(42)
for i in range(len(res_pts)):
    mult = captive_vec[i]
    expected = res_pop[i] * taxa * scale * mult / POP_SIZE
    n_pops = int(expected) + (1 if rng.random() < (expected - int(expected)) else 0)
    if n_pops < 1: continue
    ck = res_ll[i] * DEG2KM
    idxs = np.array(tree.query_ball_point(ck, MAX_DIST_KM))
    if not len(idxs): continue
    dists = np.linalg.norm(job_ll[idxs]*DEG2KM - ck, axis=1).clip(min=0.5)
    w = job_j[idxs] / dists**1.5
    ws = w.sum()
    if ws == 0: continue
    chosen = rng.choice(len(idxs), size=n_pops, p=w/ws, replace=True)
    seen = {}
    for li in chosen: seen[li] = seen.get(li, 0) + 1
    src_density = res_density[i]
    for li, n in seen.items():
        ji = idxs[li]; dk = dists[li]
        secs, meters = drive_seconds(dk, src_density)
        for _ in range(n):
            pid = f"pop_{len(pops):06d}"
            pops.append({"id": pid, "size": POP_SIZE,
                         "residenceId": res_ids[i], "jobId": job_ids[ji],
                         "drivingSeconds": secs, "drivingDistance": meters})
            pt_idx[res_ids[i]]['popIds'].append(pid)
            pt_idx[job_ids[ji]]['popIds'].append(pid)
    if i % 3000 == 0: print(f"  {i:>5}/{len(res_pts)} res | {len(pops):,} pops")
    if len(pops) >= MAX_POPS: break

print(f"  TOTAL pops: {len(pops):,}")


# === 7. Validator fix INTEGRADO: points.residents = sum(pops.size por residenceId) ===
print("[7/7] Validator fix integrado: aplicar points.residents = sum(pops.size por residenceId)...")
rep = defaultdict(int)
for pop in pops:
    rep[pop['residenceId']] += pop['size']
changed = 0
for pt in all_pts:
    if pt['residents'] > 0:
        new_val = rep.get(pt['id'], 0)
        if new_val != pt['residents']:
            pt['residents'] = new_val
            changed += 1
res_tot  = sum(p['residents'] for p in all_pts)
pops_tot = sum(p['size'] for p in pops)
print(f"  ajustados: {changed} pontos | residents={res_tot:,} pops={pops_tot:,} delta={abs(res_tot-pops_tot)}")


with gzip.open(OUTPUT_PATH, 'wt', encoding='utf-8') as f:
    json.dump({"points": all_pts, "pops": pops}, f)
print(f"\nOK {OUTPUT_PATH}")
print(f"  Points: {len(all_pts):,} | Pops: {len(pops):,} | Pessoas: {len(pops)*POP_SIZE:,}")
print(f"  Cobertura: {len(pops)*POP_SIZE/1736228*100:.1f}%")
print(f"  Tamanho: {os.path.getsize(OUTPUT_PATH)/1e6:.2f} MB")
