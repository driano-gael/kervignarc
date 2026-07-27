# Suivi des US — état d'avancement

> **Ce fichier est le point de reprise.** Quand l'utilisateur dit « **reprend les US** », l'assistant
> lit ce tableau : il y trouve ce qui est **fait** (mergé sur `main`), et **la prochaine US** à
> prendre. La séquence de référence est celle de [`stories/README.md`](../stories/README.md) (jalons
> de valeur J0→J4). Le détail de chaque US est dans `stories/Exx-*.md`.
>
> **Règle de mise à jour** : une US passe à ✅ **dans son propre dernier commit, la revue
> (`/revue-us`) faite et poussée** — sans attendre la confirmation « c'est mergé ». C'est sûr parce
> que cette mise à jour **voyage avec le diff de l'US** : elle n'atteint `main` qu'**au merge de la
> PR**. Donc sur `main` ce tableau reste **toujours vrai** (le ✅ y apparaît pile au merge) ; sur la
> branche, il est optimiste d'un cran — c'est le livrable. Le même commit pointe la 🎯 suivante. En
> cas de doute au moment de reprendre, recouper avec `git log main --first-parent` / `git branch -r`.

**Dernière mise à jour : 27/07/2026** · **69 US livrées** · dernière : `E04US015` *(abandon / DSQ — qualif + duels)*.

---

## 🎯 Prochaine US

> **`E12US008` — cycle de vie d'un départ** : faire vivre l'état d'un créneau de tir (ouvert, en
> cours, clos…) pour piloter le déroulé du jour J. *(Prochaine du J2 en séquence ; à cadrer.)*
> *Ensuite* : **bascule de tour** `E12US002` (lancer un tour, feu vert + lancement — clé du J2),
> remboursement `E08US005`, prochaine cible `E04US018`.
> *Note : le **fil équipes** est **débloqué** — `E13US002` (composer les équipes) peut être pris à tout
> moment maintenant qu'`E13US001` a posé l'abstraction `Participant`.*
> *`E12US004` (tracer un forfait) est **absorbée** par `E04US015` — voir ci-dessous.*
> *J1 est **terminé** (46/46) ; le confort « ma journée » et les classements imprimables restent hors
> décompte du jalon.*
>
> *Fait juste avant :*
> - `E04US015` **gérer abandon / disqualification** — US à **surface visible**. Un acte **scoreur**
>   « déclarer abandon / DSQ », **en qualification comme en duels** ([ADR-0050](../docs/adr/0050-forfait-abandon-et-disqualification.md),
>   qui **fusionne E04US015 + E12US004**). Concept unique `Forfait` **scopé à la phase** : en qualif
>   un **abandon** est relégué en fin de classement (rangé, score affiché), une **DSQ** en est sortie
>   (rang vide, score conservé) ; en duels le forfaitaire **cède** son match (l'adversaire passe). Les
>   **flèches sont préservées** (≠ suppression, ADR-0016) ; l'acte est **daté, attribué, motivé,
>   réversible** (`D-15`) et **audité** (`FORFAIT`). **DETTE-014 résorbée** (la complétude compte un
>   forfaitaire comme « série close »). `Q-UX5` fermée sur le **scoreur**. Recette :
>   [`docs/fonctionnel/E04US015.md`](../docs/fonctionnel/E04US015.md).
> - `E04US013` **écran scoreur (tranche front)** — US à **surface visible**, sous la **même US** que le
>   backend (le compte d'US ne bouge pas). Le scoreur choisit une **phase de tableau**, voit la **liste
>   des duels par tour**, ouvre un duel et le score : **grille de manches** (sets ou cumul selon `mode`,
>   résolu par arme côté serveur — le front n'en décide pas), **barrage** conditionnel (§8.2, désignation
>   manuelle du plus près du centre), **validation** qui verrouille et fait avancer le tableau jusqu'au
>   **podium**. **File hors-ligne + rejeu** dédiée aux actes de duel (2ᵉ occurrence du motif de
>   résilience, **dupliquée** — pas extraite, règle 12). Le **contrat de lecture** des duels a été
>   **enrichi** (pavé exposé dès la lecture : zones du blason, nb de manches/flèches, seuil), analogue à
>   la grille de qualif. Écran monté dans l'**Espace scoreur**. Recette :
>   [`docs/fonctionnel/E04US013.md`](../docs/fonctionnel/E04US013.md).
> - `E04US013` **backend** (saisie en duels) — **sans surface visible** (domaine → moteur → politiques →
>   persistance → service → **API scoreur**). Un **duel** se score au **système de sets** (points de set
>   2/1-1/0, premier à 6 — FFTA ; club 4) ou **au cumul** en arc à poulies (A.7.5.2) ; à égalité, un
>   **barrage** (1 flèche, puis désignation du plus près du centre — l'appli ne mesure pas la distance).
>   Le **vainqueur validé** est transmis au moteur `Tableau.jouer` : le tableau, **non persisté**, est
>   **reconstruit** du classement et **rejoué** des duels validés (seul le **tir** est persisté, table
>   `duel`, migration 0030). Le barème est **résolu par arme** via un **résolveur injecté à défaut FFTA**
>   (E01US011 le configurera — **dépendance sur-affirmée retirée**). Décisions :
>   [ADR-0049](../docs/adr/0049-saisie-et-scoring-des-duels.md).
> - `E03US009` (placer les duellistes côte à côte) — US à **surface visible**. Le placement d'une phase
>   de tableau met les **deux adversaires d'un duel** du 1er tour **côte à côte** « dans la mesure du
>   possible », par ré-ordonnancement de l'entrée du glouton (moteur inchangé, ADR-0048) ; les duels non
>   rapprochés sont **signalés**. Plan **matérialisé par phase** (table `placement_tableau`, migration
>   0029), ajustable au glisser-déposer. Recette : [`docs/fonctionnel/E03US009.md`](../docs/fonctionnel/E03US009.md).

---

## J0 — Walking skeleton — ✅ **terminé (12/12)**

| US | Titre | État |
|---|---|---|
| E00US001 | Initialiser le monorepo | ✅ |
| E00US002 | Configurer la qualité (ruff, mypy, ESLint…) | ✅ |
| E00US003 | CI bloquante | ✅ |
| E00US004 | Squelette de couches + garde-fou d'imports | ✅ |
| E00US005 | Composition root minimale | ✅ |
| E00US006 | SQLite (WAL) + migration initiale | ✅ |
| E00US007 | File d'écriture + writer unique | ✅ |
| E00US008 | WebSocket + diffusion post-commit | ✅ |
| E00US009 | Repository + endpoint bout-en-bout | ✅ |
| E00US010 | Shell React | ✅ |
| E00US011 | Tranche verticale démontrable | ✅ |
| E00US012 | Exécutable de dev (FastAPI sert le front) | ✅ |

## J1 — Tournoi de qualification de bout en bout — ✅ **terminé (46/46)**

| Seq | US | Titre | État |
|---|---|---|---|
| 13 | E01US001 | Créer un tournoi | ✅ |
| 14 | E10US002 | Accès administrateur protégé | ✅ |
| 15 | E10US001 | Consultation publique ouverte | ✅ |
| 16 | E01US002 | Éditer / lister les tournois | ✅ |
| 17 | E01US003 | Gérer les catégories (CRUD) | ✅ |
| 18 | E01US004 | Pré-charger les catégories FFTA salle | ✅ |
| 19 | E01US013 | Catégorie : éligibilité multi-âges | ✅ |
| 20 | E01US005 | Gérer les blasons | ✅ |
| 21 | E01US014 | Blason : valeurs de score admises | ✅ |
| 22 | E01US006 | Associer catégorie ↔ blason | ✅ |
| 23 | E01US007 | Définir un gabarit de salle | ✅ |
| 24 | E01US008 | Réutiliser / ajuster un gabarit | ✅ |
| 25 | E01US009 | Définir un barème de qualification | ✅ |
| 26 | E01US015 | Grain de validation d'une phase | ✅ |
| 27 | E01US010 | Définir le tarif par départ | ✅ |
| 28 | E02US001 | Gérer le référentiel clubs | ✅ |
| 29 | E02US002 | Créer un archer | ✅ |
| 30 | E02US003 | Éditer / supprimer un archer | ✅ |
| 31 | E02US004 | Configurer les départs (créneaux) | ✅ |
| 32 | E02US009 | Inscrire un archer sur des départs | ✅ |
| 33 | E00US014 | Outiller les tests du front | ✅ |
| 34 | E08US001 | Calculer le montant dû | ✅ |
| 35 | E03US001 | Placement automatique & plan de cibles | ✅ |
| 36 | E03US004 | Ajuster le placement (glisser-déposer) | ✅ |
| 37 | E10US003 | Scoreurs : définition & session | ✅ |
| 38 | E09US008 | Imprimer QR de cible & codes scoreurs | ✅ |
| 39 | E04US001 | Rattacher une tablette à sa cible (QR) | ✅ |
| 40 | E10US007 | Poste de cible : saisir sans s'identifier | ✅ |
| 41 | E04US002 | Saisie de qualification en temps réel | ✅ |
| 42 | E04US009 | Diffusion live & résilience réseau | ✅ |
| 43 | E12US001 | Superviser les postes de saisie | ✅ |
| 44 | E06US001 | Classement de qualification | ✅ |
| 45 | E07US001 | Vues publiques : classements, plans, live | ✅ |
| 46 | E07US006 | Suivre des archers : ma journée *(tranche 1, front)* | ✅ |
| **46b** | **E07US009** | **Suivre le déroulé du tour en direct** *(tranche 2, backend + ADR)* | ✅ |
| 47 | E10US005 | Journal d'audit métier | ✅ *(fait en avance)* |
| 48 | E12US007 | Alerter par calcul d'impact | ✅ |
| 49 | E08US002 | Suivi des paiements | ✅ |
| 50 | E12US005 | Afficher la complétude du tournoi | ✅ |
| 51 | E12US006 | Rechercher un archer depuis n'importe où | ✅ |
| 52 | E02US005 | Détecter et fusionner les doublons | ✅ |
| 53 | E02US006 | Contrôler les quotas | ✅ *(fait en avance)* |
| 54 | E09US001 | Socle PDF & feuille de marque | ✅ *(fait en avance)* |
| 55 | E09US003 | Listes imprimables (placement, club, paiement) | ✅ |
| 56 | E11US001 | Release, base et mise en réseau | ✅ |
| 57 | E11US003 | Sauvegarde & archive | ✅ |

## J2 — Duels simples + bascule de tour — 🔶 **en cours (7/14)**

| Seq | US | Titre | État |
|---|---|---|---|
| 58 | E05US001 | Séquence de phases | ✅ |
| 59 | E05US003 | Politiques injectables & assemblage | ✅ |
| 60 | E05US005 | Arbre d'élimination directe *(moteur sur `Participant`)* | ✅ |
| 61 | E03US006 | Contrainte ≥ 2 clubs par cible | ✅ |
| 62 | E03US009 | Placer les duellistes côte à côte | ✅ |
| 63 | E04US013 | Saisie en duels | ✅ *(backend + API + écran scoreur)* |
| 64 | E04US015 | Gérer abandon / disqualification | ✅ *(qualif + duels, ADR-0050)* |
| 65 | E12US004 | ~~Tracer un forfait~~ | ⛔ *(absorbée par E04US015)* |
| 66 | E12US008 | Cycle de vie d'un départ | 🎯 |
| 67 | E08US005 | Rembourser une inscription payée annulée | ⬜ |
| 68 | E12US002 | Lancer un tour (feu vert + lancement) | ⬜ |
| 69 | E04US018 | Afficher la prochaine cible après validation | ⬜ |
| 70 | E07US008 | Vue publique des affectations du prochain tour | ⬜ |
| 71 | E06US003 | Barrage de tir pour places décisives | ⬜ |
| 72 | E06US004 | Podium des duels & agrégation des rangs | ⬜ |

## J3 — Placement intégral 1→N + écran de salle — 🔶 **en cours (2/11)**

| Seq | US | Titre | État |
|---|---|---|---|
| 73 | E05US010 | Placement intégral 1→N | ⬜ |
| 74 | E05US015 | Big Shoot Off | ⬜ |
| 75 | E05US018 | Oracle 120 (rejeu + comparaison) | ⬜ |
| 76 | E06US006 | Classement intégral 1→N & profondeur | ⬜ |
| 77 | E03US007 | Contrainte séparation catégorie/blason | ⬜ |
| 78 | E09US005 | Classements PDF | ⬜ |
| 79 | E00US013 | Factoriser les briques d'UI partagées | ✅ *(remontée de J3, DETTE-004 résorbée)* |
| 80 | E01US016 | Définir l'identité visuelle du tournoi | ⬜ |
| 81 | E07US004 | Écran de salle : déroulé auto & pilotage | ⬜ |
| 82 | E07US005 | Vue tableaux/arbres live | ⬜ |
| 83 | E05US019 | Enregistrer une séquence comme modèle | ⬜ |
| — | E00US015 | Ossature de navigation admin (coquille) | ✅ *(fait en avance — ajout 18/07)* |

## J4 — Confort, richesse & robustesse — ⬜ **non commencé (0/8)**

| Seq | US | Titre | État |
|---|---|---|---|
| 84 | E02US007 | Importer un fichier inscript'arc | ⬜ |
| 85 | E01US011 | Presets de barèmes multi-phases | ⬜ |
| 86 | E01US012 | Gérer plusieurs gabarits | ⬜ |
| 87 | E03US010 | Générer / éditer le déroulé horaire | ⬜ |
| 88 | E09US007 | Déroulé horaire imprimable | ⬜ |
| 89 | E05US016 | Routing repêchage-réintégration (WA) | ⬜ |
| 90 | E11US006 | Restauration & arrêt propre | ⬜ |
| 91 | E10US006 | Modifier le mot de passe admin | ⬜ |

## Ajouts de l'entretien du 18/07/2026 — 🔶 **en cours (2/10)**

> Non renumérotés dans les jalons ci-dessus (séquence indicative, à insérer au bon rang). Cf.
> [`stories/README.md`](../stories/README.md) § « Ajouts » et ADR-0026/0027/0028.

| US | Titre | Jalon | État |
|---|---|---|---|
| E00US015 | Coquille de navigation admin | J3 | ✅ |
| E00US016 | Écrans admin : liste/fiche & référentiels | J3 | ⬜ *(définie en `stories/`, non implémentée)* |
| E01US017 | Cycle de vie enrichi (7 statuts) | J1 | ⬜ *(idem)* |
| E01US018 | Vocabulaire de score configurable | J1 | ⬜ *(idem)* |
| E01US019 | Capacité de cible non bornée | J1→J3 | ⬜ *(idem)* |
| E02US010 | Horaire de départ HH:MM obligatoire | J1 | ⬜ *(idem)* |
| E13US001 | Abstraction participant | J2 | ✅ *(livrée avant E05US005, ADR-0028)* |
| E13US002 | Composer les équipes d'un tournoi | J2 | ⬜ |
| E13US003 | Scoring d'équipe (politique injectable) | J2 | ⬜ |
| E13US004 | Placement, saisie & classement par équipe | J2→J3 | ⬜ |

## Ajout du 20/07/2026 — ✅ **livrée (1/1)**

> Issu de l'échange sur le modèle d'entrée de l'appli (une seule SPA, désormais **quatre** expériences).
> Cf. [`stories/E00-socle.md`](../stories/E00-socle.md) § E00US017 et [ADR-0042](../docs/adr/0042-modele-d-entree-choix-de-role-explicite.md).
> Livrée le 21/07 : écran de choix 4 portes (Tablette / Public / Scoreur / Admin), choix persistant,
> le public ne peut pas escalader, échappatoire « Changer de rôle » ; front seul.

| US | Titre | Jalon | État |
|---|---|---|---|
| E00US017 | Écran d'accueil : choisir son appareil / rôle | J3 | ✅ |

## Ajout du 21/07/2026 — ⬜ **à planifier (0/2)**

> Issus du cadrage d'E08US002 : la tarification devient une **configuration du tournoi**
> ([ADR-0041](../docs/adr/0041-tarification-configuration-du-tournoi.md)). Ouverture **décidée**, pas
> codée — seule « somme des tarifs de l'archer » est implémentée. Cf. [`stories/E01-configuration.md`](../stories/E01-configuration.md).

| US | Titre | Jalon | État |
|---|---|---|---|
| E01US020 | Modèle de tarification injectable & sujet de facturation (archer/club) | à planifier | ⬜ *(définie en `stories/`, non implémentée ; sujet `club` sur `club_id`/ADR-0014, **pas** via E13)* |
| E01US021 | Tarification dégressive (option config, %/montant) | à planifier | ⬜ *(définie en `stories/`, non implémentée ; dépend d'E01US020)* |

## US caduque

| US | Titre | Motif |
|---|---|---|
| E10US004 | ~~Habiliter un scoreur sur plusieurs cibles~~ | Sans objet depuis `D-12`/`D-13` (scoreur itinérant). Conservée comme trace. |

---

## Légende

- ✅ mergé sur `main` · 🎯 prochaine US à prendre · 🔶 jalon en cours · ⬜ à faire
- *« fait en avance »* : US traitée avant son rang de séquence (dépendance ou opportunité).
- *« définie en `stories/`, non implémentée »* : le fichier de spec existe (créé à l'entretien du
  18/07) mais aucun code n'est livré — ne pas confondre présence en `stories/` et US faite.
