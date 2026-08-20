# ADR-0093 — Une qualification se découpe en tours égaux, et « arrêtable » cesse d'être « déroulé »

- **Statut** : Accepté
- **Date** : 2026-08-20
- **US** : E05US035
- **S'appuie sur** : [ADR-0090](0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md) (le
  tour comme unité d'avancement générique, et l'invariant *avancer ≠ classer* sans lequel ce
  découpage aurait atterri dans le barème),
  [ADR-0091](0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md) (l'arrêt coupe à une
  frontière de tour observée — c'est la seule raison d'être du découpage),
  [ADR-0082](0082-plusieurs-qualifications-dans-un-meme-deroule.md) (plusieurs qualifications dans
  un même créneau : c'est ce qui rend « les archers de cette phase » non trivial) et
  [ADR-0083](0083-un-contrat-de-phase-decrit-ce-que-le-moteur-sait-faire.md) (le registre de
  capacités, dont cet ADR ajoute une entrée)
- **Voisin** : [ADR-0076](0076-la-definition-du-deroule-est-portee-par-le-tournoi.md) — le découpage
  est une **définition**, donc porté par l'étape du tournoi, comme les trois autres réglages de
  format

## Contexte

Depuis [ADR-0091](0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md), l'organisateur
peut programmer une pause « après le tour *n* » — sur une élimination directe, des poules, un
système suisse ou un Big Shoot Off. La **qualification** en était exclue, et c'est le format que
tout le monde tire : des heures de tir d'affilée, sans point de coupe déclarable. Le refus était
explicite (`verifier_type_arretable`), donc honnête, mais il fermait la capacité là où elle sert le
plus.

Le CA a été **reporté trois fois** — E05US033 → E05US034 → E05US035 — et le motif n'a jamais varié :
dériver le tour d'une qualification n'est pas un reste de plomberie. Deux obstacles étaient connus,
un troisième n'est apparu qu'en écrivant le code.

**1. Une qualification n'a pas de tours.** « 20 volées » ne dit pas s'il y en a un ou quatre. Les
quatre autres formats portent leur découpage dans leur structure — un arbre a des tours, un
round-robin a des tours, un suisse a des rondes réglées. La qualification n'a qu'un cumul. Il faut
donc **un réglage neuf**, et `UniteDeTour.PHASE_ENTIERE` l'annonçait déjà noir sur blanc : « *ce
réglage arrive avec E05US033 (les pauses programmées), là où il sert* ».

**2. Compter les archers d'une qualification n'est pas trivial**, et c'est ce qui a coûté les trois
reports. Le tour se dérive du **plus lent** — une phase avance au rythme du dernier archer, sinon on
coupe la salle pendant qu'une partie du pas de tir tire encore. Mais « le plus lent de qui » ? Trois
populations différentes se ressemblent :

- les **inscrits du créneau** — faux : deux qualifications peuvent coexister dans un même départ
  ([ADR-0082](0082-plusieurs-qualifications-dans-un-meme-deroule.md), la fourche *haute*/*basse*), et
  leurs archers sont placés **sur les mêmes cibles** ;
- les inscrits **moins les forfaits** — nécessaire, pas suffisant ;
- les archers **placés** — un inscrit en réserve n'a aucune affectation, donc aucune volée à tirer.

Compter faux ne produit pas une erreur : ça produit une phase qui n'avance **jamais** (un forfait ou
un réserviste à zéro volée retient le minimum toute la journée) ou qui avance **trop tôt**. Aucun des
deux ne se voit avant le jour J.

**3. Le troisième obstacle n'était pas au programme.** Lever le refus supposait d'ajouter la
qualification à `TYPES_DEROULES`, la table que lisait `verifier_type_arretable`. Or cette table
répond à une **autre** question : « le moteur *fait-il jouer* ce type ? » — et c'est elle qui décide
si le prélèvement d'une phase sera honoré, donc si son rang de départ **relève le plancher
d'inscrits** (E05US021). Y verser la qualification aurait fait réclamer un plancher par rangs à toute
qualification prélevée : un **refus de démarrage le jour J**, en échange d'un réglage d'affichage.
Les deux tables coïncidaient jusqu'ici, ce qui rendait la confusion invisible.

## Décision

**1. Une qualification se règle en `n` tours égaux, et le découpage est un réglage de déroulé, pas
de barème.** L'organisateur saisit un **nombre de tours** ; le moteur en déduit la longueur et
**refuse à la composition** un nombre qui ne divise pas les volées. 20 volées en 3 tours donneraient
7/7/6, et « après le tour 2 » ne désignerait plus le même instant selon l'archer — donc une pause qui
ne tombe pas au même endroit pour tout le monde. Le refus est réparable d'un geste à l'atelier ; le
découvrir le jour J ne l'est pas.

Le champ vit sur `EtapeDeroule` (donc au tournoi, ADR-0076) aux côtés de `poules`, `big_shoot_off` et
`suisse`, **pas** sur `BaremeQualification`. C'était le raccourci naturel — `nb_volees` y vit déjà —
et il aurait été faux : un barème dit comment on **classe**, un découpage comment on **avance**.
C'est l'invariant *avancer ≠ classer* posé par le commanditaire
([ADR-0090](0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md)). Les mêler aurait
laissé croire qu'un tour de qualification produit un classement intermédiaire, que ne prévoit aucune
règle FFTA.

Le découpage est recopié dans `Phase` par `instancier`, à la différence des `arrets` : c'est le
moteur qui lit l'avancement **sur la phase** (`ServiceSaisie` reçoit un `phase_id`), donc il doit
voyager.

**2. Le tour se dérive du plus lent d'une population résolue en trois filtres.** Les archers
**placés** du créneau (plan de cibles, ADR-0033), **admis** par cette phase (la résolution déjà
utilisée par le chemin d'écriture — `ServiceSaisie._admet` —, jamais une seconde), **moins les
forfaits de cette phase**. Le compte retenu est celui des volées **saisies**, non validées : un tour
est fini quand la salle a tiré, pas quand le scoreur a signé — sans quoi une validation en file
hors-ligne (E04US009) ferait tomber la pause plusieurs volées trop tard. C'est déjà l'oracle
d'`avancement_cible`, qui compte les mêmes volées pour la console de supervision.

**Le tour peut reculer**, et le calcul l'assume sans mémoire : un archer qui commence en retard fait
baisser le minimum. C'est `phases_a_arreter` qui absorbe le recul (comparaison `>` et non `!=`,
correctif de 2ᵉ passe d'E05US033), et il ne peut le faire que si la lecture reste honnête. Lisser ici
pour « éviter le recul » ferait mentir la lecture au moment précis où elle protège le pas de tir.

**3. « Arrêtable » devient une capacité à part entière du registre de phase, distincte de
« déroulé ».** `ContratDePhase.avancement_lisible` répond à « sait-on *observer* le tour de cette
phase ? » ; `deroule_par_un_service` répond à « le moteur *fait-il jouer* ce type ? ». La
qualification sépare les deux : on sait dire où elle en est sans que personne ne la *monte* — elle
n'a aucune opposition à monter. `TYPES_ARRETABLES` (domaine) en dérive, et `verifier_type_arretable`
le lit désormais à la place de `TYPES_DEROULES`.

Ce n'est pas une capacité de confort : c'est exactement le raisonnement qui a déjà fait de
`classement_lisible` une entrée distincte plutôt qu'un alias de `deroule_par_un_service` — « *c'est
précisément parce qu'ils ne coïncident pas qu'ils sont deux capacités du registre, et non une
seule* » ([ADR-0083](0083-un-contrat-de-phase-decrit-ce-que-le-moteur-sait-faire.md)).

**4. La qualification passe de `PHASE_ENTIERE` à `UniteDeTour.TOUR`.** Le mot de la salle est
« tour » — c'est celui du CA (« 20 volées en 2 tours de 10 »). Une qualification **non découpée**
compte alors un seul tour, ce qui reste **vrai** : la phase *est* son tour, et ce n'est pas un cas
dégénéré.

## Conséquences

**Aucune migration.** Le découpage s'écrit à la racine du `config` JSON de l'étape, comme `arrets`,
`suisse` et `big_shoot_off` avant lui (ADR-0046 laisse le document libre hors de `policies`). Une
étape écrite avant cette US se relit « non découpée », soit exactement son comportement d'avant.

**Le découpage voyage avec les formats.** `ModelePhase` le porte, sous le régime brouillon habituel
(aucune vérification de divisibilité sur une brique de bibliothèque, qui ignore le barème du tournoi
qui l'appliquera). L'omettre aurait rejoué, une **troisième** fois, le défaut de `barrage_jusqu_au`
puis d'`arrets` : capturer un tournoi en format perdrait son découpage en silence, et le format
réappliqué rendrait sa qualification non arrêtable — donc **toutes** les pauses posées dessus,
refusées.

**Deux tables doivent bouger ensemble, et rien dans le code ne l'impose** : le branchement du lecteur
au composition root (`TypePhase.QUALIFICATION` → `ServiceSaisie`) et la table de refus
`TYPES_ARRETABLES`. Un refus levé sans lecteur rendrait le réglage acceptable et **inerte** ; un
lecteur sans refus levé le rendrait inaccessible. Le vis-à-vis est tenu par
`backend/tests/test_arrets_api.py`, qui oppose le registre `_avancements` à la table — c'est un
test, pas une contrainte structurelle, et c'est la limite assumée de ce montage.

**Changer `nb_tours` en cours de phase déplace les frontières de tours.** Un arrêt déjà franchi ne
rejoue pas (le `FranchissementArret` est persisté au créneau), mais un arrêt non encore atteint
tombera au nouvel endroit. C'est le comportement voulu — et surtout, contrairement au format du tir
d'un Big Shoot Off (`DETTE-062`), **aucun score n'est re-partitionné** : le découpage ne touche que
l'avancement, jamais le classement. C'est le bénéfice concret de l'avoir tenu hors du barème.

**Ce qui reste hors périmètre, et pourquoi.** L'**échauffement** n'a ni barème ni feuille de marque :
aucune donnée existante ne dit où il en est, et lui inventer un avancement est un choix métier à
trancher, pas de la plomberie. Le **barrage**, le **placement** et la **colline** ne sont déroulés
par aucun service (`DETTE-028`). Les quatre restent **explicitement refusés** — un refus vaut mieux
qu'un réglage inerte, et `test_domain_qualification` garde cette coupe.

**`DETTE-054` s'élargit d'une paire** de DTO jumeaux (`DecoupageDTO` dans les deux routeurs de
composition), et **`DETTE-022`** — la résolution « phase de qualif → forfaits », écrite quatre fois —
gagne un cinquième site qui, lui, fait le geste **juste** (`forfaits.par_phase(phase.id)` plutôt que
« la » qualification du tournoi). C'est le chemin que cette dette devra rejoindre, pas une occurrence
de plus.

## Porté dans le code par

⚠️ Section écrite en **vérifiant dans le code du jour**, pas en déduisant de la décision.

| Décision | Module qui l'applique | Vérifié |
|---|---|---|
| §1 — le découpage est un réglage de déroulé, en tours **égaux** | `backend/domain/qualification.py` (`DecoupageEnTours`, `verifier_decoupage`, `verifier_decoupage_applicable`, `volees_par_tour`) | oui |
| §1 — porté par l'étape, recopié dans la phase | `backend/domain/deroule_etape.py` (champ `decoupage`, appel dans `__post_init__`, recopie dans `instancier`) · `backend/domain/phase.py` (champ + garde de type) | oui |
| §1 — hors du barème | `backend/domain/bareme.py` **inchangé** — c'est la vérification : `BaremeQualification` ne porte toujours que `nb_volees` / `nb_fleches_par_volee` | oui |
| §2 — le tour se dérive du plus lent d'une population à trois filtres | `backend/application/saisie.py` (`ServiceSaisie.avancement_de_phase`, `_volees_du_plus_lent`) | oui |
| §2 — l'arithmétique du tour, sans mémoire | `backend/domain/suivi_deroule.py` (`avancement_de_qualification`) | oui |
| §2 — le recul est absorbé, pas lissé | `backend/domain/arret_programme.py` (`phases_a_arreter`, comparaison `>`) — **inchangé par cette US**, et c'est le point : le calcul neuf a été écrit pour ce contrat existant | oui |
| §3 — « arrêtable » est une capacité distincte | `backend/domain/contrat_phase.py` (`ContratDePhase.avancement_lisible`, `TYPES_ARRETABLES`) | oui |
| §3 — le refus lit la nouvelle table | `backend/domain/arret_programme.py` (`verifier_type_arretable`) | oui |
| §3 — miroir front | `frontend/src/shared/phases/catalogue.ts` (`TYPES_ARRETABLES`) | oui |
| §4 — le mot de la salle est « tour » | `backend/domain/contrat_phase.py` (`_CONTRATS[QUALIFICATION].unite_de_tour`) · résolution du libellé par `backend/domain/tour_de_phase.py`, **inchangé** (il délègue déjà à l'unité) | oui |
| Conséquence — le lecteur est branché | `backend/bootstrap/composition.py` (`brancher_lecteur_avancement(TypePhase.QUALIFICATION, …)`) | oui |
| Conséquence — aucune migration, écriture à la racine du `config` | `backend/infrastructure/db/repositories/moteur.py` (`_politiques_json`, `_lire_decoupage`) | oui |
| Conséquence — le format capturé conserve le découpage | `backend/domain/format_tournoi.py` (`ModelePhase.decoupage`, `pour_tournoi`, `d_etape`) | oui |
| Conséquence — le vis-à-vis des deux tables | `backend/tests/test_arrets_api.py` | oui |
| §1 — le réglage se pose à l'atelier | `frontend/src/shared/phases/decoupage.ts` · `frontend/src/shared/phases/ReglageDecoupage.tsx` · montés par `features/phases/Phases.tsx` et `features/deroule/Deroule.tsx` | oui |
