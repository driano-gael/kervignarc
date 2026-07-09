# EPIC-02 — Inscriptions & clubs

- **ID** : EPIC-02
- **Statut** : À planifier
- **Priorité** : MVP (saisie manuelle) → MVP+1 (import)
- **Dépend de** : EPIC-00, EPIC-01
- **Réfs** : CDC fonctionnel M2

## Objectif / valeur
Constituer la liste des participants d'un tournoi, base de tout le reste (placement, facturation, tableaux).

## Périmètre
### Inclus
- Référentiel **clubs** réutilisable.
- Saisie **manuelle** d'un archer (nom, prénom, club, catégorie).
- **Départs multiples** par archer (base de la facturation : tarif × nb départs).
- **Quotas** (nb max de participants par inscription / départ).
- Modifier / supprimer / **dédoublonner**.
- **Import** de fichiers d'inscrits (« inscript'arc » XLS ou URL) — *incrément*.

### Exclus
- Le calcul/suivi du paiement (EPIC-08) ; le placement (EPIC-03).

## Capacités
- [ ] CRUD archers + clubs.
- [ ] Gestion des départs multiples.
- [ ] Contrôle des quotas.
- [ ] Import XLS avec mapping de colonnes et rapport d'erreurs.

## Incréments
- **MVP** : saisie manuelle + clubs + départs + quotas.
- **MVP+1** : import XLS « inscript'arc ».

## Critères d'acceptation (epic)
- Une liste d'inscrits cohérente et dédoublonnée est disponible pour le placement.

## Questions ouvertes
- **Format exact du fichier inscript'arc** (QT1) : bloque l'incrément import — obtenir un exemple + colonnes.
