#!/bin/sh
# Met les traductions françaises du Music Quiz (récupérées de Lokalise) dans la bêta MA
# locale, pour les voir en contexte avant leur publication officielle.
#
# Usage, sur l'hôte Docker (LXC 119), dans ~/quiz-fr :
#   export LOKALISE_TOKEN='...'
#   sh quiz_fr_local.sh
#
# Ce que ça fait (sans toucher à l'image MA) :
#   1. récupère tes traductions françaises du quiz depuis Lokalise ;
#   2. serveur : copie le fr.json de MA et y ajoute les textes du quiz ;
#   3. interface : reconstruit l'interface de MA 2.11.0b11 (frontend 2.17.381) avec ces textes,
#      dans un conteneur Node jetable ;
#   4. affiche les deux lignes à ajouter au docker-compose.yml de ~/ma-beta.
set -e
MA=${MA_CONTAINER:-ma-beta}
FRONTEND_TAG=${FRONTEND_TAG:-2.17.381}
cd "$(dirname "$0")"
DIR=$(pwd)

py() { docker exec "$MA" sh -c "python3 -c \"$1\" 2>/dev/null || python -c \"$1\""; }

echo "== 1. Traductions depuis Lokalise"
python3 lokalise_quiz_fr.py --export "$DIR"

echo "== 2. Serveur"
TR=$(py "import music_assistant,os;print(os.path.join(os.path.dirname(music_assistant.__file__),'translations'))")
docker cp "$MA:$TR/fr.json" "$DIR/fr_server_original.json"
python3 - "$DIR/fr_server_original.json" "$DIR/quiz_fr_server.json" "$DIR/fr_server.json" <<'PY'
import json, sys
base = json.load(open(sys.argv[1], encoding="utf-8"))
add = json.load(open(sys.argv[2], encoding="utf-8"))
for key, text in add.items():
    node = base
    parts = key.split(".")
    for p in parts[:-1]:
        node = node.setdefault(p, {})
    node[parts[-1]] = text
json.dump(base, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=4)
print(f"  {len(add)} texte(s) ajoutés au fr.json du serveur")
PY

echo "== 3. Interface (quelques minutes)"
if [ ! -d frontend-src ]; then
  git clone -q --depth 1 -b "$FRONTEND_TAG" https://github.com/music-assistant/frontend frontend-src
fi
git -C frontend-src checkout -q -- src/translations/fr.json
python3 - frontend-src/src/translations/fr.json "$DIR/quiz_fr_frontend.json" <<'PY'
import json, sys
base = json.load(open(sys.argv[1], encoding="utf-8"))
add = json.load(open(sys.argv[2], encoding="utf-8"))
for key, text in add.items():
    node = base
    parts = key.split(".")
    for p in parts[:-1]:
        node = node.setdefault(p, {})
    node[parts[-1]] = text
json.dump(base, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=4)
print(f"  {len(add)} texte(s) ajoutés au fr.json de l'interface")
PY
docker run --rm -v "$DIR/frontend-src:/app" -w /app node:22 \
  sh -c "corepack enable >/dev/null && pnpm install --frozen-lockfile --silent && pnpm exec vite build --logLevel error"
FE=$(py "import music_assistant_frontend,os;print(os.path.dirname(music_assistant_frontend.__file__))")

echo
echo "== 4. Ajoute ces deux lignes dans ~/ma-beta/docker-compose.yml, section volumes: du service MA,"
echo "   puis : cd ~/ma-beta && docker compose up -d --force-recreate"
echo
echo "      - $DIR/fr_server.json:$TR/fr.json:ro"
echo "      - $DIR/frontend-src/music_assistant_frontend:$FE:ro"
echo
echo "Pour revenir en arrière : retire ces deux lignes et recrée le conteneur."
