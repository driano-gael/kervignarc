# Prototype (décembre 2024) — référence, non exécuté en production

Ce dossier archive le **prototype Python initial** du domaine métier, écrit avant le
cadrage d'architecture du 08/07/2026. Il est conservé comme **référence** : le futur
`backend/domain/` **réutilise et étend** ces concepts (cf. `cahier-des-charges-technique.md`
§3–§4 et `guide-architecture.md` §4).

> ⚠️ Ce code **ne respecte pas encore** les conventions du projet (typage strict, vocabulaire
> métier FR / technique EN, couches hexagonales). Il sera **renommé et intégré** progressivement
> dans `backend/` au fil des US (ex. `Player.lettre`/`idCible` → `Archer` / `Cible.position`,
> cf. `guide-architecture.md` §4). Ne pas importer ce dossier depuis `backend/`.

## Contenu

| Fichier | Rôle (prototype) |
|---|---|
| `blason.py` | `Blason{size, capacity, name}` |
| `player.py` | `Player`/archer `{name, blason, lettre, idCible, scores…}` |
| `cible.py` | Cible (capacité 1/2/4, positions) |
| `match.py`, `round.py`, `bracket.py` | Matchs, tours, arbre d'élimination |
| `tournament_generator.py`, `tournament_tree.py`, `tree_principale.py` | Génération de tableaux |
| `classement.py` | Agrégation de classement |
| `tableau.py`, `organisation.py`, `cible.py` | Structures de placement |
| `main.py`, `testperso.py` | Points d'entrée / essais manuels |

La cible fonctionnelle et technique complète est décrite dans les cahiers des charges à la racine
et le backlog (`epics/`, `stories/`).
