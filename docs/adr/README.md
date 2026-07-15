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

## Sources
`charge.md`, `cahier-des-charges.md`, `cahier-des-charges-technique.md`, `moteur-placement-lucky-loser.md`, `guide-architecture.md`.
