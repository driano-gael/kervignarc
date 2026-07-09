# Formalisation — Mécanique de placement / « Lucky Loser »

**Annexe technique au moteur de phases (Kervignarc)**

| | |
|---|---|
| **Version** | 0.1 |
| **Date** | 08/07/2026 |
| **Source** | `Tableaux.xlsx`, onglets `PLAN DE CIBLE 120P OK`, `TABLEAU 1 OK`, `TABLEAU 2 OK` (tournoi réel à 120 archers) |
| **Objet** | Décrire précisément le format de tableau à **placement intégral** encodé dans le classeur, pour spécifier le moteur (risque R1 / QT7 du CDC technique) |

---

## 1. Nature du format : un tableau à placement intégral (cascade)

Le classeur n'encode **pas** un simple tableau à élimination + un tableau secondaire. Il encode un **format à placement intégral en cascade** :

> **Principe** — Tous les archers entrent dans un unique tableau à élimination directe. **Personne n'est éliminé** : le perdant d'un match ne rentre pas chez lui, il « descend » dans un tableau de placement **confiné à la plage de rangs qu'il peut encore atteindre**. Cette plage est **divisée par deux à chaque tour perdu**, jusqu'à ce qu'un **match terminal fixe le rang exact**. Résultat : **chaque archer obtient un rang unique de 1 à N**.

C'est le format qui produit les 484 matchs du tournoi 120 : ~4 matchs par archer en moyenne, car chacun continue de tirer après une défaite pour départager sa position finale.

> **Terminologie** — Dans le classeur, « **LUCKY LOSER 1** » désigne le **premier tableau de consolation** (celui des perdants des tours initiaux du principal), et « **TABLEAU x-y** » les tableaux de placement pour la plage de rangs `x..y`. ⚠️ Ici « Lucky Loser » ne signifie **pas** un repêchage qui *réintègre* le tableau principal (aucun archer battu ne revient disputer le titre) — c'est un **tableau de classement**. Décision (§7, Q1) : ce comportement est le **défaut**, mais le moteur doit aussi savoir faire un *vrai repêchage* réintégrant le principal — les deux sont deux configurations d'un même mécanisme de routage.

---

## 2. Le tableau principal (onglet TABLEAU 1)

- **Effectif → puissance de 2 supérieure** : 120 archers ⇒ tableau à **128 lignes** avec **8 exempts (byes)** attribués aux **8 têtes de série** (seeds 1 à 8, d'après le classement de qualification).
- **Seeding en serpent standard** (vérifié) : M1 = seed 1 (bye), M2 = 64 vs 65, M3 = 33 vs 96, M4 = 32 vs 97, M5 = 17 vs 112, M6 = 48 vs 81, M7 = 49 vs 80, M8 = 16 vs 113…
  - Règle : dans un tableau de taille `2^k`, l'archer de rang `r` affronte l'archer de rang `2^k + 1 − r`, et les têtes de série sont réparties pour ne se rencontrer que le plus tard possible (algorithme de seeding classique).
- Le vainqueur progresse dans le principal ; **le perdant est routé** vers le tableau de placement de sa plage (§4).

### Rangs 1 à 4 (haut du principal)
- **Finale → rangs 1 et 2** ; la **Grande Finale se tire en Big Shoot Off** (barème dédié).
- **Petite finale (perdants des ½ finales principales) → rangs 3 et 4**.

---

## 3. Les matchs terminaux de placement (onglet TABLEAU 2) — RÈGLE VÉRIFIÉE

Chaque **rang de 5 à 120** est décidé par un **match terminal unique** (M427 → M484) :

```
rang 5  ← Gagnant M427      rang 6  ← Perdant M427
rang 7  ← Gagnant M428      rang 8  ← Perdant M428
rang 9  ← Gagnant M429      rang 10 ← Perdant M429
…                           …
rang 119 ← Gagnant M484     rang 120 ← Perdant M484
```

> **Règle T** — Un match terminal de placement affecté à la paire de rangs `(2k−1, 2k)` (relatifs à sa plage) donne : **gagnant = rang supérieur**, **perdant = rang immédiatement inférieur**.

58 matchs terminaux (M427–M484) fixent les 116 rangs 5→120 ; les rangs 1→4 viennent du haut du principal.

---

## 4. Le routage des perdants (cascade de division par deux) — RÈGLE VÉRIFIÉE

À partir des labels de l'onglet PLAN (colonnes « TABLEAU x-y » par tour) et du graphe d'alimentation (« Perdant Mxxx »), la plage de rangs des tableaux de placement **se divise par deux à chaque tour** :

| Tour perdu (principal / placement) | Tableaux de placement actifs (plages de rangs) |
|---|---|
| Tour 4 | 65-96, 97-120 *(plages larges ~32)* |
| Tour 6 | 33-48, 49-64, 65-80, 81-96, 97-112 *(plages ~16)* |
| Tour 8 (quarts) | 17-24, 25-32, 33-40, …, 113-120 *(plages ~8)* |
| ½ finales placement (M369-426) | 9-12, 13-16, 17-24 … 113-120 *(plages ~4)* |
| Finales placement (M427-484) | 5-6, 7-8, 9-12→paires … 119-120 *(paires)* |

Chaîne d'alimentation vérifiée (exemple) :
`Perdant(quart M305-368) → ½ finale placement (M369-426) → finale placement (M427-484) → rang exact`.

> **Règle R** — Quand un archer perd au niveau dont la plage atteignable est `[a..b]` (de largeur `w = b−a+1`), il entre dans le sous-tableau de placement de cette plage. Il y dispute une élimination interne qui **divise `w` par deux à chaque tour** jusqu'à `w = 2`, où le match terminal (Règle T) fixe son rang exact.

Autrement dit, la position finale d'un archer est entièrement déterminée par **la suite de ses résultats (V/D) tour après tour** : chaque défaite le fait basculer dans la moitié inférieure de sa plage courante, chaque victoire dans la moitié supérieure — exactement comme un tri par tournoi.

---

## 5. Micro-exemple à 8 archers (pour fixer les idées)

Placement intégral de 8 archers ⇒ 3 « niveaux » :

```
QUARTS          ½ FINALES              FINALES / PLACEMENT        RANG
M1: 1 vs 8 ─┐
            ├─ SF-A: V(M1) vs V(M2) ─┐
M2: 4 vs 5 ─┘                        ├─ FINALE:  V(SF-A) vs V(SF-B)  → 1 / 2
M3: 2 vs 7 ─┐                        │  BRONZE:  P(SF-A) vs P(SF-B)  → 3 / 4
            ├─ SF-B: V(M3) vs V(M4) ─┘
M4: 3 vs 6 ─┘

Perdants des quarts (plage 5-8) :
  SF5-8-A: P(M1) vs P(M2) ─┐
  SF5-8-B: P(M3) vs P(M4) ─┴─ PLACE 5-6: V vs V → 5 / 6
                              PLACE 7-8: P vs P → 7 / 8
```

Généralisation : à chaque niveau, la plage `[a..b]` se scinde en `[a..mid]` (vainqueurs) et `[mid+1..b]` (perdants) ; on récurse jusqu'aux paires.

---

## 6. Barèmes par phase (presets modifiables — onglet PLAN)

| Phase | Barème observé |
|---|---|
| Qualification | 5 volées de 3 flèches, **cumul** des points |
| Barrage (égalités qualif) | 1 volée de **1 flèche** |
| Tours (matchs individuels) | 3 volées de 3 flèches, **système de sets, 4 pts gagnant** |
| ½ finales & finales de placement | **5 volées de 3 flèches, 6 pts gagnant** |
| Grande Finale | **Big Shoot Off** |

---

## 7. Implications pour le moteur & points à valider

### Ce que le moteur doit savoir faire (dérivé)
1. **Générer le tableau principal** : arrondi à `2^k`, byes aux têtes de série, seeding serpent.
2. **Router automatiquement chaque perdant** vers le sous-tableau de placement de sa plage courante (Règle R).
3. **Diviser récursivement les plages** jusqu'aux matchs terminaux (Règle T) et **affecter les rangs 1→N**.
4. **Appliquer le barème de la phase** en cours (presets modifiables).
5. **Gérer les byes** dans les sous-tableaux quand une plage n'est pas une puissance de 2 pleine (cas 120 : plages 9-12, 65-80…).

### Décisions (arbitrées le 08/07/2026)
| # | Sujet | Décision |
|---|---|---|
| Q1 | Nature du « Lucky Loser » | **Configurable.** Le routage des perdants est une **règle générique paramétrable** : par défaut *tableau de classement en cascade* (observé), mais le moteur doit aussi supporter le *vrai repêchage* réintégrant le principal (World Archery). Les deux sont deux configurations d'un même mécanisme de routage. |
| Q2 | Profondeur du classement | **Configurable par tournoi.** Par défaut placement intégral **1→N** ; l'organisateur peut choisir de s'arrêter à un top (classer finement le top N, regrouper le reste). |
| Q3 | Départage / barrage | **Presets FFTA modifiables** : qualif départagée au **nb de 10 puis de 9** ; match nul en sets → **shoot-off 1 flèche, plus près du centre** ; **barrage de tir** pour les places décisives. Surchargeable par l'admin. |
| Q4 | Byes dans plages non-2^k | **Aux mieux classés de la plage** (meilleur score qualif / progression). |
| Q5 | Généralité de la règle /2 | **Universelle et calculée** : division par deux systématique quel que soit l'effectif, gestion automatique des byes. Une seule logique à implémenter et tester. |
| Q6 | Autres formats | Le constructeur libre doit **aussi** couvrir des formats simples (élimination directe, top N, tableau unique) **en plus** du placement intégral. |

### Conséquences de conception
- Le **routage des perdants** (Règle R) doit être une abstraction : une fonction `route(perdant, tour, contexte) → destination` dont le placement en cascade et le repêchage-réintégration sont deux implémentations (Q1).
- La **profondeur de classement** est un paramètre de la phase de placement : on arrête la cascade à la granularité voulue et on regroupe le reliquat (Q2).
- Les **presets de barème** (Q3) et l'**attribution des byes** (Q4) sont des politiques injectables, réutilisables entre formats (Q5, Q6).

### Recommandation de validation
Implémenter d'abord le moteur, puis **rejouer le tournoi 120 de `Tableaux.xlsx`** comme test de non-régression : vérifier que l'arbre généré, le routage des perdants et le classement 1→120 correspondent exactement au classeur. C'est le meilleur oracle disponible.

---

*Formalisation établie par rétro-ingénierie du classeur. Les règles marquées « VÉRIFIÉE » sont confirmées par extraction du fichier ; les 6 points du §7 ont été arbitrés le 08/07/2026.*
