# Glossaire métier & technique — Kervignarc

Référence de l'**ubiquitous language** (ADR-0006). **Termes métier en français**, **termes techniques en anglais**. La colonne « Identifiant code » donne le nom à employer dans le code (classes/entités).

## Termes métier (français)

| Terme | Identifiant code | Définition |
|---|---|---|
| **Tournoi** | `Tournoi` | Événement complet : configuration, inscrits, phases, résultats. |
| **Club** | `Club` | Structure d'appartenance d'un archer. Référentiel **global** (aucun `tournoi_id`), réutilisé d'une compétition à l'autre. En FFTA tout licencié a un club : `archer.club_id NULL` signifie donc **club inconnu** (pas encore saisi), **jamais** « aucun club ». Il n'existe et ne doit exister **aucun club sentinelle** (« Sans club ») — voir [ADR-0014](adr/0014-club-inconnu-plutot-que-club-sentinelle.md). |
| **Club inconnu** | `club_id is None` | État d'un archer dont le club n'est **pas encore renseigné** : une **anomalie à résorber**, pas un état légitime. Signalée à l'écran (classement) et comptée par E12US005. Deux archers au club inconnu ne sont **pas** réputés du même club : le placement (RG-3) doit traiter le cas comme *indécidable*. |
| **Archer** | `Archer` | Participant (ex-`Player` du prototype). Identifié par **nom + prénom + club** (E02US002) ; son **prénom** et sa **catégorie** sont obligatoires, son club non. |
| **Homonyme** | `cle_identite` / `homonyme_archer` | Deux archers de mêmes **nom, prénom et club**, casse et accents repliés (`domain.club.cle_nom`). Doublon **probable, pas certain** : un père et son fils le sont réellement. D'où un **signalement** (409) que l'admin confirme, jamais un refus — et aucune contrainte `UNIQUE` en base, qui rejetterait le fils. Voir [ADR-0015](adr/0015-signaler-un-doublon-plutot-que-l-interdire.md). |
| **Engagé** | `archer_engage` | Archer qui a **déjà tiré** (au moins un score), **est placé** (cible renseignée) **ou est inscrit sur au moins un départ** (E02US009). Le supprimer **efface ses flèches, son placement et ses inscriptions** : d'où un **signalement** (409) que l'admin confirme, comme l'homonyme — voir [ADR-0016](adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md). Définition **encore datée** : elle s'élargira aux duels. Ne pas confondre avec **Forfait** : un engagé qui *abandonne* ne se supprime pas. |
| **Placé** | `archer.cible is not None` | Archer occupant une cible. Placement provisoire du walking skeleton (un simple numéro) jusqu'à EPIC-03. Le supprimer libère sa place : signalé au même titre qu'engagé (`archer_engage`). |
| **Forfait** | E04US015 (qualif.) · E12US004 (duels) | Archer qui **abandonne ou est absent** : une **donnée** (datée, attribuée, motif, réversible, auditée), **pas** un trou dans le tableau ni une ligne à effacer. Il **conserve ses résultats** — c'est ce qui le distingue de la **suppression** (E02US003), qui les détruit. Confondre les deux fait perdre les flèches d'un archer qui a réellement tiré. **Aucune des deux US n'est livrée** : en attendant, un abandon ne s'enregistre pas — et surtout ne se supprime pas ([ADR-0016](adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md)). |
| **Catégorie** | `Categorie` | Classe de compétition **nommée**, définie par une règle d'éligibilité (arme, **une ou plusieurs** tranches d'âge, sexe), déterminant blason par défaut et cloisonnement. Pas un triplet : la FFTA regroupe des tranches (arc nu « U18 » = U15+U18). |
| **Tranche d'âge** | `TrancheAge` | Une des **huit** tranches FFTA (U11, U13, U15, U18, U21, S1, S2, S3), par âge atteint dans l'année civile ([référentiel §2](referentiel-ffta.md)). Vocabulaire **fermé** : une catégorie couvre une ou plusieurs tranches (`Categorie.ages`). Les regroupements de classement (arc nu « U18 », « Scratch ») sont des **libellés**, jamais des tranches. |
| **Scratch** | libellé de catégorie | Regroupement de classement **arc nu** couvrant U21, S1, S2, S3 ([référentiel §3](referentiel-ffta.md)). C'est un **libellé** de catégorie, **pas** une tranche d'âge — comme le « U18 » arc nu (= U15 + U18). |
| **Blason** | `Blason` | Cible en carton visée par l'archer. Porte une **taille** (fraction de place sur la cible), une **capacité** et ses **zones** (valeurs de score admises — un triple 40 n'a pas les zones 5→1). |
| **Zone (de score)** | `ZoneScore` | Valeur marquable sur un blason. Vocabulaire **fermé** des onze valeurs en salle : 10, 9, 8, 7, 6, 5, 4, 3, 2, 1 et **M** (manqué, hors blanc) — [référentiel §4.2](referentiel-ffta.md). Un blason en admet un sous-ensemble (`Blason.zones`), qui pilote le pavé de saisie : un **triple 40** s'arrête à 6 (§4.4). La **mouche (X)** n'en est pas une : c'est le centre du 10, un diamètre (§4.3), pas un score distinct ([ADR-0020](adr/0020-blason-zones-vocabulaire-ferme-et-defaut-sur-ensemble.md)). |
| **Cible** | `Cible` | Support physique numéroté ; capacité **libre (≥ 1)** selon les blasons — usuellement 1, 2 ou 4, mais 3 existe (triples verticaux). |
| **Position** | `position` | Emplacement sur une cible : A, B, C, D (ex-`lettre` du prototype). |
| **Gabarit de salle** | `GabaritSalle` | Plan de cibles réutilisable : nombre de cibles et **plafond** d'archers par cible (défaut 4) d'où découlent les positions. |
| **Hauteur de centre** | `Categorie.hauteur_cm` | Hauteur du sol au **centre de l'or**, en cm : 130 en général, **110** pour le blason 80 cm des U11 ([référentiel §5](referentiel-ffta.md)). Portée par la **catégorie** (pas le blason — [ADR-0022](adr/0022-hauteur-de-centre-sur-la-categorie.md)). Contrainte de placement de 1er rang : **une butte, une seule hauteur** (un U11 ne partage pas une cible avec un adulte). |
| **Départ** | `Depart` | Un **créneau** (session horaire) d'un tournoi, comme si le tournoi se jouait plusieurs fois dans la journée. Entité **du tournoi** (`tournoi_id`), **partagée** par les archers qui s'y inscrivent — pas une propriété de l'archer. Porte un numéro, un horaire (facultatif), son **tarif** (obligatoire) et son **quota** (facultatif). L'archer s'y inscrit (E02US009), base de la facturation (somme des tarifs de ses départs). Voir [ADR-0017](adr/0017-le-depart-est-un-creneau-du-tournoi.md). |
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
| **Tarif d'un départ** | `Depart.tarif_centimes` | Prix d'**un créneau**, en **centimes entiers** (ADR-0012), porté par le `Depart` (E02US004 — plus par le tournoi, [ADR-0017](adr/0017-le-depart-est-un-creneau-du-tournoi.md)). **Obligatoire** (`0` = gratuit, état distinct) ; les créneaux d'un même tournoi peuvent avoir des prix différents. Le montant dû d'un archer = **somme** des tarifs des départs où il est inscrit (E08US001). |
| **Quota d'un départ** | `Depart.quota` | Nombre **maximal d'inscrits** d'**un créneau** (capacité de salle), porté par le `Depart` (E02US006). **Facultatif** : `NULL` = sans plafond ; sinon un entier `1 ≤ quota ≤ 1 000`. Le dépassement est un **blocage dur** à l'inscription (`DepartComplet`, 409) — un invariant **applicatif** vérifié par le service et sérialisé par le writer unique (règle 7), sans contrainte SQL. Il n'y a **pas** de quota « au tournoi » : le total n'est que la somme des créneaux. |
| **Grain de validation** | `GrainValidation` | **Quand le scoreur valide** une phase : *fin de série* · *fin de duel* · *toutes les N volées* (`config.validation`, `D-11`). Politique de phase, réglée à la configuration — pas un réglage global. |
| **Séquence** | `Sequence` | Enchaînement ordonné de phases définissant un format. |
| **Placement** | `Placement` | Affectation d'un archer à cible + position + départ. |
| **Plan de cibles** | `PlanDeCibles` | Vue « qui tire où » d'un **départ**, produite par le moteur de placement (E03US001, `domain/placement.py`) : cibles remplies (archers + positions) + **rapport de conflits**. Recalculée à la demande ; source des exports (E09) et de la vue publique (E07). |
| **Conflit de placement** | `Conflit` | Un archer que le placement n'a **pas** pu poser, avec sa raison : `non_place` (plus de cible : place, positions ou hauteur épuisées) ou `sans_blason` (catégorie sans blason par défaut). Pas d'échec silencieux — CA « conflits » d'E03US001. |
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
| **Centimes** | Unité de **tout montant** du projet, en entier — jamais de flottant pour de l'argent ([ADR-0012](adr/0012-argent-en-centimes-entiers.md)). Les champs portent le suffixe `_centimes` ; les euros n'existent qu'à l'affichage. |
| **WebSocket** | Canal de diffusion temps réel. |
| **Migration** | Évolution de schéma versionnée (Alembic). |
| **AuditLog** | Journal des actions sensibles (corrections, validations, forfaits). |

> Toute nouvelle notion métier doit être ajoutée ici avant d'apparaître dans le code, l'API ou l'UI.
