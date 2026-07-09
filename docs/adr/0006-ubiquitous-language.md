# ADR-0006 — Vocabulaire : métier en français, technique en anglais

- **Statut** : Accepté
- **Date** : 2026-07-08
- **Décideurs** : Organisateur / Architecte

## Contexte et problème

Le domaine est très spécifique (tir à l'arc FFTA) avec un vocabulaire précis : blason, volée, barrage, départ, duel, set. Le prototype existant est **incohérent** (`class Player`, mais `self.lettre`, `self.idCible`). Un vocabulaire flou nuit à la communication avec le client et disperse les traductions approximatives dans le code.

## Options envisagées

- **Métier en français, technique en anglais.**
- Tout en anglais : impose des traductions parfois bancales (blason → *target face* ?) et éloigne du langage FFTA partagé avec le client.
- Tout en français : gêne l'usage d'outils/conventions et le vocabulaire technique standard (repository, adapter…).

## Décision

- **Concepts métier nommés en français**, tels que la FFTA : `Archer`, `Cible`, `Blason`, `Volee`, `Fleche`, `Duel`, `Set`, `Barrage`, `Depart`, `Categorie`, `Placement`, `Tableau`, `Phase`.
- **Code technique / infrastructure en anglais** : `Repository`, `Adapter`, `Service`, `Router`, `Store`, `Factory`…
- **Cohérence obligatoire** du terme entre domaine, API, UI et documentation.
- Un **glossaire** (`docs/glossaire.md`) fait référence.
- Le prototype est **renommé** en conséquence (`Player` → `Archer`, `lettre`/`idCible` → `position`/`cible`).

## Conséquences

- **+** Langage partagé (ubiquitous language) direct avec le client et sans perte de sens.
- **+** Lecture du domaine évidente pour un connaisseur FFTA.
- **−** Mélange FR/EN dans une même base : la frontière doit être nette (métier vs technique) et tenue en revue.
- **−** Nécessite de maintenir le glossaire.

## Liens
`guide-architecture.md` §4.
