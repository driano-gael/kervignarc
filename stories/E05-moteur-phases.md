# E05 — Moteur de phases & tableaux — User Stories

> EPIC : [EPIC-05](../epics/EPIC-05-moteur-phases.md) · Réfs : `moteur-placement-lucky-loser.md`, CDC technique §4.2, ADR-0004.

---

### E05US001 — Définir le modèle de séquence de phases
*En tant que* système, *je veux* représenter un tournoi comme une séquence ordonnée de phases, *afin de* structurer le déroulement.
- **CA** : entités `Phase` (ordre, type, config JSON) rattachées au tournoi ; sorties d'une phase réutilisables.
- **Dépend de** : E01US001 · **Jalon** : J2

### E05US002 — Éditer une séquence
*En tant qu'*administrateur, *je veux* composer la séquence, *afin de* définir le format.
- **CA** : ajouter/ordonner/supprimer/typer des phases ; validation d'ordre cohérent.
- **Dépend de** : E05US001 · **Jalon** : J2

### E05US003 — Interfaces de politiques injectables
*En tant que* développeur, *je veux* des interfaces `routing/scoring/seeding/byes/tiebreak/depth`, *afin d'*assembler des formats sans code dédié.
- **CA** : chaque politique est une interface du domaine avec au moins une implémentation ; unitairement testable.
- **Notes** : cœur de l'ADR-0004.
- **Dépend de** : E05US001 · **Jalon** : J2

### E05US004 — Assembler les politiques d'une phase
*En tant qu'*administrateur, *je veux* choisir les politiques d'une phase, *afin de* paramétrer son comportement.
- **CA** : la config JSON d'une phase référence les politiques ; assemblage résolu par la composition root. **Tranche [DETTE-003](../docs/dette.md)** : politiques **à la racine** (forme écrite par E01US009/E01US015) *vs* sous **`config.policies`** (modèle cible ADR-0004), et **objet paramétré** *vs* **nom de preset** pour `scoring` ; met `modele-de-donnees.md` **et** l'ADR-0004 en accord avec la décision ; si `policies` l'emporte, fournit la migration des `config` existantes + un test de relecture de l'ancienne forme.
- **Notes** : ⚠️ à trancher **avant** d'écrire le moteur — deux conventions coexistent aujourd'hui pour le même champ. Décision structurante ⇒ **ADR** (amende ou remplace l'ADR-0011).
- **Dépend de** : E05US003 · **Jalon** : J2

### E05US005 — Arrondi 2^k + seeding serpent
*En tant que* système, *je veux* dimensionner et ensemencer le tableau, *afin de* poser un arbre équitable.
- **CA** : effectif arrondi à la puissance de 2 supérieure ; seeding serpent (r vs 2^k+1−r) vérifié sur cas connus.
- **Dépend de** : E05US004 · **Jalon** : J2

### E05US006 — Attribution des byes
*En tant que* système, *je veux* attribuer les exempts, *afin de* gérer les effectifs non-2^k.
- **CA** : byes attribués **aux mieux classés** ; calcul universel pour tout effectif.
- **Dépend de** : E05US005 · **Jalon** : J2

### E05US007 — Générer l'arbre d'élimination directe
*En tant que* système, *je veux* construire l'arbre des matchs, *afin de* dérouler les duels.
- **CA** : matchs numérotés, tours ordonnés ; chaque match relié à ses sources (seeds/byes).
- **Dépend de** : E05US006 · **Jalon** : J2

### E05US008 — Progression : le gagnant avance
*En tant que* système, *je veux* faire avancer le vainqueur, *afin de* progresser dans l'arbre.
- **CA** : à réception du vainqueur (E04US014), le match suivant est peuplé ; routing = élimination sèche pour le perdant.
- **Dépend de** : E05US007 · **Jalon** : J2

### E05US009 — Terminer sur un podium
*En tant qu'*administrateur, *je veux* clore le tableau sur un podium, *afin de* désigner les vainqueurs.
- **CA** : finale → rangs 1-2 ; petite finale → rangs 3-4 ; alimente E06US004.
- **Dépend de** : E05US008 · **Jalon** : J2

### E05US010 — Peuplement : rangs N→M
*En tant que* système, *je veux* peupler une phase depuis une plage de rangs, *afin de* composer des tableaux de placement.
- **CA** : une phase peut être alimentée par « rangs N→M » d'un classement source.
- **Dépend de** : E05US004 · **Jalon** : J3

### E05US011 — Peuplement : gagnants / perdants d'un tour
*En tant que* système, *je veux* router gagnants et perdants, *afin d'*alimenter phases et repêchages.
- **CA** : sources « gagnants du tour X » / « perdants du tour X » disponibles pour peupler une phase.
- **Dépend de** : E05US010 · **Jalon** : J3

### E05US012 — Routing cascade (placement intégral)
*En tant que* système, *je veux* faire descendre le perdant dans la plage inférieure, *afin de* classer tout le monde.
- **CA** : `route(perdant, tour) → sous-tableau de placement` ; personne n'est éliminé.
- **Notes** : Règle R de `moteur-placement-lucky-loser.md`.
- **Dépend de** : E05US011 · **Jalon** : J3

### E05US013 — Division récursive des plages
*En tant que* système, *je veux* scinder la plage de rangs à chaque tour, *afin de* converger vers des paires.
- **CA** : plage `[a..b]` → moitié haute (vainqueurs) / moitié basse (perdants) jusqu'à largeur 2.
- **Dépend de** : E05US012 · **Jalon** : J3

### E05US014 — Affectation des rangs terminaux
*En tant que* système, *je veux* fixer les rangs exacts, *afin de* produire le classement 1→N.
- **CA** : match terminal → gagnant = rang supérieur, perdant = rang suivant (Règle T vérifiée).
- **Dépend de** : E05US013 · **Jalon** : J3

### E05US015 — Big Shoot Off
*En tant que* système, *je veux* gérer la grande finale en BSO, *afin de* respecter le format.
- **CA** : barème BSO appliqué à la grande finale ; vainqueur = rang 1.
- **Dépend de** : E01US011, E05US009 · **Jalon** : J3

### E05US016 — Routing repêchage-réintégration (WA)
*En tant qu'*administrateur, *je veux* un mode repêchage réintégrant le principal, *afin de* couvrir le format World Archery.
- **CA** : `routing = repêchage` réinjecte certains perdants dans le tableau principal ; sélectionnable par phase.
- **Dépend de** : E05US012 · **Jalon** : J4

### E05US017 — Contrôles de cohérence
*En tant qu'*administrateur, *je veux* être alerté d'une phase mal alimentée, *afin d'*éviter les blocages.
- **CA** : détection source vide / rangs inexistants / effectif incompatible ; message explicite.
- **Dépend de** : E05US004 · **Jalon** : J2

### E05US018 — Oracle 120 (rejeu + comparaison)
*En tant que* équipe, *je veux* rejouer le tournoi 120 du classeur, *afin de* valider le moteur.
- **CA** : test de non-régression reconstruisant arbre + routage + classement 1→120 et comparant à `Tableaux.xlsx`.
- **Notes** : oracle de référence (risque R1).
- **Dépend de** : E05US014 · **Jalon** : J3

### E05US019 — Enregistrer une séquence comme modèle
*En tant qu'*administrateur, *je veux* sauvegarder un format, *afin de* le réutiliser.
- **CA** : une séquence + politiques enregistrable comme modèle nommé ; applicable à un nouveau tournoi.
- **Dépend de** : E05US004 · **Jalon** : J3
