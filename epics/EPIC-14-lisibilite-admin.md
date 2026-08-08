# EPIC-14 — Accueil & lisibilité de l'admin

- **ID** : EPIC-14
- **Statut** : ✅ **Close** *(3 capacités sur 3 livrées, 28–29/07/2026)*
- **Priorité** : MVP *(retours de la démo au client final, 27/07/2026)*
- **Dépend de** : EPIC-00 (coquille admin), EPIC-01 (cycle de vie 7 statuts), EPIC-12 (complétude, supervision, alertes)
- **Réfs** : [`cahier-des-charges-ux.md`](../cahier-des-charges-ux.md) §7.1 (`D-19`, `D-20`) ; [ADR-0026](../docs/adr/0026-cycle-de-vie-du-tournoi-sept-statuts.md) (7 statuts) ; ~~[ADR-0032](../docs/adr/0032-navigation-admin-par-etat-local.md) (navigation par état local)~~ **remplacé par [ADR-0059](../docs/adr/0059-routage-par-role-dans-l-url-routeur-maison.md)** ; [ADR-0052](../docs/adr/0052-accueil-admin-contextualise-par-statut.md) (accueil contextualisé par statut — *l'« ADR à créer » annoncé ici, écrit le 28/07/2026*) ; [ADR-0058](../docs/adr/0058-decoupage-de-l-admin-en-trois-axes-d-activite.md) (trois axes d'activité, révise `D-19`)

## Objectif / valeur
Rendre l'admin **lisible sans formation** : que l'interface « raconte une histoire claire » — où en est
le tournoi, quoi faire ensuite — au lieu d'aligner ~21 écrans sans fil conducteur. Retours de la démo du
27/07/2026 : « l'interface doit me raconter une histoire claire », « le découpage des écrans n'est pas
optimal, on ne sait pas ce qui se passe », « une explication de ce qui est saisissable et pourquoi — je
ne veux pas de formation ».

## Périmètre
### Inclus
- **Accueil-tableau de bord par tournoi** (`D-20`) = frise du cycle de vie + checklist fait/à faire +
  chiffres-clés & alertes (E14US001).
- **Aide contextuelle** « ce qui est saisissable et pourquoi » sur chaque écran (E14US002).
- **Réutilisé (référencé, non dupliqué)** :
  - cycle de vie enrichi à **7 statuts** — **E01US017** (EPIC-01) : la frise le consomme, c'est un **prérequis** ;
  - regroupement **liste/fiche & référentiels en déroulante** — **E00US016** (EPIC-00) : rend la saisie *propre*, quand E14US002 la rend *explicable*.

### Exclus
- Refonte de la navigation en `react-router` ([ADR-0032](../docs/adr/0032-navigation-admin-par-etat-local.md) : état local, réévaluée si vrai besoin d'URL).
- Identité visuelle par tournoi (E01US016).

## Capacités
- [x] Accueil-tableau de bord contextualisé par statut (`E14US001`) — livré le 28/07/2026 ([ADR-0052](../docs/adr/0052-accueil-admin-contextualise-par-statut.md)).
- [x] Aide contextuelle par écran (`E14US002`) — livré le 28/07/2026 (présentation pure, composant unique + dictionnaire centralisé).
- [x] **Ranger l'administration par axe d'activité** plutôt que par temps du tournoi, et donner
      **une adresse par rôle** (`E14US003`) — livré le 29/07/2026.
      [ADR-0058](../docs/adr/0058-decoupage-de-l-admin-en-trois-axes-d-activite.md) **révise `D-19`** ;
      [ADR-0059](../docs/adr/0059-routage-par-role-dans-l-url-routeur-maison.md) **remplace ADR-0032**, listé plus haut en
      « Exclus » — l'exclusion portait sur `react-router`, pas sur le découpage par rôle.
      *(Capacité **manquante jusqu'au 08/08/2026** : l'epic ne listait que 001 et 002, toutes deux
      cochées, et se présentait donc comme **terminé** alors qu'il portait la refonte de navigation
      la plus visible du lot. Le tracker, lui, la portait bien — la divergence était du côté de
      l'epic.)*

## Critères d'acceptation (epic)
- Depuis l'accueil d'un tournoi, un organisateur **non formé** voit **où il en est** et **quoi faire
  ensuite** sans avoir à ouvrir tous les écrans.
- Chaque écran de saisie dit **ce qui s'y saisit et pourquoi**.

## Risques
- **E14US001 trop large** pour une branche (frise + checklist + chiffres) → redécouper par brique (règle INVEST).
- **Dépendance E01US017** : la frise 7 statuts n'a de sens qu'une fois le cycle enrichi livré → l'ordonner avant.
