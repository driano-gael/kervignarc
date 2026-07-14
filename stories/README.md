# Backlog — User Stories (ordonné par montée en valeur)

Découpage fin des EPICs en user stories **à destination d'un développeur** (maille : un comportement testable, ~1-3 j, INVEST).

## Conventions
- **ID** : `ExxUSyyy` — `Exx` = code epic, `USyyy` = n° dans l'epic. L'ID rattache la story à son epic ; il **ne dicte pas l'ordre de réalisation**.
- **Ordre de réalisation** : la **séquence** ci-dessous, en **jalons de valeur** — on privilégie la montée en valeur, pas l'ordre des epics.
- Détail de chaque US : `stories/Exx-slug.md`. Format : *En tant que… je veux… afin de…* + **CA** (critères d'acceptation) + **Notes** (dev) + **Dépend de**.
- **Une branche par US** : `<type>/<ExxUSyyy>-<slug>` (ex. `feat/e04us003-saisie-fleches`), `type` selon le périmètre (feat/fix/refactor/test/docs/chore). PR + revue + CI verte → merge → suppression de la branche. Détail : `guide-architecture.md` §11.

> ⚠️ **Révisé le 14/07/2026** — entretien de conception, [`cahier-des-charges-ux.md`](../cahier-des-charges-ux.md) (registre `D-01`→`D-28`) et [`cahier-des-charges-design.md`](../cahier-des-charges-design.md) (registre `DV-01`→`DV-08`).
> **3 US réécrites** (E04US001, E10US003, E10US007 — leur intitulé v0.1 était contredit), **1 caduque**
> (E10US004), **12 créées** dont l'**EPIC-12** (pilotage du jour J), qui **porte la valeur du produit** et
> qu'aucun EPIC ne couvrait. Détail des impacts : [CDC UX §14](../cahier-des-charges-ux.md).

## Jalons de valeur
| Jalon | Valeur livrée |
|---|---|
| **J0** | Walking skeleton : l'architecture tourne bout-en-bout |
| **J1** | Gérer un **tournoi de qualification complet** (premier usage réel) |
| **J2** | **Duels simples** : élimination directe → podium — **et la bascule de tour**, qui porte la valeur (`D-25`) |
| **J3** | **Placement intégral 1→N** (format du classeur 120) + écran de salle & identité |
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
| 19 | E01US013 | Catégorie : éligibilité sur plusieurs tranches d'âge |
| 20 | E01US005 | Gérer les blasons (taille/fraction + capacité) |
| 21 | E01US014 | Blason : valeurs de score admises |
| 22 | E01US006 | Associer catégorie ↔ blason |
| 23 | E01US007 | Définir un gabarit de salle |
| 24 | E01US008 | Réutiliser / ajuster un gabarit |
| 25 | E01US009 | Définir un barème de qualification |
| 26 | **E01US015** | **Définir le grain de validation d'une phase** *(`D-11`)* |
| 27 | E01US010 | Définir le tarif par départ |
| 28 | E02US001 | Gérer le référentiel clubs |
| 29 | E02US002 | Créer un archer |
| 30 | E02US003 | Éditer / supprimer un archer |
| 31 | E02US004 | Ajouter des départs multiples |
| 32 | E08US001 | Calculer le montant dû |
| 33 | E03US001 | Modéliser cibles/positions depuis le gabarit |
| 34 | E03US002 | Placement auto : capacité + fraction de blason |
| 35 | E03US003 | Placement auto : signaler les conflits |
| 36 | E03US004 | Ajuster le placement en glisser-déposer |
| 37 | E03US005 | Empêcher un déplacement invalide |
| 38 | E03US008 | Générer le plan de cibles (qualif) |
| 39 | **E10US008** | **Définir les scoreurs du tournoi** *(`D-14`)* |
| 40 | **E10US003** | **Session scoreur par code personnel** — *réécrite (`D-12`, `D-13`)* |
| 41 | **E09US008** | **Imprimer les QR de cible et les codes scoreurs** *(`D-07`)* |
| 42 | **E04US001** | **Rattacher une tablette à sa cible (QR + jeton de poste)** — *réécrite (`D-06`, `D-07`)* |
| 43 | **E10US007** | **Poste de cible : saisir sans s'identifier** — *réécrite (`D-13`)* |
| 44 | E04US002 | Afficher la grille de saisie (4 archers) |
| 45 | **E04US017** | **Désigner et tracer le marqueur** *(`D-04`, FFTA B.6.1.1)* |
| 46 | E04US003 | Saisir les flèches d'une volée (pavé tactile) |
| 47 | E04US004 | Valider les valeurs autorisées (0-10 / M / X) |
| 48 | E04US005 | Enregistrer une volée via la file d'écriture |
| 49 | E04US006 | Éditer une volée non validée |
| 50 | E04US007 | Verrouiller une série validée |
| 51 | E04US008 | Cumuler le score sur les volées |
| 52 | E04US009 | Diffuser la mise à jour en live |
| 53 | **E12US001** | **Superviser les postes de saisie** *(`D-06`, `D-21`)* |
| 54 | E06US001 | Classement de qualification (cumul) |
| 55 | E06US002 | Départage qualif (nb de 10 puis 9) |
| 56 | E06US008 | Classement par catégorie |
| 57 | E07US001 | Vue publique des classements |
| 58 | **E07US006** | **« C'est moi » : ouvrir l'appli sur ma journée** *(`D-09`)* |
| 59 | E07US002 | Live des vues publiques |
| 60 | E04US010 | Mettre en file hors-ligne + rejouer |
| 61 | E04US011 | Indicateur d'état de connexion |
| 62 | E04US012 | Corriger une volée validée (tracé) |
| 63 | E10US005 | Journal d'audit métier |
| 64 | **E12US007** | **Alerter par calcul d'impact** *(`D-15`, `D-16`)* |
| 65 | E08US002 | Marquer payé / non payé |
| 66 | E08US003 | Vue paiement par archer |
| 67 | E08US004 | Vue paiement par club |
| 68 | **E12US005** | **Afficher la complétude du tournoi** *(`D-17`, `D-18`)* |
| 69 | **E12US006** | **Rechercher un archer depuis n'importe où** *(`D-10`)* |
| 70 | E02US005 | Détecter et fusionner les doublons |
| 71 | E02US006 | Contrôler les quotas |
| 72 | E07US003 | Vue publique des plans de cibles |
| 73 | E09US001 | Intégrer la bibliothèque PDF |
| 74 | E09US002 | Feuille de marque |
| 75 | E09US003 | Liste de placement |
| 76 | E09US004 | Liste club & paiement |
| 77 | E11US001 | Build de release exécutable |
| 78 | E11US002 | Création SQLite au 1er lancement |
| 79 | E11US003 | Sauvegarde automatique périodique |
| 80 | E11US004 | Export / archive en fin de tournoi |
| 81 | E11US005 | Procédure & doc réseau (routeur dédié, mDNS) |

> **Ordre contraint, pas cosmétique** : `E09US008` (les QR) précède `E04US001` (le rattachement qui les
> scanne) ; `E10US008` (déclarer les scoreurs) précède `E10US003` (leur session) ; `E12US001` (supervision)
> suit `E04US001` (il n'y a rien à superviser avant qu'un poste existe).

## J2 — Duels simples + **bascule de tour**
| Seq | US | Titre |
|---|---|---|
| 82 | E05US001 | Définir le modèle de séquence de phases |
| 83 | E05US002 | Éditer une séquence (ajouter/ordonner/typer) |
| 84 | E05US003 | Interfaces de politiques injectables |
| 85 | E05US004 | Assembler les politiques d'une phase (config JSON) |
| 86 | E05US005 | Arrondi 2^k + seeding serpent |
| 87 | E05US006 | Attribution des byes (aux mieux classés) |
| 88 | E05US007 | Générer l'arbre d'élimination directe |
| 89 | E05US008 | Progression : le gagnant avance |
| 90 | E05US009 | Terminer sur un podium |
| 91 | E05US017 | Contrôles de cohérence (phase mal alimentée) |
| 92 | E03US006 | Contrainte ≥ 2 clubs par cible |
| 93 | E03US009 | Placer les duellistes côte à côte *(cibles attribuées **aux matchs**, `D-08`)* |
| 94 | E04US013 | Saisie en sets (duels) |
| 95 | E04US014 | Désigner le vainqueur d'un match |
| 96 | E04US015 | Gérer abandon / disqualification |
| 97 | **E12US004** | **Tracer un forfait** *(`D-24`)* |
| 98 | E04US016 | Déclencher un barrage/shoot-off (égalité) |
| 99 | **E12US002** | **Feu vert : voir ce qui manque avant de lancer** *(`D-23`)* |
| 100 | **E12US003** | **Lancer un tour ou un événement** — *le cœur du produit (`D-22`, `D-25`)* |
| 101 | **E04US018** | **Afficher la prochaine cible après validation** *(`D-09`, canal 1)* |
| 102 | **E07US008** | **Vue publique des affectations du prochain tour** *(`D-09`, canal 2)* |
| 103 | E06US003 | Barrage de tir pour places décisives |
| 104 | E06US004 | Podium issu des duels |
| 105 | E06US005 | Agréger les rangs de tableau |

> **C'est ici que le produit gagne ou perd.** `E12US003` n'a de sens que si `E03US009` l'a précédé (la cible
> du match suivant est connue **d'avance**, `D-08`) et que `E04US018` / `E07US008` le suivent : **lancer sans
> prévenir les 4 canaux, c'est le temps mort d'avant.**

## J3 — Placement intégral 1→N + écran de salle & identité
| Seq | US | Titre |
|---|---|---|
| 106 | E05US010 | Peuplement : rangs N→M |
| 107 | E05US011 | Peuplement : gagnants / perdants d'un tour |
| 108 | E05US012 | Routing cascade (placement intégral) |
| 109 | E05US013 | Division récursive des plages |
| 110 | E05US014 | Affectation des rangs terminaux (gagnant/perdant) |
| 111 | E05US015 | Big Shoot Off |
| 112 | E05US018 | Oracle 120 (rejeu + comparaison) |
| 113 | E06US006 | Classement intégral 1→N |
| 114 | E06US007 | Profondeur de classement configurable |
| 115 | E03US007 | Contrainte séparation catégorie/blason |
| 116 | E09US005 | Classement PDF par catégorie |
| 117 | E09US006 | Classement intégral 1→N (PDF) |
| 118 | **E00US013** | **Factoriser les briques d'UI partagées du front** *([DETTE-004](../docs/dette.md))* |
| 119 | **E01US016** | **Définir l'identité visuelle du tournoi** *(`D-27`, `D-28`, `DV-06`)* |
| 120 | **E07US004** | **Écran de salle : poste rattaché à déroulé automatique** — *réécrite (`D-21`)* |
| 121 | **E07US007** | **Piloter l'écran de salle depuis l'admin** *(`D-21`)* |
| 122 | E07US005 | Vue tableaux/arbres live |
| 123 | E05US019 | Enregistrer une séquence comme modèle |

> `E01US016` précède `E07US004` : **l'identité n'a pas de surface avant l'écran de salle** — c'est lui, avec
> l'appli publique, qui la porte (`D-27`). L'admin et la saisie **restent l'outil**, neutres.
> `E00US013` les précède tous deux : c'est là que la duplication d'UI ([DETTE-004](../docs/dette.md))
> **commence à coûter** — un token de couleur appliqué en 8 endroits, c'est 8 occasions d'en oublier un.

## J4 — Confort, richesse & robustesse
| Seq | US | Titre |
|---|---|---|
| 124 | E02US007 | Importer un fichier inscript'arc (parsing + mapping) |
| 125 | E02US008 | Rapport d'import (rejets, doublons) |
| 126 | E01US011 | Presets de barèmes multi-phases |
| 127 | E01US012 | Gérer plusieurs gabarits |
| 128 | E03US010 | Générer / éditer le déroulé horaire |
| 129 | E09US007 | Déroulé horaire imprimable |
| 130 | E05US016 | Routing repêchage-réintégration (WA) |
| 131 | E11US006 | Restauration depuis une sauvegarde |
| 132 | E11US007 | Drain de la file d'écriture à l'arrêt |
| 133 | E10US006 | Modifier le mot de passe admin |

---

## US caduques (hors séquence)
| US | Titre | Motif |
|---|---|---|
| **E10US004** | ~~Habiliter un scoreur sur plusieurs cibles~~ | **Sans objet depuis `D-12`/`D-13`** : le scoreur **n'est habilité sur aucune cible** — il est **itinérant** et choisit celle dont il valide les scores. Il n'y a plus rien à habiliter. Conservée dans `E10-acces-roles.md` comme trace. |

---

*Séquence indicative au sein d'un jalon (ajustable selon dépendances) ; les jalons se font dans l'ordre.*
***Total : 133 US actives*** *(+ 1 caduque). Dernière révision : 14/07/2026 — entretien de conception
(CDC UX v0.2, CDC design v0.3), puis ajout d'`E00US013` (résorption de [DETTE-004](../docs/dette.md),
revue d'E01US015).*
