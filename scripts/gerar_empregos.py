import json

import geopandas as gpd
import pandas as pd
import pyrosm

BBOX = [-8.80, 40.85, -8.30, 41.40]
PBF = r"D:\porto-subway-builder\data\raw\portugal-latest.osm.pbf"

print("A ler OSM PBF...")
osm = pyrosm.OSM(PBF, bounding_box=BBOX)

# === 1. POIs (amenidades e shops) ===
print("A extrair POIs...")
pois = osm.get_pois(
    custom_filter={
        "amenity": ["hospital", "university", "college", "school", "clinic"],
        "office": True,
        "shop": ["mall", "supermarket", "department_store", "hypermarket"],
        "railway": ["station", "halt"],
    }
)

if pois is not None:
    pois = pois.to_crs(epsg=4326)
    pois["centroid"] = pois.geometry.centroid
    pois_m = pois.to_crs(epsg=3763)
    pois["area_m2"] = pois_m.geometry.area.fillna(100).clip(lower=100)
    print(f"POIs: {len(pois)}")
    print(
        "Amenity:",
        pois["amenity"].value_counts().head(10).to_string()
        if "amenity" in pois.columns
        else "N/A",
    )
    print(
        "Shop:",
        pois["shop"].value_counts().head(10).to_string()
        if "shop" in pois.columns
        else "N/A",
    )
    print(
        "Office:",
        pois["office"].value_counts().head(5).to_string()
        if "office" in pois.columns
        else "N/A",
    )
    print(
        "Area media por amenity:",
        pois.groupby("amenity")["area_m2"]
        .mean()
        .sort_values(ascending=False)
        .head(10)
        .to_string()
        if "amenity" in pois.columns
        else "N/A",
    )
else:
    print("Nenhum POI encontrado")
    pois = gpd.GeoDataFrame()

# === 2. Landuse (zonas industriais, comerciais) ===
print("\nA extrair landuse...")
try:
    landuse = osm.get_landuse()
    if landuse is not None:
        landuse = landuse[
            landuse["landuse"].isin(["industrial", "commercial", "retail", "office"])
        ]
        landuse = landuse.to_crs(epsg=4326)
        landuse["centroid"] = landuse.geometry.centroid
        landuse_m = landuse.to_crs(epsg=3763)
        landuse["area_m2"] = landuse_m.geometry.area.fillna(1000).clip(lower=500)
        print(f"Zonas landuse: {len(landuse)}")
        print(landuse["landuse"].value_counts().to_string())
        print(
            "Area media por tipo:",
            landuse.groupby("landuse")["area_m2"]
            .mean()
            .sort_values(ascending=False)
            .to_string(),
        )
    else:
        print("Nenhuma zona landuse encontrada")
        landuse = gpd.GeoDataFrame()
except Exception as e:
    print(f"Erro landuse: {e}")
    landuse = gpd.GeoDataFrame()

# === 3. Guardar para próxima etapa ===
pois_save = pois.drop(columns=["centroid"])
landuse_save = landuse.drop(columns=["centroid"])
pois_save.to_file(r"D:\porto-subway-builder\data\pois_emprego.gpkg", driver="GPKG")
landuse_save.to_file(
    r"D:\porto-subway-builder\data\landuse_emprego.gpkg", driver="GPKG"
)
print("\nFicheiros guardados.")
print(f"Total POIs: {len(pois)} | Total landuse: {len(landuse)}")
