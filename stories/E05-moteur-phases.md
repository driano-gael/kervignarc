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

### E05US001 — Séquence de phases (modèle, édition, cohérence) — ✅ livrée 26/07/2026
*En tant qu'*administrateur, *je veux* composer et éditer la séquence de phases d'un tournoi avec des
garde-fous de cohérence, *afin de* définir le format sans risque de blocage plus tard.
- **CA — modèle (ex-001)** : entités `Phase` (ordre, type, config JSON) rattachées au tournoi ;
  sorties d'une phase réutilisables ; **statuts** `a_venir / en_cours / en_pause / terminee` —
  `en_pause` **gèle la phase** (aucune validation de score acceptée) jusqu'à reprise, **distinct** du
  `en_pause` du **tournoi** ([ADR-0026](../docs/adr/0026-cycle-de-vie-du-tournoi-sept-statuts.md) §3 :
  deux niveaux de gel, même intention). Transitions **pures** sur l'agrégat, garde d'enchaînement
  dans le service (`TransitionStatutInvalide` → 409), au patron `ServiceTournois`
  ([ADR-0045](../docs/adr/0045-sequence-de-phases-cycle-de-vie-typage-source.md) §1). *Le branchement
  effectif du gel sur le chemin de saisie relève d'E04US013 (duels) : la qualification n'a qu'une
  phase, jamais gelée isolément — noté à l'ADR-0045 §1.*
- **CA — édition (ex-002)** : ajouter/ordonner/supprimer/**typer** des phases ; validation d'ordre
  cohérent (ordres contigus 1..N). **Types déclarables** : `qualification`, `elimination_directe`,
  `placement` — ceux dont la règle est écrite ; déclarer un type **ne présuppose pas** son moteur
  (les barèmes/politiques propres viennent en E05US003), les autres types s'ajoutent avec l'US qui
  les implémente (ADR-0045 §2). `bareme`/`validation` deviennent **facultatifs** sur `Phase` (requis
  pour `qualification` seulement).
- **CA — cohérence (ex-017)** : détection **source vide / rangs inexistants / effectif incompatible**
  ; message explicite. **Portée E05US001** : un **modèle de source minimal** est amorcé
  (`SourcePhase(ordre_source, rang_debut, rang_fin)` + `effectif` facultatif par phase), suffisant
  pour rendre les trois contrôles décidables — cohérence pure dans l'agrégat `SequencePhases`
  (→ `DomainError`/422). C'est une **amorce assumée provisoire** (une source « par rangs », pas de
  routing/gagnants-perdants) qu'E05US010 remplacera par le peuplement complet (DETTE-015, ADR-0045 §3).
- **Livraison — full-stack** : domaine + service + repository + API **et écran admin** d'édition de
  la séquence (rattaché à la coquille E00US015). *Arbitrages tranchés le 26/07/2026 avec le
  commanditaire : (a) livrer jusqu'à l'écran (pas backend seul) ; (b) amorcer un modèle de source
  minimal plutôt que reporter tout contrôle de source à E05US010. Reversés ici au titre de la
  règle 9.*
- **Absorbe** : ex-E05US001, E05US002, E05US017. **Dépend de** : E01US001 · **Jalon** : J2

#### Catalogue des formats de phase (cibles du moteur) — 18/07/2026
> **Un format est de la configuration, pas du code** (règle 2, [ADR-0004](../docs/adr/0004-moteur-de-phases-politiques.md)) :
> le moteur (E05US003) doit composer **n'importe quel** format via ses politiques injectables
> (`routing/scoring/seeding/byes/tiebreak/depth`). Ce catalogue liste les formats **cibles** de l'appli ;
> chacun devient une US implémentable **quand sa règle est écrite** — c'est le *gate* qui a bloqué le
> **Big Shoot Off** jusqu'au **31/07/2026**, date à laquelle le club en a fourni la règle (Q9 fermée,
> [référentiel §10.1](../docs/referentiel-ffta.md)). Un format sans
> règle écrite n'a **pas d'oracle** (règle 9) : il reste *cible documentée*, **non planifié**. Catalogue
> **ouvert** — d'autres formats s'ajoutent en fournissant leur règle.

| Format | Règle | US / note |
|---|---|---|
| Qualification (cumul) | ✅ écrite | livré (barème) |
| Élimination directe (tableau) | ✅ écrite | E05US005 |
| Duel **par sets** (1ᵉ à 6, FFTA) | ✅ écrite | politique `scoring` (E05US003) |
| Barrage / shoot-off (1 flèche) | ✅ écrite | référentiel §8.2 — **phase autonome** : E05US015 |
| Placement intégral 1→N | ✅ écrite | **E05US010** — 🎯 prochaine |
| Repêchage-réintégration (WA) | ✅ écrite | E05US015 *(absorbe ex-E05US016)* |
| Big Shoot Off | ✅ **écrite le 31/07/2026** | référentiel §10.1 — E05US015 *(Q9 fermée)* |
| **Poules / round-robin** | ✅ **écrite le 31/07/2026** | référentiel §10.1 — E05US015 |
| **Handicap** (score ajusté au niveau) | ⏳ à fournir | cible |
| **Système suisse** (appariement par score) | ⏳ à fournir | cible |
| **King of the hill** (le vainqueur reste) | ⏳ à fournir | cible (original) |
| **Montante-descendante (ladder)** | ⏳ à fournir | cible (original) |
| **Échauffement** (sans point, sans classement) | ✅ **écrite le 31/07/2026** | référentiel §10.1 — E05US015 |
| **Finale spectacle** (tir alterné, public) | ⏳ à fournir | cible |
| **Contre-la-montre / découverte** (temps limité) | ⏳ à fournir | cible (original) |

> Les formats **par équipes** relèvent d'un périmètre distinct (le moteur oppose des *participants*,
> pas des archers) — **[EPIC-13](../epics/EPIC-13-equipes.md)**, [ADR-0028](../docs/adr/0028-epreuves-par-equipes-participant.md).

### E05US003 — Politiques injectables & assemblage — ✅ livrée 26/07/2026
*En tant que* développeur, *je veux* des interfaces de politiques `routing/scoring/seeding/byes/
tiebreak/depth` assemblables par la config JSON d'une phase, *afin d'*assembler des formats sans code
dédié.
- **CA — interfaces (ex-003)** : chaque politique (`routing/scoring/seeding/byes/tiebreak/depth`) est
  une interface du domaine (`Protocol`) avec au moins une implémentation ; unitairement testable.
  Livré : `EliminationSeche`, `ScoreCumul`, `SeedingSerpent`, `ByesAuxMieuxClasses`,
  `TiebreakFftaDefaut`, `ProfondeurUnVersN` dans `backend/domain/politiques.py`.
- **CA — assemblage (ex-004)** : la config JSON d'une phase référence les politiques ; assemblage
  résolu par la composition root (`RegistrePolitiques` + `assembler_politiques`, registre peuplé dans
  `bootstrap/composition.py`). **A tranché [DETTE-003](../docs/dette.md)** via
  [ADR-0046](../docs/adr/0046-config-policies-politiques-nommees-parametrees.md) : politiques sous
  **`config.policies`**, chacune **`{"nom": …, …paramètres}`** (nom + paramètres, ni objet anonyme ni
  preset fermé) ; grain de `validation` **hors** `policies` ; `modele-de-donnees.md` et ADR-0004
  réconciliés ; migration de données `0028` + test de relecture de l'ancienne forme à plat.
- **Notes** : le socle des interfaces (ex-003) est le cœur de l'**ADR-0004**. Arbitrage tranché avec
  le commanditaire avant d'écrire le moteur (ADR-0046, amende l'**ADR-0011**).
  **Périmètre vs E05US005/E05US010** : cette US livre les **politiques** (stratégies pures) — dont le
  seeding serpent et les byes « aux mieux classés », fonctions pures unitairement testées. Le
  **tableau** qui les orchestre (dimensionnement 2^k, génération, progression, podium) reste
  **E05US005** ; le routing en cascade et le peuplement gagnants/perdants restent **E05US010**. Les
  stratégies couplées à la structure d'arbre (routing, scoring par sets) exposent ici leur **méthode
  fondatrice** ; les US consommatrices la **ressigneront** (ADR-0004 vise `route(perdant, tour,
  contexte)`) — **rupture de contrat assumée**, bon marché tant qu'il n'y a qu'un implémenteur et
  aucun consommateur (ADR-0046, § Conséquences).
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

### E05US010 — Placement intégral 1→N & peuplement multiple *(élargie le 31/07/2026)*
*En tant que* système, *je veux* peupler une phase depuis **plusieurs** sources hétérogènes, router
les perdants en cascade et fixer les rangs terminaux, *afin de* classer **tout le monde** de 1 à N —
personne éliminé — et de composer des formats qui **s'ajustent** à l'effectif réel.

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
- **CA — sources multiples (31/07/2026)** : une phase se peuple de **plusieurs** sources, de natures
  différentes. Demande du commanditaire, mot pour mot : « *les x archers doivent pouvoir venir de
  différentes sources de tableaux précédents, exemple les demi-finalistes du tableau principal, et
  le gagnant du tableau secondaire ; ce n'est qu'un exemple mais le paramétrage doit être ouvert pour
  ça* ». Conforme à **EF-3.3** du CDC, qui énumérait déjà : *tous les inscrits, rangs N→M, gagnants
  d'un tour, perdants d'un tour (Lucky Loser), exempts*.
- **CA — plages relatives (31/07/2026)** : un format composé pour un effectif doit tenir à un autre.
  Demande du commanditaire : « *il faut également que la phase et le format du tournoi soient
  capables de s'ajuster si j'ai prévu 120 archers et qu'il n'y en a que 82* ». Une plage accepte donc
  une **fin ouverte**, et le vocabulaire comporte « **le reste** » — tout ce qu'aucune autre source
  n'a prélevé. Une phase qui dirait « les rangs 33 à 120 » serait **fausse** à 82 inscrits.
- **CA — cohérence des sources** : deux sources d'une même phase ne se **recoupent** pas (un archer
  prélevé deux fois), et leur somme est compatible avec l'effectif déclaré. Un format devenu
  infaisable à effectif réduit (« les 32 premiers » avec 20 inscrits) n'est **pas** une erreur à
  corriger dans le format : c'est une **anomalie à afficher** (cf. E01US024).
- **CA — oracle 120 (ex-E05US018)** : test de non-régression reconstruisant arbre + routage +
  classement 1→120, comparé à `Tableaux.xlsx`. **Non négociable dans cette US** — un moteur de
  placement sans oracle n'est pas vérifiable (risque R1).

**Notes — état des lieux au 31/07/2026, à lire avant de commencer.**

> **Le verrou est le routing, pas le catalogue de types.** `DestinationPerdant`
> (`backend/domain/politiques.py:68`) n'a **qu'une** valeur : `ELIMINE`. Tout ce qui n'est pas
> élimination sèche — placement, repêchage, consolation, non-qualifiés de poule — a besoin que le
> perdant aille **ailleurs**. `Routing.destination_du_perdant()` doit devenir
> `route(perdant, tour, contexte)`, exactement comme [ADR-0004](../docs/adr/0004-moteur-de-phases-politiques.md)
> le prévoit et comme `politiques.py` l'annonce lui-même (« ressigneront cette méthode — rupture bon
> marché, un implémenteur, aucun consommateur »). **C'est la première chose à poser : tout en dépend.**

> **Ce qui existe déjà et se réutilise tel quel** — le risque n°1 d'une reprise à froid est de
> recoder ce qui est là : `backend/domain/tableau.py` (dimensionnement 2^k, génération de l'arbre,
> progression, podium — E05US005 ✅), `SeedingSerpent`, `ByesAuxMieuxClasses`, `EliminationSeche`
> (`domain/politiques.py`), l'abstraction `Participant` (ADR-0028). Le dimensionnement **absorbe déjà**
> les effectifs non-puissance-de-2 : un tableau de 32 avec 28 archers fonctionne, byes aux mieux
> classés.

> ⚠️ **Migration de données, sur DEUX tables.** `SourcePhase` est sérialisée dans `phase.config`
> **et**, depuis E01US023 (30/07/2026), dans `format_tournoi.config`. Les deux doivent être migrées,
> et l'**ancienne forme** (source unique) doit rester relisable — c'est un sous-cas de la nouvelle.
> C'est l'élargissement de DETTE-015 relevé par la revue d'E01US023.

> **Règles R et T** : `moteur-placement-lucky-loser.md`. **Règle R** — quand un archer perd au niveau
> dont la plage atteignable est `[a..b]` (largeur `w`), il entre dans le sous-tableau de cette plage,
> où l'élimination interne **divise `w` par deux** à chaque tour jusqu'à `w = 2`. **Règle T** — le
> match terminal d'une paire `(2k−1, 2k)` donne gagnant = rang supérieur, perdant = rang suivant.
> ⚠️ Piège de vocabulaire : dans `Tableaux.xlsx`, « LUCKY LOSER 1 » désigne le **tableau de
> consolation**, **pas** un repêchage — aucun archer battu n'y revient disputer le titre.

**Arbitrages tranchés à l'implémentation (31/07/2026)** — reversés ici pour que le CA reste vrai.

> **L'oracle 120 ne couvre pas les rangs 1 à 4, et c'est une propriété du classeur, pas une facilité.**
> À l'extraction de `Tableaux.xlsx`, le sommet du tableau principal s'est révélé n'être **pas** une
> élimination directe : la **Grande Finale s'y tire en Big Shoot Off** à **cinq** archers — les 4
> vainqueurs du 8ᵉ tour (M305-M308) et un « **Lucky-Looser** » —, et produit les rangs **1 à 5** par
> élimination du plus faible à chaque manche (onglet « TABLEAU 1 OK », colonnes « GRANDE FINALE » ;
> l'échelle 5→4→3→2 des colonnes suivantes le montre). ⚠️ Les étiquettes `BSO 6`…`BSO 10` sont des
> **postes de tir**, pas un compte d'archers ni des rangs : elles occupent la même colonne que les
> « 1 A » / « 2 C » du reste de la feuille. *(Un premier jet d'E05US010 les avait lues comme dix
> archers produisant les rangs 1 à 10 — **c'est faux**, rectifié en revue. E05US015 dimensionne donc
> son BSO sur **5** entrants, pas 10.)*
>
> **Le format du club REPÊCHE — et c'est la découverte à retenir pour E05US015.** Le
> « Lucky-Looser » est le **gagnant de M427**, le meilleur des battus, qui remonte disputer le titre
> au lieu de prendre le rang 5. D'où un fait vérifiable dans les données : M427 ne décerne qu'**un**
> rang (le 6, à son perdant), le classeur compte **115** rangs terminaux (6→120) et non 116, et
> 5 + 115 = 120. Cela **nuance** l'avertissement « Lucky Loser » ci-dessus : le classeur emploie le
> mot pour **deux** choses distinctes — « LUCKY LOSER 1 » (tableau de consolation, aucun retour au
> titre) et ce « Lucky-Looser » de la Grande Finale, qui est un **vrai repêchage**.
>
> Il n'y a donc **aucune finale d'élimination à comparer** dans le classeur. L'oracle porte sur les
> rangs **6 à 120** (57 paires terminales pleines, M428-M484) et le déclare. *Effet de bord heureux :
> cette Grande Finale, alimentée par les vainqueurs des quarts **et** par un repêché, est le **cas
> réel** du CA « sources multiples ».*
>
> **Écart de structure non expliqué, à instruire en E05US015** : le classeur compte **484** matchs,
> le moteur en produit **436**. −3 s'expliquent (le BSO remplace demies + finale), +12 aussi
> (sous-tableau des rangs 121-128, élagué car sans rang réel) ; **39 restent inexpliqués** — une
> cascade pure de 128 places en compte 448. Hypothèse : des tableaux de **consolation**
> supplémentaires, hors de la division par deux formalisée. C'est une divergence entre le classeur
> et `moteur-placement-lucky-loser.md`, **antérieure** à cette US, figée par un test qui documente
> les deux nombres.

> **L'élimination directe livrée par E05US005 est un placement tronqué au rang 4.** Un tableau à
> **petite finale** fait rejouer les perdants des demies : il ne les élimine pas. La cascade et
> l'élimination directe sont donc **le même algorithme** à profondeur près — c'est ce qui a permis
> une non-régression structurelle (même arbre, même numérotation) plutôt que plaquée. La composition
> root injecte désormais `PlacementEnCascade` + profondeur `podium`. Cf. [ADR-0061](../docs/adr/0061-routing-generique-et-placement-en-cascade.md) §2.

> **Le contrôle « la somme des sources égale l'effectif déclaré » ne s'applique plus que si tous les
> prélèvements sont dénombrables au format.** Dès qu'un seul est relatif (fin ouverte, « le reste »,
> issue de tour), le compte ne se connaît qu'à l'exécution. Ce n'est pas un relâchement : c'est la
> condition d'existence des plages relatives, et le CA « cohérence des sources » le dit déjà pour
> l'autre bout du problème (un format infaisable à effectif réduit est une **anomalie à afficher**,
> E01US024, pas une erreur de format).

> **Ce que cette US ne livre pas, par décision de périmètre.** Le **modèle** de sources multiples est
> livré (domaine, persistance, API, migration) mais **aucun moteur ne le consomme encore** : peupler
> effectivement une phase depuis ses sources est le travail d'**E01US024**. De même, l'écran
> « Phases » **affiche** tous les prélèvements mais n'en **édite** qu'un, « par rangs » ; une phase à
> composition avancée y est en **lecture seule** (un formulaire mono-source l'écraserait sans le
> dire). Le modèle est livré ici parce que c'est **lui** qui bloquait le routing, et parce que le
> reporter aurait imposé une **seconde** migration double table.

- **Absorbe** : ex-E05US010 à E05US014, **et E05US018** (oracle). **Résorbe** : DETTE-015.
- **Dépend de** : E05US003 · **Jalon** : J3 · **Origine** : cadrage du 31/07/2026
- **Livrée** : 31/07/2026 — [ADR-0061](../docs/adr/0061-routing-generique-et-placement-en-cascade.md),
  migration `0036`, oracle `backend/tests/test_oracle_120_placement.py`

### E05US015 — Le catalogue de types de phase *(élargie le 31/07/2026)*
*En tant qu'*organisateur, *je veux* disposer des types de phase qui composent un vrai tournoi de
club — échauffement, barrage, poules, repêchage, Big Shoot Off — *afin de* décrire mon déroulé réel
au lieu de l'approcher.

**Chaque type est un assemblage de politiques** ([ADR-0004](../docs/adr/0004-moteur-de-phases-politiques.md)),
pas du code en dur : `routing`, `scoring`, `seeding`, `byes`, `tiebreak`, `depth`. Les six familles
existent depuis E05US003 (✅) ; cette US en peuple le catalogue.

- **CA — échauffement** : une phase **sans point et sans classement**. Demande du commanditaire
  (31/07/2026), mot pour mot : « *ajoute une phase échauffement, sans point sans classement* ».
  Aucun barème, aucun grain de validation, aucune politique de score, personne d'éliminé, **aucun
  classement produit**. Elle **existe dans le déroulé** — et c'est tout son objet : elle occupe du
  temps et des cibles, donc elle apparaît au plan de salle, au planning et à l'écran de projection.
  ⚠️ **Elle porte la règle de cohérence la plus intéressante du lot** : une phase **sans classement**
  ne peut pas être **prélevée par rangs** — « les rangs 1 à 32 de l'échauffement » n'a aucun sens.
  C'est la seule phase dont la sortie n'est pas ordonnée, donc celle qui éprouve le mieux le modèle
  d'anomalies d'E01US024. La seule façon licite de lui succéder est « les mêmes archers, sans ordre ».
- **CA — barrage / shoot-off comme phase autonome** : départager des ex æquo **avant** de monter un
  tableau. Règle **entièrement écrite** au [référentiel §8.2](../docs/referentiel-ffta.md)
  (art. B.6.5.2) : *individuel* — **1 flèche**, plus haut score ; si l'égalité subsiste on **répète au
  plus près du centre** ; *équipe* — une volée de **3 flèches** (1 par archer). Deux règles qui
  surprennent et qu'il ne faut pas rater : le barrage **ne prend pas en compte** le nombre de 10/9
  (seul endroit du produit où ce critère ne s'applique pas), et **un archer absent au barrage annoncé
  est déclaré perdant**. Tiré sur la cible centrale du triple vertical. Le pavé de saisie des duels (E04US013 ✅) convient.
  ⚠️ **Reporté, pas oublié** : le CA prévoyait un nouveau **type de source** « les archers à égalité
  au rang r » d'un classement. Il n'est **pas livré** — `NatureSource` porte toujours `rangs` /
  `issue_de_tour` / `reste`. Motif : un prélèvement d'ex æquo ne se dénombre qu'à l'exécution, donc
  il n'a de sens qu'une fois les moteurs branchés à un déroulé — c'est **E01US024**, avec le reste
  de la consommation des sources ([DETTE-028](../docs/dette.md)). Le barrage se compose d'ici là par
  un prélèvement par rangs ordinaire. *(Reversé après la revue du 31/07, qui a relevé qu'un CA
  abandonné en cours d'US et non consigné fait dériver l'US suivante sur une base fausse.)*
- **CA — poules** : règle fournie par le commanditaire le 31/07/2026, reproduite ici **verbatim** —
  elle n'est écrite **nulle part ailleurs** (ni au règlement FFTA salle, ni dans aucun document du
  projet), donc cette US en est la source :
  > **Principe** — Les archers sont regroupés en poules et se rencontrent dans leur groupe.
  > **Fonctionnement** — Chaque archer rencontre tout ou partie des autres archers de sa poule. Un
  > barème de points attribue les victoires, nuls et défaites. Le classement de poule détermine les
  > qualifiés pour la phase suivante.
  > **Départage** — Points de match. Différence de sets. Différence de score. Nombre de 10 / 9.
  > Barrage si nécessaire.

  Se décompose **exactement** dans les familles existantes : `seeding` (composition des groupes),
  `scoring` (points de match), `tiebreak` (l'ordre à cinq critères ci-dessus), `routing` (où vont les
  qualifiés, et où vont les autres). ⚠️ `DecompteDepartage` (`domain/politiques.py`) ne porte
  aujourd'hui que `nb_dix`/`nb_neuf` : l'enrichir (points, sets, score) **sans casser**
  `TiebreakFftaDefaut` — annoncé au cadrage comme « la rupture de contrat la plus risquée de cette
  US ». *(Rectifié après la revue du 31/07 : le CA parlait de **deux** consommateurs existants, dont
  `classement._cle_departage`. C'est faux — `classement.py` travaille sur son propre décompte privé
  et n'importe pas `DecompteDepartage` ; et `TiebreakFftaDefaut` n'a lui-même aucun appelant de
  production. L'élargissement était donc non cassant, mais **pas pour la raison affirmée** : il n'y
  avait aucun consommateur du tout. On corrige le CA plutôt que de laisser la prochaine US hériter
  d'un fait inexact — cf. [DETTE-028](../docs/dette.md).)*
- **CA — repêchage World Archery (ex-E05US016)** : `routing = repêchage` **réinjecte** certains
  perdants dans le tableau principal ; sélectionnable par phase. À distinguer du **placement**, où le
  perdant va vers un tableau de **classement** sans jamais revenir. `moteur-placement-lucky-loser.md`
  (Q1) le dit : « deux configurations d'un même mécanisme de routage ». Coût faible **une fois**
  E05US010 posée.
- **CA — Big Shoot Off** : règle fournie par le commanditaire le 31/07/2026 — **ferme la question Q9**
  du cahier des charges, bloquante depuis l'origine du projet. Verbatim :
  > *Une phase finale qui reçoit x archers. Ils sont en parallèle, chacun tire x volées de x flèches,
  > et le plus faible score est éliminé — jusqu'aux x derniers restants.*

  ⚠️ **Ce n'est pas un barème de duel mais un TYPE DE PHASE à N participants.** Le « Big » désigne le
  **nombre d'archers**, pas le nombre de flèches. Cela lève la tension du CDC, qui le rangeait tantôt
  en barème (EF-1.5, EF-5.2) tantôt en type de phase (EF-3.2) : c'est bien un type. Quatre
  paramètres : N vient de la source ; V (volées), F (flèches) et K (derniers restants) se règlent à
  la composition — défauts proposés **1 volée de 3 flèches, K = 1**.
- **CA — trois types obtenus par CONFIGURATION, sans code** : le CDC (EF-3.1/EF-3.2) demande aussi un
  *tournoi des perdants*, une *finale* et un *podium*. Aucun n'est un type : le tournoi des perdants
  est un tableau alimenté par « perdants du tour X » ; la **finale** est une phase d'élimination
  directe à **2 participants** alimentée par « gagnants des demies » — elle ne devient une phase
  distincte que si l'on veut lui donner un **barème propre** (E01US011), ce que les sources multiples
  d'E05US010 rendent enfin exprimable ; le **podium** est une **sortie** (les rangs produits par la
  phase terminale), pas une phase. **Vérifier que le catalogue livré couvre bien la séquence
  d'exemple d'EF-3.1** : `qualification → barrage → tableau principal → repêchage → tournoi des
  perdants → tableaux de placement → finale → Big Shoot Off → podium`.

**Notes.**

> **Décisions prises faute de précision** — ⚠️ **arbitrées avec le commanditaire au cadrage du
> 31/07/2026** ; ce qui suit est le CA **à jour**, pas la proposition initiale.
> **Poules** : composition **serpent** depuis le classement source ; nombre de poules saisi, taille
> déduite ; **round-robin complet** par défaut (la règle dit « tout ou partie » : c'est donc un
> **réglage**, `rencontres_par_archer`, pas du code — règle 2) ; victoire **3** / nul **1** /
> défaite **0** *(le commanditaire a écarté le 2/1/0 initialement proposé : 3/1/0 **écarte
> davantage** un vainqueur d'un archer qui accumule les nuls)* ; **aucun défaut** au nombre de
> qualifiés — l'organisateur le saisit, parce qu'il dépend de ce que la **phase suivante** attend
> (un tableau de 16 alimenté par 8 poules en prend 2, par 4 poules en prend 4) ; les non-qualifiés
> vont où la séquence l'indique.
> **BSO** : le cumul entre manches est un **paramètre** (`cumul_des_manches`), à la demande du
> commanditaire, avec **remise à zéro** en valeur pré-remplie — lecture littérale de la règle, et
> c'est ce qui fait le suspense d'une finale spectacle ; au cumul, un mauvais premier tour pèse
> jusqu'au bout et les dernières manches perdent leur enjeu. Égalité au plus faible → **barrage**
> entre les ex æquo (§8.2, réutilisé tel quel) ; les éliminés prennent les rangs dans l'**ordre
> inverse** de leur sortie, ce qui fait du BSO une phase qui **classe tout le monde**, cohérente
> avec le placement 1→N ; **K = 1** par défaut, et si K > 1 les restants **partagent** le rang (la
> règle ne donne aucun critère pour les départager entre eux — leur en inventer un serait ajouter à
> la règle). **Chacune de ces décisions est une politique ou un paramètre ; aucune ne touche le
> moteur.**
>
> ⚠️ **Piège à effectif impair** : tronquer le round-robin (`rencontres_par_archer`) ne donne pas le
> même nombre de rencontres à tout le monde — un tour sur deux fait reposer quelqu'un, donc l'écart
> est d'**une** rencontre. Deux façons honnêtes de l'éviter : composer des poules de taille
> **paire**, ou laisser le round-robin complet. Signalé plutôt que corrigé en douce : rallonger le
> cercle changerait le nombre de rencontres demandé.

> **~~Ce que cette US ne fait pas~~ — le *gate* est levé.** Handicap, système suisse, King of the
> Hill, Ladder et finale spectacle étaient les **cibles** du catalogue ouvert d'EF-3.2, « livrables
> dès que leur règle est écrite », sous le même *gate* que celui qui bloquait le BSO : **pas de règle
> écrite, pas d'US**. ⚠️ **Le commanditaire a fourni les cinq règles le 31/07/2026** — elles sont
> consignées verbatim au [référentiel §10.1](../docs/referentiel-ffta.md) et **entrent dans cette
> US**. Voir les cinq CA ci-dessous.

- **CA — handicap** : règle fournie le 31/07/2026. Le score final vaut **score réalisé + handicap**,
  de sorte qu'un débutant qui dépasse son niveau habituel batte un champion en performance moyenne :
  le format récompense la **progression**, pas la performance absolue. ⚠️ **Ce n'est pas un type de
  phase mais une politique `scoring`** — il ne change ni l'arbre, ni le peuplement, ni le classement,
  seulement l'arithmétique du score ([ADR-0062](../docs/adr/0062-catalogue-de-types-de-phase.md) §1).
  **Arbitrage du 31/07** : l'archer porte **deux valeurs**, un `handicap_officiel` entretenu par le
  club et une `handicap_surcharge` qui le prime pour cette édition. ⚠️ **Aucune table de handicap
  n'entre dans le produit** : le projet n'en possède aucune (la FFTA n'a pas de système officiel ;
  celui qui fait référence est anglo-saxon), et en reconstituer une produirait des classements
  **plausibles mais faux**. Le produit fournit le mécanisme, le club répond de la valeur — cohérent
  avec le point faible que la règle reconnaît elle-même (« le calcul du handicap doit être fiable »).
- **CA — système suisse** : règle fournie le 31/07/2026 — classer beaucoup de participants **sans
  éliminer personne** ; les vainqueurs rencontrent les vainqueurs, les perdants les perdants ; après
  5 à 7 rondes le classement est fiable. **Quatre points laissés ouverts, tranchés au cadrage** :
  nombre de rondes **paramétrable, défaut 5** ; ronde 1 appariée **par classement source, jamais
  aléatoire** (la règle proposait les deux — l'aléa est écarté par la **règle 9 du projet**, qui
  interdit l'aléa non maîtrisé : c'est ce qui permet de reconstruire une phase après un incident le
  jour J) ; **pas de ré-affrontement** (la règle ne le dit pas, mais l'omettre dégrade le format —
  le suisse tire sa précision du fait que chaque ronde apporte une information nouvelle) ; départage
  final **points → Buchholz → critères FFTA**. Effectif impair : **bye** au moins bien classé n'en
  ayant pas encore eu. ⚠️ L'appariement procède par
  **essais avec retour arrière** : il n'échoue que si aucun appariement sans ré-affrontement
  n'existe réellement. *(Le premier jet était glouton et se bloquait sur 53 % des tournois au
  réglage par défaut — mesuré en revue, corrigé.)*
- **CA — King of the Hill & Ladder** : règles fournies le 31/07/2026. **Un seul type**, `colline` :
  ce qui les sépare est la **portée du défi**, donc un paramètre. ⚠️ **La portée est une distance
  MAXIMALE, pas exacte** — la règle dit « le n°6 peut seulement défier le 5 **ou** le 4 », c'est-à-dire
  un **choix** dans une fourchette ; la distance effective tourne d'une manche à l'autre.
  *(Reversé après la revue du 31/07 : le CA disait d'abord « un rang au-dessus, ou deux »,
  formulation qui décrivait l'implémentation d'alors — laquelle figeait la distance à la portée et
  rendait le Ladder **incapable de classer**, la parité de position devenant un invariant. Un CA
  réécrit pour épouser le code se relit sans effort et il est faux : c'est le piège que la règle 9
  vise, un cran au-dessus du code.)*
  **Deux arbitrages du cadrage** : (a) **version « journée »**, pas classement permanent — les règles
  décrivent un classement qui « évolue toute l'année », or une `Phase` a des sources, un effectif et
  une fin **dans un tournoi** ; le classement permanent de club reste un autre produit ; (b)
  mécanique **« deux voisins s'affrontent »**, la seconde des deux que la règle du King of the Hill
  propose, retenue parce qu'elle fait jouer **tout le monde** à chaque manche.
  ⚠️ **Écart consigné, à confirmer à la recette** : l'exemple chiffré du Ladder contredit sa propre
  règle — partant de `1 2 3 4 5 6 7 8`, « le n°6 défie le 4 et gagne » y donne `1 2 3 5 6 4 7 8`,
  soit le n°6 en **5ᵉ** position, alors que « le gagnant monte, le perdant descend » mène à la 4ᵉ.
  **Le moteur applique la règle**, et un test fige l'arbitrage pour qu'un changement futur soit une
  décision et non un glissement.
- **CA — finale spectacle** : règle fournie le 31/07/2026 — après les qualifications, top 8 → quarts
  → demies → petite finale → grande finale, pour créer une montée en intensité ; duels au **système
  de sets** (premier à 6) en arc classique, au **cumul sur 15 flèches** en poulies, barrage à
  égalité. ⚠️ **Ce n'est pas un type** : mécaniquement c'est une élimination directe à 8 avec petite
  finale (livrée par E05US005) plus un `BaremeDuel` qui **existait déjà** (E04US013,
  `preset_ffta_classique` / `preset_ffta_poulies` — 5 volées de 3 = les 15 flèches de la règle). Sa
  part réellement neuve — musique, présentation des archers, écran géant, commentateur, compte à
  rebours, tirs alternés, cible unique — est de la **mise en scène**, donc de l'écran de salle
  (E07US004) et du plan de salle, pas du moteur.

- **Absorbe** : ex-E05US016. **Ajoute** : échauffement, barrage autonome, poules, **et — après que
  le commanditaire en a fourni les règles le 31/07/2026 — handicap, système suisse, King of the Hill,
  Ladder et finale spectacle**, qui étaient jusque-là bloqués par le *gate* « pas de règle écrite,
  pas d'US ».
- **Dépend de** : **E05US010** (le routing générique, sans lequel aucun de ces types n'est routable)
- **Jalon** : J3 · **Origine** : cadrage du 31/07/2026 (règles fournies par le commanditaire)
- **Livrée** : 31/07/2026 — [ADR-0062](../docs/adr/0062-catalogue-de-types-de-phase.md),
  migration `0037` (handicap), moteurs `poule.py`, `big_shoot_off.py`, `barrage.py`, `suisse.py`,
  `colline.py`, recette [`docs/fonctionnel/E05US015.md`](../docs/fonctionnel/E05US015.md)

### ~~E05US018 — Oracle 120~~ → **absorbée par E05US010** *(31/07/2026)*
L'oracle est le **seul** contrôle sérieux du moteur de placement : les séparer laissait la porte
ouverte à un placement livré sans preuve. Le CA « oracle 120 » vit désormais dans E05US010.

### ~~E05US019 — Enregistrer une séquence comme modèle~~ → **livrée par E01US023** *(30/07/2026)*
**Doublon repéré au cadrage du 31/07/2026.** E01US023 a livré l'agrégat `FormatTournoi`, sa
bibliothèque (`/api/v1/formats`), l'application à un tournoi (qui **crée ses phases**) et la
**promotion** (capturer le déroulé d'un tournoi comme format du club) — soit exactement le CA de
cette US. Cf. [ADR-0060](../docs/adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md) §5.
*Leçon de cadrage : le backlog voisin n'avait pas été relu avant de prendre E01US023 ; l'US a été
écrite deux fois sous deux epics.*

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
