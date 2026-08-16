# ADR-0085 — Une phase décerne ses rangs si rien ne prélève dedans

- **Statut** : Accepté
- **Date** : 2026-08-16
- **Décideurs** : Organisateur / Architecte
- **Précise** : [ADR-0067](0067-palmares-agregation-des-rangs-de-phases.md) (agrégation des rangs de
  phases) · [ADR-0081](0081-une-phase-attend-que-sa-source-ait-departage-les-places-qu-elle-preleve.md)
  (plages indécises) · [ADR-0083](0083-le-contrat-de-phase-jouable.md) (contrat de phase jouable)
- **Porté dans le code par** : `application/palmares.py` (`_est_terminale`, `_resultat_classant`,
  `_a_commence`, `_est_epuisee`, `_borne`, `_TYPES_CLASSANTS_AU_PALMARES`) ·
  `domain/palmares.py` (`OriginePalmares`, `ResultatPhase.origine`, `LignePalmares.decerne`) ·
  `application/routage.py` (`LecteurRencontresARouter`, dont `epuisee` sert ici aussi)

## Contexte et problème

Jusqu'à E05US026, seules trois familles de phases entraient au palmarès : la qualification, les
phases à tableau (par rejeu d'arbre) et le Big Shoot Off (par ses rangs exacts). Les **poules** en
étaient dehors, et `application/palmares.py` disait pourquoi : *« leur classement n'est pas un ordre
de sortie — l'y verser demande de décider ce qu'une poule acquiert au palmarès, ce que le CA n'a pas
posé »*.

Rendre le système suisse jouable posait la question pour de bon, puisqu'il produit lui aussi un
classement de phase sans arbre.

**L'intuition de départ était fausse, et c'est le commanditaire qui l'a démontrée.** La règle
pressentie était « une phase de poules ne titre jamais, il faut une phase finale ». Elle a été
écartée le 15/08/2026 par la description d'un format club réel :

> 36 archers. **Phase 1** : 6 poules de 6, disputant les rangs 1-36. **Phase 2** : 6 poules de 6,
> composées **par niveau** — les rangs 1-6, 7-12, … Le classement de la phase 2 est le classement
> final du tournoi, exact de 1 à 36.

Dans ce déroulé, la **dernière phase est une phase de poules**, et c'est bien elle qui désigne le
champion. Une règle indexée sur le **type** de phase se serait donc trompée à tous les coups sur ce
format, et aurait obligé le club à ajouter une phase finale fictive pour obtenir un podium.

## Décision

### 1. Le critère est **structurel**, pas typologique

> Une phase **décerne** ses rangs — donc peut donner une médaille — **si et seulement si aucune
> phase avale ne prélève dedans.**

Le critère se lit sur le **graphe des sources** du déroulé, pas sur `TypePhase`. La même phase de
poules titre dans un format qui s'arrête là, et ne titre pas dans un format qui enchaîne, sans que
l'organisateur ait quoi que ce soit à régler.

Il se lit sur `ordre` et non sur l'identité, parce que c'est ainsi qu'une source désigne sa phase
(`SourcePhase.ordre_source`) : c'est l'ancrage par ordre de `DETTE-026`, et s'en écarter ici
créerait une seconde convention.

### 2. Deux régimes, portés par `origine`

- phase **consommée** → `origine=QUALIFICATION` : elle contribue ses rangs **sans médaille** ;
- phase **terminale** → `origine=DUELS` : elle décerne.

Le mécanisme de fusion fait le reste seul — `_positions_par_archer` retient la position de plus
grand `ordre` —, si bien que les qualifiés d'un tableau aval reçoivent le rang du tableau, tandis
que les **non-qualifiés** gardent celui de leur poule. C'est le gain principal côté organisateur :
avant cet ADR, un archer non qualifié retombait à son rang de **qualification**, comme si sa poule
n'avait pas eu lieu.

### 3. Décerner suppose d'avoir **commencé** et **fini**

Deux gardes distinctes, et l'absence de l'une comme de l'autre a produit un défaut réel, relevé en
revue :

- **`_a_commence`** — le classement d'une phase à rencontres est **complet dès la composition** : il
  dérive du classement amont, pas d'un tir. Sans cette garde, une phase terminale jamais commencée
  décernait or, argent et bronze **avant la première flèche**, sur des rangs venus de la
  qualification du matin — exactement ce qu'`OriginePalmares` avait été créé pour fermer en
  E05US025, rouvert par un autre chemin.
- **`_est_epuisee`** — tant que la phase n'est pas allée à son terme, ses archers restent `en_lice`,
  donc `decerne` est faux. Un rang annoncé avant la fin est un faux départ.

`_est_epuisee` s'appuie sur le **même port** que le routage (`LecteurRencontresARouter.epuisee`) :
la question « reste-t-il quelque chose à tirer ? » est la même des deux côtés, et deux calculs
concurrents finiraient par se contredire sur qui a fini.

### 4. Les plages indécises deviennent des **fourchettes**

C'est leur sens exact. Les quatre vainqueurs de quatre poules occupent les positions 1 à 4 sans que
rien ne les sépare tant que le départage inter-poules n'est pas demandé : le palmarès les rend donc
en `rang_min=1, rang_max=4`, et c'est la politique `aggregation` (ADR-0067) qui tranchera — comme
pour les battus d'un quart de finale. Les écraser sur leur position exacte donnerait un ordre que la
compétition n'a pas produit, ce qu'ADR-0081 nomme.

### 5. Deux chemins restent **exemptés**, et il faut le dire

`_resultat` (tableaux) et `_resultat_big_shoot_off` gardent `origine=DUELS` **en dur**, sans passer
par `_est_terminale`. Ce n'est pas un oubli :

- leurs rangs sont **gagnés au tir**, match par match ou élimination par élimination — ils ne
  dérivent pas d'un ordre hérité de l'amont, donc le risque de médaille prématurée n'existe pas ;
- la fusion par `ordre` maximal couvre déjà le cas « un tableau alimente une consolante » : les
  archers repris par l'aval y reçoivent leur rang final.

Le critère du §1 ne s'applique donc qu'à `_TYPES_CLASSANTS_AU_PALMARES` — les phases dont le
palmarès lit le **classement de phase** : poules et système suisse aujourd'hui, colline demain.

## Conséquences

**Positives**

- Le format club en cascade (`E05US029`) devient publiable : sa dernière phase décerne, sans réglage.
- Les non-qualifiés d'une phase de poules sont enfin classés à leur vraie place.
- Un format qui devient `classement_lisible` entre automatiquement dans le régime, `_TYPES_CLASSANTS_AU_PALMARES` étant **dérivée** de `TYPES_CLASSANTS_LUS`.

**Négatives, et à surveiller**

- ⚠️ **Un podium peut changer si l'organisateur édite le graphe des sources** en cours de tournoi :
  brancher une phase avale sur une phase terminale lui retire ses médailles. C'est cohérent — le
  format a changé —, mais ce n'est pas signalé à l'écran. Le cas suppose une édition volontaire du
  déroulé, donc il n'est pas traité ici.
- La règle est **générale dans son énoncé et partielle dans son application** (§5). Le prochain
  format ajouté devra savoir dans quel régime il tombe ; c'est pourquoi le §5 est écrit plutôt que
  déduit.
- `_est_epuisee` ajoute une lecture par phase classante au calcul du palmarès, sur deux routes
  publiques — `DETTE-031` est élargie d'autant.
