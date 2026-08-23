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
poll de 5 s par tablette** pour une réponse identique. Que les deux ne divergent pas n'est pas laissé
à la vigilance : `test_jalons_api.py` épingle `/jalons/terminer` ≡ `/completude.sportif`.

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
aussi ce bouton.

## Porté dans le code par

⚠️ Section écrite en **vérifiant dans le code du jour**, pas en déduisant de la décision.

| Décision | Module qui l'applique | Vérifié |
|---|---|---|
| §1 — un jalon est un état consultable | `backend/domain/jalon.py` (`PreparationJalon`, `evaluer_demarrer`, `evaluer_terminer`) | oui |
| §1 — les gardes ne sont pas réécrites : l'effectif vient de la méthode que la garde exécute | `backend/application/jalons.py` (`ServiceJalons._demarrer` → `LecteurExigenceEffectif.exigence_effectif`, réalisé par `ServiceTournois`) | oui |
| §1 — l'accord jalon ↔ garde est épinglé, pas espéré | `backend/tests/test_service_jalons.py` — les quatre cas de la section « Cohérence jalon ↔ garde », qui exercent les **mêmes dépôts** des deux côtés | oui |
| §1 — le sens **inverse** (jalon optimiste ↔ serveur qui refuse) est gardé lui aussi | `backend/tests/test_service_jalons.py` (`test_quand_le_jalon_dit_pret_les_deux_gardes_laissent_passer`) | oui — c'est le sens qui coûte le plus cher s'il casse |
| §2 — une route unique paramétrée | `backend/api/v1/jalons.py` (`GET /jalons/{jalon}`, `jalon: Jalon` en segment) | oui |
| §2 — la question se dérive du membre, côté serveur | `backend/domain/jalon.py` (`question`, `_VERBE`) · `backend/api/v1/jalons.py` (`PreparationJalonReponse.question`) — gardé par `backend/tests/test_domain_jalon.py` (`test_chaque_membre_pose_sa_question_sous_la_meme_forme`) | oui |
| §2 — une coquille front unique, montée par les **deux** membres livrés | `frontend/src/features/jalons/PretA.tsx`, montée par `PretADemarrer.tsx` **et** `completude/Completude.tsx` | oui — deux occurrences réelles, pas une abstraction sur pari |
| §2 — le DTO de ligne est **réutilisé**, pas recopié | `backend/api/v1/jalons.py` importe `LigneCompletudeReponse` de `api/v1/completude.py` | oui |
| §3 — `pret` ≠ « toutes les lignes vertes » | `backend/domain/jalon.py` (`evaluer_demarrer`, `pret=` ne retient que les deux gardes dures) — gardé par `test_un_deroule_vide_est_signale_mais_ne_retient_pas_le_depart` | oui |
| §3 — `bloquant` porte l'asymétrie | `backend/domain/jalon.py` (`bloquant=True` / `False`) · `frontend/src/features/jalons/presentation.ts` (`verdict`, **trois** cas) | oui |
| §3 — aucun bouton n'est grisé par un manque | `frontend/src/features/jalons/PretADemarrer.tsx` (`disabled` sur la seule mutation en cours) — gardé par `PretADemarrer.test.tsx` (`le bouton reste cliquable même quand rien n'est prêt`) | oui |
| §3 — l'écran *terminer* reste du bon côté de l'asymétrie | `frontend/src/features/completude/Completude.tsx` (`bloquant={false}`) — gardé par `Completude.test.tsx` (`le verdict avertit sans annoncer de refus`) ⚠️ un booléen inversé ne se verrait **que** là, `tsc` n'en dit rien | oui, **garde ajoutée avec l'US** |
| §4 — l'action offerte est lue du serveur, jamais déduite du statut | `frontend/src/features/jalons/PretADemarrer.tsx` (`useTransitions` + `VERS_LE_DEPART`) — gardé par `PretADemarrer.test.tsx` (`porte l'action que le serveur offre`) | oui |
| §4 — la famille traverse les axes sans les contredire | `frontend/src/features/admin/axes.ts` (`pret-demarrer: 'pilotage'`, voisin de `completude`) — gardé par `axes.test.ts` (comptage exhaustif des destinations) | oui, pour les **deux** membres livrés |
| §5 — un membre non instruit répond 404 | `backend/application/jalons.py` (`JalonNonInstruit`) · `backend/application/erreurs/referentiel.py` · `backend/api/erreurs.py` (chaîne `isinstance` du 404 — **le mapping est une liste écrite à la main**, cf. le précédent `MancheIntrouvable`) — gardé par `test_jalons_api.py` | oui |
