# ADR-0028 — Épreuves par équipes dans le périmètre : le match oppose des *participants*

- **Statut** : Accepté
- **Date** : 2026-07-18
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`cahier-des-charges.md`](../../cahier-des-charges.md) (EF-6.x — les équipes quittent
  « hors périmètre » ; RG à ajuster) ; [`docs/referentiel-ffta.md`](../referentiel-ffta.md) (§10, note
  « épreuves par équipes hors périmètre » → **in-scope**) ; [`cahier-des-charges-technique.md`](../../cahier-des-charges-technique.md)
  (§5, `MATCH.participant_A/B`) ; [`docs/modele-de-donnees.md`](../modele-de-donnees.md) (entités
  `EQUIPE`, `MEMBRE_EQUIPE` ; `MATCH` sur participants) ; nouveaux [`epics/EPIC-13-equipes.md`](../../epics/EPIC-13-equipes.md)
  et [`stories/E13-equipes.md`](../../stories/E13-equipes.md).
- **Introduit par** : E13US001 (abstraction participant).
- **Renverse** : la décision de cadrage du 14/07/2026 qui plaçait les épreuves par équipes **hors
  périmètre** (CDC §10 / référentiel §10 : « la porte reste ouverte »). L'organisateur a tranché le
  18/07/2026 : **les équipes entrent dans le MVP**.
- **S'appuie sur** : [ADR-0004](0004-moteur-de-phases-politiques.md) (politiques injectables — le
  scoring d'équipe en est une) ; la **porte** déjà prévue par le cadrage (le moteur devait « pouvoir
  opposer des participants qui ne sont pas des archers », CDC §10) — cet ADR la **franchit** au lieu de
  la laisser entrouverte.

## Contexte et problème

Le cadrage du 14/07/2026 a **volontairement** exclu les épreuves par équipes (matchs à 3 archers,
équipes mixtes — FFTA §6.3, §7), en ne gardant qu'une **précaution architecturale** : que le moteur de
duels oppose des *participants* et non des *archers*, pour qu'un ajout ultérieur « ne soit pas une
refonte » (CDC §10, ligne 231). L'organisateur a **rouvert** ce point le 18/07/2026 et décidé de
livrer les équipes **dans le MVP**.

Deux faits rendent la décision jouable, là où d'autres formats resteraient bloqués :

- **La règle existe et est écrite** — FFTA §6.3 et §7 (composition, volées alternées, cumul d'équipe).
  Contrairement au Big Shoot Off (bloqué faute de règle, référentiel §11) ou aux formats exotiques du
  catalogue E05, une épreuve par équipes a un **oracle** possible (règle 9).
- **La porte était déjà dessinée** : « opposer des participants » est une abstraction anticipée, pas
  une idée neuve.

Mais le coût est réel et **transverse** : un participant-équipe touche l'inscription (former l'équipe),
le placement (poser une équipe sur des cibles), la saisie (volée d'équipe), le classement (rangs
d'équipe) et le moteur (peuplement/routage sur participants). Ce n'est pas une US, c'est un **EPIC**.

## Décision

**1. Le match oppose des *participants*, jamais des archers en dur.** Le domaine du moteur (EPIC-05)
manipule un `Participant` — **soit** un archer individuel, **soit** une équipe. Le modèle porte
`MATCH.participant_A/B` (CDC technique §5), pas `archer_a/archer_b`. Un tournoi individuel est le cas
où chaque participant **est** un archer : l'abstraction ne complique pas le cas simple, elle le
**contient**.

**2. L'équipe est une entité du tournoi, nommée, composée d'archers.** `Equipe` (`tournoi_id`, `nom`,
membres) + table `MEMBRE_EQUIPE`. Composition selon la règle FFTA (§6.3/§7 : typiquement **3 archers**,
ou **équipe mixte** 2 archers H/F). Le nombre et la contrainte de composition sont **de la
configuration** (vocabulaire fermé FFTA en défaut, surchargeable — cohérent avec le principe
« template » du référentiel §10).

**3. Le scoring d'équipe est une politique injectable, pas un cas particulier codé.** Le cumul
d'équipe et les **volées alternées** (FFTA §7) sont une implémentation de la politique `scoring`
([ADR-0004](0004-moteur-de-phases-politiques.md)), résolue par le couple (phase, type de participant).
Aucune branche `if équipe` dans le moteur : une politique de plus.

**4. Placement, saisie et classement clés sur le participant.** En phase par équipes, le placement
pose des **équipes** (leurs archers sur des cibles voisines), la saisie enregistre une **volée
d'équipe**, le classement produit des **rangs d'équipe**. Chaque brique aval (EPIC-03/04/06) apprend à
traiter un participant qui n'est pas un individu — d'où la **coordination par un EPIC dédié**
(EPIC-13), les briques restant dans leurs EPICs respectifs.

## Conséquences

- **+** La précaution du cadrage **paie** : parce que le moteur était pensé « participants », l'ajout
  est une **réalisation**, pas une refonte — exactement ce que la porte ouverte visait.
- **+** Les équipes reposent sur l'existant (politique `scoring`, entité enfant du tournoi comme
  `Depart`/`Scoreur`) sans mécanisme neuf : cohérence du modèle.
- **−** **Périmètre MVP nettement élargi.** L'abstraction participant touche EPIC-03/04/05/06 ; la
  livraison des équipes est un **programme** (EPIC-13 le coordonne), pas une US. À budgéter comme tel.
- **−** L'abstraction `Participant` doit être posée **avant** que le moteur de duels (E05US005) ne se
  fige sur des archers — sinon la précaution est perdue et l'on retombe dans la refonte que le cadrage
  voulait éviter. D'où **E13US001 en dépendance amont d'E05US005**.
- **−** Deux notions d'« engagé » cohabiteront (archer inscrit ; équipe formée) : à cadrer au
  glossaire pour ne pas confondre inscription individuelle et appartenance à une équipe.
- **Hors périmètre de cet ADR** : le **détail** des règles de composition et de tir alterné (porté par
  les US d'EPIC-13, dérivé du référentiel §6.3/§7) ; le classement mixte individuel + équipes d'un même
  tournoi (si besoin, EPIC-06).
