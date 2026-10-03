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

> **Amendé le 01/10/2026 (E13US002, arbitrage du commanditaire en revue)** : seul le **nombre**
> d'archers est surchargeable, par équipe. La **contrainte** de composition (arme commune, mixité,
> sexe unique en standard) reste la règle FFTA, fixe — elle est **signalée**, jamais bloquante à la
> composition, si bien qu'une équipe hors règle s'enregistre en affichant ses écarts. La composition
> FFTA est au **§6.4** du référentiel (les « §6.3 » de cet ADR datent d'avant sa renumérotation).

**3. Le scoring d'équipe est une politique injectable, pas un cas particulier codé.** Le cumul
d'équipe et les **volées alternées** (FFTA §7) sont une implémentation de la politique `scoring`
([ADR-0004](0004-moteur-de-phases-politiques.md)), résolue par le couple (phase, type de participant).
Aucune branche `if équipe` dans le moteur : une politique de plus.

> **Amendé le 02/10/2026 (E13US003, arbitrage du commanditaire au cadrage)** : le score d'un match
> d'équipe n'est **pas** porté par la famille `scoring`, qui n'a aucun appelant de production
> (`DETTE-028`), mais par le **barème de duel** de la phase ([ADR-0117](0117-le-bareme-de-duel-est-un-reglage-d-etape-verrouille-au-premier-tir.md)),
> livré entre-temps. La volée d'un camp y est déjà le cumul de ses flèches, quel qu'en soit le
> tireur ; une phase d'équipes est une phase distincte, donc la dimension « type de participant »
> n'avait rien à départager. Seul manque comblé : le **barrage à N flèches** (1 par archer, §8.2).
> Les « volées alternées » sont un ordre de tir (§9), sans effet sur le score. Aucune branche
> `if équipe` : l'intention du point est tenue, sa lettre non. ⚠️ **Ce qui est perdu** : la
> résolution **automatique** par type de participant. Une phase d'équipes **non réglée** jouerait
> le barème individuel (`ResolveurBaremeDuelFfta` ne lit que l'arme) — **tranché le 03/10/2026** :
> le preset FFTA du type d'équipe ([ADR-0120](0120-une-phase-oppose-des-equipes-par-reglage-d-etape.md) §4).

**4. Placement, saisie et classement clés sur le participant.** En phase par équipes, le placement
pose des **équipes** (leurs archers sur des cibles voisines), la saisie enregistre une **volée
d'équipe**, le classement produit des **rangs d'équipe**. Chaque brique aval (EPIC-03/04/06) apprend à
traiter un participant qui n'est pas un individu — d'où la **coordination par un EPIC dédié**
(EPIC-13), les briques restant dans leurs EPICs respectifs.

## Conséquences

- **+** La précaution du cadrage **paie** : parce que le moteur était pensé « participants », l'ajout
  est une **réalisation**, pas une refonte — exactement ce que la porte ouverte visait.
- **+** Les équipes reposent sur l'existant (barème de duel — et non la politique `scoring`, cf.
  l'amendement du point 3 —, entité enfant du tournoi comme `Depart`/`Scoreur`) sans mécanisme
  neuf : cohérence du modèle.
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

## Suivi de réalisation

- **26/07/2026 — décision n°1 réalisée, ordonnancement honoré.** E13US001 pose l'abstraction
  `Participant` (value object `{genre, ref_id}`, `backend/domain/participant.py`) **avant** le moteur
  de duels, comme la conséquence ci-dessus l'exigeait. Le moteur d'élimination directe (E05US005)
  oppose des `Participant` — pas des archers en dur, pas de branche `if équipe` — de sorte que la
  précaution « le moteur ne se fige pas sur des archers » est tenue. `docs/modele-de-donnees.md`
  (entité MATCH) est aligné : `participant_a`/`participant_b` remplacent `archer_a_id`/`archer_b_id`.
  Restent à venir : l'entité `Equipe`/`MEMBRE_EQUIPE` et la composition (E13US002), le scoring
  d'équipe (E13US003), le placement/saisie/classement par équipe (E13US004).
- **01/10/2026 — décision n°2 réalisée (E13US002).** `Equipe` et `MEMBRE_EQUIPE` existent, avec
  une composition **signalée, pas bloquée** (le refus d'une équipe non conforme est renvoyé à
  l'engagement dans une phase, E13US004). Trois précisions tranchées au cadrage : le sexe et l'arme
  d'un membre sont lus sur **sa catégorie** ; l'effectif « configurable » est porté **par
  l'équipe** (défaut FFTA selon le type) ; un archer appartient à **une équipe par type**. Et une
  **restriction** tranchée en revue, qui amende le point 2 (cf. son encart) : seul l'effectif est
  surchargeable. « Engagé » couvre désormais l'appartenance à une équipe (glossaire) : la
  conséquence « deux notions d'engagé » s'est résolue en **une** notion élargie. Cf. `stories/E13-equipes.md` § E13US002.
- **02/10/2026 — décision n°3 réalisée, amendée (E13US003).** Barème d'équipe exprimé par
  `BaremeDuel` (presets FFTA équipe et mixte au réglage de phase), barrage à `nb_fleches_barrage`
  flèches par camp. Cf. l'encart du point 3 et `stories/E13-equipes.md` § E13US003.

## Porté dans le code par

> *Section ajoutée le 08/08/2026 (rétro-équipement des ADR structurants encore actifs). La règle
> « un ADR nomme les modules qui le portent » a été instituée le 06/08/2026 par
> [ADR-0075](0075-le-depart-est-la-portee-sportive.md) et n'avait pas été appliquée rétroactivement.
> Les modules ci-dessous ont été **vérifiés dans le code du jour**, pas déduits de l'ADR — nommer un
> module vide reproduirait exactement le défaut que la section existe pour empêcher.*

- `backend/domain/participant.py` — `Participant` (`genre` + `ref_id`, `frozen`) et
  `GenreParticipant`. Le moteur ne lit **que** l'identité, jamais pour décider d'un comportement.
- `backend/domain/tableau.py`, `backend/domain/duel.py` — les matchs opposent des `Participant`,
  conformément au point 1.

- `backend/domain/equipe.py` — `Equipe`, `TypeEquipe`, `EFFECTIF_FFTA` et la règle de composition
  `ecarts_de_composition` (point 2) ; `backend/application/equipes.py` (`ServiceEquipes`) tient les
  règles d'ensemble (nom unique, membre du tournoi, une équipe par type) ;
  `backend/infrastructure/db/repositories/equipes.py` (`EquipeRepositorySQL`) et la migration
  `0059_equipe` persistent `equipe` et `membre_equipe` ; `backend/api/v1/equipes.py` les expose ;
  `frontend/src/features/equipes/` est l'écran d'administration.
- `backend/domain/duel.py` — `BaremeDuel.nb_fleches_barrage` et `Barrage(fleches_haut,
  fleches_bas, …)` portent le point 3 tel qu'amendé : `_vainqueur_barrage` compare des **totaux**,
  `saisir_barrage` exige le compte du barème ; `frontend/src/shared/phases/baremeDuel.ts`
  (`presetFftaEquipe`, `presetFftaMixte`) pose les barèmes d'équipe FFTA.

🔴 **Cet ADR n'est pas encore porté en entier, et il faut le dire ici plutôt que le laisser croire.**
Les points 1 à 3 sont livrés ; le point 4 **n'a aucun module** :

| Point de la décision | État |
|---|---|
| 1. Le match oppose des participants | ✅ `domain/participant.py` |
| 2. `Equipe` est une entité du tournoi (+ `MEMBRE_EQUIPE`) | ✅ tel qu'amendé le 01/10/2026 — `domain/equipe.py`, `application/equipes.py`, `E13US002`. Effectif surchargeable par équipe ; règles d'arme et de sexe **fixes** (FFTA), signalées seulement. La surcharge de la *contrainte* promise par la rédaction d'origine n'est **pas** portée : elle a été **abandonnée**, pas oubliée |
| 3. Score d'équipe sans branche `if équipe` (amendé : barème de duel, pas la famille `scoring`) | ✅ tel qu'amendé le 02/10/2026 — barème de duel (`domain/duel.py`), pas la famille `scoring`. `E13US003` |
| 4. Placement / saisie / classement clés sur le participant | ◐ le **tableau à élimination directe** seul, `E13US004` ([ADR-0120](0120-une-phase-oppose-des-equipes-par-reglage-d-etape.md)) — `domain/engagement_equipes.py`, `application/saisie_duels.py`, `application/placement_duels.py`, `application/pilotage_tour.py`. Poules, suisse, colline, Big Shoot Off, palmarès et affectations publiques : ⬜ `E13US005` |

⚠️ **Une équipe ne se joue qu'en tableau à élimination directe** (E13US004). Seul
`ServiceSaisieDuels` construit `Participant.equipe(...)` ; les autres formats, le palmarès et les
affectations publiques ignorent encore les équipes. Un lecteur qui verrait un tableau d'équipes
se jouer pourrait conclure que tout format les accepte — pas avant `E13US005`. C'est le mode de défaillance
d'ADR-0017 (une décision que seule une partie du code porte), et la seule parade est de l'écrire.
