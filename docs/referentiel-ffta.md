# Référentiel FFTA — Structure (à compléter)

- **Version** : 0.1 (structure)
- **Date** : 2026-07-08
- **But** : consolider les données de règles (catégories, blasons, barèmes, départage) qui alimentent la configuration (EPIC-01) et le moteur (EPIC-05).

> ⚠️ **Statut des valeurs** — Ce document fournit la **structure** et des **valeurs à titre indicatif**. Chaque valeur est étiquetée :
> - `✅ observé` : extrait de `Tableaux.xlsx` (tournoi réel 120).
> - `❓ à confirmer` : valeur plausible **à valider officiellement** (FFTA / organisateur) avant implémentation.
>
> Ne pas coder de valeur `❓` sans confirmation.

---

## 1. Catégories

Structure d'une catégorie : `code`, `libellé`, `arme`, `tranche d'âge`, `sexe`, `blason associé`, `distance` (=18 m salle).

| Code | Libellé | Arme | Âge | Sexe | Blason | Statut |
|---|---|---|---|---|---|---|
| _(à remplir)_ | ex. Senior Homme Arc Classique | Classique / Poulie / Nu… | Poussin→Super Vétéran | H/F | cf. §2 | ❓ à confirmer |

**À obtenir** : la liste officielle FFTA salle (arme × âge × sexe) et le blason associé à chacune. Pré-chargée et modifiable (E01US004).

---

## 2. Blasons (salle 18 m)

Structure : `nom`, `taille` (**fraction de place sur une cible**), `capacité induite`, `zones de score`, `catégories concernées`.

| Nom | Taille / fraction | Zones de score | Catégories | Statut |
|---|---|---|---|---|
| Blason 40 cm monospot | 1 place | 10 (dont X centre) → 1, M | _(à préciser)_ | ❓ à confirmer |
| Trispot 40 cm (3 spots verticaux) | fraction (petits blasons) | 10 → 6, M (typiquement) | arc à poulies / selon règlement | ❓ à confirmer |
| _(autres)_ | | | | ❓ à confirmer |

**Notion clé (modèle)** : un blason occupe une **fraction** de la capacité d'une cible ; la somme des fractions d'une cible ≤ sa capacité (1/2/4). C'est cette fraction qui pilote le placement (EPIC-03), pas le nom commercial du blason.

**À obtenir** : dimensions, dispositions (mono/tri/verti), zones de score et affectation par catégorie.

---

## 3. Barèmes par phase

Structure : `phase`, `format de tir`, `mode de score`, `condition de victoire`.

| Phase | Format de tir | Mode de score | Victoire | Statut |
|---|---|---|---|---|
| Qualification | 5 volées de 3 flèches | **Cumul** des points | classement par total | ✅ observé |
| Barrage (qualif) | 1 volée de 1 flèche | valeur / plus près du centre | départage | ✅ observé |
| Tours (matchs) | 3 volées de 3 flèches | **Système de sets** | ex. 4 pts → gagnant du match | ✅ observé (4 pts) |
| ½ finales & finales de placement | 5 volées de 3 flèches | sets | ex. 6 pts → gagnant | ✅ observé (6 pts) |
| Grande finale | Big Shoot Off | tir décisif | vainqueur = rang 1 | ✅ observé |

**À confirmer** : points de set exacts (gain/nul), nb de sets, gestion du set nul, format précis du BSO. Ces valeurs deviennent des **presets modifiables** (E01US011, politique `scoring`).

---

## 4. Règles de départage

| Contexte | Règle | Statut |
|---|---|---|
| Égalité au classement de qualification | Départage au **nombre de 10**, puis de **9**, … | ❓ à confirmer (usage FFTA courant) |
| Places décisives (accès tableau) après comptage | **Barrage de tir** (shoot-off) | ✅ observé (barrage au programme) |
| Match nul en sets | **Shoot-off 1 flèche**, **plus près du centre** gagne | ❓ à confirmer |

Ces règles alimentent la politique `tiebreak` (E04US016, E06US002/003).

---

## 5. Seeding & exempts (tableaux)

| Règle | Détail | Statut |
|---|---|---|
| Dimensionnement | Effectif arrondi à la puissance de 2 supérieure | ✅ observé (120 → 128) |
| Seeding | **Serpent** : rang `r` vs rang `2^k+1−r` ; têtes de série réparties | ✅ observé |
| Exempts (byes) | Attribués **aux mieux classés** | décision projet (ADR-0004 / E05US006) |

---

## 6. À fournir par l'organisateur / la FFTA

- [ ] Liste officielle des **catégories** salle + blason associé.
- [ ] Caractéristiques des **blasons** (dimensions, zones, fractions).
- [ ] **Points de set** exacts et gestion des nuls ; format du **BSO**.
- [ ] Règles précises de **départage** (qualif et match).
- [ ] Un **fichier d'inscrits « inscript'arc »** d'exemple (pour l'import — QT1).

*Une fois ces éléments reçus, ce référentiel passe en v1.0 et sert de source de vérité pour les presets de configuration.*
