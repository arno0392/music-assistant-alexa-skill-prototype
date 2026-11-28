#!/usr/bin/env python3
"""
Remplit, dans Lokalise, les traductions françaises VIDES du plugin Music Quiz
(projets « MA Server » et « MA Frontend » de Music Assistant).

- Ne remplace jamais une traduction française existante.
- Ne touche qu'aux clés listées ci-dessous (Music Quiz).
- Par défaut, n'écrit rien : il affiche ce qu'il ferait. Ajoute --apply pour écrire.
- Saute (et signale) une clé si ses variables ({0}, {1}, {count}…) ne s'écrivent pas
  pareil dans Lokalise : celles-là sont à saisir à la main.

Utilisation :
    export LOKALISE_TOKEN='ton-jeton'          # Lokalise > Profil > API tokens
    python3 lokalise_quiz_fr.py                 # simulation
    python3 lokalise_quiz_fr.py --apply         # écriture
    python3 lokalise_quiz_fr.py --export DOSSIER # récupère les traductions françaises du quiz
                                                # (quiz_fr_server.json, quiz_fr_frontend.json)
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

API = "https://api.lokalise.com/api2"
DATA = json.loads(r"""{
 "server": {
  "project_id": "264744796a2c5fd1b48fb5.28236063",
  "fr": {
   "provider.music_quiz.manifest.description": "Animez un quiz musical à plusieurs, que vos invités rejoignent avec un QR code.",
   "provider.music_quiz.config_entries.mode.label": "Mode de lecture",
   "provider.music_quiz.config_entries.mode.description": "La façon dont les manches du quiz sont jouées. En mode salle, un lecteur configuré diffuse la musique pour toutes les personnes présentes. En mode à distance, chaque invité écoute sur son propre appareil (façon silent disco).",
   "provider.music_quiz.config_entries.mode.options.venue": "Salle (diffusion sur une vraie enceinte)",
   "provider.music_quiz.config_entries.mode.options.remote": "À distance (chaque invité écoute sur son appareil)",
   "provider.music_quiz.config_entries.player.label": "Lecteur du quiz",
   "provider.music_quiz.config_entries.player.description": "Le lecteur qui joue les manches du quiz en mode salle. En mode automatique, le dernier lecteur actif est utilisé.",
   "provider.music_quiz.config_entries.player.options.__auto__": "Automatique (dernier lecteur actif)",
   "provider.music_quiz.config_entries.use_ai_distractors.label": "Enrichir l'expérience avec l'IA",
   "provider.music_quiz.config_entries.use_ai_distractors.description": "Lorsque cette option est activée, le quiz utilise un fournisseur d'IA configuré (comme Home Assistant, qui donne accès à un LLM) pour enrichir l'expérience, par exemple en générant de fausses réponses plus crédibles à chaque manche. Sans fournisseur d'IA disponible, le quiz garde son fonctionnement intégré.",
   "provider.music_quiz.errors.music_quiz_already_answered": "Vous avez déjà répondu à cette manche.",
   "provider.music_quiz.errors.music_quiz_answer_duration_max": "Le temps de réponse doit être de {0} secondes au maximum.",
   "provider.music_quiz.errors.music_quiz_answer_duration_min": "Le temps de réponse doit être d'au moins 1 seconde.",
   "provider.music_quiz.errors.music_quiz_game_active": "Une partie de Music Quiz est déjà en cours.",
   "provider.music_quiz.errors.music_quiz_game_full": "La partie de Music Quiz est complète.",
   "provider.music_quiz.errors.music_quiz_guess_too_fast": "Patientez un instant avant de proposer une nouvelle réponse.",
   "provider.music_quiz.errors.music_quiz_invalid_answer": "Cette réponse n'est pas valable pour la partie en cours.",
   "provider.music_quiz.errors.music_quiz_invalid_bonus_mode": "Le mode de bonus de la frise chronologique sélectionné n'est pas valide.",
   "provider.music_quiz.errors.music_quiz_invalid_difficulty": "La difficulté sélectionnée n'est pas valide.",
   "provider.music_quiz.errors.music_quiz_invalid_hint_speed": "La vitesse des indices sélectionnée n'est pas valide.",
   "provider.music_quiz.errors.music_quiz_invalid_language": "La langue sélectionnée pour les questions de culture musicale n'est pas valide.",
   "provider.music_quiz.errors.music_quiz_invalid_playback_mode": "Le mode de lecture sélectionné n'est pas valide.",
   "provider.music_quiz.errors.music_quiz_invalid_typo_tolerance": "La tolérance aux fautes de frappe sélectionnée n'est pas valide.",
   "provider.music_quiz.errors.music_quiz_name_required": "Un nom de joueur est obligatoire.",
   "provider.music_quiz.errors.music_quiz_name_taken": "Ce nom de joueur est déjà pris.",
   "provider.music_quiz.errors.music_quiz_no_dated_tracks": "Aucune des pistes sélectionnées n'a d'année de sortie exploitable.",
   "provider.music_quiz.errors.music_quiz_no_game": "Aucune partie de Music Quiz n'est en cours.",
   "provider.music_quiz.errors.music_quiz_no_playback_target": "Aucun lecteur n'est disponible pour la partie de Music Quiz.",
   "provider.music_quiz.errors.music_quiz_no_unused_source_tracks": "Il ne reste plus de piste inutilisée dans les sources.",
   "provider.music_quiz.errors.music_quiz_not_active_this_round": "Vous avez rejoint la partie pendant cette manche : vous pourrez jouer à partir de la suivante.",
   "provider.music_quiz.errors.music_quiz_not_enough_dated_tracks": "Cette partie nécessite au moins {0} pistes différentes avec une année de sortie.",
   "provider.music_quiz.errors.music_quiz_not_enough_distractors": "Il n'y a pas assez de pistes différentes pour proposer des choix de réponse.",
   "provider.music_quiz.errors.music_quiz_round_count_max": "Music Quiz accepte au maximum {0} manches.",
   "provider.music_quiz.errors.music_quiz_round_count_min": "Music Quiz nécessite au moins 1 manche.",
   "provider.music_quiz.errors.music_quiz_source_count_max": "Music Quiz accepte au maximum {0} sources.",
   "provider.music_quiz.errors.music_quiz_source_required": "Au moins une source est nécessaire.",
   "provider.music_quiz.errors.music_quiz_sources_unavailable": "Aucune des sources configurées n'a pu être chargée.",
   "provider.music_quiz.errors.music_quiz_suggestion_count_max": "Le nombre de propositions doit être de {0} au maximum.",
   "provider.music_quiz.errors.music_quiz_suggestion_count_min": "Le nombre de propositions doit être d'au moins 2.",
   "provider.music_quiz.errors.music_quiz_too_many_attempts": "Vous avez utilisé toutes vos tentatives pour cette manche.",
   "provider.music_quiz.errors.music_quiz_trivia_ai_provider_required": "Les questions de culture musicale nécessitent un fournisseur d'IA configuré.",
   "provider.music_quiz.errors.music_quiz_trivia_generation_failed": "Music Assistant n'a pas pu générer de question de culture musicale valide. Veuillez réessayer.",
   "provider.music_quiz.errors.music_quiz_trivia_insufficient_metadata": "Les questions de culture musicale nécessitent au moins {0} pistes sélectionnées différentes avec des métadonnées exploitables.",
   "provider.music_quiz.errors.music_quiz_unknown_player": "Ce joueur ne participe pas à la partie de Music Quiz.",
   "provider.music_quiz.errors.music_quiz_unknown_quiz_type": "Ce type de quiz n'est pas disponible.",
   "provider.music_quiz.errors.music_quiz_unknown_suggestion": "Ce choix de réponse n'est pas disponible.",
   "provider.music_quiz.errors.music_quiz_wrong_phase": "Cette action n'est pas possible à ce stade de la partie."
  }
 },
 "frontend": {
  "project_id": "321419046440c0f2bba414.05634832",
  "fr": {
   "login.guest_ended_quiz_title": "Votre session de quiz est terminée",
   "login.guest_ended_quiz_message": "Demandez à l'organisateur de partager à nouveau le lien ou le QR code du quiz pour le rejoindre.",
   "providers.music_quiz.title": "Music Quiz",
   "providers.music_quiz.create_intro": "Créez une nouvelle partie de quiz pour tester votre culture musicale !",
   "providers.music_quiz.loading": "Chargement…",
   "providers.music_quiz.no_active_game": "Aucune partie en cours",
   "providers.music_quiz.game_ended": "Partie terminée",
   "providers.music_quiz.game_ended_detail": "Le quiz que vous avez rejoint est terminé.",
   "providers.music_quiz.start": "Lancer le quiz",
   "providers.music_quiz.phase_reveal": "Révéler la réponse",
   "providers.music_quiz.next": "Manche suivante",
   "providers.music_quiz.finish": "Terminer le quiz",
   "providers.music_quiz.new_game": "Nouvelle partie",
   "providers.music_quiz.phase_waiting_for_players": "En attente des joueurs",
   "providers.music_quiz.phase_answers_open": "À vous de répondre !",
   "providers.music_quiz.phase_enjoy_track": "Profitez du morceau !",
   "providers.music_quiz.phase_finished": "Quiz terminé",
   "providers.music_quiz.players": "Joueurs",
   "providers.music_quiz.players_count": "{0} joueur(s)",
   "providers.music_quiz.rounds_count": "{0} manche(s)",
   "providers.music_quiz.round_label": "Manche",
   "providers.music_quiz.enter_name": "Saisissez votre nom",
   "providers.music_quiz.join": "Rejoindre le quiz",
   "providers.music_quiz.waiting_for_start": "En attente du lancement du quiz par l'organisateur…",
   "providers.music_quiz.choose_answer": "Choisissez votre réponse !",
   "providers.music_quiz.answered": "Réponse envoyée ! En attente des autres joueurs…",
   "providers.music_quiz.answer_was": "La réponse était",
   "providers.music_quiz.correct": "Bonne réponse !",
   "providers.music_quiz.incorrect": "Mauvaise réponse",
   "providers.music_quiz.no_answer_submitted": "Aucune réponse envoyée",
   "providers.music_quiz.ready": "Prêt pour la manche suivante",
   "providers.music_quiz.waiting_for_next": "En attente de la manche suivante…",
   "providers.music_quiz.game_over": "Partie terminée !",
   "providers.music_quiz.final_leaderboard": "Classement final",
   "providers.music_quiz.connection_lost": "Connexion perdue, reconnexion…",
   "providers.music_quiz.rounds": "Manches",
   "providers.music_quiz.answer_seconds": "Temps de réponse (secondes)",
   "providers.music_quiz.selected_music": "Musique sélectionnée",
   "providers.music_quiz.pick_at_least_one_source": "Choisissez au moins une source",
   "providers.music_quiz.playlist": "Playlist",
   "providers.music_quiz.track_with_artist": "Piste • {0}",
   "providers.music_quiz.track": "Piste",
   "providers.music_quiz.source_music": "Musique",
   "providers.music_quiz.track_count": "{0} piste",
   "providers.music_quiz.tracks_count": "{0} pistes",
   "providers.music_quiz.playlist_count": "{0} playlist",
   "providers.music_quiz.playlists_count": "{0} playlists",
   "providers.music_quiz.player_name": "Votre nom",
   "providers.music_quiz.answers": "Réponses",
   "providers.music_quiz.leaderboard": "Classement",
   "providers.music_quiz.invite_players": "Inviter des joueurs",
   "providers.music_quiz.qr_unavailable": "Impossible d'afficher le QR code",
   "providers.music_quiz.copied": "Copié",
   "providers.music_quiz.copy_link": "Copier le lien",
   "providers.music_quiz.copy_join_link_failed": "Impossible de copier le lien d'invitation",
   "providers.music_quiz.now_playing": "En cours de lecture",
   "providers.music_quiz.current_music": "Musique en cours",
   "providers.music_quiz.copy_music_name": "Copier le titre du morceau",
   "providers.music_quiz.copy_music_name_failed": "Impossible de copier le titre du morceau",
   "providers.music_quiz.no_winner": "Pas de gagnant cette fois-ci",
   "providers.music_quiz.winner_single": "{0} gagne avec {1} points",
   "providers.music_quiz.winner_multiple": "{0} sont ex æquo avec {1} points",
   "providers.music_quiz.enter_present_mode": "Mode présentation",
   "providers.music_quiz.exit_present_mode": "Quitter le mode présentation",
   "providers.music_quiz.mode_venue": "Mode salle",
   "providers.music_quiz.mode_remote": "Mode à distance",
   "providers.music_quiz.listen_in": "Écouter",
   "providers.music_quiz.listen_in_venue": "Écouter la musique sur cet appareil",
   "providers.music_quiz.listen_in_remote": "Écouter la musique sur cet appareil",
   "providers.music_quiz.error_load_state": "Impossible de charger l'état du quiz",
   "providers.music_quiz.error_create": "Impossible de créer le quiz",
   "providers.music_quiz.error_start": "Impossible de lancer le quiz",
   "providers.music_quiz.error_reveal": "Impossible de révéler la réponse",
   "providers.music_quiz.error_next": "Impossible de passer à la manche suivante",
   "providers.music_quiz.error_reset": "Impossible de réinitialiser le quiz",
   "providers.music_quiz.error_delete": "Impossible de supprimer le quiz",
   "providers.music_quiz.error_load_info": "Impossible de charger les informations du quiz",
   "providers.music_quiz.error_join": "Impossible de rejoindre le quiz",
   "providers.music_quiz.error_not_joined": "Vous n'avez pas rejoint ce quiz",
   "providers.music_quiz.error_answer": "Impossible d'envoyer votre réponse",
   "providers.music_quiz.error_ready": "Impossible de vous indiquer comme prêt",
   "providers.music_quiz.error_no_web_player": "Le lecteur web n'est pas encore disponible",
   "providers.music_quiz.error_listen_in": "Impossible de lancer l'écoute",
   "providers.music_quiz.error_stop_listen_in": "Impossible d'arrêter l'écoute",
   "providers.music_quiz.listen_in_active": "Vous écoutez",
   "providers.music_quiz.listen_in_tap": "Touchez pour écouter",
   "providers.music_quiz.listen_in_stop": "Arrêter l'écoute",
   "providers.music_quiz.listen_in_powered_by": "Avec Sendspin",
   "providers.music_quiz.difficulty": "Difficulté",
   "providers.music_quiz.difficulty_easy": "Facile",
   "providers.music_quiz.difficulty_normal": "Normale",
   "providers.music_quiz.difficulty_hard": "Difficile",
   "providers.music_quiz.choose_game_type": "Choisissez un type de jeu",
   "providers.music_quiz.configure_game": "Configurez votre partie",
   "providers.music_quiz.answer_choices": "Choix de réponses",
   "providers.music_quiz.game_type_guess_the_song": "Devinez la chanson",
   "providers.music_quiz.game_type_guess_the_song_description": "Un morceau est joué : soyez le premier à choisir son titre parmi les propositions.",
   "providers.music_quiz.waiting_for_answer": "En attente de la réponse",
   "providers.music_quiz.unsupported_title": "Mise à jour nécessaire",
   "providers.music_quiz.unsupported_description": "Ce type de jeu nécessite une version plus récente de l'interface de Music Assistant.",
   "providers.music_quiz.end_game_confirm": "Voulez-vous vraiment terminer cette partie ? Elle sera supprimée pour tous les joueurs.",
   "providers.music_quiz.end_game": "Terminer la partie",
   "providers.music_quiz.remove_music_source": "Retirer {0}",
   "providers.music_quiz.timeline_anchor": "Repère",
   "providers.music_quiz.timeline_revealed": "Nouveau",
   "providers.music_quiz.timeline_place_help": "Choisissez où placer le morceau en cours, du plus ancien au plus récent.",
   "providers.music_quiz.timeline_place_here": "Placer ici",
   "providers.music_quiz.timeline_placed_here": "Placé ici",
   "providers.music_quiz.timeline_place_before": "Placer avant {0} : {1}",
   "providers.music_quiz.timeline_place_after": "Placer après {0} : {1}",
   "providers.music_quiz.timeline_place_between": "Placer entre {0} : {1} et {2} : {3}",
   "providers.music_quiz.timeline_choose_position": "Où placer ce morceau ?",
   "providers.music_quiz.timeline_placement_locked": "Placement verrouillé",
   "providers.music_quiz.timeline_progress": "Progression de la manche",
   "providers.music_quiz.timeline_placed_count": "{0} placé(s)",
   "providers.music_quiz.timeline_complete": "Réponse complète",
   "providers.music_quiz.timeline_bonuses_pending": "Réponses bonus en attente",
   "providers.music_quiz.timeline_artist_bonus": "Bonus artiste",
   "providers.music_quiz.timeline_title_bonus": "Bonus titre",
   "providers.music_quiz.timeline_bonus_off": "Désactivé",
   "providers.music_quiz.timeline_bonus_free_text": "Réponse libre",
   "providers.music_quiz.timeline_bonus_multiple_choice": "Choix multiples",
   "providers.music_quiz.timeline_bonus_optional": "Les réponses bonus sont facultatives.",
   "providers.music_quiz.timeline_submit_bonus": "Envoyer le bonus",
   "providers.music_quiz.timeline_correct_placement": "Bon placement",
   "providers.music_quiz.timeline_incorrect_placement": "Mauvais placement",
   "providers.music_quiz.timeline_round_results": "Résultats de la manche",
   "providers.music_quiz.timeline_result_placement": "Placement",
   "providers.music_quiz.round_result_answer": "Réponse",
   "providers.music_quiz.add_music_sources": "Ajouter des sources musicales",
   "providers.music_quiz.genre": "Genre",
   "providers.music_quiz.album": "Album",
   "providers.music_quiz.artist": "Artiste",
   "providers.music_quiz.genre_count": "{0} genre",
   "providers.music_quiz.genres_count": "{0} genres",
   "providers.music_quiz.album_count": "{0} album",
   "providers.music_quiz.albums_count": "{0} albums",
   "providers.music_quiz.artist_count": "{0} artiste",
   "providers.music_quiz.artists_count": "{0} artistes",
   "providers.music_quiz.game_type_trivia": "Culture musicale",
   "providers.music_quiz.game_type_trivia_description": "Répondez à des questions sur la musique, générées par l'IA à partir de la bibliothèque sélectionnée.",
   "providers.music_quiz.phase_answer_revealed": "Réponse révélée !",
   "providers.music_quiz.error_load_game_types": "Impossible de charger les types de quiz disponibles",
   "providers.music_quiz.game_ended_wait": "Demandez à l'organisateur de lancer une nouvelle partie quand tout le monde est prêt.",
   "providers.music_quiz.ready_for_final_results": "Prêt pour les résultats finaux",
   "providers.music_quiz.waiting_for_final_results": "En attente des résultats finaux…",
   "providers.music_quiz.next_round_in": "Manche suivante dans {0}",
   "providers.music_quiz.final_results_in": "Résultats finaux dans {0}",
   "providers.music_quiz.timeline_skip_remaining_bonuses": "Passer les bonus restants",
   "providers.music_quiz.play_again": "Rejouer",
   "providers.music_quiz.set_up_new_game": "Préparer une nouvelle partie…",
   "providers.music_quiz.game_type_music_timeline": "Frise musicale",
   "providers.music_quiz.game_type_music_timeline_description": "Placez les morceaux dans l'ordre chronologique, puis gagnez des points bonus en trouvant l'artiste et le titre.",
   "providers.music_quiz.music_timeline_listen_title": "Écoutez bien",
   "providers.music_quiz.music_timeline_listen_description": "Placez le morceau en cours sur la frise. Ses détails restent cachés jusqu'à la révélation.",
   "providers.music_quiz.music_timeline_session_summary": "Réglages de la frise musicale",
   "providers.music_quiz.music_timeline_song_hidden": "Le morceau en cours reste caché jusqu'à la révélation.",
   "providers.music_quiz.start_now_countdown": "Lancer maintenant · {0}",
   "providers.music_quiz.start_now_waiting": "Lancer maintenant · En attente…",
   "providers.music_quiz.game_starts_in": "La partie commence dans {0}",
   "providers.music_quiz.waiting_for_game_start": "En attente du début de la partie…",
   "providers.music_quiz.question_language": "Langue des questions",
   "providers.music_quiz.ready_for_next_round_countdown": "Prêt pour la manche suivante · {0}",
   "providers.music_quiz.waiting_for_next_round_countdown": "En attente de la manche suivante · {0}",
   "providers.music_quiz.ready_for_final_results_countdown": "Prêt pour les résultats finaux · {0}",
   "providers.music_quiz.waiting_for_final_results_countdown": "En attente des résultats finaux · {0}",
   "providers.music_quiz.next_round_countdown": "Manche suivante · {0}",
   "providers.music_quiz.finish_quiz_countdown": "Terminer le quiz · {0}",
   "providers.music_quiz.play_revealed_songs": "Jouer les morceaux révélés",
   "providers.music_quiz.play_revealed_songs_help": "La musique ne joue qu'une fois la réponse révélée.",
   "providers.music_quiz.reveal_audio_on": "Activé",
   "providers.music_quiz.reveal_audio_off": "Désactivé",
   "providers.music_quiz.include_similar_music": "Inclure des musiques similaires",
   "providers.music_quiz.include_similar_music_help": "Ajoute des morceaux recommandés en plus des sources sélectionnées, pour plus de variété.",
   "providers.music_quiz.playback": "Lecture",
   "providers.music_quiz.playback_help": "Choisissez où les joueurs entendent la musique.",
   "providers.music_quiz.playback_mode": "Mode de lecture",
   "providers.music_quiz.playback_venue": "Salle",
   "providers.music_quiz.playback_venue_help": "La musique est jouée sur un seul lecteur.",
   "providers.music_quiz.playback_remote": "À distance",
   "providers.music_quiz.playback_remote_help": "Chaque joueur écoute sur son propre appareil.",
   "providers.music_quiz.playback_summary_venue": "Salle · {0}",
   "providers.music_quiz.playback_summary_remote": "À distance · Chaque joueur écoute sur son propre appareil",
   "providers.music_quiz.playback_venue_unavailable": "Le mode salle n'est pas disponible.",
   "providers.music_quiz.playback_remote_unavailable": "Le mode à distance n'est pas disponible.",
   "providers.music_quiz.player": "Lecteur",
   "providers.music_quiz.choose_player": "Choisissez un lecteur",
   "providers.music_quiz.no_available_players": "Aucun lecteur disponible. Utilisez le mode à distance ou vérifiez les réglages des lecteurs.",
   "providers.music_quiz.no_playback_modes": "Aucun mode de lecture n'est disponible. Vérifiez les réglages de Music Quiz.",
   "providers.music_quiz.loading_playback_options": "Chargement des options de lecture…",
   "providers.music_quiz.error_load_playback_options": "Impossible de charger les options de lecture",
   "providers.music_quiz.playback_options_unavailable": "Impossible de charger les options de lecture. Réessayez avant de créer la partie.",
   "providers.music_quiz.preparing_game": "Préparation de la partie",
   "providers.music_quiz.preparing_game_help": "Chargement de la musique sélectionnée et création des manches. Cela peut prendre un moment.",
   "providers.music_quiz.settings": "Réglages de Music Quiz",
   "providers.music_quiz.more_share_options": "Plus d'options de partage",
   "providers.music_quiz.share_description": "Utilisez ce lien ou scannez le QR code pour rejoindre le Music Quiz.",
   "providers.music_quiz.share_failed": "Impossible de partager l'invitation au quiz",
   "providers.music_quiz.share_invitation": "Partager l'invitation",
   "providers.music_quiz.share_title": "Rejoignez le quiz Music Assistant",
   "providers.music_quiz.timeline_order": "Frise, du plus ancien au plus récent",
   "providers.music_quiz.timeline_older": "Plus ancien",
   "providers.music_quiz.timeline_newer": "Plus récent",
   "providers.music_quiz.timeline_place_before_year": "Avant {0}",
   "providers.music_quiz.timeline_place_after_year": "Après {0}",
   "providers.music_quiz.timeline_place_between_years": "Entre {0} et {1}",
   "providers.music_quiz.timeline_place_in_year": "En {0}",
   "providers.music_quiz.play_along": "Jouer aussi",
   "providers.music_quiz.host_controls": "Commandes de l'organisateur",
   "providers.music_quiz.return_to_host_panel": "Retour au panneau de l'organisateur",
   "providers.music_quiz.dashboard_waiting": "En attente du début du quiz",
   "providers.music_quiz.name_that_track": "Trouvez le titre",
   "providers.music_quiz.how_to_play_guess_the_song_description": "Écoutez le morceau en cours et choisissez le bon titre parmi les propositions avant la fin du temps imparti.",
   "providers.music_quiz.how_to_play_trivia_description": "Répondez à des questions sur la musique. Choisissez la réponse qui vous semble juste avant la fin du temps imparti.",
   "providers.music_quiz.game_type_title_reveal": "Titre mystère",
   "providers.music_quiz.game_type_title_reveal_description": "Un morceau est joué : tapez son titre pendant que ses lettres se dévoilent une à une.",
   "providers.music_quiz.how_to_play_title_reveal_description": "Écoutez le morceau en cours et tapez son titre. Des lettres se dévoilent au fil du temps et les petites fautes de frappe sont acceptées, mais plus vous trouvez vite, plus vous gagnez de points.",
   "providers.music_quiz.title_reveal_hint_speed": "Vitesse des indices",
   "providers.music_quiz.title_reveal_hint_speed_slow": "Lente (peu de lettres)",
   "providers.music_quiz.title_reveal_hint_speed_normal": "Normale",
   "providers.music_quiz.title_reveal_hint_speed_fast": "Rapide (beaucoup de lettres)",
   "providers.music_quiz.title_reveal_typo_tolerance": "Tolérance aux fautes de frappe",
   "providers.music_quiz.title_reveal_typo_tolerance_strict": "Stricte",
   "providers.music_quiz.title_reveal_typo_tolerance_normal": "Normale",
   "providers.music_quiz.title_reveal_typo_tolerance_lenient": "Souple",
   "providers.music_quiz.title_reveal_mask_label": "Titre du morceau : {0}, {1} lettres encore cachées",
   "providers.music_quiz.title_reveal_hints_progress": "{0} indice(s) sur {1} dévoilé(s)",
   "providers.music_quiz.title_reveal_typos_allowed": "Jusqu'à {count} faute de frappe acceptée | Jusqu'à {count} fautes de frappe acceptées",
   "providers.music_quiz.title_reveal_exact_spelling": "Orthographe exacte exigée",
   "providers.music_quiz.title_reveal_guess_label": "Titre du morceau",
   "providers.music_quiz.title_reveal_guess_placeholder": "Tapez le titre…",
   "providers.music_quiz.title_reveal_submit_guess": "Proposer",
   "providers.music_quiz.title_reveal_attempts_left": "{count} tentative restante | {count} tentatives restantes",
   "providers.music_quiz.title_reveal_your_guesses": "Vos propositions",
   "providers.music_quiz.title_reveal_close": "Presque !",
   "providers.music_quiz.title_reveal_solved": "Trouvé !",
   "providers.music_quiz.title_reveal_points": "+{0} points",
   "providers.music_quiz.title_reveal_solved_players": "Ont trouvé",
   "providers.music_quiz.title_reveal_not_solved": "Vous n'avez pas trouvé le titre cette manche",
   "providers.music_quiz.title_reveal_first_bonus": "Premier ! +{0}",
   "providers.music_quiz.title_reveal_first_bonus_result": "Première bonne réponse",
   "providers.music_quiz.title_reveal_artist_bonus_setting": "Bonus artiste",
   "providers.music_quiz.title_reveal_artist_bonus_setting_help": "Après avoir trouvé le titre, les joueurs ont un essai pour trouver l'artiste et gagner des points bonus.",
   "providers.music_quiz.title_reveal_artist_bonus_label": "Bonus : qui est l'artiste ?",
   "providers.music_quiz.title_reveal_artist_bonus_help": "Un seul essai pour des points en plus.",
   "providers.music_quiz.title_reveal_artist_placeholder": "Tapez l'artiste…",
   "providers.music_quiz.title_reveal_artist_skip": "Passer",
   "providers.music_quiz.title_reveal_artist_correct": "{0}, c'est ça ! +{1}",
   "providers.music_quiz.title_reveal_artist_wrong": "Pas tout à fait, c'était {0}",
   "providers.music_quiz.title_reveal_artist_skipped": "Passé, c'était {0}",
   "providers.music_quiz.landing_continue": "Continuer",
   "guest.no_quiz_title": "Aucun quiz n'est en cours",
   "guest.no_quiz_description": "Demandez à l'organisateur de lancer un Music Quiz.",
   "onboarding.steps.ai.features.music_quiz": "Animer le quiz musical"
  }
 }
}""")


def call(method, path, token, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"X-Api-Token": token, "Content-Type": "application/json",
                                          "Accept": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode()), resp.headers
        except urllib.error.HTTPError as err:
            if err.code == 429:
                time.sleep(2 + attempt * 2)
                continue
            raise SystemExit(f"Erreur Lokalise {err.code} sur {path} : {err.read().decode()[:300]}")
    raise SystemExit("Lokalise refuse trop de requêtes, réessaie plus tard.")


def norm(name):
    return name.replace("::", ".")


def tokens(text):
    return sorted(re.findall(r"\{\w+\}", text or ""))


def main():
    token = os.environ.get("LOKALISE_TOKEN")
    if not token:
        raise SystemExit("Définis d'abord LOKALISE_TOKEN (export LOKALISE_TOKEN='...').")
    apply = "--apply" in sys.argv
    export_dir = None
    if "--export" in sys.argv:
        rest = sys.argv[sys.argv.index("--export") + 1:]
        export_dir = rest[0] if rest and not rest[0].startswith("--") else "."
    total_done = 0
    for name, project in DATA.items():
        wanted = project["fr"]
        pid = project["project_id"]
        print(f"\n== Projet {name} ({len(wanted)} textes Music Quiz)")
        found, page = {}, 1
        while True:
            res, headers = call("GET", f"/projects/{pid}/keys?include_translations=1&limit=500&page={page}", token)
            for key in res.get("keys", []):
                names = key.get("key_name") or {}
                kname = norm(names.get("web") or names.get("other") or next(iter(names.values()), ""))
                if kname in wanted:
                    found[kname] = key
            pages = int(headers.get("X-Pagination-Page-Count", "1"))
            if page >= pages:
                break
            page += 1
            time.sleep(0.2)
        if export_dir:
            out = {}
            for kname, key in sorted(found.items()):
                for tr in key.get("translations", []):
                    if tr["language_iso"].split("_")[0] == "fr" and (tr.get("translation") or "").strip():
                        out[kname] = tr["translation"]
            path = os.path.join(export_dir, f"quiz_fr_{name}.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(out, fh, ensure_ascii=False, indent=1)
            print(f"  {len(out)} traduction(s) française(s) enregistrée(s) dans {path}")
            continue
        missing = sorted(set(wanted) - set(found))
        if missing:
            print(f"  {len(missing)} clé(s) introuvable(s) dans Lokalise (à saisir à la main) :")
            for k in missing[:15]:
                print("   -", k)
            if len(missing) > 15:
                print(f"   … et {len(missing) - 15} autres")
        done = skipped = present = 0
        for kname, key in sorted(found.items()):
            trs = {t["language_iso"].split("_")[0]: t for t in key.get("translations", [])}
            fr, en = trs.get("fr"), trs.get("en")
            if fr is None:
                print(f"  ! pas de langue française sur {kname}")
                continue
            if (fr.get("translation") or "").strip():
                present += 1
                continue
            text = wanted[kname]
            if en is not None and tokens(en.get("translation")) != tokens(text):
                print(f"  ! variables différentes dans Lokalise, à saisir à la main : {kname}")
                print(f"      anglais Lokalise : {en.get('translation')}")
                skipped += 1
                continue
            if apply:
                call("PUT", f"/projects/{pid}/translations/{fr['translation_id']}", token, {"translation": text})
                time.sleep(0.2)
            done += 1
        verb = "écrit(s)" if apply else "à écrire (simulation)"
        print(f"  {done} texte(s) {verb}, {present} déjà traduit(s), {skipped} à saisir à la main.")
        total_done += done
    if export_dir:
        return
    if not apply:
        print("\nSimulation terminée : relance avec --apply pour écrire dans Lokalise.")
    else:
        print(f"\nTerminé : {total_done} traduction(s) écrite(s). Vérifie-les dans l'interface de Lokalise.")


if __name__ == "__main__":
    main()
