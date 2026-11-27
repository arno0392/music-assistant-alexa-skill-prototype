#!/bin/sh
# Rebuild every patched file of the Alexa skill from the ORIGINAL files of the image.
# Run from the project folder (where docker-compose.yml is):  sh patches/rebuild.sh
# Safe: on any error the previous patches/src is kept untouched.
set -eu

BRANCH_URL="https://raw.githubusercontent.com/arno0392/music-assistant-alexa-skill-prototype/local-patches/patches"
SCRIPTS="fix_meta fix_apl fix_apl_buttons fix_apl_refresh fix_apl_time fix_live_page fix_live_report fix_apl_ux fix_apl_seek fix_apl_pause fix_stream_key fix_apl_followups fix_apl_sequencer fix_seek_offset fix_time_binds fix_apl_background"
FILES="skill/util.py skill/apl.py skill/apl_document.json skill/lambda_function.py skill/ma_control.py shared_store.py music_assistant_api/ma_routes.py alexa_api/alexa_routes.py"

[ -f docker-compose.yml ] || { echo "Lance ce script depuis le dossier du projet (docker-compose.yml)"; exit 1; }
IMAGE="${IMAGE:-$(docker compose config --images | head -n 1)}"
echo "Image : $IMAGE"

mkdir -p patches/scripts
for s in $SCRIPTS; do
    curl -fsSLo "patches/scripts/$s.py" "$BRANCH_URL/$s.py"
done
echo "Scripts telecharges."

NEW=patches/src.new
rm -rf "$NEW"
mkdir -p "$NEW/skill" "$NEW/music_assistant_api" "$NEW/alexa_api"
for f in $FILES; do
    # original file from the image itself, never the mounted (patched) one
    docker run --rm --entrypoint cat "$IMAGE" "/app/src/$f" > "$NEW/$f"
done
echo "Fichiers d'origine extraits de l'image."

P="python3 patches/scripts"
$P/fix_meta.py        "$NEW/skill/util.py"
$P/fix_apl.py         "$NEW/skill/apl.py"
$P/fix_apl_buttons.py "$NEW/skill/apl_document.json" "$NEW/skill/lambda_function.py"
$P/fix_apl_refresh.py "$NEW/skill/ma_control.py" "$NEW/skill/lambda_function.py"
$P/fix_apl_time.py    "$NEW/skill/apl_document.json" "$NEW/skill/ma_control.py" "$NEW/skill/lambda_function.py"
$P/fix_live_page.py   "$NEW"
$P/fix_live_report.py "$NEW"
$P/fix_apl_ux.py      "$NEW" "$NEW/skill/ma_control.py"
$P/fix_apl_seek.py    "$NEW"
$P/fix_apl_pause.py   "$NEW/skill/apl.py"
$P/fix_stream_key.py  "$NEW"
$P/fix_apl_followups.py "$NEW"
$P/fix_apl_sequencer.py "$NEW"
$P/fix_seek_offset.py "$NEW"
$P/fix_time_binds.py "$NEW"
$P/fix_apl_background.py "$NEW"

for f in $FILES; do
    case "$f" in
        *.py)   python3 -m py_compile "$NEW/$f" ;;
        *.json) python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$NEW/$f" ;;
    esac
done
find "$NEW" -name "__pycache__" -type d -exec rm -rf {} +

rm -rf patches/src.old
[ -d patches/src ] && mv patches/src patches/src.old
mv "$NEW" patches/src
echo
echo "OK : patches/src reconstruit (ancienne version dans patches/src.old)."
echo "Montages attendus dans docker-compose.yml (section volumes:) :"
for f in $FILES; do
    echo "      - ./patches/src/$f:/app/src/$f:ro"
done
echo "Puis : docker compose up -d --force-recreate   (les fichiers montes ont ete remplaces)"
