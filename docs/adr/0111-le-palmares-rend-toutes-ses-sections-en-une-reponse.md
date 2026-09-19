# ADR-0111 — Le palmarès rend toutes ses sections en **une** réponse

- **Statut** : Accepté
- **Date** : 2026-09-19
- **US** : E06US009
- **Décideurs** : Organisateur / Architecte
- **S'appuie sur** :
  - [ADR-0075](0075-le-depart-est-la-portee-sportive.md) — le **départ** est la portée sportive :
    deux archers de créneaux différents ne sont jamais comparés
  - [ADR-0103](0103-la-portee-d-un-podium-est-un-reglage-du-tournoi.md) — la portée d'un podium est
    un **réglage du tournoi**, et le serveur porte les faits que le client ne déduit pas
  - [ADR-0101](0101-le-catalogue-d-exports-porte-les-formats-pas-les-url.md) — le catalogue
    d'exports porte les formats, `?format=` choisit

> ⚠️ **Cet ADR figure à la liste nominative d'[ADR-0075 § « Portée de la règle »](0075-le-depart-est-la-portee-sportive.md).**
> Il n'est pas d'outillage : il décide de la **forme sous laquelle le moteur sportif publie ses
> résultats**, et ferme une capacité (demander un créneau seul). Il porte donc sa section
> « Porté dans le code par ».

## Contexte

`DETTE-045` décrivait un raccourci : le palmarès résolvait « le premier départ » et ignorait les
autres, silencieusement. Le registre **annonçait aussi son remède**, et la docstring de
`ServicePalmares._premier_depart` le répétait mot pour mot :

> « le remède se réduit à **une route par départ** (E06US009). »

E06US009 n'a pas fait cela. Elle rend `N` sections dans **une seule** réponse de la route tournoi,
et n'ouvre aucune route `/departs/{id}/palmares`. Le choix est défendable — il est même meilleur —
mais il **contredit** ce que le dépôt avait inscrit, et il a été pris dans un corps de commit.

C'est un relecteur (axe C2) qui l'a relevé : *« une dette enregistre un coût, elle ne tient pas lieu
de décision »*. Le présent ADR existe pour que la décision soit opposable, et pas seulement écrite
dans un message que personne ne relit.

## Décision

### 1. Une réponse, `N` sections — et **aucune route par départ**

`GET /api/v1/tournois/{id}/palmares` rend `sections: [{ depart_id, libelle, podiums,
classement_vide, classement_clubs, lignes }]`, une par créneau, dans l'ordre des départs.

**Pourquoi pas une route par départ**, qui était le remède annoncé : les quatre surfaces du
palmarès (pilotage, écran de salle, appli publique, document) veulent **toutes** les afficher
ensemble. Une route par départ leur aurait imposé `N` requêtes, donc `N` instants de lecture
différents pour un même écran — exactement ce que `RenduPalmares` existe pour empêcher : un `PUT`
de réglage intercalé entre deux requêtes rendrait des blocs qui se contredisent.

⚠️ **Cela ferme une capacité, et c'est assumé** : aucun client ne peut demander un seul créneau.
`ServicePalmares.pour_depart` existe mais n'a **aucun appelant de production** — c'est une commodité
de lecture, pas une route en attente. Le jour où un écran voudra un créneau seul, il faudra une
route, et **cet ADR sera à rouvrir**, pas à contourner.

### 2. Aucun champ agrégé au niveau du tournoi

`PalmaresReponse` ne porte que `tournoi_id`, `profondeur_podium` et la liste des sections. Il n'y a
**aucun** total, classement d'ensemble ou compteur inter-départs — conformément à l'arbitrage du
07/08/2026 (« juxtaposé — 4 départs = 4 podiums »).

⚠️ **L'absence est la décision.** Un champ agrégé au niveau tournoi serait la porte par laquelle
l'agrégation rentrerait, et elle rentrerait sans discussion parce qu'elle aurait l'air d'un détail
de DTO. `profondeur_podium` est la seule exception, et elle n'est pas un résultat sportif : c'est un
réglage du tournoi (ADR-0103 §1), identique pour tous ses créneaux.

### 3. Les documents suivent : **`N` sections dans un fichier**, jamais un fichier par départ

Le PDF titre chaque créneau et empile ses sections. Le tableur garde **une** grille et ouvre une
colonne « Départ » en première position.

**Pourquoi une grille et non `N` onglets** : le parti de ce format est le classement **à plat**, qui
se trie et se filtre (ADR-0101 §4). Des onglets rendraient les `N` rangs 1 indiscernables à l'œil,
alors qu'une colonne les nomme.

⚠️ **Corollaire à connaître : la colonne « Rang » n'est plus unique** — chaque créneau y recommence
à 1. C'est la juxtaposition, pas un doublon.

⚠️ `stories/E06-classements.md` disait avant cette US : « un fichier par départ ou un fichier à N
sections est un choix de **format d'export**, à trancher dans l'US d'export, pas ici ». Il est
tranché ici parce que l'US d'export (`E16US007`, `E16US016`) était **déjà livrée** : renvoyer le
choix à une US passée revenait à ne le trancher nulle part.

## Conséquences

- **Le coût de la route est multiplié par `N`.** Elle est **publique, non authentifiée et pollée
  toutes les 30 s** par chaque tablette. `DETTE-031` est élargie en conséquence. Une part est
  irréductible (un podium par départ demande un classement par départ) ; une autre ne l'est pas —
  `ServiceClassement.pour_phase` relit les archers, les catégories et les forfaits **à la maille
  tournoi**, donc `N` fois le même résultat. Cette part est tracée, pas fermée.
- **Un seul instant de lecture** pour toutes les sections : le réglage et les `N` palmarès viennent
  du même `par_id`, ce qu'une route par départ n'aurait pas garanti.
- **L'écran de salle projeté ne pagine pas `VuePalmares`** : à `N` créneaux empilés, seul le haut
  est lisible et personne ne fait défiler devant un vidéoprojecteur. `DETTE-097` est élargie : son
  déclencheur cesse d'être un réglage explicite pour devenir le cas nominal.
- **Le contrat de `GenerateurPalmares` a changé** (`complet=`/`affiche=` → `sections=`), et avec lui
  les deux adapters. Un troisième format d'export devra parler en sections.

## Porté dans le code par

- `backend/api/v1/palmares.py` — `PalmaresReponse` (décision 2 : les trois seuls champs de niveau
  tournoi) et `SectionPalmaresReponse` / `.de_section` (décision 1). ⚠️ **C'est `de_section` qui
  tient la décision 2** : remonter l'appel à `classer_clubs` d'un cran au-dessus rendrait un
  classement de clubs agrégé sans qu'aucun champ neuf n'apparaisse.
- `backend/application/palmares.py` — `RenduPalmares.sections` et `ServicePalmares.rendu` : le
  « un seul instant de lecture » des Conséquences. `pour_depart` **n'est pas** une route en
  attente — sa docstring porte l'avertissement.
- `backend/domain/ports.py` — `GenerateurPalmares.palmares(sections=…)` : la décision 3 côté port,
  donc opposable aux deux adapters et à tout format à venir.
- `backend/infrastructure/pdf/palmares.py` — `_corps` (une section par créneau, titrée) et
  `_corps_creneau` ; `backend/infrastructure/tableur/palmares.py` — `_ENTETE` (colonne « Départ » en
  tête) et la double boucle `for section … for ligne`, qui **est** le « une grille, pas N onglets ».
- `frontend/src/features/palmares/VuePalmares.tsx` — `SectionCreneau` : la pile titrée, et la garde
  globale qui ne parle que si **aucun** créneau n'est classé.
- `backend/tests/test_service_palmares_par_depart.py` — garde la décision 1 et l'absence d'agrégat.
- `backend/tests/test_pdf_palmares.py` (`test_deux_creneaux_font_deux_sections`) et
  `backend/tests/test_tableur_palmares.py` (`test_la_colonne_depart_nomme_le_creneau_de_chaque_ligne`)
  gardent la décision 3 — **tous deux à deux sections**, sans quoi « le libellé du premier partout »
  resterait invisible.
