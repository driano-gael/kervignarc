# E01 — Configuration du tournoi — User Stories

> EPIC : [EPIC-01](../epics/EPIC-01-configuration-tournoi.md) · Réfs : CDC fonctionnel M1, ADR-0006 (vocabulaire).

---

### E01US001 — Créer un tournoi
*En tant qu'*administrateur, *je veux* créer un tournoi (nom, date, lieu, type officiel/non), *afin de* disposer d'un contexte pour inscrire et placer.
- **CA** : tournoi persisté et listable ; champs obligatoires validés ; type officiel/non stocké.
- **Notes** : agrégat `Tournoi` (domaine) ; écriture via la file ; DTO distinct.
- **Dépend de** : E00US009 · **Jalon** : J1

### E01US002 — Éditer / lister les tournois
*En tant qu'*administrateur, *je veux* retrouver et modifier mes tournois, *afin de* les gérer dans le temps.
- **CA** : liste des tournois ; édition des métadonnées ; un tournoi en cours n'est pas supprimable sans confirmation.
- **Dépend de** : E01US001 · **Jalon** : J1

### E01US003 — Gérer les catégories (CRUD)
*En tant qu'*administrateur, *je veux* définir les catégories du tournoi, *afin de* classer et cloisonner les archers.
- **CA** : créer/éditer/supprimer une catégorie (libellé, arme, âge, sexe) ; rattachable à un tournoi.
- **Notes** : entité `Categorie` (FR, ADR-0006).
- **Dépend de** : E01US001 · **Jalon** : J1

### E01US004 — Pré-charger les catégories FFTA salle
*En tant qu'*administrateur, *je veux* partir de catégories FFTA prédéfinies modifiables, *afin de* ne pas tout ressaisir.
- **CA** : un jeu de catégories FFTA salle est proposé à la création ; chaque catégorie reste modifiable/supprimable.
- **Notes** : jeu de référence à obtenir (question ouverte EPIC-01).
- **Dépend de** : E01US003 · **Jalon** : J1

### E01US005 — Gérer les blasons (taille/fraction + capacité)
*En tant qu'*administrateur, *je veux* définir les blasons, *afin de* modéliser l'occupation d'une cible.
- **CA** : blason = `taille` (fraction de place) + `capacite` + `nom` ; CRUD.
- **Notes** : réutilise/étend le prototype `Blason`.
- **Dépend de** : E01US001 · **Jalon** : J1

### E01US006 — Associer catégorie ↔ blason
*En tant qu'*administrateur, *je veux* lier une catégorie à un blason, *afin que* le placement en tienne compte (officiel).
- **CA** : chaque catégorie peut porter un blason par défaut ; utilisé par le placement (EPIC-03).
- **Dépend de** : E01US003, E01US005 · **Jalon** : J1

### E01US007 — Définir un gabarit de salle
*En tant qu'*administrateur, *je veux* décrire le plan de salle, *afin de* cadrer le placement.
- **CA** : gabarit = nb de cibles + capacité (1/2/4) + positions (A/B/C/D) ; persisté.
- **Notes** : entité `GabaritSalle` ; base du plan de cibles.
- **Dépend de** : E01US001 · **Jalon** : J1

### E01US008 — Réutiliser / ajuster un gabarit
*En tant qu'*administrateur, *je veux* réutiliser un gabarit existant et l'ajuster, *afin de* gagner du temps d'un tournoi à l'autre.
- **CA** : appliquer un gabarit enregistré à un tournoi ; ajuster (nb cibles, capacités) sans altérer l'original.
- **Dépend de** : E01US007 · **Jalon** : J1

### E01US009 — Définir un barème de qualification
*En tant qu'*administrateur, *je veux* paramétrer le barème de qualif, *afin de* calculer les scores.
- **CA** : preset (ex. 5 volées de 3 flèches, cumul) sélectionnable ; valeurs modifiables.
- **Notes** : politique `scoring` (ADR-0004) ; MVP = qualif seule.
- **Dépend de** : E01US001 · **Jalon** : J1

### E01US010 — Définir le tarif par départ
*En tant qu'*administrateur, *je veux* fixer le tarif d'un départ, *afin d'*alimenter le suivi de paiement.
- **CA** : tarif paramétrable par tournoi ; utilisé par le calcul du montant dû (E08US001).
- **Dépend de** : E01US001 · **Jalon** : J1

### E01US011 — Presets de barèmes multi-phases
*En tant qu'*administrateur, *je veux* des presets pour chaque type de phase, *afin de* couvrir les formats riches.
- **CA** : presets barrage (1 flèche), sets (4 pts), finales (6 pts), Big Shoot Off ; modifiables et réutilisables.
- **Notes** : alimente les politiques `scoring` du moteur (EPIC-05).
- **Dépend de** : E01US009 · **Jalon** : J4

### E01US012 — Gérer plusieurs gabarits
*En tant qu'*administrateur, *je veux* une bibliothèque de gabarits, *afin de* gérer plusieurs salles.
- **CA** : créer/nommer/lister plusieurs gabarits ; en choisir un par tournoi.
- **Dépend de** : E01US007 · **Jalon** : J4
