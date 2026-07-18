# ADR-0024 — Plan de cibles matérialisé et ajustable : persistance, modèle transactionnel, réserve

- **Statut** : Accepté
- **Date** : 2026-07-18
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E03-placement.md`](../../stories/E03-placement.md) (E03US004) ;
  [`docs/glossaire.md`](../glossaire.md) (`Réserve`, `Affectation`)
- **Introduit par** : E03US004 (ajustement manuel du placement).
- **Prolonge** : [ADR-0023](0023-moteur-de-placement-glouton-deterministe.md), dont le point 3
  (« recalcul à la demande, sans persistance ») **fléchait explicitement** la persistance sur cette
  US. Le moteur glouton déterministe (`domain/placement.py`) reste inchangé ; on lui ajoute deux
  primitives pures (validation d'un ajout, placement des restants) et une couche de persistance.

## Contexte et problème

E03US001 (ADR-0023) livre un plan de cibles **recalculé à la demande**, sans persistance : parfait
tant que le plan n'est pas retouchable. E03US004 le rend **ajustable** — l'admin déplace un archer,
en met de côté, échange deux tireurs — ce qui force trois décisions structurantes que le CA ne
tranche pas seul (arbitrées avec l'organisateur le 18/07/2026) :

1. **Que persiste-t-on ?** Un déplacement doit survivre au rechargement. Deux modèles cohérents : une
   **surcouche** d'écarts posés sur un auto-placement qui reste vivant, ou un **plan matérialisé**
   dont l'état édité fait foi.
2. **Quand écrit-on, et que veut dire « annuler » ?** À chaque geste (serveur autoritaire) ou à une
   validation finale (brouillon côté client) ?
3. **Comment représenter un archer non placé ?** Le CA veut qu'un archer hors cible ait une **raison
   explicite** — il ne « tombe » pas silencieusement.

## Décision

**1. Plan matérialisé, source de vérité — pas une surcouche.** Une table `placement` porte, par
**inscription** (l'archer sur *ce* départ), la case occupée : `(inscription_id, depart_id,
cible_index, position)`. Un inscrit **sans ligne** est *en réserve*. La lecture
(`plan_de_cibles`) ne recalcule plus : elle **lit** l'état persisté (les gardes 404 d'ADR-0023
demeurent). Motif du choix contre la surcouche : le geste « réserve » (mettre N archers de côté puis
les reposer un à un pour valider le plan final) décrit une **session d'édition sur un plan**, pas des
écarts sur un calcul vivant. Faire tourner l'auto « par-dessus » des archers épinglés reviendrait à
un placement **sous contraintes fixes** — plus de code, sémantique trouble — pour un besoin que le
matérialisé sert directement. Un nouvel inscrit après matérialisation apparaît **en réserve** (pas de
ligne = pas placé), prêt à poser : pas de déplacement-surprise.

**2. Modèle live / serveur autoritaire ; « annuler » = régénérer.** Chaque geste (déplacer,
échanger, mettre en réserve, placer les restants) est **une écriture via la file** (writer unique,
règle 7 / ADR-0005), diffusée en direct par le broadcaster post-commit (règle 10 : le front invalide
et refetch). Aucun brouillon client divergent — cohérent avec le principe « serveur autoritaire » du
projet et avec le CA (« persistance via la file ; mise à jour live » **sur le geste**). Comme
l'auto-placement est **déterministe** (ADR-0023), « annuler les modifications » n'a pas besoin d'un
instantané : c'est **régénérer** (`placer` puis réécriture complète du plan du départ). Une seule
opération sert donc « générer le plan initial » **et** « annuler » — l'admin la déclenche, avec
confirmation (elle écrase les ajustements manuels).

**3. Réserve = première classe, raison dérivée.** Un inscrit en réserve est listé dans
`PlanDeCibles.conflits` avec une raison **calculée à la lecture**, jamais persistée : `SANS_BLASON`
si sa catégorie n'a pas de blason (donnée), sinon `NON_PLACE` si **aucune cible** ne peut plus
l'accueillir (le placement est saturé/incompatible), sinon `EN_RESERVE` (plaçable, en attente). C'est
la « raison explicite » du CA, et elle reste juste après n'importe quelle édition — là où une raison
gelée mentirait. Un `SANS_BLASON` n'est jamais placé (fraction inconnue).

**Corollaires.**

- **Échange atomique** (drag d'un archer sur une case occupée) : validé **en bloc** — chacun doit
  tenir dans la cible de l'autre — et appliqué en **une transaction** (deux upserts dans une seule
  commande en file). Si l'un ne tient pas, refus, **état inchangé** (`DeplacementInvalide`, 409).
  Déposer depuis la réserve sur une case occupée n'est **pas** un échange (rien à permuter en retour)
  : refusé. La validation réutilise la règle de budgets d'ADR-0023 via la primitive pure
  `cible_accepte` (lecture seule, ne mute pas le moteur).
- **Placer les restants** : primitive pure `placer_restants` — pose la réserve dans les **trous** du
  plan **sans déplacer** les archers en place (positions préservées, premier-trouvé déterministe) ;
  ce qu'aucune cible ne prend reste en réserve (`NON_PLACE`).
- **`ON DELETE CASCADE` sur `placement`**, à rebours de la convention DETTE-001 (« FK sans
  `ON DELETE`, purge applicative »). Justifié : `placement` est de la donnée **dérivée,
  reconstructible et feuille** (régénérable par l'auto), pas de la donnée saisie remontant l'arbre du
  tournoi comme les cas *non tranchés* de DETTE-001. Cascader sa disparition (désinscription,
  suppression d'archer/de départ) est **correct et automatique** — et évite d'étendre les trois
  cascades applicatives existantes. FK enforced (`PRAGMA foreign_keys=ON`).

## Conséquences

- **+** Le drag & drop a un **état stable** à manipuler ; la « mise à jour live » est **gratuite**
  (tout commit passe par la file → broadcast → invalidation front), sans événement ciblé à écrire.
- **+** Le moteur pur d'ADR-0023 est **réutilisé** intégralement (validation et restants dérivent de
  `_CibleEnCours`), testable depuis le CA sans base.
- **+** `ON DELETE CASCADE` garde le plan **cohérent** sans coupler la logique de placement aux
  repositories archer/départ/inscription.
- **−** La lecture **ne reflète plus automatiquement** les inscriptions courantes : un archer ajouté
  après génération est en réserve tant qu'on ne le place pas (auto des restants ou à la main). C'est
  **voulu** (pas de déplacement-surprise), mais l'admin doit y penser — l'écran le signale (réserve
  visible).
- **−** « Annuler » **écrase** tout l'ajustement manuel (régénération déterministe) : d'où la
  **confirmation**. Pas d'undo pas-à-pas en E03US004 (backlog si le besoin émerge).
- **−** Une entorse **locale et argumentée** à DETTE-001 (`ON DELETE CASCADE`) : à ne pas
  généraliser aux tables de données saisies, dont la politique de cascade reste non tranchée.
- **Périmètre** : la persistance, les endpoints d'écriture et l'écran d'ajustement (admin, PC, drag
  HTML5 natif — la règle 10 tactile vise les tablettes de saisie, pas cet écran) sont E03US004.
