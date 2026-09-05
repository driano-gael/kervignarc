/* GÉNÉRÉ par `cd backend && python -m atlas` — ne pas éditer à la main.
   Toute modification sera écrasée à la régénération et rejetée par la CI. */
window.ATLAS = window.ATLAS || {};
window.ATLAS.controles = {
 "controles": [
  {
   "code": "date-non-canonique",
   "message": "date « 01/08/2026 » hors du format ISO utilisé par le reste du registre (AAAA-MM-JJ).",
   "severite": "signal",
   "sujet": "ADR-0064"
  },
  {
   "code": "date-non-canonique",
   "message": "date « 02/08/2026 » hors du format ISO utilisé par le reste du registre (AAAA-MM-JJ).",
   "severite": "signal",
   "sujet": "ADR-0065"
  },
  {
   "code": "date-non-canonique",
   "message": "date « 03/08/2026 » hors du format ISO utilisé par le reste du registre (AAAA-MM-JJ).",
   "severite": "signal",
   "sujet": "ADR-0067"
  },
  {
   "code": "date-non-canonique",
   "message": "date « 03/08/2026 » hors du format ISO utilisé par le reste du registre (AAAA-MM-JJ).",
   "severite": "signal",
   "sujet": "ADR-0068"
  },
  {
   "code": "date-non-canonique",
   "message": "date « 04/08/2026 » hors du format ISO utilisé par le reste du registre (AAAA-MM-JJ).",
   "severite": "signal",
   "sujet": "ADR-0069"
  },
  {
   "code": "date-non-canonique",
   "message": "date « 04/08/2026 » hors du format ISO utilisé par le reste du registre (AAAA-MM-JJ).",
   "severite": "signal",
   "sujet": "ADR-0070"
  },
  {
   "code": "date-non-canonique",
   "message": "date « 04/08/2026 » hors du format ISO utilisé par le reste du registre (AAAA-MM-JJ).",
   "severite": "signal",
   "sujet": "ADR-0071"
  },
  {
   "code": "date-non-canonique",
   "message": "date « 05/08/2026 » hors du format ISO utilisé par le reste du registre (AAAA-MM-JJ).",
   "severite": "signal",
   "sujet": "ADR-0072"
  },
  {
   "code": "date-non-canonique",
   "message": "date « 05/08/2026 » hors du format ISO utilisé par le reste du registre (AAAA-MM-JJ).",
   "severite": "signal",
   "sujet": "ADR-0073"
  },
  {
   "code": "date-non-canonique",
   "message": "date « 05/08/2026 » hors du format ISO utilisé par le reste du registre (AAAA-MM-JJ).",
   "severite": "signal",
   "sujet": "ADR-0074"
  },
  {
   "code": "date-non-canonique",
   "message": "date « 08/08/2026 » hors du format ISO utilisé par le reste du registre (AAAA-MM-JJ).",
   "severite": "signal",
   "sujet": "ADR-0079"
  },
  {
   "code": "date-non-canonique",
   "message": "date « 2026-08-09, **amendé le 2026-08-14** (E05US028 — le contrat cède où le §2 l'annonçait : une capacité renommée, cf. § « Ce que le contrat a appris de sa **deuxième** mise à l'épreuve ») » hors du format ISO utilisé par le reste du registre (AAAA-MM-JJ).",
   "severite": "signal",
   "sujet": "ADR-0083"
  },
  {
   "code": "date-non-canonique",
   "message": "date « 20/08/2026 » hors du format ISO utilisé par le reste du registre (AAAA-MM-JJ).",
   "severite": "signal",
   "sujet": "ADR-0092"
  },
  {
   "code": "features-enchevetrees",
   "message": "et 3 autre(s) feature(s) s'importent mutuellement (accueil, completude, jalons, paiements) : aucune ne peut plus être lue, testée ni retirée seule (règle 10). Lecture heuristique — jamais bloquante.",
   "severite": "signal",
   "sujet": "accueil"
  },
  {
   "code": "features-enchevetrees",
   "message": "et 1 autre(s) feature(s) s'importent mutuellement (admin, tournois) : aucune ne peut plus être lue, testée ni retirée seule (règle 10). Lecture heuristique — jamais bloquante.",
   "severite": "signal",
   "sujet": "admin"
  },
  {
   "code": "features-enchevetrees",
   "message": "et 23 autre(s) feature(s) s'importent mutuellement (archers, big-shoot-off, blasons, categories, colline, competition, departs, duels, en-cours, forfaits, inscriptions, palmares, patrimoine, phases, placement, poules, routage, saisie, saisie-duels, salle, suisse, suivi, suivi-deroule, tableaux) : aucune ne peut plus être lue, testée ni retirée seule (règle 10). Lecture heuristique — jamais bloquante.",
   "severite": "signal",
   "sujet": "archers"
  },
  {
   "code": "features-enchevetrees",
   "message": "et 1 autre(s) feature(s) s'importent mutuellement (bareme, grain-validation) : aucune ne peut plus être lue, testée ni retirée seule (règle 10). Lecture heuristique — jamais bloquante.",
   "severite": "signal",
   "sujet": "bareme"
  },
  {
   "code": "port-hors-domaine",
   "message": "déclare 26 port(s) hors du domaine (CompteurEngages, ConstructeurArchive, DiffusionSimulation, EvaluateurArrets…) — la règle 2 veut les ports dans le domaine et les adapters dans l'infrastructure. Écart peut-être légitime (une préoccupation technique n'est pas du métier de tir à l'arc) : à trancher par un humain, pas par la porte. Détail sur « La carte du code ».",
   "severite": "signal",
   "sujet": "application"
  },
  {
   "code": "portage-non-verifiable",
   "message": "annonce DEPART dans « backend/infrastructure/db/repositories/ », qui n'est pas un fichier lisible symbole par symbole : la promesse existe mais n'est pas contrôlée.",
   "severite": "signal",
   "sujet": "ADR-0017"
  },
  {
   "code": "portage-non-verifiable",
   "message": "annonce podium dans « backend/tests/ », qui n'est pas un fichier lisible symbole par symbole : la promesse existe mais n'est pas contrôlée.",
   "severite": "signal",
   "sujet": "ADR-0061"
  },
  {
   "code": "portage-non-verifiable",
   "message": "annonce Pages.carte dans « atlas/code.html », qui n'est pas un fichier lisible symbole par symbole : la promesse existe mais n'est pas contrôlée.",
   "severite": "signal",
   "sujet": "ADR-0086"
  },
  {
   "code": "portage-non-verifiable",
   "message": "annonce Pages.carte dans « atlas/statique/pages.js », qui n'est pas un fichier lisible symbole par symbole : la promesse existe mais n'est pas contrôlée.",
   "severite": "signal",
   "sujet": "ADR-0086"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce Protocol dans « backend/domain/tableau.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0004"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce elimination_directe dans « backend/domain/politiques.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0062"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce FormatTournoi.effectif_minimum_exige dans « backend/domain/deroule.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0069"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce PrelevementVide dans « backend/application/formats.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0069"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce pour_tournoi, phase_id dans « backend/application/classements.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0075"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce DecorDeSaisie.VOLEE_COLLECTIVE dans « frontend/src/features/big-shoot-off/SaisieBigShootOff.tsx » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0083"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce LecteurClassementBigShootOff dans « backend/application/big_shoot_off.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0083"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce ProchainDuel, _resultat_classant, ScoreAvecHandicap, RoutingRepechage dans « backend/tests/test_domain_contrat_phase.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0083"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce brancher_poules dans « backend/application/saisie_duels.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0083"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce saisir_manche, saisir_barrage, projection dans « backend/application/saisie.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0091"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce CeQuiManqueEncore dans « frontend/src/features/suisse/presentation.test.ts » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0092"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce CeQuiManqueEncore dans « frontend/src/features/suisse/presentation.ts » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0092"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce IntegrityError, doublon_d_arret dans « backend/infrastructure/db/models.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0092"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce IntegrityError, doublon_d_arret dans « backend/migrations/versions/0049_arret_de_circonstance.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0092"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce PoserUnePause, peutPoserUnePause, toursBloquablesRestants dans « frontend/src/features/suivi-deroule/api.ts » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0092"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce PoserUnePause, peutPoserUnePause, toursBloquablesRestants dans « frontend/src/features/suivi-deroule/hooks.ts » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0092"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce test_un_arret_relatif_coupe_la_phase_quand_son_tour_s_acheve dans « backend/application/arrets_programmes.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0092"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce test_chaque_format_porte_un_media_type_distinct dans « backend/api/documents.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0101"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce test_le_catalogue_construit_annonce_les_formats_qu_on_lui_donne dans « backend/application/exports.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0101"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce test_le_catalogue_construit_annonce_les_formats_qu_on_lui_donne dans « backend/bootstrap/composition.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0101"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce test_le_contenu_compose_ne_depend_pas_du_format dans « backend/application/listes_impression.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0101"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce test_un_club_nomme_comme_une_formule_n_est_pas_execute, test_les_montants_ne_sont_jamais_neutralises dans « backend/infrastructure/tableur/listes_impression.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0101"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce vu_par_archer dans « backend/domain/classement_clubs.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0104"
  },
  {
   "code": "portage-symbole-absent",
   "message": "annonce application.formats.LecteurDonneesDePhase dans « backend/domain/ports.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0106"
  }
 ],
 "resume": {
  "bloquants": 0,
  "signaux": 46
 }
};
