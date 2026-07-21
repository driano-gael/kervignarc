# ADR-0040 — Alerter par **calcul d'impact** : prévisualisation, échelle à trois niveaux, geste délibéré

- **Statut** : Accepté
- **Date** : 2026-07-21
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E12-pilotage-jour-j.md`](../../stories/E12-pilotage-jour-j.md) (E12US007 :
  section « Arbitrages » ajoutée — périmètre, fork, échelle). N'amende pas le glossaire. **Ne résout
  pas** [DETTE-007](../dette.md#dette-007--la-confirmation-dune-suppression-darcher-est-aveugle) (autre
  action) mais en **pose la plomberie** (§ Conséquences).
- **Introduit par** : E12US007 (alerter par calcul d'impact).
- **S'appuie sur** : [ADR-0035](0035-atomicite-acte-trace-session-partagee.md) (co-écriture atomique
  acte↔trace), l'audit E10US005 (`EntreeAudit`, `ServiceAudit`), le placement matérialisé E03US004
  ([ADR-0024](0024-plan-de-cibles-materialise-et-ajustable.md)), et le protocole de **signalement
  confirmable** d'[ADR-0016](0016-supprimer-un-archer-engage-plutot-que-le-refuser.md) /
  [ADR-0018](0018-supprimer-un-depart-a-inscriptions-confirmable.md).

## Contexte et problème

E12US007 est une **règle transverse** (`P-4`, `D-15`, `D-16`, [CDC UX §9.1](../../cahier-des-charges-ux.md)) :
une action d'écriture ne doit demander confirmation **que quand ça compte**, et alors **chiffrer son
impact** (« 156 archers perdront leur place ; 4 cibles ont déjà des scores, conservés »). Une action
**massive** exige un **geste délibéré** (taper un mot, ex. `REPLACER`), impossible par réflexe, et
laisse une **trace d'audit**. La ligne de partage n'est ni *brouillon / en cours*, ni *sportif /
tiers*, mais : **est-ce que ça a déjà produit des données réelles ?**

Deux problèmes appellent un arbitrage, pas un choix purement technique :

1. **Périmètre.** « Toutes les écritures » est un CA **clair mais non borné**. Aucune infrastructure
   n'existe (ni calcul d'impact, ni composant de confirmation générique, ni geste « taper un mot »).
   Tout couvrir d'un coup serait un chantier mal délimité — plusieurs écritures n'ont pas d'impact
   *réel défini* aujourd'hui (que « perd » un changement de blason par défaut ?), et la règle du
   projet est de **poser le mécanisme sur un cas réel du code d'aujourd'hui**, pas de l'étaler par
   anticipation.

2. **Où vivent les chiffres.** Deux façons de livrer l'impact au front : (A) un endpoint de
   **prévisualisation** qui calcule sans écrire, ou (B) un **409-avec-impact** où l'action réelle
   refuse en portant les chiffres. (B) réutilise le pattern existant (`autoriser_*`) mais fait naître
   l'alerte d'un **échec**, pas d'un **calcul** — et recalcule au commit, jamais « en continu ».

## Décision

**1. Périmètre (arbitrage produit) : le mécanisme réutilisable + la seule action `régénérer le plan de
cibles`.** C'est l'action qui correspond **mot pour mot** à l'exemple du CDC (le cas « REPLACER »).
Les autres écritures destructrices existantes (changer le gabarit, modifier un barème/phase, une
catégorie/blason) **gardent leur comportement actuel** ; elles se grefferont sur le mécanisme quand
leur propre US les touchera. Aucun comportement perdu (règle 9) : le CA « toutes les écritures » reste
l'horizon, il est **séquencé**, pas rogné — comme l'écran de salle d'E12US001.

**2. Fork tranché (arbitrage technique) : (A) endpoint de prévisualisation, avec re-calcul de l'impact
au commit.** C'est le seul choix fidèle au CA (« calcule l'impact **au moment où on agit**, ne classe
pas d'avance ») **et** sûr au rejeu. Le front lit l'impact par un `GET …/plan-de-cibles/impact-regeneration`
(lecture pure, hors file), affiche l'alerte, puis appelle `POST …/regenerer` avec `confirme=true`.
L'action réelle **recalcule** l'impact dans la file (writer unique) : elle ne croit pas le front sur
parole. C'est précisément ce qui **évite** le défaut de [DETTE-007](../dette.md) (décompte cru sur
parole, non revérifié) — le re-placement ne rejoint donc **pas** la famille des confirmations aveugles.

**3. Échelle d'impact à trois niveaux (`NiveauImpact`), calculée dans le domaine.**

| Niveau | Condition (régénérer un départ) | Alerte | Geste | Trace |
|---|---|---|---|---|
| `AUCUN` | aucune affectation (plan jamais généré) | aucune | direct | non |
| `CONFIRMATION` | des archers placés, **aucun score** | chiffrée (« N archers replacés ») | bouton | non |
| `MASSIF` | des archers placés **+ au moins un score** | chiffrée (« N archers ; M cibles ont des scores, conservés ») | **taper `REPLACER`** | **oui** |

La dérivation du niveau est une **règle métier** (ce qui mérite un geste délibéré) → domaine pur
(`domain/impact.py`, value object `ImpactRegeneration` immuable, propriété `niveau`). `archers_deplaces`
= nombre d'affectations actuelles (tout le monde est re-brassé par le glouton déterministe) ;
`cibles_avec_scores` = cibles distinctes du plan dont **au moins un archer a une série**.

**4. Répartition de la garde.** Le **serveur** n'observe qu'un seul seuil : il **bloque** (409
`replacement_non_confirme`) et **trace** ssi `niveau == MASSIF`. Les niveaux `AUCUN` et `CONFIRMATION`
sont traités identiquement côté serveur (« fais-le ») — la confirmation `CONFIRMATION` est une friction
**purement front** (via la prévisualisation), parce que re-brasser un placement **sans scores** est une
config réversible et déterministe (ADR-0024), pas un acte sensible à auditer. Le **mot à taper**
(`REPLACER`) est une friction **humaine côté front** ; le serveur, lui, n'exige qu'un booléen
`confirme` explicite — exactement le contrat `autoriser_*` d'ADR-0015/0016/0018. Coupler le serveur à
la copie d'UI (« le mot doit être REPLACER ») serait une inversion de dépendance.

**5. Trace atomique acte↔trace (ADR-0035).** La régénération massive co-écrit le plan **et** son
`EntreeAudit` (nouvelle action `ActionAuditee.REPLACEMENT`) dans **une seule transaction**, via une
nouvelle méthode d'adapter `PlacementRepositorySQL.definir_plan_avec_trace` (miroir de
`SerieRepositorySQL.enregistrer_avec_trace`). L'`auteur` est `« Administrateur »` (l'action est admin ;
l'admin est un **secret**, pas une personne nommée — E10US002/`D-13`). Jamais de replacement massif non
tracé, jamais de trace fantôme.

## Conséquences

- **Le canal `details` de `{code, message, details?}` est peuplé pour la première fois** : le 409
  `replacement_non_confirme` y porte les chiffres (`archers_deplaces`, `cibles_avec_scores`). Le
  gestionnaire `_sur_erreur_application` lit désormais un `details` optionnel sur l'exception. C'est la
  **plomberie même** que [DETTE-007](../dette.md) et [DETTE-008](../dette.md) annonçaient comme « jamais
  peuplée à ce jour, c'est elle qui fait le coût » — E12US007 la pose, réduisant le coût futur du
  correctif de DETTE-007 (sans le résoudre : DETTE-007 porte sur la suppression d'archer/départ, hors
  de ce périmètre).
- **Un composant de confirmation générique naît dans `shared/`** (chiffrage + mot à taper optionnel) —
  la première brique transverse pour les futures appliquations de la règle. Jusqu'ici chaque feature
  bricolait un `useState` local (règle 10, factorisation à venir).
- **Le mécanisme est réutilisable mais non sur-généralisé** : `NiveauImpact` (l'échelle) est générique ;
  `ImpactRegeneration` (le calcul) est spécifique au placement. La 2ᵉ action à câbler (gabarit, barème…)
  dupliquera d'abord — « attendre le 3ᵉ cas » avant d'abstraire un port `CalculateurImpact` (règle
  « remède structurel sur preuve », § Dette).
- **`ServicePlacement` gagne deux ports** : `SerieRepository` (savoir « a des scores ») et `Horloge`
  (dater la trace). Reflété au composition root.
- **Limite connue (héritée d'ADR-0024)** : un plan **vidé à la main** (tous en réserve) est
  indiscernable d'un plan jamais généré → `niveau == AUCUN`, régénération sans alerte. Effet borné et
  réversible (auto déterministe) ; on l'assume plutôt que de persister un drapeau « généré ».

## Alternatives écartées

- **(B) 409-avec-impact seul** : l'alerte naîtrait d'un refus, pas d'un calcul — infidèle au CA, et
  n'affiche pas l'impact « en continu » avant le geste.
- **Couvrir toutes les écritures d'emblée** : chantier non borné, impacts mal définis → gaspillage
  d'implémentation (le garde-fou « CA clair mais trop étroit/large » du pilotage de l'assistant).
- **Valider le mot `REPLACER` côté serveur** : couplerait le domaine/API à la copie d'UI. Le geste
  humain vit au front ; le serveur exige un consentement explicite (booléen), pas une chaîne magique.
- **Trace non atomique (`ServiceAudit.consigner` après `definir_plan`)** : deux transactions → fenêtre
  où le replacement est écrit mais pas tracé. ADR-0035 existe pour l'éviter.
