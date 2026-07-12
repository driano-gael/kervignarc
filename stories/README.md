# Backlog — User Stories (ordonné par montée en valeur)

Découpage fin des EPICs en user stories **à destination d'un développeur** (maille : un comportement testable, ~1-3 j, INVEST).

## Conventions
- **ID** : `ExxUSyyy` — `Exx` = code epic, `USyyy` = n° dans l'epic. L'ID rattache la story à son epic ; il **ne dicte pas l'ordre de réalisation**.
- **Ordre de réalisation** : la **séquence** ci-dessous, en **jalons de valeur** — on privilégie la montée en valeur, pas l'ordre des epics.
- Détail de chaque US : `stories/Exx-slug.md`. Format : *En tant que… je veux… afin de…* + **CA** (critères d'acceptation) + **Notes** (dev) + **Dépend de**.
- **Une branche par US** : `<type>/<ExxUSyyy>-<slug>` (ex. `feat/e04us003-saisie-fleches`), `type` selon le périmètre (feat/fix/refactor/test/docs/chore). PR + revue + CI verte → merge → suppression de la branche. Détail : `guide-architecture.md` §11.

## Jalons de valeur
| Jalon | Valeur livrée |
|---|---|
| **J0** | Walking skeleton : l'architecture tourne bout-en-bout |
| **J1** | Gérer un **tournoi de qualification complet** (premier usage réel) |
| **J2** | **Duels simples** : élimination directe → podium |
| **J3** | **Placement intégral 1→N** (format du classeur 120) + écran projeté |
| **J4** | Confort, richesse & robustesse (import, presets, repêchage, restauration) |

---

## J0 — Walking skeleton
| Seq | US | Titre |
|---|---|---|
| 1 | E00US001 | Initialiser le monorepo + gestionnaires (uv, pnpm/Vite) |
| 2 | E00US002 | Configurer la qualité (ruff, mypy strict, ESLint, Prettier, pre-commit) |
| 3 | E00US003 | CI bloquante (lint + types + tests) |
| 4 | E00US004 | Squelette de couches + garde-fou d'imports du domaine |
| 5 | E00US005 | Composition root minimale (bootstrap) |
| 6 | E00US006 | Connexion SQLite (WAL) + migration initiale (Alembic) |
| 7 | E00US007 | File d'écriture + writer unique |
| 8 | E00US008 | Canal WebSocket + diffusion d'un événement post-commit |
| 9 | E00US009 | Repository + endpoint de bout en bout (agrégat trivial) |
| 10 | E00US010 | Shell React (React Query + Zustand + client WS) |
| 11 | E00US011 | Tranche verticale démontrable |
| 12 | E00US012 | Exécutable de dev (FastAPI sert le build front) |

## J1 — Tournoi de qualification de bout en bout
| Seq | US | Titre |
|---|---|---|
| 13 | E01US001 | Créer un tournoi |
| 14 | E10US002 | Accès administrateur protégé |
| 15 | E10US001 | Consultation publique ouverte |
| 16 | E01US002 | Éditer / lister les tournois |
| 17 | E01US003 | Gérer les catégories (CRUD) |
| 18 | E01US004 | Pré-charger les catégories FFTA salle |
| 19 | E01US005 | Gérer les blasons (taille/fraction + capacité) |
| 20 | E01US006 | Associer catégorie ↔ blason |
| 21 | E01US007 | Définir un gabarit de salle |
| 22 | E01US008 | Réutiliser / ajuster un gabarit |
| 23 | E01US009 | Définir un barème de qualification |
| 24 | E01US010 | Définir le tarif par départ |
| 25 | E02US001 | Gérer le référentiel clubs |
| 26 | E02US002 | Créer un archer |
| 27 | E02US003 | Éditer / supprimer un archer |
| 28 | E02US004 | Ajouter des départs multiples |
| 29 | E08US001 | Calculer le montant dû |
| 30 | E03US001 | Modéliser cibles/positions depuis le gabarit |
| 31 | E03US002 | Placement auto : capacité + fraction de blason |
| 32 | E03US003 | Placement auto : signaler les conflits |
| 33 | E03US004 | Ajuster le placement en glisser-déposer |
| 34 | E03US005 | Empêcher un déplacement invalide |
| 35 | E03US008 | Générer le plan de cibles (qualif) |
| 36 | E10US003 | Session scoreur par code de cible |
| 37 | E10US004 | Habiliter un scoreur sur plusieurs cibles |
| 38 | E04US001 | Rattacher un appareil à une cible |
| 39 | E04US002 | Afficher la grille de saisie (4 archers) |
| 40 | E04US003 | Saisir les flèches d'une volée (pavé tactile) |
| 41 | E04US004 | Valider les valeurs autorisées (0-10 / M / X) |
| 42 | E04US005 | Enregistrer une volée via la file d'écriture |
| 43 | E04US006 | Éditer une volée non validée |
| 44 | E04US007 | Verrouiller une série validée |
| 45 | E04US008 | Cumuler le score sur les volées |
| 46 | E04US009 | Diffuser la mise à jour en live |
| 47 | E06US001 | Classement de qualification (cumul) |
| 48 | E06US002 | Départage qualif (nb de 10 puis 9) |
| 49 | E06US008 | Classement par catégorie |
| 50 | E07US001 | Vue publique des classements |
| 51 | E07US002 | Live des vues publiques |
| 52 | E04US010 | Mettre en file hors-ligne + rejouer |
| 53 | E04US011 | Indicateur d'état de connexion |
| 54 | E04US012 | Corriger une volée validée (tracé) |
| 55 | E10US005 | Journal d'audit métier |
| 56 | E08US002 | Marquer payé / non payé |
| 57 | E08US003 | Vue paiement par archer |
| 58 | E08US004 | Vue paiement par club |
| 59 | E02US005 | Détecter et fusionner les doublons |
| 60 | E02US006 | Contrôler les quotas |
| 61 | E07US003 | Vue publique des plans de cibles |
| 62 | E09US001 | Intégrer la bibliothèque PDF |
| 63 | E09US002 | Feuille de marque |
| 64 | E09US003 | Liste de placement |
| 65 | E09US004 | Liste club & paiement |
| 66 | E11US001 | Build de release exécutable |
| 67 | E11US002 | Création SQLite au 1er lancement |
| 68 | E11US003 | Sauvegarde automatique périodique |
| 69 | E11US004 | Export / archive en fin de tournoi |
| 70 | E11US005 | Procédure & doc réseau (routeur dédié, mDNS) |

## J2 — Duels simples (élimination directe → podium)
| Seq | US | Titre |
|---|---|---|
| 71 | E05US001 | Définir le modèle de séquence de phases |
| 72 | E05US002 | Éditer une séquence (ajouter/ordonner/typer) |
| 73 | E05US003 | Interfaces de politiques injectables |
| 74 | E05US004 | Assembler les politiques d'une phase (config JSON) |
| 75 | E05US005 | Arrondi 2^k + seeding serpent |
| 76 | E05US006 | Attribution des byes (aux mieux classés) |
| 77 | E05US007 | Générer l'arbre d'élimination directe |
| 78 | E05US008 | Progression : le gagnant avance |
| 79 | E05US009 | Terminer sur un podium |
| 80 | E05US017 | Contrôles de cohérence (phase mal alimentée) |
| 81 | E03US006 | Contrainte ≥ 2 clubs par cible |
| 82 | E03US009 | Placer les duellistes côte à côte |
| 83 | E04US013 | Saisie en sets (duels) |
| 84 | E04US014 | Désigner le vainqueur d'un match |
| 85 | E04US015 | Gérer abandon / disqualification |
| 86 | E04US016 | Déclencher un barrage/shoot-off (égalité) |
| 87 | E06US003 | Barrage de tir pour places décisives |
| 88 | E06US004 | Podium issu des duels |
| 89 | E06US005 | Agréger les rangs de tableau |

## J3 — Placement intégral 1→N + écran projeté
| Seq | US | Titre |
|---|---|---|
| 90 | E05US010 | Peuplement : rangs N→M |
| 91 | E05US011 | Peuplement : gagnants / perdants d'un tour |
| 92 | E05US012 | Routing cascade (placement intégral) |
| 93 | E05US013 | Division récursive des plages |
| 94 | E05US014 | Affectation des rangs terminaux (gagnant/perdant) |
| 95 | E05US015 | Big Shoot Off |
| 96 | E05US018 | Oracle 120 (rejeu + comparaison) |
| 97 | E06US006 | Classement intégral 1→N |
| 98 | E06US007 | Profondeur de classement configurable |
| 99 | E03US007 | Contrainte séparation catégorie/blason |
| 100 | E09US005 | Classement PDF par catégorie |
| 101 | E09US006 | Classement intégral 1→N (PDF) |
| 102 | E07US004 | Écran projeté plein écran |
| 103 | E07US005 | Vue tableaux/arbres live |
| 104 | E05US019 | Enregistrer une séquence comme modèle |

## J4 — Confort, richesse & robustesse
| Seq | US | Titre |
|---|---|---|
| 105 | E02US007 | Importer un fichier inscript'arc (parsing + mapping) |
| 106 | E02US008 | Rapport d'import (rejets, doublons) |
| 107 | E01US011 | Presets de barèmes multi-phases |
| 108 | E01US012 | Gérer plusieurs gabarits |
| 109 | E03US010 | Générer / éditer le déroulé horaire |
| 110 | E09US007 | Déroulé horaire imprimable |
| 111 | E05US016 | Routing repêchage-réintégration (WA) |
| 112 | E11US006 | Restauration depuis une sauvegarde |
| 113 | E11US007 | Drain de la file d'écriture à l'arrêt |
| 114 | E10US006 | Modifier le mot de passe admin |

---

*Séquence indicative au sein d'un jalon (ajustable selon dépendances) ; les jalons se font dans l'ordre. Total : 114 US.*
