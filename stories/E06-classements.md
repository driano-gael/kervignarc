# E06 — Classements & résultats — User Stories

> EPIC : [EPIC-06](../epics/EPIC-06-classements.md) · Réfs : CDC fonctionnel M7, `moteur-placement-lucky-loser.md` §3-4.

---

### E06US001 — Classement de qualification (cumul)
*En tant que* public/organisateur, *je veux* le classement de qualif, *afin de* connaître les positions.
- **CA** : archers triés par score cumulé ; mis à jour en live ; par tournoi.
- **Dépend de** : E04US008 · **Jalon** : J1

### E06US002 — Départage qualif (nb de 10 puis 9)
*En tant que* système, *je veux* départager les ex æquo, *afin d'*ordonner sans ambiguïté.
- **CA** : à score égal, tri par nb de 10 puis de 9 ; départage déterministe et traçable.
- **Notes** : politique `tiebreak` (ADR-0004), preset FFTA modifiable.
- **Dépend de** : E06US001 · **Jalon** : J1

### E06US003 — Barrage de tir pour places décisives
*En tant que* système, *je veux* un barrage quand le comptage ne suffit pas, *afin de* trancher les places décisives.
- **CA** : déclenchement d'un barrage (shoot-off) pour les positions à enjeu ; résultat intégré au classement.
- **Dépend de** : E06US002, E04US016 · **Jalon** : J2

### E06US004 — Podium issu des duels
*En tant que* public, *je veux* voir le podium, *afin de* connaître les vainqueurs.
- **CA** : rangs 1-4 issus de la finale/petite finale (E05US009) ; affiché et exportable.
- **Dépend de** : E05US009 · **Jalon** : J2

### E06US005 — Agréger les rangs de tableau
*En tant que* système, *je veux* consolider les rangs produits par les phases, *afin de* bâtir le classement des duels.
- **CA** : rangs des différentes phases fusionnés en un classement cohérent par catégorie.
- **Dépend de** : E05US008 · **Jalon** : J2

### E06US006 — Classement intégral 1→N
*En tant que* public/organisateur, *je veux* un classement complet, *afin de* connaître le rang de chaque archer.
- **CA** : chaque archer a un rang unique 1→N, alimenté par les matchs terminaux (E05US014).
- **Notes** : cohérent avec l'oracle 120.
- **Dépend de** : E05US014 · **Jalon** : J3

### E06US007 — Profondeur de classement configurable
*En tant qu'*administrateur, *je veux* choisir jusqu'où classer, *afin d'*adapter au tournoi.
- **CA** : mode 1→N (défaut) OU top N + regroupement du reliquat ; politique `depth`.
- **Dépend de** : E06US006 · **Jalon** : J3

### E06US008 — Classement par catégorie
*En tant que* public, *je veux* les classements par catégorie, *afin de* voir les résultats pertinents.
- **CA** : filtrage/segmentation par catégorie ; applicable qualif et duels.
- **Dépend de** : E06US001 · **Jalon** : J1
