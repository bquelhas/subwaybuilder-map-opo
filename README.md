# Porto (AMP) — mapa para Subway Builder

Mapa cobrindo os 17 municípios da Área Metropolitana do Porto (1.7M habitantes), construído a partir de dados do INE BGRI21 (subsecções estatísticas), OpenStreetMap e curadoria manual de POIs portuenses.

## Features

- **17 municípios**: Porto, Vila Nova de Gaia, Matosinhos, Maia, Valongo, Gondomar, Vila do Conde, Póvoa de Varzim, Santo Tirso, Trofa, Paredes, Espinho, Santa Maria da Feira, São João da Madeira, Oliveira de Azeméis, Arouca, Vale de Cambra.
- **24.816 pontos** de procura, **54.643 pops** simuladas, **1.09M passageiros**, **cobertura 64.3%** da população real.
- **Drive-times realistas** (19 km/h médio urbano) — metro fica genuinamente competitivo no centro.
- **Captive boost** para zonas urbanas densas (Porto 1.8×, Matosinhos/Gaia 1.35×, Maia 1.2×) modelando a menor taxa de motorização.
- **Cap de 5000 jobs/ponto** para evitar concentrações artificiais de grandes polígonos OSM.
- **56 pontos manuais** cobrindo aeroporto SAC, porto de Leixões, estádios (Dragão, Bessa), hospitais (S. João, Pedro Hispano, Sto. António), universidades (FEUP, ISEP, FLUP, UCP), shoppings, corporates (Sonae HQ, Continental Lousado, EXPONOR), casinos (Póvoa, Espinho).
- **30+ POIs turísticos** com labels: Torre dos Clérigos, Livraria Lello, Café Majestic, Mercado do Bolhão, Palácio da Bolsa, Sé do Porto, Casa da Música, Pavilhão Rosa Mota, Coliseu, Ribeira, Foz, Aliados, Boavista, Cedofeita, Bonfim, Paranhos, Caves do Vinho do Porto, Mosteiro da Serra do Pilar.
- **Norte de Portugal** a baixa zoom: Braga, Aveiro, Viana do Castelo, Bragança, Chaves, Vila Real, Guimarães — a geografia não acaba abruptamente nos limites do AMP.

## Instalação via Railyard

1. Abre o Railyard.
2. Pesquisa "Porto" ou "OPO" no browser de mapas.
3. Clica em Install.

## Instalação manual

Descarrega o pack (`OPO_porto_amp_*.zip`) da página de [Releases](../../releases) e segue as instruções no `README.txt` interno.

## Estrutura do repo

```
manifest.json              -- meta-dados para o registry do Subway Builder Modded
OPO.json                   -- ficheiro de update lido pelo Railyard
config.json                -- config da cidade (bbox, viewstate)
OPO.pmtiles                -- basemap vetorial (Tilezen + OMT translated)
demand_data.json.gz        -- origens/destinos simulados (24816 pts, 54643 pops)
roads.geojson.gz           -- rede viária para pathfinding
buildings_index.json.gz    -- edifícios indexados em grid
runways_taxiways.geojson.gz -- pistas/taxiways do aeroporto SAC
ocean_depth_index.json.gz  -- placeholder
gallery/                   -- screenshots
```

## Fontes de dados

- **INE BGRI21** (Censos 2021, subsecção estatística) — Creative Commons via [Geoportal INE](https://mapas.ine.pt/)
- **OpenStreetMap** — ODbL via [Geofabrik](https://download.geofabrik.de/europe/portugal.html)
- POIs manuais e captive multipliers — curadoria do autor

## Licença

Dados derivados:
- Conteúdo deste mapa em si: CC BY-SA 4.0
- Dados OSM derivados: ODbL (a manter atribuição "© OpenStreetMap contributors")
- Dados INE BGRI21: CC BY 4.0 (manter atribuição "© INE, Censos 2021")
- Dados COS2018v2.0

## Changelog

- **v0.1.0** Lançamento inicial. AMP completa + Norte de PT a low-zoom + drive-times realistas + captive boost.
- **v0.2.0** Dados de Procura de COS2018v2.0 adicionados para empregos.
- **v0.2.1** Tentativa de fix para que funcione com o railyard.
