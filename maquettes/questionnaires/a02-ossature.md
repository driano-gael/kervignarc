# A02 · Ossature — sidebar groupée par temps

> **Écran** : [A02 — Ossature](../a02-ossature.html) · **Appli** : Appli admin (`/admin`)
> **Rôle** : Le squelette stable de l'appli : 16 destinations rangées par temps du tournoi, toutes cliquables en permanence.
>
> Rempli le 29/07/2026. **Réponse sur la v1** — la planche a été refaite le jour même à partir de ce retour.

---

## 1. Quel parti pris retiens-tu ?

- [ ] A — Sidebar groupée repliable
- [ ] B — Barre horizontale par temps
- [ ] C — Sidebar plate (16 entrées à plat)
- [x] Aucun — voir « à refaire » plus bas

**Pourquoi ce choix**

> ce n'est pas le cycle de vie que je souhaite, mais le theme et les design sont bien.

**Ce que tu prendrais dans les autres variantes**

> _(sans réponse)_

---

## 2. Verdict

- [ ] ✅ Validé tel quel — on peut coder ça
- [ ] 🟡 Validé avec les réserves ci-dessous
- [x] 🔴 À refaire — l'écran ne répond pas au besoin

---

## 3. Critiques

> la sidebar fait vivire le tournoi sous tout ses etat en meme temps, je trouve cela confus. Un tournoi en preparation est le moment ou il est crée, il merite son propre cycle de vie, on ne dit pas etre pollué par jour J et apres.
> Cela doit plutot passé par un accueil, qui choisit le cycle. puis on retourne a l'acceuil pour un autre cycle, mais le jour J, on est centré sur le déroulé du ou des tournois en cours. tournois, pas sur sa création ou son apres.
> dans le menu on doit avoir un champs lancé un tournois. dans lequel on peut demarré plusieur tournois. et apres un espace dédié pour gerer le déroulé de ces tournois.

---

## 4. Évolutions souhaitées

> la navbar doit servir au action possible lors du déroulé.

---

## 5. Questions ciblées

**1. Les groupes Préparation / Jour J / Après correspondent-ils à ta façon de travailler, ou raisonnes-tu par objet (archers, cibles, scores) ?**

> _(sans réponse)_

**2. La recherche d'archer en haut de sidebar est-elle au bon endroit, ou la veux-tu ailleurs (barre du haut, raccourci clavier) ?**

> la recherche d'un archer est bien, mais il depend du cycle ou l'on est.
> dans le cycle preparation et apres, on doit pouvoir faire une recherche sur tout items-entité, par une liste deroulante et un champs de saisie. une completion de recherche montre une liste des items possible avec la possibilité de clique dessus et d'ouvrir la fiche en modification.
> dans le cycle deroulé du tournoi, on peut faire une recherche d'un archer *du tournoi* et ouvrir sa fiche en consultation avec ses information du tournoi. puis possibilité d'agir dessus si besoin.

**3. Le sélecteur de tournoi au-dessus de tout : suffisant pour éviter de modifier le mauvais tournoi ?**

> Les tournoi en cycle déroulé, peuvent etre multiple et on doit etre sur de celui sur lequel on est placé, donc en déroulé la liste de selection doit etre bien visibible. (sous header par exemple, bien demarqé)

---

## 6. Vocabulaire

| À l'écran | Le bon mot |
|---|---|
|  |  |

---

## 7. Ce qui manque complètement

> _(sans réponse)_

---

## Précisions apportées en échange (29/07/2026)

**Le découpage de la Préparation**, en quatre temps de travail distincts :

1. créer / gérer les briques nécessaires à un tournoi
2. assembler les briques pour créer un tournoi
3. gérer l'organisation du tournoi en amont
4. gérer le remplissage du tournoi

Ce découpage **s'applique aussi au Déroulé et à l'Après**, qui ont chacun leurs propres temps de vie —
non détaillés à ce stade.

**Vocabulaire arrêté par le commanditaire :** *rôle* pour le choix de l'écran, *espace* pour le choix
Préparation / Déroulé / Après. Le mot du troisième niveau et le nom exact des espaces sont laissés à
l'assistant.

**Non tranché par le commanditaire**, donc décidé par l'assistant et signalé sur la planche v2 :
enchaînement contraignant ou non des étapes, portée des briques (patrimoine du club ou par tournoi),
étapes du Déroulé et de l'Après.
