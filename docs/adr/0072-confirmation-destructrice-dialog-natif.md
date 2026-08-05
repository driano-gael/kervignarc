# ADR-0072 — Confirmation d'un geste destructeur : `<dialog>` natif, pas de librairie

- **Statut** : accepté
- **Date** : 05/08/2026
- **Contexte** : lot « retours du questionnaire de maquettes » (`maquettes/questionnaires/a15-bascule-de-tour.md`)
- **Remplace** : rien. **Complète** [ADR-0059](0059-routage-par-role-dans-l-url-routeur-maison.md) et
  [ADR-0008](0008-gestionnaire-de-paquets.md) sur la même question — « dépendance ou quelques lignes maison ? »

## Contexte

Le produit posait ses questions de confirmation avec `window.confirm`. Ce n'était pas un cas isolé :
**huit** appels, sur les gestes les plus lourds — lancer un tour, terminer un tournoi, l'annuler,
l'archiver, révoquer un poste de cible, retirer un écran de salle, annuler un barrage déjà saisi.
Tous portaient la même note « en attendant une friction plus riche », et cette note avait survécu à
plusieurs US.

Le commanditaire a tranché le 04/08/2026 : *« la confirmation passe par un window.confirm que le
code signale comme provisoire — que veux-tu à la place ? → **une pop-up propre et bien design** »*.

Trois défauts de `window.confirm` comptent ici, et aucun n'est esthétique :

1. **Il bloque le fil d'exécution.** Sur des écrans temps réel (poll court, WebSocket, file
   hors-ligne en rejeu), les requêtes en vol et le rendu s'arrêtent tant que la boîte est ouverte.
2. **Il ne peut rien nommer.** Ni le ton, ni la conséquence chiffrée (« il reste 3 séries à
   valider », « 4 manches seront effacées »), ni un libellé de bouton qui redit le geste. On lit
   « OK / Annuler » — franchement trompeur sur la transition *annuler un tournoi*, où « Annuler »
   désigne à la fois le geste et son abandon.
3. **Son apparence dépend du navigateur**, donc du parc BYOD — ce que le cahier des charges design
   n'accepte pas.

## Décision

**1. `window.confirm` est proscrit du produit.** Toute confirmation passe par deux composants de
`shared/ui/` : `DialogueConfirmation` (le primitif) et `BoutonConfirme` (le cas courant, « un bouton
+ une question », qui possède son propre état d'ouverture).

**2. On n'ajoute pas de librairie de modale.** L'élément `<dialog>` et `showModal()` fournissent
nativement le piège de focus, la fermeture par `Échap`, l'inertie de l'arrière-plan et le
`::backdrop` — c'est-à-dire exactement la liste de ce pour quoi on prendrait une dépendance. La règle
11 du projet dit « stdlib ou quelques lignes maison préférées » ; c'est le même arbitrage qu'ADR-0059
a rendu pour le routeur.

**3. Le produit assume une baseline navigateur** : Chrome 37+, Safari 15.4+, Firefox 98+ — en
pratique, « pas antérieur à mars 2022 ». C'est le point le plus engageant de cet ADR, parce qu'il
porte sur le matériel des bénévoles, que le club ne maîtrise pas.

## Alternatives écartées

- **Garder `window.confirm`.** Écarté par le commanditaire, et par les trois défauts ci-dessus. Le
  premier (blocage du fil) suffisait à lui seul sur un écran de supervision.
- **Prendre une librairie de modale** (Radix, Headless UI, react-modal). Écarté : elle apporterait ce
  que `<dialog>` fournit déjà, contre une dépendance de plus à auditer, documenter et maintenir
  (règle 11) — sur un produit qui n'a que quatre dépendances de production.
- **Un overlay maison en `<div>`** (le patron de `QrCible`). Écarté : il faudrait réimplémenter le
  piège de focus et l'inertie, c'est-à-dire précisément la partie difficile, et la refaire moins bien
  que le navigateur.

## Conséquences

**Positives.** Une question de confirmation peut enfin être *écrite* : titre qui pose la question,
phrase qui dit ce qui va se passer, détail chiffré à part, libellé de bouton qui reprend le geste.
Le fil n'est plus bloqué. L'apparence est celle du produit sur tous les appareils.

**Négatives, et à surveiller.**

- **La baseline navigateur devient un engagement.** Un appareil plus ancien que 2022 verra un
  `<dialog>` rendu en ligne, non modal : la question s'affichera mais l'arrière-plan restera
  actionnable. L'argument « il ne ferait pas tourner le reste de l'app non plus » est **plausible et
  non vérifié** — aucun test sur parc réel n'a été fait.
- **jsdom n'implémente ni `showModal()` ni `close()`.** L'environnement de test partagé est complété
  (cf. [ADR-0053](0053-outillage-test-de-rendu-front.md), Conséquences) ; ce complément ne simule que
  `open`, donc **aucun test du dépôt ne pourra jamais prouver le piège de focus, `Échap` ou
  l'inertie**. Un futur composant qui reposerait sur la sémantique modale passerait en test et
  casserait au navigateur.
- **Le geste destructeur ne prend pas le focus.** Sur `ton="danger"`, c'est « Annuler » qui est
  focalisé à l'ouverture : `showModal()` focalise le premier élément focusable, et `Entrée` par
  réflexe ne doit pas déclencher un archivage. Conséquence acceptée : confirmer demande un geste
  délibéré, ce qui est le but.
- **`BoutonConfirme` ferme le dialogue *avant* d'agir**, pour que le résultat de la mutation (erreur,
  compte de duels partis) s'affiche sur l'écran derrière. Le paramètre `enCours` du primitif reste
  donc inutilisé par ce chemin : il n'a de sens que pour un appelant qui garderait le dialogue ouvert
  pendant la mutation.

## Références

- `maquettes/questionnaires/a15-bascule-de-tour.md` — question 2 et sa réponse.
- `frontend/src/shared/ui/DialogueConfirmation.tsx`, `frontend/src/shared/ui/BoutonConfirme.tsx`.
- [ADR-0053](0053-outillage-test-de-rendu-front.md) — outillage de test de rendu front.
- [ADR-0059](0059-routage-par-role-dans-l-url-routeur-maison.md) — même arbitrage « maison plutôt que
  dépendance », sur le routage.
