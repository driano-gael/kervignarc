# ADR-0001 — Adopter les ADR

- **Statut** : Accepté
- **Date** : 2026-07-08
- **Décideurs** : Organisateur / Architecte

## Contexte et problème

Le projet prend des décisions d'architecture non triviales et parfois contre-intuitives (voir ADR suivants). Sans trace du *pourquoi*, ces choix seront re-débattus ou cassés par méconnaissance, d'autant que le moteur métier est subtil et l'équipe réduite.

## Options envisagées

- **Journaliser les décisions en ADR** (fichiers Markdown versionnés dans le dépôt).
- Documenter dans un wiki externe : se désynchronise du code, non versionné avec lui.
- Ne rien formaliser : perte du contexte, décisions implicites.

## Décision

Nous adoptons les **Architecture Decision Records**, stockés dans `docs/adr/`, au format court (contexte / options / décision / conséquences). Toute décision structurante donne lieu à un ADR ; un ADR accepté est immuable et remplacé par un nouvel ADR en cas d'évolution.

## Conséquences

- **+** Le « pourquoi » est versionné avec le code et relu en revue.
- **+** Onboarding facilité, décisions opposables.
- **−** Légère discipline à tenir (créer l'ADR au bon moment).

## Liens
`guide-architecture.md` §11.
