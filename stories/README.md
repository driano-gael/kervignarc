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
| 32 | E02US009 | Inscrire un archer sur des départs |
| 33 | **E00US014** | **Outiller les tests du front** *([DETTE-005](../docs/dette.md) — avant E08US001)* |
| 34 | E08US001 | Calculer le montant dû |
| 35 | E03US001 | Placement automatique & plan de cibles |
| 36 | E03US004 | Ajuster le placement (glisser-déposer) |
| 37 | **E10US003** | **Scoreurs du tournoi : définition & session** — *réécrite (`D-12`, `D-13`)* |
| 38 | **E09US008** | **Imprimer les QR de cible et les codes scoreurs** *(`D-07`)* |
| 39 | **E04US001** | **Rattacher une tablette à sa cible (QR + jeton de poste)** — *réécrite (`D-06`, `D-07`)* |
| 40 | **E10US007** | **Poste de cible : saisir sans s'identifier** — *réécrite (`D-13`)* |
| 41 | E04US002 | Saisie de qualification en temps réel |
| 42 | E04US009 | Diffusion live & résilience réseau |
| 43 | **E12US001** | **Superviser les postes de saisie** *(`D-06`, `D-21`)* |
| 44 | E06US001 | Classement de qualification (cumul, départage, par catégorie) |
| 45 | E07US001 | Vues publiques : classements, plans de cibles et live |
| 46 | **E07US006** | **« C'est moi » : ouvrir l'appli sur ma journée** *(`D-09`)* |
| 47 | E10US005 | Journal d'audit métier |
| 48 | **E12US007** | **Alerter par calcul d'impact** *(`D-15`, `D-16`)* |
| 49 | E08US002 | Suivi des paiements (marquer, vue par archer, vue par club) |
| 50 | **E12US005** | **Afficher la complétude du tournoi** *(`D-17`, `D-18`)* |
| 51 | **E12US006** | **Rechercher un archer depuis n'importe où** *(`D-10`)* |
| 52 | E02US005 | Détecter et fusionner les doublons |
| 53 | E02US006 | Contrôler les quotas |
| 54 | E09US001 | Socle PDF & feuille de marque |
| 55 | E09US003 | Listes imprimables (placement, club & paiement) |
| 56 | E11US001 | Release, base et mise en réseau |
| 57 | E11US003 | Sauvegarde & archive |

> **Ordre contraint, pas cosmétique** : `E02US004` (les départs) précède `E02US009` (l'inscription sur ces
> départs) ; `E09US008` (les QR) précède `E04US001` (le rattachement qui les scanne) ; `E12US001`
> (supervision) suit `E04US001` (il n'y a rien à superviser avant qu'un poste existe) ; `E00US014` (tests
> du front) précède `E08US001` — c'est lui qui calcule **de l'argent** à partir d'une conversion que rien ne
> couvre aujourd'hui ([DETTE-005](../docs/dette.md), [ADR-0012](../docs/adr/0012-argent-en-centimes-entiers.md)).

## J2 — Duels simples + **bascule de tour**
| Seq | US | Titre |
|---|---|---|
| 58 | E05US001 | Séquence de phases (modèle, édition, cohérence) |
| 59 | E05US003 | Politiques injectables & assemblage |
| 60 | E05US005 | Arbre d'élimination directe |
| 61 | E03US006 | Contrainte ≥ 2 clubs par cible |
| 62 | E03US009 | Placer les duellistes côte à côte *(cibles attribuées **aux matchs**, `D-08`)* |
| 63 | E04US013 | Saisie en duels |
| 64 | E04US015 | Gérer abandon / disqualification |
| 65 | **E12US004** | **Tracer un forfait** *(`D-24`)* |
| 66 | E12US008 | Cycle de vie d'un départ (créneau) |
| 67 | E08US005 | Rembourser une inscription payée annulée |
| 68 | **E12US002** | **Lancer un tour (feu vert + lancement)** *(`D-22`, `D-23`, `D-25`)* |
| 69 | **E04US018** | **Afficher la prochaine cible après validation** *(`D-09`, canal 1)* |
| 70 | **E07US008** | **Vue publique des affectations du prochain tour** *(`D-09`, canal 2)* |
| 71 | E06US003 | Barrage de tir pour places décisives |
| 72 | E06US004 | Podium des duels & agrégation des rangs |

> **C'est ici que le produit gagne ou perd.** `E12US002` n'a de sens que si `E03US009` l'a précédé (la cible
> du match suivant est connue **d'avance**, `D-08`) et que `E04US018` / `E07US008` le suivent : **lancer sans
> prévenir les 4 canaux, c'est le temps mort d'avant.** `E12US008` (cycle de vie d'un départ) et `E08US005`
> (remboursement) partagent le même déclencheur — la suppression d'un départ à inscriptions confirmée
> ([ADR-0018](../docs/adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md)) — d'où leur position
> côte à côte, près d'`E12US004` (même famille : un aléa qui ne bloque pas le tour, mais se documente).

## J3 — Placement intégral 1→N + écran de salle & identité
| Seq | US | Titre |
|---|---|---|
| 73 | E05US010 | Placement intégral 1→N |
| 74 | E05US015 | Big Shoot Off |
| 75 | E05US018 | Oracle 120 (rejeu + comparaison) |
| 76 | E06US006 | Classement intégral 1→N & profondeur configurable |
| 77 | E03US007 | Contrainte séparation catégorie/blason |
| 78 | E09US005 | Classements PDF (par catégorie, intégral 1→N) |
| 79 | **E00US013** | **Factoriser les briques d'UI partagées du front** *([DETTE-004](../docs/dette.md))* |
| 80 | **E01US016** | **Définir l'identité visuelle du tournoi** *(`D-27`, `D-28`, `DV-06`)* |
| 81 | **E07US004** | **Écran de salle : déroulé automatique et pilotage admin** — *réécrite (`D-21`)* |
| 82 | E07US005 | Vue tableaux/arbres live |
| 83 | E05US019 | Enregistrer une séquence comme modèle |

> `E01US016` précède `E07US004` : **l'identité n'a pas de surface avant l'écran de salle** — c'est lui, avec
> l'appli publique, qui la porte (`D-27`). L'admin et la saisie **restent l'outil**, neutres.
> `E00US013` les précède tous deux : c'est là que la duplication d'UI ([DETTE-004](../docs/dette.md))
> **commence à coûter** — un token de couleur appliqué en 8 endroits, c'est 8 occasions d'en oublier un.

## J4 — Confort, richesse & robustesse
| Seq | US | Titre |
|---|---|---|
| 84 | E02US007 | Importer un fichier inscript'arc (parsing + rapport) |
| 85 | E01US011 | Presets de barèmes multi-phases |
| 86 | E01US012 | Gérer plusieurs gabarits |
| 87 | E03US010 | Générer / éditer le déroulé horaire |
| 88 | E09US007 | Déroulé horaire imprimable |
| 89 | E05US016 | Routing repêchage-réintégration (WA) |
| 90 | E11US006 | Restauration & arrêt propre |
| 91 | E10US006 | Modifier le mot de passe admin |

---

## US caduques (hors séquence)
| US | Titre | Motif |
|---|---|---|
| **E10US004** | ~~Habiliter un scoreur sur plusieurs cibles~~ | **Sans objet depuis `D-12`/`D-13`** : le scoreur **n'est habilité sur aucune cible** — il est **itinérant** et choisit celle dont il valide les scores. Il n'y a plus rien à habiliter. Conservée dans `E10-acces-roles.md` comme trace. |

---

*Séquence indicative au sein d'un jalon (ajustable selon dépendances) ; les jalons se font dans l'ordre.*
***Total : 91 US actives*** *(+ 1 caduque). Dernière révision : 15/07/2026 — entretien de conception
du 14/07 (CDC UX v0.2, CDC design v0.3), puis deux US de résorption issues des revues :
`E00US013` ([DETTE-004](../docs/dette.md), revue d'E01US015) et `E00US014`
([DETTE-005](../docs/dette.md), revue d'E01US010). Maille révisée le 17/07/2026 (regroupement au grain
capacité ÷~1,5, backlog non livré uniquement ; les US livrées et E10US004 caduque restent inchangées).
Trois US manquantes depuis leur création du 16/07 (staleness préexistante à la maille) ont été
réintégrées le 17/07 : `E02US009`, `E08US005`, `E12US008`.*
