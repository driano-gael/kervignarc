# ADR-0075 — Le départ est la portée sportive, pas seulement un créneau logistique

- **Statut** : Accepté
- **Date** : 2026-08-06
- **Décideurs** : Organisateur / Architecte
- **Amende** : [ADR-0017](0017-le-depart-est-un-creneau-du-tournoi.md) (dont la décision n'avait été
  portée que par la **logistique** — cf. « Contexte » ci-dessous) ;
  [ADR-0045](0045-sequence-de-phases-ordonnee-et-invariants-collectifs.md) (la séquence 1..N est
  désormais celle **d'un départ**) ; [`docs/modele-de-donnees.md`](../modele-de-donnees.md)
  (`PHASE` change de parent : `DEPART` et non plus `TOURNOI`) ;
  [`docs/glossaire.md`](../glossaire.md) (*Départ*, *Phase*, *Classement*) ;
  [`docs/referentiel-ffta.md`](../referentiel-ffta.md) (§ « portée d'un classement », qui était muet)
- **Introduit par** : E01US025 (le format de tournoi porte un effectif **par départ** et un déroulé
  rejoué **par départ**) — la décision la précède logiquement et a donc été appliquée d'abord

## Contexte et problème

[ADR-0017](0017-le-depart-est-un-creneau-du-tournoi.md) a tranché, le 16/07/2026, le sens du mot
« départ », en citant l'arbitrage de l'organisateur mot pour mot :

> « un départ est un créneau horaire sur un tournoi, **comme si le tournoi pouvait se jouer plusieurs
> fois dans la même journée** »

**Seule la moitié logistique de cette phrase a été portée dans le code.** Un an de développement plus
tard, `Depart` porte un horaire, un tarif, un quota, des inscriptions, un placement et une feuille de
marque — tout ce qui remplit la salle. Mais rien de ce qui **compte les points** ne le connaît :

| Ce que « le tournoi se joue plusieurs fois » impliquait | État constaté le 06/08/2026 |
|---|---|
| Une séquence de phases par départ | `Phase.tournoi_id` — aucune notion de départ dans `domain/phase.py` |
| Des ordres 1..N par départ | `SequencePhases` valide 1..N **par tournoi** (ADR-0045 §3) |
| Un classement par départ | `ServiceClassements.pour_tournoi()` classe **tous** les archers du tournoi |
| Des tableaux et duels par départ | `domain/tableau.py`, `domain/duel.py` — zéro occurrence de « départ » |
| Un prélèvement « rangs 1 à 16 **de mon départ** » | `SourcePhase` prélève dans la phase amont, toutes vagues confondues |
| Le modèle de données | `TOURNOI ||--o{ PHASE : "séquence"` |

Concrètement : sur un tournoi de 4 départs de 100 archers, l'application produit **un** classement de
400, où l'archer du matin est rangé contre celui du soir qu'il n'a jamais affronté.

**Pourquoi personne ne l'a vu.** L'oracle 120 — le rejeu de `Tableaux.xlsx`, garde-fou le plus solide
du projet (règle 9) — ne contient **aucun départ** (zéro occurrence dans le test). Il valide un
tournoi **mono-départ**, cas où portée tournoi et portée départ se **confondent**. Le modèle était
donc juste par accident, et le seul test capable de révéler l'écart ne l'exerçait pas.

**C'est le vrai enseignement de cet ADR, et il dépasse le sujet du départ** : une décision d'ADR
n'était reliée à **aucun** module chargé de la porter, et aucun test ne couvrait le cas qui les
distingue. Une décision écrite mais non rattachée au code n'est pas une décision, c'est une
intention — et elle diverge en silence, d'autant plus vite que le projet grossit.

## Décision

**Le départ est la portée sportive du tournoi.** Un départ est une *exécution complète* de la
compétition : il a sa séquence de phases, ses classements, ses tableaux, ses duels et son podium. Les
archers de deux départs ne sont jamais comparés.

1. **`Phase` appartient au départ** (`depart_id`), plus au tournoi. `SequencePhases` valide la suite
   contiguë 1..N **d'un départ** ; ses invariants sont inchangés, seule leur portée l'est.
2. **Le classement se calcule par départ.** `calculer_classement` reste une fonction pure sur un lot
   d'archers — c'est l'**appelant** qui ne lui passe plus que les archers d'un départ. Le rang
   scratch et le rang de catégorie sont donc des rangs *dans le départ*.
3. **Tableaux, duels, barrages et suivi de déroulé suivent la phase**, donc le départ, sans autre
   changement que leur rattachement.
4. **Les prélèvements (`SourcePhase`) restent intra-départ.** « Les rangs 1 à 16 de la phase 1 »
   désigne les rangs 1 à 16 *de la phase 1 de ce départ*. Aucune source ne traverse un départ.
5. **Le tournoi reste le contenant** : identité, dates, club organisateur, inscriptions, copies du
   patrimoine, format appliqué. Il n'a plus de phases en propre — les siennes sont l'union de celles
   de ses départs.
6. **Appliquer un format crée une séquence par départ.** Les N départs partent de **copies
   identiques** du déroulé du format, puis vivent leur vie : ajuster la phase 2 du départ 1 ne touche
   pas le départ 2. C'est le même patron de copie que partout ailleurs dans le patrimoine
   (ADR-0060) — un cran plus bas.

### Ce qui a été écarté

- **Garder `Phase.tournoi_id` et ajouter `depart_id`.** Deux portées coexistantes obligeraient chaque
  lecture à choisir laquelle honorer, et la première qui se tromperait rétablirait le bug en silence.
  Une phase a **une** portée.
- **Scoper seulement le classement, en laissant les phases au tournoi.** C'est le correctif qui
  répare le symptôme visible et laisse la maladie : le `statut` d'une phase serait partagé, donc un
  départ en duels forcerait l'autre à l'être aussi alors qu'il qualifie encore.

## Conséquences

**Positives**

- Le code dit enfin ce qu'ADR-0017 avait décidé ; le mot « départ » a le même sens partout.
- Le format de tournoi (E01US025) peut porter un effectif **par départ** — sa notion naturelle,
  déjà présente sous le nom `Depart.quota`.
- Chaque départ étant étanche, plusieurs départs peuvent avancer **indépendamment** le jour J : le
  départ du matin peut être en duels pendant que celui de l'après-midi qualifie.

**Coûteuses / à surveiller**

- **Migration destructrice de portée** : les phases existantes doivent être rattachées à un départ.
  Les tournois **mono-départ** se migrent sans perte (leur unique départ reçoit la séquence) ; un
  tournoi **sans départ** ne peut pas conserver ses phases — cas traité explicitement par la
  migration, pas laissé au hasard.
- **Rupture d'API** : les routes de phases et de classement changent de parent
  (`/tournois/{id}/phases` → `/departs/{id}/phases`). Acceptable, l'application n'ayant aucun client
  tiers (mono-club, réseau local).
- **L'oracle 120 doit gagner un cas multi-départ.** Sans lui, cet ADR pourrait diverger comme
  ADR-0017 l'a fait.

### Remèdes contre la récidive (le point que l'organisateur a demandé)

Cette divergence a coûté cher parce que rien ne la rendait **visible**. Trois mesures, toutes
appliquées dans l'US qui porte cet ADR :

1. **Un ADR nomme les modules qui le portent.** Un champ « **Porté dans le code par** » listant les
   fichiers responsables. Un ADR qui n'en nomme aucun est une intention, pas une décision — et ça se
   voit en revue. ADR-0017 est amendé rétroactivement pour porter ce champ.
2. **Un test de conformité de portée** (`tests/test_portee_sportive.py`), sur le modèle du garde-fou
   d'isolation du domaine : il échoue si une phase, un classement ou un tableau redevient rattaché au
   tournoi. Mécanique, donc insensible à l'oubli.
3. **L'oracle gagne un scénario multi-départ**, parce que le cas qui distingue les deux portées doit
   être exercé par le test qui fait autorité — c'est son absence qui a permis douze ADR de silence.

## Porté dans le code par

- `backend/domain/phase.py` (`Phase.depart_id`, `SequencePhases`)
- `backend/domain/classement.py` + `backend/application/classements.py` (portée du classement)
- `backend/domain/tableau.py`, `backend/domain/duel.py` (rattachement des tableaux et duels)
- `backend/domain/format_tournoi.py` (`appliquer` produit une séquence par départ)
- `backend/infrastructure/db/repositories/moteur.py` + migration `0042`
- `backend/tests/test_portee_sportive.py` (garde-fou mécanique)
