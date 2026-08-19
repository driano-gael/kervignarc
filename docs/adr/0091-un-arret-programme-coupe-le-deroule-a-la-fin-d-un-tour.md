# ADR-0091 — Un arrêt programmé coupe le déroulé à la fin d'un tour

- **Statut** : Accepté
- **Date** : 2026-08-19
- **US** : E05US033 (tranche A ; la tranche B est E05US034)
- **S'appuie sur** : [ADR-0090](0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md) (le
  tour comme unité d'avancement générique, sans lequel « après le tour 3 » n'aurait pas de référent),
  [ADR-0076](0076-la-definition-du-deroule-est-portee-par-le-tournoi.md) (définition au tournoi /
  avancement au créneau — ce qui répartit ici la *définition* d'un arrêt et son *franchissement*) et
  [ADR-0045](0045-sequence-de-phases-cycle-de-vie-typage-source.md) §1 (le cycle de vie d'une phase,
  dont `EN_PAUSE` : cette US n'invente pas d'état, seulement un déclencheur)
- **Voisin** : [ADR-0056](0056-le-lancement-est-un-evenement-pas-un-etat.md) — dont cet ADR **s'écarte**
  sur un point précis, et la § *Décision* dit pourquoi

## Contexte

Une phase de tournoi en salle peut durer des heures. Le commanditaire a demandé, au cadrage du
18/08/2026, à **pouvoir couper** : interrompre la salle pour le repas, une réorganisation, une
annonce. La demande n'est pas « piloter chaque tour à la main » — cette formulation était le CA
d'origine de l'US, et il a été **explicitement révoqué** : l'enchaînement automatique reste le défaut.

Trois faits du code encadrent la décision, et le troisième n'a été découvert qu'en vérifiant.

**1. Il n'existe aucun événement « tour terminé ».** Chaque service de format **recalcule** l'état
complet à chaque lecture : `ServicePoules.avancement_de_phase` prend le premier tour dont une
rencontre n'est pas verrouillée, `ServiceSuisse` la première ronde non close, `ServiceBigShootOff` la
première manche non jouée. Rien n'est persisté, et le lancement d'un tour est délibérément un
*événement* et non un *état* ([ADR-0056](0056-le-lancement-est-un-evenement-pas-un-etat.md)). Il n'y a
donc **nulle part** où accrocher un déclencheur d'arrêt.

**2. La condition de déclenchement est monotone.** « Le tour 2 est achevé » ne redevient jamais faux.
C'est le fait décisif de tout cet ADR, développé en § *Décision*.

**3. `StatutPhase.EN_PAUSE` ne gelait rien.** Vérification faite au cadrage du 19/08/2026 :

- `application/saisie.py` et `application/saisie_duels.py` n'avaient **aucune** garde de statut — ni
  sur la phase, ni sur le tournoi ;
- `application/routage.py` sélectionnait ses phases sur `statut is not TERMINEE` : une phase en pause
  était routée **exactement** comme une phase en cours, et les archers recevaient leur cible ;
- `ServiceTournois.mettre_en_pause` **documentait le contraire** — « la saisie s'arrête jusqu'à
  `reprendre` ». Docstring fausse.

La pause était donc **cosmétique** : un libellé dans le suivi. La fiche de l'US annonçait ce point à
l'envers (« `EN_PAUSE` gèle la validation » y figurait comme un *piège à vérifier*, c'est-à-dire comme
un acquis) — et sans la vérification, l'US aurait livré un arrêt programmé qui n'arrête personne.

## Décision

### 1. Un arrêt se pose **après un tour**, jamais à une heure

`ArretProgramme(apres_tour, portee)`. Le tour est l'unité d'avancement générique posée par ADR-0090 :
c'est ce qui rend un arrêt exprimable sur les **six** formats sans un cas par format.

**Le planning horaire de journée** (« pause repas 12h–13h30 », l'application calculant quel tour tombe
avant) est un besoin **futur** annoncé par le commanditaire le 19/08/2026, hors du besoin d'aujourd'hui.
Il n'est **pas** anticipé : un déclencheur polymorphe posé sur une évolution supposée est exactement ce
que le § *Dette* de `CLAUDE.md` interdit — un remède structurel se propose sur preuve dans le code du
jour, 3ᵉ occurrence réelle, et il y en a **une**. Cet ADR se contente de **nommer** le point
d'extension attendu le jour où ce besoin arrivera : c'est le **déclencheur** (« quand »), et non la
portée (« sur quoi ») ni l'effet (« quoi »), qui aura une seconde forme.

### 2. La **définition** vit sur l'étape, le **franchissement** sur la phase

C'est ADR-0076 appliqué à la lettre, et la conséquence est à assumer en clair.

| | Définition | Franchissement |
|---|---|---|
| Quoi | « après le tour 3, portée départ » | « cet arrêt a coupé ces phases ; relevé ou non » |
| Où | `EtapeDeroule.arrets`, dans `deroule_etape.config` (JSON) | table `franchissement_arret` |
| Maille | le **tournoi** | le **créneau** |
| Migration | **aucune** (ADR-0046 laisse le document libre) | `0048` |

**Tous les départs d'un tournoi rejouent donc les mêmes arrêts.** C'est voulu : un planning de journée
est une propriété du *déroulé*, et deux créneaux libres de diverger sur leurs pauses seraient
exactement la divergence silencieuse qu'ADR-0076 a rendue impossible. En pratique les créneaux d'un
tournoi de salle enchaînent le même programme.

Corollaire à connaître : `Phase` porte le **découpage** en mémoire (le suivi le lit pour résoudre
l'unité de tour, la couture d'assemblage doit rester invisible) mais **pas** les arrêts — personne ne
les lit depuis une phase, et l'import fermerait un cycle (`arret_programme` a besoin de `PhaseId`).
L'asymétrie est documentée aux deux endroits plutôt que laissée à deviner.

### 3. Le franchissement est **persisté**, contre l'habitude du projet

Tout le reste de l'avancement est dérivé à la lecture. Celui-ci ne peut pas l'être, et c'est le point
que la revue doit pouvoir vérifier :

> Une fois le tour 2 achevé, « le tour 2 est achevé **et** un arrêt est posé après le tour 2 » reste
> vrai **pour toujours**. Un déclencheur qui relirait cette condition sans mémoire remettrait la phase
> en pause à la seconde suivant chaque reprise. L'organisateur perdrait la main **définitivement** :
> la salle ne repartirait jamais.

La trace n'est donc pas un confort d'implémentation, c'est **ce qui rend la reprise possible**. C'est
aussi le seul endroit où cet ADR s'écarte d'ADR-0056 (« le lancement est un événement, pas un état ») :
l'asymétrie est réelle et assumée — *lancer* est un geste dont l'effet se relit dans les données,
*avoir coupé* ne se relit nulle part.

L'état a trois valeurs, cycle **monotone** comme celui d'une phase (ADR-0045) : `ARME` → `FRANCHI` →
`LEVE`. Il n'y a **pas** d'état « programmé » : c'est l'absence de ligne. En ajouter un obligerait à
écrire une ligne par arrêt et par créneau dès la composition, donc à réécrire l'avancement de tous les
créneaux à chaque édition du déroulé — ce qu'ADR-0076 a précisément supprimé.

### 4. Un arrêt de portée « départ » laisse **chaque phase finir son tour**

Arbitrage du commanditaire, 18/08/2026 : l'arrêt n'est **pas simultané**. Si la coupe tombe à la fin
du tour 3 des poules, la qualification finit ses volées en cours et le duel engagé va à son terme.
Personne n'est coupé en plein tir ; la salle s'éteint en quelques minutes, pas d'un coup.

C'est la raison d'être de l'état `ARME`, et de la seule donnée de forme inhabituelle du modèle :
`tours_a_finir`, la **photo** — prise à l'armement — du tour que chaque phase avait en cours. Une
phase s'arrête quand son tour courant a **changé**. Comparer à un tour noté, plutôt qu'attendre un
événement « tour fini », est la seule formulation compatible avec un avancement dérivé (fait 1).

⚠️ **Les phases déjà en pause sont exclues de la photo**, et l'exclusion n'est pas cosmétique : une
phase suspendue à la main ne progresse plus, donc son tour ne change jamais, donc l'arrêt resterait
`ARME` **pour toujours** — et un arrêt armé n'est pas relançable. L'organisateur perdait la main sur
tout le créneau à cause d'une phase qu'il avait suspendue lui-même. La première rédaction filtrait sur
`STATUTS_DEMARRES` (`EN_COURS` **ou** `EN_PAUSE`), qui est le bon ensemble pour *lire* un avancement et
le mauvais pour *décider d'arrêter*. Trouvé par un test écrit depuis le CA.

### 5. La reprise est un geste d'admin, **un seul par arrêt**

`POST /departs/{id}/arrets/{id}/relancer` relance **toutes** les phases que cet arrêt a coupées.
« Quatre boutons pour un seul arrêt créerait exactement le piège qu'on cherche à éviter — en oublier
une » (CA). D'où une route adressée par **arrêt**, là où la reprise manuelle d'une phase seule garde la
sienne (`POST /departs/{id}/phases/{id}/statut`).

La liste des phases relancées est **persistée** (`phases_arretees`) et non déduite. La déduire
(« toutes les phases en pause du créneau ») relancerait aussi une phase suspendue à la main pour une
autre raison — un effet de bord qu'aucun écran n'expliquerait, remettant des archers en piste sans que
personne l'ait demandé.

Après reprise, la phase repart en automatique jusqu'au prochain arrêt. Le pilotage tour par tour reste
donc possible **sans second mode** : il suffit de programmer un arrêt à chaque tour.

### 6. `EN_PAUSE` gèle désormais quelque chose — et pas tout

Le fait 3 obligeait à trancher. Périmètre arbitré par le commanditaire le 19/08/2026 :

| Geste | Pendant `StatutPhase.EN_PAUSE` | Pourquoi |
|---|---|---|
| Saisir une volée, valider une série | **refusé** (`PhaseEnPause`, 409) | c'est ce qui ferait avancer le tour |
| Saisir une manche, un barrage, valider un duel | **refusé** (409) | idem |
| **Corriger** un score déjà saisi | **autorisé** | CA explicite — voir ci-dessous |
| Router un archer | issue **`EN_ATTENTE`** (réutilisée d'E05US030) | « rien à tirer pour l'instant » est déjà rendu par la tablette |
| **Lire** un tableau, un état, le suivi | **autorisé** | le pilotage doit voir où il en est *pendant* la pause |
| Pause du **tournoi** (`StatutTournoi.EN_PAUSE`) | **inchangée, toujours cosmétique** | autre maille (ADR-0026 §3), hors périmètre → `DETTE-073` |

**La correction reste possible, et c'est un CA, pas une omission.** La pause gèle ce qui *avance* ;
elle ne gèle pas ce qui *répare*. C'est précisément quand la salle souffle que l'on relit les feuilles
et que l'on découvre un 9 pris pour un 10 : interdire la correction ferait de chaque pause un
cul-de-sac, dont la seule issue serait de relancer toute la salle pour corriger une flèche. D'où une
garde sur `saisir_volee` et `valider`, et **aucune** sur `corriger_volee`.

⚠️ **La garde de routage est posée après la résolution de la phase, pas dans la sélection.** Écarter
les phases en pause de la sélection aurait fait tomber le routage sur une *autre* phase — ou sur
`tableaux[-1]` — donc envoyé l'archer tirer ailleurs au lieu de lui dire d'attendre : un défaut pire
que celui qu'on corrige. La sélection dit *de quoi on parle*, pas *si ça tourne*.

⚠️ **Les duels n'ont aucun chemin de correction** (à la différence de la qualification). Le CA de la
correction est donc sans objet pour eux. C'est un manque **préexistant** — un duel validé de travers
ne se rectifie nulle part aujourd'hui —, ni introduit ni aggravé ici, signalé plutôt que passé sous
silence.

### 7. Le déclencheur est un service, appelé après chaque validation

`ServiceArretsProgrammes.evaluer(depart_id)` **constate** au lieu d'écouter (fait 1) : il compare le
tour courant de chaque phase à ce que les arrêts attendent. Il est **idempotent**, ce qui n'est pas un
raffinement mais une nécessité — il est appelé après chaque validation de score, soit des centaines de
fois par jour, depuis ~30 tablettes dont plusieurs peuvent valider dans la même seconde. L'idempotence
est tenue **deux fois** : par la mémoire des franchissements, et par l'unicité `(phase_id, apres_tour)`
en base.

**La couture d'avancement passe par `ServiceSuiviDeroule`**, port `LecteurAvancementDuDepart`. C'est le
seul endroit du projet qui sache répondre « quel tour tourne » pour **tous** les formats : les poules,
le suisse et le Big Shoot Off répondent par `LecteurAvancementDePhase`, mais l'**élimination directe**
— le format le plus courant d'un tournoi de salle — n'a aucun lecteur branché et voit son avancement
reconstruit sur place à partir des braquets. Tenir un second registre par type aurait donc laissé les
tableaux **hors du mécanisme d'arrêt** sans que rien ne rougisse, et aurait été la 4ᵉ occurrence d'une
résolution par type — ce dont la docstring du port met explicitement en garde.

Le signalement se fait par un port étroit `EvaluateurArrets`, branché **tardivement** au composition
root : la saisie n'a pas à connaître les arrêts, seulement à signaler qu'un résultat est écrit.
**Non branché, toute l'US est inerte** — mode de panne de `DETTE-028` (six moteurs livrés, aucun
appelé), d'où deux lignes explicitement commentées dans `bootstrap/`.

Une exception levée par le déclencheur **ne remonte pas au scoreur** : la validation, elle, a réussi et
est persistée. La laisser remonter rendrait un 500 à un archer qui a bien tiré, qui ressaisirait alors
une volée déjà enregistrée. On journalise ; la validation suivante réévaluera.

### 8. La qualification et l'échauffement deviennent divisibles en tours

`DecoupageEnTours(nb_tours)`, réglage d'organisateur : « 20 volées en 2 tours de 10 ». Sans lui ces deux
types n'ont qu'un tour, et un arrêt « après le tour n » n'a nulle part où se poser.

Ce réglage **précise** le contrat de phase, il ne le contredit pas : `PHASE_ENTIERE` signifie
littéralement « rien dans la structure de ce format ne dit combien de tours » (ADR-0090). Quand
l'organisateur le dit, la source existe enfin — et il n'y a jamais deux sources pour le même nombre.
Sur un format qui compte déjà ses tours, l'agrégat **refuse** le réglage (patron de `poules`,
`big_shoot_off`, `suisse` : « un réglage que rien ne lit est invisible et faux ») tandis que le
résolveur de lecture reste **total** — l'agrégat garde la cohérence de la donnée, la fonction pure garde
la propriété de toujours rendre une réponse.

## Conséquences

**Ce qui devient vrai.**

- Une phase sans arrêt programmé se comporte **exactement** comme avant : aucune phase en cours le jour
  du déploiement ne change de comportement. Une base non migrée relit `arrets` absent comme « aucun
  arrêt ». C'est ce qui rend la livraison sûre.
- Mettre une phase en pause **arrête réellement le tir**, à la main comme par arrêt programmé. Le
  bouton de pause manuelle d'une phase cesse d'être décoratif — sa docstring devient vraie.
- Un tournoi capturé en format **conserve** ses pauses et son découpage : `ModelePhase` porte les deux
  champs. Leur absence aurait rejoué le défaut de `barrage_jusqu_au`, que le dépôt a déjà payé une fois.

**Ce qui reste faux, et qu'il faut savoir.**

- La pause du **tournoi** reste cosmétique (`DETTE-073`) : autre maille, hors périmètre.
- `E05US034` porte l'**angle mort** de cette tranche : ni le public ni l'écran de salle ne *disent* que
  c'est une pause, et rien ne rappelle à l'organisateur qu'une phase attend sa relance. Tolérable
  parce qu'il vient de programmer l'arrêt et se tient devant le pilotage ; **pas** tolérable le jour J.
  À livrer avant tout déploiement réel de la capacité.
- `DETTE-031` est **élargie** : le déclencheur paie la recomposition du créneau après chaque validation,
  là où seuls le pilotage et l'écran de salle la payaient toutes les 10 s. Le facteur d'appel a changé
  de nature. Tenable au contexte (mono-club, local, une ou deux phases actives) et **tracé** plutôt que
  contourné par une mémoïsation locale, qui serait un remède structurel au mauvais endroit.
- `DETTE-064` est **élargie de deux occurrences** : les helpers de décor `poser_phase_factice` /
  `poser_phase_sql` recopient les réglages champ par champ, et rien ne rougit quand on en oublie un.
  L'oubli s'est déjà produit **trois** fois ; le remède (`EtapeDeroule.de_phase`) reste une US dédiée.
- `DETTE-054` est **élargie** : les DTO de réglage sont dupliqués entre `api/v1/phases.py` et
  `api/v1/formats.py`, et cette US en ajoute deux paires.
- Plusieurs arrêts dus au même instant (l'avancement a sauté des tours entre deux évaluations) ne
  produisent qu'**une** pause : le plus ancien est crédité, les autres sont consommés et journalisés.
  Les laisser en attente les ferait se déclencher l'un après l'autre à chaque reprise, obligeant à
  relancer trois fois pour une seule coupe. Rendre ce cas **visible** relève d'`E05US034`.

## Porté dans le code par

⚠️ Section écrite en **vérifiant dans le code du jour**, pas en déduisant de la décision.

| Décision | Module qui l'applique | Vérifié |
|---|---|---|
| §1 arrêt après un tour, invariants | `backend/domain/arret_programme.py` (`ArretProgramme`, `verifier_arrets`, `arrets_atteints`) | oui — `tests/test_domain_arret_programme.py` |
| §2 définition sur l'étape | `backend/domain/deroule_etape.py` (`EtapeDeroule.arrets`, `.decoupage`, `_verifier_arrets_applicables`) ; JSON dans `backend/infrastructure/db/repositories/moteur.py` (`_politiques_json`, `_lire_arrets`, `_lire_decoupage`) | oui |
| §2 pas de miroir sur `Phase` | `backend/domain/phase.py` (`Phase.decoupage` et sa docstring) ; `EtapeDeroule.instancier` | oui — l'absence est commentée aux deux endroits |
| §3 franchissement persisté, cycle monotone | `backend/domain/arret_programme.py` (`FranchissementArret`, `EtatFranchissement`) ; `backend/infrastructure/db/models.py` (`FranchissementArretORM`) ; `migrations/versions/0048_franchissement_arret.py` | oui |
| §4 chaque phase finit son tour | `backend/domain/arret_programme.py` (`phases_a_arreter`) ; `backend/application/arrets_programmes.py` (`_armer_sur_le_depart`, `_resoudre_les_arrets_armes`) | oui — `tests/test_service_arrets_programmes.py` |
| §5 reprise d'un seul geste | `backend/application/arrets_programmes.py` (`lever`) ; `backend/api/v1/phases.py` (`relancer_arret`) ; `frontend/src/features/suivi-deroule/PilotageCreneau.tsx` (`RelanceDesArrets`) | oui |
| §6 gel de la saisie | `backend/application/saisie.py` (`_refuser_si_en_pause`), `backend/application/saisie_duels.py` (idem) | oui — `tests/test_service_saisie.py` § E05US033 |
| §6 gel du routage | `backend/application/routage.py` (`_en_pause`, appelé aux **deux** résolutions de phase) | oui |
| §6 correction non gelée | `backend/application/saisie.py` (`corriger_volee`, **sans** garde — délibéré) | oui — oracle de non-garde dans `test_service_saisie.py` |
| §7 déclencheur idempotent | `backend/application/arrets_programmes.py` (`evaluer`) ; couture `backend/application/suivi_deroule.py` (`avancement_par_phase`) ; branchement `backend/bootstrap/composition.py` | oui |
| §8 découpage en tours | `backend/domain/tour_de_phase.py` (`DecoupageEnTours`, `unite_de_tour_effective`, `nb_tours_regles`) ; garde de type dans `backend/domain/phase.py` | oui |
| §2 conservation à la promotion | `backend/domain/format_tournoi.py` (`ModelePhase.arrets`, `.decoupage`, `pour_tournoi`, `d_etape`) | oui |
| Atelier (les deux éditeurs) | `frontend/src/shared/phases/ReglageArrets.tsx` + `arrets.ts`, montés par `features/phases/Phases.tsx` et `features/deroule/Deroule.tsx` | oui |
