# Correctifs locaux (skill Alexa Music Assistant)

Scripts appliqués sur des copies des fichiers du conteneur (`/app/src/skill/…`), montées ensuite en lecture seule.

| Script | Fichiers | Effet |
|---|---|---|
| `fix_meta.py` | `util.py` | titre/artiste/pochette dans AudioPlayer.Play (PR #101) |
| `fix_apl.py` | `apl.py` | URL audio APL encodée (%20) et .flac -> .mp3 |
| `fix_apl_buttons.py` | `apl_document.json` + `lambda_function.py` | boutons suivant/précédent de l'écran APL -> Music Assistant |
| `fix_apl_refresh.py` | `ma_control.py` + `lambda_function.py` | écran APL mis à jour quand MA enchaîne le morceau suivant dans le flux |
