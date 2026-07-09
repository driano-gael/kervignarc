# ADR-0008 — Outillage : npm + venv/pip au lieu de pnpm + uv

- **Statut** : Accepté
- **Date** : 2026-07-09
- **Décideurs** : Organisateur / Architecte

## Contexte et problème

Le `guide-architecture.md` §3 impose **uv** (gestion Python & venv) et **pnpm + Vite** (front)
comme gestionnaires de paquets. Or, sur le poste de développement de l'organisateur,
**ni `uv` ni `pnpm` ne sont installés** ; seuls **Python 3.13**, **Node 24** et **npm** le sont.

Le projet est un **outil interne mono-club** développé par une équipe très réduite. Introduire
deux gestionnaires supplémentaires (installation globale, apprentissage, maintenance) apporte peu
de valeur à ce stade au regard des outils standard déjà présents et maîtrisés.

## Options envisagées

- **Installer uv + pnpm** pour se conformer au guide : conforme mais ajoute de l'outillage global
  à installer/maintenir sur le poste, sans bénéfice tangible pour un mono-repo local simple.
- **Rester sur npm (front) et venv/pip (back)** : outillage déjà présent, standard, suffisant pour
  ce périmètre ; s'écarte du guide.
- **Mélange** (ex. uv seul) : incohérent, cumule les inconvénients.

## Décision

Pour ce projet, l'outillage est :

- **Python (backend)** : environnement virtuel **`python -m venv .venv`** + **`pip`**.
  `pyproject.toml` reste la **source de vérité** des dépendances ; `requirements.txt` est
  **régénéré** (jamais édité à la main) via `pip freeze` (versions épinglées) et versionné.
- **Frontend** : **npm** + **Vite** ; `package.json` + `package-lock.json` (lockfile) versionnés.

Les **principes** du guide restent valables : source de vérité unique des dépendances, lockfiles
versionnés, aucune dépendance « fantôme », versions figées. **Seuls les gestionnaires changent.**

Cette décision est **réversible** : une migration vers uv/pnpm reste possible ultérieurement
(nouvel ADR remplaçant celui-ci) sans impact sur l'architecture applicative.

## Conséquences

- **+** Aucun outillage global supplémentaire à installer ; démarrage immédiat avec l'existant.
- **+** Outils standard, largement documentés, connus de l'équipe.
- **−** Écart au `guide-architecture.md` §3 (à mettre à jour ou à noter comme toléré par cet ADR).
- **−** `requirements.txt` est régénéré par `pip freeze` (moins déterministe que `uv export`) :
  discipline à tenir pour garder `pyproject.toml` et `requirements.txt` synchronisés.
- **−** Le contrôle CI « requirements.txt à jour » (guide §3) devra s'appuyer sur pip, pas uv.

## Liens

`guide-architecture.md` §3 ; ADR-0002 ; story `E00US001`.
