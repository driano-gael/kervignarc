# Cahier des charges fonctionnel — Kervignarc

**Solution logicielle de gestion de tournoi de tir à l'arc en salle (18 m)**

| | |
|---|---|
| **Version** | 0.3 (fonctionnel — cadrage FFTA) |
| **Date** | 14/07/2026 |
| **Statut** | À valider par le client |
| **Sources du besoin** | `charge.md` (recueil client), entretiens de cadrage du 08/07/2026, `Tableaux.xlsx` (exemple réel d'un tournoi à 120 participants), [`docs/referentiel-ffta.md`](docs/referentiel-ffta.md) (règlement FFTA déc. 2023) |
| **Nouveautés v0.3** | Confrontation au référentiel FFTA : catégories (EF-1.2), blason par phase (EF-1.4), presets FFTA vs club (EF-1.5), barème par division (EF-3.4), capacité de cible (EF-4.3), pavé de saisie (EF-5.2), RG-2/RG-4/RG-8. Q2 fermée, Q9 ouverte. |
| **Périmètre de ce document** | Fonctionnel uniquement. Le volet technique découlera de ce cahier des charges. |

---

## 1. Contexte et objectifs

### 1.1 Contexte
L'organisation d'un tournoi de tir à l'arc en salle sur cible à 18 m mobilise de nombreuses tâches manuelles : recueil des inscriptions, répartition des archers sur les cibles, saisie et cumul des scores, gestion des duels et tableaux de placement, calcul des classements et suivi des paiements. Ces opérations sont chronophages, sources d'erreurs et difficiles à suivre en temps réel le jour de l'événement.

Le classeur `Tableaux.xlsx` illustre la complexité réelle : un tournoi à 120 participants y est décrit à la main avec un déroulé horaire, un plan de 30 cibles, un tableau principal à élimination (matchs M1→M484), des repêchages « Lucky Loser », des tableaux de placement classant **tous** les archers, et une grande finale en *Big Shoot Off*. La solution doit permettre de produire ce type de tournoi — et d'autres formats — **sans ressaisie manuelle**.

### 1.2 Objectif de la solution
Fournir une application permettant d'**organiser et de piloter de bout en bout un tournoi de tir à l'arc en salle**, depuis les inscriptions jusqu'aux classements finaux, avec un **moteur de tournoi configurable** (enchaînement libre de phases), la saisie des scores en temps réel sur tablettes et l'affichage public des résultats.

### 1.3 Principe directeur
> **Ne pas coder un format de tournoi figé, mais un moteur permettant de composer n'importe quel format** comme une séquence de phases (qualification, barrage, tableau principal, repêchage, tournoi des perdants, tableaux de placement, finale, Big Shoot Off, podium…), chaque phase ayant ses propres règles de peuplement, de scoring et de progression.

### 1.4 Objectifs mesurables (cibles à confirmer)
- Réduire le placement des archers (aujourd'hui manuel) à une opération automatique ajustable en quelques minutes.
- Permettre la saisie des scores en temps réel sur ~30 tablettes simultanées.
- Produire déroulé, plans de cibles, tableaux et classements complets sans ressaisie.
- Fonctionner **sans connexion internet**, en réseau local (gymnase).

---

## 2. Périmètre

### 2.1 Dans le périmètre
- Gestion de tournois **officiels et non officiels**, en configuration libre (sur-ensemble paramétrable des règles FFTA/WA salle).
- Discipline : **tir en salle à 18 m** uniquement.
- Moteur de phases configurable, inscriptions, placement, saisie de scores, tableaux et repêchages, classement intégral, suivi des paiements, exports.

### 2.2 Hors périmètre (à ce stade)
- Autres disciplines / distances (extérieur, 3D, campagne).
- ~~**Épreuves par équipes** (matchs à 3 archers, équipes mixtes) — non gérées par l'application~~ → **entrées au périmètre MVP le 18/07/2026** ([ADR-0028](docs/adr/0028-epreuves-par-equipes-participant.md), [EPIC-13](epics/EPIC-13-equipes.md)). Documentées au [référentiel FFTA](docs/referentiel-ffta.md) §6.3/§7. La précaution du cadrage **paie** : le moteur oppose des *participants* (archer **ou** équipe, `MATCH.participant_A/B`, cf. CDC technique §5), donc l'ajout est une **réalisation**, pas une refonte.
- Paiement en ligne / transactions bancaires (seul le **suivi** est prévu).
- Gestion multi-tournois simultanés sur un même serveur (à confirmer).
- Application mobile native (la solution est une web app / PWA).

### 2.3 Rapport au règlement FFTA

> **Le règlement n'est jamais une contrainte, toujours un template.** L'application pré-charge des catégories, blasons et barèmes conformes à la FFTA, et **tout reste modifiable et supprimable** par l'administrateur. L'app ne vérifie pas la conformité d'un tournoi et ne l'impose pas : elle la rend *facile par défaut*. C'est la lecture opérationnelle du « sur-ensemble paramétrable des règles FFTA/WA salle » du §2.1 (cf. RG-8).

---

## 3. Acteurs et rôles

| Rôle | Description | Droits principaux |
|---|---|---|
| **Administrateur / Organisateur** | Prépare et pilote le tournoi | Accès total : configuration, moteur de phases, inscriptions, placement, validation, exports, gestion des utilisateurs |
| **Scoreur** | Responsable d'une cible | Saisie **et validation** des scores des archers de sa cible |
| **Archer** | Participant | Saisie de ses propres scores (mode alternatif), consultation de ses résultats |
| **Public / Spectateur** | Accompagnants, autres archers | Consultation seule des classements, tableaux et placements |

> **Hypothèse H1** — Sur une tablette partagée par une cible, le mode courant est « scoreur » (une personne saisit pour les 4 archers). Le mode « archer saisit ses propres scores » est un mode alternatif à confirmer.

---

## 4. Vue d'ensemble fonctionnelle

La solution s'articule autour de 9 modules :

1. **M1 — Configuration du tournoi** (catégories, blasons, gabarits de salle, presets de barèmes)
2. **M2 — Inscriptions** (saisie manuelle + import)
3. **M3 — Moteur de phases** *(cœur du produit)* : composition de la séquence de phases
4. **M4 — Placement des archers & plan de cibles**
5. **M5 — Saisie des scores** (tablettes, temps réel, tous types de phases)
6. **M6 — Tableaux, repêchages & progression** (constructeur de tableau, Lucky Loser, placement)
7. **M7 — Classement & affichage public** (classement intégral 1→N, écran projeté + mobile)
8. **M8 — Paiement** (suivi des montants)
9. **M9 — Exports & documents** (déroulé, plans, feuilles de marque, classements)

---

## 5. Exigences fonctionnelles détaillées

### M1 — Configuration du tournoi

| ID | Exigence |
|---|---|
| EF-1.1 | Créer un tournoi : nom, date, lieu, type officiel/non officiel. Le type est **informatif** (cf. RG-4). |
| EF-1.2 | Gérer les **catégories**. Une catégorie est une **entité nommée** portant une **règle d'éligibilité** : une arme, **une ou plusieurs** tranches d'âge, un sexe. Elle n'est **pas** le triplet `arme × âge × sexe` : la FFTA regroupe (arc nu « U18 » = U15 + U18 ; arc nu « Scratch » = U21 + S1 + S2 + S3), et un même libellé d'âge n'a pas le même sens d'une arme à l'autre. Un archer doit tomber dans **une seule** catégorie du tournoi. |
| EF-1.3 | Gérer les **blasons** : chaque blason a un **nom**, une **taille** exprimée comme **fraction de place sur une cible** (ex. trispot), une **capacité**, et les **valeurs de score admises** (cf. EF-1.3b). |
| EF-1.3b | Un blason porte les **valeurs de score qu'il permet** : un triple 40 n'a pas les zones 5 → 1 (minimum = 6), et le « 10 intérieur » des poulies diffère du 10 classique. Ces valeurs pilotent le pavé de saisie (EF-5.2). |
| EF-1.4 | Associer à une catégorie un **blason par défaut**, qu'une **phase peut surcharger** (ex. « toutes les finales sur triples verticaux »). Le blason réel dépend de la catégorie, de la phase et du choix de l'organisateur (unique vs triple) — un blason figé par catégorie ne suffit pas. Sert au placement et à la séparation par blason. |
| EF-1.5 | Gérer des **presets de barèmes** réutilisables et **modifiables**, en **deux jeux** livrés : **FFTA officiel** (qualif 60 flèches / 20 volées de 3, cumul ; duel en 5 sets, premier à 6 pts ; poulies au cumul ; barrage 1 flèche) et **format club** (qualif 15 flèches ; sets à 4 pts ; finales 5 volées / 6 pts ; Big Shoot Off). L'organisateur choisit un jeu et le surcharge librement. Cf. [référentiel FFTA §10.1](docs/referentiel-ffta.md). |
| EF-1.6 | **Gabarits de salle réutilisables** : plan type (nb de cibles, **capacité libre ≥ 1**, positions A/B/C/D) réutilisable et ajustable d'un tournoi à l'autre. |
| EF-1.7 | Paramétrer le **tarif par départ** (pour le suivi de paiement). |

> **Pré-réglages FFTA** — Les catégories, blasons et barèmes FFTA pré-chargés sont des **templates ordinaires** : une fois créés, ils se modifient et se suppriment comme n'importe quelle donnée saisie à la main (RG-8, §2.3).

### M2 — Inscriptions

| ID | Exigence |
|---|---|
| EF-2.1 | Saisie **manuelle** d'un archer : nom, prénom, club, catégorie, nombre de départs. |
| EF-2.2 | **Import** d'inscrits (export « inscript'arc » / XLS ou redirection URL). *(format exact à fournir — Q ouverte)* |
| EF-2.3 | Un archer peut avoir **plusieurs départs** ; facturation = tarif × nb départs. |
| EF-2.4 | Quota configurable : nombre **maximum** de participants par inscription / départ. |
| EF-2.5 | Modifier, supprimer, dédoublonner les inscrits ; référentiel des **clubs** réutilisable. |

### M3 — Moteur de phases *(cœur du produit)*

> Une **phase** est une étape du tournoi. Un tournoi est une **séquence ordonnée de phases**. La solution fournit un éditeur permettant de composer cette séquence librement et de la réutiliser comme modèle.

| ID | Exigence |
|---|---|
| EF-3.1 | **Composer une séquence de phases** (ajouter / ordonner / supprimer), ex. : `qualification → barrage → tableau principal → repêchage (Lucky Loser) → tournoi des perdants → tableaux de placement → finale → Big Shoot Off → podium`. |
| EF-3.2 | Choisir le **type** de chaque phase : *classement par cumul* (qualif), *barrage/shoot-off*, *tableau à élimination*, *repêchage*, *placement*, *finale*, *Big Shoot Off*. **Catalogue ouvert** — un type de phase est un **assemblage de politiques** (règle 2), pas une valeur figée ; d'autres formats (poules, handicap, suisse, king of the hill, ladder, finale spectacle…) sont des **cibles** livrables dès que leur règle est écrite (cf. [stories/E05](stories/E05-moteur-phases.md) — catalogue des formats). |
| EF-3.3 | Définir la **source de participants** de chaque phase à partir des sorties des phases précédentes : *tous les inscrits*, *rangs N→M d'un classement*, *gagnants d'un tour*, *perdants d'un tour donné* (Lucky Loser), *exempts*. |
| EF-3.4 | Associer à chaque phase un **preset de barème** (M1), surchargeable localement **et par arme**. Le barème se résout par le couple **(phase, arme)** : au même tour de duels, arc classique et arc nu tirent en sets (premier à 6) quand les arcs à poulies tirent au **cumul**, sans sets. Une phase porte donc un barème par défaut + d'éventuelles surcharges par arme. |
| EF-3.5 | Définir la **sortie** de chaque phase : classement produit et/ou flux « gagnants » / « perdants » réutilisables comme source d'une phase ultérieure. |
| EF-3.6 | **Enregistrer une séquence comme modèle** réutilisable (ex. « Format 120 WA placement intégral ») et l'appliquer à un nouveau tournoi. |
| EF-3.7 | Le moteur **calcule automatiquement** le nombre de tours, de matchs et l'enchaînement à partir de la séquence et de l'effectif. |
| EF-3.8 | **Contrôles de cohérence** : détecter une phase mal alimentée (source vide, rangs inexistants, effectif incompatible avec la structure) et alerter l'organisateur. |

> **Note de conception** — Le classeur `Tableaux.xlsx` est la matérialisation manuelle d'une telle séquence pour 120 archers ; le moteur doit pouvoir la reproduire et la généraliser à d'autres effectifs et formats.

### M4 — Placement des archers & plan de cibles

| ID | Exigence |
|---|---|
| EF-4.1 | **Placement automatique** des archers sur les cibles selon les contraintes ci-dessous, à partir du **gabarit de salle** (M1). |
| EF-4.2 | **Ajustement manuel** par glisser-déposer après placement automatique. |
| EF-4.3 | Contrainte : **capacité cible** = nombre d'archers admis, **libre (≥ 1)**, selon la taille des blasons. Les cas courants sont 1, 2 et 4, mais la FFTA décrit aussi une configuration à **3 triples verticaux** — la capacité n'est donc pas une énumération fermée. |
| EF-4.4 | Contrainte : **fraction de place** — somme des blasons d'une cible ≤ capacité. |
| EF-4.4b | Contrainte : **hauteur de centre**. Les archers d'une même butte doivent tirer à la même hauteur de centre — la FFTA impose 130 cm en général, mais **110 cm** pour le 80 cm des U11 : un U11 ne peut donc pas partager une butte avec des adultes. Cette contrainte n'est **pas** réductible à la fraction de place. *(livrée en E03US001 : la hauteur vit sur la catégorie — `CATEGORIE.hauteur_cm` —, [ADR-0022](docs/adr/0022-hauteur-de-centre-sur-la-categorie.md), contrainte de placement de 1er rang)* |
| EF-4.5 | Contrainte : **au moins 2 clubs différents** par cible lorsque c'est possible. |
| EF-4.6 | Contrainte (officiel) : **séparation par catégorie/blason** sur une même cible. |
| EF-4.7 | Chaque archer se voit attribuer **cible + position (A/B/C/D) + départ**. |
| EF-4.8 | **Placement des duellistes côte à côte** dans la mesure du possible lors des phases de tableau. |
| EF-4.9 | Produire le **plan de cibles** par phase/tour (qui tire où), à la manière de l'onglet `PLAN DE CIBLE`. |
| EF-4.10 | Produire un **déroulé horaire** de la journée croisant phases, tours et matchs. *(génération auto vs saisie manuelle — Q ouverte)* |

> **Règle de priorité (à confirmer)** — En cas de conflit entre contraintes, hypothèse d'ordre : capacité > catégorie/blason > mixité club.

### M5 — Saisie des scores

| ID | Exigence |
|---|---|
| EF-5.1 | Saisie sur **tablettes/smartphones** (~30 appareils), chaque appareil rattaché à une cible. |
| EF-5.2 | Saisie **en temps réel**, volée par volée, adaptée au **barème de la phase en cours** (cumul, sets, shoot-off, BSO) **et au blason tiré**. Les valeurs proposées au pavé de saisie viennent du **blason** (EF-1.3b), pas du barème : sur un triple 40, les touches 5 → 1 n'existent pas. |
| EF-5.2b | Le **marquage** est configurable : le format club marque volée par volée, la FFTA établit les scores **toutes les 2 volées** de 3 flèches (art. B.6.1.2). |
| EF-5.3 | Le **scoreur valide** les scores d'une volée/set ; verrouillage après validation. |
| EF-5.4 | **Cumul / calcul automatique** selon le type de phase (total qualif, points de set, vainqueur du match). |
| EF-5.5 | Fonctionnement **tolérant à la perte de réseau** (wifi local sans internet, PWA) ; synchronisation à la reconnexion. |
| EF-5.6 | Correction d'un score validé par un rôle habilité, avec **traçabilité**. |
| EF-5.7 | Gestion des cas particuliers : abandon, disqualification, **égalité → barrage/shoot-off** déclenché selon la séquence. |

### M6 — Tableaux, repêchages & progression

| ID | Exigence |
|---|---|
| EF-6.1 | **Constructeur de tableau libre** : l'organisateur choisit qui entre (tous les inscrits façon WA / top N / plage de rangs), le **seeding** (têtes de série depuis le classement de qualif) et les **exempts (byes)**. |
| EF-6.2 | Génération automatique de l'**arbre** (numéros de matchs, tours) — cf. `TABLEAU 1 OK`. |
| EF-6.3 | **Progression automatique** : le gagnant d'un match avance ; le perdant est routé selon la règle de la phase (élimination, repêchage, placement). |
| EF-6.4 | **Repêchage Lucky Loser** : reversement des perdants d'un tour donné dans un tableau de repêchage. |
| EF-6.5 | **Tableaux de placement** : sous-tableaux classant les rangs intermédiaires (ex. 17-24, 25-32…) — cf. `TABLEAU 2 OK`. |
| EF-6.6 | **Big Shoot Off** en grande finale (barème dédié). ⚠️ **Règle non spécifiée — cf. Q9** : format club sans équivalent FFTA, non implémentable tant que le club n'a pas fourni sa règle. |
| EF-6.7 | Édition manuelle ponctuelle d'un tableau par l'organisateur (correction, forfait) avec recalcul de la progression. |

### M7 — Classement & affichage public

| ID | Exigence |
|---|---|
| EF-7.1 | **Classement intégral 1→N** : chaque archer obtient un rang final, alimenté par les tableaux principaux, de placement et les repêchages. |
| EF-7.2 | Classements **par catégorie** et intermédiaires (par phase). |
| EF-7.3 | **Temps réel** : mise à jour des scores, tableaux et classements quasi immédiate. |
| EF-7.4 | **Écran projeté** dans la salle (classement / tableaux live). |
| EF-7.5 | **Consultation mobile/web** par archers et public (réseau local). |
| EF-7.6 | Affichage des **plans de cibles** et du déroulé. |

### M8 — Paiement (suivi)

| ID | Exigence |
|---|---|
| EF-8.1 | Calcul du **montant dû** = résultat d'une **politique de tarification** configurée par tournoi ([ADR-0041](docs/adr/0041-tarification-configuration-du-tournoi.md)) : sujet facturé **archer** ou **club**, dégressif éventuel. *Stratégie par défaut et seule implémentée : somme des tarifs des départs d'un archer ([ADR-0017](docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md)).* |
| EF-8.2 | Suivi du **règlement** : montant réglé (**partiel** possible → reste dû), donc statut non réglé / partiel / réglé (pas de transaction en ligne). |
| EF-8.3 | Vue consolidée **par archer** et **par club** (dû / réglé / reste), règlement groupé par club. |

### M9 — Exports & documents

| ID | Exigence |
|---|---|
| EF-9.1 | **Déroulé horaire** de la journée (phases, tours, matchs). |
| EF-9.2 | **Plans de cibles** par phase/tour (placement à afficher à l'entrée). |
| EF-9.3 | **Feuilles de marque** par cible/archer. |
| EF-9.4 | **Tableaux** (principal, repêchages, placement) imprimables. |
| EF-9.5 | **Classements PDF** par catégorie et classement intégral 1→N. |
| EF-9.6 | **Listes club & paiement** : nom/prénom, n° de départ, nb de départs, montant dû, payé/non payé. |

---

## 6. Règles de gestion transverses

- **RG-1** — Un tournoi = séquence ordonnée de phases ; chaque phase consomme des sorties des phases précédentes.
- **RG-2** — Un blason occupe une **fraction** de la capacité d'une cible ; somme des fractions ≤ capacité. La capacité est **libre (≥ 1)**, pas une énumération 1/2/4. La fraction ne dit **rien** de la hauteur du blason, qui est une contrainte distincte (EF-4.4b).
- **RG-3** — Mixité club : minimum **2 clubs par cible** lorsque c'est possible.
- **RG-4** — Le **cloisonnement par catégorie/blason** sur une cible est une **contrainte de placement activable**, indépendante du type de tournoi. Le drapeau officiel/non officiel ne verrouille rien : il oriente les templates proposés à la création et figure sur les exports (cf. §2.3, RG-8).
- **RG-5** — Un score validé est verrouillé ; toute correction est tracée.
- **RG-6** — Les barèmes proviennent de **presets modifiables** ; une surcharge locale à une phase n'altère pas le preset.
- **RG-7** — Le classement final couvre **tous** les archers (1→N).
- **RG-8** — **Tout pré-réglage FFTA est un template surchargeable.** Aucune donnée pré-chargée depuis le référentiel n'est en lecture seule ni protégée : une fois créée, elle se modifie et se supprime comme une donnée saisie à la main. L'application n'impose ni ne vérifie la conformité au règlement.

---

## 7. Exigences non-fonctionnelles à impact fonctionnel

> *(Le détail technique fera l'objet d'un document dédié ; on ne fixe ici que ce qui conditionne le fonctionnel.)*

| ID | Exigence |
|---|---|
| ENF-1 | **Réseau local sans internet** (serveur local dans le gymnase). |
| ENF-2 | **Temps réel** : scores, tableaux et classements visibles quasi immédiatement. |
| ENF-3 | **Tolérance hors-ligne** sur les tablettes (PWA), synchronisation à la reconnexion. |
| ENF-4 | **Volumétrie de référence** : tournoi à 120 archers / 30 cibles (exemple du classeur) ; plafond réel à confirmer. |
| ENF-5 | **Ergonomie tactile** : saisie sur tablette rapide, gros boutons, peu de clics. |
| ENF-6 | **Robustesse du moteur** : cohérence garantie de la progression même en cas de correction/forfait en cours d'épreuve. |
| ENF-7 | **Recette avec parc réduit** : l'app **poste de cible** (saisie) doit être **vérifiable fonctionnellement avec une seule tablette physique**, alors qu'elle en vise ~30 en production. Le comportement **multi-poste** (rattachements distincts, diffusion live, supervision) doit être exerçable **sans 30 appareils**. *(Contrainte matérielle de dev/recette, ajoutée le 18/07/2026 — mise en œuvre : `guide-architecture.md` §9.)* |

---

## 8. Parcours utilisateurs types

1. **Préparation** — L'admin crée le tournoi, choisit un gabarit de salle, **compose (ou réutilise) la séquence de phases**, importe/saisit les inscrits, lance le placement puis l'ajuste, imprime déroulé, plans de cibles et feuilles de marque.
2. **Qualifications** — Chaque cible saisit ses volées ; classement de qualif live sur écran et mobile ; barrage automatique en cas d'égalité.
3. **Passage aux tableaux** — Le moteur peuple le tableau principal (selon la règle choisie : tous / top N / rangs), génère l'arbre, le seeding et les exempts.
4. **Duels, repêchages, placement** — Saisie des sets ; progression automatique ; Lucky Loser et tableaux de placement alimentés selon la séquence ; Big Shoot Off en grande finale.
5. **Clôture** — Classement intégral 1→N, exports PDF, listes club/paiement, archivage.

---

## 9. Périmètre par lot (indicatif, à arbitrer)

| Lot | Contenu | Notes |
|---|---|---|
| **MVP** | M1, M2 (manuel), M4, M5, M7 (mobile), M8, M9 (déroulé + plans + feuilles) ; **M3 avec séquence simple** (qualif → tableau principal → podium) | Un tournoi complet mono-tableau |
| **MVP+1** | M2 (import XLS), **M3 complet** (repêchage, tournoi des perdants, placement), M6 (Lucky Loser + placement + BSO), M7 (classement intégral 1→N), M9 (tableaux + classements PDF), écran projeté | Format riche « type 120 » |
| **Ultérieur** | Modèles de séquences partagés, modes de saisie alternatifs, multi-tournois, statistiques | À prioriser |

---

## 10. Hypothèses et questions ouvertes restantes

| # | Sujet | À obtenir |
|---|---|---|
| Q1 | **Format du fichier d'import** « inscript'arc » | Un exemple XLS + description des colonnes |
| ~~Q2~~ | ~~**Règles de départage / barrage**~~ | ✅ **Fermée le 14/07/2026** — qualif : plus grand nombre de **10**, puis de **9** (spécifique 18 m). Barrage : **1 flèche au plus haut score**, puis **au plus près du centre** si l'égalité persiste ; les 10/9 ne sont pas recomptés. Cf. [référentiel FFTA §8](docs/referentiel-ffta.md). |
| Q3 | **Mécanique précise du Lucky Loser** et des tableaux de placement | 2-3 cas réels formalisés (quel tour reverse vers quel tableau) |
| Q4 | **Génération des horaires** | Auto (durées × tours) ou saisie manuelle par l'organisateur ? |
| Q5 | **Volumétrie max** | Plafond nb archers / cibles / départs au-delà de 120 |
| Q6 | **Priorité des contraintes de placement** en cas de conflit (cf. M4) | Ordre de priorité souhaité |
| Q7 | **Mode de saisie par défaut** sur tablette (scoreur vs archer, cf. H1) | Décision |
| Q8 | **Récompenses / podiums** | Gestion de l'attribution par catégorie ? |
| **Q9** | 🔴 **Règle du Big Shoot Off** — **bloquante** | Le BSO est cité comme barème de la grande finale (EF-1.5, EF-3.2, EF-5.2, M6) mais **n'existe pas au règlement FFTA** et n'est défini **dans aucun document du projet**. Il est donc **non implémentable en l'état**. À obtenir du club : nombre de flèches, critère de victoire, départage. |

---

*Document produit à partir de `charge.md` et `Tableaux.xlsx`. À relire et amender avec le client avant chiffrage et rédaction du volet technique.*
