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
| `fix_seek_offset.py` | `lambda_function.py` | après un déplacement du curseur sur l'écran, temps recalé sur la position demandée (plus de retour à 0) |
| `fix_time_binds.py` | `apl_document.json`, `lambda_function.py` | valeurs de temps (décalage, recalage) portées par le composant Video lui-même : les recalages s'appliquent enfin |
| `fix_apl_background.py` | `apl_document.json` | fond : pochette légèrement floutée (filtre Blur 8 dp) et assombrie ; temps total = durée du titre uniquement |
| `fix_apl_lyrics.py` | `apl_document.json`, `ma_control.py`, `lambda_function.py` | paroles synchronisées : bouton micro à droite de ⏭, panneau à la place de la pochette, ligne en cours en blanc, défilement automatique |
| `fix_root_id.py` | `apl_document.json`, `lambda_function.py` | les SetValue visent l'id réel du conteneur racine (AudioPlayerRoot) : bouton paroles et total enfin pris en compte |
| `fix_time_precision.py` | `apl_document.json`, `shared_store.py`, `lambda_function.py` | position exacte sans attendre MA : 0 au début d'un flux, décalage précédent + durée au changement de titre ; horloge de l'Echo dans les rapports |
| `fix_lyrics_keep.py` | `apl_document.json`, `lambda_function.py` | le panneau des paroles reste ouvert après ⏮ ⏭ ou un déplacement du curseur |
| `fix_flow_end.py` | `apl_document.json`, `ma_control.py`, `lambda_function.py` | flux terminé par MA entre deux titres (changement de fréquence d'échantillonnage) : le skill relance le titre suivant |
| `fix_voice_next.py` | `lambda_function.py` | « Alexa, suivant / précédent » : la session (et l'écran) restent ouverts quand l'écran est affiché |
| `fix_lyrics_scroll.py` | `apl_document.json`, `lambda_function.py` | défilement des paroles calculé par l'écran (table par tranches de 250 ms, séquenceur dédié) : ligne en cours toujours centrée |
| `fix_lyrics_header.py` | `apl_document.json`, `lambda_function.py` | mode paroles : titre et artiste en haut à gauche, alignés sur les marges de l'écran (toutes tailles), coupés sur une ligne |
| `fix_apl_logo.py` | `apl_document.json` | logo Music Assistant blanc (vectoriel, net sur tous les écrans) en haut à droite |
| `fix_voice_pause.py` | `lambda_function.py` | la pause faite par l'Echo pendant une commande vocale n'est plus transmise à MA (lecture figée après « Alexa, suivant ») |
| `fix_voice_transport.py` | `apl_document.json`, `apl.py`, `lambda_function.py` | « Alexa, suivant / précédent » (traités par l'Echo sur la vidéo) renvoyés à MA : 2e source factice pour suivant, retour en arrière du flux pour précédent |
| `fix_meta_churn.py` | `lambda_function.py` | titre et pochette renvoyés à l'écran seulement quand ils changent |
| `fix_refresh_loop.py` | `apl_document.json`, `util.py` | boucle de rafraîchissement autonome (1/s, se répète seule) : l'écran ne « meurt » plus si une réponse se perd |
| `fix_play_audio_live.py` | `lambda_function.py` | « PlayAudio » pendant que l'écran joue : simple reprise, plus de redémarrage du titre |
| `fix_fallback_live.py` | `lambda_function.py` | phrase non comprise pendant que l'écran joue : ignorée, l'écran reste ouvert |
| `fix_custom_skip_intents.py` | `lambda_function.py` | intents perso MaNextIntent / MaPreviousIntent (phrases en plus : « chanson précédente »…) traités comme suivant/précédent |
| `fix_stream_ran_out.py` | `lambda_function.py` | flux épuisé en fin de titre (MA l'a terminé avant un titre 96 kHz) : le skill lance le titre suivant au lieu d'une pause |
| `fix_multi_player.py` | `shared_store.py`, `ma_routes.py`, `alexa_routes.py`, `util.py`, `lambda_function.py` | plusieurs Echo : un « en cours » par lecteur MA (titre, pochette, flux), selon /devices ou le playerId de MA 2.11 |
| `fix_tv_remote.py` | `apl_document.json`, `lambda_function.py` | télécommande de TV : gauche/droite = précédent/suivant, OK = lecture/pause, haut/bas = paroles (focus donné au bouton paroles sur une TV) |
| `fix_tv_diag.py` | `apl_document.json`, `lambda_function.py` | diagnostic temporaire TV : journalise chaque touche reçue par la page (« Remote key ») et le type d’écran de chaque appareil (« Screen of ») |
| `fix_voice_next_file.py` | `app.py` | la 2e piste de l’écran (`/ma-voice-next.mp3`) est un vrai MP3 silencieux, servi sans authentification : plus de fenêtre « Nom d’utilisateur / Mot de passe » sur une TV. **Nouveau montage : `app.py`** |
| `fix_tv_nav.py` | `apl_document.json` | TV : les flèches déplacent la sélection (⏮ ⏯ ⏭ paroles ; ↑ = barre de lecture, ←/→ y déplacent le curseur de 10 s et MA saute 1,2 s après le dernier appui ; ↓ = retour aux boutons), OK appuie (⏯ joue/met en pause directement sur la page, l’icône bascule) ; sélection lumineuse, le reste estompé ; rien ne change sur écran tactile |
| `fix_time_sanity.py` | `lambda_function.py` | filet de sécurité du temps : si l’écran affiche une position hors du morceau (au-delà de sa durée), recalage sur le temps de MA, à tout moment (au plus toutes les 20 s) |
| `fix_previous_guard.py` | `lambda_function.py` | pas de « précédent vocal » détecté dans les 5 premières secondes d’un nouvel écran (un dernier rapport de l’ancienne page annulait le « suivant » sur une TV) |
