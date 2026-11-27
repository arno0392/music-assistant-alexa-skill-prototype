# Correctifs locaux (skill Alexa Music Assistant)

**Méthode recommandée** : depuis le dossier du projet, `sh patches/rebuild.sh`.
Le script télécharge tous les scripts ci-dessous, extrait les fichiers **d'origine** de l'image
(`docker run --entrypoint cat`), applique les correctifs dans l'ordre, vérifie la syntaxe,
puis remplace `patches/src` (l'ancienne version est gardée dans `patches/src.old`).
Tests : `test_all.py` (scénarios MA 2.10 / 2.11 / sans écran) et `test_http.py` (application réelle).

Scripts appliqués sur des copies des fichiers du conteneur (`/app/src/skill/…`), montées ensuite en lecture seule.

| Script | Fichiers | Effet |
|---|---|---|
| `fix_meta.py` | `util.py` | titre/artiste/pochette dans AudioPlayer.Play (PR #101) |
| `fix_apl.py` | `apl.py` | URL audio APL encodée (%20) et .flac -> .mp3 |
| `fix_apl_buttons.py` | `apl_document.json` + `lambda_function.py` | boutons suivant/précédent de l'écran APL -> Music Assistant |
| `fix_apl_refresh.py` | `ma_control.py` + `lambda_function.py` | écran APL mis à jour quand MA enchaîne le morceau suivant dans le flux |
| `fix_apl_time.py` | `apl_document.json` + `ma_control.py` + `lambda_function.py` | temps écoulé / durée du morceau en cours sur l'écran APL (après fix_apl_refresh.py) |
| `fix_live_page.py` | `shared_store.py`, `ma_routes.py`, `alexa_routes.py`, `util.py`, `apl_document.json`, `lambda_function.py` | écran APL piloté par Music Assistant 2.11 (pageLive, /ma/control, /alexa/playback-state) + temps par morceau corrigé |
| `fix_live_report.py` | `apl_document.json`, `util.py`, `lambda_function.py` | position/état réels de l'écran APL transmis au skill (après fix_live_page.py) |
| `fix_apl_ux.py` | `apl_document.json`, `lambda_function.py`, `ma_control.py` | barre de lecture -> seek Music Assistant, retour visuel des boutons, temps recalé à chaque nouvel écran |
| `fix_apl_seek.py` | `apl_document.json`, `util.py`, `lambda_function.py` | la barre de lecture passe par le rafraîchissement (SendEvent ignoré en mode rapide) -> seek Music Assistant |
| `fix_apl_pause.py` | `apl.py` | pause depuis Music Assistant : autoplay coupé aussi sur les contrôles (introuvables après fix_apl_buttons.py) |
| `fix_stream_key.py` | `shared_store.py`, `ma_routes.py`, `alexa_routes.py`, `lambda_function.py` | flux comparés par identité (rapport de position "current" correct) + titre frais avant réaffichage |
| `fix_apl_followups.py` | `apl_document.json`, `ma_control.py`, `lambda_function.py` | temps renvoyé ~6 s après puis recalé si écart > 3 s ; pause/lecture de l'écran renvoyées à MA ; écran gardé 10 min en pause (idleTimeout) ; précédent calculé depuis le titre affiché |
| `fix_apl_sequencer.py` | `apl_document.json`, `util.py`, `ma_routes.py` | boucle de rafraîchissement sur son propre séquenceur APL (un appui sur l'écran ne la coupe plus) ; logs push-url/control avec pageLive |
