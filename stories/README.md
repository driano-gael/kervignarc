# Backlog — User Stories (ordonné par montée en valeur)

Découpage des EPICs en user stories **à destination d'un développeur** (maille : une **capacité** cohérente, livrable et testable d'un bloc — plus grosse qu'un comportement isolé, assez petite pour tenir dans une branche revue en une passe ; INVEST). Voir [ADR-0021](../docs/adr/0021-maille-des-us-au-grain-capacite.md).

## Conventions
- **ID** : `ExxUSyyy` — `Exx` = code epic, `USyyy` = n° dans l'epic. L'ID rattache la story à son epic ; il **ne dicte pas l'ordre de réalisation**.
- **Ordre de réalisation** : la **séquence** ci-dessous, en **jalons de valeur** — on privilégie la montée en valeur, pas l'ordre des epics.
- Détail de chaque US : `stories/Exx-slug.md`. Format : *En tant que… je veux… afin de…* + **CA** (critères d'acceptation) + **Notes** (dev) + **Dépend de**.
- **Une branche par US** : `<type>/<ExxUSyyy>-<slug>` (ex. `feat/e04us003-saisie-fleches`), `type` selon le périmètre (feat/fix/refactor/test/docs/chore). PR + revue + CI verte → merge → suppression de la branche. Détail : `guide-architecture.md` §11.

> ### 🧭 Ce fichier ordonne, il ne suit pas
>
> **Ce README dit dans quel ordre les US se prennent. Il ne dit pas ce qui est fait.**
> L'état d'avancement et **la prochaine US à prendre** sont dans
> [`journal-d-avancement/SUIVI-US.md`](../journal-d-avancement/SUIVI-US.md), **qui fait autorité** —
> y compris sur la file d'exécution courante, qui a quitté l'ordre des jalons depuis que J0→J2 sont
> clos. Les deux fichiers **ne doivent pas porter deux comptes divergents** : ici, le **nombre d'US
> définies** ; là-bas, le **nombre d'US livrées**.
>
> *(Ajouté le 08/08/2026. Ce README annonçait « 101 US actives » contre 141 en-têtes réels — périmé
> depuis le 18/07 — et **ordonnançait encore quatre US mortes**, dont une en gras comme US porteuse.
> La cause est structurelle : chaque vague d'ajouts (démo du 27/07, maquettes du 04/08, fidélité du
> 05/08) a été inscrite au tracker, qui est le point de reprise quotidien, et pas ici, qui ne se lit
> qu'au moment de planifier. Le remède n'est pas la vigilance mais la **section par vague** ci-dessous :
> une vague neuve s'ajoute en un bloc, sans renuméroter 91 lignes — c'est ce coût de renumérotation
> qui faisait renoncer.)*

## Historique des révisions

| Date | Révision |
|---|---|
| **08/08/2026** | **Mise en conformité du backlog.** Recompte (141 → **147 en-têtes**, dont **143 actives** — l'index annonçait **101**), intégration des **42 US absentes** de la séquence (E14, E15, E16, E17, `E01US020`→`026`, `E05US020`→`025`, `E06US009`, `E07US009`, `E00US017`, `E11US008`, `E03US011`), **retrait des 4 US absorbées** qui étaient encore ordonnancées, section « US absorbées » créée, ordre `E09US008`/`E04US001` corrigé, titres réalignés sur les fiches. **6 US créées** pour les capacités qu'`EPIC-17` annonçait sans les porter. |
| **05/08/2026** | [`E17`](E17-fidelite-aux-maquettes.md) — **à ne pas confondre avec `E16`.** E16 traite ce que le commanditaire reproche **aux maquettes** ; **E17 amène le produit jusqu'à elles.** Le premier écart relevé était total : le front tournait encore sur la palette du walking skeleton (accent violet, fond blanc), les « US design » annoncées dans `index.css` n'ayant jamais été écrites. [ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md) rend les planches **opposables** en revue. |
| **04/08/2026** | **Retours du questionnaire de maquettes** — les 36 planches passées en revue une par une (verdict, critiques, évolutions, vocabulaire). Le **lot front seul** livré dans la foulée, **hors US** ; le reste est [`E16`](E16-retours-maquettes.md). Quatre écrans refusés en l'état : A07 phases, A10 plan de salle, A14 complétude, P03 classements publics. |
| **27/07/2026** | **Ajouts de la démo** (client final + développeur). Réutilisent des US déjà spécifiées (`E02US010` horaire, `E01US017` 7 statuts) ou en créent de neuves (`E11US008` LAN+QR, `E03US011` placement, `E01US022` blason FFTA). **Deux épics neufs** : [`E14`](E14-lisibilite-admin.md) (accueil & lisibilité admin) et [`E15`](E15-jeu-d-essai-simulation.md) (jeu d'essai & simulation). |
| **21/07/2026** | Cadrage d'`E08US002` : la tarification devient une **configuration du tournoi** ([ADR-0041](../docs/adr/0041-tarification-configuration-du-tournoi.md)) — `E01US020`, `E01US021`. |
| **20/07/2026** | Modèle d'entrée de l'appli : une seule SPA, **quatre expériences** — `E00US017` ([ADR-0042](../docs/adr/0042-modele-d-entree-choix-de-role-explicite.md)). |
| **18/07/2026** | **Entretien de conception** : 10 US + l'**EPIC-13** (équipes, **in-scope MVP** — renverse le « hors périmètre » du 14/07). Arbitrages : [ADR-0026](../docs/adr/0026-cycle-de-vie-du-tournoi-sept-statuts.md), [ADR-0027](../docs/adr/0027-vocabulaire-de-score-injectable-defaut-ffta.md), [ADR-0028](../docs/adr/0028-epreuves-par-equipes-participant.md), [DETTE-010](../docs/dette.md), ENF-7. |
| **17/07/2026** | Maille révisée au **grain capacité** (÷~1,5, backlog non livré uniquement). Trois US manquantes depuis le 16/07 réintégrées : `E02US009`, `E08US005`, `E12US008`. |
| **15/07/2026** | Entretien du 14/07 ([CDC UX](../cahier-des-charges-ux.md) v0.2 `D-01`→`D-28`, [CDC design](../cahier-des-charges-design.md) v0.3 `DV-01`→`DV-08`) : **3 US réécrites** (`E04US001`, `E10US003`, `E10US007`), **1 caduque** (`E10US004`), **12 créées** dont l'**EPIC-12** (pilotage du jour J), qui **porte la valeur du produit** et qu'aucun EPIC ne couvrait. Plus deux US de résorption issues des revues : `E00US013` ([DETTE-004](../docs/dette.md)) et `E00US014` ([DETTE-005](../docs/dette.md)). |

## Jalons de valeur
| Jalon | Valeur livrée |
|---|---|
| **J0** | Walking skeleton : l'architecture tourne bout-en-bout |
| **J1** | Gérer un **tournoi de qualification complet** (premier usage réel) |
| **J2** | **Duels simples** : élimination directe → podium — **et la bascule de tour**, qui porte la valeur (`D-25`) |
| **J3** | **Placement intégral 1→N** (format du classeur 120) + écran de salle & identité |
| **J4** | Confort, richesse & robustesse (import, presets, repêchage, restauration) |

> **Les jalons ordonnent les 91 US du plan initial.** Tout ce qui a été ajouté depuis le 18/07/2026
> vit dans les **sections par vague**, plus bas : ces US portent bien un jalon (colonne *Jalon*) mais
> **pas de numéro de séquence**, parce que les insérer aurait renuméroté tout ce qui suit. L'ordre
> réel de prise est celui de [`SUIVI-US.md`](../journal-d-avancement/SUIVI-US.md).

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
| 31 | E02US004 | Configurer les départs (créneaux) |
| 32 | E02US009 | Inscrire un archer sur des départs |
| 33 | **E00US014** | **Outiller les tests du front** *([DETTE-005](../docs/dette.md) — avant E08US001)* |
| 34 | E08US001 | Calculer le montant dû |
| 35 | E03US001 | Placement automatique & plan de cibles |
| 36 | E03US004 | Ajuster le placement (glisser-déposer) |
| 37 | **E10US003** | **Scoreurs du tournoi : définition & session** — *réécrite (`D-12`, `D-13`)* |
| 38 | **E04US001** | **Rattacher une tablette à sa cible (QR + jeton de poste)** — *réécrite (`D-06`, `D-07`)* |
| 39 | **E09US008** | **Imprimer les QR de cible et les codes scoreurs** *(`D-07`)* |
| 40 | **E10US007** | **Poste de cible : saisir sans s'identifier** — *réécrite (`D-13`)* |
| 41 | E04US002 | Saisie de qualification en temps réel |
| 42 | E04US009 | Diffusion live & résilience réseau |
| 43 | **E12US001** | **Superviser les postes de saisie** *(`D-06`, `D-21`)* |
| 44 | E06US001 | Classement de qualification (cumul, départage, par catégorie) |
| 45 | E07US001 | Vues publiques : classements, plans de cibles et live |
| 46 | **E07US006** | **Suivre des archers : ma journée** *(`D-09` ; tranche 1, front)* |
| 46b | **E07US009** | **Suivre le déroulé du tour en direct** *(tranche 2 d'E07US006 : backend + ADR)* |
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
> départs) ; **`E04US001` (le rattachement) précède `E09US008` (l'impression des QR)** ; `E12US001`
> (supervision) suit `E04US001` (il n'y a rien à superviser avant qu'un poste existe) ; `E00US014` (tests
> du front) précède `E08US001` — c'est lui qui calcule **de l'argent** à partir d'une conversion que rien ne
> couvre aujourd'hui ([DETTE-005](../docs/dette.md), [ADR-0012](../docs/adr/0012-argent-en-centimes-entiers.md)).
>
> ⚠️ **Cet ordre `E04US001` → `E09US008` a été corrigé le 08/08/2026 ; il disait l'inverse.**
> La contradiction était visible dans le dépôt : `E09US008` **déclare** dépendre d'`E04US001`, et
> les deux ont été livrées dans cet ordre (18/07 puis 19/07). L'erreur venait d'un raisonnement juste
> appliqué au mauvais objet — *« on ne scanne pas un QR qui n'existe pas »* décrit l'ordre d'**usage
> le jour J**, pas l'ordre de **construction** : le QR **encode le jeton de poste**, dont `E04US001`
> définit le concept, donc c'est elle qui doit exister d'abord. **À retenir** : quand une note de
> séquence contredit un « Dépend de » d'une fiche, c'est la fiche qui a raison — elle est écrite par
> qui a lu le code.

## J2 — Duels simples + **bascule de tour**
| Seq | US | Titre |
|---|---|---|
| 58 | E05US001 | Séquence de phases (modèle, édition, cohérence) |
| 59 | E05US003 | Politiques injectables & assemblage |
| 60 | E05US005 | Arbre d'élimination directe |
| 61 | E03US006 | Contrainte ≥ 2 clubs par cible |
| 62 | E03US009 | Placer les duellistes côte à côte *(cibles attribuées **aux matchs**, `D-08`)* |
| 63 | E04US013 | Saisie en duels |
| 64 | E04US015 | Gérer abandon / disqualification *(**absorbe `E12US004`**, ADR-0050)* |
| 65 | E12US008 | Cycle de vie d'un départ (créneau) |
| 66 | E08US005 | Rembourser une inscription payée annulée |
| 67 | **E12US002** | **Lancer un tour (feu vert + lancement)** *(`D-22`, `D-23`, `D-25`)* |
| 68 | **E04US018** | **Afficher la prochaine cible après validation** *(`D-09`, canal 1)* |
| 69 | **E07US008** | **Vue publique des affectations du prochain tour** *(`D-09`, canal 2)* |
| 70 | E06US003 | Barrage de tir pour places décisives |
| 71 | E06US004 | Podium des duels & agrégation des rangs |

> **C'est ici que le produit gagne ou perd.** `E12US002` n'a de sens que si `E03US009` l'a précédé (la cible
> du match suivant est connue **d'avance**, `D-08`) et que `E04US018` / `E07US008` le suivent : **lancer sans
> prévenir les 4 canaux, c'est le temps mort d'avant.** `E12US008` (cycle de vie d'un départ) et `E08US005`
> (remboursement) partagent le même déclencheur — la suppression d'un départ à inscriptions confirmée
> ([ADR-0018](../docs/adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md)) — d'où leur position
> côte à côte, dans la **même famille** qu'`E04US015` : un aléa qui ne bloque pas le tour, mais se documente.
>
> *(Les séquences 58→72 ont été **resserrées en 58→71** le 08/08/2026 par le retrait d'`E12US004`,
> absorbée. Une US morte laissée dans une file ordonnée n'est pas inerte : celle-ci y figurait **en
> gras**, comme US porteuse.)*

## J3 — Placement intégral 1→N + écran de salle & identité
| Seq | US | Titre |
|---|---|---|
| 72 | E05US010 | Placement intégral 1→N **& peuplement multiple** *(**absorbe `E05US018`**, l'oracle 120)* |
| 73 | E05US015 | **Le catalogue de types de phase** *(**absorbe `E05US016`**, le repêchage — qui est une politique `routing`, pas un type)* |
| 74 | E06US006 | Classement intégral 1→N & profondeur configurable |
| 75 | E03US007 | Contrainte séparation catégorie/blason |
| 76 | E09US005 | Classements PDF (par catégorie, intégral 1→N) |
| 77 | **E00US013** | **Factoriser les briques d'UI partagées du front** *([DETTE-004](../docs/dette.md))* |
| 78 | **E01US016** | **Définir l'identité visuelle du tournoi** *(`D-27`, `D-28`, `DV-06`)* |
| 79 | **E07US004** | **Écran de salle : déroulé automatique et pilotage admin** — *réécrite (`D-21`)* |
| 80 | E07US005 | Vue tableaux/arbres live |

> `E01US016` précède `E07US004` : **l'identité n'a pas de surface avant l'écran de salle** — c'est lui, avec
> l'appli publique, qui la porte (`D-27`). L'admin et la saisie **restent l'outil**, neutres.
> `E00US013` les précède tous deux : c'est là que la duplication d'UI ([DETTE-004](../docs/dette.md))
> **commence à coûter** — un token de couleur appliqué en 8 endroits, c'est 8 occasions d'en oublier un.
>
> *(Séquences resserrées le 08/08/2026 : `E05US018` (ex-seq 75) et `E05US019` (ex-seq 83) en ont été
> retirées, absorbées. `E05US019` était d'ailleurs marquée **✅** au tracker alors qu'aucune US de ce
> nom n'a été livrée — c'est `E01US023` qui a livré la capacité.)*

## J4 — Confort, richesse & robustesse
| Seq | US | Titre |
|---|---|---|
| 81 | E02US007 | Importer un fichier inscript'arc (parsing + rapport) |
| 82 | E01US011 | Presets de barèmes multi-phases *(⚠️ dépend de `E05US023` : un preset pour un format non jouable ne se recette pas)* |
| 83 | E01US012 | Gérer plusieurs gabarits |
| 84 | E03US010 | Générer / éditer le déroulé horaire |
| 85 | E09US007 | Déroulé horaire imprimable |
| 86 | E11US006 | Restauration & arrêt propre |
| 87 | E10US006 | Modifier le mot de passe admin |

---

# Ajouts postérieurs au plan initial

> Ces US **portent un jalon** mais **pas de numéro de séquence** : les insérer aurait renuméroté tout
> ce qui précède, et c'est ce coût qui avait fait renoncer à les inscrire du tout. L'ordre de prise
> effectif est dans [`SUIVI-US.md`](../journal-d-avancement/SUIVI-US.md).

## Vague du 18/07/2026 — entretien de conception

| US | Titre | Jalon | Réf |
|---|---|---|---|
| **E00US015** | Ossature de navigation de l'appli admin (coquille) | J3 | `D-19`/`D-20` |
| **E00US016** | Écrans admin : liste/fiche & référentiels en déroulante | J3 | remontées UX |
| **E01US017** | Cycle de vie enrichi du tournoi (7 statuts) | J1 | ADR-0026 |
| **E01US018** | Vocabulaire de score configurable (défaut FFTA) | J1 | ADR-0027 |
| **E01US019** | Capacité de cible non bornée (positions > D) | J1→J3 | DETTE-010 |
| **E02US010** | Horaire de départ HH:MM obligatoire & ≥ 1 départ | J1 | remontée « 9hzc » |
| **E13US001** | Abstraction participant (le match oppose des participants) | J2 | ADR-0028 (**avant E05US005**) |
| **E13US002** | Composer les équipes d'un tournoi | J2 | EPIC-13 |
| **E13US003** | Scoring d'équipe (politique injectable) | J2 | EPIC-13 |
| **E13US004** | Placement, saisie & classement par équipe | J2→J3 | EPIC-13 |

> **[EPIC-13](../epics/EPIC-13-equipes.md)** créé — épreuves par équipes, **in-scope MVP** (renverse le « hors périmètre » du 14/07, ADR-0028).

## Vague du 20/07/2026 — modèle d'entrée

| US | Titre | Jalon | Réf |
|---|---|---|---|
| **E00US017** | Écran d'accueil : choisir son appareil / rôle | J3 | [ADR-0042](../docs/adr/0042-modele-d-entree-choix-de-role-explicite.md) — 4 portes (Tablette / Public / Scoreur / Admin) |

## Vague du 21/07/2026 — la tarification devient une configuration

| US | Titre | Jalon | Réf |
|---|---|---|---|
| **E01US020** | Modèle de tarification injectable & sujet de facturation (archer / club) | à planifier | [ADR-0041](../docs/adr/0041-tarification-configuration-du-tournoi.md) — sujet `club` sur `club_id`/ADR-0014, **pas** via E13 |
| **E01US021** | Tarification dégressive (option de config, % ou montant) | à planifier | dépend d'`E01US020` |

## Vague du 27/07/2026 — retours de la démo

> Client final + développeur. Deux US **déjà spécifiées** remontent en priorité (♻️, pas de doublon) ;
> les autres sont **neuves** (🆕). **Bugs d'abord**, puis les deux épics.

| US | Titre | Épic | Jalon |
|---|---|---|---|
| E02US010 | Horaire de départ `HH:MM` (corrige « 8h00 → 18h00 ») | E02 ♻️ | J1 |
| E01US017 | Cycle de vie enrichi (7 statuts) — **prérequis** du tableau de bord | E01 ♻️ | J1 |
| **E11US008** | Accès réseau LAN (poste organisateur) + QR de rattachement à l'écran | E11 🆕 | J1 |
| **E03US011** | Placement : retour visuel de génération + position A..D côté admin | E03 🆕 | J1 |
| **E01US022** | Blason FFTA par défaut par catégorie + affichage du blason hérité | E01 🆕 | J1 |
| **E14US001** | Accueil-tableau de bord contextualisé par tournoi (`D-20`) | E14 🆕 | J3 |
| **E14US002** | Aide contextuelle « ce qui est saisissable et pourquoi » | E14 🆕 | J3 |
| **E14US003** | Ranger l'administration par axe d'activité (`D-19`) | E14 🆕 | J3 |
| **E15US001** | Jeu d'essai : générer des inscrits + scénarios rejouables | E15 🆕 | J3 |
| **E15US002** | Moteur de simulation éphémère + garde-fou (non-persistance) | E15 🆕 | J3 |
| **E15US003** | Bot pilote automatique pausable + cockpit interactif multi-vues | E15 🆕 | J3 |
| **E01US023** | Les briques de l'atelier deviennent le patrimoine du club | E01 🆕 | J3 |

> Épics : [`EPIC-14`](../epics/EPIC-14-lisibilite-admin.md) (close), [`EPIC-15`](../epics/EPIC-15-jeu-d-essai-simulation.md) (close).

## Chantier « moteur de phases & plan de tournoi » — cadré le 31/07/2026, élargi depuis

> Parti du constat que l'écran « Formats » livré par `E01US023` ne savait composer **qu'une
> qualification**. Ces US se prennent **dans l'ordre** : chacune lève le verrou de la suivante.

| Ordre | US | Titre | Jalon |
|---|---|---|---|
| 1 | **E01US024** | Composer, diagnostiquer et simuler un déroulé de tournoi | J3 |
| 2 | **E05US020** | Le moteur consomme les prélèvements déclarés *(cœur de `DETTE-028`)* | J3 |
| 3 | **E05US021** | Un format connaît son effectif minimum, et le lancement le vérifie | J3 |
| 4 | **E01US025** | Le départ est la portée sportive, le déroulé se définit une fois | J3 |
| 5 | **E05US024** | Un prélèvement lit le classement de **sa** phase source | J3 |
| 6 | **E05US025** | Plusieurs qualifications dans un même déroulé *(**dépend d'`E05US024`** par nécessité)* | J3 |
| 7 | **E05US023** | Rendre jouables poules, suisse, colline et Big Shoot Off *(**à découper**)* | J3 |

> ⚠️ **`E05US023` est au rang 7 de ce chantier — soit le rang 2 de la file d'exécution**
> (cf. [`SUIVI-US.md`](../journal-d-avancement/SUIVI-US.md), qui ne compte que ce qui reste ; ce
> tableau-ci inclut les US déjà livrées) — **sur arbitrage du 08/08/2026** : priorité « au plus tôt » donnée par
> le commanditaire, tempérée par une dépendance dure : `E05US024`+`E05US025` forment **un seul
> chantier**, et couper au milieu laisserait le peuplement générique à moitié exploité. Elle passe
> donc **devant `E16US002`** mais **derrière `E05US025`**.
> **Elle oblige à corriger le CA d'`E06US003`**, qui prévoit explicitement sa reprise, et **débloque
> `E01US011`** (J4).

## Vague du 04/08/2026 — retours du questionnaire de maquettes ([`E16`](E16-retours-maquettes.md))

> Ce que le commanditaire reproche **aux maquettes**. Les **quatre écrans refusés (🔴)** passent en
> premier : ce sont les seuls retours qui disent « l'écran ne répond pas au besoin ».

| US | Titre | Jalon | Réf |
|---|---|---|---|
| **E16US001** | Plan de salle : se mettre d'accord sur ce qu'est un pas de tir | J2 | 🔴 A10 · [ADR-0073](../docs/adr/0073-pas-de-tir-groupe-de-cibles-couloir-de-tir-place-d-archer.md) |
| **E16US002** | Phases : une bibliothèque de phases réglables, pas une séquence figée | J3 | 🔴 A07 · **à recadrer contre ADR-0076 avant d'être prise** |
| **E16US003** | Complétude : ne plus mélanger le déroulé et la gestion administrative | J2 | 🔴 A14 |
| **E16US004** | Le public suit **plusieurs** archers, de bout en bout | J2 | 🔴 P03 · [ADR-0079](../docs/adr/0079-un-seul-interrupteur-mes-archers-pour-tout-l-onglet-public.md) |
| **E16US005** | Placement : la largeur d'un PC, et un puits de réserve | J2 | ⚠️ **recoupe `E03US004`** (zone réserve déjà livrée) — lire son CA d'abord |
| **E16US006** | Patrimoine : distinguer l'officiel FFTA du local, et porter le logo du club | J3 | questionnaire A16 |
| **E16US007** | Impressions, exports et podiums paramétrables | J3 | **à redécouper** · recoupe `E16US012` |
| **E16US008** | Feu vert : agir depuis la ligne du duel qui bloque | J2 | recoupe `E16US012` |
| **E16US009** | Écran de salle : régler ce qui défile, et défiler ce qui ne tient pas | J3 | questionnaires P06/P07 |
| **E16US010** | Chercher partout, et voir d'avance ce qui bloque un lancement | J3 | questionnaire A02 |
| **E16US011** | Ce que trois questionnaires « validés » demandaient quand même | J3 | **rattrapage** · 2 contradictions à arbitrer (S08, A09) |
| **E16US012** | La famille des écrans « prêt à… » | J3 | née d'`E16US003` · **refonte de navigation, à instruire avant `E16US007`/`E16US008`** |

## Vague du 05/08/2026 — fidélité du produit aux maquettes ([`E17`](E17-fidelite-aux-maquettes.md))

> **À ne pas confondre avec `E16`** : `E16` traite ce qu'on reproche **aux maquettes**, `E17` amène
> **le produit** jusqu'à elles. Une US qui change ce que *montre* un écran est une `E16` ; une US qui
> change la **ressemblance** entre l'écran et sa planche est une `E17`.

| US | Titre | Jalon | Réf |
|---|---|---|---|
| **E17US001** | Poser la charte du club dans l'application | J1 | [ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md) |
| **E17US002** | Le catalogue de composants adopte les formes des planches | J1 | dépend d'`E17US001` |
| **E17US003** | Les deux premiers écrans de l'admin se conforment à leur planche | J1 | A01 + A02 |
| **E17US004** | La supervision passe en grille de tuiles | J2 | A13, variante B |
| **E17US005** | Embarquer la police du club pour le jour J | J3 | `DV-07` · 🔒 **arbitrage d'ajout d'actif en attente (règle 11)** |
| **E17US006** | Donner une couleur à l'action destructrice | J3 | `DV-03` · 🔒 **trou de charte, ADR attendu** |
| **E17US007** | Résorber les écarts relevés sur les écrans d'administration | J3 | le relevé est **fait** ; l'US qui le solde manquait |
| **E17US008** | Confronter les 9 planches de saisie `S**` et résorber | J3 | recoupe `E16US011` (S08) |
| **E17US009** | Confronter les 7 planches publiques `P**` et résorber | J3 | A14 et P03 **hors résorption** (réserve 2 d'ADR-0074) |
| **E17US010** | Empêcher le dossier de maquettes de dériver du produit | J3 | **à prendre avant `E17US008`/`E17US009`** |

> 🔒 = **spécifiée, pas prenable** : l'US attend un arbitrage de l'utilisateur. Ne pas la commencer.
> *(Les six dernières ont été créées le 08/08/2026 : l'epic annonçait ces capacités **sans aucune US
> pour les porter**, et comme ses quatre US étaient cochées, il se lisait comme terminé.)*

## Résorptions de dette planifiées — arbitrages du 07/08/2026

> Quatre questions ouvertes du registre, **tranchées par le commanditaire** à la revue d'`E01US025`.
> Hors jalon courant : elles sont ici pour qu'une décision prise ne se reperde pas.

| US | Titre | Résorbe |
|---|---|---|
| **E05US023** | Rendre jouables poules, suisse, colline, Big Shoot Off *(voir le chantier moteur ci-dessus)* | `DETTE-028` |
| **E06US009** | Un palmarès **par départ, juxtaposés** *(« 4 départs = 4 podiums » : **aucune** agrégation inter-départs à écrire)* | `DETTE-045` |
| **E01US026** | Supprimer un tournoi : signaler ce qui partira, puis confirmer | `DETTE-001` *(la **plus ancienne** du registre)* |
| **E05US022** | Ancrer la séquence sur **l'identité** de l'étape | `DETTE-026` |

> ⚠️ **`DETTE-044` (`NewType` sur les identifiants) n'a pas d'US** — à prendre avant la prochaine US
> qui touche une portée.

---

## US absorbées (hors séquence — l'identifiant reste, la capacité est livrée ailleurs)

> **Ne jamais les ordonnancer.** Une US absorbée dont l'identifiant traîne dans une file de priorité
> se prend pour du travail restant. ⚠️ Et « absorbée, donc faite » reste un **raccourci** : rien ne
> garantit qu'une US absorbante ait livré **toute** la capacité de l'absorbée. Les quatre ci-dessous
> le sont — `E12US004` comprise : le producteur d'audit `FORFAIT` est livré et câblé
> (`application/forfaits.py`, trace atomique via `declarer_avec_trace` / `annuler_avec_trace`).
> Se le faire confirmer **par le code**, jamais par ce tableau.

| US | Titre | Absorbée par | Date |
|---|---|---|---|
| **E05US016** | ~~Routing repêchage-réintégration (WA)~~ | **E05US015** — le repêchage est une politique `routing`, pas un type de phase ([ADR-0062](../docs/adr/0062-catalogue-de-types-de-phase.md) §1) | 31/07/2026 |
| **E05US018** | ~~Oracle 120 (rejeu + comparaison)~~ | **E05US010** — le moteur et sa preuve ne se séparent pas | 31/07/2026 |
| **E05US019** | ~~Enregistrer une séquence comme modèle~~ | **E01US023** — doublon repéré au cadrage ([ADR-0060](../docs/adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md) §5) | 31/07/2026 |
| **E12US004** | ~~Tracer un forfait~~ *(`D-24`)* | **E04US015** — concept unique `Forfait` scopé à la phase ([ADR-0050](../docs/adr/0050-forfait-abandon-et-disqualification.md)) | 27/07/2026 |

## US caduques (hors séquence — la capacité elle-même n'a plus d'objet)

| US | Titre | Motif |
|---|---|---|
| **E10US004** | ~~Habiliter un scoreur sur plusieurs cibles~~ | **Sans objet depuis `D-12`/`D-13`** : le scoreur **n'est habilité sur aucune cible** — il est **itinérant** et choisit celle dont il valide les scores. Il n'y a plus rien à habiliter. Conservée dans [`E10-acces-roles.md`](E10-acces-roles.md) comme trace. |

> **Absorbée ≠ caduque.** Une US **absorbée** a vu sa capacité livrée par une autre US : le besoin
> existait et il est couvert. Une US **caduque** a vu son besoin disparaître : il n'y a rien à
> livrer, ni ici ni ailleurs. La confusion coûte cher dans les deux sens — chercher un livrable qui
> n'existe pas, ou croire couvert un besoin qui ne l'est pas.

---

## Compte

| | Compte | Détail |
|---|---|---|
| **En-têtes d'US dans `stories/`** | **147** | `grep -cE "^### " stories/E*.md` |
| **US actives** | **143** | = 88 ordonnancées par jalon (J0→J4) + 55 ajoutées par vague |
| Absorbées | **4** | `E05US016`, `E05US018`, `E05US019`, `E12US004` — dont **3 ont encore une fiche** dans `stories/` (`E05US016` n'en a jamais eu) |
| Caduques | **1** | `E10US004` — la fiche est conservée comme trace |

> **147 = 143 actives + 3 fiches absorbées + 1 fiche caduque.** `E05US016` est le 4ᵉ identifiant
> absorbé mais **n'a pas de fiche** : il n'existe que dans la table de refonte de maille
> d'[`E05`](E05-moteur-phases.md) et dans le CA « repêchage World Archery (ex-E05US016) »
> d'`E05US015`. C'est ce qui le rendait invisible à un recompte par en-têtes — et pourtant il était
> **ordonnancé en seq 89** jusqu'au 08/08/2026.

> **Ce compte est celui des US *définies*, pas des US *livrées*.**
> Le nombre d'US **livrées** est dans [`SUIVI-US.md`](../journal-d-avancement/SUIVI-US.md), **qui
> fait autorité** — ne pas en tenir un second ici. *(Recompté le 08/08/2026 en comptant les en-têtes
> du dossier, pas en reprenant le chiffre précédent : il annonçait **101 actives** contre 141
> en-têtes réels, soit un tiers du backlog invisible depuis le 18/07.)*
