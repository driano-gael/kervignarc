# E03 — Placement des archers & plan de cibles — User Stories

> EPIC : [EPIC-03](../epics/EPIC-03-placement.md) · Réfs : CDC fonctionnel M4, prototype `blason.py`/`player.py`.

> ⚠️ **Maille révisée le 17/07/2026** — regroupement des US au grain « capacité » (10 → 6). Les
> anciennes US découpées par étape technique (modéliser / placer / signaler / ajuster / générer le
> plan…) sont devenues des **critères d'acceptation** de l'US de capacité qui les porte. **Aucun
> comportement n'est perdu** (règle 9 — chaque ancien titre = une puce CA identifiée). Correspondance
> ancien → nouveau en fin de fichier. Aucune US de cet epic n'était livrée avant ce refactor : c'est
> un pur regroupement de backlog, sans impact sur du code existant.

---

### E03US001 — Placement automatique & plan de cibles
*En tant qu'*administrateur, *je veux* que le système instancie les cibles/positions depuis le
gabarit, place automatiquement les archers en respectant capacité et fractions de blason, signale
les conflits qu'il ne peut résoudre, et produise le plan de cibles de la qualification, *afin de*
disposer d'un plan exploitable sans saisie manuelle.
- **CA — cibles/positions (ex-001)** : à partir du gabarit (E01US007), génération des `Cible`
  (index, capacité) et positions A/B/C/D.
- **CA — capacité & fraction (ex-002)** : somme des fractions de blasons d'une cible ≤ capacité ;
  chaque archer reçoit cible + position + départ.
- **CA — conflits (ex-003)** : si une contrainte ne peut être satisfaite, un rapport liste les
  archers/cibles en conflit (pas d'échec silencieux).
- **CA — plan de cibles (ex-008)** : vue par cible listant archers + positions + départ ; source
  des exports (E09US003).
- **Notes** : entité `Cible` ; `position` (ex-`lettre` du prototype) — ex-001. Algo de placement
  dans `domain/placement`, pur et testable — ex-002. **L'ex-E03US008 est absorbée ici** : ses
  nombreux liens entrants (E09US002/003, E07US003/006, E04US001, E12US001/US00x) référencent
  aujourd'hui « E03US008 » et devront être redirigés vers **E03US001** — hors périmètre de ce
  refactor de maille, qui ne touche que ce fichier (cf. contrat, point 7) ; à traiter dans une passe
  globale dédiée.
- **Absorbe** : ex-E03US001 à 003, E03US008. **Dépend de** : E01US007, E02US004 · **Jalon** : J1

### E03US004 — Ajuster le placement (glisser-déposer)
*En tant qu'*administrateur, *je veux* déplacer un archer à la main et être empêché par l'UI si le
déplacement viole les règles, *afin d'*affiner le placement auto sans le casser.
- **CA — glisser-déposer (ex-004)** : drag & drop d'un archer d'une position à une autre ;
  persistance via la file ; mise à jour live.
- **CA — déplacement invalide (ex-005)** : un déplacement violant capacité/fraction est refusé
  avec message ; état inchangé.
- **Notes** : front feature `placement`.
- **Absorbe** : ex-E03US004, E03US005. **Dépend de** : E03US001 · **Jalon** : J1

### E03US006 — Contrainte ≥ 2 clubs par cible
*En tant qu'*administrateur, *je veux* au moins 2 clubs par cible quand c'est possible, *afin d'*
assurer la mixité.
- **CA** : le placement auto favorise ≥ 2 clubs/cible ; signalé si impossible.
- **Dépend de** : E03US001 · **Jalon** : J2

### E03US007 — Contrainte séparation catégorie/blason
*En tant qu'*administrateur (officiel), *je veux* cloisonner par catégorie/blason, *afin de*
respecter les règles officielles.
- **CA** : sur une cible, respect du blason associé à la catégorie ; conflits signalés.
- **Notes** : ordre de priorité des contraintes à confirmer (question ouverte EPIC-03).
- **Dépend de** : E03US001, E01US006 · **Jalon** : J3

### E03US009 — Placer les duellistes côte à côte
*En tant qu'*administrateur, *je veux* que les adversaires d'un duel soient sur des positions
voisines, *afin de* faciliter les matchs.
- **CA** : lors d'une phase de tableau, les 2 duellistes sont placés côte à côte dans la mesure du
  possible.
- **Dépend de** : E03US001, E05US007 · **Jalon** : J2

### E03US010 — Générer / éditer le déroulé horaire
*En tant qu'*administrateur, *je veux* un déroulé horaire de la journée, *afin de* cadencer
l'événement.
- **CA** : grille horaire par phase/tour ; éditable manuellement (génération auto en option —
  question ouverte).
- **Dépend de** : E05US002 · **Jalon** : J4

---

## Correspondance ancien → nouveau (maille du 17/07/2026)

| Ancienne US | Titre d'origine | Devient |
|---|---|---|
| E03US001 | Modéliser cibles/positions depuis le gabarit | **E03US001** — CA « cibles/positions » |
| E03US002 | Placement auto : capacité + fraction de blason | **E03US001** — CA « capacité & fraction » |
| E03US003 | Placement auto : signaler les conflits | **E03US001** — CA « conflits » |
| E03US004 | Ajuster le placement en glisser-déposer | **E03US004** — CA « glisser-déposer » |
| E03US005 | Empêcher un déplacement invalide | **E03US004** — CA « déplacement invalide » |
| E03US006 | Contrainte ≥ 2 clubs par cible | **E03US006** (inchangée) |
| E03US007 | Contrainte séparation catégorie/blason | **E03US007** (inchangée) |
| E03US008 | Générer le plan de cibles (qualif) | **E03US001** — CA « plan de cibles » |
| E03US009 | Placer les duellistes côte à côte | **E03US009** (inchangée) |
| E03US010 | Générer / éditer le déroulé horaire | **E03US010** (inchangée) |

**Redirections de liens entrants à appliquer** (passe globale, hors périmètre de ce fichier) :
`stories/E04-saisie-scores.md` (E04US001 dép `E03US008`→`E03US001`) ; `stories/E09-exports.md`
(deux dép `E03US008`→`E03US001`) ; `stories/E07-affichage-public.md` (deux dép `E03US008`→
`E03US001`) ; `stories/E12-pilotage-jour-j.md` (deux dép `E03US008`→`E03US001`) ;
`stories/README.md` (index des US002/003/005/008 à mettre à jour) ; `docs/adr/0017-le-depart-est-
un-creneau-du-tournoi.md` (mention `E03US008`→`E03US001`).
