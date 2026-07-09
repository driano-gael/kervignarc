# E03 — Placement des archers & plan de cibles — User Stories

> EPIC : [EPIC-03](../epics/EPIC-03-placement.md) · Réfs : CDC fonctionnel M4, prototype `blason.py`/`player.py`.

---

### E03US001 — Modéliser cibles/positions depuis le gabarit
*En tant que* système, *je veux* instancier les cibles et positions d'un tournoi depuis son gabarit, *afin de* disposer d'emplacements à peupler.
- **CA** : à partir du gabarit (E01US007), génération des `Cible` (index, capacité) et positions A/B/C/D.
- **Notes** : entité `Cible` ; `position` (ex-`lettre` du prototype).
- **Dépend de** : E01US007 · **Jalon** : J1

### E03US002 — Placement auto : capacité + fraction de blason
*En tant qu'*administrateur, *je veux* un placement automatique respectant capacité et fractions, *afin de* remplir les cibles correctement.
- **CA** : somme des fractions de blasons d'une cible ≤ capacité ; chaque archer reçoit cible + position + départ.
- **Notes** : algo dans `domain/placement` ; pur, testable.
- **Dépend de** : E03US001, E02US004 · **Jalon** : J1

### E03US003 — Placement auto : signaler les conflits
*En tant qu'*administrateur, *je veux* être alerté des infaisabilités, *afin de* corriger le placement.
- **CA** : si une contrainte ne peut être satisfaite, un rapport liste les archers/cibles en conflit (pas d'échec silencieux).
- **Dépend de** : E03US002 · **Jalon** : J1

### E03US004 — Ajuster le placement en glisser-déposer
*En tant qu'*administrateur, *je veux* déplacer un archer à la main, *afin d'*affiner le placement auto.
- **CA** : drag & drop d'un archer d'une position à une autre ; persistance via la file ; mise à jour live.
- **Notes** : front feature `placement`.
- **Dépend de** : E03US002 · **Jalon** : J1

### E03US005 — Empêcher un déplacement invalide
*En tant qu'*administrateur, *je veux* que l'UI refuse un déplacement contraire aux règles, *afin de* garder un placement valide.
- **CA** : un déplacement violant capacité/fraction est refusé avec message ; état inchangé.
- **Dépend de** : E03US004 · **Jalon** : J1

### E03US006 — Contrainte ≥ 2 clubs par cible
*En tant qu'*administrateur, *je veux* au moins 2 clubs par cible quand c'est possible, *afin d'*assurer la mixité.
- **CA** : le placement auto favorise ≥ 2 clubs/cible ; signalé si impossible.
- **Dépend de** : E03US002 · **Jalon** : J2

### E03US007 — Contrainte séparation catégorie/blason
*En tant qu'*administrateur (officiel), *je veux* cloisonner par catégorie/blason, *afin de* respecter les règles officielles.
- **CA** : sur une cible, respect du blason associé à la catégorie ; conflits signalés.
- **Notes** : ordre de priorité des contraintes à confirmer (question ouverte EPIC-03).
- **Dépend de** : E03US002, E01US006 · **Jalon** : J3

### E03US008 — Générer le plan de cibles (qualif)
*En tant qu'*administrateur, *je veux* le plan « qui tire où » pour la qualif, *afin de* l'afficher et l'exporter.
- **CA** : vue par cible listant archers + positions + départ ; source des exports (E09US003).
- **Dépend de** : E03US002 · **Jalon** : J1

### E03US009 — Placer les duellistes côte à côte
*En tant qu'*administrateur, *je veux* que les adversaires d'un duel soient sur des positions voisines, *afin de* faciliter les matchs.
- **CA** : lors d'une phase de tableau, les 2 duellistes sont placés côte à côte dans la mesure du possible.
- **Dépend de** : E03US002, E05US007 · **Jalon** : J2

### E03US010 — Générer / éditer le déroulé horaire
*En tant qu'*administrateur, *je veux* un déroulé horaire de la journée, *afin de* cadencer l'événement.
- **CA** : grille horaire par phase/tour ; éditable manuellement (génération auto en option — question ouverte).
- **Dépend de** : E05US002 · **Jalon** : J4
