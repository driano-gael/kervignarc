/* GÉNÉRÉ par `cd backend && python -m atlas` — ne pas éditer à la main.
   Toute modification sera écrasée à la régénération et rejetée par la CI. */
window.ATLAS = window.ATLAS || {};
window.ATLAS.carte = {
 "couches": [
  "domain",
  "application",
  "infrastructure",
  "api",
  "bootstrap"
 ],
 "front": {
  "enchevetrements": [
   [
    "archers",
    "big-shoot-off",
    "blasons",
    "categories",
    "colline",
    "competition",
    "departs",
    "duels",
    "en-cours",
    "forfaits",
    "inscriptions",
    "palmares",
    "patrimoine",
    "phases",
    "placement",
    "poules",
    "routage",
    "saisie",
    "saisie-duels",
    "salle",
    "suisse",
    "suivi",
    "suivi-deroule",
    "tableaux"
   ],
   [
    "accueil",
    "completude",
    "jalons",
    "paiements"
   ],
   [
    "admin",
    "recherche",
    "tournois"
   ],
   [
    "bareme",
    "grain-validation"
   ]
  ],
  "fan_in": [
   {
    "clientes": 18,
    "feature": "competition"
   },
   {
    "clientes": 17,
    "feature": "departs"
   },
   {
    "clientes": 10,
    "feature": "salle"
   },
   {
    "clientes": 8,
    "feature": "phases"
   },
   {
    "clientes": 8,
    "feature": "saisie-duels"
   },
   {
    "clientes": 7,
    "feature": "categories"
   },
   {
    "clientes": 6,
    "feature": "blasons"
   },
   {
    "clientes": 6,
    "feature": "placement"
   },
   {
    "clientes": 5,
    "feature": "clubs"
   },
   {
    "clientes": 5,
    "feature": "patrimoine"
   },
   {
    "clientes": 5,
    "feature": "routage"
   },
   {
    "clientes": 4,
    "feature": "archers"
   },
   {
    "clientes": 4,
    "feature": "colline"
   },
   {
    "clientes": 4,
    "feature": "completude"
   },
   {
    "clientes": 4,
    "feature": "poules"
   },
   {
    "clientes": 4,
    "feature": "suisse"
   },
   {
    "clientes": 4,
    "feature": "suivi-deroule"
   },
   {
    "clientes": 3,
    "feature": "accueil"
   },
   {
    "clientes": 3,
    "feature": "ecrans"
   },
   {
    "clientes": 3,
    "feature": "forfaits"
   },
   {
    "clientes": 3,
    "feature": "identite"
   },
   {
    "clientes": 3,
    "feature": "jalons"
   },
   {
    "clientes": 3,
    "feature": "palmares"
   },
   {
    "clientes": 3,
    "feature": "suivi"
   },
   {
    "clientes": 2,
    "feature": "admin"
   },
   {
    "clientes": 2,
    "feature": "bareme"
   },
   {
    "clientes": 2,
    "feature": "big-shoot-off"
   },
   {
    "clientes": 2,
    "feature": "duels"
   },
   {
    "clientes": 2,
    "feature": "en-cours"
   },
   {
    "clientes": 2,
    "feature": "grain-validation"
   },
   {
    "clientes": 2,
    "feature": "paiements"
   },
   {
    "clientes": 2,
    "feature": "saisie"
   },
   {
    "clientes": 2,
    "feature": "supervision"
   },
   {
    "clientes": 2,
    "feature": "tableaux"
   },
   {
    "clientes": 2,
    "feature": "tournois"
   },
   {
    "clientes": 1,
    "feature": "archive"
   },
   {
    "clientes": 1,
    "feature": "deroule"
   },
   {
    "clientes": 1,
    "feature": "exports"
   },
   {
    "clientes": 1,
    "feature": "feu-vert"
   },
   {
    "clientes": 1,
    "feature": "gabarits"
   },
   {
    "clientes": 1,
    "feature": "inscriptions"
   },
   {
    "clientes": 1,
    "feature": "jeu-essai"
   },
   {
    "clientes": 1,
    "feature": "postes"
   },
   {
    "clientes": 1,
    "feature": "recherche"
   },
   {
    "clientes": 1,
    "feature": "scoreurs"
   },
   {
    "clientes": 1,
    "feature": "simulation"
   }
  ],
  "features": 49
 },
 "matrice": [
  {
   "autorise": false,
   "cible": "application",
   "occurrences": 0,
   "source": "domain"
  },
  {
   "autorise": false,
   "cible": "infrastructure",
   "occurrences": 0,
   "source": "domain"
  },
  {
   "autorise": false,
   "cible": "api",
   "occurrences": 0,
   "source": "domain"
  },
  {
   "autorise": false,
   "cible": "bootstrap",
   "occurrences": 0,
   "source": "domain"
  },
  {
   "autorise": true,
   "cible": "domain",
   "occurrences": 360,
   "source": "application"
  },
  {
   "autorise": false,
   "cible": "infrastructure",
   "occurrences": 0,
   "source": "application"
  },
  {
   "autorise": false,
   "cible": "api",
   "occurrences": 0,
   "source": "application"
  },
  {
   "autorise": false,
   "cible": "bootstrap",
   "occurrences": 0,
   "source": "application"
  },
  {
   "autorise": true,
   "cible": "domain",
   "occurrences": 86,
   "source": "infrastructure"
  },
  {
   "autorise": true,
   "cible": "application",
   "occurrences": 1,
   "source": "infrastructure"
  },
  {
   "autorise": false,
   "cible": "api",
   "occurrences": 0,
   "source": "infrastructure"
  },
  {
   "autorise": false,
   "cible": "bootstrap",
   "occurrences": 0,
   "source": "infrastructure"
  },
  {
   "autorise": true,
   "cible": "domain",
   "occurrences": 96,
   "source": "api"
  },
  {
   "autorise": true,
   "cible": "application",
   "occurrences": 71,
   "source": "api"
  },
  {
   "autorise": true,
   "cible": "infrastructure",
   "occurrences": 42,
   "source": "api"
  },
  {
   "autorise": false,
   "cible": "bootstrap",
   "occurrences": 0,
   "source": "api"
  },
  {
   "autorise": true,
   "cible": "domain",
   "occurrences": 3,
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "application",
   "occurrences": 53,
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "infrastructure",
   "occurrences": 12,
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "api",
   "occurrences": 57,
   "source": "bootstrap"
  }
 ],
 "paquets": [
  {
   "autorise": true,
   "cible": "api",
   "couche_cible": "api",
   "couche_source": "api",
   "occurrences": 42,
   "origines": [
    "backend/api/v1/archive.py",
    "backend/api/v1/audit.py",
    "backend/api/v1/auth.py",
    "backend/api/v1/bareme_qualification.py",
    "backend/api/v1/barrages.py",
    "backend/api/v1/big_shoot_off.py",
    "backend/api/v1/blasons.py",
    "backend/api/v1/categories.py",
    "backend/api/v1/clubs.py",
    "backend/api/v1/colline.py",
    "backend/api/v1/competition.py",
    "backend/api/v1/completude.py",
    "backend/api/v1/departs.py",
    "backend/api/v1/documents_salle.py",
    "backend/api/v1/ecrans.py",
    "backend/api/v1/feuille_de_marque.py",
    "backend/api/v1/forfaits.py",
    "backend/api/v1/formats.py",
    "backend/api/v1/gabarits.py",
    "backend/api/v1/grain_validation.py",
    "backend/api/v1/identite.py",
    "backend/api/v1/inscriptions.py",
    "backend/api/v1/jalons.py",
    "backend/api/v1/jeu_essai.py",
    "backend/api/v1/listes_impression.py",
    "backend/api/v1/paiements.py",
    "backend/api/v1/patrimoine.py",
    "backend/api/v1/phases.py",
    "backend/api/v1/pilotage.py",
    "backend/api/v1/placement.py",
    "backend/api/v1/placement_duels.py",
    "backend/api/v1/postes.py",
    "backend/api/v1/poules.py",
    "backend/api/v1/recherche.py",
    "backend/api/v1/remboursements.py",
    "backend/api/v1/saisie.py",
    "backend/api/v1/saisie_duels.py",
    "backend/api/v1/scoreurs.py",
    "backend/api/v1/simulation.py",
    "backend/api/v1/suisse.py",
    "backend/api/v1/supervision.py",
    "backend/api/v1/tournois.py"
   ],
   "source": "api/v1"
  },
  {
   "autorise": true,
   "cible": "application",
   "couche_cible": "application",
   "couche_source": "api",
   "occurrences": 3,
   "origines": [
    "backend/api/dependances.py"
   ],
   "source": "api"
  },
  {
   "autorise": true,
   "cible": "application/erreurs",
   "couche_cible": "application",
   "couche_source": "api",
   "occurrences": 2,
   "origines": [
    "backend/api/dependances.py",
    "backend/api/erreurs.py"
   ],
   "source": "api"
  },
  {
   "autorise": true,
   "cible": "application",
   "couche_cible": "application",
   "couche_source": "api",
   "occurrences": 58,
   "origines": [
    "backend/api/v1/archive.py",
    "backend/api/v1/audit.py",
    "backend/api/v1/auth.py",
    "backend/api/v1/bareme_qualification.py",
    "backend/api/v1/barrages.py",
    "backend/api/v1/big_shoot_off.py",
    "backend/api/v1/blasons.py",
    "backend/api/v1/categories.py",
    "backend/api/v1/clubs.py",
    "backend/api/v1/colline.py",
    "backend/api/v1/competition.py",
    "backend/api/v1/completude.py",
    "backend/api/v1/departs.py",
    "backend/api/v1/deroule.py",
    "backend/api/v1/documents_salle.py",
    "backend/api/v1/ecrans.py",
    "backend/api/v1/feuille_de_marque.py",
    "backend/api/v1/forfaits.py",
    "backend/api/v1/formats.py",
    "backend/api/v1/gabarits.py",
    "backend/api/v1/grain_validation.py",
    "backend/api/v1/identite.py",
    "backend/api/v1/inscriptions.py",
    "backend/api/v1/jalons.py",
    "backend/api/v1/jeu_essai.py",
    "backend/api/v1/listes_impression.py",
    "backend/api/v1/paiements.py",
    "backend/api/v1/palmares.py",
    "backend/api/v1/patrimoine.py",
    "backend/api/v1/phases.py",
    "backend/api/v1/pilotage.py",
    "backend/api/v1/placement.py",
    "backend/api/v1/placement_duels.py",
    "backend/api/v1/postes.py",
    "backend/api/v1/poules.py",
    "backend/api/v1/recherche.py",
    "backend/api/v1/remboursements.py",
    "backend/api/v1/routage.py",
    "backend/api/v1/saisie.py",
    "backend/api/v1/saisie_duels.py",
    "backend/api/v1/scoreurs.py",
    "backend/api/v1/simulation.py",
    "backend/api/v1/suisse.py",
    "backend/api/v1/suivi_deroule.py",
    "backend/api/v1/supervision.py",
    "backend/api/v1/tableaux.py",
    "backend/api/v1/tournois.py"
   ],
   "source": "api/v1"
  },
  {
   "autorise": true,
   "cible": "application/erreurs",
   "couche_cible": "application",
   "couche_source": "api",
   "occurrences": 8,
   "origines": [
    "backend/api/v1/big_shoot_off.py",
    "backend/api/v1/colline.py",
    "backend/api/v1/forfaits.py",
    "backend/api/v1/identite.py",
    "backend/api/v1/poules.py",
    "backend/api/v1/saisie.py",
    "backend/api/v1/saisie_duels.py",
    "backend/api/v1/suisse.py"
   ],
   "source": "api/v1"
  },
  {
   "autorise": true,
   "cible": "domain",
   "couche_cible": "domain",
   "couche_source": "api",
   "occurrences": 2,
   "origines": [
    "backend/api/dependances.py"
   ],
   "source": "api"
  },
  {
   "autorise": true,
   "cible": "domain/erreurs",
   "couche_cible": "domain",
   "couche_source": "api",
   "occurrences": 1,
   "origines": [
    "backend/api/erreurs.py"
   ],
   "source": "api"
  },
  {
   "autorise": true,
   "cible": "domain",
   "couche_cible": "domain",
   "couche_source": "api",
   "occurrences": 92,
   "origines": [
    "backend/api/v1/audit.py",
    "backend/api/v1/bareme_qualification.py",
    "backend/api/v1/barrages.py",
    "backend/api/v1/big_shoot_off.py",
    "backend/api/v1/blasons.py",
    "backend/api/v1/categories.py",
    "backend/api/v1/clubs.py",
    "backend/api/v1/colline.py",
    "backend/api/v1/competition.py",
    "backend/api/v1/completude.py",
    "backend/api/v1/departs.py",
    "backend/api/v1/deroule.py",
    "backend/api/v1/ecrans.py",
    "backend/api/v1/forfaits.py",
    "backend/api/v1/formats.py",
    "backend/api/v1/gabarits.py",
    "backend/api/v1/grain_validation.py",
    "backend/api/v1/identite.py",
    "backend/api/v1/jalons.py",
    "backend/api/v1/listes_impression.py",
    "backend/api/v1/paiements.py",
    "backend/api/v1/palmares.py",
    "backend/api/v1/patrimoine.py",
    "backend/api/v1/phases.py",
    "backend/api/v1/placement.py",
    "backend/api/v1/postes.py",
    "backend/api/v1/poules.py",
    "backend/api/v1/recherche.py",
    "backend/api/v1/remboursements.py",
    "backend/api/v1/routage.py",
    "backend/api/v1/saisie.py",
    "backend/api/v1/saisie_duels.py",
    "backend/api/v1/scoreurs.py",
    "backend/api/v1/simulation.py",
    "backend/api/v1/suisse.py",
    "backend/api/v1/suivi_deroule.py",
    "backend/api/v1/supervision.py",
    "backend/api/v1/tournois.py"
   ],
   "source": "api/v1"
  },
  {
   "autorise": true,
   "cible": "domain/erreurs",
   "couche_cible": "domain",
   "couche_source": "api",
   "occurrences": 1,
   "origines": [
    "backend/api/v1/barrages.py"
   ],
   "source": "api/v1"
  },
  {
   "autorise": true,
   "cible": "infrastructure",
   "couche_cible": "infrastructure",
   "couche_source": "api",
   "occurrences": 1,
   "origines": [
    "backend/api/erreurs.py"
   ],
   "source": "api"
  },
  {
   "autorise": true,
   "cible": "infrastructure/realtime",
   "couche_cible": "infrastructure",
   "couche_source": "api",
   "occurrences": 2,
   "origines": [
    "backend/api/realtime.py",
    "backend/api/realtime_simulation.py"
   ],
   "source": "api"
  },
  {
   "autorise": true,
   "cible": "infrastructure",
   "couche_cible": "infrastructure",
   "couche_source": "api",
   "occurrences": 7,
   "origines": [
    "backend/api/v1/big_shoot_off.py",
    "backend/api/v1/colline.py",
    "backend/api/v1/forfaits.py",
    "backend/api/v1/poules.py",
    "backend/api/v1/saisie.py",
    "backend/api/v1/saisie_duels.py",
    "backend/api/v1/suisse.py"
   ],
   "source": "api/v1"
  },
  {
   "autorise": true,
   "cible": "infrastructure/db",
   "couche_cible": "infrastructure",
   "couche_source": "api",
   "occurrences": 31,
   "origines": [
    "backend/api/v1/bareme_qualification.py",
    "backend/api/v1/barrages.py",
    "backend/api/v1/big_shoot_off.py",
    "backend/api/v1/blasons.py",
    "backend/api/v1/categories.py",
    "backend/api/v1/clubs.py",
    "backend/api/v1/colline.py",
    "backend/api/v1/competition.py",
    "backend/api/v1/departs.py",
    "backend/api/v1/ecrans.py",
    "backend/api/v1/forfaits.py",
    "backend/api/v1/formats.py",
    "backend/api/v1/gabarits.py",
    "backend/api/v1/grain_validation.py",
    "backend/api/v1/identite.py",
    "backend/api/v1/inscriptions.py",
    "backend/api/v1/jeu_essai.py",
    "backend/api/v1/paiements.py",
    "backend/api/v1/patrimoine.py",
    "backend/api/v1/phases.py",
    "backend/api/v1/pilotage.py",
    "backend/api/v1/placement.py",
    "backend/api/v1/placement_duels.py",
    "backend/api/v1/postes.py",
    "backend/api/v1/poules.py",
    "backend/api/v1/remboursements.py",
    "backend/api/v1/saisie.py",
    "backend/api/v1/saisie_duels.py",
    "backend/api/v1/scoreurs.py",
    "backend/api/v1/suisse.py",
    "backend/api/v1/tournois.py"
   ],
   "source": "api/v1"
  },
  {
   "autorise": true,
   "cible": "infrastructure/realtime",
   "couche_cible": "infrastructure",
   "couche_source": "api",
   "occurrences": 1,
   "origines": [
    "backend/api/v1/pilotage.py"
   ],
   "source": "api/v1"
  },
  {
   "autorise": true,
   "cible": "application/erreurs",
   "couche_cible": "application",
   "couche_source": "application",
   "occurrences": 51,
   "origines": [
    "backend/application/archers.py",
    "backend/application/archive.py",
    "backend/application/arrets_programmes.py",
    "backend/application/audit.py",
    "backend/application/auth.py",
    "backend/application/bareme_qualification.py",
    "backend/application/barrages.py",
    "backend/application/big_shoot_off.py",
    "backend/application/blasons.py",
    "backend/application/categories.py",
    "backend/application/classements.py",
    "backend/application/clubs.py",
    "backend/application/colline.py",
    "backend/application/completude.py",
    "backend/application/departs.py",
    "backend/application/documents_salle.py",
    "backend/application/ecrans.py",
    "backend/application/feuille_de_marque.py",
    "backend/application/forfaits.py",
    "backend/application/formats.py",
    "backend/application/gabarits.py",
    "backend/application/gel_de_pause.py",
    "backend/application/grain_validation.py",
    "backend/application/identite.py",
    "backend/application/inscriptions.py",
    "backend/application/jalons.py",
    "backend/application/jeu_essai.py",
    "backend/application/listes_impression.py",
    "backend/application/paiements.py",
    "backend/application/palmares.py",
    "backend/application/patrimoine.py",
    "backend/application/phases.py",
    "backend/application/pilotage_simulation.py",
    "backend/application/pilotage_tour.py",
    "backend/application/placement.py",
    "backend/application/placement_duels.py",
    "backend/application/postes.py",
    "backend/application/poules.py",
    "backend/application/prelevement.py",
    "backend/application/remboursements.py",
    "backend/application/routage.py",
    "backend/application/saisie.py",
    "backend/application/saisie_duels.py",
    "backend/application/scoreurs.py",
    "backend/application/simulation.py",
    "backend/application/simulation_format.py",
    "backend/application/suisse.py",
    "backend/application/suivi_deroule.py",
    "backend/application/supervision.py",
    "backend/application/tableaux_publics.py",
    "backend/application/tournois.py"
   ],
   "source": "application"
  },
  {
   "autorise": true,
   "cible": "domain",
   "couche_cible": "domain",
   "couche_source": "application",
   "occurrences": 346,
   "origines": [
    "backend/application/archers.py",
    "backend/application/archive.py",
    "backend/application/arrets_programmes.py",
    "backend/application/audit.py",
    "backend/application/bareme_qualification.py",
    "backend/application/barrages.py",
    "backend/application/big_shoot_off.py",
    "backend/application/blasons.py",
    "backend/application/categories.py",
    "backend/application/classements.py",
    "backend/application/clubs.py",
    "backend/application/colline.py",
    "backend/application/completude.py",
    "backend/application/departs.py",
    "backend/application/documents_salle.py",
    "backend/application/ecrans.py",
    "backend/application/feuille_de_marque.py",
    "backend/application/forfaits.py",
    "backend/application/formats.py",
    "backend/application/gabarits.py",
    "backend/application/gel_de_pause.py",
    "backend/application/generateur_scores.py",
    "backend/application/grain_validation.py",
    "backend/application/identite.py",
    "backend/application/inscriptions.py",
    "backend/application/jalons.py",
    "backend/application/jeu_essai.py",
    "backend/application/listes_impression.py",
    "backend/application/paiements.py",
    "backend/application/palmares.py",
    "backend/application/patrimoine.py",
    "backend/application/phases.py",
    "backend/application/pilotage_simulation.py",
    "backend/application/pilotage_tour.py",
    "backend/application/placement.py",
    "backend/application/placement_duels.py",
    "backend/application/portee.py",
    "backend/application/postes.py",
    "backend/application/poules.py",
    "backend/application/prelevement.py",
    "backend/application/recherche.py",
    "backend/application/referentiel_ffta.py",
    "backend/application/remboursements.py",
    "backend/application/routage.py",
    "backend/application/saisie.py",
    "backend/application/saisie_duels.py",
    "backend/application/scoreurs.py",
    "backend/application/simulation.py",
    "backend/application/simulation_format.py",
    "backend/application/suisse.py",
    "backend/application/suivi_deroule.py",
    "backend/application/supervision.py",
    "backend/application/tableaux_publics.py",
    "backend/application/tournois.py"
   ],
   "source": "application"
  },
  {
   "autorise": true,
   "cible": "domain/erreurs",
   "couche_cible": "domain",
   "couche_source": "application",
   "occurrences": 14,
   "origines": [
    "backend/application/barrages.py",
    "backend/application/classements.py",
    "backend/application/clubs.py",
    "backend/application/formats.py",
    "backend/application/palmares.py",
    "backend/application/pilotage_simulation.py",
    "backend/application/pilotage_tour.py",
    "backend/application/poules.py",
    "backend/application/routage.py",
    "backend/application/saisie.py",
    "backend/application/saisie_duels.py",
    "backend/application/simulation.py",
    "backend/application/suivi_deroule.py",
    "backend/application/tableaux_publics.py"
   ],
   "source": "application"
  },
  {
   "autorise": true,
   "cible": "api",
   "couche_cible": "api",
   "couche_source": "bootstrap",
   "occurrences": 5,
   "origines": [
    "backend/bootstrap/composition.py"
   ],
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "api/v1",
   "couche_cible": "api",
   "couche_source": "bootstrap",
   "occurrences": 52,
   "origines": [
    "backend/bootstrap/composition.py"
   ],
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "application",
   "couche_cible": "application",
   "couche_source": "bootstrap",
   "occurrences": 53,
   "origines": [
    "backend/bootstrap/composition.py"
   ],
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "domain",
   "couche_cible": "domain",
   "couche_source": "bootstrap",
   "occurrences": 3,
   "origines": [
    "backend/bootstrap/composition.py"
   ],
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "infrastructure",
   "couche_cible": "infrastructure",
   "couche_source": "bootstrap",
   "occurrences": 2,
   "origines": [
    "backend/bootstrap/composition.py"
   ],
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "infrastructure/archive",
   "couche_cible": "infrastructure",
   "couche_source": "bootstrap",
   "occurrences": 1,
   "origines": [
    "backend/bootstrap/composition.py"
   ],
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "infrastructure/auth",
   "couche_cible": "infrastructure",
   "couche_source": "bootstrap",
   "occurrences": 1,
   "origines": [
    "backend/bootstrap/composition.py"
   ],
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "infrastructure/backup",
   "couche_cible": "infrastructure",
   "couche_source": "bootstrap",
   "occurrences": 2,
   "origines": [
    "backend/bootstrap/composition.py"
   ],
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "infrastructure/db",
   "couche_cible": "infrastructure",
   "couche_source": "bootstrap",
   "occurrences": 1,
   "origines": [
    "backend/bootstrap/composition.py"
   ],
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "infrastructure/memory",
   "couche_cible": "infrastructure",
   "couche_source": "bootstrap",
   "occurrences": 1,
   "origines": [
    "backend/bootstrap/composition.py"
   ],
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "infrastructure/pdf",
   "couche_cible": "infrastructure",
   "couche_source": "bootstrap",
   "occurrences": 1,
   "origines": [
    "backend/bootstrap/composition.py"
   ],
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "infrastructure/postes",
   "couche_cible": "infrastructure",
   "couche_source": "bootstrap",
   "occurrences": 1,
   "origines": [
    "backend/bootstrap/composition.py"
   ],
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "infrastructure/realtime",
   "couche_cible": "infrastructure",
   "couche_source": "bootstrap",
   "occurrences": 1,
   "origines": [
    "backend/bootstrap/composition.py"
   ],
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "infrastructure/scoreurs",
   "couche_cible": "infrastructure",
   "couche_source": "bootstrap",
   "occurrences": 1,
   "origines": [
    "backend/bootstrap/composition.py"
   ],
   "source": "bootstrap"
  },
  {
   "autorise": true,
   "cible": "domain/erreurs",
   "couche_cible": "domain",
   "couche_source": "domain",
   "occurrences": 34,
   "origines": [
    "backend/domain/anomalie.py",
    "backend/domain/archer.py",
    "backend/domain/arret_programme.py",
    "backend/domain/bareme.py",
    "backend/domain/barrage.py",
    "backend/domain/big_shoot_off.py",
    "backend/domain/blason.py",
    "backend/domain/categorie.py",
    "backend/domain/club.py",
    "backend/domain/colline.py",
    "backend/domain/depart.py",
    "backend/domain/deroule.py",
    "backend/domain/deroule_etape.py",
    "backend/domain/duel.py",
    "backend/domain/ecran.py",
    "backend/domain/entree_audit.py",
    "backend/domain/forfait.py",
    "backend/domain/format_tournoi.py",
    "backend/domain/gabarit_salle.py",
    "backend/domain/grain_validation.py",
    "backend/domain/identite.py",
    "backend/domain/phase.py",
    "backend/domain/plage.py",
    "backend/domain/politiques.py",
    "backend/domain/poste.py",
    "backend/domain/poule.py",
    "backend/domain/qualification.py",
    "backend/domain/remboursement.py",
    "backend/domain/score.py",
    "backend/domain/scoreur.py",
    "backend/domain/serie.py",
    "backend/domain/suisse.py",
    "backend/domain/tableau.py",
    "backend/domain/tournoi.py"
   ],
   "source": "domain"
  },
  {
   "autorise": true,
   "cible": "application",
   "couche_cible": "application",
   "couche_source": "infrastructure",
   "occurrences": 1,
   "origines": [
    "backend/infrastructure/auth/identifiants.py"
   ],
   "source": "infrastructure/auth"
  },
  {
   "autorise": true,
   "cible": "domain",
   "couche_cible": "domain",
   "couche_source": "infrastructure",
   "occurrences": 1,
   "origines": [
    "backend/infrastructure/backup/sauvegarde.py"
   ],
   "source": "infrastructure/backup"
  },
  {
   "autorise": true,
   "cible": "domain",
   "couche_cible": "domain",
   "couche_source": "infrastructure",
   "occurrences": 53,
   "origines": [
    "backend/infrastructure/db/repositories/_mapping.py",
    "backend/infrastructure/db/repositories/exploitation.py",
    "backend/infrastructure/db/repositories/moteur.py",
    "backend/infrastructure/db/repositories/referentiel.py",
    "backend/infrastructure/db/repositories/tir.py"
   ],
   "source": "infrastructure/db"
  },
  {
   "autorise": true,
   "cible": "domain/erreurs",
   "couche_cible": "domain",
   "couche_source": "infrastructure",
   "occurrences": 3,
   "origines": [
    "backend/infrastructure/db/repositories/exploitation.py",
    "backend/infrastructure/db/repositories/moteur.py",
    "backend/infrastructure/db/repositories/referentiel.py"
   ],
   "source": "infrastructure/db"
  },
  {
   "autorise": true,
   "cible": "domain",
   "couche_cible": "domain",
   "couche_source": "infrastructure",
   "occurrences": 17,
   "origines": [
    "backend/infrastructure/memory/repositories.py"
   ],
   "source": "infrastructure/memory"
  },
  {
   "autorise": true,
   "cible": "domain",
   "couche_cible": "domain",
   "couche_source": "infrastructure",
   "occurrences": 5,
   "origines": [
    "backend/infrastructure/pdf/documents_salle.py",
    "backend/infrastructure/pdf/feuille_de_marque.py",
    "backend/infrastructure/pdf/listes_impression.py",
    "backend/infrastructure/pdf/palmares.py"
   ],
   "source": "infrastructure/pdf"
  },
  {
   "autorise": true,
   "cible": "domain",
   "couche_cible": "domain",
   "couche_source": "infrastructure",
   "occurrences": 6,
   "origines": [
    "backend/infrastructure/postes/consignes.py",
    "backend/infrastructure/postes/presence.py",
    "backend/infrastructure/postes/sessions.py"
   ],
   "source": "infrastructure/postes"
  },
  {
   "autorise": true,
   "cible": "domain",
   "couche_cible": "domain",
   "couche_source": "infrastructure",
   "occurrences": 1,
   "origines": [
    "backend/infrastructure/scoreurs/sessions.py"
   ],
   "source": "infrastructure/scoreurs"
  },
  {
   "autorise": true,
   "cible": "infrastructure/db",
   "couche_cible": "infrastructure",
   "couche_source": "infrastructure",
   "occurrences": 1,
   "origines": [
    "backend/infrastructure/archive/constructeur.py"
   ],
   "source": "infrastructure/archive"
  },
  {
   "autorise": true,
   "cible": "infrastructure",
   "couche_cible": "infrastructure",
   "couche_source": "infrastructure",
   "occurrences": 1,
   "origines": [
    "backend/infrastructure/auth/identifiants.py"
   ],
   "source": "infrastructure/auth"
  },
  {
   "autorise": true,
   "cible": "infrastructure/db",
   "couche_cible": "infrastructure",
   "couche_source": "infrastructure",
   "occurrences": 1,
   "origines": [
    "backend/infrastructure/backup/sauvegarde.py"
   ],
   "source": "infrastructure/backup"
  },
  {
   "autorise": true,
   "cible": "infrastructure",
   "couche_cible": "infrastructure",
   "couche_source": "infrastructure",
   "occurrences": 4,
   "origines": [
    "backend/infrastructure/db/repositories/exploitation.py",
    "backend/infrastructure/db/repositories/moteur.py",
    "backend/infrastructure/db/repositories/referentiel.py",
    "backend/infrastructure/db/repositories/tir.py"
   ],
   "source": "infrastructure/db"
  },
  {
   "autorise": true,
   "cible": "infrastructure",
   "couche_cible": "infrastructure",
   "couche_source": "infrastructure",
   "occurrences": 1,
   "origines": [
    "backend/infrastructure/memory/repositories.py"
   ],
   "source": "infrastructure/memory"
  },
  {
   "autorise": true,
   "cible": "infrastructure",
   "couche_cible": "infrastructure",
   "couche_source": "infrastructure",
   "occurrences": 4,
   "origines": [
    "backend/infrastructure/pdf/documents_salle.py",
    "backend/infrastructure/pdf/feuille_de_marque.py",
    "backend/infrastructure/pdf/listes_impression.py",
    "backend/infrastructure/pdf/palmares.py"
   ],
   "source": "infrastructure/pdf"
  }
 ],
 "ports": [
  {
   "adapters": [
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "AggregationExAequo"
    },
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "AggregationParQualification"
    },
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "TiebreakAvecBarrage"
    },
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "TiebreakFftaDefaut"
    },
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "TiebreakPoules"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/politiques.py",
   "hors_domaine": false,
   "methodes": [
    "departager"
   ],
   "nom": "Aggregation",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "ArcherRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryArcherRepository"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "ajouter",
    "enregistrer",
    "fusionner",
    "par_club",
    "par_id",
    "par_tournoi",
    "supprimer",
    "tous"
   ],
   "nom": "ArcherRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "ArretDeCirconstanceRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "FranchissementArretRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "PhaseRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "InscriptionRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryInscriptionRepository"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryPhaseRepository"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "ajouter",
    "par_depart"
   ],
   "nom": "ArretDeCirconstanceRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/exploitation.py",
     "nom": "AuditRepositorySQL"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "consigner",
    "par_tournoi"
   ],
   "nom": "AuditRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/tir.py",
     "nom": "BarrageRepositorySQL"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "clore",
    "enregistrer_manche",
    "ouvrir",
    "par_depart",
    "par_id",
    "par_tournoi",
    "rouvrir",
    "supprimer"
   ],
   "nom": "BarrageRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "BlasonRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "CategorieRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryBlasonRepository"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryCategorieRepository"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "ajouter",
    "enregistrer",
    "par_bibliotheque",
    "par_id",
    "par_tournoi",
    "supprimer"
   ],
   "nom": "BlasonRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "ByesAuxMieuxClasses"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/politiques.py",
   "hors_domaine": false,
   "methodes": [
    "porteurs_de_bye"
   ],
   "nom": "Byes",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "CategorieRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryCategorieRepository"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "ajouter",
    "enregistrer",
    "par_bibliotheque",
    "par_blason",
    "par_id",
    "par_tournoi",
    "supprimer"
   ],
   "nom": "CategorieRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "FormatTournoiRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "ClubRepositorySQL"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "ajouter",
    "enregistrer",
    "lister",
    "par_id",
    "par_nom",
    "supprimer"
   ],
   "nom": "ClubRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/suivi_deroule.py",
     "nom": "CompteurEngagesRepository"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/suivi_deroule.py",
   "hors_domaine": true,
   "methodes": [
    "nb_engages_du_depart"
   ],
   "nom": "CompteurEngages",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/archive/constructeur.py",
     "nom": "ConstructeurArchiveZip"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/archive.py",
   "hors_domaine": true,
   "methodes": [
    "construire"
   ],
   "nom": "ConstructeurArchive",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "DepartRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryDepartRepository"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "ajouter",
    "enregistrer",
    "par_id",
    "par_tournoi",
    "supprimer",
    "supprimer_avec_remboursements"
   ],
   "nom": "DepartRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "AucunClassement"
    },
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "ProfondeurPodium"
    },
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "ProfondeurUnVersN"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/politiques.py",
   "hors_domaine": false,
   "methodes": [
    "rangs_a_classer"
   ],
   "nom": "Depth",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "DerouleEtapeRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "PhaseRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryDerouleRepository"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryPhaseRepository"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "ajouter",
    "enregistrer",
    "par_tournoi",
    "reordonner",
    "supprimer"
   ],
   "nom": "DerouleRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/gel_de_pause.py",
     "nom": "DeclencheurArrets"
    },
    {
     "fichier": "backend/infrastructure/realtime/diffusion_simulation.py",
     "nom": "DiffusionSimulationBroadcaster"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/pilotage_simulation.py",
   "hors_domaine": true,
   "methodes": [
    "signaler"
   ],
   "nom": "DiffusionSimulation",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/tir.py",
     "nom": "DuelRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryDuelRepository"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "charger",
    "enregistrer",
    "numeros_enregistres"
   ],
   "nom": "DuelRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/api/v1/formats.py",
     "nom": "EtapeDTO"
    },
    {
     "fichier": "backend/domain/deroule_etape.py",
     "nom": "EtapeDeroule"
    },
    {
     "fichier": "backend/domain/format_tournoi.py",
     "nom": "ModelePhase"
    },
    {
     "fichier": "backend/domain/phase.py",
     "nom": "Phase"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/deroule.py",
   "hors_domaine": false,
   "methodes": [
    "bareme",
    "effectif",
    "ordre",
    "poules",
    "sources",
    "type",
    "validation"
   ],
   "nom": "EtapeProjetable",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/api/v1/formats.py",
     "nom": "EtapeDTO"
    },
    {
     "fichier": "backend/api/v1/phases.py",
     "nom": "EtapeReponse"
    },
    {
     "fichier": "backend/api/v1/phases.py",
     "nom": "PhaseReponse"
    },
    {
     "fichier": "backend/domain/deroule_etape.py",
     "nom": "EtapeDeroule"
    },
    {
     "fichier": "backend/domain/format_tournoi.py",
     "nom": "ModelePhase"
    },
    {
     "fichier": "backend/domain/phase.py",
     "nom": "Phase"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/phase.py",
   "hors_domaine": false,
   "methodes": [
    "effectif",
    "ordre",
    "sources",
    "type"
   ],
   "nom": "EtapeSequencee",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/arrets_programmes.py",
     "nom": "ServiceArretsProgrammes"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/gel_de_pause.py",
   "hors_domaine": true,
   "methodes": [
    "evaluer"
   ],
   "nom": "EvaluateurArrets",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/tir.py",
     "nom": "ForfaitRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryForfaitRepository"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "annuler_avec_trace",
    "declarer_avec_trace",
    "par_archer_et_phase",
    "par_phase",
    "par_tournoi"
   ],
   "nom": "ForfaitRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "FormatTournoiRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "ClubRepositorySQL"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "ajouter",
    "enregistrer",
    "lister",
    "par_id",
    "par_nom",
    "supprimer"
   ],
   "nom": "FormatTournoiRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "FranchissementArretRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "PhaseRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "InscriptionRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryInscriptionRepository"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryPhaseRepository"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "ajouter",
    "enregistrer",
    "par_depart",
    "par_id"
   ],
   "nom": "FranchissementArretRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "GabaritSalleRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryGabaritSalleRepository"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "ajouter",
    "enregistrer",
    "lister",
    "par_id",
    "par_tournoi",
    "supprimer"
   ],
   "nom": "GabaritSalleRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/documents_salle.py",
     "nom": "ServiceDocumentsSalle"
    },
    {
     "fichier": "backend/infrastructure/pdf/documents_salle.py",
     "nom": "GenerateurDocumentsSallePdf"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "cartes_scoreurs",
    "etiquettes_cibles",
    "qr_rattachement"
   ],
   "nom": "GenerateurDocumentsSalle",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/feuille_de_marque.py",
     "nom": "ServiceFeuilleDeMarque"
    },
    {
     "fichier": "backend/infrastructure/pdf/feuille_de_marque.py",
     "nom": "GenerateurFeuilleDeMarquePdf"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "generer"
   ],
   "nom": "GenerateurFeuilleDeMarque",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/pdf/listes_impression.py",
     "nom": "GenerateurListesImpressionPdf"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "club_paiement",
    "placement"
   ],
   "nom": "GenerateurListesImpression",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/pdf/palmares.py",
     "nom": "GenerateurPalmaresPdf"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "palmares"
   ],
   "nom": "GenerateurPalmares",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/api/v1/simulation.py",
     "nom": "ProchaineUniteReponse"
    },
    {
     "fichier": "backend/application/generateur_scores.py",
     "nom": "GenerateurScoresPlausibles"
    },
    {
     "fichier": "backend/domain/serie.py",
     "nom": "Serie"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/generateur_scores.py",
   "hors_domaine": true,
   "methodes": [
    "volee"
   ],
   "nom": "GenerateurScores",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/horloge.py",
     "nom": "HorlogeSysteme"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "maintenant"
   ],
   "nom": "Horloge",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "IdentiteVisuelleRepositorySQL"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "empreinte_du_logo",
    "enregistrer_accents",
    "enregistrer_logo",
    "logo",
    "reglages"
   ],
   "nom": "IdentiteVisuelleRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "InscriptionRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryInscriptionRepository"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "ajouter",
    "definir_paye_avec_trace",
    "enregistrer",
    "par_archer",
    "par_archer_et_depart",
    "par_depart",
    "par_id",
    "supprimer",
    "supprimer_avec_remboursement"
   ],
   "nom": "InscriptionRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/saisie.py",
     "nom": "ServiceSaisie"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/supervision.py",
   "hors_domaine": true,
   "methodes": [
    "avancement_cible"
   ],
   "nom": "LecteurAvancement",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/big_shoot_off.py",
     "nom": "ServiceBigShootOff"
    },
    {
     "fichier": "backend/application/colline.py",
     "nom": "ServiceColline"
    },
    {
     "fichier": "backend/application/poules.py",
     "nom": "ServicePoules"
    },
    {
     "fichier": "backend/application/saisie.py",
     "nom": "ServiceSaisie"
    },
    {
     "fichier": "backend/application/suisse.py",
     "nom": "ServiceSuisse"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/suivi_deroule.py",
   "hors_domaine": true,
   "methodes": [
    "avancement_de_phase"
   ],
   "nom": "LecteurAvancementDePhase",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/completude.py",
     "nom": "ServiceCompletude"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/departs.py",
   "hors_domaine": true,
   "methodes": [
    "avancement_depart"
   ],
   "nom": "LecteurAvancementDepart",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/suivi_deroule.py",
     "nom": "ServiceSuiviDeroule"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/arrets_programmes.py",
   "hors_domaine": true,
   "methodes": [
    "avancement_par_phase"
   ],
   "nom": "LecteurAvancementDuDepart",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/big_shoot_off.py",
     "nom": "ServiceBigShootOff"
    },
    {
     "fichier": "backend/application/colline.py",
     "nom": "ServiceColline"
    },
    {
     "fichier": "backend/application/poules.py",
     "nom": "ServicePoules"
    },
    {
     "fichier": "backend/application/suisse.py",
     "nom": "ServiceSuisse"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/prelevement.py",
   "hors_domaine": true,
   "methodes": [
    "classement_de_phase"
   ],
   "nom": "LecteurClassementDePhase",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/completude.py",
     "nom": "ServiceCompletude"
    },
    {
     "fichier": "backend/application/identite.py",
     "nom": "ServiceIdentite"
    },
    {
     "fichier": "backend/application/palmares.py",
     "nom": "ServicePalmares"
    },
    {
     "fichier": "backend/domain/blason.py",
     "nom": "Blason"
    },
    {
     "fichier": "backend/domain/categorie.py",
     "nom": "Categorie"
    },
    {
     "fichier": "backend/domain/format_tournoi.py",
     "nom": "ModelePhase"
    },
    {
     "fichier": "backend/domain/gabarit_salle.py",
     "nom": "GabaritSalle"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/jalons.py",
   "hors_domaine": true,
   "methodes": [
    "pour_tournoi"
   ],
   "nom": "LecteurCompletude",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/exploitation.py",
     "nom": "AuditRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/exploitation.py",
     "nom": "PosteRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/exploitation.py",
     "nom": "ScoreurRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "DerouleEtapeRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "PhaseRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "ArcherRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "BlasonRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "CategorieRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "DepartRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "GabaritSalleRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "RemboursementRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/tir.py",
     "nom": "BarrageRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/tir.py",
     "nom": "ForfaitRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/tir.py",
     "nom": "ScoreRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/tir.py",
     "nom": "SerieRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryArcherRepository"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryBlasonRepository"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryCategorieRepository"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryDepartRepository"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryDerouleRepository"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryForfaitRepository"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryGabaritSalleRepository"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryPhaseRepository"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemorySerieRepository"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/tournois.py",
   "hors_domaine": true,
   "methodes": [
    "par_tournoi"
   ],
   "nom": "LecteurDerouleDuTournoi",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "PlacementParBlocRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "PlacementTableauRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/tir.py",
     "nom": "ForfaitRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/tir.py",
     "nom": "SerieRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryForfaitRepository"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryPlacementTableauRepository"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemorySerieRepository"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/formats.py",
   "hors_domaine": true,
   "methodes": [
    "par_phase"
   ],
   "nom": "LecteurDonneesDePhase",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/api/v1/completude.py",
     "nom": "LigneCompletudeReponse"
    },
    {
     "fichier": "backend/api/v1/departs.py",
     "nom": "DepartReponse"
    },
    {
     "fichier": "backend/api/v1/supervision.py",
     "nom": "LigneSupervisionReponse"
    },
    {
     "fichier": "backend/application/big_shoot_off.py",
     "nom": "ServiceBigShootOff"
    },
    {
     "fichier": "backend/application/colline.py",
     "nom": "ServiceColline"
    },
    {
     "fichier": "backend/application/departs.py",
     "nom": "ServiceDeparts"
    },
    {
     "fichier": "backend/application/pilotage_simulation.py",
     "nom": "ServicePilotageSimulation"
    },
    {
     "fichier": "backend/application/poules.py",
     "nom": "ServicePoules"
    },
    {
     "fichier": "backend/application/suisse.py",
     "nom": "ServiceSuisse"
    },
    {
     "fichier": "backend/application/supervision.py",
     "nom": "LigneSupervision"
    },
    {
     "fichier": "backend/application/supervision.py",
     "nom": "ServiceSupervision"
    },
    {
     "fichier": "backend/application/tableaux_publics.py",
     "nom": "TableauPublic"
    },
    {
     "fichier": "backend/domain/arret_programme.py",
     "nom": "FranchissementArret"
    },
    {
     "fichier": "backend/domain/big_shoot_off.py",
     "nom": "IssueManche"
    },
    {
     "fichier": "backend/domain/completude.py",
     "nom": "LigneCompletude"
    },
    {
     "fichier": "backend/domain/cycle_depart.py",
     "nom": "AvancementDepart"
    },
    {
     "fichier": "backend/infrastructure/db/models.py",
     "nom": "FranchissementArretORM"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/big_shoot_off.py",
   "hors_domaine": true,
   "methodes": [
    "etat"
   ],
   "nom": "LecteurEtatBigShootOff",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/tournois.py",
     "nom": "ServiceTournois"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/jalons.py",
   "hors_domaine": true,
   "methodes": [
    "exigence_effectif"
   ],
   "nom": "LecteurExigenceEffectif",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/inscriptions.py",
     "nom": "ServiceInscriptions"
    },
    {
     "fichier": "backend/application/paiements.py",
     "nom": "ServicePaiements"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/completude.py",
   "hors_domaine": true,
   "methodes": [
    "lister_par_archer"
   ],
   "nom": "LecteurPaiements",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/saisie_duels.py",
     "nom": "ServiceSaisieDuels"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/prelevement.py",
   "hors_domaine": true,
   "methodes": [
    "resolveur_de_classement"
   ],
   "nom": "LecteurPopulationPhase",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/ecrans.py",
     "nom": "ServiceEcrans"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/supervision.py",
   "hors_domaine": true,
   "methodes": [
    "prises"
   ],
   "nom": "LecteurPrises",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/paiements.py",
     "nom": "ServicePaiements"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/listes_impression.py",
   "hors_domaine": true,
   "methodes": [
    "recap_par_club"
   ],
   "nom": "LecteurRecapClub",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/colline.py",
     "nom": "ServiceColline"
    },
    {
     "fichier": "backend/application/poules.py",
     "nom": "ServicePoules"
    },
    {
     "fichier": "backend/application/suisse.py",
     "nom": "ServiceSuisse"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/routage.py",
   "hors_domaine": true,
   "methodes": [
    "rencontres_a_tirer"
   ],
   "nom": "LecteurRencontresARouter",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/application/saisie_duels.py",
     "nom": "ServiceSaisieDuels"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/suivi_deroule.py",
   "hors_domaine": true,
   "methodes": [
    "reconstruire"
   ],
   "nom": "LecteurTableau",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "PhaseRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryPhaseRepository"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "ajouter",
    "enregistrer",
    "par_depart",
    "par_depart_et_type",
    "par_id",
    "par_tournoi",
    "reordonner",
    "supprimer"
   ],
   "nom": "PhaseRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "PlacementParBlocRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "PlacementTableauRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryPlacementTableauRepository"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "definir_plan",
    "par_phase"
   ],
   "nom": "PlacementParBlocRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "PlacementRepositorySQL"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "definir_plan",
    "definir_plan_avec_trace",
    "par_depart",
    "poser_plusieurs",
    "retirer"
   ],
   "nom": "PlacementRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "PlacementTableauRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryPlacementTableauRepository"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "definir_plan",
    "par_phase",
    "poser_plusieurs",
    "retirer"
   ],
   "nom": "PlacementTableauRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/exploitation.py",
     "nom": "PosteRepositorySQL"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "ajouter",
    "enregistrer",
    "par_code",
    "par_id",
    "par_tournoi",
    "par_tournoi_et_type",
    "supprimer"
   ],
   "nom": "PosteRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/postes/consignes.py",
     "nom": "RegistreConsignesMemoire"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "poser",
    "prise_de",
    "retirer",
    "retirer_si",
    "toutes"
   ],
   "nom": "RegistreConsignes",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/postes/presence.py",
     "nom": "RegistrePresenceMemoire"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "derniere_activite",
    "enregistrer",
    "oublier"
   ],
   "nom": "RegistrePresence",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "RemboursementRepositorySQL"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "enregistrer_avec_trace",
    "par_id",
    "par_tournoi"
   ],
   "nom": "RemboursementRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/domain/duel.py",
     "nom": "ResolveurBaremeDuelFfta"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/duel.py",
   "hors_domaine": false,
   "methodes": [
    "bareme_pour"
   ],
   "nom": "ResolveurBaremeDuel",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "EliminationSeche"
    },
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "PlacementEnCascade"
    },
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "RoutingRepechage"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/politiques.py",
   "hors_domaine": false,
   "methodes": [
    "route"
   ],
   "nom": "Routing",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/tir.py",
     "nom": "ScoreRepositorySQL"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "ajouter",
    "par_archer",
    "par_tournoi"
   ],
   "nom": "ScoreRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/exploitation.py",
     "nom": "PosteRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/exploitation.py",
     "nom": "ScoreurRepositorySQL"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "ajouter",
    "enregistrer",
    "par_code",
    "par_id",
    "par_tournoi",
    "supprimer"
   ],
   "nom": "ScoreurRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/api/v1/competition.py",
     "nom": "LigneClassementReponse"
    },
    {
     "fichier": "backend/api/v1/completude.py",
     "nom": "LigneCompletudeReponse"
    },
    {
     "fichier": "backend/api/v1/formats.py",
     "nom": "LigneClassementDTO"
    },
    {
     "fichier": "backend/api/v1/recherche.py",
     "nom": "RechercheReponse"
    },
    {
     "fichier": "backend/domain/classement.py",
     "nom": "LigneClassement"
    },
    {
     "fichier": "backend/domain/classement.py",
     "nom": "_Decompte"
    },
    {
     "fichier": "backend/domain/completude.py",
     "nom": "LigneCompletude"
    },
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "ScoreAvecHandicap"
    },
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "ScoreCumul"
    },
    {
     "fichier": "backend/domain/recherche.py",
     "nom": "Recherche"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/politiques.py",
   "hors_domaine": false,
   "methodes": [
    "total"
   ],
   "nom": "Scoring",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "SeedingSerpent"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/politiques.py",
   "hors_domaine": false,
   "methodes": [
    "ordre_des_tetes"
   ],
   "nom": "Seeding",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/tir.py",
     "nom": "SerieRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemorySerieRepository"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "enregistrer",
    "enregistrer_avec_trace",
    "horodatages",
    "par_archer",
    "par_phase",
    "par_tournoi"
   ],
   "nom": "SerieRepository",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/auth/identifiants.py",
     "nom": "AdminCredentialsStore"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/auth.py",
   "hors_domaine": true,
   "methodes": [
    "ecrire",
    "lire"
   ],
   "nom": "StoreIdentifiantsAdmin",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/auth/sessions.py",
     "nom": "SessionStore"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/auth.py",
   "hors_domaine": true,
   "methodes": [
    "est_valide",
    "fermer",
    "ouvrir"
   ],
   "nom": "StoreSessions",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/postes/sessions.py",
     "nom": "PosteSessionStore"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/postes.py",
   "hors_domaine": true,
   "methodes": [
    "depart_courant_par_poste",
    "depart_de",
    "fermer",
    "fixer_depart",
    "invalider_poste",
    "ouvrir",
    "poste_de",
    "postes_rattaches"
   ],
   "nom": "StoreSessionsPoste",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/scoreurs/sessions.py",
     "nom": "ScoreurSessionStore"
    }
   ],
   "couche": "application",
   "fichier": "backend/application/scoreurs.py",
   "hors_domaine": true,
   "methodes": [
    "fermer",
    "invalider_scoreur",
    "ouvrir",
    "scoreur_de"
   ],
   "nom": "StoreSessionsScoreur",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "TiebreakAvecBarrage"
    },
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "TiebreakFftaDefaut"
    },
    {
     "fichier": "backend/domain/politiques.py",
     "nom": "TiebreakPoules"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/politiques.py",
   "hors_domaine": false,
   "methodes": [
    "barrage_requis",
    "departager"
   ],
   "nom": "Tiebreak",
   "sans_adapter": false
  },
  {
   "adapters": [
    {
     "fichier": "backend/infrastructure/db/repositories/moteur.py",
     "nom": "FormatTournoiRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "ClubRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "GabaritSalleRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/db/repositories/referentiel.py",
     "nom": "TournoiRepositorySQL"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryGabaritSalleRepository"
    },
    {
     "fichier": "backend/infrastructure/memory/repositories.py",
     "nom": "InMemoryTournoiRepository"
    }
   ],
   "couche": "domain",
   "fichier": "backend/domain/ports.py",
   "hors_domaine": false,
   "methodes": [
    "ajouter",
    "enregistrer",
    "lister",
    "par_id",
    "supprimer"
   ],
   "nom": "TournoiRepository",
   "sans_adapter": false
  }
 ],
 "resume": {
  "aretes_front": 173,
  "enchevetrements": 4,
  "features": 49,
  "imports": 920,
  "imports_entre_couches": 781,
  "plus_gros_noeud": 24,
  "ports": 68,
  "ports_hors_domaine": 25,
  "ports_sans_adapter": 0,
  "violations": 0
 },
 "sens_autorise": {
  "api": [
   "application",
   "domain",
   "infrastructure"
  ],
  "application": [
   "domain"
  ],
  "bootstrap": [
   "api",
   "application",
   "domain",
   "infrastructure"
  ],
  "domain": [],
  "infrastructure": [
   "application",
   "domain"
  ]
 }
};
