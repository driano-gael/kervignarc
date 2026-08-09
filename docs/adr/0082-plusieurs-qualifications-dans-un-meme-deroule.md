# ADR-0082 — Plusieurs qualifications dans un même déroulé

- **Statut** : Accepté
- **Date** : 2026-08-09
- **Décideurs** : Organisateur / Architecte
- **Portée** : E05US025 (un déroulé peut enchaîner plusieurs phases de qualification)
- **Amende** : [ADR-0069](0069-effectif-minimum-deduit-et-exige.md) — qui listait « une séquence ne
  porte qu'une qualification » parmi les anomalies bloquantes. Cette règle est **retirée** ; le
  reste d'ADR-0069 est intact.
- **Lie** : [ADR-0075](0075-le-depart-est-la-portee-sportive.md) (un départ rejoue le tournoi, donc
  porte ses phases), [ADR-0076](0076-un-deroule-defini-une-fois-un-avancement-par-depart.md) (le
  déroulé se définit une fois, chaque créneau l'instancie),
  [ADR-0080](0080-un-prelevement-lit-le-classement-de-sa-phase-source.md) (un prélèvement lit le
  classement de **sa** source — sans quoi la seconde qualification recevrait tous les inscrits),
  [ADR-0068](0068-le-moteur-consomme-les-prelevements-declares.md) §5 (`rang_premier`, le décalage
  de tranche que ce déroulé rend enfin visible)
- **Source métier** : arbitrage du commanditaire du **08/08/2026** — « *pourquoi on ne peut pas,
  dans la création d'un tournoi, faire plusieurs phases de qualification ?* » —, précisé au cadrage
  du **09/08/2026** par un exemple de référence, repris tel quel ci-dessous.

## Contexte et problème

`E05US021` avait posé un invariant : **une séquence ne porte qu'une phase de qualification**
(`_anomalies_unicite_qualification`, erreur `PlusieursQualifications`). Sa propre docstring en
reconnaissait la nature :

> L'invariant était supposé partout et vérifié nulle part : neuf sites lisent « **la** »
> qualification, dont deux la résolvaient différemment.

Autrement dit, ce n'était **pas une règle du tir à l'arc** : c'était un pansement posé sur des
lecteurs incohérents. Le coût réel — un minimum d'inscrits calculé sur une phase et un prélèvement
fait dans l'autre — était bien réel, mais le remède fermait le cas au lieu de réparer les lecteurs.

Le commanditaire a demandé le cas. Il est légitime et courant : un tour de qualification général,
puis une coupe où chaque moitié rejoue.

### L'exemple de référence

```
ordre 1 : Qualification          3×20   ← les 120 inscrits        → classement de 120
ordre 2 : Qualification haute    3×15   ← rangs   1..60 de l'ordre 1
ordre 3 : Qualification basse    3×15   ← rangs  61..120 de l'ordre 1
```

Trois choses s'y lisent, et chacune a dû être tranchée :

1. **La forme du déroulé.** L'`ordre` d'une phase est un **ordre topologique**, pas un niveau de
   jeu : il dit *qui peut alimenter qui*, pas *qui passe avant qui sur le pas de tir*. La *haute*
   et la *basse* portent les ordres 2 et 3 uniquement parce que `_anomalies_ordres` exige la suite
   `1..N` ; elles se jouent **en même temps**, et rien ne l'interdit — `ServicePhases._transition`
   ne regarde que la phase visée, aucune contrainte de base ne borne le nombre de phases en cours,
   et `domain/suivi_deroule.py` le dit noir sur blanc depuis toujours.

   ⚠️ **Ce point a d'abord été mal lu**, y compris dans le cadrage de cette US : « suite 1..N sans
   doublon » a été pris pour « déroulé linéaire, donc pas de fourche », et un chantier de graphe a
   été envisagé pour rien. Le contrôle de non-recoupement des rangs ne joue **qu'entre les sources
   d'une même phase** ; que deux phases partitionnent le classement d'une troisième n'est pas un
   conflit. C'est noté ici pour que la fausse contrainte ne soit pas réintroduite.

2. **Le rang final.** Le classement de fin va de **1 à 120** : la *haute* occupe 1..60, la *basse*
   61..120. Le dernier de la haute précède donc le premier de la basse **même si celui-ci a mieux
   tiré son second tour** — la répartition a été décidée par la phase amont.

3. **La feuille de marque.** Un archer qui tire 3×20 puis 3×15 tient **deux** feuilles. Une flèche
   du second tour ne peut pas atterrir dans la première.

## Décision

**Un déroulé peut porter plusieurs phases de qualification.** L'invariant d'unicité est retiré, et
les lecteurs qui le supposaient sont réparés — c'était l'ordre des opérations que le pansement avait
inversé.

### 1. La feuille de marque pend à sa phase

La clé de `Serie` descend de `(tournoi, archer)` à **`(phase, archer)`**. `tournoi_id` reste comme
cadre des vues d'ensemble, mais n'est plus une clé.

**Cela résorbe `DETTE-046`** sans détour. Le registre signalait qu'un archer inscrit sur deux
créneaux n'avait qu'un emplacement pour ses flèches — la seconde série écrasant la première — et
proposait `Serie.depart_id`. La phase **subsume** le départ (elle lui appartient depuis ADR-0075) :
un seul champ règle les deux cas, au lieu de deux qui diraient la même chose à deux mailles.

### 2. Le rang vient de la phase, jamais du cumul

Le classement est la **position dans l'effectif de sa phase**, décalée par les effectifs des phases
amont. `ResultatPhase.rang_premier` porte ce décalage depuis ADR-0068 §5 et
`application/prelevement.py:tranche` le calcule : il n'y avait rien à inventer, seulement un
producteur à brancher pour les qualifications aval.

⚠️ **Un classement obtenu en triant toutes les séries par total est faux.** C'est la réalisation
naïve que cette décision interdit, et un test la tient en croisant volontairement les scores.

### 3. Une qualification ne décerne pas de médaille

`ResultatPhase` porte désormais son **origine**. Sans cela, `LignePalmares.decerne` — la seule forme
qui vaut un podium — se déduisait de « position acquise fermée », or le rang d'une qualification
l'est toujours : un tournoi de trois qualifications d'affilée aurait remis or, argent et bronze
**avant le moindre duel**. C'est exactement le défaut que la revue d'E06US004 avait corrigé, revenu
par une autre porte.

Le défaut du champ est `DUELS` : les producteurs existants ne passent rien et doivent continuer de
décerner. L'inverse aurait retiré le podium à tous les tournois d'aujourd'hui.

### 4. La saisie écrit dans la phase où l'on tire

`portee.qualification_courante(phases, depart_id)` désigne la qualification **démarrée et non
terminée** du créneau, à défaut la première **à venir**, à défaut la dernière. Le repli sur « à
venir » n'est pas de la complaisance : démarrer une phase est un geste **manuel** de l'organisateur,
et faire dépendre le pas de tir de sa discipline bloquerait la saisie tout l'après-midi s'il
l'oublie — même parti que `ServicePalmares._resultat`.

L'écran de saisie **ne montre que la phase en cours**, sans rappel du tour précédent (arbitrage du
commanditaire, 09/08/2026) : il sert debout au pas de tir, on ne le charge pas d'une information qui
n'entre pas dans le geste.

### 5. Chaque qualification a ses réglages

Le barème et le grain se règlent sur une **étape désignée**. `PhasePasUneQualification` (409) refuse
un barème de série sur un tableau — pendant symétrique de `PhasePasUnTableau`, et une erreur qui ne
pouvait pas exister tant qu'il n'y avait rien à désigner de travers.

⚠️ **Une qualification composée à l'atelier reçoit le preset FFTA 18 m** comme valeur de départ.
L'invariant `anomalies_etape` exige qu'une qualification porte barème **et** grain : sans cela,
composer la *haute* échouait, et le cas restait infaisable de bout en bout alors que le domaine
l'acceptait. `ServiceGrainValidation` refuse par ailleurs « d'inventer un barème que l'organisateur
n'a pas choisi », et la contradiction n'est qu'apparente — là-bas l'alternative était de demander le
barème d'abord, ici c'était de ne pas pouvoir composer. La valeur est **listée à l'écran**, donc
ajustable plutôt que subie.

### 6. La complétude juge chaque qualification sur son effectif

« Prêt à terminer ? » exige les trois qualifications de l'exemple : la première sur ses 120 archers,
la haute et la basse sur leurs 60. Ne regarder que les phases terminales laisserait passer une
feuille jamais close au premier tour — or c'est ce tour-là qui décide qui va où.

## Ce qui a été écarté

- **Cumuler les scores des deux tours en un seul classement.** Le message de l'ancienne anomalie le
  proposait (« une qualification en plusieurs manches se règle par son barème, pas par plusieurs
  phases ») et cette voie reste valide *pour une qualification en plusieurs manches* — ce n'est
  simplement pas le cas demandé. Le commanditaire a été explicite : « ce qui fait que le classement
  est différent du cumul des points ».
- **Aligner les lecteurs sur une résolution commune de « la » qualification.** C'est ce qu'E05US021
  avait envisagé et écarté à raison : un réordonnancement les redésaccorde. La vraie réponse est que
  chaque lecteur sache **de quelle** phase il parle.
- **Un déroulé en graphe.** Envisagé au cadrage sur une lecture fausse de l'invariant d'ordres (cf.
  §1). Inutile : la fourche est déjà représentable.
- **Corriger les forfaits en même temps.** Le forfait s'**écrit** sur la phase rendue par
  `qualification_du_tournoi` et se **lit** par le même chemin : l'affichage est « cohérent par
  accident ». Ne corriger que la lecture rendrait les forfaits **invisibles** au lieu de les rendre
  justes. C'est `DETTE-047`, et ses deux côtés se portent au créneau ensemble, dans son US.

## Conséquences

**Positives.** Le club compose le format qu'il veut, ce qui était la demande. `DETTE-046` disparaît.
Les lecteurs de qualification sont explicites sur la phase dont ils parlent, ce qui retire une classe
entière de défauts silencieux. Le déroulé de l'exemple se compose, se joue et se classe.

**Négatives, ou à surveiller.**

- **Migration `0044` destructrice à la marge** : une série dont le tournoi n'a plus **aucune** phase
  de qualification (créneau supprimé, ses phases effacées par cascade) ne peut pas recevoir de
  `phase_id` `NOT NULL` et est **supprimée**, avec journalisation. Arbitrage du commanditaire du
  09/08/2026.
- **`bareme_du_tournoi` porte un nom qui ment** : il rend celui de la **première** qualification.
  Conservé parce que la route historique le sert et qu'il est juste sur la quasi-totalité des
  tournois — mais tout appelant qui veut être juste sur un déroulé composé passe par
  `qualifications`.
- **La saisie admin devine le créneau de l'archer** (`# DETTE-049`) : la route ne le porte pas
  encore. Sans conséquence tant qu'un archer ne tire qu'un créneau, ce qui est le cas courant.
- **Le plan de cibles reste par créneau, pas par phase.** La *haute* et la *basse* se placent sur
  le même plan que le premier tour. Suffisant pour l'exemple — les archers ne bougent pas de cible
  entre deux tours — mais un format qui l'exigerait demanderait une US.

## Porté dans le code par

*(Vérifié dans le code du 09/08/2026, module par module — pas déduit de la décision.)*

- `backend/domain/phase.py` — le retrait de `_anomalies_unicite_qualification`, avec un commentaire
  à l'endroit exact pour qu'il ne soit pas réintroduit « par prudence »
- `backend/domain/serie.py` — `Serie.phase_id`, obligatoire et **sans défaut** (§1)
- `backend/domain/ports.py` — `SerieRepository` : `par_archer(phase_id, …)`, `par_phase`, et
  l'avertissement sur `par_tournoi` (un archer y figure une fois par phase tirée)
- `backend/domain/palmares.py` — `ResultatPhase.origine` et la condition `decerne` (§3)
- `backend/application/portee.py` — `qualification_courante` (§4), et le tri écrit des appelants
  restants de `qualification_du_tournoi`
- `backend/application/classements.py` — `pour_phase` et `_premiere_qualification` (§2)
- `backend/application/saisie_duels.py` — `_classement_de_l_ordre`, branche `QUALIFICATION` : la
  population par `preleves` et la tranche par `tranche`, sur le **même** résolveur
- `backend/application/palmares.py` — `_resultat_qualification` (§2, §3) et ses trois écartements
- `backend/application/completude.py` — `_compter_cibles` et `avancement_depart`, par créneau (§6)
- `backend/application/saisie.py` — `_phase_qualification` et `_feuille` (§4)
- `backend/application/bareme_qualification.py` · `backend/application/grain_validation.py` —
  `definir_pour_etape`, `qualifications` (§5)
- `backend/application/phases.py` — `ajouter` : les réglages de départ d'une qualification composée
  à l'atelier (§5)
- `backend/infrastructure/db/models.py` · `.../repositories/tir.py` — `UNIQUE(phase_id, archer_id)`
  et l'upsert sur la nouvelle clé
- `backend/migrations/versions/0044_serie_par_phase.py` — la reprise des données, ses trois cas
- `backend/api/v1/bareme_qualification.py` · `.../grain_validation.py` — les routes par étape
- `frontend/src/features/bareme/` — l'écran « Barème & validation », un formulaire par qualification
- `backend/tests/test_domain_palmares_qualifications_multiples.py`,
  `backend/tests/test_domain_phase.py` (§ E05US025),
  `backend/tests/test_bareme_qualification_api.py` (§ E05US025)
