# ADR-0050 — Forfait unifié (abandon / disqualification), scopé à la phase

- **Statut** : Accepté
- **Date** : 2026-07-27
- **Décideurs** : Organisateur / Architecte
- **Portée** : E04US015 (gérer abandon / disqualification)
- **Complète / amende** : [ADR-0016](0016-supprimer-un-archer-engage-plutot-que-le-refuser.md)
  (forfait ≠ suppression : le forfait **préserve** les flèches) ; **absorbe E12US004** (« tracer un
  forfait en duels »), qui n'est plus une US distincte
- **Lie** : [ADR-0049](0049-saisie-et-scoring-des-duels.md) (reconstruction/rejeu du tableau),
  E06US001 (classement), E12US005 (complétude — DETTE-014), E10US005 (audit `FORFAIT`)

## Contexte et problème

E04US015 (« abandon / DSQ en qualification ») et E12US004 (« tracer un forfait en duels ») étaient
deux US, séparées au regroupement de maille du 17/07/2026 parce qu'E04US015 est **ancrée par
ADR-0016** (qui lui fait porter l'abandon en qualification *et*, via E12US004, aux duels). La story
d'E04US015 signalait explicitement une **incohérence latente « à arbitrer »** : son jalon (J2) et sa
dépendance affichée (E04US013, saisie en duels) contredisaient le « abandon en **qualification** » de
sa note — le seul cas exerçable *avant* les duels.

Au cadrage (27/07/2026), l'organisateur a tranché : **traiter les deux contextes dans une seule US**.
La question devient donc de conception : comment modéliser un « forfait » qui vaut en qualification
**et** en duels sans que l'un fausse l'autre ?

Le piège central : un forfait est un fait sur un `(tournoi, archer)`. Mais un archer peut **terminer
sa qualification normalement** puis **abandonner en duels**. Un modèle « forfait global au tournoi »
reléguerait alors, à tort, son **rang de qualification** — qu'il avait pourtant mérité.

## Décision

**Un seul concept `Forfait`**, agrégat de domaine immuable, **scopé à une phase** (`phase_id`) :

- `nature` ∈ { `abandon`, `disqualification` } — porte l'effet sur le **classement** ;
- **daté** (`declare_le`, UTC via le port `Horloge`), **attribué** (`declare_par`, un **nom**, pas
  une FK — la trace survit à la suppression du scoreur, comme l'audit), **motif** optionnel ;
- **réversible** : l'annulation **supprime** la déclaration (les flèches, `serie`/`volee`, ne sont
  **jamais** touchées) — pas un troisième état ; interdite si le tournoi est **terminé** (`D-15`).

Un même concept, lu par **trois** endroits selon la phase où le forfait est déclaré :

1. **Classement de qualification** (`domain.classement`) — lit les forfaits **de la phase de
   qualif** : un **abandon** est **relégué en fin** (rangé, derrière tous les en-lice, score
   affiché — Q2) ; une **DSQ** est **sortie** du classement (`rang_* = None`, listée avec son statut
   et son score — Q3). Les deux **préservent** les flèches.
2. **Reconstruction du tableau** (`ServiceSaisieDuels`) — lit les forfaits **de la phase de
   tableau** : le duelliste forfait **cède** son match (walkover), l'adversaire passe d'office
   (analogue à un bye), le tableau reste cohérent. Les forfaits de **qualif** sont, eux, **exclus à
   l'ensemencement** (un abandon en qualif n'entre pas dans le bracket).
3. **Complétude** (`ServiceCompletude`) — un archer forfait en qualif a sa série **close par
   forfait** malgré ses volées partielles : sa cible n'est plus « à finir » à jamais. **DETTE-014
   résorbée.**

Le scope `phase_id` est **ce qui rend la fusion correcte** : un forfait en duels ne relègue pas le
rang de qualif (les lecteurs filtrent par phase), un abandon en qualif ne s'invente pas de match.

**Acteur — deux régimes depuis E16US008 (28/08/2026)** :

- **en qualification**, le **scoreur seul** (`exiger_scoreur`), dans **son** tournoi
  (`403 scoreur_hors_tournoi`) — cohérent avec la validation (E04US002/E04US013). *(Résout `Q-UX5`
  d'E12US004, qui laissait l'acteur « admin par défaut » ouvert : le scoreur est celui qui, sur le
  terrain, constate l'abandon.)* Aucun écran d'administration ne le demande : on n'ouvre pas une
  autorisation sans appelant.
- **en duels**, **l'admin *ou* le scoreur** (`autoriser_forfait_duel`), déclaration **et** annulation
  (`D-15` : qui peut déclarer doit pouvoir défaire). L'organisateur doit lever un duel bloqué depuis
  le feu vert sans aller chercher un scoreur. C'est un **élargissement de la route existante**, au
  patron d'[ADR-0030](0030-saisie-autorisee-au-poste-de-cible-403-hors-cible.md), et non une
  route parallèle : deux routes vers la même écriture tiendraient idempotence, audit et règles
  métier en double. L'admin n'est borné à aucun tournoi (le secret vaut pour l'instance, `D-13`), la
  garde `scoreur_hors_tournoi` ne s'appliquant donc qu'au scoreur ; `declare_par` vaut
  `"Administrateur"`, sans quoi la trace d'audit cesse de distinguer les deux origines.

⚠️ La route des duels **refuse une phase de qualification** (`phase.type is QUALIFICATION` →
`PhaseIntrouvable`). Le `phase_id` vient du client : sans ce refus, elle écrirait un forfait relu par
le classement de qualification et contournerait `exiger_scoreur`, seule garde de l'autre route.
*(Trou trouvé en revue d'E16US008, axe A — le bornage « admin en duels seulement » était asséré par
un test qui ne couvrait qu'une des deux portes.)*

**Atomicité acte↔trace** (ADR-0035) : déclarer/annuler co-écrivent une entrée d'audit `FORFAIT` dans
**une seule transaction** (port `ForfaitRepository.declarer_avec_trace` / `annuler_avec_trace`,
adapter à session partagée — infra→infra, comme la série).

**Unicité** `(tournoi, archer, phase)` : re-déclarer lève `ForfaitDejaDeclare` (409). Changer la
nature (abandon ↔ DSQ) = **annuler puis re-déclarer** — deux traces plutôt qu'une mutation muette.

## Conséquences

- **+** Le geste que l'ADR-0016 appelait de ses vœux existe : un archer qui abandonne n'est plus
  effacé (« le bouton Supprimer sans le forfait »), il est **statué**, flèches conservées.
- **+** Un seul concept, une seule table (`forfait`, migration 0031), trois lecteurs — pas de
  duplication entre « abandon qualif » et « forfait duels ».
- **+** Réversibilité gratuite : le classement et le tableau étant **dérivés**, annuler un forfait
  fait disparaître la relégation ou le walkover à la reconstruction suivante.
- **−** Les **rangs deviennent nullables** (`LigneClassement.rang_* : int | None`, DTO et front
  compris) : une DSQ n'a pas de rang. Ripple assumé (competition DTO, `TableClassement`, seeding).
- **−** **E12US004 disparaît** du backlog (absorbée). Le tracker la marque « absorbée », `stories/`
  et `journal` réconciliés dans le même commit (sinon CA périmé — règle 9).
- **−** **Deux forfaits face à face** en duels (rare) : le camp **haut** avance par convention (lui
  même walkover en aval s'il reste forfait). Documenté dans `_appliquer_forfaits`.
- **−** Le **motif** n'est pas exposé à l'UI en v1 (API prête) ; l'abandon en duels n'a pas de file
  hors-ligne dédiée (à rebours de la saisie de duels) — acte rare, hors chemin critique jour J.
- **−** FK `forfait.tournoi_id`/`archer_id` **sans `ON DELETE`** (DETTE-001, comme `serie`) :
  supprimer un archer porteur d'un forfait échouerait sur la FK — même dette latente que la série.

## Alternatives écartées

1. **Forfait global au tournoi** (sans `phase_id`). Écartée : reléguerait le rang de qualif d'un
   archer abandonnant *en duels* — exactement le piège identifié.
2. **Garder E04US015 (qualif) et E12US004 (duels) séparées** (respecter ADR-0016 à la lettre).
   Écartée par l'organisateur au cadrage : le même concept, la même table, le même audit — deux US
   auraient dupliqué la mécanique pour un gain nul.
3. **Un drapeau `actif` plutôt qu'une suppression à l'annulation.** Écarté : un troisième état sans
   valeur (les flèches ne sont jamais détruites, il n'y a rien à « désarchiver ») ; la suppression +
   trace d'audit dit tout ce qu'il faut.

## Porté dans le code par

*(Vérifié dans le code du 28/08/2026, pas déduit de la décision.)*

| Module | Ce qu'il porte |
|---|---|
| `backend/domain/forfait.py` | `Forfait`, `NatureForfait` ; le scope `(tournoi, archer, phase_id)` qui rend la fusion correcte |
| `backend/application/forfaits.py` | `ServiceForfait` — les deux contextes (`declarer_en_qualification` / `declarer_en_duel` et leurs annulations), l'unicité (`ForfaitDejaDeclare`), `AUTEUR_ADMIN`, et `_exiger_phase_de_tableau` qui n'admet que **`TYPES_EN_TABLEAU_JOUE`** (ADR-0083) sur le chemin des duels — miroir exact de la surface de lecture |
| `backend/api/dependances.py` | `autoriser_forfait_duel` (admin **ou** scoreur, `Scoreur \| None`) ; `exiger_scoreur` reste sur la qualification |
| `backend/api/v1/forfaits.py` | Les quatre routes ; `_garder_tournoi` (garde de tournoi appliquée **au seul scoreur**) et `_auteur` (`declare_par`) |
| `backend/application/classements.py` | `_forfaits_qualif` — le lecteur « qualification » (relégation/exclusion) |
| `backend/application/saisie_duels.py` | `_appliquer_forfaits` — le lecteur « duels » (walkover). ⚠️ **Saute un match dont un camp est vide** : un forfait y est écrit sans effet visible, ce que le front doit refuser d'offrir |
| `backend/application/completude.py` | Clôture par forfait de la série en qualif (DETTE-014 résorbée) |
| `backend/infrastructure/db/repositories/tir.py` | `ForfaitRepositorySQL.declarer_avec_trace` / `annuler_avec_trace` — l'**atomicité acte↔trace** promise par la Décision (ADR-0035) ; port en `backend/domain/ports.py` |
| `frontend/src/features/feu-vert/hooks.ts` | `useDeclarerForfaitDepuisFeuVert` — **c'est ici, et nulle part ailleurs, que vit la portée `'admin'`** |
| `frontend/src/features/feu-vert/{etat.ts,FeuVert.tsx}` | `archersForfaitables` / `deplier` (`etat.ts`) — quels archers sont **déclarables** : le forfait exige les deux camps, le dépliage dit le camp connu ; `ActionLevee` (`FeuVert.tsx`) — le dialogue qui avertit de l'irréversibilité |
| `backend/tests/test_forfaits_api.py` | Les bornes : qualification fermée à l'admin, phase de qualif refusée sur la route duel, scoreur hors tournoi, anonyme refusé |

⚠️ **Ce qui n'est porté par rien** : aucun écran n'**annule** un forfait de duel — l'élargissement de
`D-15` est livré côté serveur et testé, sans appelant produit (`DETTE-090`).

## Liens

[ADR-0016](0016-supprimer-un-archer-engage-plutot-que-le-refuser.md) (forfait ≠ suppression) ;
[ADR-0035](0035-atomicite-acte-trace-session-partagee.md) (co-écriture acte↔trace) ;
[ADR-0049](0049-saisie-et-scoring-des-duels.md) (reconstruction/rejeu du tableau) ;
`backend/domain/forfait.py`, `backend/domain/classement.py` (`StatutClassement`),
`backend/application/forfaits.py`, `backend/api/v1/forfaits.py` ;
[`docs/dette.md`](../dette.md) (DETTE-014) ; [`docs/glossaire.md`](../glossaire.md) (*Forfait*,
*Abandon*, *Disqualification*).
