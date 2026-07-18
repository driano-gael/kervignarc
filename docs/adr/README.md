# Architecture Decision Records (ADR)

Journal des décisions d'architecture du projet **Kervignarc**.

Chaque ADR est un fichier `NNNN-titre.md` au format court : contexte / options / décision / conséquences. Un ADR est **immuable** une fois accepté ; une décision qui change fait l'objet d'un **nouvel ADR** qui *remplace* le précédent (mettre l'ancien en statut `Remplacé par ADR-XXXX`).

## Statuts possibles
`Proposé` · `Accepté` · `Déprécié` · `Remplacé par ADR-XXXX`

## Index

| # | Titre | Statut |
|---|---|---|
| [0001](0001-adopter-les-adr.md) | Adopter les ADR | Accepté |
| [0002](0002-stack-et-topologie.md) | Stack technique & topologie de déploiement | Accepté |
| [0003](0003-architecture-hexagonale.md) | Architecture hexagonale ciblée + composition root explicite | Accepté |
| [0004](0004-moteur-de-phases-politiques.md) | Moteur de phases à politiques injectables | Accepté |
| [0005](0005-async-et-sqlite.md) | Accès SQLite : lectures synchrones + file d'écriture (single-writer) | Accepté |
| [0006](0006-ubiquitous-language.md) | Vocabulaire : métier en français, technique en anglais | Accepté |
| [0007](0007-erreurs-par-couche.md) | Erreurs typées par couche | Accepté |
| [0008](0008-outillage-npm-venv.md) | Outillage : npm + venv/pip au lieu de pnpm + uv | Accepté |
| [0009](0009-gouvernance-dependances.md) | Gouvernance des dépendances externes (parcimonie, sécurité, doc) | Accepté |
| [0010](0010-unite-de-travail-transactionnelle.md) | Unité de travail : la commande d'écriture est la frontière transactionnelle | Accepté |
| [0011](0011-phase-qualification-anticipee.md) | Introduire une `Phase` minimale dès J1 pour héberger le barème de qualification | Accepté |
| [0012](0012-argent-en-centimes-entiers.md) | Compter l'argent en centimes entiers, jamais en flottants | Accepté |
| [0013](0013-conduite-de-la-revue-d-us.md) | Conduite de la revue d'US : axes parallèles + porte mécanique | Accepté |
| [0014](0014-club-inconnu-plutot-que-club-sentinelle.md) | Club d'un archer facultatif : `NULL` = *inconnu*, jamais un club sentinelle | Accepté |
| [0015](0015-signaler-un-doublon-plutot-que-l-interdire.md) | Doublon d'archer : signaler (409) et laisser confirmer, plutôt qu'un `UNIQUE` qui rejetterait un homonyme réel | Accepté |
| [0016](0016-supprimer-un-archer-engage-plutot-que-le-refuser.md) | Archer engagé : suppression **confirmable et destructrice**, plutôt qu'un refus sans issue — et à ne pas confondre avec le **forfait**, qui préserve les résultats | Accepté |
| [0017](0017-le-depart-est-un-creneau-du-tournoi.md) | Le départ est un **créneau du tournoi**, pas une participation de l'archer | Accepté |
| [0018](0018-supprimer-un-depart-a-inscriptions-confirmable.md) | Supprimer un départ à inscriptions : confirmable, effets monétaires déportés | Accepté |
| [0019](0019-categorie-eligibilite-multi-tranches.md) | La catégorie porte un **ensemble** de tranches d'âge, pas une tranche unique | Accepté |
| [0020](0020-blason-zones-vocabulaire-ferme-et-defaut-sur-ensemble.md) | Le blason porte ses **valeurs de score admises** ; vocabulaire fermé, défaut = blason simple complet | Accepté |
| [0021](0021-maille-des-us-au-grain-capacite.md) | Maille des US au grain **capacité** (regroupement du backlog non livré ; livré gelé) | Accepté |
| [0022](0022-hauteur-de-centre-sur-la-categorie.md) | La **hauteur du centre de l'or** vit sur la catégorie ; contrainte de placement de 1er rang | Accepté |
| [0023](0023-moteur-de-placement-glouton-deterministe.md) | Moteur de placement : **glouton déterministe**, contraintes câblées, recalcul à la demande | Accepté |
| [0024](0024-plan-de-cibles-materialise-ajustable.md) | Plan de cibles **matérialisé et ajustable** : persistance, modèle transactionnel, réserve | Accepté |
| [0025](0025-mode-d-identite-scoreur-par-code-individuel.md) | Mode d'identité **scoreur** : entité de domaine, code individuel généré, session nominative en mémoire | Accepté |

## Sources
`charge.md`, `cahier-des-charges.md`, `cahier-des-charges-technique.md`, `moteur-placement-lucky-loser.md`, `guide-architecture.md`.
