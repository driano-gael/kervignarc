# Glossaire métier & technique — Kervignarc

Référence de l'**ubiquitous language** (ADR-0006). **Termes métier en français**, **termes techniques en anglais**. La colonne « Identifiant code » donne le nom à employer dans le code (classes/entités).

## Termes métier (français)

| Terme | Identifiant code | Définition |
|---|---|---|
| **Tournoi** | `Tournoi` | Événement complet : configuration, inscrits, phases, résultats. |
| **Club** | `Club` | Structure d'appartenance d'un archer. |
| **Archer** | `Archer` | Participant (ex-`Player` du prototype). |
| **Catégorie** | `Categorie` | Classe de compétition **nommée**, définie par une règle d'éligibilité (arme, **une ou plusieurs** tranches d'âge, sexe), déterminant blason par défaut et cloisonnement. Pas un triplet : la FFTA regroupe des tranches (arc nu « U18 » = U15+U18). |
| **Blason** | `Blason` | Cible en carton visée par l'archer. Porte une **taille** (fraction de place sur la cible), une **capacité** et ses **zones** (valeurs de score admises — un triple 40 n'a pas les zones 5→1). |
| **Cible** | `Cible` | Support physique numéroté ; capacité **libre (≥ 1)** selon les blasons — usuellement 1, 2 ou 4, mais 3 existe (triples verticaux). |
| **Position** | `position` | Emplacement sur une cible : A, B, C, D (ex-`lettre` du prototype). |
| **Gabarit de salle** | `GabaritSalle` | Plan de cibles réutilisable : nombre de cibles et **plafond** d'archers par cible (défaut 4) d'où découlent les positions. |
| **Départ** | `Depart` | Une participation d'un archer ; un archer peut avoir plusieurs départs (base de la facturation). |
| **Flèche** | `Fleche` | Un tir unique ; valeur 0-10, X (centre), M (manqué). |
| **Volée** | `Volee` | Groupe de flèches tirées d'affilée (ex. 3 flèches). |
| **Série** | `Serie` | Ensemble de volées validé d'un bloc. |
| **Score** | `score` | Total de points (cumul en qualif, points de set en duel). |
| **Barème** | `Bareme` | Règle de calcul/victoire d'une phase (cumul, sets, shoot-off, BSO). |
| **Qualification** | phase type `qualification` | Phase de classement par cumul de volées. |
| **Barrage** | phase type `barrage` | Tir de départage (souvent 1 flèche) pour les égalités décisives. |
| **Duel / Match** | `Match` | Affrontement individuel entre deux archers. |
| **Set** | `Set` | Manche d'un duel ; le vainqueur marque des points de set. |
| **Shoot-off** | — | Tir de barrage (1 flèche) ; départage au plus près du centre. |
| **Big Shoot Off (BSO)** | phase type `big_shoot_off` | Grande finale au format tir décisif. |
| **Tableau** | `Tableau` | Arbre de matchs à élimination. |
| **Tableau principal** | — | Arbre menant au titre. |
| **Tableau de placement** | — | Sous-arbre classant une plage de rangs (ex. 17-24). |
| **Lucky Loser** | — | Dans ce projet : **tableau de classement/consolation** (pas un repêchage par défaut — cf. `moteur-placement-lucky-loser.md`). |
| **Repêchage** | routing `repechage` | Réintégration de perdants dans le principal (mode World Archery, optionnel). |
| **Exempt / Bye** | `bye` | Archer qualifié d'office pour un tour (sans adversaire). |
| **Tête de série** | `seed` | Rang d'un archer issu de la qualification, servant à l'ensemencement. |
| **Seeding** | `seeding` | Placement des archers dans l'arbre (serpent). |
| **Phase** | `Phase` | Étape du tournoi (qualif, barrage, tableau, placement, finale, BSO…). |
| **Barème** | `BaremeQualification` | Comment se tire et se compte une phase. En qualification : N volées de M flèches, au cumul (`config.scoring`). |
| **Grain de validation** | `GrainValidation` | **Quand le scoreur valide** une phase : *fin de série* · *fin de duel* · *toutes les N volées* (`config.validation`, `D-11`). Politique de phase, réglée à la configuration — pas un réglage global. |
| **Séquence** | `Sequence` | Enchaînement ordonné de phases définissant un format. |
| **Placement** | `Placement` | Affectation d'un archer à cible + position + départ. |
| **Plan de cibles** | — | Vue « qui tire où » pour une phase/tour. |
| **Déroulé** | — | Grille horaire de la journée. |
| **Classement** | `Classement` | Ordre des archers ; peut être intégral (1→N) ou partiel. |
| **Rang** | `rang` | Position finale d'un archer. |
| **Feuille de marque** | — | Document de scores par cible/archer. |

## Rôles

| Rôle | Identifiant | Définition |
|---|---|---|
| **Administrateur** | `admin` | Accès total : configuration, moteur, exports, corrections. |
| **Scoreur** | `scoreur` | Saisit et valide les scores ; rattaché à une ou plusieurs cibles par code. |
| **Public** | `public` | Consultation en lecture seule. |

## Termes techniques (anglais)

| Terme | Définition |
|---|---|
| **Port / Adapter** | Interface du domaine (port) et son implémentation d'infrastructure (adapter) — architecture hexagonale (ADR-0003). |
| **Composition root** | Point unique de câblage explicite des dépendances (`bootstrap/`). |
| **Policy** | Stratégie injectable d'une phase : `routing`, `scoring`, `validation`, `seeding`, `byes`, `tiebreak`, `depth` (ADR-0004 ; `validation` = `D-11`). |
| **Repository** | Port d'accès aux données d'un agrégat. |
| **DTO** | Objet de transport à la frontière API (Pydantic), distinct du domaine. |
| **File d'écriture (write queue)** | File des commandes d'écriture consommée par un **writer unique** (ADR-0005). |
| **WebSocket** | Canal de diffusion temps réel. |
| **Migration** | Évolution de schéma versionnée (Alembic). |
| **AuditLog** | Journal des actions sensibles (corrections, validations, forfaits). |

> Toute nouvelle notion métier doit être ajoutée ici avant d'apparaître dans le code, l'API ou l'UI.
