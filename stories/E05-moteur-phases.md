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

### E05US020 — Le moteur consomme les prélèvements déclarés *(résorbe le cœur de DETTE-028)*
*En tant qu'*organisateur, *je veux* que le tableau se monte avec **les archers que ma phase déclare
prélever**, *afin que* le tournoi se déroule comme le schéma que j'ai composé et validé.

Origine : [`docs/dette.md` → DETTE-028](../docs/dette.md) (« aucun service ne lit encore
`Phase.sources` pour peupler une phase : `ServiceSaisieDuels._decor` ensemence **chaque** tableau
avec *tous* les archers en lice, quel que soit le prélèvement déclaré ») et
[l'audit de maintenabilité du 03/08/2026](../docs/audit-maintenabilite.md), qui la désigne comme la
**seule dette ouverte fabriquant des défauts visibles par l'utilisateur** — trois des cinq bloquants
d'E06US004 en découlaient.

- **CA — prélèvement par rangs** : une phase qui déclare « les rangs 1 à 32 de la phase 1 » monte son
  tableau avec **ces archers-là**. À 120 archers classés, le tableau est de **32**, pas de 120.
- **CA — plage relative** : « les rangs 33 **et suivants** » se résout sur l'effectif **réel** de la
  phase source — 88 archers si 120 sont classés, 50 si 82 le sont. C'est la promesse d'E05US010
  (`rang_fin=None`), jusqu'ici tenue par la composition seule.
- **CA — première phase** : une phase **sans source déclarée** est alimentée par les inscriptions —
  comportement d'aujourd'hui, à ne pas casser (c'est celui de la qualification, et du tableau tant
  que l'organisateur n'a rien déclaré).
- **CA — l'écart se referme** : la simulation ne signale plus d'écart entre effectif **projeté** et
  **constaté** sur une phase à prélèvement par rangs. Le test de caractérisation posé par E01US024
  (`test_la_simulation_signale_l_ecart_quand_le_moteur_ignore_le_prelevement`) **doit échouer** — il
  a été écrit pour ça, et le retirer fait partie de l'US.
- **CA — le rang prélevé est celui du classement au moment de la lecture** : un abandon est
  **relégué en fin** de classement (ADR-0050) et les suivants **remontent**. « Les rangs 1 à 32 »
  prélève donc toujours 32 archers tant que 32 restent en lice — le 33ᵉ prend la place laissée. Ce
  n'est pas un repêchage décidé ici : c'est la conséquence du classement de qualification, qui se
  recalcule à chaque lecture. *(Vérifié au cadrage : un premier jet de ce CA supposait l'inverse —
  que le prélèvement laisserait un trou.)*
- **Notes — hors périmètre, et dit explicitement** : (a) les prélèvements par **issue de tour**
  (`par_issue_de_tour`) **et « le reste »** (`le_reste`) restent inertes. Vérifié dans le code au
  cadrage : ni l'un ni l'autre n'est **résolu nulle part** — `effectif_selectionne`, `resoudre` et
  `intervalle` rendent tous `None`, et aucun module ne les interprète. Leur donner un sens **ici**
  serait décider une règle métier dans un service d'exécution, l'erreur exacte qu'ADR-0065 §3 a
  refusé de commettre et que `DETTE-033` acte ; (b) une
  source dont la phase amont **n'est pas la qualification** garde le comportement actuel — lire le
  classement d'un tableau amont demande la lecture d'E06US004, et l'y brancher créerait un cycle ;
  (c) les **tableaux par catégorie** ne sont **pas** dans cette US : `SourcePhase` sélectionne par
  **rangs**, `Phase` ne porte aucune catégorie, et le podium par catégorie décerné par des matchs
  demande donc un concept qui n'existe pas encore — US dédiée, avec son ADR. *(L'audit du 03/08
  laissait croire l'inverse ; corrigé dans le même commit que cette US.)*
- **Dépend de** : E05US010, E01US024 · **Jalon** : J3

### E05US021 — Un format connaît son effectif minimum, et le lancement le vérifie
*En tant qu'*organisateur, *je veux* être averti **avant de lancer** mon tournoi si je n'ai pas assez
d'inscrits pour le format choisi, *afin de* basculer sur un autre format plutôt que de le découvrir
sur une tablette en pleine compétition.

Origine : arbitrage du commanditaire du 03/08/2026, au cadrage d'E05US020 —
[ADR-0068](../docs/adr/0068-le-moteur-consomme-les-prelevements-declares.md) §6. « Les inscrits sont
connus au lancement, donc on ne peut pas lancer un tournoi qui n'a pas assez d'inscrits pour son
format ; le logiciel doit connaître la fourchette basse et avertir l'admin avant de lancer. »

- **CA — effectif minimum déduit** : l'application **dérive** des prélèvements le **nombre d'inscrits
  en dessous duquel le format ne peut pas se dérouler** (« les rangs 33 et suivants » exige au moins
  34 classés pour produire un tableau de 2). *(Arbitrage du 04/08/2026 : la déduction, **et non** une
  saisie seule — un nombre saisi peut contredire le déroulé écrit juste en dessous, et le problème
  reviendrait sur la tablette. Le CA d'origine laissait les deux ouverts.)*
- **CA — minimum exigé, facultatif** : un format peut en plus **exiger davantage** que son minimum
  technique (« pas de tournoi de ce type sous 40 archers », règle de club). La valeur saisie ne peut
  pas être **inférieure** au minimum déduit — un format qui l'énonce est **inapplicable**, au même
  titre qu'un format sans barème. *(Arbitrage du 04/08/2026, en réponse au CA d'origine « déclare,
  ou dérive » : c'est **les deux**, le déduit servant de plancher au déclaré.)*
- **CA — avertissement au lancement** : passer un tournoi « en cours » avec un effectif insuffisant
  est **refusé**, avec un message qui nomme la phase et son prélèvement. L'organisateur peut alors
  changer de format. Le compte des inscrits est celui des **archers distincts tous départs
  confondus**, tel que l'affiche déjà le suivi de déroulé.
- **CA — visible avant le clic** : tant que le compte n'y est pas **et que le tournoi n'est pas
  lancé**, l'écran du tournoi affiche en continu **« N inscrits / M requis »** et la cause (la phase
  en cause, ou la règle de club). L'organisateur voit le manque arriver au lieu de le découvrir en
  cliquant « Démarrer ». *(Arbitrage du 04/08/2026 : ajouté au CA — le CA d'origine ne prévoyait que
  le refus au clic, ce qui n'apprend rien tant qu'on ne clique pas. La restriction « pas lancé » a
  été tranchée à la revue : rappeler le manque sur un tournoi en cours serait un reproche sans
  action possible.)*
- **CA — visible à la composition** : l'écran « Composer un déroulé » annonce le minimum du format,
  qu'un effectif soit simulé ou non.
- **Notes** : le moteur refuse déjà de monter un tableau vide (E05US020, `EffectifTableauInvalide`) —
  c'est le **dernier** garde-fou, pas le bon endroit : il s'exprime sur la tablette, en compétition.
  Cette US met le contrôle là où la décision se prend.
- **Notes — portée du calcul** : un rang se lit dans le classement de la **phase source**, pas dans
  les inscrits. Le minimum n'est donc déduit que des prélèvements visant la **phase de
  qualification** — la seule que le moteur sache lire (`_ordre_de_la_qualification`). ⚠️ Viser « la
  première phase » **ne revient pas au même** : un échauffement en tête désactivait tout le contrôle,
  et un déroulé sans qualification se voyait refuser à tort (défaut bloquant trouvé à la revue). Les
  prélèvements par issue de tour, « le reste », et ceux qui visent une phase intermédiaire n'y
  contribuent pas — annoncer un minimum qui les englobe serait annoncer un chiffre faux. Il leur
  reste le **plancher structurel** : une phase qui oppose des tireurs en exige deux, quelle que soit
  la source qui l'alimente (seuls la qualification et l'échauffement se contentent d'un). Ce
  plancher est le **seul** filet pour ces cas : contrairement à ce qu'une première rédaction
  affirmait, `PrelevementVide` ne les couvre pas (il n'existe que pour les prélèvements par rangs, et
  seulement à compte nul).
- **Notes — le plancher ne vaut que pour ce que le moteur déroule.** Un prélèvement par rangs vers
  une **poule**, un système suisse, une colline, un Big Shoot Off ou un barrage autonome ne fixe
  **aucun** minimum : ces types ont un moteur de domaine mais aucun service ne les exécute
  (`DETTE-028`), donc rien ne cassera en salle. Refuser le lancement pour eux serait un **refus
  abusif**, qui ne se répare que le jour J. *(Arbitrage de la contre-revue du 04/08/2026 : un
  premier jet réclamait 34 inscrits pour « qualification → poules », donc empêchait de démarrer un
  tournoi qui se serait joué. L'oracle « ce que le moteur lira » vaut dans les **deux** sens.)*
- **Notes — une seule qualification par déroulé.** L'invariant était supposé par neuf lecteurs de
  « **la** » qualification et vérifié nulle part ; deux d'entre eux la résolvaient différemment
  (plus petit `ordre` / plus grand `id`), si bien qu'un déroulé à deux qualifications faisait
  calculer le minimum sur une phase et prélever dans l'autre. Une anomalie **bloquante**
  (`PlusieursQualifications`) le rend désormais impossible. Une qualification en plusieurs manches
  se règle par son **barème**. *(Arbitrage de la contre-revue du 04/08/2026.)*

  ⚠️ **REVERSÉ le 09/08/2026 par E05US025** ([ADR-0082](../docs/adr/0082-plusieurs-qualifications-dans-un-meme-deroule.md)).
  Le **diagnostic** ci-dessus reste exact ; c'est le **remède** qui était mauvais — on a interdit le
  cas au lieu de réparer les neuf lecteurs, et le commanditaire a ensuite demandé le cas.
  `PlusieursQualifications` n'existe plus, et chaque lecteur sait désormais **de quelle** phase il
  parle. La phrase « une qualification en plusieurs manches se règle par son barème » reste vraie
  *pour ce cas-là* : elle ne décrit simplement pas le format demandé, où les deux tours produisent
  des classements **distincts** et non un cumul.
- **Notes — pas de nouvelle anomalie de composition** : le diagnostic signale **déjà**
  `PrelevementVide` quand un prélèvement ne prend personne à l'effectif simulé. Le minimum est donc
  exposé comme une **donnée** de la projection, pas comme une anomalie de plus — un second
  avertissement sur le même défaut le ferait remonter deux fois, le piège déjà documenté dans
  `_anomalies_effectif_declare`.
- **Dépend de** : E05US020 · **Jalon** : J3

---

### E05US022 — Ancrer la séquence sur l'identité de l'étape
*En tant que* développeur, *je veux* qu'une phase et une source désignent leur cible par son
**identité** et non par son rang, *afin qu'*un réordonnancement ne puisse plus faire exécuter à un
créneau le barème d'une autre étape.

Origine : `DETTE-026`, dont le seuil de résorption (règle 16 — « au 3ᵉ écrivain de la séquence ») a
été **dépassé** par E01US025 : il y en a quatre. Arbitrage du commanditaire du 07/08/2026 —
« prévois ADR et US pour le remède ». Décision : [ADR-0078](../docs/adr/0078-la-sequence-s-ancre-sur-l-identite-de-l-etape.md).

- **CA — la phase pend à son étape** : `phase.etape_id` (clé étrangère vers `deroule_etape`)
  remplace l'appariement par rang. Le rang reste porté par la **seule** étape, et ne décrit plus que
  l'ordre d'affichage.
- **CA — une source désigne une identité** : dans une **édition concrète**, `SourcePhase` cite
  `etape_source_id`. Migration des `config` JSON existantes, la résolution `ordre → identité` se
  faisant **avant** que les rangs perdent leur rôle.
- **CA — le format garde l'ancrage par ordre** : `FormatTournoi` est inchangé. Ses `ModelePhase`
  n'ont pas d'identité par construction ([ADR-0060](../docs/adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md) §5) ;
  l'ordre y est **correct**, pas dégradé. La conversion se fait à `appliquer`, seul point où les
  deux mondes se touchent.
- **CA — les deux `reordonner` de port disparaissent** : renuméroter ne touche plus qu'une colonne
  sans signification relationnelle, donc plus d'état transitoire à doublon et plus d'écriture
  d'ensemble à orchestrer.
- **CA — non-régression** : l'oracle 120 et l'oracle multi-départ restent verts, et le garde-fou de
  portée (`test_portee_sportive.py`) aussi. Le comportement observable ne change **pas** : c'est un
  remède structurel, pas une évolution fonctionnelle.
- **Notes — le contre-argument est écarté explicitement, pas ignoré.** `models.py` objecte qu'« une
  FK dupliquerait l'information tout en pouvant en diverger ». L'ADR répond : le remède ne duplique
  pas, il **sépare** deux rôles que le rang cumulait depuis ADR-0076 (ordre d'affichage **et**
  appariement définition ↔ avancement) — et c'est ce cumul qui produisait la divergence.
- **Notes — l'asymétrie est permanente.** Deux ancrages coexisteront (identité côté édition, ordre
  côté bibliothèque). Ils doivent porter des **noms différents** dans le code, jamais un champ
  polymorphe : un lecteur doit savoir lequel il tient sans relire l'ADR.
- **Résorbe** : `DETTE-026` ; **allège** `DETTE-025` (moins d'écritures à réunir, et celles qui
  restent ne peuvent plus produire d'appariement faux). **Dépend de** : E01US025 · **Jalon** : J3

---

### E05US023 — Les poules jouables de bout en bout *(1ʳᵉ tranche — découpée le 09/08/2026)*
*En tant qu'*organisateur, *je veux* **composer** une phase de poules dans le déroulé à l'atelier
**et** la faire jouer le jour J, *afin de* couvrir le format que le club organise réellement et pas
seulement l'élimination directe.

Origine : `DETTE-028` — les six moteurs et les trois politiques livrés par E05US015 n'ont **aucun
appelant de production** : aucun service ne les instancie, aucune `config.policies` ne sait porter
leurs paramètres, et `ServiceSaisieDuels._decor` refuse tout type autre que l'élimination directe.
**Arbitrage du commanditaire (07/08/2026)** : « oui je veux ces formats jouables, **au plus tôt dans
le backlog**, et aussi et surtout pouvoir les **générer dans le déroulé du format de tournoi dans
l'atelier** ».

⚠️ **Découpage arrêté le 09/08/2026.** Le périmètre d'origine (quatre moteurs × deux surfaces) ne
tient pas dans une branche. Cette US devient la **1ʳᵉ tranche** : le **contrat de phase jouable**
(cf. [ADR-0083](../docs/adr/0083-le-contrat-de-phase-jouable.md)) **plus les poules**, de bout en
bout. Les trois autres formats suivent en `E05US026` (système suisse), `E05US027` (colline),
`E05US028` (Big Shoot Off), chacun portant son moteur **et** son exposition à l'atelier.
**Les poules ouvrent délibérément** : c'est le format le plus riche des quatre (groupes, duels,
barème, table de rangs, départage à cinq critères, barrage), donc celui qui dessine le contrat le
plus accueillant. Poser le contrat sur un format pauvre — le Big Shoot Off n'a ni groupes ni duels —
aurait obligé à le refaire à l'arrivée des poules, **et à repasser sur du code déjà livré**.

- **CA — composer et régler une phase de poules à l'atelier** : choisir le type « poules » ouvre une
  fiche de réglages, là où aujourd'hui le type est sélectionnable mais ses réglages n'ont nulle part
  où aller. Trois réglages : la **taille de poule**, le **barème** de points (victoire / nul /
  défaite, défaut **3 / 1 / 0**, arbitrage du 31/07/2026), et **ce que la poule produit** — un
  classement, ou un nombre de qualifiés. Le schéma à braquets **dessine** la phase comme il dessine
  les tableaux.
- **CA — la taille commande, le nombre de groupes s'en déduit** *(arbitrage du 09/08/2026)* :
  l'organisateur saisit « poules de 4 », **pas** « 8 poules ». Le nombre de groupes vaut
  `effectif ÷ taille` **arrondi vers le bas** (au moins 1), et le reste **gonfle** quelques poules :
  32 archers en poules de 4 donnent 8 poules de 4 ; **30 archers donnent 7 poules — cinq de 4 et
  deux de 5**. Aucune poule ne compte **moins** que la taille demandée. `composer_poules` produit
  déjà des tailles inégales d'une unité : la conversion taille → nombre de groupes se fait à la
  frontière, le domaine ne bouge pas.
- **CA — la répartition obtenue est montrée avant d'être validée** : l'écran affiche, en direct,
  ce que le réglage produit sur l'effectif réel (« 30 archers → 7 poules : cinq de 4, deux de 5 »).
  C'est ce qui rend l'arrondi lisible plutôt que surprenant, et ce qui rend inoffensif le cas
  extrême où l'effectif est inférieur au double de la taille demandée (7 archers en poules de 4 →
  **une** poule de 7, que l'organisateur voit et corrige s'il ne la veut pas).
- **CA — le réglage vit dans le `config` de l'étape, sans migration** : il tient dans le JSON
  existant, **à la racine** (`config.poules`), comme `validation`, `sources` et `effectif`. Aucune
  colonne neuve.

  *(Arbitrage tranché à la revue du 10/08/2026, reversé ici — règle 9. Le CA disait « sous
  `config.policies` », par analogie avec [ADR-0046](../docs/adr/0046-config-policies-politiques-nommees-parametrees.md).
  C'était insatisfaisable en l'état : `config.policies` est le **catalogue fermé** des familles
  injectables (`domain/politiques.py`, `FamillePolitique`), et `assembler_politiques` refuse toute
  clé hors énumération — une phase de poules réglée serait devenue illisible le jour où l'on branche
  la config d'une phase sur son propre validateur. Y faire entrer `poules` aurait demandé une
  **huitième famille décorative** : il n'existe ni implémentation alternative, ni point d'injection,
  ni registre qui la résolve — une taille de poule et un barème sont des **paramètres de phase**,
  pas une stratégie. L'intention du CA — « ça tient dans le JSON, aucune colonne neuve » — est
  tenue à l'identique, et rien ne change pour l'organisateur.)*
- **CA — une poule occupe un bloc de couloirs contigus** *(arbitrage du 09/08/2026, précisé par le
  commanditaire le même jour)* : la phase produit un **plan de cibles**, comme un tableau. L'empreinte
  d'une poule n'est **pas son effectif** mais le nombre d'archers **simultanément sur la ligne**,
  soit `2 × (effectif ÷ 2 arrondi bas)` couloirs — la méthode du cercle ne fait tirer que
  `effectif ÷ 2` rencontres par tour, et à effectif impair un membre se repose. Donc une poule de
  **4 comme de 5 tient sur une seule cible** de 4 couloirs ; une poule de 6 en demande 6 et
  **déborde** sur la cible suivante. Une poule qui déborde n'ouvre pas une cible neuve pour la
  suivante : **la poule d'après démarre au couloir libre juste après**, sans trou. La salle se
  remplit en continu, poule après poule.
- **CA — les rencontres se saisissent comme des duels ordinaires** : une poule n'invente pas une
  façon de tirer, seulement une façon d'apparier et de compter (`domain/poule.py`). Le scoreur
  retrouve le **pavé de saisie de duel** d'E04US013, rencontre par rencontre. Les rencontres sont
  présentées **par tour**, l'ordre que le moteur produit déjà — c'est lui qui garantit qu'un archer
  ne figure pas deux fois dans le même tour, donc que le tour se tire en parallèle.
- **CA — la poule se classe** : la table de poule applique les cinq critères du
  [référentiel §10.1](../docs/referentiel-ffta.md) — points de match, différence de sets, différence
  de score, nombre de 10, nombre de 9 — et marque `ex_aequo` ce que ces cinq critères ne séparent pas.
- **CA — deux régimes d'ex æquo, selon ce que la poule produit** *(arbitrage du 09/08/2026)* :
  - la poule produit un **classement** → le classement *est* le livrable, donc **tout** ex æquo
    irréductible se départage au barrage ;
  - la poule produit un **nombre de qualifiés** → seul le franchissement de la barre compte. Barrage
    **uniquement** si l'égalité tombe **pile sur la barre** ; deux archers à égalité aux rangs 3-4
    d'une poule qui en qualifie 2 **restent à égalité**, et l'outil ne les départage pas.

  Ce régime n'est pas un réglage neuf en base : c'est `nb_qualifies` — vide = « la poule classe »,
  renseigné = « la poule qualifie » —, seulement rendu **explicite à l'écran** plutôt que déduit
  d'un champ laissé vide.
- **CA — le barrage se tire et se saisit** *(arbitrage du 09/08/2026)* : quand un barrage est requis,
  l'outil ouvre une **saisie de flèches** — une par archer à départager — et `resoudre_barrage`
  applique la règle fédérale B.6.5.2 : plus haut score, puis **le plus près du centre**, répété tant
  que l'égalité subsiste ; l'archer **absent est déclaré perdant**. Le verdict **referme le
  classement de la poule**. C'est ce qui ferme la boucle que `DETTE-028` laissait ouverte : le
  moteur de barrage est complet depuis E05US015 et son verdict ne retournait dans aucun classement.
  Le tir de barrage est **tracé en base**, pas seulement son issue.
- **CA — la phase avale consomme les qualifiés** : un tableau déclarant prendre les rangs d'une phase
  de poules est ensemencé par ce que la poule a qualifié, par le mécanisme d'**E05US024**. Le
  classement de la phase de poules est une **source de prélèvement** comme une autre.
- **CA — le classement de phase se lit « par rang de poule d'abord »** *(arbitrage du commanditaire
  du 09/08/2026)* : les poules se jouent **en parallèle** et donnent donc le même classement. Sur
  `P` poules, les rangs `1..P` sont les **vainqueurs** de poule, `P+1..2P` les **deuxièmes**, et
  ainsi de suite. Exemple donné : 4 poules de 3 → rangs 1-4 les premiers de poule, 5-8 les
  deuxièmes, 9-12 les troisièmes.
  - **Tout le monde y figure**, pas seulement les qualifiés : avec `nb_qualifies = 2` sur 4 poules
    de 4, les 3ᵉˢ occupent les rangs 9-12 et les 4ᵉˢ les rangs 13-16. C'est le **prélèvement** de la
    phase avale qui sélectionne, pas le classement qui tronque — ce qui rend une consolante « les
    rangs 9 à 16 » composable sans réglage neuf.
  - **Le dernier bloc peut être incomplet, et les surnuméraires vont en dernier** : 30 archers en
    poules de 4 donnent 7 poules (cinq de 4, deux de 5), donc les rangs 29-30 ne portent que les
    **5ᵉˢ des deux poules de 5**. Normal et sans conséquence.
  - **À l'intérieur d'un bloc, les archers sont ex æquo par défaut.** Un **départage optionnel** par
    décompte (les cinq critères du [référentiel §10.1](../docs/referentiel-ffta.md) — points de
    match, différence de sets, différence de score, nombre de 10, nombre de 9) affine le classement
    **si l'organisateur le demande**. Il n'est pas imposé : comparer des décomptes obtenus contre
    des adversaires différents n'a de valeur que si l'on en a besoin.
- **CA — un prélèvement qui coupe un bloc de poules est refusé, celui qui le contient est honoré** :
  c'est [ADR-0081](../docs/adr/0081-une-phase-attend-que-sa-source-ait-departage-les-places-qu-elle-preleve.md)
  appliqué tel quel, **sans règle nouvelle**. Sur 4 poules, « les rangs 1 à 4 » prend le bloc entier
  des vainqueurs et passe, ex æquo ou non ; « les rangs 1 à 2 » **coupe** ce bloc et est refusé et
  annoncé — sauf si le départage optionnel ci-dessus a été activé. C'est ce qui rend l'option
  auto-régulée : le départage n'est nécessaire que quand la phase avale prélève *à l'intérieur* d'un
  bloc, et l'outil le dit au lieu de qualifier sur un ordre d'affichage.
- **Notes — l'ordre interne d'un bloc pilote la tête de série** : sans départage, l'ordre entre les
  quatre vainqueurs est celui de la composition, donc le vainqueur de la poule 1 devient tête de
  série n°1 — au seul motif que sa poule porte le n°1, qui n'a aucun sens sportif. C'est la même
  faute que `qualifies_de_poule` refuse déjà (« qualifier sur l'ordre d'affichage »). ADR-0081 la
  ferme pour les prélèvements *partiels* ; elle subsiste pour un prélèvement qui prend le bloc
  entier, où elle est sans conséquence sur *qui* passe, mais pas sur *contre qui*.
- **Notes — aucune politique `seeding` neuve n'est nécessaire** *(vérifié le 09/08/2026)*. Le
  **serpent sépare naturellement** les archers d'une même poule au premier tour, parce que le 1ᵉʳ et
  le 2ᵉ d'une poule sont distants de `P` rangs et que le serpent apparie des rangs de somme
  constante.

  ⚠️ **Corrigé à la revue du 10/08/2026 — la conclusion tient, sa raison était fausse.** La mesure
  d'origine (4×2, 8×2, 4×4, 8×4, 16×2, 2×4, 5×2 : « aucun choc ») était un **échantillon biaisé** :
  toutes ces configurations ont soit un nombre de poules pair, soit un effectif non puissance de 2.
  Deux d'entre elles sont même fausses — `5×2` produit la paire (3, 8), tous deux de la poule 3.

  Le vrai discriminant est la **parité du nombre de poules `P`** : à `P` pair le tableau apparie des
  rangs d'écart **impair**, jamais divisible par `P`, donc aucun choc — byes ou pas. À `P` impair il
  existe des paires fautives dès que la paire tombe dans le prélèvement. Le prédicat exact est
  `P impair ET (M+1+P)//2 ≤ N`, `M` étant la taille du tableau ; il a été confronté à l'appariement
  réel du serpent sur 9945 configurations, **zéro désaccord**. Trois réglages le rendent
  inapplicable et font signaler par défaut : le **départage inter-poules** (il réordonne chaque bloc
  de rangs), des **poules de tailles inégales** au-delà du dernier niveau plein, et un nombre de
  poules **inconnu**.

  L'exemple du CA reste vrai : 3 poules × 4 qualifiés = 12 archers produit bien la paire (7, 10) —
  parce que `P = 3` est impair, non parce que 12 n'est pas une puissance de 2. À **signaler à
  l'atelier** plutôt qu'à corriger en douce : corriger demanderait une politique de croisement, donc
  une règle métier que personne n'a demandée.
- **CA — le signal d'écart disparaît pour les poules, et pour elles seules** *(précisé à la revue
  du 10/08/2026 : **deux signaux distincts**, pas un)*. Le **bandeau d'atelier**
  (`TYPES_SIGNALES_EN_ECART`, `Deroule.tsx`) cesse de viser les poules — c'est ce que la puce
  demande, et c'est tenu. Le **bot de simulation** (`simulation_format.py`), lui, ne sait toujours
  pas les jouer : `fabriquer_harnais_simulation` ne construit aucun `ServicePoules`, donc
  `joue=False` y reste **exact**. Les confondre faisait annoncer « joué : 0 tour, 0 duel » comme un
  constat et supprimait l'avertissement. E01US024 signale à
  l'atelier qu'un type composé n'est pas exécutable (`Deroule.tsx`, `simulation_format.py`). Ce
  signal doit cesser de viser les poules **et continuer de viser** le suisse, la colline et le Big
  Shoot Off — sans quoi il mentirait pour ceux qui restent.
- **CA — non-régression** : l'oracle 120 et l'oracle multi-départ restent verts ; un déroulé sans
  phase de poules se comporte **exactement** comme aujourd'hui.
- **Notes — tranche d'un bloc, assumé** : le commanditaire a **explicitement** refusé de couper
  entre « composable » et « jouable » (09/08/2026), en connaissance de la taille annoncée. La revue
  sera lourde ; c'est le prix accepté pour livrer les poules finies en une fois.
- **Notes — un ex æquo *interne* à une poule enjambe deux blocs, et les lie** *(arbitrage tranché en
  cours d'US, 09/08/2026)*. Deux archers que les cinq critères ne séparent pas aux 3ᵉ et 4ᵉ places de
  leur poule occupent le 3ᵉ **et** le 4ᵉ bloc du classement de phase — mais on ne sait pas lequel est
  où. Ces deux blocs sont donc déclarés indécis **ensemble**, sur la seule plage que l'égalité
  enjambe. Sans cette liaison, « les rangs 5 à 6 » passerait en prenant un archer pour un 3ᵉ avéré :
  bien formé, plausible, faux — exactement la classe de défaut qu'ADR-0081 existe pour fermer. La
  liaison est **locale** : elle ne contamine pas les blocs que l'égalité n'enjambe pas, sans quoi un
  ex æquo de fond de poule rendrait toute la phase illisible et refuserait des prélèvements décidés.
  ⚠️ Conséquence à connaître : **avant le premier tir**, tous les membres sont à zéro donc tous
  ex æquo, et le classement de la phase est un **seul** bloc indécis — aucun prélèvement partiel n'y
  est honoré tant que les poules n'ont pas commencé. C'est exact, et c'est ce qu'on veut.
- **Notes — ce que cette tranche ne fait pas** : le suisse, la colline et le Big Shoot Off restent
  injouables (`E05US026` à `E05US028`). `ScoreAvecHandicap` et `RoutingRepechage` restent sans
  appelant — `DETTE-028` n'est donc **pas** refermée ici, seulement rétrécie au périmètre poules.
  Trois capacités restent hors périmètre pour les poules elles-mêmes, et sont dites comme telles :
  le **routage** (« où je tire ensuite » après une rencontre), l'entrée au **palmarès**, et le
  **forfait en poule** — un abandon en poule n'est pas un *walkover*, et la règle n'a pas été posée.
- **Résorbe** : `DETTE-028`, **partiellement** (volet poules + barrage). **Dépend de** : E05US015,
  E05US024 · **Jalon** : J3 · **Origine** : arbitrages des 07/08 et 09/08/2026

---

### E05US024 — Un prélèvement lit le classement de **sa** phase source
*En tant qu'*organisateur, *je veux* que « les rangs 1 à 8 de la phase 2 » prenne les huit premiers
**de la phase 2**, *afin de* composer mon format librement sans que le moteur ne substitue en silence
le classement de la qualification.

Origine : **arbitrage du commanditaire du 08/08/2026**, au cadrage d'`E16US002` — « *la création du
déroulé doit permettre de composer les phases comme on en a envie, le club est libre de son format de
tournoi* ». Reste ouvert de `DETTE-028` : E05US020 a fait consommer les prélèvements **visant la
qualification** et a laissé les autres au comportement d'avant, explicitement.

- **CA — le classement lu est celui de la phase désignée** : une phase déclarant « les rangs 1 à 8 de
  la phase 2 » monte son tableau avec les huit premiers du classement **de la phase 2**, quel que
  soit le type de celle-ci. Aujourd'hui ce prélèvement est **ignoré** et la phase reçoit *tous* les
  archers en lice — un tableau bien formé, plausible, et faux, que rien ne signale.
- **CA — la cascade tient sur plusieurs crans** : la phase 3 prélève dans la phase 2, qui prélève
  dans la phase 1. La résolution est **récursive** sur le déroulé, acyclique par construction —
  `verifier_sequence` exige qu'une source soit **antérieure**, donc la descente termine.
- **CA — la phase de tête est inchangée** : une phase **sans** source déclarée est alimentée par les
  inscriptions. C'est le cas de la qualification, et d'un tableau tant que rien n'est déclaré. Le
  comportement d'aujourd'hui ne bouge pas — c'est le CA « première phase » d'E05US020, à ne pas casser.
- **CA — `tranche` suit la même règle** : le premier rang du tournoi qu'une phase dispute se lit sur
  **sa** phase source ([ADR-0068](../docs/adr/0068-le-moteur-consomme-les-prelevements-declares.md) §5).
  Sans quoi le palmarès resitue les positions dans le mauvais espace de rangs — c'était `DETTE-034`.
  Le décalage se **cumule** : une phase prélevant « les rangs 1 à 2 » d'un tableau qui disputait
  lui-même les places 33 et suivantes joue pour la **33ᵉ** place, pas pour la 1ᵉʳᵉ.
- **CA — une phase attend que sa source ait départagé les places qu'elle prélève**
  *(ajouté le 08/08/2026 sur relevé de revue adversariale — [ADR-0081](../docs/adr/0081-une-phase-attend-que-sa-source-ait-departage-les-places-qu-elle-preleve.md))*.
  Un tableau ne décerne pas des rangs mais des **fourchettes**, et avant son premier duel un tableau
  de 8 porte ses huit archers sur la même plage `[1..8]`. Une consolante « les rangs 5 à 8 » y
  recevait les 4 derniers **qualifiés** au lieu des 4 battus des quarts — bien formé, plausible et
  faux, et **moins détectable** qu'avant l'US (la population avait le bon cardinal).
  La règle : une fenêtre est honorée si elle ne **coupe** pas un bloc indécis — chevaucher **sans
  contenir**. « Les rangs 1 à 2 » sur les deux finalistes `[1..2]` reste honoré (elle veut les deux
  finalistes) ; « les rangs 5 à 8 » sur un tableau non commencé est **refusé et annoncé**.
  L'écran public affiche « en attente du tableau *n* », le plan de cibles n'est pas produit, la
  saisie refuse (409), et le palmarès écarte la phase.
- **CA — l'effectif minimum suit la chaîne** : `effectif_minimum` (E05US021) traduit un rang en
  nombre d'inscrits en **remontant la chaîne des sources** jusqu'à la phase alimentée par les
  inscriptions, au lieu de ne reconnaître que la qualification. Un déroulé « tableau des rangs 17 à
  32 → tableau des rangs 5 et suivants » annonce donc son plancher (22 inscrits), là où il est muet
  aujourd'hui.
  ⚠️ **Arbitrage du 08/08/2026, reversé ici depuis la revue** : ce CA citait « poules → tableau »,
  ce que l'US **ne livre pas** — le moteur ne sait lire que la qualification et l'élimination
  directe (`_TYPES_CLASSANTS_LUS`), une source visant des poules reste ignorée en silence jusqu'à
  **E05US023**. Le CA était **faux, et non ambigu** : il s'écrivait sans effort, donc le garde-fou
  « CA ambigu » ne pouvait pas se déclencher, et l'US suivante en aurait dérivé ses tests.
- **CA — plan de cibles et arbre restent ensemencés à l'identique** : `ServicePlacementDuels` et
  `ServiceSaisieDuels` continuent de lire la **même** règle (`application/prelevement.py`). L'écart
  mesuré à la revue d'E05US020 — plan de 8 placements pour un tableau de 4 — ne doit pas se rouvrir.
- **CA — non-régression** : l'oracle 120 et l'oracle multi-départ restent verts.
- **Notes — le cycle invoqué par E05US020 n'existe pas** *(vérifié le 08/08/2026)*. E05US020 écartait
  le cas parce que « lire le classement d'un tableau amont demande la lecture d'E06US004 et créerait
  un cycle ». `palmares.py` importe bien `ServiceSaisieDuels`, donc l'inverse fermerait la boucle —
  mais la lecture nécessaire est `tableau.positions_acquises()`, que `ServiceSaisieDuels.reconstruire`
  produit **déjà lui-même**. Ce n'est donc pas un cycle de modules, c'est une **récursion** d'un
  service sur lui-même, sur un graphe acyclique. La note était exacte quand elle a été écrite
  (E06US004 n'était pas livrée) ; elle ne l'est plus.
- **Notes — coût d'exécution à surveiller** : `DETTE-031` signale déjà que `reconstruire` rebâtit
  tout le classement du tournoi **une fois par phase à tableau**, sans cache ni plafond, sur deux
  routes publiques non authentifiées. La récursion multiplie ces reconstructions par la profondeur de
  la cascade. Mémoïser la résolution **à l'intérieur d'un appel** fait partie de cette US ; le cache
  transverse reste `DETTE-031` et n'est pas rouvert ici.
- **Notes — natures inertes inchangées** : `le_reste` et `par_issue_de_tour` restent non résolues
  (`DETTE-033`). Cette US élargit **quelle phase** on lit, pas **quelles natures** on sait résoudre.
- **Notes — ne préempte pas E05US022** : les sources désignent toujours leur cible par `ordre_source`.
  L'ancrage par **identité** reste le sujet d'E05US022, et cette US ne le rend ni plus ni moins urgent.
- **Notes — surface** : **aucune ligne de front, aucun écran neuf**, donc pas de fiche
  `docs/fonctionnel/` (rien de nouveau à faire cliquer). Mais la capacité **est visible du
  commanditaire** — « composer mon format et qu'il se joue » est exactement ce qu'il a demandé le
  08/08/2026 —, donc **fichier daté au journal et résumé mis à jour**. Le critère retenu est *ce que
  l'US change pour l'organisateur*, pas *le nombre de fichiers `.tsx` touchés* : une US de moteur peut
  n'avoir aucune surface d'écran et changer ce que la salle joue.
- **Résorbe** : le reste de `DETTE-028` pour les prélèvements **par rangs**.
  **Dépend de** : E05US020, E06US004 · **Jalon** : J3 · **Origine** : arbitrage du 08/08/2026

---

### E05US025 — Plusieurs qualifications dans un même déroulé
*En tant qu'*organisateur, *je veux* composer **plus d'une** phase de qualification dans un tournoi,
*afin de* ne pas être enfermé dans le format « une qualification, puis des tableaux ».

Origine : **arbitrage du commanditaire du 08/08/2026** — « *pourquoi on ne peut pas, dans la création
d'un tournoi, faire plusieurs phases de qualification ?* ». L'interdiction n'est **pas une règle
métier** : `_anomalies_unicite_qualification` (`domain/phase.py`, E05US021) se décrit elle-même comme
un invariant « **supposé partout et vérifié nulle part** », posé pour fermer un bug — neuf lecteurs de
« **la** » qualification, dont deux la résolvaient différemment — plutôt que pour exprimer une règle
du tir à l'arc. On a interdit le cas au lieu de réparer les lecteurs ; cette US répare les lecteurs.

- **CA — deux qualifications coexistent** : un déroulé porte plusieurs étapes de type `qualification`,
  chacune avec ses **propres** réglages (barème, grain de validation). L'anomalie
  `PlusieursQualifications` disparaît.
- **CA — qualifications successives** : la seconde se peuple du prélèvement qu'elle déclare
  (« seuls les X premiers sont qualifiés »), par le mécanisme livré en **E05US024**.
- **CA — le barème se règle par qualification** : `ServiceBaremeQualification` cesse de parler du
  « barème **du tournoi** » (`bareme_du_tournoi`, et un `definir` qui crée la qualification en tête
  d'office) ; il règle celui d'une **étape désignée**. L'écran « Barème & validation » suit.
- **CA — la saisie sait dans quelle qualification elle écrit** : un archer engagé dans deux
  qualifications y tient deux séries distinctes, et une flèche saisie ne peut pas atterrir dans la
  mauvaise.
- **CA — non-régression** : un tournoi à **une** qualification se comporte exactement comme
  aujourd'hui, oracle 120 compris.
- **CA — le rang vient de la phase, jamais du cumul** : le classement d'un archer est sa **position
  dans l'effectif de sa phase**, décalée par les effectifs des phases amont. Un tournoi qui coupe
  120 archers en une *haute* (rangs 1..60) et une *basse* (rangs 61..120) rend un classement final
  de 1 à 120 où **le dernier de la haute précède le premier de la basse, même si celui-ci a mieux
  tiré** : la répartition est décidée par la phase amont, pas par les points du second tour.
  ⚠️ Un classement obtenu en **triant toutes les séries par total** est donc faux — c'est la
  réalisation naïve que ce CA existe pour interdire.
- **CA — la complétude juge chaque qualification sur son propre effectif** : « Prêt à terminer ? »
  exige les **trois** qualifications de l'exemple, la première sur ses 120 archers, la haute et la
  basse sur leurs 60. Ne regarder que les phases terminales laisserait passer une feuille jamais
  close au premier tour — or c'est ce tour-là qui décide qui va où.
- **CA — la saisie ne montre que la phase en cours** : au second tour, l'écran de saisie affiche les
  flèches du moment et **rien du tour précédent** (pas de rappel du total). Écran utilisé debout au
  pas de tir : on ne le charge pas d'une information qui ne sert pas au geste (règle 10).

  **Arbitrages rendus au cadrage du 09/08/2026** *(les trois points laissés ouverts le 08/08 ci-dessus
  sont tranchés ; le quatrième — la forme du déroulé — s'est révélé être une **fausse contrainte** de
  l'assistant, et mérite d'être noté pour qu'on ne la réintroduise pas)* :
  **la fourche est déjà représentable.** `_anomalies_ordres` exige des ordres `1..N` sans trou ni
  doublon, ce qui se lit à tort comme « le déroulé est linéaire, donc pas de branchement ». L'`ordre`
  est un **ordre topologique** — il dit *qui peut alimenter qui*, pas *qui passe avant qui sur le pas
  de tir* — et le contrôle de recoupement de rangs ne joue **qu'entre les sources d'une même phase**.
  Deux phases peuvent donc puiser dans la même phase amont, et rien n'impose non plus **une seule
  phase en cours à la fois** (`ServicePhases._transition` ne regarde que la phase visée ;
  `domain/suivi_deroule.py` le dit noir sur blanc). La *haute* et la *basse* se composent et se
  jouent ensemble sans toucher au séquencement : seul `_anomalies_unicite_qualification` les bloque.
  L'exemple de référence du commanditaire :

  ```
  ordre 1 : Qualification          3×20   ← les 120 inscrits       → classement de 120
  ordre 2 : Qualification haute    3×15   ← rangs   1..60 de l'ordre 1  → rangs finaux   1..60
  ordre 3 : Qualification basse    3×15   ← rangs  61..120 de l'ordre 1 → rangs finaux  61..120
  ```
- **Notes** : les **9 appels** de `application/portee.py:qualification_du_tournoi` (7 modules —
  `saisie` ×3, `completude` ×2, `classements`, `feuille_de_marque`, `forfaits`,
  `pilotage_simulation`) sont à trier un par un — plusieurs restent légitimes tels quels. Terrain
  marqué `DETTE-048` : ce module est « le seul à n'être ni testé ni surveillé », et les deux derniers
  défauts de portée en sont sortis. *(La fiche annonçait « 12 appels, 9 modules » ; le relevé du
  09/08/2026 en trouve 9 dans 7 modules. Chiffre corrigé plutôt que recopié.)*
  **ADR attendu.**
- **Notes — arbitrage rendu en revue (09/08/2026) : qui écrit dans quelle qualification.** Le CA
  « la saisie sait dans quelle qualification elle écrit » n'est **pas** satisfait par « la phase en
  cours du créneau » : la *haute* et la *basse* se jouant **ensemble**, cette règle désigne la même
  phase pour tout le monde et enverrait les 60 archers de la basse écrire dans la feuille de la
  haute. La discrimination se fait sur la **population** — une qualification prélevée ne reçoit que
  les archers que ses sources lui ont donnés, lus par le **même** résolveur de classement que le
  plan de cibles et le palmarès (`application/prelevement.py`, port `LecteurPopulationPhase`). Même
  règle pour la complétude, qui juge **chaque** qualification sur **sa** population. Sur un créneau
  mono-qualification, la lecture de classement n'est pas même tentée : non-régression par
  construction, et aucun coût ajouté au chemin chaud de la saisie.
- **Notes — le vrai câblage à casser** : au-delà de la portée, c'est `application/saisie_duels.py`
  qui résout « phase de type qualification → le classement du départ », **quel que soit son ordre**.
  Tant qu'il tient, la *haute* et la *basse* liraient toutes deux le classement du premier tour.
- **Notes — `Serie` n'a pas de phase** : le port l'annonce (« une série par archer ») et la clé est
  `(tournoi_id, archer_id)`. Un archer engagé dans deux qualifications y tient **deux feuilles** :
  changement de modèle + **migration Alembic**, et reprise des lecteurs qui indexent par
  `dict[ArcherId, Serie]`. C'est le vrai coût de l'US, pas le tri des appels de portée.
- **Notes — `definir` crée une qualification d'office** : `ServiceBaremeQualification.definir` fabrique
  une étape de qualification **en tête du déroulé** et décale tout le reste d'un cran quand il n'en
  trouve pas, et l'API n'expose que `PUT /tournois/{id}/bareme-qualification`, sans `phase_id`. Avec
  trois qualifications à 3×20, 3×15 et 3×15, ce chemin n'a plus de sens : le barème se règle sur une
  **étape désignée**. Emporte l'écran « Barème & validation » et une route neuve — donc **fiche
  `docs/fonctionnel/`** (contrairement à E05US024, cette US a bien une surface).
- **Dépend de** : **E05US024** (nécessaire, pas seulement souhaitable : sans peuplement générique une
  seconde qualification recevrait *tous* les inscrits) · **Jalon** : J3 · **Origine** : arbitrage du 08/08/2026

---

### E05US026 — Le système suisse jouable
*En tant qu'*organisateur, *je veux* composer et faire jouer une phase au **système suisse**, *afin de*
classer un gros effectif en peu de rondes sans éliminer personne.

Origine : 2ᵉ tranche du découpage d'`E05US023` (09/08/2026). Le moteur (`domain/suisse.py`,
`apparier_ronde` / `classement_suisse`, appariement par points avec évitement des revanches et
gestion des byes) est complet depuis E05US015 et **sans appelant de production**.

- **CA — habiter le contrat de phase jouable** posé par `E05US023`
  ([ADR-0083](../docs/adr/0083-le-contrat-de-phase-jouable.md)) : cette US **n'a pas à le redessiner**.
  Si elle doit l'élargir, l'élargissement se documente à l'ADR — c'est le signal que le contrat a été
  taillé trop court, et il vaut d'être tracé.
- **CA — réglages à l'atelier** : nombre de rondes (`ConfigurationSuisse`), avec le maximum que
  l'effectif autorise affiché en clair (`_rondes_maximales`).
- **CA — les rondes s'enchaînent** : l'appariement de la ronde `n+1` se calcule des résultats de la
  ronde `n`, et le plan de cibles suit — mêmes règles d'empreinte et de contiguïté qu'en poules.
- **CA — le signal d'écart d'E01US024 cesse de viser le suisse**, et lui seul.
- **Dépend de** : `E05US023` · **Jalon** : J3 · **Résorbe** : `DETTE-028` (volet suisse)

#### Arbitrages du cadrage du 15/08/2026 *(reversés ici, règle 9)*

Le CA ci-dessus est celui du découpage du 09/08/2026. Cinq points ont été tranchés au cadrage, et
le périmètre en sort **élargi** — trois d'entre eux dépassent le seul système suisse :

1. **Le plan de cibles du suisse est `PAR_DUEL`, recalculé à chaque ronde.** Le CA disait « mêmes
   règles d'empreinte et de contiguïté qu'en poules », ce qui n'était pas transposable : une poule
   est un **groupe stable** occupant un bloc de couloirs (ADR-0083 §3), là où une ronde de suisse
   ré-apparie **tout le plateau**. Une ronde de suisse est un tour de duels : elle réutilise
   `ServicePlacementDuels` et le côte-à-côte d'[ADR-0048](../docs/adr/0048-cote-a-cote-des-duellistes-par-reordonnancement.md),
   donc **aucune table ni migration neuve**. Le CA a été écrit par analogie avec la tranche
   précédente ; l'analogie était fausse.
2. **Le routage entre dans le périmètre — et il y entre aussi pour les poules.** `route_l_archer`
   passe à `True` pour `SUISSE` **et** `POULES`. Le calcul « où cet archer tire-t-il à la ronde
   suivante » s'écrit de toute façon pour le suisse ; l'étendre aux poules coûte quelques lignes, et
   ne pas le faire laisserait les poules **seul format jouable sans routage** alors que le Big Shoot
   Off l'a depuis `E05US028`.
3. **Le palmarès entre dans le périmètre, et sa règle n'est pas « par type de phase ».**
   Une phase **décerne** ses rangs — donc peut donner une médaille — **si et seulement si aucune
   phase avale ne prélève dedans**. Le critère est structurel, lu sur le graphe des sources, et il
   remplace l'intuition de départ (« une phase de poules ne titre jamais »), que le commanditaire a
   lui-même invalidée en décrivant sa cascade : dans un format « 6 poules → 6 poules de niveau », la
   dernière phase **est** une phase de poules et rend le classement final exact. Conséquences :
   - une phase **consommée** contribue ses rangs sans médaille (`origine=QUALIFICATION`) — ce qui
     classe enfin les **non-qualifiés** d'une phase de poules à leur vraie place plutôt qu'à leur
     rang de qualification ;
   - une phase **terminale** décerne (`origine=DUELS`) ;
   - la règle vaut pour **tous** les types, donc elle sert aussi la colline en `E05US027`.
4. **Le palmarès affiche les deux informations** *(arbitrage du commanditaire, 15/08/2026)* : le rang
   de tournoi **et** l'origine du rang — « **19ᵉ** » *et* « **1ᵉʳ de la poule D** ». La question posée
   était de choisir l'information principale ; la réponse est qu'aucune ne se suffit. Le rang seul
   perd ce que l'archer a réellement gagné sur le terrain ; l'origine seule ne dit pas où il finit au
   tournoi. Le modèle porte déjà les deux (`OriginePalmares`, `PositionPhase`) : c'est l'écran et le
   PDF qui doivent rendre le couple.
5. **L'US s'arrête au backend ; le front part en `E05US030`** *(arbitrage du commanditaire,
   15/08/2026, en cours d'US)*. Le périmètre avait triplé depuis la fiche d'origine — suisse +
   routage des poules + palmarès + remède structurel — et le commanditaire a coupé au bon endroit :
   la couture backend/front est la seule qui **ne coûte rien** à trancher ici, parce que les quatre
   commits déjà écrits sont chacun cohérents et relisibles seuls.

   ⚠️ **Conséquence sur les livrables de suivi, et elle a été rectifiée en cours d'US.** Le premier
   raisonnement disait : `E05US026` n'a **aucune** surface utilisateur, donc ni fichier daté ni
   scénario fonctionnel, seuls les chiffres repères bougent. **C'était faux d'un cran**, et la
   vérification l'a montré : deux élargissements du cadrage touchent des écrans **déjà livrés** —
   le **routage des poules** (le panneau « où je tire ensuite » répondait à tous les formats joués
   sauf celui-là) et le **palmarès des poules** (les non-qualifiés retombaient à leur rang de
   qualification). Un fichier daté est donc bien produit, **restreint à ces deux effets**, et il dit
   explicitement que le suisse n'a pas encore d'écran. Le scénario dans
   [`docs/fonctionnel/`](../docs/fonctionnel/) reste à `E05US030`, qui livrera les écrans à
   recetter. *Leçon : « pas d'écran neuf » ne veut pas dire « rien de visible » — un changement de
   règle se voit sur les écrans existants.*

6. **Le port de classement est unifié dans cette US, avec son ADR.** `LecteurClassementPoules` et
   `LecteurClassementBigShootOff` sont deux protocoles identiques, dupliqués **volontairement** en
   `E05US028` faute d'une 3ᵉ occurrence réelle ; le suisse est cette 3ᵉ. Le remède —
   `dict[TypePhase, LecteurClassementDePhase]` — se pose donc sur preuve. ⚠️ **Écart assumé à la
   règle « un remède structurel se traite en US dédiée »**, tranché par le commanditaire le
   15/08/2026 : la preuve naît *dans ce diff*, et différer obligerait à écrire un 3ᵉ port jetable
   pour le défaire aussitôt. La contrepartie exigée est la **lisibilité de la revue** — le remède
   voyage dans un **commit séparé**, en tête de branche, sans une ligne de suisse dedans.

---

### E05US027 — La colline jouable
*En tant qu'*organisateur, *je veux* composer et faire jouer une phase de **colline**, *afin de*
proposer le format à défis que le club utilise en animation.

Origine : 3ᵉ tranche du découpage d'`E05US023` (09/08/2026). Moteur complet (`domain/colline.py`,
`defis_de_la_manche` / `appliquer_manche` / `classement_colline`), sans appelant de production.

> 📌 **Rendez-vous posé par la revue d'`E05US030` (16/08/2026) — la 3ᵉ occurrence, c'est ici.**
> `decrirePlaces` et `etatRencontre` sont aujourd'hui **dupliqués** entre `features/poules` et
> `features/suisse`, caractère pour caractère. C'est une 2ᵉ occurrence, et « dupliquer une 2ᵉ fois
> et attendre le 3ᵉ cas » est la réponse que le § *Dette* de `CLAUDE.md` tient pour valide : rien
> n'a donc été extrait. Mais sans ce rendez-vous écrit, la colline recopierait une **3ᵉ** fois par
> mimétisme, et le seuil serait franchi sans que personne le remarque. À l'extraction, les emmener
> vers `shared/` — le tuple `Place` y est déjà parti (`shared/salle/place.ts`).
>
> ⚠️ **Et un point de contrat** : la colline partage le décor `RONDES_APPARIEES` du suisse, donc
> elle produira le même cas « en course, mais rien à tirer maintenant ». L'issue existe désormais
> (`EN_ATTENTE`, [ADR-0087](../docs/adr/0087-une-attente-n-est-pas-une-indisponibilite.md)) —
> il n'y aura rien à inventer, mais il faudra la **brancher des deux côtés dans la même US**, la
> sûreté du contrat venant du déploiement conjoint et non d'un mécanisme de typage.

- **CA — habiter le contrat de phase jouable**, mêmes termes qu'`E05US026`.
- **CA — réglages à l'atelier** : portée de défi et nombre de manches (`ConfigurationColline`).
- **CA — les manches s'enchaînent** et le classement se lit de l'ordre final de la colline.
- **CA — le signal d'écart d'E01US024 cesse de viser la colline**, et elle seule.
- **Dépend de** : `E05US023` · **Jalon** : J3 · **Résorbe** : `DETTE-028` (volet colline)

---

### E05US028 — Le Big Shoot Off jouable
*En tant qu'*organisateur, *je veux* composer et faire jouer un **Big Shoot Off**, *afin de* trancher
un gros effectif au spectacle, tout le monde sur la ligne.

Origine : 4ᵉ tranche du découpage d'`E05US023` (09/08/2026). Moteur complet
(`domain/big_shoot_off.py`, `demarrer` / `jouer_manche` / `eliminer_apres_barrage`), sans appelant.

- **CA — habiter le contrat de phase jouable**, mêmes termes qu'`E05US026`. ⚠️ C'est le format qui
  **l'éprouvera le plus** : il n'a ni groupes ni duels, et son grain de validation est
  `FIN_DE_SERIE` là où les trois autres sont `FIN_DE_DUEL`. Si le contrat d'`E05US023` doit céder
  quelque part, c'est ici — et c'est **voulu** : on a préféré tailler le contrat sur le format le
  plus riche et l'assouplir pour le plus pauvre, plutôt que l'inverse.
- **CA — réglages à l'atelier** : **le nombre de sortants, manche par manche** — une liste écrite par
  l'organisateur (`4, 2, 1` = quatre sortent au 1ᵉʳ tour, deux au 2ᵉ, un au 3ᵉ) —, plus le format du
  tir (volées, flèches par volée), le **cumul** entre manches et le **départage des sortants**
  (`ConfigurationBigShootOff`). L'atelier **montre la projection** sur l'effectif du jour, patron
  `RepartitionPoules` : « avec vos 12 inscrits : 12 → 8 → 6 → 5 ».

  ⚠️ **Ce CA était faux, et sa correction est l'événement du cadrage** *(14/08/2026)*. Il annonçait
  « nombre d'éliminés par manche **et restants** » en citant `ConfigurationBigShootOff`, qui ne
  portait **ni l'un ni l'autre** : elle avait `restants` (K) et éliminait **un** archer par manche.
  La divergence est apparue en essayant d'écrire le test depuis le CA — exactement le garde-fou de
  la règle 9 — et le commanditaire, questionné, a **élargi la règle** plutôt que corrigé le CA :
  plusieurs sortants par manche, dits manche par manche. Quatre arbitrages en sont sortis, tous
  reversés au [référentiel §10.1](../docs/referentiel-ffta.md) qui fait autorité sur ce format :
  - le réglage est **une liste, une case par manche** — pas une progression imposée ;
  - **K disparaît** des réglages : il se déduit de ce que la liste n'élimine pas ;
  - **on joue tant que la manche est possible** : une liste ne se refuse jamais, elle s'écourte (un
    format est de la configuration, règle 2 — il se réutilise sur des effectifs qu'il ignore) ;
  - les sortants d'une même manche sont **classés au score de la manche** ; les départager quand ils
    sont à égalité est un **paramètre** (`departage_les_sortants`), jumeau de
    `ReglageDePoules.departage_inter_poules`.

- **CA — le classement de la phase est lisible** : une phase avale peut y prélever, et le
  **palmarès** consomme les rangs qu'elle a décernés. *(Ajouté au cadrage du 14/08/2026 : le CA
  initial s'arrêtait à « habiter le contrat », or `TYPES_RECONSTRUCTIBLES` n'accueille que les
  arbres rejouables — un Big Shoot Off rend des rangs **exacts** sans arbre à rejouer, donc un
  `_resultat` propre au format, ce qu'[ADR-0083](../docs/adr/0083-le-contrat-de-phase-jouable.md)
  annonçait déjà comme la condition d'entrée au palmarès.)*

- **CA — le routage sait où l'archer tire ensuite** (`route_l_archer`). *(Ajouté au cadrage du
  14/08/2026, à la demande du commanditaire. `route_l_archer` était resté `False` pour les poules
  en E05US023, capacité explicitement hors périmètre ; elle est demandée ici.)*
- **CA — le barrage y retourne son verdict** : l'égalité au plus faible se départage par
  `resoudre_barrage`, dont `eliminer_apres_barrage` consomme déjà l'issue. La **saisie** du barrage
  est celle livrée par `E05US023` — pas une seconde.
- **CA — le signal d'écart d'E01US024 cesse de viser le Big Shoot Off**, et lui seul. À cette US, et
  seulement à cette US, `DETTE-028` peut être **refermée** sur son volet « moteurs sans appelant ».
- **Dépend de** : `E05US023` · **Jalon** : J3 · **Résorbe** : `DETTE-028` (volet Big Shoot Off)

#### Arbitrages tranchés en cours d'US et à la revue *(reversés ici, règle 9)*

Trois arbitrages du commanditaire, **postérieurs à la rédaction du CA**, tous reversés au
[référentiel §10.1](../docs/referentiel-ffta.md) dans le même commit que le code qui les applique :

1. **Convention du rang partagé** *(15/08/2026)* — « à égalité ils partagent leur rang » ne disait
   pas **lequel**. C'est la convention **« 1224 »** : chacun prend `1 + le nombre d'archers
   strictement meilleurs`, les rangs sautés restent vacants **après** le groupe. Le code appliquait
   la convention inverse, et son test la figeait tout en invoquant « 1224 » dans sa docstring.
2. **Une liste doit converger vers un vainqueur unique** *(15/08/2026)* — refus **à la composition**,
   là où l'effectif est connu (une phase posée sur un créneau), jamais sur le format de bibliothèque :
   la convergence est une propriété du couple (liste, effectif), pas de la liste. Sans ce refus, un
   Big Shoot Off fini à N rescapés leur décernait l'or à tous et bloquait définitivement le
   prélèvement d'une phase avale.
3. **La correction d'une flèche validée reste hors périmètre** *(15/08/2026)* — dette assumée
   (`DETTE-061`), livrée en US dédiée. Le rejeu la supporte déjà ; c'est le geste d'entrée qui manque.

⚠️ **Le CA portait par ailleurs un réglage que le moteur n'a jamais eu** (« nombre d'éliminés par
manche **et restants** ») : la contradiction est sortie en écrivant les tests depuis le CA, et a
produit l'élargissement de règle du 14/08/2026 — `K` cesse d'être un paramètre et se déduit. C'est le
garde-fou de la règle 9 qui a fonctionné, et la trace est gardée ici pour la prochaine lecture.

**Vocabulaire tranché au cadrage** : on dit « **le nombre de sortants, manche par manche** », jamais
« la suite » — le mot faisait entendre une progression imposée par l'outil, alors que l'organisateur
écrit une liste libre.

---

### E05US029 — Des **poules de niveau** en une seule étape
*En tant qu'*organisateur, *je veux* composer « une phase de poules **par niveau** » en une étape qui
se déplie en groupes, *afin de* monter un tournoi club en cascade sans écrire une étape par groupe.

Origine : **cadrage d'`E05US026`, le 15/08/2026**. Le commanditaire a décrit un format club en
cascade et demandé que cette US soit prise **après** `E05US026`, dont elle dépend par le palmarès :

> 36 archers. **Phase 1** : 6 poules de 6, disputant les rangs 1-36. **Phase 2** : 6 poules de 6, mais
> composées **par niveau** — les rangs 1-6, 7-12, 13-18, 19-24, 25-30, 31-36. Le classement de la
> phase 2 est alors le **classement final** du tournoi, exact de 1 à 36. Variante : 3 qualifiés par
> poule, plusieurs phases enchaînées, et le palmarès se resserre de cran en cran.

**Le format est déjà composable aujourd'hui, et il faut le dire d'emblée** : il s'écrit en **une étape
par niveau** — six étapes, chacune portant une poule et sa source (« les rangs 1 à 6 de la phase 1 »,
« les rangs 7 à 12 »…). C'est `E05US024` / [ADR-0080](../docs/adr/0080-un-prelevement-lit-le-classement-de-sa-phase-source.md)
qui l'a ouvert, et `E05US026` qui rend son classement final réellement publiable. Cette US-ci est donc
un **confort de composition**, pas une capacité manquante — d'où son rang après, et non avant.

⚠️ **Et « une étape par niveau » n'est pas qu'un contournement : c'est la forme exacte.** Deux
obstacles s'y opposent dans le modèle du jour, tous deux structurels et non cosmétiques :

1. **Le serpent.** `composer_poules` répartit en serpentin — 1→A, 2→B, 3→C, 4→C, 5→B, 6→A — et c'est
   un arbitrage explicite du 31/07/2026 : il équilibre la force des groupes pour ne pas éliminer la
   moitié des favoris au premier tour. Il est **juste pour la première** phase de poules, où personne
   ne connaît encore les niveaux, et **faux pour les suivantes**, dont tout l'intérêt est que la poule
   A soit celle des meilleurs. Composer les six poules d'une phase 2 par le serpent éparpillerait les
   six têtes dans les six groupes, soit l'inverse exact de l'intention.
2. **L'espace de rangs est porté par la *phase*, pas par la *poule*.** `ResultatPhase.rang_premier`
   (« le premier rang du tournoi que cette phase dispute », [ADR-0068](../docs/adr/0068-le-moteur-consomme-les-prelevements-declares.md) §5)
   vaut pour l'étape entière. Six poules de niveau dans **une** étape disputent six espaces distincts
   (1-6, 7-12, …) ; sans décalage par groupe, le classement de phase se re-rangerait par blocs et
   annoncerait le vainqueur de la poule F — composée des 31ᵉ-36ᵉ — « 1ᵉʳ-6ᵉ du tournoi ». Un
   classement bien formé, plausible, et faux : la classe de défaut qu'[ADR-0081](../docs/adr/0081-une-phase-attend-que-sa-source-ait-departage-les-places-qu-elle-preleve.md)
   nomme.

- **CA — une étape « poules de niveau » se déplie en groupes** : l'organisateur déclare une seule
  étape, sa taille de poule et sa source ; l'outil en dérive les groupes **par tranches de rangs
  contiguës**, un groupe par tranche, au lieu du serpent.
- **CA — le mode de composition est un réglage, pas un type de phase neuf** : `ReglageDePoules` gagne
  le choix « serpent » (défaut, comportement d'aujourd'hui) ou « par niveau ». Un format de tournoi
  est de la **configuration** (règle 2) ; `TypePhase.POULES` ne se dédouble pas.
- **CA — chaque groupe dispute son propre espace de rangs**, et le classement de l'étape le respecte :
  le vainqueur du groupe des 31ᵉ-36ᵉ est **31ᵉ**, jamais 1ᵉʳ. C'est le point qui demande de porter le
  décalage **au groupe** et non à l'étape.
- **CA — l'atelier montre la répartition avant validation**, patron `RepartitionPoules` d'`E05US023` :
  « 36 archers → 6 poules de niveau : rangs 1-6, 7-12, 13-18, 19-24, 25-30, 31-36 ».
- **CA — l'organisateur est averti s'il compose une 2ᵉ phase de poules au serpent**, cas où le réglage
  par défaut est très probablement le mauvais. C'est le seul garde-fou du lot qui vaut **avant** cette
  US, et il est tracé à ce titre (`DETTE-062`).
- **Dépend de** : `E05US026` (le palmarès d'une phase terminale de poules — sans lui la cascade
  s'arrête sans classement final publiable) · **Jalon** : J3 · **Origine** : cadrage d'`E05US026`,
  15/08/2026

---

### E05US030 — Le système suisse à l'écran
*En tant qu'*organisateur *et* scoreur, *je veux* régler, suivre et saisir un système suisse depuis
l'application, *afin de* faire jouer le format que le backend sait dérouler depuis `E05US026`.

Origine : **arbitrage du commanditaire du 15/08/2026, en cours d'`E05US026`**. Le périmètre de
celle-ci avait triplé au cadrage (le suisse, plus le routage des poules, plus le palmarès, plus le
remède structurel du port de classement) ; la coupe backend / front a été choisie parce que c'est la
seule qui ne coûte rien — les commits du backend sont cohérents et relisibles indépendamment, et le
front n'a aucune dette à reprendre puisqu'il n'a pas commencé.

⚠️ **C'est cette US-ci qui porte les livrables de suivi du *système suisse***, faute d'écran à
recetter avant elle : le scénario de recette du suisse dans
[`docs/fonctionnel/`](../docs/fonctionnel/). ⚠️ **Correction apportée en revue d'`E05US026`** : cette
phrase disait d'abord que `E05US026` n'avait « aucune surface utilisateur » et lui retirait *tous*
les livrables — c'était faux d'un cran. Elle a bien livré son fichier daté, son résumé **et** un
scénario restreint à ses deux effets visibles (routage et palmarès des poules). Ne reste ici que ce
qui n'existait pas encore : les écrans du suisse.

- **CA — la fiche de réglages** : choisir « système suisse » ouvre le champ **nombre de rondes**,
  avec le **maximum que l'effectif du jour autorise affiché en clair** — la borne existe au domaine
  (`rondes_maximales`, vérifiée par `EtapeDeroule`), il reste à la montrer plutôt qu'à la faire
  découvrir par un refus. Patron `ReglageBigShootOffTsx` / `ReglagePoules`.
- **CA — l'écran de saisie, ronde par ronde** : le scoreur entre par la **ronde**, pas par un numéro
  de match d'arbre — c'est le décor `RONDES_APPARIEES` du contrat (ADR-0083 §1, 2ᵉ question). Le
  **pavé** de saisie est celui d'un duel ordinaire, réutilisé tel quel : une rencontre de suisse
  *est* un duel (ADR-0083 §7), comme une rencontre de poule.
- **CA — la ronde suivante n'apparaît qu'une fois la précédente close**, et l'écran le dit : le
  moteur refuse d'apparier sur une ronde partiellement saisie (`_rondes_closes`), donc l'écran doit
  nommer l'attente au lieu de laisser un bouton inerte.
- **CA — le suivi du déroulé et l'écran de salle montrent le suisse** : catalogue de vues d'ADR-0064,
  au même titre que les poules et le Big Shoot Off. ✅ **Tenu au niveau où ses deux jumeaux le sont,
  et sans une ligne de code** *(vérifié en revue)* : le suivi du déroulé et l'écran de salle sont
  **génériques** — ils rendent un bloc par son libellé de type et les affectations par le panneau de
  routage, qui bifurque déjà sur le suisse. ⚠️ **Ce que « au même titre » ne veut pas dire** : il
  n'existe **aucune** vue détaillée par format dans le catalogue — ni pour les poules, ni pour le Big
  Shoot Off, ni ici. Ce manque est commun aux trois, et il part en `E05US031` ; il ne faut pas lire
  cette puce comme si la vue publique du suisse avait été livrée.
- **CA — le bandeau d'écart de l'atelier cesse de viser le suisse côté front** (`TYPES_SIGNALES_EN_ECART`
  du catalogue TS — la puce disait `TYPES_DEROULES`, constante qui n'existe pas côté front ; corrigé en revue), miroir de ce que `E05US026` a fait côté registre de contrat.
- **CA — l'issue de routage `EN_ATTENTE`** *(reversé ici en revue d'`E05US026`, règle 9)*. Le
  panneau doit distinguer « il a fini » de « il n'a rien à tirer **pour l'instant** » — le porteur
  d'un bye, ou l'archer dont la rencontre vient d'être validée pendant que la ronde s'achève.
  `E05US026` a **emprunté `INDISPONIBLE`** avec un motif explicite, faute de pouvoir toucher au
  contrat d'API depuis une US backend seule : `IssueRoutage` est une union que le front tient dans
  `features/routage/api.ts`. Cette US-ci livre l'issue propre, des deux côtés. *(Sans cette puce, le
  report ne vivait que dans une docstring de `application/routage.py` — invisible au cadrage.)*
- **CA — le classement provisoire se lit entre les rondes** *(ajouté au cadrage du 16/08/2026)*. Le
  suisse n'a pas d'arbre : à mi-parcours, seul le classement dit où en est chacun, et c'est lui qui
  détermine les appariements de la ronde suivante. Le backend le rend **déjà** dans la réponse d'état
  (`EtatSuisseReponse.classement`, `EtatSuissePubliqueReponse.classement` — `rang` en convention
  « 1224 », `points` en demi-points doublés, `buchholz`, `ex_aequo`) : il n'y a qu'à l'afficher, côté
  organisateur et scoreur. La lecture **publique** de ce même classement part en `E05US031`.
  ⚠️ **Le volet organisateur a failli être oublié** (rattrapé en revue) : le tableau n'était rendu
  que par l'écran de saisie, alors que l'écran des phases lisait déjà l'état pour son bouton de plan
  et n'en affichait rien. Les deux surfaces partagent désormais le même composant.
- **CA — `DETTE-056` se résorbe ici** *(tranché au cadrage du 16/08/2026)*. Elle passerait sinon à
  **quatre** sélecteurs de créneau indépendants dans l'espace scoreur. Le choix de créneau remonte
  dans un état **partagé** par les quatre panneaux ; les trois marqueurs `# DETTE-056` disparaissent
  et la ligne se ferme au registre. Motif du choix : c'est la **4ᵉ occurrence** — le seuil « attendre
  le 3ᵉ cas » du § *Dette* est dépassé — et le défaut n'est pas cosmétique, il fait scorer le mauvais
  départ avec des identifiants valides, donc **sans erreur visible**.
- **Dépend de** : `E05US026` · **Jalon** : J3 · **Origine** : arbitrage du 15/08/2026

> **Cadrage du 16/08/2026 — le lot demandé a été découpé en trois tranches.** Le commanditaire a
> demandé, en plus du CA ci-dessus, le **classement provisoire entre rondes**, une **vue publique du
> suisse** et un **pilotage explicite des rondes**, en autorisant le découpage si le lot était trop
> gros. Il l'était, et deux des trois ajouts se sont révélés d'une autre nature que « du front » :
>
> - Le **classement provisoire** est resté ici : le backend le rend déjà, c'est de l'affichage.
> - La **vue publique** n'est pas un manque du suisse mais des **trois formats non-tableau** :
>   `features/tableaux/` ne sait rendre qu'un arbre de duels, et ni les poules ni le Big Shoot Off
>   n'ont de vue publique aujourd'hui. La livrer pour le seul suisse créerait une occurrence isolée
>   d'un geste qui en réclame trois → `E05US031`.
> - Le **pilotage explicite des rondes** demande de rouvrir un **choix de conception du backend**,
>   assumé et documenté (`backend/api/v1/suisse.py`, en-tête) : il n'existe aucune route « ronde
>   suivante », la ronde N+1 **se déduit à la lecture** dès que la dernière rencontre de la ronde N
>   est validée. Un geste organisateur explicite suppose une clôture de ronde au contrat → `E05US032`.

---

### E05US031 — Le public voit les formats sans arbre

*En tant que* spectateur, *je veux* suivre à l'écran une **poule**, un **système suisse** ou un **Big
Shoot Off** comme je suis déjà un tableau de duels, *afin de* ne pas perdre de vue les archers que je
suis dès que le tournoi quitte l'élimination directe.

Origine : **cadrage d'`E05US030`, le 16/08/2026**. La demande initiale était « une vue publique du
suisse » ; l'exploration a montré que le manque est **commun aux trois formats sans arbre**, livrés
successivement par `E05US023` (poules), `E05US028` (Big Shoot Off) et `E05US026` (suisse) sans qu'un
seul d'entre eux n'atteigne jamais l'application publique. Faire le suisse seul figerait une
troisième variante locale au lieu de combler le trou.

- **CA — l'onglet public rend les phases sans arbre**, au même titre que les tableaux : les
  rencontres de la ronde ou du groupe en cours, avec leur cible, et le classement du format. Le
  catalogue de vues d'[ADR-0064](../docs/adr/0064-un-catalogue-de-vues-pour-l-ecran-de-salle.md) est
  aujourd'hui restreint à l'**arbre de duels** (`TableauPublic` : `duels`, `nb_tours`, `plage`,
  `podium`) — c'est cette restriction qui est levée.
- **CA — « mes archers » gouverne cette vue comme les autres** : l'interrupteur unique
  d'[ADR-0079](../docs/adr/0079-un-seul-interrupteur-mes-archers-pour-tout-l-onglet-public.md) vaut
  ici sans exception, et la vue nomme « aucun de vos archers ici » distinctement de son propre vide.
- **CA — l'écran de salle sait projeter ces formats**, puisqu'il puise au même catalogue de vues.
- **CA — le classement d'un suisse en cours est public** : c'est la part publique du classement
  provisoire livré côté organisateur par `E05US030`. Le backend l'expose déjà
  (`GET /api/v1/suisse/etat/{tournoi_id}/{phase_id}`, publique et anonyme).
- **CA — l'onglet s'appelle « En cours » et remplace « Tableaux »** *(arbitrage du cadrage,
  18/08/2026)*. **Un seul** onglet, pas un par format : le spectateur n'a pas à savoir quel format le
  club a choisi. Le libellé a été tranché en trois temps — « Tableaux » élargi serait **faux**
  (`Tableau` = « arbre de matchs à élimination » au glossaire, règle 3) ; « Phases » serait **exact**
  mais demande au spectateur un vocabulaire qu'il n'a pas ; « En cours » ne nomme aucun format et
  reste vrai quand un dixième type arrivera.
- **CA — l'onglet remonte le déroulé du départ** *(ajouté au cadrage, 18/08/2026)*. Il **atterrit**
  sur la phase en cours, et les phases précédentes du départ sont accessibles d'un geste. À
  l'intérieur d'une phase, la profondeur d'historique suit la **forme du format** : une poule montre
  tous ses tours, un Big Shoot Off toutes ses manches jouées, un système suisse atterrit sur la ronde
  courante avec un retour aux rondes closes.
- ✅ **ADR requis, et écrit** : [ADR-0089](../docs/adr/0089-le-catalogue-de-vues-porte-des-phases-pas-des-arbres.md),
  qui **révise** ADR-0064. Le renommage de `VueEcran.TABLEAUX` en `EN_COURS` **coûte une migration**
  (`0047`) : persister la chaîne rendait un *ajout* gratuit, pas un *renommage*.
- ✅ **Vérification faite au cadrage, et elle donne du backend à cette US.** Les **poules**
  (`/poules/etat/…`) et le **suisse** (`/suisse/etat/…`) ont déjà leur route anonyme avec DTO public
  dédié. Le **Big Shoot Off n'en a aucune** : son `/etat/` était `exiger_scoreur` et sa
  `/projection/` est `exiger_admin`. L'US porte donc un DTO public neuf et ouvre `/etat/`, la lecture
  du scoreur migrant sur `/saisie/` — le couple exact de ses deux jumeaux.
  ⚠️ **La justification de l'ancienne restriction était fausse** : l'en-tête du routeur invoquait
  « les scores manche par manche, que le public n'a pas à voir avant validation », or
  `_scores_par_manche` ne rend **que** les manches entièrement validées. Ce qui distingue réellement
  les deux formes est l'**adressage de saisie** (`prochaine_volee`, `volees`).
- **Dépend de** : `E05US030` · **Jalon** : J3 · **Origine** : cadrage d'`E05US030`, 16/08/2026 ·
  **Périmètre arrêté** : cadrage du 18/08/2026

---

### E05US032 — Une phase avance par tours

*En tant qu'*organisateur, *je veux* que l'application sache où en est **chaque** phase — pas
seulement celles en tableau —, *afin de* lire d'un coup d'œil ce qui se joue en salle quel que soit
le format.

Origine : **cadrage du 18/08/2026**, qui a **recadré** cette US et l'a coupée en deux. Le
commanditaire a demandé pourquoi le projet emploie **quatre mots** — tour, ronde, manche, volée —
pour ce qui lui semblait un seul concept, et s'il y avait une raison ou un angle mort. La réponse
est qu'il **a raison** : la pluralité des mots est légitime **à l'écran** (c'est le vocabulaire de
la salle, règle 3, et le glossaire assume déjà l'homonymie « manche » duel / Big Shoot Off), mais
elle ne recouvre **aucun concept commun dans le code**. Chaque format a inventé sa progression dans
son coin — `Match.tour`, `RondeAffichee`, les manches du Big Shoot Off, les tours de poule —, et
`domain/suivi_deroule.py` le constate sans le nommer : « une phase sans braquet rend un bloc à zéro
tour », avec un marqueur `# DETTE-028`. Cinq occurrences : le seuil du § *Dette* pour un remède
structurel est largement franchi.

⚠️ **Le CA précédent de cette US est révoqué**, et il faut le lire pour comprendre la suite. Il
disait : « la ronde suivante ne s'ouvre **que** sur décision de l'organisateur ». Le commanditaire a
tranché **l'inverse** le 18/08/2026 : l'enchaînement **automatique reste le défaut**, et l'arrêt
devient une décision **programmée** — c'est `E05US033`. Cette US-ci ne livre aucun pilotage : elle
pose le concept dont il aura besoin, et qui manque de toute façon au suivi.

- **CA — toute phase compte des tours, quel que soit son format.** Le tour est un **numéro** (1..N)
  qui dit où en est la phase. Aucun type n'en est exclu — ni la qualification, ni l'échauffement.
- **CA — un tour est une unité d'*avancement*, jamais de *classement*** *(invariant posé par le
  commanditaire au cadrage)*. Certaines phases classent **au fil des tours** (l'élimination directe :
  chaque tour attribue une tranche de rangs, le *braquet*, Règle R) ; d'autres ne classent **qu'à la
  fin** (la qualification : le total, pas la volée 12). Les deux notions doivent rester séparées dans
  le modèle. C'est précisément ce que le code confond aujourd'hui — `AvancementTour` **dérive** les
  tours des braquets, d'où la phase sans braquet qui affiche zéro tour.
- **CA — le nombre de tours est dérivé quand la structure le détermine, et vaut 1 sinon.** Dérivé :
  élimination directe (braquets), poules (round-robin), suisse et colline (rondes réglées), Big Shoot
  Off (manches). **1 tour** : qualification et échauffement — rien dans « 20 volées » ne dit s'il y a
  un ou quatre tours, c'est un **choix** de l'organisateur, et ce réglage est reporté à `E05US033`,
  là où il sert. « 1 tour » est **vrai**, pas un trou : la phase entière est un tour.
- **CA — le libellé affiché est le mot du métier, résolu par le type de phase.** « Demi-finale »
  (tableau), « Tour 3 » (poules), « Ronde 3 » (suisse, colline), « Manche 2 » (Big Shoot Off). Une
  phase à **un seul** tour n'annonce pas de numéro : il n'y a rien à distinguer.
  ⚠️ **Ne pas ouvrir un troisième domicile au libellé de tour** : [DETTE-020](../docs/dette.md) en
  compte déjà deux (`domain/tableau.py` et le front `saisie-duels/duel.ts`), et `E07US005` a failli
  en ouvrir un troisième avant de le refermer en **servant** le libellé du domaine au DTO. La
  résolution générique doit **absorber** l'existante, pas s'ajouter à côté.
- **CA — le suivi du déroulé montre le tour en cours de *chaque* phase démarrée**, plus seulement
  des phases en tableau. C'est la surface visible de l'US.
- ⚠️ **ADR requis** : le tour comme unité d'avancement générique, et sa séparation d'avec le braquet.
  Complète [ADR-0083](../docs/adr/0083-le-contrat-de-phase-jouable.md) — le contrat de phase est
  l'endroit où chaque format répond aux questions « comment on me joue », et « en combien de tours,
  sous quel nom » en est une.
- ✅ **Arbitrages rendus en revue, le 19/08/2026** *(reversés ici dans le même commit, règle 9)* :
  - **le CA fait foi sur la portée** — le tour s'affiche pour **chaque** phase démarrée et sur les
    **deux** écrans (pilotage et salle). La divergence relevée par l'axe C1 est tranchée en faveur
    de `stories/` : le libellé descend dans le composant partagé `SchemaBraquets`, et non dans la
    seule phrase d'en-tête du suivi — c'est le composant que monte l'écran de salle, la surface que
    l'US invoque. `docs/fonctionnel/` a été aligné, qui rétrécissait à « seule la phrase d'état
    change » ;
  - **une phase à un seul tour n'annonce rien**, y compris en poules, en suisse et en Big Shoot Off
    — le code ne l'appliquait qu'à la qualification et à l'échauffement. Le tableau garde son
    exception : son tour unique s'appelle « Finale », qui est un **nom**, pas un numéro.
- **Dépend de** : rien · **Jalon** : J3 · **Origine** : cadrage du 18/08/2026 (recadrage de l'US
  « L'organisateur ouvre la ronde suivante », dont la seconde moitié devient `E05US033`)

---

### E05US033 — L'organisateur programme les pauses du déroulé

*En tant qu'*organisateur, *je veux* prévoir à l'atelier les moments où la salle s'arrête, *afin de*
garder la main sur une phase qui dure plusieurs heures au lieu de la voir enchaîner toute seule
jusqu'au bout.

Origine : **cadrage du 18/08/2026**, seconde moitié de l'ancienne `E05US032`. Le besoin énoncé n'est
pas « déclencher chaque tour à la main » mais « **pouvoir couper** » : une phase longue doit pouvoir
s'interrompre pour le repas, une réorganisation de salle, une annonce.

⚠️ **Périmètre réduit au cadrage du 19/08/2026 : cette US est la tranche A d'un découpage en deux.**
La fiche portait **13 CA** traversant modèle persisté, migration, moteur d'avancement, routes admin,
atelier, pilotage, tableau de bord et écran public — trop pour une branche (maille INVEST,
§ Workflow). Le commanditaire a arbitré la coupe. Cette tranche livre **le mécanisme** : *la salle
peut s'arrêter et se relancer*. La tranche B (`E05US034`) livre **la lisibilité** : *personne ne
reste dans le noir*. Aucun CA n'a été supprimé — chacun est reversé dans l'une des deux fiches, et le
compte se vérifie **puce par puce** : 10 ici, 5 là, 15 pour 13 d'origine — les deux de plus sont
deux notes « piège à vérifier » promues en CA. Ce recomptage n'est pas un ornement : c'est la leçon
qu'`E05US032` a laissée derrière elle en effaçant deux CA sans trace (cf. `E05US034`).

- **CA — l'enchaînement automatique reste le défaut.** Une phase sans arrêt programmé se comporte
  **exactement** comme aujourd'hui. C'est ce qui rend la livraison sûre : aucune phase en cours le
  jour du déploiement ne change de comportement.
- **CA — les arrêts se programment à l'atelier**, à la création du déroulé, sur une phase, après un
  tour donné. **Plusieurs par phase** : c'est une liste, pas un arrêt unique — l'organisateur prépare
  son planning de journée à l'avance (« pause après le tour 2, pause après le tour 5 »).
- **CA — un arrêt porte une portée** : **cette phase seule**, ou **toutes les phases du même
  départ**. Le départ est la portée sportive du projet ([ADR-0075](../docs/adr/0075-le-depart-est-la-portee-sportive.md))
  et correspond à « ce qui tire en salle en ce moment ». Le statut du **tournoi** n'est pas touché :
  il a déjà sa propre pause, à une autre maille (ADR-0026 §3).
- **CA — un arrêt de portée « départ » laisse chaque phase finir son tour en cours.** Il n'est donc
  **pas simultané** : si l'arrêt tombe à la fin du tour 3 des poules, la qualification finit ses
  volées en cours et le duel engagé va à son terme. Personne n'est coupé en plein tir ; la salle
  s'éteint en quelques minutes, pas d'un coup. *(Arbitrage du commanditaire, 18/08/2026.)*
- **CA — un arrêt atteint met la phase en pause toute seule**, sur le statut **existant**
  `StatutPhase.EN_PAUSE` ([ADR-0045](../docs/adr/0045-sequence-de-phases-cycle-de-vie-typage-source.md) §1).
  On n'invente pas une notion parallèle d'« arrêtée » à côté du cycle de vie : c'est le déclencheur
  qui est neuf, pas l'état.
- **CA — la reprise est un geste manuel d'un admin**, et un arrêt de portée « départ » se relance
  **d'un seul geste** pour toutes les phases qu'il a arrêtées. Quatre boutons pour un seul arrêt
  créerait exactement le piège qu'on cherche à éviter — en oublier une.
- **CA — après reprise, la phase repart en automatique jusqu'au prochain arrêt.** Le pilotage tour
  par tour reste donc possible sans second mode : il suffit de programmer un arrêt à chaque tour.
- **CA — une correction de score reste possible pendant la pause.** `EN_PAUSE` gèle la **validation**
  d'une rencontre nouvelle ; il ne doit pas geler la **rectification** d'un score déjà saisi, sinon
  la pause devient un cul-de-sac en salle — précisément le moment où l'on découvre les erreurs.
  *(Était une note « piège à vérifier » ; promue en CA, parce qu'un piège vérifié sans oracle ne
  laisse aucune trace exécutable.)*
- **CA — pendant la pause, le routage dit « en attente » à l'archer.** L'issue `EN_ATTENTE` existe
  depuis `E05US030` : elle se réutilise plutôt que de s'inventer. *(Même promotion : c'était une
  note.)*
- **CA — la qualification devient divisible en tours** (« 20 volées en 2 tours de 10 »), réglage
  reporté d'`E05US032` — sans lui, elle n'a qu'un tour et ne peut donc pas s'arrêter en cours de
  route.
  ⚠️ **CA amputé à la revue du 19/08/2026 : l'échauffement en est retiré, faute de matière.** Le CA
  d'origine nommait « la qualification **et** l'échauffement ». Or son contrat de phase le déclare
  sans décor de saisie ni plan de cibles : il n'a **ni barème ni feuille de marque**, donc il n'existe
  *rien* dont dériver un tour, et aucun lecteur d'avancement ne peut exister pour lui. Un découpage y
  aurait été accepté à l'atelier et définitivement inerte le jour J. Ce n'est pas un manque
  d'implémentation mais une **absence de donnée** — d'où le retrait plutôt qu'un report. Le besoin
  repart en `E05US034` s'il se confirme : il faudra alors décider de quoi un échauffement tire son
  avancement (une horloge ? un geste d'organisateur ?), ce qui est un choix métier, pas de la
  plomberie. *(Le **barrage** est exclu pour une autre raison, purement technique : son contrat vaut
  aussi `PHASE_ENTIERE`, si bien que la garde écrite sur le contrat le laissait passer.)*
  ⚠️ **Le réglage avait été livré INERTE**, et c'est le bloquant central relevé par les cinq axes de
  revue : rien ne le lisait. Il est désormais branché — `ServiceSaisie` réalise le port d'avancement
  pour la qualification, le tour se dérivant des volées **validées** de l'archer le **moins** avancé
  (une phase avance au rythme du dernier, pas du premier). Cf.
  [ADR-0091](../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md) §8.
- ⚠️ **ADR requis** : portée et sémantique de l'arrêt programmé (ce qu'il gèle, ce qu'il laisse
  finir, ce que « toutes les phases » recouvre, et où s'insère le déclencheur dans le contrat de
  phase d'ADR-0083).
- ⚠️ **Angle mort assumé de la tranche A livrée seule** : l'organisateur peut arrêter la salle, mais
  ni le public ni l'écran de salle ne **disent** que c'est une pause, et rien ne lui rappelle qu'une
  phase attend sa relance. C'est tolérable parce qu'il vient lui-même de programmer l'arrêt et se
  tient devant le pilotage — ce n'est **pas** tolérable le jour J. `E05US034` doit donc être livrée
  **avant tout déploiement réel** de cette capacité. À ne pas laisser filer dans la file.
- 🔭 **Évolution prévue, hors périmètre : le planning horaire de journée** (« pause repas
  12h–13h30 », l'application calculant quel tour tombe avant). Le commanditaire l'annonce comme
  besoin **futur** — le besoin d'aujourd'hui s'arrête à « après le tour n ». **On ne généralise donc
  pas le déclencheur maintenant** : un déclencheur polymorphe posé sur une évolution *supposée* est
  exactement ce que le § *Dette* interdit (remède structurel sur preuve dans le code du jour, 3ᵉ
  occurrence réelle — ici il y en a **une**). L'ADR de cette US **nomme** l'évolution pour que le
  jour où elle arrive, on sache que le point d'extension attendu est le **déclencheur**, et non la
  portée ni l'effet.
- **Dépend de** : `E05US032` · **Jalon** : J3 · **Origine** : cadrage du 18/08/2026 ·
  **Périmètre arrêté** : cadrage du 19/08/2026

---

### E05US034 — La pause se voit, et se pose en cours de journée

*En tant qu'*organisateur *et* spectateur, *je veux* que l'arrêt de la salle soit **annoncé** et que
je puisse en poser un sans avoir tout prévu à l'atelier, *afin de* ne jamais laisser croire à une
panne ni oublier une phase en attente.

Origine : **cadrage du 19/08/2026**, tranche B du découpage d'`E05US033`. Elle ne rouvre pas le
mécanisme : elle le rend **lisible** et **ajustable le jour J**.

- **CA — le jour J, l'organisateur pose un arrêt relatif** depuis le pilotage : « bloquer dans
  x tours ». Il s'ajoute aux arrêts programmés, il ne les remplace pas.
- **CA — l'application rappelle qu'une phase attend sa relance.** Pastille au tableau de bord
  (« 2 phases attendent votre relance depuis 14 min »). Sans ce filet, la capacité livrée en
  `E05US033` crée un **mode de panne neuf** : la salle attend, personne ne sait pourquoi, et rien
  n'a l'air anormal.
- **CA — la pause se voit du public et de l'écran de salle.** Sans mention explicite, un spectateur
  lira l'arrêt comme une panne.
- **CA — un refus dit ce qui manque** *(CA **récupéré** de l'ancienne `E05US032`)* : quelles
  rencontres ne sont pas validées, et lesquelles ne sont pas encore saisies. Le refus muet actuel
  (`ConfigurationSuisseInvalide`) n'est pas un message d'écran.
- **CA — l'état d'un tour devient lisible en tant que tel** *(CA **récupéré** de l'ancienne
  `E05US032`)*, et non déduit du compte de résultats.
  ⚠️ **Ce CA est partiellement rouvert par `E05US032`, qui a tranché dans l'autre sens sans le
  dire** : `ServiceSuisse.avancement_de_phase` *dérive* précisément l'état de ronde du compte de
  résultats relu, et l'ADR-0090 a conservé la **dérivation à la lecture** — c'est une décision, pas
  un non-choix. Reste donc à trancher ici, sur preuve d'usage : ce que le pilotage exige de plus
  qu'un numéro de tour lisible (une clôture persistée ? un simple message circonstancié ?).
- ⚠️ **Ces deux derniers CA avaient disparu sans trace au recadrage du 18/08/2026** — le bloc
  supprimé en portait **trois**, et un seul (« la ronde suivante ne s'ouvre que sur décision de
  l'organisateur ») a été explicitement révoqué. Rattrapé par l'axe adversarial de `/revue-us`.
  C'est pire qu'un CA périmé, que la règle 9 sait détecter : un CA **effacé** ne s'écrit pas de
  travers, il ne s'écrit plus du tout. Leçon à retenir pour tout recadrage : **compter les puces
  avant et après**.
- 🔭 **Hérité de l'amputation d'`E05US033`** : si le commanditaire veut qu'un **échauffement** puisse
  porter une pause, il faut d'abord décider de quoi il tire son avancement — il n'a ni barème ni
  feuille de marque, donc aucune donnée existante ne dit où il en est. Choix métier à trancher, pas
  un reste de plomberie.
- ⚠️ **Bloquante avant déploiement réel des pauses** — cf. l'angle mort assumé d'`E05US033`. Ne pas
  la laisser dériver dans la file sous prétexte qu'elle « n'ajoute que de l'affichage » : c'est le
  filet de sécurité de la capacité précédente.
- **Dépend de** : `E05US033` · **Jalon** : J3 · **Origine** : cadrage du 19/08/2026 (tranche B du
  découpage d'`E05US033`)
