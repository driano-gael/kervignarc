# ADR-0049 — Saisie et scoring des duels : agrégat `Duel`, barème résolu par (phase, arme), barrage dans l'agrégat, résultats persistés / tableau reconstruit

- **Statut** : Accepté
- **Date** : 2026-07-27
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E04-saisie-scores.md`](../../stories/E04-saisie-scores.md) (E04US013 — dépendance
  E01US011 **corrigée**, arbitrages reversés) ; [`docs/glossaire.md`](../glossaire.md)
  (`duel`, `set`/`manche`, `point de set`, `barrage`/`shoot-off`, `barème de duel`)
- **Introduit par** : E04US013 (saisie en duels — système de sets, vainqueur, barrage).
- **S'appuie sur** : [ADR-0004](0004-politiques-de-tableau-injectables.md) /
  [ADR-0046](0046-config-policies-politiques-nommees-parametrees.md) (politiques `scoring`/`tiebreak`
  injectables, ressignature assumée « un implémenteur, aucun consommateur ») · [ADR-0028](0028-participant-abstraction-du-competiteur.md)
  (le moteur oppose des `Participant`) · [ADR-0023](0023-moteur-de-placement-glouton-deterministe.md)
  /[ADR-0048](0048-cote-a-cote-des-duellistes-par-reordonnancement.md) (le tableau est **recalculé**,
  jamais persisté ; seul le tir/la pose se matérialise).

## Contexte et problème

E04US013 veut « saisir un duel au système de sets, en désigner le vainqueur et résoudre les égalités,
afin de faire progresser le tableau ». L'exploration établit l'état des lieux :

- Le **moteur d'élimination** (E05US005, `domain/tableau.py`) est livré : `Tableau.jouer(numero,
  vainqueur)` attend un `Participant` **opaque** comme vainqueur et propage au tour suivant. Il ne
  connaît **rien** aux sets — la désignation du vainqueur est **hors moteur**, à la charge de cette US.
- L'agrégat de saisie **`Serie`/`Volee`** (E04US002) porte des volées de `ZoneScore`, mais `Serie`
  est un agrégat **au cumul d'un seul archer** : ni set, ni point de set, ni opposition. Il n'est pas
  un agrégat de duel.
- Les **politiques injectables** (E05US003, `domain/politiques.py`) posent les protocoles `Scoring` et
  `Tiebreak` avec, en toutes lettres, l'anticipation qu'E04US013 « ressignera » le scoring pour les
  sets — latitude explicite (« rupture bon marché tant qu'il n'y a qu'un implémenteur et aucun
  consommateur par famille »).
- Le **tableau n'est pas persisté** (ADR-0023/0048) : il se **reconstruit** du classement via
  `construire_tableau`. `ServicePlacementDuels` le fait déjà pour placer les duellistes du 1er tour.

Quatre questions qu'aucun CA ne tranche :

1. **Où vit le scoring d'un duel** (sets, points de set, barrage), puisque `Serie` ne convient pas ?
2. **Comment résoudre le barème** — les sets FFTA (1er à 6) pour classique/arc nu, le **cumul** pour
   l'arc à poulies (A.7.5.2) — sans E01US011 (presets configurables), qui est **bloquée** sur le Big
   Shoot Off (règle inconnue du club) et vit en J4 ?
3. **Où traiter le barrage** (§8.2 : 1 flèche, plus haut score, puis plus près du centre) — dans la
   politique `tiebreak` d'ADR-0004, ou ailleurs ?
4. **Comment « faire progresser le tableau »** alors qu'il n'est pas persisté ?

## Décision

### 1. Un agrégat de domaine **`Duel`** distinct, réutilisant `Volee`/`ZoneScore`

Le scoring d'un duel est un **nouvel agrégat pur** `domain/duel.py`, pas une extension de `Serie` :

- `MancheDuel(numero, volee_haut: Volee, volee_bas: Volee)` — une manche (un « set ») oppose deux
  volées ; on **réutilise** `Volee`/`ZoneScore` (`.points`) sans les dupliquer.
- `Duel(bareme, participant_haut, participant_bas, manches, barrage)` — racine d'agrégat immuable
  (comme `Serie`/`Tableau`) : `saisir_manche(...)`, `saisir_barrage(...)` renvoient un **nouveau**
  `Duel`. La **configuration** (barème, zones admises du blason) est **passée aux opérations** par le
  service, jamais dupliquée dans l'agrégat — patron d'ADR-0027/`Serie`.
- Le **résultat** (`ResultatDuel` : points de chaque camp, `vainqueur: Cote | None`, `termine`,
  `barrage_requis`) est **calculé par l'agrégat**. Le barème du système de sets (2 points au vainqueur
  de la manche, 1-1 à égalité, 0 au perdant ; premier à `points_pour_gagner`) est un **invariant du
  format**, pas une stratégie que l'on brancherait : on le tient dans l'agrégat, paramétré par le
  `BaremeDuel`.

> Pourquoi pas `Serie` ? `Serie.cumul` somme les points d'**un** archer ; un duel compare **deux**
> volées manche par manche et s'arrête dès qu'un camp atteint 6. La structure est différente ;
> mutualiser `Volee` suffit — mutualiser la racine coûterait des `if mode` partout.

### 2. Le barème de duel est un **value object** `BaremeDuel`, résolu par **(phase, arme)** via un résolveur **injecté** (défaut FFTA)

`BaremeDuel(mode: ModeDuel, nb_manches, nb_fleches_par_volee, points_pour_gagner)` — jumeau de
`BaremeQualification` (une **structure** paramétrée, pas un choix dans un catalogue fermé) :

- `ModeDuel.SETS` (classique / arc nu, §7) : `nb_manches=5`, `points_pour_gagner=6` (FFTA) ;
- `ModeDuel.CUMUL` (arc à poulies, A.7.5.2) : 5 volées de 3, **plus haut cumul**, sans sets.
- Presets : `preset_ffta_classique()`, `preset_ffta_poulies()`, `preset_club()` (1er à **4 pts**).

La **résolution par (phase, arme)** (référentiel §10, `config.policies.scoring_par_arme`) passe par un
**résolveur injecté** `ResolveurBaremeDuel` (`bareme_pour(arme) -> BaremeDuel`), dont le défaut
`ResolveurBaremeDuelFfta` renvoie le preset poulies pour une arme « poulies/compound », le preset
classique sinon. **C'est le point d'injection d'ADR-0004** (règle 2) : E01US011 y branchera plus tard
les **catalogues configurables** (FFTA/club, surcharge par arme) **sans toucher** l'agrégat ni le
service.

**La dépendance E04US013 → E01US011 déclarée dans la story est sur-affirmée** (même classe d'erreur
que la « dépendance ADR-0005 » et le cycle E04US016 déjà corrigés dans cette même story) : le
**mécanisme** de scoring n'a besoin que d'une **politique injectée à défaut FFTA**, pas du catalogue
configurable. La story est corrigée : E04US013 **ne dépend plus** d'E01US011 ; E01US011 **configurera**
ce que cette US **livre déjà** en dur FFTA. Décision produit du 27/07/2026 (cadrage d'intention).

### 3. Le **barrage** (shoot-off) est traité **dans l'agrégat**, **pas** par la politique `tiebreak`

Le CA dit « politique `tiebreak` (ADR-0004) ». Mais l'interface `Tiebreak.departager(a:
DecompteDepartage, b: DecompteDepartage) -> int` compare des **décomptes de 10 et de 9** — c'est le
**départage du classement de qualification** (§8.1). Le **barrage de duel** (§8.2) est structurellement
autre : **1 flèche**, plus haut score, et **si l'égalité persiste, plus près du centre** — un jugement
que **l'application ne peut pas mesurer** (elle ne connaît pas la distance au centre). Forcer l'un dans
l'autre trahirait les deux.

Décision (arbitrage règle 9, reversé dans la story) : le barrage vit **dans l'agrégat `Duel`**
(`Barrage(fleche_haut, fleche_bas, gagnant_designe: Cote | None)`) : le vainqueur est le plus haut
score ; **à égalité de flèche**, le scoreur **désigne** le gagnant (le plus près du centre, jugé à
l'œil / à l'arbitrage — §8.2), via `gagnant_designe`. La politique `tiebreak` d'ADR-0004 **reste**
réservée au **classement** (E06US003 en fera l'autre implémentation, comme sa docstring l'annonce) :
E04US013 ne la consomme pas. Le barrage ne recompte pas les 10/9 (§8.2) — cohérent avec « c'est un
autre mécanisme que le départage de classement ».

### 4. Le vainqueur est **transmis** à `Tableau.jouer` ; on persiste le **tir**, on **reconstruit** le tableau

Fidèle à ADR-0023/0048 : le tableau **n'est pas persisté**. On persiste le **tir** de chaque match et
on **reconstruit** le tableau à la demande — `classement → construire_tableau → rejeu` des duels
**validés** dans l'ordre des tours (`Tableau.jouer(numero, vainqueur)`). C'est le **pendant** de ce que
`ServicePlacementDuels` fait déjà pour le tour 1 ; le rejeu peuple les tours ≥ 2 (occupants
`VainqueurDe`).

- **Table dédiée `duel`** (migration `0030`), **une ligne par match**, clé primaire composite
  `(phase_id, match_numero)`, `ON DELETE CASCADE` sur `phase_id` (feuille dérivée d'une phase, comme
  `placement_tableau`). Colonnes : `manches` **JSON** (la liste des sets — deux volées de `ZoneScore`
  par manche, procédé de `VoleeORM`/`BlasonORM.zones`), `barrage` **JSON** nullable (une flèche par
  camp + `gagnant_designe`), `validee_par` (le scoreur ; `NULL` = non validé). Le **barème** n'est
  **pas** stocké : il est re-résolu de l'arme à la lecture (à duellistes identiques, même arme, même
  barème). **Aucun `Match`/`Tableau` en base** : la structure de l'arbre est **dérivée** de la
  reconstruction — déterministe (ADR-0023).
- **L'identité des deux duellistes est persistée** (`haut_genre`/`haut_ref`, `bas_genre`/`bas_ref`) —
  et c'est un **correctif de fond** (revue adversariale). Ce n'est **pas** l'appariement *plan*
  (recalculé du classement, ADR-0048) : c'est le fait « **qui** a tiré ce résultat ». Sans lui, le tir
  n'était keyé que sur la **position** `match_numero`, une identité **volatile** : une correction de
  score de qualification ré-ordonne l'ensemencement, un autre couple occupe alors ce numéro, et
  `Tableau.jouer` — dont la garde `VainqueurHorsMatch` ne se déclenche pas (le vainqueur était
  re-dérivé des occupants courants) — **faisait avancer le mauvais archer en silence** (« un score faux
  et silencieux est pire qu'une erreur visible »). Désormais, à la reconstruction, si les occupants
  recalculés **divergent** des duellistes enregistrés, le tir est **ignoré** (rejeu) et toute écriture
  dessus **refusée** (`DuelDesynchronise`, 409) — jamais ré-attribué. Le **gel** du classement pendant
  la phase de tableau (garde de cycle de vie) reste downstream (E01US017/E12US002) ; l'ancrage par
  identité en fait, entre-temps, une **erreur visible** et non une corruption.
- **Pas de trace d'audit à cette US.** La validation d'un duel enregistre son **validateur**
  (`validee_par`) mais **ne consigne pas** d'`AuditLog` (pas d'atomicité acte↔trace ADR-0035) — même
  choix que le **jumeau** `ServicePlacementDuels` (aucune couture d'audit). C'est un **différé assumé**,
  additif et réversible : parité avec la validation de série (auditée, E10US005) si un besoin émerge,
  au même point (le service reçoit alors un port d'audit). Ne pas le décrire comme livré tant qu'il ne
  l'est pas.

### 5. Le grain `FIN_DE_DUEL` est **ouvert** pour `ELIMINATION_DIRECTE`

`GrainValidation` connaît déjà `FIN_DE_DUEL` (E01US015) mais `_GRAINS_ADMIS` ne l'autorisait que pour
la qualification. E04US013 l'ouvre pour `ELIMINATION_DIRECTE` : un duel se valide **d'un bloc en fin
de duel** (la feuille de marque se signe « à la fin du duel », FFTA B.6.1.1).

## Conséquences

- **+** Le scoring de duel est **pur, injectable et testable** ; le mécanisme est livré à défaut FFTA
  et E01US011 le **configurera** au même point d'injection (règle 2) — aucun sur-gel.
- **+** `Volee`/`ZoneScore` sont **mutualisés** sans coupler les racines ; le moteur reste **opaque**
  aux `Participant` (ADR-0028) et **inchangé** (E04US013 ne touche pas `tableau.py`).
- **+** Fidélité au régime de persistance d'ADR-0023/0048 : **rien de l'arbre** n'est figé, une seule
  table nouvelle (le **tir**), la progression **reconstruite**. La reconstruction suit le classement
  **courant** — un tir reste cependant **ancré** sur l'identité des duellistes qui l'ont produit, si
  bien qu'un classement modifié après coup produit une **divergence détectée** (erreur visible), jamais
  une ré-attribution silencieuse (cf. §4).
- **−** Le **Big Shoot Off** (grande finale, format club) reste **hors périmètre** : sa règle n'existe
  dans aucun document (bloque E01US011). Un duel de grande finale se score comme un duel normal en
  attendant.
- **−** La reconstruction du tableau **duplique** (2ᵉ occurrence, avec `ServicePlacementDuels`) le pont
  `classement → construire_tableau`. Assumé en l'état (règle 12) ; extraction au 3ᵉ cas. Signalé,
  non masqué (docstring).
- **−** L'arme est un **champ texte libre** de `Categorie` (pas d'énuméré) : le résolveur normalise et
  reconnaît « poulies/compound ». Fragile par nature — **centralisé** dans le résolveur (point unique
  de correction quand E01US018/E01US011 formalisera l'arme). Dans le **bracket mixte-armes** du MVP
  (un seul tableau tournoi-large, ADR-0048), le barème est résolu **par duel** depuis l'arme du camp
  **haut** ; le tableau **par catégorie/division** reste downstream (E05US010/E06US006).
- **−** **L'ancrage par identité couvre la position, pas la mutation d'arme.** La garde de divergence
  compare l'**identité** des duellistes (`{genre, ref_id}`), non leur **catégorie** ; le barème, lui,
  est re-dérivé **en direct** de la catégorie courante à chaque lecture/rejeu. Cas résiduel (edge,
  exige une action admin **en cours** de tableau, revue adversariale) : un archer dont on change la
  catégorie « classique »→« poulies » après avoir tiré ses manches verrait son tir **validé**
  réinterprété du mode **sets** au mode **cumul**, faisant potentiellement basculer le vainqueur en
  silence. **Même classe** que le re-classement de qualification : les deux sont refermés par le
  **gel du classement/état pendant la phase de tableau** (garde de cycle de vie, E01US017/E12US002).
  Assumé et documenté ici, non traité dans cette US ; le tir enregistre déjà l'identité (position
  ancrée), le mode reste tributaire du gel à venir.

## Tranche front (27/07/2026) — écran scoreur

Le backend ci-dessus a été livré **sans surface**. L'**écran tactile scoreur** (grille de saisie d'un
duel) l'a suivi en tranche front dédiée (`frontend/src/features/saisie-duels/`), monté dans l'**Espace
scoreur** : choix d'une phase de tableau, **liste des duels par tour**, grille de manches (sets/cumul),
**barrage** conditionnel avec désignation manuelle, **validation** verrouillante, **podium**. Deux
décisions techniques, tranchées et reversées ici (règle 9) :

- **Le contrat de lecture est enrichi du « pavé ».** `DuelReponse`/`EtatDuel` exposent désormais, dès
  qu'un match est **jouable** et **avant tout tir**, les **zones** du blason tiré, le **nombre de
  flèches par volée**, le **nombre de manches** et le seuil (`points_pour_gagner`) — ce que le service
  calculait déjà mais gardait pour l'écriture. Sans quoi le front ne pourrait pas bâtir un pavé fidèle
  au blason (« touches illégales absentes », principe d'E04US002). Les **zones** sont résolues
  **best-effort en lecture** (`_zones_best_effort` : vides si blason indéterminable, l'écran affiche
  « pavé indisponible » sur ce match) tandis que le chemin d'**écriture** reste **strict**
  (`BlasonIntrouvable`, 404) — même asymétrie que la grille de qualification. Le `mode` (sets/cumul)
  est lui aussi déplacé sur le **barème du match** (connu avant la 1ʳᵉ manche), non plus sur le tir.
- **Aucune autre modification backend.** La navigation du scoreur suppose de lister les phases ; or
  `GET /tournois/{id}/phases` est une lecture **déjà publique** (E10US001) — le scoreur l'appelle sans
  jeton (portée `'aucune'`), aucune route à ouvrir. Le « manque » initialement pressenti n'en était pas
  un ; vérifié avant de coder.

Côté résilience, la saisie de duel **résiste aux coupures** comme la qualif (E04US009) : une **file
hors-ligne dédiée aux actes de duel** (manche / barrage / validation) + rejeu idempotent. C'est la
**2ᵉ occurrence** du motif de résilience — **dupliquée**, pas extraite en socle générique (règle 12 ;
l'extraction en `shared/` attend un 3ᵉ cas). Divergence assumée avec la file de qualif : **FIFO strict
sans dédup à l'enfilage**, car l'ordre des actes (manches → barrage → validation) porte du sens au
rejeu (valider suppose les manches déjà passées). Le front **ne recompute jamais** l'issue d'un duel :
`termine`/`vainqueur`/`barrage_requis` restent l'autorité serveur ; hors-ligne, la grille avance en
affichant les actes « en attente » sans en déduire le résultat.
