# Référentiel FFTA — Tir à 18 m (salle)

- **Version** : 1.1
- **Date** : 2026-07-14 *(v1.1 : §10 réécrit après confrontation au CDC — arbitrages du 14/07 ; §10.1 « formats club » ajouté ; contradictions internes du §3 et du §10 levées)*
- **Source** : *Règlements sportifs et Arbitrage de la FFTA, édition décembre 2023* — chapitre **II.2 « Le Tir à 18 m »** et **Chapitre I « Les Règlements Généraux »**. Texte intégral archivé dans `docs/sources/ffta/reglement-sportif-ffta-2023_texte-integral.txt`.
- **But** : source de vérité des règles (catégories, blasons, barèmes, départage, formats) qui alimentent la configuration des tournois (EPIC-01) et le moteur de phases/placement (EPIC-03, EPIC-05). Sert aussi de base documentaire générale sur la discipline.

> **Légende de statut** — chaque valeur est étiquetée :
> - `✅ FFTA` : extraite du règlement officiel déc. 2023, **avec l'article cité** entre parenthèses.
> - `❓ à confirmer` : valeur d'usage ou correspondance non écrite noir sur blanc dans ce règlement (à valider avant d'en coder une valeur numérique).
>
> Les articles cités sans préfixe de chapitre appartiennent au chapitre **II.2 Le Tir à 18 m** ; les renvois au Tir Extérieur ou aux Règlements Généraux sont explicités.

---

## 1. Divisions (armes)

La FFTA reconnaît pour le Tir à 18 m trois divisions concourant séparément (art. A.6.2) :

| Division | Nom courant | Équipement de référence | Statut |
|---|---|---|---|
| **Arc Classique** | recurve | art. B.3.1 | ✅ FFTA (A.6.2) |
| **Arc Nu** | barebow | art. B.3.2 / II.3.B.3 | ✅ FFTA (A.6.2) |
| **Arc à Poulies** | compound | art. B.3.3 | ✅ FFTA (A.6.2) |

Divisions **reconnues mais non ouvertes au Championnat de France**, rattachées à une division principale pour le classement (art. A.7.1.2) :
- **Arcs droits (longbow)** → classés en **Arc Nu**.
- **Arcs chasse** → classés en **Arc Nu**.
- **Arcs à poulies nus** → classés en **Arc à Poulies**.

---

## 2. Catégories d'âge

Catégories reconnues, définies par l'**âge atteint dans l'année civile** de la licence (art. C.3.1 des Règlements Généraux). La saison court du 01/09 au 31/08 suivant.

| Code | Âge dans l'année civile | Correspondance usuelle (héritée) | Statut |
|---|---|---|---|
| **U11** | 10 ans et moins | Poussin | ✅ FFTA (C.3.1) — corresp. `❓` |
| **U13** | 11 & 12 ans | Benjamin | ✅ FFTA (C.3.1) — corresp. `❓` |
| **U15** | 13 & 14 ans | Minime | ✅ FFTA (C.3.1) — corresp. `❓` |
| **U18** | 15, 16 & 17 ans | Cadet | ✅ FFTA (C.3.1) — corresp. `❓` |
| **U21** | 18, 19 & 20 ans | Junior | ✅ FFTA (C.3.1) — corresp. `❓` |
| **Seniors 1 (S1)** | 21 à 39 ans | Senior | ✅ FFTA (C.3.1) — corresp. `❓` |
| **Seniors 2 (S2)** | 40 à 59 ans | Vétéran | ✅ FFTA (C.3.1) — corresp. `❓` |
| **Seniors 3 (S3)** | 60 ans et + | Super Vétéran | ✅ FFTA (C.3.1) — corresp. `❓` |

> Les libellés « Poussin → Super Vétéran » sont la nomenclature historique ; le système officiel en vigueur est **U11…U21 + Seniors 1/2/3**. La correspondance ci-dessus est l'usage courant, **non écrite dans le règlement 2023** (`❓`).
>
> **U11** : admis en compétition officielle 18 m à partir de 8 ans, arc classique uniquement, puissance ≤ 18 livres (art. C.3.1.1). Un surclassement en U13 à 10 ans est possible sous certificat médical. Aucun titre/record national U11.

Chaque catégorie d'âge se décline par **sexe** (Hommes / Femmes).

---

## 3. Catégories officielles par division (classements 18 m)

Catégories utilisées pour les classements de compétition (art. A.7.1.2), et **blason associé à 18 m** (art. A.7.1.3) :

### Arc Classique
| Catégories d'âge | Blason à 18 m | Statut |
|---|---|---|
| U11 | **80 cm** (centre à 1,10 m — art. C.3.1.1) | ✅ FFTA (A.7.1.3) |
| U13, U15 | **60 cm** | ✅ FFTA (A.7.1.3) |
| U18, U21, S1, S2, S3 | **40 cm** | ✅ FFTA (A.7.1.3) |

Blasons uniques **ou** triples (verticaux ou triangulaires), au choix de l'organisateur (art. A.7.1.3).

### Arc à Poulies
| Catégories d'âge | Blason à 18 m | Statut |
|---|---|---|
| U15\*, U18, U21, S1, S2, S3 | **40 cm — triples** | ✅ FFTA (A.7.1.3) |

\* U15 poulies ouvert à partir de la saison 2024/2025 (art. A.7.1.2). Les arcs à poulies **tirent toujours sur triples** (art. A.7.1.3).

### Arc Nu
| Catégories | Blason à 18 m | Statut |
|---|---|---|
| U18 (H/F) — regroupe U15, U18 | **60 cm** | ✅ FFTA (A.7.1.2 / A.7.1.3) |
| Scratch (H/F) — U21, S1, S2, S3 | **40 cm** | ✅ FFTA (A.7.1.2 / A.7.1.3) |

> **Épreuve de qualification (18 m)** : **60 flèches** (art. A.7.3). Le **blason** est celui de la ligne de la catégorie dans les tableaux ci-dessus : 40 cm (ou triple 40) pour la majorité des catégories, mais **80 cm** en U11 classique, **60 cm** en U13/U15 classique et en U18 arc nu. La formule « 40 cm pour toutes les catégories », qu'on lit souvent, décrit le **cas adulte** et non une règle générale — elle ne prime pas sur le blason de la ligne.

---

## 4. Blasons 18 m

### 4.1 Types (art. B.2.1)
Dix types de blasons homologués (fabricant sous licence World Archery) :
- blason **60 cm** ; triple triangulaire 60 cm ; triple vertical 60 cm ;
- blason **40 cm** ; triple triangulaire 40 cm ; triple vertical 40 cm ;
- triple triangulaire 40 cm **arcs classiques/nus** ; triple triangulaire 40 cm **arcs à poulies** ;
- triple vertical 40 cm **arcs classiques/nus** ; triple vertical 40 cm **arcs à poulies**.

À 25 m on emploie le blason **60 cm**, à 18 m le blason **40 cm** (art. B.2.2).

### 4.2 Structure et zones de score (art. B.2.1.1)
Cinq zones de couleur concentriques, du centre vers l'extérieur : **or (jaune), rouge, bleu clair, noir, blanc**. Chaque couleur est divisée en deux → **10 zones de score**. Largeur d'un anneau (mesurée du centre) : **3 cm** (blason 60 cm), **2 cm** (blason 40 cm). Centre = « mouche / croix centrale » (X).

Valeur des scores et couleurs (art. B.2.1.2, renvoi au Tir Extérieur — table vérifiée) :

| Couleur | Zones (score) | Pantone |
|---|---|---|
| Or (jaune) | 10 (X au centre), 9 | 107 U |
| Rouge | 8, 7 | 032 U |
| Bleu clair | 6, 5 | 306 U |
| Noir | 4, 3 | Process Black |
| Blanc | 2, 1 | — (blanc) |
| Hors blanc | M (manqué) | — |

Statut : `✅ FFTA` (structure B.2.1.1 + barème couleur→valeur et Pantone de l'art. B.2.1.2 du Tir Extérieur, relu). Le tableau des diamètres B.2.1.3 du chapitre extérieur reproduit à l'identique la colonne 18 m du §4.3 (Ø 60/40 cm), ce qui corrobore ces valeurs.

### 4.3 Diamètres des zones (art. B.2.1.3)
Diamètres en **cm** de chaque cercle, mesurés depuis le centre. Tolérance ± 1 mm pour les zones 10/9/8, ± 2 mm pour les autres.

| Zone (score) | Ø blason 60 cm | Ø blason 40 cm | Tolérance |
|---|---|---|---|
| 10 (poulies, « 10 intérieur ») | 3 cm | 2 cm | ± 1 mm |
| 10 (classique) | 6 cm | 4 cm | ± 1 mm |
| 9 | 12 cm | 8 cm | ± 1 mm |
| 8 | 18 cm | 12 cm | ± 1 mm |
| 7 | 24 cm | 16 cm | ± 2 mm |
| 6 | 30 cm | 20 cm | ± 2 mm |
| 5 | 36 cm | 24 cm | ± 2 mm |
| 4 | 42 cm | 28 cm | ± 2 mm |
| 3 | 48 cm | 32 cm | ± 2 mm |
| 2 | 54 cm | 36 cm | ± 2 mm |
| 1 | 60 cm | 40 cm | ± 2 mm |

Statut : `✅ FFTA (B.2.1.3)`. Le « 10 intérieur » compound vaut **3 cm** (Ø, blason 60) / **2 cm** (blason 40) — art. B.2.1.1.

### 4.4 Blasons triples (tri-spots) 40 cm (art. B.2.1.1)
- Trois petits blasons sur fond blanc, disposés en **triangle** ou en **colonne verticale**.
- **Mêmes dimensions que le 40 cm mais sans les zones 5 → 1** : la zone la plus basse est le **bleu clair = 6**.
- Taille du cercle du 10 : **40 mm** (Arc Classique / Arc Nu), **20 mm** (Arc à Poulies), version « combinée » = deux cercles de 10.
- Distance entre centres des jaunes : ≈ **22 cm** (triples 40 cm), ≈ 32 cm (triples 60 cm).

> **Championnats de France** : qualification sur **triples verticaux** (classique et poulies) et blason unique pour l'arc nu ; **toutes les phases finales sur triples verticaux** (art. A.7.1.3, A.7.6, A.7.7). Duels et matchs par équipe : triples verticaux 40 cm.

---

## 5. Agencement des cibles (art. B.2.2)

Hauteurs mesurées du **sol au centre de l'or**. Tolérance de positionnement : **± 2 cm** (art. B.2.2.1.4).

| Configuration | Hauteur du centre | Espacement min. | Statut |
|---|---|---|---|
| Blason simple / paire, ou triple vertical | **130 cm** (centre du blason unique / spot du milieu) | 10 cm entre zones marquantes (2 cm pour blasons 60 cm) | ✅ FFTA (B.2.2.1.1) |
| **4 blasons** 40 cm simples ou triples triangulaires | ligne haute ≤ **162 cm**, ligne basse ≥ **100 cm** | 10 cm entre zones marquantes de même hauteur ; un blason par quart de butte | ✅ FFTA (B.2.2.1.2) |
| 3 ou 4 triples **verticaux** 40 cm | ligne du milieu à **130 cm** | 10 cm (colonnes 2/3), ≤ 2 cm (colonnes 1-2 et 3-4) | ✅ FFTA (B.2.2.1.3) |
| 2 triples verticaux (individuel & équipes) | 130 cm | **25 cm** entre colonnes | ✅ FFTA (B.2.2.1.3) |

Aux **éliminatoires et finales**, les triples 40 cm sont placés **par paire sur chaque cible** (art. B.2.2.1). Cibles numérotées (n° ≥ 15 cm, noir/jaune alterné — art. B.2.2.3.2).

**Terrain** (art. B.1) : ligne d'attente ≥ 3 m derrière la ligne de tir ; ligne des 3 m devant ; couloirs ≥ 160 cm pour 2 archers (min. 80 cm/archer, toléré 70 cm) ; tolérance de distance 18 m/25 m = ± 10 cm.

---

## 6. Format des épreuves

### 6.1 Qualification (art. A.7.3)
- **60 flèches** à 18 m sur blason 40 cm (ou triple 40 cm), par volées de 3 flèches (**20 volées**).
- **Établissement des scores** toutes les **2 volées de 3 flèches** (ou toutes les volées de 6) — art. B.6.1.2.
- Classement par **cumul des points**.
- Épreuve combinée = 2 × 25 m + 2 × 18 m (art. A.7.4).

### 6.2 Duels individuels (phases éliminatoires & finales, art. A.7.5)
Éliminatoire : **32 meilleurs** placés selon la qualification ; finale : **8 meilleurs** issus de l'éliminatoire. Tir sur triples verticaux 40 cm.

| Division | Format d'un duel | Victoire | Statut |
|---|---|---|---|
| **Arc Classique / Arc Nu** | meilleur des **5 sets de 3 flèches** (système de sets) | premier à **6 points de set** | ✅ FFTA (A.7.5.1, B.6.1.4.1) |
| **Arc à Poulies** | **5 volées de 3 flèches**, **score cumulé** (pas de sets) | plus haut cumul | ✅ FFTA (A.7.5.2, B.6.1.4.2) |

### 6.3 Épreuves par équipes (3 archers, art. A.7.5)
Éliminatoire : 16 équipes/sexe placées selon la qualification ; finale : 4 équipes/sexe. Volée tirée en **2 minutes**.

| Division | Format d'un match | Victoire | Statut |
|---|---|---|---|
| **Arc Classique** | meilleur des **4 sets de 6 flèches** (2/archer) | premier à **5 points de set** | ✅ FFTA (A.7.5.1, B.6.1.5.1) |
| **Arc à Poulies** | **4 volées de 6 flèches** (2/archer), **cumulé** | plus haut cumul | ✅ FFTA (A.7.5.2, B.6.1.5.2) |

---

## 7. Barème du système de sets (art. B.6.1.4 / B.6.1.5)

Applicable aux duels/matchs **Arc Classique et Arc Nu** (les poulies tirent au cumul, sans sets).

- **Individuel** : score max 30 pts/set (3 flèches). Le vainqueur de la volée marque **2 points de set**, le perdant **0** ; **égalité → 1 point chacun**. Premier à **6 points de set** (duel en 5 sets) = vainqueur.
- **Équipe** : score max **60 pts/set** (6 flèches), **40** en équipe mixte (2 flèches/archer). Même règle 2 / 1-1 / 0. Premier à **5 points de set** (match en 4 sets) = vainqueur.
- **Égalité de sets** (5-5 en individuel, 4-4 en équipe) → **tir de barrage** ; le vainqueur du barrage marque **1 point de set supplémentaire** (score final 6-5 ou 5-4).

---

## 8. Départage des égalités

### 8.1 Classement de qualification (art. C.3 / réf. ligne « Tir à 18 m »)
En cas d'égalité de total : départage au **plus grand nombre de 10**, puis de **9** (spécifique 18 m). `✅ FFTA` (mention « le nombre de 10 et de 9 (Tir à 18 m) »).

### 8.2 Duels & matchs — tir de barrage (art. B.6.5.2)
- **Individuel** : **1 flèche**, le plus haut score gagne. Si l'égalité subsiste, on **répète au plus près du centre** jusqu'à résolution. Barrage tiré sur la **cible centrale du triple vertical** (B.6.5.2.3).
- **Équipe** : une volée de **3 flèches (1 par archer)**, plus haut total gagne ; répété si nécessaire (B.6.5.2.2). Blason triple vertical installé horizontalement, 1 butte par équipe (B.6.5.2.3).
- Le barrage **ne prend pas en compte** le nombre de 10/9 (B.6.5.2). Un archer absent au barrage annoncé est déclaré perdant (B.6.5.2.4).

---

## 9. Contrôle du temps (art. B.2.3, B.5)

- Signaux **sonores** (sifflet) + **visuels** ; en cas de discordance, le **son prévaut** (B.2.3.2).
- **Feux** verticaux rouge / jaune / vert (rouge en haut), une seule couleur à la fois (B.2.3.3).
- **Chronomètres digitaux** en décompte, chiffres ≥ 20 cm ; prioritaires sur les feux en cas de divergence (B.2.3.3).
- Contrôle manuel de secours : panneaux vert / jaune ≥ 120 × 80 cm ; **face jaune montrée à 30 s de la fin** (B.2.3.3).
- Volée par équipes : **2 minutes** (A.7.5) ; 20 s/flèche aux éliminatoires/finales par équipes des autres tournois (B.5.6.3).
- Duels : indicateurs d'ordre de tir (lumières vertes/rouges) pour le tir alterné (B.2.3.3, B.2.4.2).

---

## 10. Rattachement au projet

> Ces notes relient le référentiel réglementaire aux besoins applicatifs (cf. [[projet-kervignarc-scope]]). Elles ne font pas partie du règlement FFTA.

> **Principe directeur (arbitré le 2026-07-14)** — Le règlement FFTA n'entre jamais dans l'application comme une **contrainte** : il y entre comme un **template**. Tout ce qui est pré-chargé depuis ce référentiel (catégories, blasons, barèmes) reste **modifiable et supprimable** par l'administrateur. Un tournoi conforme FFTA est donc un tournoi dont l'admin n'a pas touché aux templates — l'application ne le vérifie pas et ne l'impose pas.

- **Catégories (EPIC-01 / E01US003-004)** : une catégorie **n'est pas** le triplet `division × âge × sexe`. C'est une **entité nommée** portant une **règle d'éligibilité** : une division, **une ou plusieurs** catégories d'âge, un sexe. Le §3 l'impose — l'arc nu regroupe U15+U18 dans une catégorie « U18 », et U21+S1+S2+S3 dans un « Scratch ». Un même libellé d'âge n'a donc pas le même sens d'une division à l'autre : « U18 » désigne une seule tranche en classique, **deux** en arc nu. Modéliser l'âge par une valeur unique rend ces deux cas indistinguables.
- **Blason d'une catégorie (E01US006)** : la catégorie porte un **blason par défaut** (§3), qu'une **phase peut surcharger**. Le blason réel dépend en effet de trois facteurs : la catégorie, la **phase** (les finales des Championnats de France se tirent toutes sur triples verticaux — A.7.6, A.7.7), et le **choix de l'organisateur** entre blason unique et triple (A.7.1.3) — sauf en poulies, toujours sur triples.
- **Blasons & saisie (EPIC-04)** : un blason ne se réduit pas à sa taille. Les **valeurs de score admises** en dépendent : un triple 40 n'a **pas les zones 5 → 1** (son minimum est 6, §4.4), et le « 10 intérieur » des poulies est un cercle plus petit que le 10 classique (§4.3). Le pavé de saisie de la tablette se déduit donc du **blason**, pas du barème de la phase.
- **Blasons & placement (EPIC-03)** : le paramètre qui pilote le placement n'est pas le nom commercial du blason mais la **fraction de cible** qu'il occupe (1 blason simple, paire, 4 blasons, ou triples verticaux par colonnes). La capacité d'une butte n'est pas bornée à 1/2/4 : le §5 décrit aussi une configuration à **3 triples verticaux**. Les **hauteurs** du §5 sont une contrainte à part entière, non réductible à une fraction : un U11 tire à **110 cm** de centre contre **130 cm** pour les autres, il ne peut donc pas partager une butte avec eux.
- **Barèmes & moteur de phases (EPIC-05 / E01US011)** : les formats du §6-7 deviennent des **presets modifiables**. Un barème ne se résout **pas** à partir de la seule phase : au même tour de duels, classique et arc nu tirent **en sets** (premier à 6) quand les poulies tirent **au cumul** (A.7.5.1 / A.7.5.2). La politique `scoring` se résout donc par le couple **(phase, division)**.
- **Départage (EPIC-06 / E04US013, E06US001/003)** : politique `tiebreak` — qualif au nombre de 10 **puis** de 9 (§8.1). Match nul → barrage d'**1 flèche au plus haut score** ; ce n'est **que si l'égalité persiste** qu'on départage au plus près du centre (§8.2). Les deux critères sont séquentiels, pas fusionnés. Le barrage ne recompte pas les 10/9.
- **Seeding / tableaux (ADR-0004, E05US005)** : effectif arrondi à la puissance de 2 (ex. 32/16 places pour les duels FFTA), placement selon le rang de qualification (« serpent »), exempts aux mieux classés — **décision projet** (`❓` côté FFTA, non normé dans ce chapitre).
- **Épreuves par équipes (§6.3, §7)** : documentées ici, **hors périmètre** applicatif. La porte reste ouverte : le moteur devra pouvoir opposer des participants qui ne sont pas des archers individuels (`MATCH.participant_A/B` plutôt que `archer_a/archer_b`).

---

### 10.1 Formats club (hors FFTA)

> ⚠️ Les valeurs pratiquées par le club (relevées dans `Tableaux.xlsx` et reprises telles quelles dans le CDC v0.2) **ne sont pas les valeurs FFTA**. Elles décrivent un format court non officiel, parfaitement légitime, mais qu'il ne faut pas présenter comme un « preset FFTA ».

| Sujet | Format club (`Tableaux.xlsx`) | FFTA officiel (ce référentiel) |
|---|---|---|
| Qualification | 5 volées de 3 = **15 flèches** | **60 flèches**, 20 volées de 3 (A.7.3) |
| Duel individuel | sets, premier à **4 pts** | sets, premier à **6 pts**, 5 sets (B.6.1.4.1) |
| ½ finales / finales | 5 volées de 3, 6 pts | *(format normal du duel — la FFTA ne distingue pas un « barème de finale »)* |
| Marquage | volée par volée | scores établis **toutes les 2 volées** de 3 (B.6.1.2) |
| Grande finale | **Big Shoot Off** | *(n'existe pas — voir §11)* |
| Structure | 120 archers, placement intégral 1→N | 32 à l'éliminatoire, 8 en finale (A.7.5) |

**Décision (2026-07-14)** — L'application livre **deux jeux de presets** : *FFTA officiel* et *format club*. L'organisateur choisit à la création ; les deux restent surchargeables (principe directeur du §10).

---

## 11. Points restés `❓ à confirmer`

- **Big Shoot Off** — 🔴 **bloquant**. Le CDC en fait le barème de la grande finale, mais le BSO **n'existe nulle part dans le règlement FFTA** : c'est un format club, et sa règle n'est écrite **dans aucun document du projet**. Impossible à implémenter en l'état. À obtenir auprès du club (nombre de flèches, départage, critère de victoire), puis à documenter en §10.1.
- **Correspondance** catégories historiques (Poussin…Super Vétéran) ↔ U11…S3 : usage courant, non écrit dans le règlement 2023.
- **Découpage exact des 60 flèches de qualification** en volées (20 × 3 retenu par usage + art. B.6.1.2) : à confirmer sur le mandat de l'organisateur.
- **Règles de seeding/exempts** : non normées dans le chapitre 18 m → décision projet.
- Un **fichier d'inscrits d'exemple** (format « inscript'arc ») reste à obtenir pour l'import.

> **Points levés le 2026-07-14** (ils ne sont plus des questions ouvertes) : le **départage** de qualification (nombre de 10 puis de 9) et le **barrage** (1 flèche au plus haut score, puis au plus près du centre) répondent à la Q2 du CDC fonctionnel et à une partie de la QT7 du CDC technique.

*Une fois ces points levés, le référentiel sert de source de vérité pour les presets de configuration.*
