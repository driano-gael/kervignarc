# EPIC-14 — Accueil & lisibilité de l'admin — User Stories

> Issu des **retours de la démo au client final du 27/07/2026**. Objectif : l'admin « raconte une
> histoire claire » et se pilote **sans formation**. Voir [`epics/EPIC-14`](../epics/EPIC-14-lisibilite-admin.md).
>
> **Réutilise sans dupliquer** : le cycle de vie à 7 statuts est **E01US017** (prérequis de la frise) ;
> le regroupement liste/fiche des écrans est **E00US016**.
>
> ⚠️ **Stubs** : le CA fin de chaque US visible se **précise au cadrage d'intention en tête d'US**
> (maquette comprise) — l'esprit agile du projet, pas une spec figée d'avance.

### E14US001 — Accueil-tableau de bord contextualisé par tournoi (`D-20`)
*En tant qu'*organisateur, *je veux* un écran d'accueil par tournoi qui me dise **où j'en suis** et **ce qu'il reste à faire**, *afin de* piloter sans formation et « lire une histoire claire » au lieu de parcourir ~21 écrans.
- **Contexte** : retours de la démo du 27/07/2026 (« raconter une histoire claire », « on ne sait pas ce qui se passe »). La coquille admin (E00US015) ouvre déjà un point d'entrée contextualisé, mais sur **3 statuts** seulement (les 7 d'ADR-0026 sont **E01US017**) et sans vue d'ensemble. `D-20` (CDC UX §7.1) prévoit un accueil par statut, non encore livré.
- **CA — les trois combinés** : l'accueil par tournoi montre (1) une **frise du cycle de vie** (les 7 statuts d'E01US017, statut courant surligné, transitions possibles indiquées) ; (2) une **checklist « fait / à faire »** qui **réutilise** la complétude (E12US005) et la supervision (E12US001) ; (3) des **chiffres-clés & alertes** (inscrits, payés, postes en ligne, avancement ; alertes via la règle d'impact E12US007) ; le tout menant vers la **prochaine action**.
- **CA — pas de logique métier nouvelle** : l'accueil **agrège** des sources existantes (complétude, supervision, impact) ; il ne **recalcule** aucune règle métier.
- **Notes** : `D-20` (CDC UX §7.1) ; consomme les extrémités neuves d'E01US017 (`prêt`, `archivé`). Front principalement (agrégation de lecture côté API si besoin, **sans** nouveau calcul métier). ⚠️ Front sans tests de rendu → vérifier **à l'écran**. **Redécoupable par brique** (frise / checklist / chiffres) si trop large pour une branche (règle INVEST). **ADR à créer** : « Accueil d'admin contextualisé par statut ». US à **surface visible** → doc fonctionnelle + journal d'avancement.
- **Dépend de** : E01US017, E00US015, E12US001, E12US005, E12US007 · **Jalon** : J3 · **Origine** : démo 27/07/2026

### E14US002 — Aide contextuelle « ce qui est saisissable et pourquoi »
*En tant qu'*organisateur non formé, *je veux* que chaque écran de saisie explique **ce qu'on y saisit et pourquoi**, *afin de* ne pas avoir besoin de formation pour utiliser le logiciel.
- **Contexte** : retour de la démo du 27/07/2026 (« sur la gestion et les écrans dédiés, une explication de ce qui est saisissable et pourquoi ; je ne veux pas de formation »). Complémentaire d'**E00US016** (pattern liste/fiche + déroulantes/cases à cocher) : E00US016 rend la saisie **propre**, cette US la rend **explicable**.
- **CA — aide par écran** : chaque écran d'administration porte une **aide brève** (encart ou infobulle) disant **ce qui est saisissable** et **pourquoi** (à quoi ça sert en aval) ; **patron réutilisable** (un composant d'aide unique), rédigé en **langage organisateur**, non technique.
- **Notes** : présentation uniquement — **aucun** changement de domaine/API. Le **contenu** d'aide se rédige avec l'organisateur (langage métier). ⚠️ Front sans tests de rendu → vérifier **à l'écran**. US à **surface visible** → doc fonctionnelle + journal d'avancement.
- **Dépend de** : E00US015 · **Jalon** : J3 · **Origine** : démo 27/07/2026
