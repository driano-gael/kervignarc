# ADR-0095 — Un titre de phase est un libellé, et chaque écran de composition porte le mot de sa portée

- **Statut** : Accepté
- **Date** : 2026-08-22
- **US** : E16US002
- **Décideurs** : Organisateur / Architecte
- **S'appuie sur** :
  - [ADR-0076](0076-un-deroule-defini-une-fois-un-avancement-par-depart.md) — le **déroulé** est le
    plan composé une fois sur un tournoi ; c'est lui qui fixe le sens du mot, donc le renommage du §4
  - [ADR-0060](0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md) §5 — ce qui se
    range en bibliothèque et se rejoue d'une année sur l'autre est le **format**, pas la phase isolée
  - [ADR-0045](0045-sequence-de-phases-cycle-de-vie-typage-source.md) §3 — l'identité d'une étape
    reste son rang dans la séquence 1..N, ce que le titre ne remplace pas
  - [ADR-0046](0046-politiques-dans-le-config-json.md) — la racine du `config` JSON accueille ce qui
    n'est pas une politique injectable, sans migration
- **Voisin** : [ADR-0073](0073-pas-de-tir-groupe-de-cibles-couloir-de-tir-place-d-archer.md) — même
  nature de décision (vocabulaire opposable à l'écran comme au code, règle 3), née du même genre de
  refus de maquette

> **Hors de la liste nominative d'[ADR-0075](0075-le-depart-est-la-portee-sportive.md), et c'est
> délibéré.** Cet ADR est de **vocabulaire et d'IHM** : il n'est porté ni par le moteur sportif, ni
> par la portée, ni par une politique injectable au sens de la règle 2 — le critère de `CLAUDE.md`
> exclut explicitement ces ADR-là. Il porte en revanche sa section « Porté dans le code par », qui
> est exigée de **tout ADR neuf** sans condition.
>
> *(Dit en prose et non en puce d'en-tête : l'en-tête d'un ADR est lu par le générateur d'atlas
> comme une liste de **relations** entre décisions, et « ne figure pas à une liste » n'en est pas
> une. Le hook `atlas-a-jour` a refusé la première rédaction et proposait d'étendre le vocabulaire
> partagé des relations — l'étendre pour une formulation ponctuelle aurait été le mauvais échange.)*

## Contexte

Le questionnaire de maquettes du 04/08/2026 a **refusé** la planche A07 (« Phases »). Le motif tenait
en une phrase : « *la création/gestion d'une phase est assez compliquée et demande des écrans plus
détaillés. Je voudrais une liste des phases dans un écran […] Sur chaque ligne du tableau on peut
ouvrir une fiche de la phase, qui reprend son titre et ses réglages.* »

Deux des trois CA ont été **arbitrés le 08/08/2026 sans écrire une ligne d'écran** : « plusieurs
phases de même type » était un défaut de moteur (livré par `E05US024` + `E05US025`), et « gabarit de
phase » a confirmé ADR-0060 §5 — un seul niveau, le format reste la brique. Restaient la **liste**,
la **fiche** et le **titre**.

Entre-temps, six US de formats (`E05US023` → `E05US029`) ont livré **cinq fiches de réglages**
(poules, Big Shoot Off, suisse, colline, découpage) plus les arrêts programmés. L'écran ne manquait
donc plus de réglages : il les empilait **tous à plat**, aiguillés par quatre booléens et du JSX
conditionnel, sous un formulaire d'ajout permanent. Le refus d'origine visait un écran pauvre ; le
même refus vaut aujourd'hui pour un écran **surchargé**.

Deux constats de plus, faits en instruisant l'US :

1. **Aucune phase ne porte de nom.** Ni `EtapeDeroule`, ni `ModelePhase`, ni la table
   `deroule_etape`, ni aucun DTO. Une phase n'est identifiée que par son type et son rang. Or
   `E05US024`/`E05US025` ont rendu composables **plusieurs phases du même type** : l'écran les rend
   depuis identiques — même `LIBELLE_TYPE`, seul le rang pour les distinguer. La capacité était
   livrée, elle n'était pas *utilisable*.
2. **Les deux écrans de composition portaient chacun le mot de l'autre.** La destination `phases`
   s'intitulait « Phases (**format**) » alors qu'elle compose le **déroulé d'un tournoi** — son
   propre `<h3>` le disait déjà. La destination `deroule` s'intitulait « Composer un **déroulé** »
   alors qu'elle fabrique un **format** de bibliothèque, hors tournoi (ADR-0063). Le premier libellé
   n'avait pas été repris quand ADR-0076 a changé la nature de l'écran ; le second emploie pour
   l'atelier un mot qu'ADR-0076 réserve au plan composé sur un tournoi.

## Décision

### §1 — Le titre est un **libellé**, pas une identité

`EtapeDeroule` et `ModelePhase` gagnent un champ `titre: str | None`. Ce qu'il **n'est pas** :

- **pas une clé** — l'identité d'une étape reste son `id` et son rang dans la séquence 1..N
  (ADR-0045 §3). Deux étapes du même déroulé peuvent porter le même titre. Imposer l'unicité aurait
  fait échouer la **composition** sur une gêne d'**affichage**, et déplacé dans le domaine une règle
  qu'aucun besoin métier ne réclame ;
- **pas obligatoire** — `None` est l'état de **tous les déroulés déjà composés**. L'exiger aurait
  invalidé l'existant à la première lecture, c'est-à-dire converti un libellé en migration de données ;
- **pas propre à un type** — à la différence des cinq réglages voisins, retyper une étape n'**efface
  pas** son titre : « Tableau des jeunes » reste juste si la phase devient des poules.

**Un titre blanc vaut absence de titre, jamais un refus.** Effacer le champ est le geste par lequel
l'organisateur *retire* un titre ; le traiter en erreur lui interdirait de revenir au libellé
automatique sans supprimer la phase. La normalisation (espaces de bord retirés, blanc ramené à
`None`) vit dans `__post_init__` et non dans une fabrique, parce que `EtapeDeroule` promet de tenir
sa cohérence « quelle que soit la porte d'entrée, `replace()` compris » — normaliser en amont aurait
laissé passer un `replace(etape, titre="  x  ")`.

**La borne de longueur (80) vit à la frontière, pas dans le domaine.** Le métier n'a aucune règle sur
la longueur d'un libellé ; inventer un maximum sportif serait faux. Ce qu'il faut borner est
l'**entrée**, qui gonflerait sinon le `config` JSON — même garde que `sources` (16) et `arrets` (64).

### §2 — Le titre traverse la promotion **dans les deux sens**

Il est porté par `ModelePhase` autant que par `EtapeDeroule`, et recopié par `pour_tournoi` comme par
`d_etape`. C'est la lettre du CA « réutilisable d'une année sur l'autre » : un titre perdu à la
promotion ferait remonter, l'année suivante, un format aux phases anonymes.

⚠️ **C'est le défaut `barrage_jusqu_au` qu'ADR-0076 a fermé** — un champ présent d'un côté de la
traversée et absent de l'autre. Le dépôt l'a payé une fois côté serveur, et une seconde fois côté
front (`ReglageSuisse`, ignoré du client pendant quatre US). D'où le câblage **des deux formulaires**
dès cette US : l'atelier `PUT` le format **entier**, donc un front qui ignorerait le champ
n'omettrait pas le titre — il **effacerait** ceux d'un format promu depuis un tournoi titré.

### §3 — Le titre reste sur l'**étape** ; `Phase` ne le porte pas

`Phase` — l'avancement d'une étape dans un créneau — ne gagne rien. Le titre décrit la
**composition**, et il est lu par l'écran qui lit des étapes (`GET /tournois/{id}/phases` →
`EtapeReponse`).

Ce n'est pas l'écart de champs que §2 proscrit : celui-là opposait deux représentations de la **même**
définition, alors qu'ici il n'y en a qu'une — l'étape.

⚠️ **Une première rédaction invoquait ici « le régime déjà retenu pour `arrets` » : l'analogie est
fausse, et la revue l'a démontrée.** `arrets` n'est pas absent de `Phase` par choix de modèle mais
par contrainte **technique** — un cycle d'import du domaine, documenté par ADR-0091 §2 et repris mot
pour mot par `DETTE-064`. Aucune contrainte de ce genre ne pèse sur un `str | None`. Le §3 est donc
une décision de **périmètre**, et la présenter comme une nécessité était une rationalisation.

**Ce que la décision de périmètre implique, et qui a été corrigé en revue** : l'écran de **pilotage**
(« Suivi du déroulé ») est le seul endroit où l'on *démarre* et où l'on *termine* une phase — donc le
seul où confondre deux qualifications homonymes coûte réellement quelque chose, publier le mauvais
classement. Y laisser le libellé du type aurait livré « vous pouvez nommer vos phases » en laissant
anonyme l'écran du geste : la capacité livrée mais inutilisable que cette US existe précisément pour
fermer. `PilotageCreneau` **joint donc le titre par `ordre`**, clé partagée entre une étape et ses
instances (ADR-0076 §3), sans que `Phase` ait à porter le champ.

Côté front, `Phase` étant dérivée d'`EtapeDeroule` par `Omit`, `titre` **doit** y être
retiré explicitement, faute de quoi TypeScript garantirait un champ `undefined` à l'exécution — le
défaut exact que le même `Omit` a dû absorber pour `arrets` puis `nb_volees`.

### §4 — Chaque écran de composition porte le mot de **sa portée**

| Destination | Avant | Après | Ce qu'elle compose réellement |
|---|---|---|---|
| `phases` | « Phases (format) » | **« Phases du tournoi »** | le **déroulé** d'un tournoi concret (ADR-0076) |
| `deroule` | « Composer un déroulé » | **« Composer un format »** | un **format** de bibliothèque, sans tournoi (ADR-0060 §5, ADR-0063) |

Les deux libellés étaient **croisés** : chacun portait le mot de son voisin. Le corriger n'est pas
cosmétique — c'est le motif exact du refus d'A10, qu'ADR-0073 a fait lever sur le plan de salle, et
il portait ici sur les deux écrans les plus proches l'un de l'autre du parcours de composition.

**Portée exacte de ce §, et ce qu'il ne couvre pas.** La décision porte sur les **deux entrées de
menu**, plus deux libellés qui les contredisaient à l'intérieur même de l'atelier : un `placeholder`
« Nom du déroulé » sous un label « Nouveau format », et un titre de section « Faire tourner le
déroulé » sur un écran qui ne fait tourner aucun tournoi.

⚠️ **La PLUPART des occurrences de « déroulé » restantes sur cet écran sont CORRECTES**, et un
relecteur les avait toutes comptées comme une dérive. Vérification faite au glossaire : *Déroulé
projeté* y est une entrée à part entière (`ProjectionDeroule`, « ce qu'un **format** produit à un
effectif donné »). « Ce déroulé tient debout », « voir le déroulé se dessiner », « Calcul du
déroulé… » désignent donc la **projection**, pas le plan d'un tournoi ; les renommer en « format »
aurait effacé une distinction que le glossaire porte depuis E01US024. L'axe concerné a accepté
l'écart (« *j'ai compté des mots au lieu de lire l'entrée* »).

⚠️ **Mais « les autres sont correctes » était faux de DEUX chaînes**, trouvées à la 2ᵉ passe par
deux axes — et cette formulation absolue aurait **gelé** la question, nul ne rouvrant un point
qu'un ADR déclare vérifié. Corrigées : « créez-en un pour composer son déroulé » (aucune projection
n'existe quand la bibliothèque est vide) et « **Ce déroulé** ne décrit aucune qualification […] **Le
format** reste applicable » — un même objet, deux mots, une phrase. La leçon vaut au-delà du cas :
un écart motivé se rédige **par énumération de ce qui est vérifié**, jamais par « le reste va bien ».

⚠️ **Un message d'un troisième écran renvoyait à la destination renommée** (`features/duels`,
« ajoutez-en une dans « Phases (format) » ») : corrigé en revue. Le renommage était mécaniquement
traçable par `grep`, et ne pas l'avoir fait rejouait le défaut que la Conséquence n°2 ci-dessous se
félicite d'avoir fermé.

### §5 — Une **fiche par ligne**, la même bascule pour tous les types

La ligne montre `titre ?? LIBELLE_TYPE[type]`, le type restant lisible en détail — sans lui, deux
phases nommées ne diraient plus ce qu'elles **font**. L'ouvrir déplie **sa** fiche : son titre et les
seuls réglages de son type.

⚠️ **La bascule est offerte pour tous les types, qualification comprise.** C'est le cas qui portait le
défaut : la qualification est « gérée ailleurs » (son barème se règle sur « Barème & validation », et
l'éditer ici le perdrait par surprise), elle n'ouvrait donc **aucun** formulaire, et ses réglages
propres — barrage, découpage, arrêts — traînaient à plat dans la barre d'actions de sa ligne. Elle
était de ce fait le seul type impossible à nommer : précisément celui dont le CA dit qu'on peut en
avoir plusieurs.

**Ce qui reste hors de la fiche** : la génération du plan de cibles (`PlanParBlocs`). C'est une
**action**, pas un réglage, et le dépôt s'est déjà brûlé trois fois sur des plans de cibles
inatteignables (E05US023, E05US026, E05US030) — la replier derrière un clic n'aurait rien apporté et
aurait rejoué ce risque.

## Conséquences

- **Aucune migration.** Le titre vit à la racine du `config` JSON de l'étape (ADR-0046), comme
  `decoupage` (E05US035) et le mode de poules (E05US029). Une étape écrite avant cette US se relit
  sans titre, soit exactement son comportement d'avant. Une **colonne** dédiée a été envisagée puis
  écartée : les quatre seules colonnes de `deroule_etape` sont `id`, `tournoi_id`, `ordre`, `type` —
  tous les champs de définition, sans exception, vivent dans le JSON. Les deux arguments qui
  plaidaient pour une colonne (tri, contrainte d'unicité) sont tombés avec §1.
- **Le refus « composition avancée » a été corrigé au passage, et il était trompeur.** Il disait
  « éditable depuis l'écran de composition du déroulé » et désignait l'atelier — qui ne travaille sur
  **aucun tournoi** et ne pouvait donc pas éditer cette phase. Le renommage du §4 l'a mis à nu :
  recopier la phrase avec le nouveau nom aurait conservé le cul-de-sac. Elle nomme désormais le vrai
  chemin (composer un format, puis l'appliquer depuis « Assemblage »).
- **`DETTE-080` est inscrite** : la plomberie d'état des deux formulaires de composition est écrite
  deux fois, et `titre` en est le **10ᵉ** réglage. Antérieure à cette US, aggravée par elle, donc
  inscrite par elle. Le remède est une US `refactor/` dédiée, pas un geste en douce ici.
- **Une duplication a été fermée, sur preuve** : `configInchangee` remplace la recopie **manuelle**
  de la config complète dans les widgets qui n'éditent qu'un champ. Trois occurrences réelles et
  **deux bugs déjà payés** — `ReglageBarrage` effaçait le `decoupage` (rendant inertes les pauses
  posées dessus), et le couple découpage/arrêts partait en 422. Le `titre` en aurait été le
  troisième : sans cette fonction, régler un barrage renommait la phase en silence. Portée locale
  (une fonction, un fichier), donc pas de remède structurel ni d'ADR pour elle-même. Son type de
  retour est `Required<ConfigPhase>` — c'est **le typecheck** qui garde l'exhaustivité, et non la
  vigilance : un 13ᵉ réglage oublié devient une erreur de compilation (correctif de revue).
- **Le champ de saisie a été extrait en revue, sur constat.** Il était écrit **trois fois** et les
  trois copies **divergeaient déjà** dans le commit qui les créait — libellé, classe, placeholder,
  et surtout la borne de 80 recopiée trois fois face à un serveur qui la déclare une fois.
  `shared/phases/ChampTitre.tsx` est le **8ᵉ** exemplaire d'un pattern déjà établi dans ce dossier (sept contrôles y vivaient déjà — décompte corrigé en 2ᵉ passe, il disait « 7ᵉ ») :
  c'est de la conformité à une convention, pas l'introduction d'un pattern — donc ni ADR ni US
  dédiée. La divergence de mot (« phase » côté tournoi, « étape » côté atelier) est **conservée et
  assumée** : chaque écran garde le registre qu'il emploie partout ailleurs (règle 3, la pluralité
  est légitime à l'écran), et le composant l'expose en `prop` plutôt que de le figer.
- **Un garde-fou de test a changé de geste, et un autre était plus faible que son nom.** Les tests
  d'E05US035 cherchaient les réglages de la qualification à l'écran ; ils ouvrent désormais sa fiche.
  Ce faisant, on a découvert qu'ils **portaient leurs requêtes à l'écran entier** alors que le
  formulaire d'ajout, monté en permanence, affiche les mêmes libellés : `findByText` résolvant à la
  première correspondance, l'assertion matchait le formulaire d'ajout et serait restée verte avec le
  réglage de la qualification **entièrement décâblé** — soit le défaut exact que ce fichier existe
  pour empêcher. Les requêtes sont désormais portées à la **ligne**.
- **Le réglage de la qualification n'est plus visible sans clic.** C'est la contrepartie assumée du
  §5, et elle mérite d'être dite : le CA demande une fiche qu'on ouvre, pas un mur qu'on parcourt.
- **`DETTE-035` n'est pas résorbée** et reste rattachée à l'exigence `P-4` de cette même planche
  (« chiffrer la conséquence au moment du choix » : un tableau de 120 passe de 128 à 436 duels selon
  la profondeur). Arbitrage du commanditaire du 22/08/2026 : hors périmètre — le remède touche la
  politique `Depth` côté domaine, soit un chantier moteur dans une US déjà large côté IHM.

## Porté dans le code par

⚠️ Section écrite en **vérifiant dans le code du jour**, pas en déduisant de la décision.

| Décision | Module qui l'applique | Vérifié |
|---|---|---|
| §1 — le titre est un champ d'étape, facultatif | `backend/domain/deroule_etape.py` (champ `titre`) | oui |
| §1 — blanc ramené à l'absence, espaces de bord retirés, sur **toute** porte d'entrée | `backend/domain/deroule_etape.py` (`titre_normalise`) · `backend/domain/format_tournoi.py` (`ModelePhase.__post_init__`) — gardés par `backend/tests/test_domain_titre_de_phase.py`, cas *le titre est normalisé* et *un modèle de format normalise son titre comme une étape* | oui, la **2ᵉ porte** ajoutée en revue |
| §1 — aucune unicité, aucune garde de type | `backend/tests/test_domain_titre_de_phase.py` — les cas *deux étapes du même déroulé peuvent porter le même titre* et *le titre survit à un retypage* | oui |
| §1 — la borne de longueur vit à la frontière | `backend/api/v1/phases.py` (`ConfigPhaseRequete.titre`, `max_length=80`) · `backend/api/v1/formats.py` (`EtapeDTO.titre`, idem) | oui |
| §2 — la traversée format ↔ étape, dans les deux sens | `backend/domain/format_tournoi.py` (`ModelePhase.titre`, `pour_tournoi`, `d_etape`) | oui |
| §2 — l'aller-retour persistant, table `deroule_etape` | `backend/infrastructure/db/repositories/moteur.py` (`_politiques_json`, **`_config_etape`**, `_lire_titre`, `_vers_etape`) | oui |
| §2 — l'aller-retour persistant, `config` d'un **format** | `backend/infrastructure/db/repositories/moteur.py` (**`_config_format`**, `_vers_modele_phase`) — gardé par `backend/tests/test_phase_repository.py` (cas *un format conserve le titre de ses étapes*) et `backend/tests/test_patrimoine_api.py` (aller-retour HTTP) | oui, **après correctif de revue** |
| §2 — le câblage front de l'atelier, sans lequel un format promu perdrait ses titres | `frontend/src/features/patrimoine/api.ts` (`Etape.titre`) · `frontend/src/features/deroule/Deroule.tsx` (état, champ, charge utile, reset) | oui |
| §3 — le titre reste sur l'étape, absent de `Phase` | `backend/domain/phase.py` **inchangé** (aucun champ `titre`) · `backend/api/v1/phases.py` (`PhaseReponse` **inchangée**) ⚠️ **instantané, pas garde-fou** : rien ne rougirait si une US ajoutait `titre` à `Phase`. Le versant front, lui, est gardé par le typecheck — voir la ligne suivante | oui |
| §3 — le retrait explicite côté front, pour ne pas garantir un `undefined` | `frontend/src/features/phases/api.ts` (`Omit<EtapeDeroule, … 'titre'>`) | oui |
| §4 — chaque destination porte le mot de sa portée | `frontend/src/features/admin/CoquilleAdmin.tsx` (libellés `phases` et `deroule`) | oui |
| §5 — une bascule de fiche par ligne, tous types confondus | `frontend/src/features/phases/Phases.tsx` (`LignePhase`, état `ficheOuverte`, bouton « Ouvrir la fiche ») | oui |
| §5 — la fiche de la qualification réunit ses réglages propres | `frontend/src/features/phases/Phases.tsx` (`ReglageTitre`, `ReglageBarrage`, `ReglageDecoupageDePhase` montés dans la fiche) | oui |
| §3 — le titre **joint** au pilotage, sans que `Phase` le porte | `frontend/src/features/suivi-deroule/PilotageCreneau.tsx` (`usePhases` + jointure par `ordre`) | oui, **ajouté en revue** |
| §1 — le champ de saisie, **une seule fois** | `frontend/src/shared/phases/ChampTitre.tsx` (`LONGUEUR_MAX_TITRE`, miroir unique du `max_length=80` des deux DTO), monté par les trois sites | oui, **après correctif de revue** |
| §5 — le plan de cibles reste une **action**, hors de la fiche | `frontend/src/features/phases/Phases.tsx` (`PlanParBlocs`, toujours dans `phase__actions`) | oui |
| Conséquence — la recopie de config est centralisée | `frontend/src/features/phases/Phases.tsx` (`configInchangee`, consommée par les trois widgets à champ unique) | oui |
