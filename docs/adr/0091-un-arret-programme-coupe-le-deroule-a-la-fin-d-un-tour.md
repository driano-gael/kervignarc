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

Corollaire à connaître : `Phase` ne porte **pas** les arrêts, à la différence des quatre réglages de
format (`profondeur`, `poules`, `big_shoot_off`, `suisse`) que `instancier` recopie dans le créneau.
Deux raisons : personne ne les lit depuis une phase — le déclencheur lit l'**étape** —, et l'import
fermerait un cycle, `arret_programme` ayant besoin de `PhaseId`. L'asymétrie est commentée dans
`EtapeDeroule.instancier` plutôt que laissée à deviner.

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
| Saisir une volée, valider une série (qualification) | **refusé** (`PhaseEnPause`, 409) | c'est ce qui ferait avancer le tour |
| Valider un duel (élimination directe) | **refusé** (409) | seule la validation fait avancer un braquet |
| Saisir ou rééditer une **manche**, un **barrage** | **autorisé** | un duel du tour suivant peut être **déjà engagé** — cf. l'encart ci-dessous |
| Valider une rencontre de **poules**, de **suisse**, une **manche de Big Shoot Off** | **refusé** (409) | trois chemins d'écriture à part entière, oubliés à la première livraison |
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

⚠️ **`ServiceRoutage` résout une phase à TROIS endroits, et deux seulement sont gardés.** Le compte
exact importe, parce qu'un lecteur qui en trouve trois là où l'ADR en annonce deux ne peut pas savoir
si le troisième est un oubli :

| Point de résolution | Gardé ? | Pourquoi |
|---|---|---|
| `routage()` → `_phase_de_tableau` | **oui** | c'est ce qui dit à un archer où tirer |
| `routage()` → `_phase_restreinte_en_cours` (voie superposée) | **oui** | elle **court-circuite** la résolution principale ; sans garde, une finale en pause aurait continué à router ses huit finalistes |
| `affectations()` → `_phase_de_tableau` | **non, délibérément** | c'est une **lecture publique** (`VueEcran.AFFECTATIONS`, E07US008), pas un ordre de tir. Le CA veut qu'on puisse *voir* où en est la salle pendant la pause |

La conséquence assumée de la troisième ligne : l'écran de salle continue d'afficher les affectations
pendant une pause, **sans dire qu'il y a pause**. Ce n'est pas un trou de cette décision mais
exactement l'angle mort déclaré en § *Conséquences* — la mention publique de la pause est le CA
d'`E05US034`. Le distinguer d'un oubli est le seul objet de ce tableau.

⚠️ **La garde des duels ne porte que sur `valider`, et c'est un correctif de revue.** La première
rédaction gardait aussi `saisir_manche` et `saisir_barrage` — ce qui coupait **en plein tir** un duel
du tour suivant déjà engagé : `_match_saisissable` rend un match jouable dès que ses deux occupants
sont connus, donc des quarts se tirent pendant que les derniers huitièmes finissent. Quand le dernier
huitième était validé, l'arrêt figeait la phase et le scoreur ne pouvait **ni finir ni rectifier** le
quart en cours. Deux CA violés d'un coup : « personne n'est coupé en plein tir » — qui ne vaut pas que
pour la portée départ — et « la correction reste possible ». La justification d'alors était fausse en
plus d'être trop large (« les duels n'ont aucun chemin de correction ») : `saisir_manche` se documente
« Saisit **ou réédite** une manche ». Relevé par l'axe adversarial.

⚠️ **Cinq chemins d'écriture, pas deux — et c'était le second bloquant de l'US.** Le gel et le
déclencheur n'étaient posés que sur la qualification et l'élimination directe. `ServicePoules.valider`,
`ServiceSuisse.valider` et `ServiceBigShootOff.valider_manche` sont trois écritures à part entière :
un arrêt programmé sur une phase de poules ou de suisse ne se déclenchait donc **jamais** (ces phases
tournent seules, aucune validation n'atteignait le déclencheur), et une phase mise en pause y restait
entièrement saisissable — l'archer lisait « en attente » pendant que le scoreur écrivait. C'est le
défaut que `DETTE-073` constate à la maille tournoi, reproduit sur trois formats **en écrivant ici
qu'il est refermé**. Relevé par les quatre axes.

Pour éviter cinq copies du même trio, `application/gel_de_pause.py` — module **neutre**, sans
dépendance de service — porte le port `EvaluateurArrets`, le collaborateur `DeclencheurArrets` et la
garde `refuser_si_en_pause`. Le patron existait déjà dans le dépôt (`application/prelevement.py`
héberge `LecteurPopulationPhase`, port à deux consommateurs, exactement pour éviter qu'un service de
saisie importe l'autre).

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

⚠️ **Le déclencheur sort AVANT la lecture lourde quand il n'y a rien à faire**, et c'est un correctif
de revue (axe adversarial). Il payait la recomposition intégrale du créneau — engagés, projection,
reconstruction de chaque tableau, `etat()` de chaque phase déroulée — **avant** de savoir s'il existe
un seul arrêt programmé. Cela contredisait à la lettre la promesse « une phase sans arrêt se comporte
exactement comme avant » : le comportement fonctionnel était bien identique, le **coût** ne l'était
pas. Aggravant, et c'est ce qui rend la garde non négociable : `evaluer` est appelé **depuis une
commande de la file d'écriture**, donc cette lecture occupait le **writer unique** qui sérialise toutes
les écritures de l'application (règle 7 : « pas de logique métier longue »). Deux requêtes légères — le
déroulé du tournoi, les franchissements du créneau — remplacent désormais la recomposition dans le cas
normal du dépôt, qui est « aucun arrêt nulle part ».

⚠️ **La résolution des arrêts armés boucle, et la boucle est bornée.** Mettre une phase en pause peut
**débloquer** un arrêt armé qui l'attendait : deux arrêts de portée départ dus au même appel
s'attendaient mutuellement et restaient tous deux `ARME` — donc absents de la liste de relance, donc la
salle arrêtée **sans aucun bouton pour la repartir**. Une seule passe ne suffit pas, l'ordre
d'itération décidant qui voit quoi. La borne est le nombre de phases : chaque tour supplémentaire met
au moins une phase en pause.

⚠️ **Le statut d'une phase est relu au dépôt, jamais lu dans un cliché.** `evaluer` prend son cliché
une fois, mais la première passe **change des statuts en base** avant que la seconde ne les relise :
une phase mise en pause par un arrêt de départ y apparaissait encore `EN_COURS`, et si elle portait son
propre arrêt dû au même tour, `mettre_en_pause` levait `TransitionStatutInvalide`. Ce que ça coûtait est
pire que l'exception : elle était **avalée** par le rattrapage du signalement et **abandonnait la
boucle**, si bien que l'arrêt non tracé se redéclenchait à la relance — « l'organisateur perd la main »,
que tout cet ADR est construit pour empêcher. Le cliché est aussi **rafraîchi** : relire ne suffit pas
si l'appelant continue de décider sur du périmé.

Une exception levée par le déclencheur **ne remonte pas au scoreur** : la validation, elle, a réussi et
est persistée. La laisser remonter rendrait un 500 à un archer qui a bien tiré, qui ressaisirait alors
une volée déjà enregistrée. On journalise ; la validation suivante réévaluera.

### 8. Un arrêt ne se pose que sur un type dont l'application **lit** le tour

Quatre types : élimination directe, poules, système suisse, Big Shoot Off (`TYPES_DEROULES`,
ADR-0083). Partout ailleurs — qualification, échauffement, barrage, placement, colline — l'agrégat
**refuse** l'arrêt (`ArretProgrammeInvalide`, 422) et l'écran ne l'offre pas, en disant pourquoi.

Le déclencheur ne coupe qu'à une frontière de tour **observée** : il demande le tour courant au
service qui déroule la phase. Un type qu'aucun service ne déroule n'a aucun tour à observer, et un
arrêt posé dessus serait **accepté à l'atelier puis définitivement inerte le jour J** —
l'organisateur découvrirait le jour de la compétition que sa pause repas n'a jamais eu lieu. C'est
exactement le mode de panne que `DETTE-028` nomme (« six moteurs livrés, aucun appelé »), et un refus
explicite vaut mieux qu'un réglage inerte.

⚠️ **La qualification a été dans le périmètre pendant toute l'implémentation, avec un réglage
« découper en x tours ». Elle en est sortie en fin de revue, sur arbitrage du commanditaire du
19/08/2026.** La raison n'est pas un renoncement au besoin mais un **budget de tranche** : dériver le
tour d'une qualification demande de résoudre sa **population réelle** — deux qualifications peuvent
coexister dans un créneau (la « fourche », ADR-0082), donc « les archers de cette phase » n'est pas
« les inscrits du créneau » —, puis le **plan de cibles** et les **forfaits**. Trois sujets que la
tranche n'avait pas budgétés, et qui ont produit à eux seuls quatre des six bloquants de la seconde
passe de revue. `E05US034` les reprend avec son budget propre.

⚠️ **Le jour où `E05US034` branchera le lecteur de la qualification, DEUX choses devront bouger
ensemble** : la table de refus (`TYPES_DEROULES` côté `EtapeDeroule`, `TYPES_ARRETABLES` côté front)
et le registre d'avancement du suivi. `tests/test_arrets_api.py` porte les deux oracles en vis-à-vis,
de sorte qu'ils tombent ensemble : c'est tout l'intérêt de les avoir écrits tous les deux.

⚠️ **Ce que la première rédaction affirmait, pour mémoire.** Elle promettait un découpage « lu par un
lecteur d'avancement » alors que `unite_de_tour_effective` n'avait **aucun appelant de production** :
le réglage était écrit, validé, sérialisé, exposé en DTO, éditable dans deux écrans — et inerte. Le
mode de panne `DETTE-028` reproduit dans l'US qui le cite en garde-fou, relevé par les quatre axes de
revue. Le remède livré a d'abord été un lecteur de qualification ; c'est en l'écrivant que les trois
dépendances non budgétées sont apparues, et c'est ce constat qui a motivé l'arbitrage.

## Conséquences

**Ce qui devient vrai.**

- Une phase sans arrêt programmé se comporte **exactement** comme avant : aucune phase en cours le jour
  du déploiement ne change de comportement. Une base non migrée relit `arrets` absent comme « aucun
  arrêt ». C'est ce qui rend la livraison sûre.
- Mettre une phase en pause **arrête réellement le tir**, à la main comme par arrêt programmé. Le
  bouton de pause manuelle d'une phase cesse d'être décoratif — sa docstring devient vraie.
- Un tournoi capturé en format **conserve** ses pauses : `ModelePhase` porte le champ. Son absence
  aurait rejoué le défaut de `barrage_jusqu_au`, que le dépôt a déjà payé une fois.

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
- `DETTE-064` n'est **pas** élargie, et c'est un effet du périmètre final : les arrêts ne se
  recopient pas sur `Phase`, donc les helpers de décor `poser_phase_factice` / `poser_phase_sql` n'ont
  aucun champ de plus à recopier. Le piège reste entier pour les quatre réglages qui, eux, descendent
  dans le créneau.
- `DETTE-054` est **élargie d'une paire** : `ArretProgrammeDTO` est dupliqué entre `api/v1/phases.py`
  et `api/v1/formats.py`, comme ses quatre voisins. Une paire, et non deux — le DTO de découpage a
  disparu avec le réglage.
- Plusieurs arrêts dus au même instant (l'avancement a sauté des tours entre deux évaluations) ne
  produisent qu'**une** pause : le plus ancien est crédité, les autres sont consommés et journalisés.
  Les laisser en attente les ferait se déclencher l'un après l'autre à chaque reprise, obligeant à
  relancer trois fois pour une seule coupe. Rendre ce cas **visible** relève d'`E05US034`.

## Porté dans le code par

⚠️ Section écrite en **vérifiant dans le code du jour**, pas en déduisant de la décision.

⚠️ **Trois lignes de la première rédaction affirmaient plus que ce que le code portait**, et une
colonne « Vérifié : oui » se lit comme une preuve — c'est pire qu'une absence. Les axes C2 et
adversarial les ont recoupées une à une : §8 nommait `unite_de_tour_effective`, qui n'avait aucun
appelant ; §7 disait « branchement au composition root » là où deux services sur cinq l'étaient ; §6
promettait un refus que trois formats n'appliquaient pas. C'est le défaut d'ADR-0017 — « nommer un
module vide » — et le tableau ci-dessous a été refait **après** correction du code, module par module.

| Décision | Module qui l'applique | Vérifié |
|---|---|---|
| §1 arrêt après un tour, invariants | `backend/domain/arret_programme.py` (`ArretProgramme`, `verifier_arrets`, `arrets_atteints`) | oui — `tests/test_domain_arret_programme.py` |
| §2 définition sur l'étape | `backend/domain/deroule_etape.py` (`EtapeDeroule.arrets`, `_verifier_arrets_applicables`) ; JSON dans `backend/infrastructure/db/repositories/moteur.py` (`_politiques_json`, `_lire_arrets`) | oui — round-trip par l'API dans `tests/test_arrets_api.py` |
| §2 pas de miroir sur `Phase` | `backend/domain/deroule_etape.py` (`EtapeDeroule.instancier`, qui n'y recopie **aucun** des deux champs) | oui — `Phase` ne porte ni les arrêts ni leur franchissement, et le type front l'exclut (`Omit<…, 'arrets'>`) |
| §2 conservation à la promotion | `backend/domain/format_tournoi.py` (`ModelePhase.arrets`, `pour_tournoi`, `d_etape`) | oui |
| §3 franchissement persisté, cycle monotone | `backend/domain/arret_programme.py` (`FranchissementArret`, `EtatFranchissement`) ; `backend/infrastructure/db/models.py` (`FranchissementArretORM`) ; `migrations/versions/0048_franchissement_arret.py` | oui — aller-retour et unicité dans `tests/test_arrets_api.py` |
| §4 chaque phase finit son tour | `backend/domain/arret_programme.py` (`phases_a_arreter`) ; `backend/application/arrets_programmes.py` (`_armer_sur_le_depart`, `_resoudre_les_arrets_armes`, `_avancement_connu`) | oui — dont l'oracle « une phase au tour inconnu n'est pas coupée » |
| §5 reprise d'un seul geste | `backend/application/arrets_programmes.py` (`lever`) ; `backend/api/v1/phases.py` (`relancer_arret`) ; `frontend/src/features/suivi-deroule/PilotageCreneau.tsx` (`RelanceDesArrets`) | oui — 404 sur arrêt armé / déjà levé, testé |
| §6 gel de la saisie, **les cinq chemins** | `backend/application/gel_de_pause.py` (`refuser_si_en_pause`), appelé par `backend/application/saisie.py`, `backend/application/saisie_duels.py`, `backend/application/poules.py`, `backend/application/suisse.py`, `backend/application/big_shoot_off.py` | oui — les cinq appels comptés à la main ; **un oracle par format**, ajouté en 2ᵉ passe : trois manquaient, et c'est ce qui avait laissé la garde du Big Shoot Off se poser dans `projection()` — une **lecture** — sans que rien ne rougisse |
| §6 correction et rencontre engagée non gelées | `backend/application/saisie.py` (`corriger_volee`, **sans** garde) ; `saisie_duels.py`, `poules.py`, `suisse.py` (`saisir_manche`, `saisir_barrage`, **sans** garde) ; `big_shoot_off.py` (`projection`, `etat` : des lectures) | oui — six oracles de **non-garde**, dont « le tableau reste lisible » et « la projection reste consultable pendant la pause » |
| §6 gel du routage | `backend/application/routage.py` (`_en_pause`, aux **deux** résolutions de `routage()` ; `affectations()` porte un commentaire disant pourquoi elle n'est pas gardée) | oui — trois oracles dans `tests/test_service_routage.py` |
| §7 déclencheur idempotent, garde bon marché | `backend/application/arrets_programmes.py` (`evaluer`) ; couture `backend/application/suivi_deroule.py` (`avancement_par_phase`) | oui — dont « sans arrêt, l'avancement n'est même pas lu » |
| §7 branchement des **cinq** services | `backend/bootstrap/composition.py` (une boucle nommant les cinq) | oui — `tests/test_arrets_api.py` assère les cinq, et **rien d'autre** ne le ferait |
| §8 arrêt refusé hors des types déroulés | `backend/domain/deroule_etape.py` (`_verifier_arrets_applicables`, garde sur `TYPES_DEROULES`) ; front : `frontend/src/shared/phases/catalogue.ts` (`TYPES_ARRETABLES`), consommé par les deux éditeurs | oui — la garde vit sur l'**étape** et non sur `Phase` seule, sans quoi `ServicePhases.modifier` persistait l'arrêt et rendait le créneau illisible ; testée par l'API et par `frontend/src/features/phases/Arrets.test.tsx` |
| §8 le registre d'avancement est **inchangé** | `backend/bootstrap/composition.py` (trois branchements, ceux d'E05US032) | oui — `tests/test_arrets_api.py` assère que **ni** la qualification **ni** l'échauffement n'y sont, en vis-à-vis du refus ci-dessus |
| §7 une phase dont tout est tiré n'est pas mise en pause | `backend/application/arrets_programmes.py` (`_appliquer`, branche « plus rien en cours ») | oui — l'arrêt est consommé et journalisé comme un **manqué** ; sans cela la phase était figée alors qu'il ne restait rien à interrompre, et il fallait la relancer pour la clôturer |
| Atelier (les deux éditeurs) | `frontend/src/shared/phases/ReglageArrets.tsx` + `frontend/src/shared/phases/arrets.ts`, montés par `frontend/src/features/phases/Phases.tsx` et `frontend/src/features/deroule/Deroule.tsx` (dont `ReglageBarrage`, qui réémet le planning) | oui — `frontend/src/features/phases/Arrets.test.tsx` garde le `PUT` total : 3ᵉ occurrence de ce défaut sur ce formulaire, et la première à être figée par un test |
| Pilotage (relance, et son rafraîchissement) | `frontend/src/features/suivi-deroule/{PilotageCreneau.tsx,hooks.ts}` (invalide suivi **et** avancement, poll sur la liste de phases) | oui |
