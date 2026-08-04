# P05 · Tableau de duels

> **Écran** : [P05 — Tableau de duels](../p05-tableau-duels.html) · **Appli** : Appli publique (`/`)
> **Rôle** : L'arbre d'élimination directe sur 360 px : le vrai problème de conception de l'appli publique.
>
> Remplis ce qui te parle, laisse le reste vide. Une ligne barrée ou un « non »
> sec est une réponse parfaitement utile — c'est même la plus rapide à exploiter.

---

## 1. Quel parti pris retiens-tu ?

- [ ] A — « Mon chemin » en liste
- [ ] B — Arbre complet défilable
- [ ] Aucun — voir « à refaire » plus bas

**Pourquoi ce choix** *(ce qui a emporté la décision, même si c'est un détail)*
>

**Ce que tu prendrais dans les autres variantes**
>

---

## 2. Verdict

- [ ] ✅ Validé tel quel — on peut coder ça
- [ ] 🟡 Validé avec les réserves ci-dessous
- [ ] 🔴 À refaire — l'écran ne répond pas au besoin

---

## 3. Critiques

*Ce qui ne va pas : hiérarchie, vocabulaire, information manquante, geste pénible,
cas réel non couvert.*

>

---

## 4. Évolutions souhaitées

*Ce que tu veux en plus ou en moins. Sans te censurer sur la faisabilité —
c'est mon travail de dire ce que ça coûte.*

>

---

## 5. Questions ciblées

*Ces questions viennent de points que la maquette n'a pas pu trancher seule.*

**1. Le tableau complet est-il attendu par le public, ou est-ce surtout l'affaire de l'organisation ?**
> **Tranchée le 04/08/2026 (cadrage E07US005) : les deux.** Les deux partis pris sont livrés — A
> « Mon chemin » (par archer suivi, lecture par défaut) et B « Tableau complet ». Ils ne servent pas
> le même geste, et offrir les deux coûte un bouton. Cf. `stories/E07-affichage-public.md`.

**2. Faut-il afficher les horaires prévisionnels des tours suivants, au risque qu'ils glissent ?**
> **Reste ouverte.** E07US005 a tranché « non » **pour cette US** : le domaine ne porte aucun horaire
> au grain de la phase ou du duel (seul le départ en a un), les afficher supposerait un moteur
> d'ordonnancement qui n'existe pas. La question de fond — le public en veut-il ? — n'est pas close.

---

## 6. Vocabulaire

*Un mot faux à l'écran coûte cher toute la journée. Corrige sans hésiter.*

| À l'écran | Le bon mot |
|---|---|
|  |  |

---

## 7. Ce qui manque complètement

*Un écran, un état, un cas que cette maquette ignore.*

>
