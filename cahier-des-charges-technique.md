# Cahier des charges technique — Kervignarc

**Solution logicielle de gestion de tournoi de tir à l'arc en salle (18 m)**

| | |
|---|---|
| **Version** | 0.1 (technique) |
| **Date** | 08/07/2026 |
| **Statut** | À valider par le client |
| **Documents liés** | `cahier-des-charges.md` (fonctionnel v0.2), `charge.md`, `Tableaux.xlsx` |
| **Périmètre** | Architecture technique découlant du CDC fonctionnel |

---

## 1. Objet et rappel du contexte

Ce document décrit l'**architecture technique** de la solution dont le besoin fonctionnel est spécifié dans `cahier-des-charges.md`. Il traduit les exigences (moteur de phases configurable, saisie temps réel sur ~30 tablettes, réseau local sans internet, classement intégral 1→N) en choix technologiques, modèle de données, API, déploiement et contraintes non-fonctionnelles.

### 1.1 Décisions structurantes actées (cadrage du 08/07/2026)

| Sujet | Décision |
|---|---|
| **Backend** | Python **FastAPI**, en réutilisant/étendant le prototype de domaine existant (`blason.py`, `player.py`…) |
| **Frontend** | **React** (SPA), servi par le backend |
| **Base de données** | **SQLite** (fichier local) |
| **Architecture réseau** | **Serveur-autoritaire sur LAN** (pas d'offline-first ; tolérance aux brèves coupures wifi) |
| **Clients** | **BYOD** — navigateur web sur tablettes/smartphones variés (~30) |
| **Serveur** | **PC portable** de l'organisateur, sur un **réseau wifi dédié** (routeur/point d'accès) |
| **Livrable** | **Outil interne mono-club** (une instance, pas de multi-tenant) |
| **Lancement** | **Exécutable auto-contenu** (double-clic), sans compétence technique |
| **Accès** | Consultation publique ouverte ; **scoreur par code de cible** (peut valider **plusieurs cibles**) ; **admin protégé** |
| **Sauvegarde** | **Auto périodique** du fichier SQLite + **export en fin** de tournoi |

---

## 2. Vue d'architecture générale

```
        Gymnase — réseau wifi local dédié (sans internet)
   ┌──────────────────────────────────────────────────────────┐
   │                                                            │
   │   [Routeur / point d'accès wifi dédié]                     │
   │        │                                                   │
   │        ├──── PC portable (serveur)                         │
   │        │        └─ Exécutable Kervignarc                   │
   │        │             ├─ FastAPI (API REST + WebSocket)     │
   │        │             ├─ Sert le build React (statique)     │
   │        │             ├─ Moteur de phases (domaine Python)  │
   │        │             └─ SQLite (fichier local + backups)   │
   │        │                                                   │
   │        ├──── ~30 tablettes/smartphones BYOD (scoreurs)     │
   │        │        └─ Navigateur → SPA React                  │
   │        │                                                   │
   │        ├──── Écran projeté (classements/tableaux live)     │
   │        │                                                   │
   │        └──── Public (mobiles) — consultation               │
   │                                                            │
   └──────────────────────────────────────────────────────────┘
```

- **Un seul processus serveur** sur le portable : FastAPI expose l'API et sert les fichiers statiques du front React (build de production).
- Les clients (tablettes, écran, public) accèdent à une **URL locale** (ex. `http://<ip-portable>:<port>` ou nom mDNS `kervignarc.local`).
- Le **temps réel** (scores, tableaux, classements) est diffusé via **WebSocket**.

---

## 3. Choix technologiques (stack)

| Couche | Technologie | Justification |
|---|---|---|
| Domaine métier | **Python 3.11+** | Réutilise le prototype (`Blason`, `Player`), langage maîtrisé pour la maintenance |
| API / serveur | **FastAPI** + **Uvicorn** | Async, WebSocket natif, typage Pydantic, sert aussi les statiques React |
| Persistance | **SQLite** + **SQLAlchemy** (ORM) | Zéro administration, sauvegarde = copie de fichier, adapté au mono-club local |
| Migrations | **Alembic** | Évolution de schéma maîtrisée entre versions |
| Frontend | **React** + **TypeScript** + **Vite** | SPA riche pour le temps réel et le glisser-déposer du placement |
| Temps réel | **WebSocket** (FastAPI) | Diffusion des mises à jour aux clients connectés |
| Génération PDF | Bibliothèque Python (ex. **WeasyPrint** ou **ReportLab**) | Déroulé, plans de cibles, feuilles de marque, classements |
| Import XLS | **openpyxl** / **pandas** | Import « inscript'arc » |
| Packaging | **PyInstaller** (exécutable) | Livrable double-clic auto-contenu (Python + front buildé embarqués) |

> Choix de bibliothèques indicatifs, à confirmer au démarrage technique.

---

## 4. Architecture applicative

Découpage en couches, le domaine métier restant indépendant du framework web (le prototype existant y est intégré et étendu).

```
kervignarc/
├── domain/            # logique métier pure (réutilise/étend le prototype)
│   ├── blason.py      # Blason{size, capacity, name}  (existant)
│   ├── player.py      # Player/Archer{name, blason, lettre, idCible, scores…} (existant)
│   ├── target.py      # Cible{capacité 1/2/4, positions A/B/C/D}
│   ├── placement.py   # algo de placement (contraintes capacité/club/blason)
│   ├── phase/         # MOTEUR DE PHASES
│   │   ├── engine.py       # séquence de phases, orchestration
│   │   ├── phase_types.py  # qualif, barrage, tableau, repêchage, placement, finale, BSO
│   │   ├── sourcing.py     # peuplement (rangs N→M, gagnants, perdants d'un tour)
│   │   ├── bracket.py      # génération d'arbre, seeding, progression
│   │   └── policies/       # POLITIQUES INJECTABLES (configurables par phase)
│   │       ├── routing.py    # route(perdant, tour, contexte) → destination
│   │       │                 #   (cascade de placement | repêchage-réintégration)
│   │       ├── scoring.py    # presets de barèmes (cumul, sets, shoot-off, BSO)
│   │       ├── seeding.py    # seeding serpent, arrondi 2^k
│   │       ├── byes.py       # attribution des exempts (défaut: mieux classés)
│   │       ├── tiebreak.py   # départage (nb de 10/9, shoot-off plus près du centre)
│   │       └── depth.py      # profondeur de classement (1→N | top N + regroupement)
│   └── ranking.py     # agrégation du classement final (intégral ou tronqué)
├── db/                # SQLAlchemy models, repositories, migrations Alembic
├── api/               # FastAPI: routers REST + endpoints WebSocket + auth
├── services/          # exports PDF/XLS, sauvegarde, import inscrits
├── web/               # build React embarqué (servi en statique)
└── main.py            # point d'entrée (packagé en exécutable)
```

### 4.1 Moteur de phases (composant central)
- Un **tournoi** = liste ordonnée de **phases**. Chaque phase est décrite par une **configuration** (type, source de participants, structure) et un **jeu de politiques injectables**.
- Le moteur **résout** la séquence : il calcule les tours, matchs, seeding et byes, puis expose les **flux de sortie** (classement, gagnants, perdants) consommables par les phases suivantes.
- Les **règles de peuplement** (`sourcing.py`) formalisent « rangs 17→24 », « perdants du tour N », etc. — c'est le point technique le plus sensible (voir §12, risque R1).
- Chaque type de phase implémente une **interface commune** (peupler → dérouler → produire sorties) pour rester extensible.

### 4.2 Politiques injectables (abstraction issue de la formalisation du placement)

> Cf. `moteur-placement-lucky-loser.md` §7. Plutôt que de câbler un format de tableau, le moteur compose des **politiques** paramétrables. Un « format » (placement intégral, élimination directe, top N, tableau unique…) n'est qu'un **assemblage de ces politiques**. C'est ce qui rend le constructeur de tableau libre du CDC fonctionnel réalisable sans multiplier le code.

| Politique | Rôle | Variantes / décisions |
|---|---|---|
| **Routage** (`routing.py`) | `route(perdant, tour, contexte) → destination` : où va le perdant d'un match | **Cascade de placement** (défaut, personne éliminé, plage /2) OU **repêchage-réintégration** (World Archery) OU **élimination sèche** (sort du tournoi). *(Q1)* |
| **Barème** (`scoring.py`) | Comment se calcule/gagne un match ou un cumul | Presets FFTA/WA **modifiables** : cumul de volées, sets 4 pts, finales 6 pts, shoot-off, Big Shoot Off. *(Q3)* |
| **Seeding** (`seeding.py`) | Composition de l'arbre | Arrondi à `2^k`, **seeding serpent** standard. |
| **Byes** (`byes.py`) | Attribution des exempts quand l'effectif ≠ `2^k` | Défaut : **aux mieux classés** de la plage ; universel, calculé pour tout effectif. *(Q4, Q5)* |
| **Départage** (`tiebreak.py`) | Résolution des égalités | Qualif : **nb de 10 puis de 9** ; match nul : **shoot-off 1 flèche, plus près du centre** ; barrage de tir pour places décisives. Modifiable. *(Q3)* |
| **Profondeur** (`depth.py`) | Jusqu'où classer | **1→N** (défaut) OU **top N + regroupement** du reliquat, par tournoi. *(Q2)* |

- Une **phase de tableau** reçoit donc : `{sourcing, routing, scoring, seeding, byes, tiebreak, depth}`. Le format « placement intégral 120 » du classeur = `routing=cascade, depth=1→N, byes=mieux classés, seeding=serpent`.
- Les politiques sont **stockées dans la config JSON de la phase** (cf. §5) et **réutilisables entre formats et tournois** (modèles de séquence, EF-3.6 fonctionnel).
- **Testabilité** : chaque politique est unitairement testable ; l'assemblage « placement intégral » est validé en rejouant le tournoi 120 de `Tableaux.xlsx` (§13).

---

## 5. Modèle de données (SQLite)

Entités principales (schéma logique — détail des colonnes à préciser en conception détaillée) :

| Entité | Rôle | Champs clés |
|---|---|---|
| `Tournament` | Le tournoi | nom, date, lieu, type officiel/non, statut |
| `Club` | Référentiel clubs | nom |
| `Archer` | Inscrit | nom, prénom, club_id, catégorie_id |
| `Category` | Catégorie | libellé, blason par défaut |
| `Blason` | Blason | name, size (fraction), capacity |
| `Departure` | Départ d'un archer | archer_id, n° départ, tarif, montant dû, payé (bool) |
| `TargetTemplate` | Gabarit de salle | nb cibles, capacités, positions |
| `Target` | Cible d'un tournoi | index, capacité, positions A/B/C/D |
| `Placement` | Affectation | archer_id, target_id, position, phase_id/tour |
| `Phase` | Phase de la séquence | tournament_id, ordre, type, config (JSON incl. **politiques** : routage/barème/seeding/byes/départage/profondeur — cf. §4.2) |
| `Match` | Match/duel | phase_id, n° (M1…), archer_A, archer_B, tour |
| `SetScore` / `Volley` | Volées/sets saisis | match_id ou qualif_id, valeurs, validé (bool), auteur, horodatage |
| `Ranking` | Classement produit | phase_id, archer_id, rang, contexte (qualif/final 1→N) |
| `User` / `Session` | Accès | rôle (admin/scoreur), code de cible(s), jeton |
| `AuditLog` | Traçabilité | corrections de score (qui, quand, ancienne/nouvelle valeur) |

- La **configuration d'une phase** est stockée en **JSON** (souplesse du moteur configurable) tout en gardant les entités relationnelles pour les données volumineuses (matchs, scores).
- Contrainte d'intégrité : un score **validé** est verrouillé ; toute modification passe par `AuditLog` (RG-5 fonctionnel).

---

## 6. API et communication temps réel

### 6.1 REST (FastAPI)
Regroupée par domaines : `tournaments`, `archers`, `imports`, `phases`, `placements`, `targets`, `matches`, `scores`, `rankings`, `payments`, `exports`, `auth`. Contrats typés via Pydantic ; documentation OpenAPI auto-générée (utile en dev).

### 6.2 WebSocket
- Un canal de diffusion par tournoi ; les clients s'abonnent aux **sujets** utiles (scores d'une cible, tableau, classement live).
- À chaque validation de score / progression de match, le serveur **pousse** l'événement aux abonnés (écran projeté, mobiles, autres scoreurs).
- Le serveur reste **autoritaire** : le client envoie une intention (saisie), le serveur valide, persiste, puis diffuse l'état à jour.

### 6.3 Tolérance aux coupures wifi (sans offline-first)
- Le front met en **file d'attente locale** les saisies non confirmées et **rejoue** à la reconnexion (idempotence côté API via un identifiant de saisie).
- Reconnexion WebSocket automatique + **resynchronisation** de l'état à la reprise.
- Objectif : encaisser des coupures **brèves**, sans viser un fonctionnement prolongé hors réseau.

---

## 7. Front-end React

- **SPA** en TypeScript (Vite), buildée et **embarquée** dans l'exécutable, servie par FastAPI.
- Écrans principaux : administration/configuration, moteur de phases (éditeur de séquence), placement (**glisser-déposer**), saisie scoreur (tablette), tableaux/arbres, classements, écran projeté (mode plein écran), consultation publique.
- **Ergonomie tactile** prioritaire sur l'écran de saisie (gros boutons, pavé de points, peu de clics).
- Client WebSocket pour le live ; **service worker léger** (PWA) pour le cache des assets et la file d'attente des saisies (tolérance coupures).
- Détection de perte de connexion avec indicateur visible pour le scoreur.

---

## 8. Déploiement et exécution

### 8.1 Packaging
- **Exécutable unique** (PyInstaller) intégrant : runtime Python, FastAPI/Uvicorn, moteur de domaine, build React statique.
- Au premier lancement : création du fichier SQLite s'il n'existe pas, port fixe, ouverture éventuelle du navigateur sur l'écran d'administration.

### 8.2 Réseau
- **Routeur / point d'accès wifi dédié** (recommandé : routeur de voyage) auquel se connectent le portable-serveur et les clients.
- Accès via IP locale du portable ou nom **mDNS** (`kervignarc.local`) pour éviter de retenir l'IP.
- Dimensionné pour **~30 clients simultanés** ; le portable-serveur n'assure PAS le hotspot (fiabilité), il se connecte au routeur dédié.

### 8.3 Procédure day-of (cible)
1. Allumer le routeur wifi dédié.
2. Connecter le portable, lancer l'exécutable (double-clic).
3. Les scoreurs/écrans/public rejoignent le wifi et ouvrent l'URL locale.

---

## 9. Sécurité et gestion des accès

- Périmètre **réseau local fermé** (pas d'exposition internet) → modèle d'accès **léger** et adapté au terrain.
- **Consultation publique** : ouverte en lecture seule.
- **Scoreur** : saisie/validation via **code de cible** ; un scoreur peut être habilité sur **plusieurs cibles** (sélection multiple). Jeton de session simple.
- **Administrateur** : accès protégé (mot de passe) pour configuration, moteur de phases, exports, corrections.
- **Traçabilité** : toute correction d'un score validé est journalisée (`AuditLog`).
- Communications en **HTTP local** (HTTPS optionnel via certificat auto-signé — à arbitrer, cf. Q ouverte).

---

## 10. Sauvegarde, exports et cycle de vie des données

- **Sauvegarde automatique périodique** du fichier SQLite (copie horodatée dans un dossier local) pendant l'événement → protège contre un plantage du portable.
- **Export / archive en fin de tournoi** (fichier SQLite + exports documentaires).
- **Exports documentaires** (via services PDF/XLS) : déroulé horaire, plans de cibles, feuilles de marque, tableaux, classements par catégorie, classement intégral 1→N, listes club & paiement.
- Restauration = relancer l'exécutable en pointant sur une sauvegarde.

---

## 11. Performance et dimensionnement

| Aspect | Cible |
|---|---|
| Clients simultanés | ~30 tablettes + écran + public (référence : tournoi 120 archers / 30 cibles) |
| Latence live | Mise à jour perçue « quasi immédiate » (< 1–2 s) après validation |
| Charge serveur | Faible : SQLite + FastAPI async suffisent pour ce volume sur un portable récent |
| Point de vigilance | Capacité du **wifi** (30 clients) > capacité applicative → routeur dédié dimensionné |

---

## 12. Contraintes non-fonctionnelles techniques

- **Compatibilité BYOD** : le front doit fonctionner sur navigateurs mobiles récents variés (Chrome/Safari Android & iOS). Prévoir les **limites PWA iOS/Safari** (stockage, service worker) → la file d'attente locale reste volontairement minimale.
- **Résilience** : reconnexion WebSocket et resynchronisation transparentes ; aucune perte de saisie validée.
- **Cohérence du moteur** : recalcul fiable de la progression après correction/forfait en cours d'épreuve.
- **Maintenabilité** : domaine métier découplé du web ; couverture de tests sur le moteur de phases (voir §13).
- **Portabilité** : cible Windows (portable de l'organisateur) ; exécutable Windows en priorité.

---

## 13. Environnement de développement, tests et qualité

- **Dépôt** unique (mono-repo) : `domain/`, `db/`, `api/`, `services/`, `web/`.
- **Tests** : priorité sur le **moteur de phases** et le **placement** (tests unitaires sur cas réels tirés de `Tableaux.xlsx`, ex. reconstruire le tournoi 120 et vérifier arbre, Lucky Loser, classement 1→N).
- **CI** légère (lint + tests) adaptée à une petite équipe.
- **Versionnement** de schéma via Alembic ; migrations testées.
- Le classeur `Tableaux.xlsx` sert de **jeu de données de référence** pour la validation.

---

## 14. Hypothèses et risques techniques

| # | Risque / hypothèse | Mitigation |
|---|---|---|
| R1 | **Complexité du moteur de phases** (Lucky Loser, placement 1→N) — cœur du produit | Formaliser 2-3 flux réels depuis `Tableaux.xlsx` avant dev ; tests de non-régression sur ces cas |
| R2 | **Fiabilité wifi** pour 30 clients | Routeur dédié dimensionné ; file d'attente + reconnexion côté front |
| R3 | **Limites PWA iOS/Safari** (BYOD) | Tolérance coupures volontairement minimale ; tests multi-navigateurs |
| R4 | **Packaging exécutable** (PyInstaller + front + PDF) | Prototype de build tôt ; valider WeasyPrint/dépendances natives dans le binaire |
| R5 | **Panne du portable-serveur** | Sauvegarde auto périodique + procédure de restauration |
| R6 | **Format d'import inscript'arc** inconnu | Obtenir un fichier d'exemple avant de figer le parseur |

---

## 15. Questions ouvertes restantes (techniques)

| # | Sujet | À décider |
|---|---|---|
| QT1 | **Format exact du fichier inscript'arc** | Exemple XLS + colonnes (bloque le parseur d'import) |
| QT2 | **HTTPS local** (certificat auto-signé) ou HTTP simple | Selon exigence navigateurs / confort |
| QT3 | **Bibliothèque PDF** (WeasyPrint vs ReportLab) | Selon rendu attendu des documents |
| QT4 | **Nom d'accès** : IP fixe vs mDNS `kervignarc.local` | Confort terrain |
| QT5 | **OS cible du build** : Windows seul ou aussi macOS/Linux | Parc de l'organisateur |
| QT6 | **Volumétrie plafond** au-delà de 120 archers | Dimensionnement / tests de charge |
| QT7 | **Détail des règles** de barrage/départage et de peuplement Lucky Loser | Conception détaillée du moteur (R1) |

---

*Document produit à partir du CDC fonctionnel et des décisions de cadrage du 08/07/2026. À relire et amender avant chiffrage et développement.*
