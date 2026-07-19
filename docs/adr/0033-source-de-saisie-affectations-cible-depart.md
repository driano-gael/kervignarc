# ADR-0033 — Source des archers d'un poste : les affectations `(cible, départ)`, pas `Archer.cible`

- **Statut** : Accepté
- **Date** : 2026-07-19
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E04-saisie-scores.md`](../../stories/E04-saisie-scores.md) (E04US002, bloc
  « Arbitrages tranchés »). N'amende pas le glossaire (« cible », « départ », « affectation » y sont
  déjà définis) ni la dette (aucun raccourci assumé ; DETTE-011 traitée séparément dans la story).
- **Introduit par** : E04US002 (saisie de qualification — tranche backend).
- **S'appuie sur** : [ADR-0024](0024-plan-de-cibles-materialise-ajustable.md) (plan de cibles
  matérialisé : `Affectation` par départ), [ADR-0017](0017-le-depart-est-un-creneau-du-tournoi.md)
  (le départ est un créneau du tournoi), [ADR-0029](0029-mode-d-identite-poste-de-cible-et-jeton-de-poste.md)
  (le jeton de poste résout un `Poste(tournoi_id, cible_index)`), [ADR-0030](0030-saisie-autorisee-au-poste-de-cible-403-hors-cible.md)
  (la saisie est bornée par le lieu).

## Contexte et problème

Le walking skeleton (E00US011) place un archer via un champ direct **`Archer.cible`** (le numéro de
peloton) et sa démo `saisir_score` s'en sert pour vérifier « ce poste sert-il cet archer ». Depuis,
E03US004 (ADR-0024) a introduit le **vrai** modèle de placement : l'agrégat **`Affectation`**
(`inscription_id`, `cible_index`, `position` A–D), matérialisé et ajustable. **Deux représentations
du placement coexistent donc** : le champ `Archer.cible` (walking skeleton) et les `Affectation`
(placement réel).

E04US002 doit afficher, sur le poste, **les archers de la cible avec leur position A–D** pour saisir
leurs volées. La question : de quelle source ? Et un obstacle de fond apparaît alors : les
`Affectation` sont indexées **par départ** (`PlacementRepository.par_depart(depart_id)`), or un
`Poste` ne connaît que **`(tournoi_id, cible_index)`** (ADR-0029). **La même cible héberge des
archers différents selon le départ** (une séance le matin, une autre l'après-midi). Il n'existe donc
aucun chemin `(tournoi_id, cible_index) → archers` : il manque la dimension **départ**.

## Décision

**1. La source des archers d'une saisie est le modèle `Affectation`, pas `Archer.cible`.** Un poste
reconstitue ses archers par `Affectation` filtrées sur `cible_index`, avec leur `position` A–D. Le
champ `Archer.cible` **n'est plus une source de saisie** : il reste, pour l'instant, la donnée du
seul chemin de démo `saisir_score` (walking skeleton), remplacé par la nouvelle surface
volée-par-volée. **Son retrait a été différé** (arbitrage tranché en tranche exposition PR2b,
reversé dans [`stories/E04-saisie-scores.md`](../../stories/E04-saisie-scores.md)) : `/scores` est le
véhicule de test du walking skeleton (E2E, « engagé », diffusion) et son retrait casse ~10 tests —
c'est une **US de nettoyage dédiée**. La démo coexiste sans conflit (tables `score` vs `serie`/`volee`
disjointes), sans régression. `Archer.cible` deviendra mort une fois le classement de démo rebasé sur
les volées (E06US001) ; sa suppression est un nettoyage ultérieur, pas cette US.

**2. La dimension manquante — « quel départ » — est portée par le poste, explicitement.** Le poste
gagne un **départ courant** (cf. [ADR-0034](0034-poste-selectionne-son-depart-courant.md)). La chaîne
de reconstitution est alors déterministe : `Poste → (tournoi_id, cible_index, depart_id)` →
`PlacementRepository.par_depart(depart_id)` filtré sur `cible_index` → `position` A–D → archers (via
inscriptions). Aucune heuristique « départ actif » : le lien est **posé**, jamais **deviné**.

**3. Le contrôle « SA cible » (ADR-0030) reste au service et s'étend à « SON départ ».** La saisie
n'est légale que pour un archer effectivement affecté à `(cible_index, depart_id)` du poste ; sinon
`SaisieHorsCible` (403). Le couple `(tournoi_id, cible_index)` d'ADR-0030 devient le triplet
`(tournoi_id, cible_index, depart_id)`.

## Conséquences

- **+** La saisie s'appuie sur le placement **réel** (ajustable, ADR-0024) et non sur un champ hérité
  du walking skeleton : glisser-déposer un archer (E03US004) déplace aussi *où il saisit*, sans code
  supplémentaire.
- **+** Le triplet `(tournoi, cible, départ)` ferme la faille de l'ADR-0030 en concurrence de
  tournois **et** de départs : deux séances sur la même cible ne se mélangent pas.
- **−** Deux représentations du placement (`Archer.cible` et `Affectation`) coexistent encore le temps
  que le classement de démo (`calculer_classement` sur l'agrégat `Score`) soit rebasé sur les volées
  (E06US001). C'est une **transition assumée**, pas une dette silencieuse : `Archer.cible` n'a plus
  qu'un lecteur (le classement de démo), voué au remplacement.
- **−** Le poste doit connaître son départ **avant** de saisir : sans départ courant, il ne sait pas
  qui afficher. C'est l'objet d'ADR-0034 ; côté ergonomie, le cas courant (un seul départ ayant des
  archers sur la cible) permettra une présélection (relève du front).
