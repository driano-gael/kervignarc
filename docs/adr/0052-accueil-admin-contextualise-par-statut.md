# ADR-0052 — Accueil d'admin contextualisé par statut

- **Statut** : Accepté
- **Date** : 2026-07-28
- **Décideurs** : Organisateur / Architecte
- **Introduit par** : E14US001 (accueil-tableau de bord contextualisé par tournoi).
- **Amende** : [`stories/E14-lisibilite-admin.md`](../../stories/E14-lisibilite-admin.md) (E14US001) ;
  [`cahier-des-charges-ux.md`](../../cahier-des-charges-ux.md) §7.1 (`D-20`).
- **S'appuie sur** : [ADR-0026](0026-cycle-de-vie-du-tournoi-sept-statuts.md) (7 statuts),
  [ADR-0032](0032-navigation-admin-par-etat-local.md) (navigation par état local),
  la complétude (E12US005), la supervision (E12US001), les paiements (E08US002).

## Contexte et problème

Retours de la démo du 27/07/2026 : « l'interface doit me raconter une histoire claire », « on ne
sait pas ce qui se passe ». La coquille admin (E00US015) aligne ~21 écrans sans fil conducteur ;
`D-20` (CDC UX §7.1) prévoit un **accueil contextualisé par statut**, jamais livré. Trois manques :

1. **Aucun écran d'ensemble** : `destinationParDefaut(statut)` ne faisait que *choisir la destination
   d'ouverture* (brouillon→Tournoi, en_cours→Supervision, terminé→Classement) — pas de vue « où j'en
   suis, quoi faire ensuite ».
2. **Front bloqué à 3 statuts** : le type `StatutTournoi` du front ne connaissait que
   `brouillon | en_cours | termine` alors qu'ADR-0026 (E01US017, **livré**) en expose **7**. Dès
   qu'un tournoi atteignait `prêt`/`en_pause`/`archivé`/`annulé`, le **badge était muet** et le
   **pilotage bloqué** (aucun bouton) — un bug latent, pas seulement une lacune d'accueil.
3. **Pas de vue des transitions possibles** : la topologie de la machine à états (qui peut passer de
   quoi à quoi) vivait **implicitement** dans les gardes `depuis` de `ServiceTournois`, sans lecture.

Livrer un accueil « à boutons » (frise + actions) exige de résoudre les trois d'un coup. C'est
structurant (nouvelle surface, nouvelle lecture, alignement d'un type partagé), d'où cet ADR.

## Décision

**1. L'accueil est un écran dédié qui *agrège*, il ne *recalcule* rien.** `Accueil` (feature
`accueil`) compose des sources **déjà livrées** — complétude (E12US005), supervision (E12US001),
paiements (E08US002) — plus la frise du cycle de vie. Aucune règle métier nouvelle : la checklist
« à faire » est la complétude, les chiffres-clés sont des lectures existantes, les alertes sont
**dérivées** (lignes de complétude en `alerte` + postes hors ligne). C'est le cadrage d'E14US001.

**2. Le front s'aligne sur les 7 statuts d'ADR-0026.** Le type `StatutTournoi` passe à 7 valeurs ;
`BadgeStatut` devient exhaustif (un statut sans libellé casse la compilation — le badge ne peut plus
être muet) ; les classes CSS `badge--pret/-archive/-annule` complètent l'existant.

**3. La topologie du cycle de vie est exposée en *lecture*, source unique côté domaine.** Plutôt que
dupliquer la machine à états en front (règle 1 d'isolation), le domaine gagne
`transitions_possibles(statut)` (table déclarative des arêtes d'ADR-0026 §2) et l'API
`GET /api/v1/tournois/{id}/transitions`. La frise en fait ses boutons. Les **gardes** restent au
service (ADR-0026 §4) : une transition **offerte** peut échouer à l'exécution (ex. `vers-pret` sans
départ → 409). Un **test de cohérence** (`test_service_tournois`) recoupe la table du domaine et les
gardes du service pour qu'elles ne divergent pas.

**4. La frise remplace l'ancien `CycleDeVie`.** `FriseCycleDeVie` (feature `accueil`) devient la
**source unique** du pilotage du cycle de vie, montée à la fois sur l'Accueil et sur la destination
« Tournoi ». Elle couvre les 7 statuts ; l'ancien contrôle local (3 statuts, bloquant dès `prêt`) est
supprimé. Le passage à `terminé` **conserve** son avertissement chiffré (complétude, E12US005) ;
`annuler`/`archiver` sont confirmés.

**5. Choisir un tournoi ouvre *toujours* sur son accueil.** `destinationParDefaut()` renvoie
désormais l'accueil quel que soit le statut : la **contextualisation se joue dans l'écran** (frise,
checklist, chiffres), plus dans l'aiguillage de la destination d'ouverture. Les autres destinations
restent à un clic (`P-3`, priorité d'affichage, pas restriction — cf. ADR-0032).

## Conséquences

- **+** `D-20` est livré : un organisateur non formé voit **où il en est** et **quoi faire ensuite**
  sans ouvrir tous les écrans. Le bug latent des 3 statuts (badge muet, pilotage bloqué dès `prêt`)
  est corrigé au passage.
- **+** La machine à états a une **lecture** réutilisable (topologie), sans second encodage : la
  frise ne décide rien, le test de cohérence garantit l'alignement service ↔ domaine.
- **−** Le front porte désormais une frise 7 statuts à maintenir en phase avec ADR-0026 (mais
  l'exhaustivité TS et le test de cohérence backend le protègent).
- **−** L'accueil **poll** (complétude, supervision) : c'est un écran live, comme la supervision.
- **Périmètre.** L'**aide contextuelle par écran** (`E14US002`) et le regroupement liste/fiche
  (`E00US016`) restent hors de cette US. Pas de refonte `react-router` (ADR-0032 tient), pas
  d'identité visuelle par tournoi (E01US016).
