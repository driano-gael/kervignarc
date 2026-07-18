# ADR-0026 — Cycle de vie du tournoi : sept statuts explicites

- **Statut** : Accepté
- **Date** : 2026-07-18
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E01-configuration.md`](../../stories/E01-configuration.md) (E01US002 — note de renvoi ;
  **E01US017** nouvelle) ; [`stories/E12-pilotage-jour-j.md`](../../stories/E12-pilotage-jour-j.md)
  (E12US005 — la complétude devient la **garde** du passage `brouillon → prêt`) ;
  [`docs/modele-de-donnees.md`](../modele-de-donnees.md) (enum `TOURNOI.statut`) ;
  [`cahier-des-charges-ux.md`](../../cahier-des-charges-ux.md) (`D-20`, accueil contextualisé par statut).
- **Introduit par** : E01US017 (cycle de vie enrichi du tournoi).
- **S'appuie sur** : le cycle **à trois statuts** déjà livré (`brouillon → en_cours → terminé`,
  E01US002 — domaine `Tournoi`, `ServiceTournois`, endpoints `demarrer`/`terminer`/`supprimer`).
  Cet ADR l'**enrichit** sans renier ses transitions existantes.

## Contexte et problème

Le tournoi livré (E01US002) porte **trois** statuts avec des transitions irréversibles
(`brouillon → en_cours → terminé`) et **une seule** garde métier : un tournoi `en_cours` n'est pas
supprimable. Trois manques sont apparus à l'usage (remontées du 18/07/2026) :

1. **Rien ne dit qu'un brouillon est *prêt*.** `demarrer()` ne vérifie **que** `statut == brouillon` —
   un brouillon vide (sans catégories, sans départ, sans barème) démarre sans broncher. L'organisateur
   veut savoir « est-ce que je peux lancer ? » **avant** de lancer.
2. **Rien ne permet de *geler* un tournoi en cours** sans le terminer (incident, coupure, pause
   déjeuner) — un état transitoire où la saisie s'arrête et reprend.
3. **`terminé` est un fourre-tout de fin.** Il mélange « sportivement fini mais on encaisse encore un
   chèque en retard » (`D-18`) et « clos, exporté, verrouillé pour de bon » (archive, EPIC-11) — et il
   n'existe aucun état pour un tournoi **abandonné** (météo, effectif insuffisant) qu'on veut **garder
   en trace** plutôt que supprimer.

Ajouter des statuts est structurant : chaque statut conditionne des **permissions** (ce qui est
éditable, supprimable) et des **transitions**, et pilote l'accueil de l'admin (`D-20`). D'où cet ADR.
**Règle que l'on s'impose : un statut n'existe que s'il *change un comportement*** — sinon c'est du
bruit. Les sept ci-dessous la respectent chacun.

## Décision

**1. Sept statuts, chacun porteur d'un comportement distinct.**

| Statut | Ce qu'il change concrètement |
|---|---|
| `brouillon` | Config **libre**, tout éditable ; suppression libre. État initial. |
| `prêt` | Déclare la config **complète et validée** ; suppression encore libre ; sert de « feu vert » au démarrage. |
| `en_cours` | Compétition lancée ; **suppression interdite** ; le structurel (catégories, gabarit, barème) se fige, les métadonnées restent éditables. |
| `en_pause` | **Gèle la saisie** de tout le tournoi (aucune validation de score acceptée) sans le terminer ; reprend en `en_cours`. |
| `terminé` | Résultats **sportifs figés** (seule action irréversible côté sportif) ; la complétude **hors-sportif** reste consultable et modifiable — encaisser un paiement en retard (`D-18`). |
| `archivé` | **Verrou total**, lecture seule définitive, après export (EPIC-11). |
| `annulé` | Tournoi **abandonné** ; **conserve la trace** (≠ suppression) ; terminal. |

**2. Transitions autorisées (le reste est refusé en `409`, `TransitionStatutInvalide`).**

```
brouillon  ⇄  prêt  ─(démarrer)→  en_cours  ─(terminer)→  terminé  ─(archiver)→  archivé
    │           │                   ⇅ (mettre en pause / reprendre)
    │           │                 en_pause
    └───────────┴─────────────────────┴──(annuler)──→  annulé   (terminal)
```

- `brouillon → prêt` est **gardé par la complétude** : la vue de complétude d'E12US005, appliquée
  « à froid » (catégories, blasons associés, gabarit, barème, **≥ 1 départ à horaire valide**…), doit
  être satisfaite. **C'est le « prêt à démarrer ».**
- `prêt → brouillon` : toute édition qui **invalide** la complétude y ramène automatiquement (le feu
  vert ne ment pas). `prêt` reste donc un état *vrai*, pas un simple voyant, mais **calculé au maintien**.
- `en_cours ⇄ en_pause` : réversible, sans perte.
- `annuler` accessible depuis `brouillon`, `prêt`, `en_cours`, `en_pause` — **pas** depuis `terminé`
  (un tournoi joué jusqu'au bout n'est pas « annulé »).
- **Pas** de `terminé → en_cours` : la réouverture reste **différée** (hors de cet ADR), cohérente avec
  « `terminé` = seule action irréversible » (E12US005).

**3. `en_pause` du tournoi et `en_pause` de la phase sont deux niveaux distincts.** Le statut de
tournoi `en_pause` (ici) gèle **tout l'événement** ; le statut de phase `en_pause`
([ADR-0004](0004-moteur-de-phases-politiques.md), moteur E05) gèle **une** phase pendant que le reste
vit. Ils ne se confondent pas et peuvent coexister ; la saisie est refusée si **l'un ou l'autre** gèle
le contexte concerné. Cette symétrie de vocabulaire est **voulue** (même mot, même intention : « figer
jusqu'à relance »), à deux mailles.

**4. La garde vit dans le service, l'agrégat ne connaît que la valeur.** Comme le cycle à trois
statuts existant : l'agrégat `Tournoi` porte l'enum et des transitions **pures** (`vers_pret()`,
`mettre_en_pause()`, `reprendre()`, `archiver()`, `annuler()`) qui valident **la valeur** ; c'est
`ServiceTournois` qui arbitre l'**enchaînement** et interroge la complétude (règle 2 : la règle vit
dans le service/domaine, pas dans l'API). Aucune horloge injectée : toutes les transitions sont
**déclenchées** par un acte admin, donc déterministes (règle 9).

## Conséquences

- **+** L'accueil contextualisé (`D-20`) gagne ses deux extrémités manquantes : `prêt` (préparation
  bouclée, feu vert) et `archivé` (lecture seule). Le front n'a plus à **deviner** l'état.
- **+** La complétude (E12US005) n'est plus seulement un tableau de bord du jour J : elle devient une
  **garde de transition** réutilisée « à froid ». Une seule logique de complétude, deux usages.
- **+** `annulé` sauve la **trace** d'un tournoi abandonné, là où seule la suppression existait —
  cohérent avec l'esprit « signaler plutôt qu'effacer » ([ADR-0015](0015-signaler-un-doublon-plutot-que-l-interdire.md),
  [ADR-0016](0016-supprimer-un-archer-engage-plutot-que-le-refuser.md)).
- **−** Quatre statuts de plus = **plus de transitions à tester** et un tableau de permissions plus
  large (ce qui est éditable/supprimable par statut). Assumé : chacun porte un comportement réel.
- **−** `prêt` « calculé au maintien » impose de **recontrôler la complétude** à chaque édition d'un
  tournoi `prêt` (pour, au besoin, le rétrograder). Coût maîtrisé : la complétude est déjà calculée.
- **−** L'ancienne transition directe `brouillon → en_cours` (E01US002) **disparaît** au profit de
  `brouillon → prêt → en_cours`. E01US002 est **livré** ; le changement se fait dans **E01US017**
  (implémentation), pas dans l'US livrée — dont le CA reçoit seulement une **note de renvoi**.
- **Périmètre** : E01US017 livre l'enum, les transitions et leurs gardes. L'**archive** effective
  (contenu exporté, verrou physique) reste EPIC-11 ; la **réouverture** d'un `terminé` reste différée.
