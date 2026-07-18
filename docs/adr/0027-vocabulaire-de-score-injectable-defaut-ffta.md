# ADR-0027 — Le vocabulaire de score est injectable par tournoi ; défaut FFTA

- **Statut** : Accepté
- **Date** : 2026-07-18
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E01-configuration.md`](../../stories/E01-configuration.md) (E01US014 — note de
  renvoi ; **E01US018** nouvelle) ; [`docs/modele-de-donnees.md`](../modele-de-donnees.md)
  (`BLASON.zones`, vocabulaire porté par le tournoi ; `PHASE.config.scoring`) ;
  [`docs/referentiel-ffta.md`](../referentiel-ffta.md) §4.2, §10.
- **Introduit par** : E01US018 (vocabulaire de score configurable par tournoi).
- **Révise** : [ADR-0020](0020-blason-zones-vocabulaire-ferme-et-defaut-sur-ensemble.md) **point 1**
  (l'énuméré `ZoneScore` **fermé** en dur) et la constante `VALEUR_FLECHE_MAX = 10` de
  `domain.bareme`. Les points 2 à 6 d'ADR-0020 (règles structurelles, défaut = sur-ensemble, édition =
  remplacement, relecture rejouée) **restent valides** — ils s'appliquent désormais au vocabulaire
  *configuré* au lieu de l'enum figé. Prolonge l'esprit d'[ADR-0004](0004-moteur-de-phases-politiques.md)
  (les politiques du moteur sont injectables) et le principe directeur du référentiel §10 (« le
  règlement entre comme un **template**, pas une contrainte »).

## Contexte et problème

ADR-0020 a figé les valeurs de score en un énuméré **fermé** (`10`…`1` + `M`), et `domain.bareme`
plafonne la flèche à `VALEUR_FLECHE_MAX = 10` (constante). C'était **cohérent** tant que le seul
règlement visé était la FFTA salle. Mais deux besoins le débordent (remontée du 18/07/2026) :

- l'application doit composer **n'importe quel format** (CDC ligne 27, règle 2) — or certains formats
  n'ont ni le même maximum (un « 11 » existe sur certains blasons/formats) ni les mêmes zones ;
- le principe directeur du référentiel (§10) veut que **rien de FFTA n'entre comme contrainte**. Un
  vocabulaire de score gravé dans un enum Python **est** une contrainte : impossible de le déborder
  sans toucher au code.

Le problème : un énuméré fermé donne des garanties précieuses (mypy détecte `zones=("foo",)`, la
frontière rejette en **400** avant le domaine — ADR-0020 pt 1). Les rendre **configurables**, c'est
**renoncer à ces garanties statiques**. C'est l'arbitrage. Il a été soumis à l'organisateur, qui a
tranché : *« évite l'enum figé, place-le en paramètre injectable, avec par défaut les valeurs FFTA »*.

## Décision

**1. Le vocabulaire de score devient une donnée du tournoi, injectée, défaut FFTA.** Les valeurs
admissibles (`10 → 1` + `M` en FFTA salle) ne sont plus un énuméré gravé mais un **jeu configuré**,
rattaché au tournoi (résolu par la politique `scoring`, [ADR-0004](0004-moteur-de-phases-politiques.md)).
À la création d'un tournoi, il est **pré-rempli** avec le vocabulaire FFTA — exactement comme les
catégories et barèmes (référentiel §10, template modifiable). L'admin peut le **surcharger**.

**2. Le maximum de flèche se *dérive* du vocabulaire, il ne se déclare plus.** `score_max` d'un
barème = `nb_flèches_total × max(valeurs marquantes du vocabulaire)`. La constante
`VALEUR_FLECHE_MAX = 10` disparaît au profit de ce calcul ; « 10 » n'est plus qu'une **valeur par
défaut**, comme `PRESET_FFTA_18M_NB_VOLEES = 20` l'est déjà pour le barème (le preset n'est pas la
contrainte — cf. `domain.bareme`).

**3. Les règles d'intégrité d'ADR-0020 survivent, mais changent de gardien.** `M` (manqué) toujours
présent, au moins une zone marquante, pas de doublon, ordre canonique (centre → extérieur) : **règles
conservées** (leur motif — *restreindre la saisie*, intégrité aval — est intact). Mais un vocabulaire
ouvert ne peut plus être validé par un `Enum` à la **frontière (400)** : cette validation **descend au
domaine/service (422)**. C'est la contrepartie assumée du point 1 : on troque une garantie *statique*
(mypy + 400) contre une validation *dynamique* (422), au bénéfice de l'ouverture des formats.

**4. Les `zones` d'un blason restent un sous-ensemble du vocabulaire du tournoi.** Un triple 40
restreint à `10 → 6` reste un **sous-ensemble** ; ce qui change, c'est que le **sur-ensemble** de
référence n'est plus l'enum global mais le vocabulaire **configuré du tournoi**. Le défaut à la
création d'un blason (ADR-0020 pt 4, le sur-ensemble) devient : *le vocabulaire du tournoi*.

## Conséquences

- **+** Le moteur peut porter des formats à barème non-FFTA (« 11 », zones exotiques) **sans toucher au
  code** — le vocabulaire est de la configuration (règle 2, référentiel §10). C'est ce qui rend
  crédibles les formats (b)/(c) du catalogue E05 (poules, handicap, king of the hill…).
- **+** Une seule source de vérité pour « quelles valeurs existent dans ce tournoi », partagée par le
  pavé de saisie (EPIC-04), les blasons et le calcul de `score_max`.
- **−** **Perte des garanties statiques d'ADR-0020 pt 1** : plus de détection mypy d'une zone
  invalide, plus de rejet 400 à la frontière. La validation devient dynamique (422) contre le
  vocabulaire configuré. C'est le prix explicite de l'ouverture — à ne pas regretter en revue.
- **−** **E01US014 et le barème sont livrés** : généraliser l'enum en vocabulaire configuré est une
  **migration** (colonne/JSON de vocabulaire par tournoi, backfill FFTA). Portée par **E01US018** ;
  E01US014 reçoit une note de renvoi. Tant qu'E01US018 n'est pas faite, le comportement observable ne
  change pas (le défaut FFTA = l'enum actuel).
- **−** Deux niveaux de configuration coexistent désormais (vocabulaire du **tournoi**, `zones` du
  **blason** qui en est un sous-ensemble) : à documenter clairement pour ne pas les confondre.
- **Hors périmètre** : la **mouche (X)** reste hors vocabulaire de score (ADR-0020 pt 1, §4.3 — un
  diamètre, pas une valeur) ; si un départage au nombre de X arrive, il naîtra en EPIC-06.
