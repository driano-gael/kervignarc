# E05 — Moteur de phases & tableaux — User Stories

> EPIC : [EPIC-05](../epics/EPIC-05-moteur-phases.md) · Réfs : `moteur-placement-lucky-loser.md`, CDC technique §4.2, ADR-0004.

> ⚠️ **Maille révisée le 17/07/2026** — regroupement des US au grain « capacité » (19 → 8). Les
> anciennes US découpées par étape technique (modèle / édition / cohérence, interfaces / assemblage,
> arrondi / byes / arbre / progression / podium, peuplement / routing / division / rangs
> terminaux…) sont devenues des **critères d'acceptation** de l'US de capacité qui les porte.
> **Aucun comportement n'est perdu** (règle 9 — chaque ancien titre = une puce CA identifiée), et les
> arbitrages/notes déjà tranchés (ADR-0004, ADR-0011, DETTE-003, Règles R/T de
> `moteur-placement-lucky-loser.md`) sont repris avec l'US qui les porte désormais. **Aucune US
> n'était livrée** au moment du regroupement. Correspondance ancien → nouveau en fin de fichier.

---

### E05US001 — Séquence de phases (modèle, édition, cohérence)
*En tant qu'*administrateur, *je veux* composer et éditer la séquence de phases d'un tournoi avec des
garde-fous de cohérence, *afin de* définir le format sans risque de blocage plus tard.
- **CA — modèle (ex-001)** : entités `Phase` (ordre, type, config JSON) rattachées au tournoi ;
  sorties d'une phase réutilisables ; **statuts** `a_venir / en_cours / en_pause / terminee` —
  `en_pause` **gèle la phase** (aucune validation de score acceptée) jusqu'à reprise, **distinct** du
  `en_pause` du **tournoi** ([ADR-0026](../docs/adr/0026-cycle-de-vie-du-tournoi-sept-statuts.md) §3 :
  deux niveaux de gel, même intention).
- **CA — édition (ex-002)** : ajouter/ordonner/supprimer/typer des phases ; validation d'ordre
  cohérent.
- **CA — cohérence (ex-017)** : détection source vide / rangs inexistants / effectif incompatible ;
  message explicite.
- **Absorbe** : ex-E05US001, E05US002, E05US017. **Dépend de** : E01US001 · **Jalon** : J2

#### Catalogue des formats de phase (cibles du moteur) — 18/07/2026
> **Un format est de la configuration, pas du code** (règle 2, [ADR-0004](../docs/adr/0004-moteur-de-phases-politiques.md)) :
> le moteur (E05US003) doit composer **n'importe quel** format via ses politiques injectables
> (`routing/scoring/seeding/byes/tiebreak/depth`). Ce catalogue liste les formats **cibles** de l'appli ;
> chacun devient une US implémentable **quand sa règle est écrite** — **même *gate* que le Big Shoot Off**,
> aujourd'hui bloqué faute de règle ([référentiel §11](../docs/referentiel-ffta.md), Q9). Un format sans
> règle écrite n'a **pas d'oracle** (règle 9) : il reste *cible documentée*, **non planifié**. Catalogue
> **ouvert** — d'autres formats s'ajoutent en fournissant leur règle.

| Format | Règle | US / note |
|---|---|---|
| Qualification (cumul) | ✅ écrite | livré (barème) |
| Élimination directe (tableau) | ✅ écrite | E05US005 |
| Duel **par sets** (1ᵉ à 6, FFTA) | ✅ écrite | politique `scoring` (E05US003) |
| Barrage / shoot-off (1 flèche) | ✅ écrite | référentiel §8.2 |
| Placement intégral 1→N | ✅ écrite | E05US010 |
| Repêchage-réintégration (WA) | ✅ écrite | E05US016 |
| Big Shoot Off | 🔴 à fournir | bloqué (Q9) |
| **Poules / round-robin** | ⏳ à fournir | cible |
| **Handicap** (score ajusté au niveau) | ⏳ à fournir | cible |
| **Système suisse** (appariement par score) | ⏳ à fournir | cible |
| **King of the hill** (le vainqueur reste) | ⏳ à fournir | cible (original) |
| **Montante-descendante (ladder)** | ⏳ à fournir | cible (original) |
| **Finale spectacle** (tir alterné, public) | ⏳ à fournir | cible |
| **Contre-la-montre / découverte** (temps limité) | ⏳ à fournir | cible (original) |

> Les formats **par équipes** relèvent d'un périmètre distinct (le moteur oppose des *participants*,
> pas des archers) — **[EPIC-13](../epics/EPIC-13-equipes.md)**, [ADR-0028](../docs/adr/0028-epreuves-par-equipes-participant.md).

### E05US003 — Politiques injectables & assemblage
*En tant que* développeur, *je veux* des interfaces de politiques `routing/scoring/seeding/byes/
tiebreak/depth` assemblables par la config JSON d'une phase, *afin d'*assembler des formats sans code
dédié.
- **CA — interfaces (ex-003)** : chaque politique (`routing/scoring/seeding/byes/tiebreak/depth`) est
  une interface du domaine avec au moins une implémentation ; unitairement testable.
- **CA — assemblage (ex-004)** : la config JSON d'une phase référence les politiques ; assemblage
  résolu par la composition root. **Tranche [DETTE-003](../docs/dette.md)** : politiques **à la
  racine** (forme écrite par E01US009/E01US015) *vs* sous **`config.policies`** (modèle cible
  ADR-0004), et **objet paramétré** *vs* **nom de preset** pour `scoring` ; met `modele-de-donnees.md`
  **et** l'ADR-0004 en accord avec la décision ; si `policies` l'emporte, fournit la migration des
  `config` existantes + un test de relecture de l'ancienne forme.
- **Notes** : le socle des interfaces (ex-003) est le cœur de l'**ADR-0004**. **⚠️ Arbitrage à
  trancher avant d'écrire le moteur** (ex-004) — deux conventions coexistent aujourd'hui pour le même
  champ (politiques à la racine *vs* `config.policies`, cf. DETTE-003). Décision structurante ⇒ ADR
  (amende ou remplace l'**ADR-0011**).
- **Absorbe** : ex-E05US003, E05US004. **Dépend de** : E05US001 · **Jalon** : J2

### E05US005 — Arbre d'élimination directe
*En tant que* système, *je veux* dimensionner, ensemencer, construire et faire vivre l'arbre
d'élimination directe jusqu'au podium, *afin de* dérouler un tableau équitable de bout en bout.
- **CA — dimensionnement & seeding (ex-005)** : effectif arrondi à la puissance de 2 supérieure ;
  seeding serpent (r vs 2^k+1−r) vérifié sur cas connus.
- **CA — byes (ex-006)** : byes attribués **aux mieux classés** ; calcul universel pour tout effectif.
- **CA — génération de l'arbre (ex-007)** : matchs numérotés, tours ordonnés ; chaque match relié à
  ses sources (seeds/byes).
- **CA — progression (ex-008)** : à réception du vainqueur (E04US013), le match suivant est peuplé ;
  routing = élimination sèche pour le perdant.
- **CA — podium (ex-009)** : finale → rangs 1-2 ; petite finale → rangs 3-4 ; alimente E06US004.
- **Absorbe** : ex-E05US005 à E05US009. **Dépend de** : E05US003 · **Jalon** : J2

### E05US010 — Placement intégral 1→N
*En tant que* système, *je veux* peupler des phases de placement depuis n'importe quelle source
(rangs, gagnants/perdants), router les perdants en cascade et fixer les rangs terminaux, *afin de*
classer **tout le monde** de 1 à N, personne éliminé.
- **CA — peuplement par rangs (ex-010)** : une phase peut être alimentée par « rangs N→M » d'un
  classement source.
- **CA — peuplement gagnants/perdants (ex-011)** : sources « gagnants du tour X » / « perdants du
  tour X » disponibles pour peupler une phase.
- **CA — routing cascade (ex-012)** : `route(perdant, tour) → sous-tableau de placement` ; personne
  n'est éliminé.
- **CA — division récursive (ex-013)** : plage `[a..b]` → moitié haute (vainqueurs) / moitié basse
  (perdants) jusqu'à largeur 2.
- **CA — rangs terminaux (ex-014)** : match terminal → gagnant = rang supérieur, perdant = rang
  suivant (Règle T vérifiée).
- **Notes** : le routing cascade (ex-012) applique la **Règle R** de `moteur-placement-lucky-loser.md`
  ; les rangs terminaux (ex-014) appliquent la **Règle T** du même document.
- **Absorbe** : ex-E05US010 à E05US014. **Dépend de** : E05US003 · **Jalon** : J3

### E05US015 — Big Shoot Off
*En tant que* système, *je veux* gérer la grande finale en BSO, *afin de* respecter le format.
- **CA** : barème BSO appliqué à la grande finale ; vainqueur = rang 1.
- **Dépend de** : E01US011, E05US005 · **Jalon** : J3

### E05US016 — Routing repêchage-réintégration (WA)
*En tant qu'*administrateur, *je veux* un mode repêchage réintégrant le principal, *afin de* couvrir
le format World Archery.
- **CA** : `routing = repêchage` réinjecte certains perdants dans le tableau principal ;
  sélectionnable par phase.
- **Dépend de** : E05US010 · **Jalon** : J4

### E05US018 — Oracle 120 (rejeu + comparaison)
*En tant que* équipe, *je veux* rejouer le tournoi 120 du classeur, *afin de* valider le moteur.
- **CA** : test de non-régression reconstruisant arbre + routage + classement 1→120 et comparant à
  `Tableaux.xlsx`.
- **Notes** : oracle de référence (risque R1).
- **Dépend de** : E05US010 · **Jalon** : J3

### E05US019 — Enregistrer une séquence comme modèle
*En tant qu'*administrateur, *je veux* sauvegarder un format, *afin de* le réutiliser.
- **CA** : une séquence + politiques enregistrable comme modèle nommé ; applicable à un nouveau
  tournoi.
- **Dépend de** : E05US003 · **Jalon** : J3

---

## Correspondance ancien → nouveau (maille ÷~2,4 du 17/07/2026)

| Ancienne US | Titre d'origine | Devient |
|---|---|---|
| E05US001 | Définir le modèle de séquence de phases | **E05US001** — CA « modèle » |
| E05US002 | Éditer une séquence | **E05US001** — CA « édition » |
| E05US003 | Interfaces de politiques injectables | **E05US003** — CA « interfaces » |
| E05US004 | Assembler les politiques d'une phase | **E05US003** — CA « assemblage » |
| E05US005 | Arrondi 2^k + seeding serpent | **E05US005** — CA « dimensionnement & seeding » |
| E05US006 | Attribution des byes | **E05US005** — CA « byes » |
| E05US007 | Générer l'arbre d'élimination directe | **E05US005** — CA « génération de l'arbre » |
| E05US008 | Progression : le gagnant avance | **E05US005** — CA « progression » |
| E05US009 | Terminer sur un podium | **E05US005** — CA « podium » |
| E05US010 | Peuplement : rangs N→M | **E05US010** — CA « peuplement par rangs » |
| E05US011 | Peuplement : gagnants / perdants d'un tour | **E05US010** — CA « peuplement gagnants/perdants » |
| E05US012 | Routing cascade (placement intégral) | **E05US010** — CA « routing cascade » |
| E05US013 | Division récursive des plages | **E05US010** — CA « division récursive » |
| E05US014 | Affectation des rangs terminaux | **E05US010** — CA « rangs terminaux » |
| E05US015 | Big Shoot Off | **E05US015** (inchangée) |
| E05US016 | Routing repêchage-réintégration (WA) | **E05US016** (inchangée) |
| E05US017 | Contrôles de cohérence | **E05US001** — CA « cohérence » |
| E05US018 | Oracle 120 (rejeu + comparaison) | **E05US018** (inchangée) |
| E05US019 | Enregistrer une séquence comme modèle | **E05US019** (inchangée) |
