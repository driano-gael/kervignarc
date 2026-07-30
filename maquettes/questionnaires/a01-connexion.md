# A01 · Connexion

> **Écran** : [A01 — Connexion](../a01-connexion.html) · **Appli** : Appli admin (`/admin`)
> **Rôle** : Le seul écran à mot de passe du produit : l'admin est le seul rôle authentifié par compte.
>
> Rempli le 30/07/2026. **Réponse sur la v1** — la planche a été corrigée le jour même à partir de ce
> retour. **Verdict non rendu** (aucune case cochée en §2) : noté tel quel plutôt qu'interprété.

---

## 1. Quel parti pris retiens-tu ?

- [✅] A — Formulaire sobre plein cadre
- [ ] B — Connexion + choix du tournoi en une étape
- [ ] Aucun — voir « à refaire » plus bas

**Pourquoi ce choix** *(ce qui a emporté la décision, même si c'est un détail)*
>suffisant, respecte le theme

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

>un retour vers les autres ecrans (public, cible, scoreur, ...)

---

## 5. Questions ciblées

*Ces questions viennent de points que la maquette n'a pas pu trancher seule.*

**1. Faut-il proposer une reconnexion automatique sur le poste de la table d'organisation, ou est-ce un risque le jour J (poste laissé sans surveillance) ?**
>non, pas de reconnexion automatique

**2. Le lien de secours vers /saisie et / est-il utile, ou source de confusion pour un bénévole ?**
>non, pas utile

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

---

## Ce que ce retour a produit (30/07/2026)

| Ta réponse | Suite donnée |
|---|---|
| Parti pris **A** retenu | Conservé : avec les URL par rôle, `/admin` sans session affiche ce login. |
| « **pas de reconnexion automatique** » | **Décision actée**, reversée dans l'ADR du routage — pas de session admin ressuscitée sans mot de passe sur un poste laissé sans surveillance. |
| « le **lien de secours n'est pas utile** » | **Décision actée** : l'écran de connexion ne porte aucun lien en dur vers un autre monde. La question elle-même était **périmée** — `/saisie` et `/` n'existaient pas dans le code. Les liens ont été retirés de la planche. |
| « un **retour vers les autres écrans** (public, cible, scoreur…) » | **Déjà livré** avant ta demande : bouton « Changer de rôle » de l'en-tête (E00US017 / ADR-0042, mergé le 21/07/2026), avec verrou `D-13` pour une tablette rattachée. L'écran correspondant, jamais maquetté, a désormais sa planche : [A00](../a00-portes.html). |

**Défaut du dossier révélé par ce questionnaire** : les 35 planches décrivaient trois applications à trois
URL (31 mentions de `/admin` et `/saisie`) alors que l'application livrée n'en avait aucune, et que son
écran d'entrée à quatre portes n'était nulle part. Corrigé le 30/07/2026.

