# E02 — Inscriptions & clubs — User Stories

> EPIC : [EPIC-02](../epics/EPIC-02-inscriptions.md) · Réfs : CDC fonctionnel M2.

---

### E02US001 — Gérer le référentiel clubs
*En tant qu'*administrateur, *je veux* gérer une liste de clubs, *afin de* rattacher les archers sans ressaisie.
- **CA** : CRUD club (nom) ; réutilisable entre tournois ; un club utilisé n'est pas supprimable sans avertissement.
- **Notes** : entité **globale** — pas de `tournoi_id`, routes `/api/v1/clubs` non imbriquées. Unicité du nom au sens de `domain.club.cle_nom` (casse **et** accents repliés), qui sert aussi au tri : sans quoi les sommes par club (E08US004/E09US004) se couperaient en deux. Pose aussi `Archer.club_id` (**facultatif**, migration `0014`) : c'est lui qui rend le CA « club utilisé non supprimable » **exerçable** — sans rattachement possible, le refus (`ClubReference` → 409, patron `BlasonReference` d'E01US006) serait un garde-fou qu'aucun chemin réel ne déclenche. La FK naît **avec** sa politique de suppression, contrairement à celles de DETTE-001 — et elle en sort du périmètre : elle pointe hors de la descendance de `tournoi`.
- **Dépend de** : E00US009 · **Jalon** : J1

### E02US002 — Créer un archer
*En tant qu'*administrateur, *je veux* saisir un archer, *afin de* l'inscrire au tournoi.
- **CA** : nom, prénom, club, catégorie obligatoires ; archer rattaché au tournoi ; persisté via la file.
- **Notes** : entité `Archer` (FR, ADR-0006) — renommage du prototype `Player`. **Acquis d'E02US001** : `Archer.club_id` + FK + `ArcherRepository.par_club` + refus de suppression d'un club référencé existent déjà. Cette US **rend le club obligatoire** (`NOT NULL` + migration des archers sans club) et ajoute `prenom`, `categorie_id` et l'index UNIQUE de dédoublonnage.
- **Dépend de** : E01US003, E02US001 · **Jalon** : J1

### E02US003 — Éditer / supprimer un archer
*En tant qu'*administrateur, *je veux* corriger ou retirer un archer, *afin de* tenir la liste à jour.
- **CA** : édition des champs ; suppression bloquée si l'archer est déjà placé/engagé (ou confirmation + recalcul).
- **Dépend de** : E02US002 · **Jalon** : J1

### E02US004 — Ajouter des départs multiples
*En tant qu'*administrateur, *je veux* inscrire un archer sur plusieurs départs, *afin de* refléter sa participation réelle.
- **CA** : un archer peut avoir N départs ; chaque départ porte un n° ; base du calcul de facturation.
- **Notes** : entité `Depart` liée à l'archer.
- **Dépend de** : E02US002 · **Jalon** : J1

### E02US005 — Détecter et fusionner les doublons
*En tant qu'*administrateur, *je veux* repérer les doublons, *afin de* fiabiliser la liste.
- **CA** : détection par nom/prénom/club ; proposition de fusion conservant départs et scores.
- **Dépend de** : E02US002 · **Jalon** : J1

### E02US006 — Contrôler les quotas
*En tant qu'*administrateur, *je veux* plafonner le nombre d'inscrits, *afin de* respecter la capacité.
- **CA** : quota configurable (par tournoi / par départ) ; blocage ou alerte au dépassement.
- **Dépend de** : E02US004 · **Jalon** : J1

### E02US007 — Importer un fichier inscript'arc (parsing + mapping)
*En tant qu'*administrateur, *je veux* importer les inscrits depuis un fichier, *afin d'*éviter la ressaisie.
- **CA** : import XLS ; mapping des colonnes ; création des archers/clubs/départs.
- **Notes** : **bloqué** tant que le format exact (QT1) n'est pas fourni ; adapter d'infrastructure (openpyxl).
- **Dépend de** : E02US002, E02US004 · **Jalon** : J4

### E02US008 — Rapport d'import
*En tant qu'*administrateur, *je veux* un compte-rendu d'import, *afin de* corriger les anomalies.
- **CA** : lignes importées / rejetées (avec motif) / doublons détectés ; aucun import partiel silencieux.
- **Dépend de** : E02US007 · **Jalon** : J4
