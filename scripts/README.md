# Build scripts — demand_data.json pipeline

Scripts que geraram o `demand_data.json` do mapa **Porto (AMP)** para o
Subway Builder.

> ⚠️ Estes scripts foram desenvolvidos iterativamente com o Claude (vibecoded)
> ao longo de várias releases (v0.1.0 → v0.4.3). Não são um pacote polido —
> partilho-os para quem quiser adaptar/aprender.

## Pipeline (3 etapas)

### 1. `gerar_empregos.py`
Extrai polos de emprego a partir de OSM:

- **POIs**: amenidades (hospital, university, school, clinic), offices, shops (mall, supermarket, department_store), railway stations
- **Landuse**: zonas `industrial`, `commercial`, `retail`, `office`
- Guarda como GeoPackage (`pois_emprego.gpkg`, `landuse_emprego.gpkg`)

Dependências: `pyrosm`, `geopandas`.

### 2. `gerar_demand_final_v4.py`
O core do pipeline. Junta múltiplas fontes:

- **INE BGRI21** (subsecções estatísticas, censos 2021) → residentes por polígono
- **COS 2018 v3 Série 2** (DGT — Carta Ocupação do Solo, 83 classes) → densidade de emprego por classe
- **PDM Porto** (Qualificação Funcional Municipal) → refina peso em Porto
- **OSM POIs + landuse** (de `gerar_empregos.py`) → localização exacta de empregos
- **Fonte manual** (56 pontos curados no script) — Aeroporto SAC=9000, Leixões=5000, hospitais, universidades, shoppings, estádios, casinos

Lógica:
- Pares O/D com peso pela distância
- `CAPTIVE_MULT` por município (Porto ×1.8, Gaia ×1.6, Matosinhos ×1.35, Maia ×1.15, etc.) — reflete taxa de motorização
- `drive_seconds` com 5 buckets de distância + fator de densidade populacional (metro-competitive em zonas urbanas densas)
- Cap **5000 empregos/ponto** OSM para evitar concentrações artificiais
- Boost especial para POIs turísticos/culturais (Torre Clérigos, Casa da Música, Serralves)

Output: `demand_data_v4.json.gz`

### 3. `patch_outliers.py`
Limpeza final para passar o validator do Railyard:

- Remove pontos fora do bbox AMP (`-8.95, 40.83, -8.05, 41.50`)
- Reconstrói `popIds` de cada point
- **Corrige `residents = sum(pops.size per residenceId)`** — validator do Railyard exige esta igualdade
- Reporta max nearest-neighbor distance (deve ficar <5 km)

Output: `demand_data_v4_clean.json.gz`

## Resultado (v0.2.1)

| Métrica | Valor |
|---|---|
| Points | 48.485 |
| O/D pairs | 59.476 |
| População simulada | 1.19M |
| Cobertura do total AMP | ~70% |
| NN distance max | 2.74 km |

## Contexto extra

- Bbox AMP: `[-8.95, 40.83, -8.05, 41.50]`
- Env: Python 3.13 conda, deps chave: `geopandas`, `pyrosm`, `numpy`, `scipy` (cKDTree)
- `portugal-latest.osm.pbf` de Geofabrik como input OSM
- INE BGRI21 shapefile do site do INE (subsecções + variáveis censos 2021)
- COS2018 v3 Série 2 GPKG da DGT
- PDM Porto do Portal do Munícipe

## Como adaptar para outra cidade

1. Muda `BBOX` para a tua área
2. Adapta os 56 pontos manuais (linhas dentro do `gerar_demand_final_v4.py`)
3. Substitui a fonte de residentes (INE PT → INSEE FR / Census US / etc.)
4. Substitui o COS (equivalente do teu país: Corine Land Cover europeu funciona)
5. `CAPTIVE_MULT` requer conhecimento local sobre taxa de motorização
