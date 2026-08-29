# ADR-0096 — Un jalon énumère ses gardes au lieu de les lever, et les quatre « prêt à… » partagent une forme

- **Statut** : Accepté
- **Date** : 2026-08-23
- **US** : E16US012
- **Décideurs** : Organisateur / Architecte
- **S'appuie sur** :
  - [ADR-0026](0026-cycle-de-vie-du-tournoi-sept-statuts.md) §2 — la machine à états et ses gardes ;
    c'est elle que les jalons **lisent**, et qu'ils ne redoublent jamais
  - [ADR-0058](0058-decoupage-de-l-admin-en-trois-axes-d-activite.md) — les trois axes d'activité,
    que la famille traverse (§4)
  - [ADR-0069](0069-effectif-minimum-deduit-et-exige.md) — le contrôle d'effectif remonté au
    lancement, dont cet ADR généralise la leçon (§1)
- **Voisin** : [ADR-0073](0073-pas-de-tir-groupe-de-cibles-couloir-de-tir-place-d-archer.md) —
  même famille de défaut : deux écrans voisins qui divergent finissent par dire deux choses

> ⚠️ **Cet ADR ne figure pas à la liste nominative d'[ADR-0075 § « Portée de la règle »](0075-le-depart-est-la-portee-sportive.md#portée-de-la-règle--porté-dans-le-code-par--tranchée-le-08082026), et c'est volontaire.**
> Il est de **navigation et d'IHM** : le moteur sportif ne lit aucun jalon, aucune portée ne change,
> aucune politique injectable n'est en jeu. Le critère de `CLAUDE.md` exclut nommément les ADR d'UI ;
> les précédents existent (`0086`, `0088`, `0095`). Il porte en revanche sa section « Porté dans le
> code par », exigée de **tout ADR neuf** sans condition.
>
> *(Noté explicitement, sur le précédent d'ADR-0095 : cette liste documente quatre omissions
> consécutives, et un trou **non commenté** est précisément ce qui produit la suivante.)*

## Contexte

Le questionnaire de maquettes du 04/08/2026 avait fait naître E16US003 — l'écran de complétude,
refusé parce qu'il mélangeait le déroulé et l'administratif. Interrogé sur le seul **libellé** de cet
écran, le commanditaire a répondu plus large :

> « je viserais plus 2 notions : prêt à démarrer, prêt à terminer, et prêt à archiver, prêt à
> exporter »

E16US003 n'a livré **qu'un** membre — « Prêt à terminer ? » — et a explicitement refusé d'improviser
les autres. La fiche E16US012 a été ouverte pour instruire la famille, avec une consigne d'ordre :
**avant** `E16US007` (exports) et `E16US008` (feu vert), sans quoi chacune figerait sa propre
variante dans son coin.

### Le vrai problème, découvert en instruisant

La fiche parlait de navigation. En vérifiant dans le code, le défaut s'est révélé plus profond, et
il n'est pas cosmétique : **les gardes du cycle de vie ne sont lisibles qu'en échouant.**

| Garde | Où elle vit | Comment on l'apprend aujourd'hui |
|---|---|---|
| « au moins un créneau » (E02US010) | `ServiceTournois.vers_pret` | `TournoiSansDepart` → 409, **au clic** |
| « assez d'inscrits » (E05US021) | `ServiceTournois.demarrer` | `EffectifInsuffisantPourDemarrer` → 409, **au clic** |
| « le tournoi est-il dans l'état d'où l'on part ? » (ADR-0026 §2) | `ServiceTournois.vers_pret`, `demarrer`, `terminer`, `archiver`… | `TransitionStatutInvalide` → 409, **au clic** |

⚠️ **La troisième ligne a été ajoutée en revue, et son oubli n'était pas anodin.** La première
version de ce tableau — donc de l'implémentation qu'il décrit — ne comptait que **deux** gardes. Or
la garde de statut est la seule **universelle** : `ServiceTournois` la lève *avant* toutes les
autres. Trois conséquences, toutes vérifiées dans le code livré et toutes corrigées depuis :

1. `/jalons/demarrer` répondait `pret: true` sur un tournoi **déjà en cours**, alors que `demarrer`
   y lève à coup sûr. Seul le front masquait le mensonge, en n'affichant plus l'écran ;
2. `evaluer_terminer` documentait « terminer n'a **aucune** garde dure » et posait `bloquant=false`
   sur cette base. Faux : `terminer` n'accepte que `EN_COURS`, donc un tournoi **en pause** (la
   pause déjeuner du jour J) s'entendait dire « rien ne vous en empêchera » juste avant un 409 ;
3. surtout, **`ARCHIVER` — le membre que cet ADR promet de laisser « se brancher » — n'a QUE cette
   garde.** Sans elle, la forme livrée ne lui offrait rien à énumérer : liste vide et `pret` toujours
   vrai, c'est-à-dire exactement le « 200 rassurant et faux » que le §5 interdit par ailleurs.

C'est le mode de défaillance qu'ADR-0017 avait produit treize mois durant : une décision juste,
portée à moitié, et rien pour le signaler.

Une exception ne rend **qu'un** manquement : le premier rencontré. L'organisateur ajoute un créneau,
reclique, découvre alors l'effectif. Le jour J, devant la salle, ce sont deux allers-retours dont le
second était connu depuis le début.

C'est la même leçon qu'ADR-0069, un cran plus haut. ADR-0069 avait déjà remonté un contrôle *de la
compétition vers le lancement*, parce qu'un refus arrivé trop tard n'est plus actionnable. Ici le
contrôle est au bon moment, mais sous la **mauvaise forme** : une exception est un verdict, pas un
état consultable.

### La question qui commandait le découpage

« 2 notions » puis quatre membres cités : la fiche notait que savoir s'il en visait quatre écrans,
deux, ou une forme unique paramétrée était **la** question de cadrage. Posée le 23/08/2026, elle a
été tranchée : **une forme unique paramétrée**.

## Décision

### §1 — Un jalon est un état consultable, pas une exception

Une **préparation à un jalon** (`PreparationJalon`) énumère ce que les gardes vérifient, **sans les
exécuter** : une liste d'états (`D-17` : jamais une barre de progression) et une réponse binaire.
Tout ce qui manque se lit d'un coup.

Les gardes ne sont **pas réécrites** — c'est le CA « sans doublonner ce qui existe ». L'effectif
affiché avant le clic sort de `ServiceTournois.exigence_effectif`, **la méthode que la garde exécute
elle-même** ; les créneaux du **même** `DepartRepository.par_tournoi` ; « prêt à terminer » relit
`ServiceCompletude` sans y toucher.

Là où le partage mécanique s'arrête — le jalon traduit « aucun créneau » en `EN_ATTENTE`, la garde
le traduit en `TournoiSansDepart` —, l'accord est **épinglé par un test de cohérence** qui exerce
les deux versants sur les mêmes dépôts. C'est le patron déjà employé entre `domain.tournoi._TRANSITIONS`
et la légalité effective du service : quand on ne peut pas partager le calcul, on interdit la dérive
par un test, jamais par la vigilance.

### §2 — Une forme unique paramétrée par le membre, pas quatre écrans jumeaux

Un seul type de réponse, une seule route (`GET /api/v1/tournois/{id}/jalons/{jalon}`), une seule
coquille front (`PretA`). La **question** elle-même se dérive du membre (« Prêt à `<verbe>` ? »)
côté serveur : le front ne tient aucune table de libellés, qui divergerait au premier membre ajouté.

> **Amendement du 29/08/2026 (E16US010).** La famille a désormais **deux contrats**, et c'est
> délibéré : à la **préparation d'un tournoi** (ci-dessus) s'ajoute l'**aperçu de la collection**
> — `GET /api/v1/jalons/{jalon}/apercus`, qui rend un `ApercuJalonReponse` par tournoi
> (`tournoi_id`, `niveau`, `resume`). Ce n'est pas une `PreparationJalonReponse` allégée : une
> **liste rend une pastille, pas un écran**, et lui servir des `lignes` l'obligerait à les masquer.
> Ce que la forme unique continue de garantir est ce qu'elle a toujours garanti — **le membre
> `Jalon` et la question** sont uniques et dérivés côté serveur ; c'est le *rendu* qui se décline.
> ⚠️ L'aperçu vit **hors** du préfixe `/api/v1/tournois` : sous ce préfixe, le segment `jalons`
> était appariable comme identifiant de tournoi, et seule la méthode HTTP séparait les deux
> (démontré en revue d'E16US010). ⚠️ Seul `DEMARRER` a un aperçu ; les autres répondent `404`
> `jalon_non_instruit`, comme `ARCHIVER` et `EXPORTER` pour l'écran.

**Ce que la forme unifie, et ce qu'elle ne fusionne pas.** Elle unifie la *réponse* et la *question*,
pas les *règles* : chaque membre a ses propres entrées, donc sa propre politique pure. Fusionner les
règles dans une fonction unique aurait demandé l'union de toutes leurs entrées — et aurait
reconstruit, à l'intérieur, les quatre variantes qu'on cherche à éviter.

### §3 — *Ce qui manque* et *ce qui bloque* sont deux choses distinctes

`pret` n'est **pas** « toutes les lignes vertes ». Une ligne dit ce qui manque ; `pret` dit si
l'action passera. Les deux se séparent parce que `D-15` (« l'appli n'empêche pas, elle avertit »)
autorise des manquements qui ne bloquent pas : un tournoi **sans déroulé composé démarre**
aujourd'hui, et l'écran doit le dire sans le refuser. Les confondre ferait dire à l'écran « vous ne
pouvez pas » là où le serveur accepte — un écran plus sévère que le produit.

D'où un second drapeau, `bloquant`, qui porte **l'asymétrie de la famille** : *démarrer* a des
gardes dures, *terminer* n'en a aucune (`sportif_complet` choisit le libellé de la confirmation, il
ne garde rien — E12US005). Sans lui, la forme unique dirait la même chose des deux, donc serait
fausse sur l'un des deux.

⚠️ **Aucun bouton n'est jamais désactivé sur la foi de ces champs.** E05US021 avait déjà tranché
pour le démarrage : l'avertissement se lit avant le clic, le refus remonte du serveur. Un front qui
grise le bouton se met à décider d'une garde — et redevient la seconde source que le CA interdit.

### §4 — Les quatre membres ne sont pas de même nature, et la famille n'est pas la machine à états

`DEMARRER`, `TERMINER` et `ARCHIVER` gardent une **transition** du cycle de vie (ADR-0026 §2) ;
`EXPORTER` garde un **geste répétable**, qui ne fait franchir aucun statut. La fiche présentait les
quatre comme homogènes ; ils ne le sont pas.

Ce qu'ils partagent n'est donc **pas** la machine à états — c'est la *question posée à
l'organisateur*. C'est ce qui rend la famille légitime malgré l'hétérogénéité, et ce qui l'autorise
à traverser deux axes d'ADR-0058 (démarrer/terminer en **pilotage**, archiver/exporter en
**gestion**) sans les contredire : un jalon ne déménage aucune activité, il pose une question à
l'endroit où l'activité se fait déjà.

### §5 — Un membre non instruit le dit, il ne rend pas une réponse vide

`ARCHIVER` et `EXPORTER` existent dans l'énumération (la forme est posée, la question se dérive) mais
n'ont aucune règle : le serveur répond **404** (`jalon_non_instruit`). Un `200` à liste vide se lirait
« rien ne manque, vous pouvez exporter » — exactement le mensonge que la famille supprime. C'est la
couture où `E16US007` et l'US d'archivage se brancheront.

## Conséquences

**Ce que l'organisateur gagne.** Un écran « Prêt à démarrer ? » qui liste les deux gardes du feu vert
avant le clic, au lieu de les découvrir une par une en échouant. Et un verdict écrit en tête des deux
écrans : la liste dit *pourquoi*, la phrase répond *tout de suite*.

**Ce que les deux US en aval gagnent.** `E16US007` et `E16US008` n'ont plus de forme à inventer : la
route, le DTO, la coquille et le vocabulaire existent. C'était la raison d'ordre inscrite au tracker,
et elle est honorée.

**Ce que ça coûte.** Un service et une route de plus pour une information qui, pour *terminer*,
existait déjà sous un autre chemin (`/completude`). L'écran « Prêt à terminer ? » **continue de lire
`/completude`** — les deux rendent la même chose, mais sa confirmation a besoin en plus du volet
administratif pour chiffrer les impayés, et basculer sa liste sur le jalon aurait ajouté un **second
poll de 5 s par tablette** pour une réponse identique. ⚠️ **Cet argument a été revu** : `hors_sportif`
n'est lu, dans cet écran, que par le dialogue de confirmation — la migration est donc possible sans
second poll, cf. `DETTE-084` § Résorption. Que les deux ne divergent pas n'est pas laissé
à la vigilance : `test_jalons_api.py` épingle `/jalons/terminer` ≡ `/completude.sportif` — **sur un
tournoi en cours**, seule fenêtre où terminer est offert (cf. la garde de statut ci-dessus). Le
membre `terminer` du jalon n'a donc **aucun client front aujourd'hui** : il existe pour la forme,
pour l'épinglage, et comme couture du jour où l'écran migrera. C'est un choix relu, pas un oubli.

⚠️ **Ce choix a un prix, et il faut le nommer** : puisque `Completude.tsx` ne lit pas le jalon, c'est
**lui** qui doit redéduire la garde de statut (`questionPosee={enCours}`), là où `PretADemarrer` n'en
déduit plus aucune. C'est la seule déduction de garde qui subsiste côté front, et elle est le miroir
explicite d'`evaluer_terminer`, épinglé des deux côtés. La 2ᵉ passe de revue a montré ce que coûte
d'oublier ce miroir : l'écran a affiché « l'application ne vous en empêchera pas » sur un tournoi en
pause pendant tout le temps où le domaine, lui, était déjà corrigé.

⚠️ **Une asymétrie assumée entre les deux membres, et il faut la dire** : `evaluer_demarrer` vide
ses lignes quand la transition n'est plus offerte, `evaluer_terminer` **garde les siennes**. Ce n'est
pas une incohérence de la « forme unique » : chez *démarrer*, la liste **est** la préparation (plus
rien à préparer ⇒ rien à lister) ; chez *terminer*, elle **est l'état sportif**, qui existe à tout
statut et que l'organisateur vient précisément consulter pendant la pause. La garde de statut y est
portée par `pret`, `bloquant` et `detail`. *(Tranché en 5ᵉ passe de revue : la vider avait été une
sur-correction, et elle rendait la résorption de `DETTE-084` régressive.)*

**Aucune migration.** Tout est de la lecture dérivée : rien n'est persisté.

**Question laissée ouverte, et c'est délibéré.** Démarrer un tournoi **sans déroulé composé** reste
permis (le service l'autorise, la ligne n'est qu'un avertissement). Est-ce *souhaitable* ? C'est un
arbitrage métier, pas une conséquence de cet ADR : le durcir ici aurait changé une règle de
lancement sous couvert d'une US de navigation. Le test
`test_un_deroule_vide_ne_bloque_ni_le_jalon_ni_la_garde` **tombera** si la garde durcit un jour —
c'est voulu, la décision doit être prise, pas subie.

**Angle mort assumé.** La frise du cycle de vie (E14US001) porte toujours ses propres boutons
« Démarrer » / « Terminer » sur l'accueil admin. Elle n'est pas en contradiction — elle lit la même
topologie serveur — mais l'organisateur dispose désormais de **deux** endroits pour démarrer un
tournoi : la frise (action nue) et le jalon (action expliquée). Les fondre relèverait de la refonte
de navigation complète que la fiche annonçait ; ce n'est pas fait ici, et c'est à instruire quand
`ARCHIVER` rejoindra la famille — c'est là que la question se posera pour de bon, la frise portant
aussi ce bouton. ⚠️ **Inscrit au registre en revue** (`DETTE-082`) : un angle mort qui ne vit que
dans une section *Conséquences* n'apparaît à aucun tri de dette, donc n'est jamais repris. La règle
du projet demande la ligne **plus** le marqueur à l'endroit du raccourci ; ils y sont désormais.

**Une dette de conception livrée avec, et tracée elle aussi** (`DETTE-083`) : la coquille commune
`jalons/PretA` importe `completude/SectionCompletude`, pendant que `completude/Completude` importe
la coquille — un **cycle d'imports** entre deux features, que l'atlas de ce dépôt signale. La sortir
suppose de remonter `SectionCompletude`, `LigneCompletude`, `afficheEtat` et `detailLigne` dans
`shared/`, soit un rangement transverse qui n'a rien à faire dans une branche fonctionnelle
(règle 16 : un remède structurel se traite en US dédiée, jamais en douce). Le registre porte le
constat et le remède.

## Porté dans le code par

⚠️ Section écrite en **vérifiant dans le code du jour**, pas en déduisant de la décision.

| Décision | Module qui l'applique | Vérifié |
|---|---|---|
| §1 — un jalon est un état consultable | `backend/domain/jalon.py` (`PreparationJalon`, `evaluer_demarrer`, `evaluer_terminer`) | oui |
| §1 — les gardes ne sont pas réécrites : le **verdict** vient de la méthode que la garde exécute | `backend/application/jalons.py` (`ServiceJalons._demarrer` passe `exigence.suffisant` — le champ exact que `_exiger_un_effectif_suffisant` lit — et non `inscrits`/`minimum` à recomparer) · `backend/domain/jalon.py` (`evaluer_demarrer(effectif_suffisant=…)`) — gardé par `backend/tests/test_domain_jalon.py` (`test_l_effectif_suit_le_verdict_de_la_garde_et_ne_le_recalcule_pas`) | oui — ⚠️ **corrigé en revue** : la 1ʳᵉ version recomparait `inscrits >= minimum` au domaine. Vrai ce jour-là, faux au premier assouplissement de `exigence_effectif`, et **invisible aux tests** puisque les deux formules coïncidaient |
| §1 — l'accord jalon ↔ garde est épinglé, pas espéré | `backend/tests/test_service_jalons.py`, section « Cohérence jalon ↔ garde » — les mêmes dépôts des deux côtés, **dans les deux sens**, et depuis la revue : le **multi-créneaux** (`test_le_jalon_chiffre_l_effectif_du_creneau_le_moins_garni`, la règle d'ADR-0075 qui n'était pas exercée), la **borne d'égalité** `inscrits == minimum`, et la **garde de statut** (`test_un_tournoi_deja_lance_n_annonce_pas_qu_il_peut_demarrer`) | oui — la 1ʳᵉ version n'avait qu'**un** créneau et ne quittait jamais `brouillon → prêt → en cours` |
| §1 — le sens **inverse** (jalon optimiste ↔ serveur qui refuse) est gardé lui aussi | `backend/tests/test_service_jalons.py` (`test_quand_le_jalon_dit_pret_les_deux_gardes_laissent_passer`) | oui — c'est le sens qui coûte le plus cher s'il casse |
| §2 — un membre et une question uniques, **deux** rendus | `backend/api/v1/jalons.py` — `GET /api/v1/tournois/{id}/jalons/{jalon}` (préparation, `PreparationJalonReponse`) **et** `GET /api/v1/jalons/{jalon}/apercus` (collection, `ApercuJalonReponse`, E16US010) ; `jalon: Jalon` en segment dans les deux | oui — ⚠️ **amendé le 29/08/2026** : la ligne disait « une route unique paramétrée » et est restée vraie **un jour de trop**, E16US010 ayant ajouté le second contrat sans rouvrir cet ADR (relevé par l'axe A) |
| §2 — la question se dérive du membre, côté serveur **et le front la consomme** | `frontend/src/features/jalons/PretADemarrer.tsx` (`question={preparation.data?.question ?? …}`) · `backend/domain/jalon.py` (`question`, `_VERBE`) · `backend/api/v1/jalons.py` (`PreparationJalonReponse.question`) — gardé par `backend/tests/test_domain_jalon.py` (`test_chaque_membre_pose_sa_question_sous_la_meme_forme`) ⚠️ **une réserve** : `Completude.tsx` garde son libellé en dur, parce qu'il lit `/completude` et non `/jalons/terminer` (cf. § Conséquences) — la dérivation vaut donc pour tout membre qui consomme la route | oui |
| §2 — une coquille front unique, montée par les **deux** membres livrés | `frontend/src/features/jalons/PretA.tsx`, montée par `frontend/src/features/jalons/PretADemarrer.tsx` **et** `frontend/src/features/completude/Completude.tsx` | oui — deux occurrences réelles, pas une abstraction sur pari |
| §2 — le DTO de ligne est **réutilisé**, pas recopié | `backend/api/v1/jalons.py` importe `LigneCompletudeReponse` de `api/v1/completude.py` | oui |
| §3 — `pret` ≠ « toutes les lignes vertes » | `backend/domain/jalon.py` (`evaluer_demarrer` : `pret=` ne retient que le statut, les créneaux et l'effectif — jamais le déroulé) — gardé par `test_un_deroule_vide_est_signale_mais_ne_retient_pas_le_depart` (`backend/tests/test_domain_jalon.py`) | oui |
| §3 — `bloquant` porte l'asymétrie | `backend/domain/jalon.py` (`bloquant=True` / `False`) · `frontend/src/features/jalons/presentation.ts` (`verdict`, **trois** cas) | oui |
| §3 — aucun bouton n'est grisé par un manque | `frontend/src/features/jalons/PretADemarrer.tsx` (`disabled` sur la seule mutation en cours) — gardé par `PretADemarrer.test.tsx` (`le bouton reste cliquable même quand rien n'est prêt`) | oui |
| §3 — l'écran *terminer* reste du bon côté de l'asymétrie | `frontend/src/features/completude/Completude.tsx` (`bloquant={false}` : terminer n'a aucune garde de **contenu**) — gardé par `Completude.test.tsx` (`le verdict avertit sans annoncer de refus`) ⚠️ une **inversion** ne se verrait que là, le typage n'en dit rien | oui — ⚠️ la ligne a porté successivement `bloquant={false}` (juste, mais pour la mauvaise raison : il manquait la garde de statut), puis `bloquant={!enCours}` (inerte), et de nouveau `bloquant={false}` — la garde de statut étant désormais portée par `questionPosee`, ligne ci-dessous |
| §4 — l'action offerte est lue du serveur, jamais déduite du statut | `frontend/src/features/jalons/PretADemarrer.tsx` (`useTransitions` + `VERS_LE_DEPART`) — gardé par `PretADemarrer.test.tsx` (`porte l'action que le serveur offre`) | oui |
| §4 — la famille traverse les axes sans les contredire | `frontend/src/features/admin/axes.ts` (`pret-demarrer: 'pilotage'`, voisin de `completude`) — gardé par `axes.test.ts` (comptage exhaustif des destinations) | oui, pour les **deux** membres livrés |
| §3 — la **liste** et le **verdict** se gardent séparément | `frontend/src/features/jalons/PretA.tsx` (le verdict est gardé par `questionPosee` **et** par la présence de lignes ; la section ne dépend que des lignes) — gardé par `Completude.test.tsx` (`hors du tournoi en cours…` assère liste **présente** et verdict **absent**), filet vérifié par mutation | oui — ⚠️ les piloter par le même booléen a produit **deux défauts opposés** : un verdict qui accusait une liste verte (3ᵉ passe), puis la disparition d'un affichage livré — la liste sportive n'était plus visible pendant la pause déjeuner (4ᵉ passe, axe C1) |
| §3 — le badge « complet » de la section **n'est pas** `pret` | `frontend/src/features/jalons/PretA.tsx` (prop `complet` distincte, que l'écran *démarrer* n'utilise pas) · `frontend/src/features/completude/Completude.tsx` (`complet={sportif_complet}`, rendu inchangé) | oui — ⚠️ **corrigé en revue** : `complet={pret}` affichait « Avant de démarrer — complet » au-dessus d'une ligne « En attente » |
| §3 — le verdict dit **quand** le refus tombe | `backend/domain/jalon.py` (`_moment_du_refus`, dérivé de la garde qui bloque en premier) · `frontend/src/features/jalons/presentation.ts` (`verdict(pret, bloquant, moment)`) · `frontend/src/features/jalons/PretADemarrer.tsx` (`moment={preparation.data?.moment ?? null}`) — gardé par `backend/tests/test_domain_jalon.py` (`test_sans_creneau_le_refus_est_annonce_pour_le_passage_en_pret`) et `presentation.test.ts` | oui — ⚠️ **la ligne citait encore `moment="au démarrage"`**, le littéral que ce même tableau désigne ailleurs comme le défaut corrigé (3ᵉ passe, axes C2 et D) |
| §3 — la cause du blocage est **chiffrée**, avec la phrase du refus lui-même | `backend/application/jalons.py` (`cause_effectif=exigence.message_de_refus()`) · `backend/domain/jalon.py` (`PreparationJalon.detail`) · `frontend/src/features/jalons/PretA.tsx` | oui — ⚠️ **ajouté en revue** : « 8/34 » sans nommer le créneau contredit le total affiché ailleurs (`D-16` / `P-4`) |
| **la garde de statut** — commune aux trois membres qui gardent une transition | `backend/domain/jalon.py` (`transition_offerte`, `_TRANSITIONS_DU_JALON`) · `backend/application/jalons.py` (le tournoi relu une fois porte l'existence **et** le statut) — gardé par `backend/tests/test_service_jalons.py` (`test_le_jalon_terminer_suit_la_table_des_transitions_sur_tous_les_statuts`, qui confronte les deux versants sur les **sept** statuts) | oui — ⚠️ **absente de la 1ʳᵉ version** (c'est le bloquant de la 1ʳᵉ passe), puis **recopiée** de la table au lieu d'en être dérivée (2ᵉ passe, axes A et C2). Sans elle, `ARCHIVER` n'aurait rien à énumérer |
| **la phrase annoncée est celle du refus** — pour les trois gardes, pas seulement l'effectif | `backend/domain/tournoi.py` (`MESSAGE_SANS_DEPART`, `MESSAGE_TERMINER_HORS_EN_COURS`, consommées par `ServiceTournois` **et** par `domain/jalon.py`) — gardé par `backend/tests/test_service_jalons.py`, qui compare `preparation.detail` à `str(refus.value)` en **exécutant** la garde | oui — ⚠️ la 1ʳᵉ correction recopiait deux de ces phrases en littéral. **Une exception assumée**, écrite au contrat (`api/v1/jalons.py`) : la garde de **statut de *démarrer*** rédige une phrase par statut terminal (« annulé », « archivé », « déjà lancé ») là où le refus serveur n'en distingue aucun — c'est le seul endroit où le jalon dit **plus** que le refus, et non autre chose |
| **le moment du refus suit la garde qui bloque en premier** | `backend/domain/jalon.py` (`_moment_du_refus`) · `frontend/src/features/jalons/PretA.tsx` (`moment`) — gardé par `backend/tests/test_domain_jalon.py` (`test_sans_creneau_le_refus_est_annonce_pour_le_passage_en_pret`) | oui — ⚠️ le front l'écrivait en dur (« au démarrage »), donc **faux** pour la garde des créneaux, qui refuse dès « Marquer prêt » (2ᵉ passe, axe C1) |
| §3 — l'écran *terminer* porte lui aussi la garde de statut | `frontend/src/features/completude/Completude.tsx` (`questionPosee={enCours}` pour le verdict, `detail` pour la raison, `enCours` pour l'intro et le pied) — gardé par `Completude.test.tsx`, dont les trois gardes conditionnelles sont **vérifiées par mutation** | oui — ⚠️ la ligne a nommé successivement deux props **inertes** (`bloquant`, puis `pret`) : le seul cas où elles changeaient de valeur était celui où le verdict n'est pas rendu. Une prop qui ne peut plus être observée se lit comme une preuve et n'en est pas une |
| §3 — **`question_posee`** dit si la question a encore un objet | `backend/domain/jalon.py` (`PreparationJalon.question_posee`, renseigné par les deux membres) · `backend/api/v1/jalons.py` (champ du DTO) · `frontend/src/features/jalons/PretA.tsx` (prop `questionPosee`, **obligatoire** : `tsc` force chaque membre à trancher) — gardé par `backend/tests/test_domain_jalon.py` (les deux sens, sur les deux membres), `backend/tests/test_jalons_api.py` (au contrat), `backend/tests/test_service_jalons.py` (les sept statuts) et `Completude.test.tsx` — filets vérifiés par mutation | oui — ⚠️ **la ligne citait auparavant la convention « liste vide »**, et nommait `evaluer_terminer` comme la portant alors qu'il avait cessé de vider sa liste dans le commit même. Le signal machine avait disparu sans être remplacé — un écran neuf recopiant le patron aurait rétabli le bloquant de la 3ᵉ passe (6ᵉ passe, axes C1 et D) |
| §5 — un membre non instruit répond 404 | `backend/application/jalons.py` (`JalonNonInstruit`) · `backend/application/erreurs/referentiel.py` · `backend/api/erreurs.py` (chaîne `isinstance` du 404 — **le mapping est une liste écrite à la main**, cf. le précédent `MancheIntrouvable`) — gardé par `test_jalons_api.py` | oui |
