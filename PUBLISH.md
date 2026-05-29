# Como publicar o mapa OPO

## Pré-requisitos

- Conta GitHub
- Git instalado (Windows: Git for Windows; Linux: `apt install git`)
- ~70 MB de dados para publicar

## Passo 1 — Criar o repositório de dados

```bash
# Cria repo vazio no GitHub: subwaybuilder-map-opo (recomendo public)

git clone https://github.com/<USERNAME>/subwaybuilder-map-opo.git
cd subwaybuilder-map-opo

# Copia para aqui:
#   README.md   (deste pacote)
#   OPO.json    (deste pacote — edita a substituir <USERNAME>)

git add README.md OPO.json
git commit -m "Initial: README and update manifest"
git push
```

## Passo 2 — Publicar os ficheiros via GitHub Release

Os ficheiros `.pmtiles` e `.json.gz` são grandes para git (até 44 MB). Solução: pôr na release.

```bash
# Via gh CLI (recomendado)
gh release create v0.1.0 \
  D:\porto-subway-builder\export\OPO_ubuntu\tiles\OPO.pmtiles \
  D:\porto-subway-builder\export\OPO_ubuntu\cities\data\OPO\demand_data.json.gz \
  D:\porto-subway-builder\export\OPO_ubuntu\cities\data\OPO\roads.geojson.gz \
  D:\porto-subway-builder\export\OPO_ubuntu\cities\data\OPO\buildings_index.json.gz \
  D:\porto-subway-builder\export\OPO_ubuntu\cities\data\OPO\runways_taxiways.geojson.gz \
  D:\porto-subway-builder\export\OPO_ubuntu\cities\data\OPO\ocean_depth_index.json.gz \
  D:\porto-subway-builder\export\OPO_ubuntu\cities\data\OPO\config.json \
  --title "Porto (AMP) v0.1.0" \
  --notes "Lancamento inicial — AMP completa + Norte de PT low-zoom + drive-times realistas + captive boost."
```

Sem gh CLI: GitHub UI → Releases → New release → drag-and-drop dos 7 ficheiros.

## Passo 3 — Calcular sha256 e actualizar OPO.json

```bash
# No PowerShell
foreach ($f in "OPO.pmtiles","demand_data.json.gz","roads.geojson.gz","buildings_index.json.gz","runways_taxiways.geojson.gz","ocean_depth_index.json.gz","config.json") {
    $h = (Get-FileHash "D:\porto-subway-builder\export\OPO_ubuntu\<path>\$f" -Algorithm SHA256).Hash.ToLower()
    "$f : $h"
}

# Edita OPO.json substituindo cada "<fill>" pelo hash correspondente
git add OPO.json
git commit -m "Add sha256 hashes"
git push
```

## Passo 4 — Submeter ao registry oficial

```bash
# Fork do registry no GitHub UI: https://github.com/Subway-Builder-Modded/registry

git clone https://github.com/<USERNAME>/registry.git
cd registry

mkdir -p maps/opo-amp/gallery

# Copia para maps/opo-amp/:
#   manifest.json (deste pacote — edita a substituir <USERNAME> e github_id)
#   gallery/screenshot1.jpg
#   gallery/screenshot2.jpg

# Descobre o github_id (numerico):
# curl https://api.github.com/repos/<USERNAME>/subwaybuilder-map-opo | grep '"id"' | head -1

git add maps/opo-amp/
git commit -m "Add Porto (AMP) map by <USERNAME>"
git push origin <branch>

# Abre Pull Request para Subway-Builder-Modded/registry
```

## Passo 5 — Aguardar aprovação

Os maintainers do `Subway-Builder-Modded/registry` revêem PRs. Quando aprovado, o teu mapa aparece no Railyard de todos os utilizadores.

## Updates futuros

Quando lançares uma nova versão:

1. `gh release create v0.2.0 ...` (novos ficheiros)
2. Edita `OPO.json` (version + URLs + hashes)
3. `git commit && git push`
4. Os Railyards dos utilizadores detectam a nova versão via `update.url` e fazem download automático.

## Notas legais

- Inclui no README do repo: **"© INE Censos 2021, CC BY 4.0"** e **"© OpenStreetMap contributors, ODbL"**.
- Recomenda-se licença CC BY-SA 4.0 para o conteúdo derivado.
