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
   "message": "et 24 autre(s) feature(s) s'importent mutuellement (archers, big-shoot-off, blasons, categories, colline, competition, departs, duels, en-cours, equipes, forfaits, inscriptions, palmares, patrimoine, phases, placement, poules, routage, saisie, saisie-duels, salle, suisse, suivi, suivi-deroule, tableaux) : aucune ne peut plus être lue, testée ni retirée seule (règle 10). Lecture heuristique — jamais bloquante.",
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
   "message": "déclare 31 port(s) hors du domaine (CompteurArchersParTournoi, CompteurEngages, ConstructeurArchive, DiffusionSimulation…) — la règle 2 veut les ports dans le domaine et les adapters dans l'infrastructure. Écart peut-être légitime (une préoccupation technique n'est pas du métier de tir à l'arc) : à trancher par un humain, pas par la porte. Détail sur « La carte du code ».",
   "severite": "signal",
   "sujet": "application, infrastructure"
  },
  {
   "code": "portage-non-verifiable",
   "message": "annonce DEPART dans « backend/infrastructure/db/repositories/ », qui n'est pas un fichier lisible symbole par symbole : la promesse existe mais n'est pas contrôlée.",
   "severite": "signal",
   "sujet": "ADR-0017"
  },
  {
   "code": "portage-non-verifiable",
   "message": "annonce Equipe, TypeEquipe, EFFECTIF_FFTA, ecarts_de_composition, ServiceEquipes, EquipeRepositorySQL, equipe, membre_equipe dans « frontend/src/features/equipes/ », qui n'est pas un fichier lisible symbole par symbole : la promesse existe mais n'est pas contrôlée.",
   "severite": "signal",
   "sujet": "ADR-0028"
  },
  {
   "code": "portage-non-verifiable",
   "message": "annonce InscriptionRepositorySQL.supprimer_avec_remboursement, DepartRepositorySQL.supprimer_avec_remboursements, ArcherRepositorySQL.supprimer_avec_remboursements, DELETE, commit dans « backend/infrastructure/db/repositories/ », qui n'est pas un fichier lisible symbole par symbole : la promesse existe mais n'est pas contrôlée.",
   "severite": "signal",
   "sujet": "ADR-0057"
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
   "code": "portage-non-verifiable",
   "message": "annonce InterVariable.woff2, OFL.txt dans « frontend/src/assets/fonts/ », qui n'est pas un fichier lisible symbole par symbole : la promesse existe mais n'est pas contrôlée.",
   "severite": "signal",
   "sujet": "ADR-0116"
  },
  {
   "code": "portage-non-verifiable",
   "message": "annonce swap, input, select, textarea dans « frontend/src/index.css », qui n'est pas un fichier lisible symbole par symbole : la promesse existe mais n'est pas contrôlée.",
   "severite": "signal",
   "sujet": "ADR-0116"
  }
 ],
 "resume": {
  "bloquants": 0,
  "signaux": 26
 }
};
