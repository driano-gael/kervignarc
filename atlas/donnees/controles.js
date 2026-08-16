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
   "code": "etat-contradictoire",
   "message": "porte deux états différents selon la section : ✅ dans « J3 — Placement intégral 1→N + écran de salle — 🔶 **en cours (16/18)** » · ⬜ dans « Résorptions de dette planifiées (arbitrages du 07/08/2026) ».",
   "severite": "signal",
   "sujet": "E05US023"
  },
  {
   "code": "features-enchevetrees",
   "message": "et 1 autre(s) feature(s) s'importent mutuellement (admin, tournois) : aucune ne peut plus être lue, testée ni retirée seule (règle 10). Lecture heuristique — jamais bloquante.",
   "severite": "signal",
   "sujet": "admin"
  },
  {
   "code": "features-enchevetrees",
   "message": "et 18 autre(s) feature(s) s'importent mutuellement (archers, blasons, categories, competition, departs, duels, forfaits, inscriptions, palmares, patrimoine, phases, placement, poules, routage, saisie-duels, salle, suivi, suivi-deroule, tableaux) : aucune ne peut plus être lue, testée ni retirée seule (règle 10). Lecture heuristique — jamais bloquante.",
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
   "message": "déclare 20 port(s) hors du domaine (CompteurEngages, ConstructeurArchive, DiffusionSimulation, GenerateurScores…) — la règle 2 veut les ports dans le domaine et les adapters dans l'infrastructure. Écart peut-être légitime (une préoccupation technique n'est pas du métier de tir à l'arc) : à trancher par un humain, pas par la porte. Détail sur « La carte du code ».",
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
   "message": "annonce saisie_duels.TYPES_DELEGUES, palmares._TYPES_CLASSANTS_AU_PALMARES dans « backend/domain/contrat_phase.py » — introuvable(s) dans le fichier.",
   "severite": "signal",
   "sujet": "ADR-0083"
  }
 ],
 "resume": {
  "bloquants": 0,
  "signaux": 31
 }
};
