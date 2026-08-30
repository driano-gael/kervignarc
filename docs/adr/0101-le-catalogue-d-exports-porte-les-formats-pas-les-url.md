# ADR-0101 — Le catalogue d'exports porte les formats, pas les URL

- **Statut** : Accepté
- **Date** : 2026-08-30
- **US** : E16US007
- **Décideurs** : Organisateur / Architecte
- **S'appuie sur** :
  - [ADR-0031](0031-bibliotheque-pdf-reportlab.md) — ReportLab comme unique moteur de rendu PDF ;
    cet ADR ne le remplace pas, il lui ajoute un **frère** au même rang
  - [ADR-0058](0058-decoupage-de-l-admin-en-trois-axes-d-activite.md) — les trois axes : c'est lui
    qui justifie que les documents de salle **restent** dans leur écran de travail

> ⚠️ **Cet ADR ne figure pas à la liste nominative d'[ADR-0075 § « Portée de la règle »](0075-le-depart-est-la-portee-sportive.md), et c'est volontaire.**
> Il est d'**outillage documentaire** : aucun moteur sportif ne lit un format de fichier, aucune
> portée ne change, aucune politique injectable au sens de la règle 2 n'est en jeu.
> ⚠️ **« Au sens de la règle 2 » désigne les six politiques du moteur** — `routing`, `scoring`,
> `seeding`, `byes`, `tiebreak`, `depth`. Le §2 ci-dessous dit « la règle 2 appliquée au rendu » :
> c'est un emprunt de **forme** (un adapter plutôt qu'une branche), pas une septième politique.
> Sans cette précision, un relecteur appliquant le critère mot à mot conclut que l'exclusion est
> fausse *(levé en revue, axe C2)*. Le critère de
> `CLAUDE.md` exclut nommément les ADR d'outillage ; précédents : `0095`, `0096`, `0098`, `0100`.
> ⚠️ **Il est en revanche inscrit à la liste « hors critère » d'ADR-0075** — le plaider ici ne
> suffit pas, c'est cette liste qui borne ce qu'une revue a le droit de relever. Il porte sa
> section « Porté dans le code par », exigée de **tout ADR neuf**.

## Contexte

Le questionnaire A18 demande que « chaque ligne d'export propose plusieurs formats possibles (CSV,
EXCEL, PDF…) » et que cela « puisse évoluer, donc être paramétrable ». Le CA d'E16US007 en tire la
formulation vérifiable : **« l'ajout d'un format ne demande pas de toucher l'écran »**.

L'état des lieux au 30/08/2026 (relevé dans le code, pas supposé) :

- **huit routes** rendent un fichier, réparties sur cinq modules d'API, et **chacune est
  mono-format, câblée en dur** — `media_type="application/pdf"` et un nom de fichier suffixé
  `.pdf` recopiés à chaque endroit ;
- **aucune notion de format n'existe** : ni énumération, ni paramètre de route, ni de service. Le
  seul « format » du dépôt (`ServiceSimulationFormat`) désigne un **format de tournoi** FFTA ;
- le seul CSV produit est **ad hoc** — `infrastructure/archive/constructeur.py` dumpe les tables
  SQL brutes dans le ZIP d'archive. Ce n'est pas une vue métier, il n'est pas réutilisable ;
- côté front, **chaque feature réécrit son bouton d'export** (cinq occurrences) ; seule la
  plomberie `fetchBlob` / `telechargerFichier` est factorisée.

Le risque de conception est identifié d'avance : servir un « catalogue d'exports » invite à y mettre
**tout** ce qu'un export a besoin de dire — son URL, ses paramètres (`tri`, `depart_id`,
`categorie_id`), sa méthode. On obtiendrait un gabarit d'URL par entrée et un sac de paramètres
générique, c'est-à-dire l'**union de toutes les entrées** que l'instruction de la famille
« prêt à… » (E16US012) a déjà refusée une fois : *« les fusionner aurait demandé l'union de toutes
les entrées, donc reconstruit les quatre variantes à l'intérieur »*.

## Décision

### §1 — Le catalogue porte les formats, et rien d'autre

`GET /api/v1/exports` énumère les documents proposés par l'écran « Exports & impressions » et, pour
chacun, **les formats que ce serveur sait produire**. Il ne porte **ni URL, ni verbe HTTP, ni
paramètres** : chaque document garde sa route et ses options d'IHM.

La propriété obtenue est donc exactement celle du CA, ni plus ni moins :

| Geste | L'écran change-t-il ? |
|---|---|
| Ajouter un **format** à un document existant | **non** — un adapter, une ligne au composition root |
| Ajouter un **document** au catalogue | **oui** — il lui faut ses commandes (quel départ, quel tri) |

C'est assumé : le CA demande le premier. Promettre le second aurait coûté le gabarit d'URL, et il
n'a pas d'usage — un export neuf arrive avec ses propres options, qui sont de l'IHM.

### §2 — Un format est un adapter, pas une branche

Un service générateur ne reçoit plus **un** générateur mais un `RegistreDeFormats` — les
générateurs du même document indexés par format (`application/exports.py`). Il ne contient aucun
`if format == …` : il délègue. Ajouter `xlsx` sera un adapter et une entrée de dictionnaire.

C'est la règle 2 (stratégies injectables) appliquée au rendu : *un format de sortie est de la
configuration, pas du code*.

### §3 — Les formats annoncés **dérivent** du câblage

`RegistreDeFormats.formats` lit les clés réellement câblées ; le composition root passe ces formats
à `construire_catalogue`, **fonction pure**, qui compose les entrées. **Aucune ligne n'écrit une
liste de formats à la main.**

⚠️ **La fonction est pure exprès** : composer le catalogue *dans* `bootstrap/` rendait la
dérivation intestable, si bien qu'une liste réécrite à la main y serait passée sans rien faire
rougir — alors que c'est l'invariant central de cet ADR. *(Relevé en revue, axe B : la promesse
était plus forte que la preuve.)*

C'est le point qui empêche le défaut caractéristique du projet — « bien formé, plausible et faux »
([ADR-0081](0081-un-classement-de-poule-se-lit-par-groupe.md)). Une entrée qui figerait
`(PDF, CSV)` continuerait de proposer le CSV après un débranchement, et l'organisateur recevrait
une **400 sur un choix que le serveur lui a lui-même offert**.

Corollaire : un `RegistreDeFormats` **vide est refusé à la construction**. Le tolérer publierait au
catalogue un document affiché **sans aucun bouton**.

Corollaire d'ordre : `formats` sort dans l'ordre de `FormatExport`, jamais dans celui du câblage —
sinon l'ordre d'écriture au composition root, détail invisible en revue, déplacerait un bouton sous
le doigt de l'organisateur.

### §4 — Le CSV rend des lignes, pas une mise en page

Un CSV n'est pas un PDF sans police. Quatre partis, tous dictés par le tableur réel de
l'utilisateur plutôt que par la RFC 4180 — un CSV « correct » qui s'ouvre en bouillie n'exporte
rien :

1. **BOM UTF-8** (`utf-8-sig`). Sans lui, Excel lit l'UTF-8 en ANSI : « Grégoire » devient
   « GrÃ©goire » — sur un fichier dont chaque ligne est un nom d'archer.
2. **Point-virgule en séparateur.** Sur une machine dont la virgule est le séparateur décimal
   (toute machine française), Excel n'attend pas la virgule en séparateur de champ et verse tout
   dans la colonne A.
3. **Montants en nombres** (`8,00`, sans « € »). Un montant suffixé reste du **texte**, donc
   insommable — or l'usage de cet export *est* la somme.
4. **Aucun total, aucun bloc, aucun en-tête de document.** Le club devient une **colonne**, une
   ligne = un archer. Ce qui fait un beau PDF (regroupements, ligne « Total », titre) casse le tri
   et le filtre d'un tableur. Le tournoi et la portée sont portés par le **nom du fichier**.

⚠️ Conséquence à ne pas manquer : le PDF et le CSV du même document **ne se ressemblent pas**. Ce
n'est pas une divergence de données — le service compose **un seul** contenu et le format n'agit
qu'au rendu (garde-fou : `test_le_contenu_compose_ne_depend_pas_du_format`). C'est une divergence
de *présentation*, voulue.

### §5 — Un export n'offre que les formats qui ont un sens

La liste est **par document**, pas globale. Une **feuille de marque** se remplit au stylo sur la
cible : elle n'existe qu'en PDF, et son registre à un seul générateur le dit tout seul. Un
catalogue dont toutes les entrées offriraient les mêmes formats ne prouverait pas le CA.

Sa route accepte tout de même `?format=` : le refus devient une **400 explicite** au lieu d'un
paramètre ignoré en silence, qui rendrait un PDF à qui a demandé du CSV.

## Conséquences

- **Un point unique** compose la réponse binaire (`api/documents.reponse_document`) : type de
  contenu **et** extension dérivés du format. Sans lui, un format ajouté se téléchargerait en
  `.pdf` contenant du CSV — un fichier qu'aucun outil n'ouvre et dont rien, côté serveur, ne dirait
  qu'il est faux.
- **Le catalogue ne porte pas non plus les libellés.** Un libellé et une description sont des
  choix d'IHM au même titre que l'URL et les commandes : les faire descendre dans le catalogue
  mettrait la copie de l'écran dans le composition root, et une correction de formulation
  deviendrait une modification du backend. Ils vivent donc dans la table `documents` de
  `Exports.tsx`, à côté du chemin. *(Corrigé en revue, axe C2 : la 1ʳᵉ livraison les portait.)*
- **Le nom de fichier est dérivé des deux côtés** : le serveur pour le `Content-Disposition`
  (`api/documents.py`), le front pour le fichier enregistré (`telechargerExport`). Le « point
  unique » ne couvre que la paire **(type MIME, extension)**, pas le radical du nom. Le remède —
  lire le `Content-Disposition` côté front — demanderait d'exposer les en-têtes dans `fetchBlob`,
  utilisé par tout le dépôt, pour un défaut qui produit un fichier mal nommé et rien de plus.
  Écrit ici pour qu'on ne croie pas le point unique plus large qu'il n'est *(axes C2 et D)*.
- **Le type MIME vit à la frontière API** (`api/documents.py`), pas dans `application/` : c'est une
  décision HTTP, même partage que le mapping des erreurs (règle 5/6) — `FormatExportIndisponible`
  ne porte pas son 400. Le libellé de **format**, lui, reste applicatif, et pour une raison
  vérifiable : l'écran doit rendre un format **qu'il ne connaît pas** (`Exports.test.tsx`, cas
  `ods`), donc son nom ne peut venir que du serveur. Un **document** inconnu de l'écran est hors
  périmètre par §1 — son libellé peut donc y vivre. *(La 1ʳᵉ rédaction disait « il est servi au
  client, donc il fait partie du contrat » : circulaire, relevé en 2ᵉ passe.)* *(Corrigé en revue, axe A.)*
- **Le paquet d'infra s'appelle `tableur/`, pas `csv/`** : il porterait le nom du module stdlib que
  ses propres modules importent.
- **Aucune dépendance ajoutée** (règle 11) : ReportLab était déjà là, `csv` est stdlib. `xlsx`
  reste dû et demande un arbitrage — `E16US016`.
- **Le palmarès reste dehors.** Sa route s'appelle littéralement `/palmares.pdf` et elle est
  **publique** : lui ajouter un format est un renommage d'API publique, pas une entrée de registre.
  `DETTE-031` y ajoute un coût — chaque lecture reconstruit toutes les phases à tableau, et un
  format de plus multiplie ce recalcul sur une route non authentifiée. À trancher en `E16US016`.
- **Les documents de salle restent dans leur écran** (étiquettes QR, cartes scoreur, archive) :
  ADR-0058 veut l'activité là où elle se fait. Ils ne sont pas au catalogue.
- ⚠️ **La compatibilité repose sur un défaut de paramètre.** `format_` retombe sur `PDF` dans les
  trois services : `ServiceArchive` régénère ses documents sans rien passer, et l'écran d'avant
  l'US aussi. Retirer ce défaut casserait l'archive **en silence** (elle a un `.pdf` en dur dans
  ses noms de fichiers).

## Porté dans le code par

⚠️ Section écrite en **vérifiant dans le code du jour**, pas en déduisant de la décision.

| Décision | Module qui l'applique | Vérifié |
|---|---|---|
| §1 — le catalogue ne porte que des formats | `backend/api/v1/exports.py` (`EntreeCatalogueReponse` : `identifiant`, `libelle`, `description`, `formats` — **aucun** champ d'URL) · `backend/application/exports.py` (`CatalogueExports`, `EntreeCatalogueExport`) | oui |
| §1 — chaque document garde sa route et ses options | `backend/api/v1/listes_impression.py` (`tri`, `depart_id` **inchangés**) · `backend/api/v1/feuille_de_marque.py` (`depart_id` en chemin) | oui — aucune option déplacée |
| §2 — le format est un adapter, jamais une branche | `backend/application/exports.py` (`RegistreDeFormats.pour`) · `backend/application/listes_impression.py` et `backend/application/feuille_de_marque.py` (`self._generateurs.pour(format_)`, **zéro** `if`) | oui |
| §2 — l'adapter CSV réalise le **même** port que le PDF | `backend/infrastructure/tableur/listes_impression.py` (`GenerateurListesImpressionCsv`, port `GenerateurListesImpression`) | oui |
| §3 — les formats dérivent du câblage | `backend/application/exports.py` (`construire_catalogue`, fonction **pure**) · `backend/bootstrap/composition.py` (`construire_catalogue(formats_listes, formats_feuille)`) · `RegistreDeFormats.formats` — gardé par `test_le_catalogue_construit_annonce_les_formats_qu_on_lui_donne` (décor **mono-format** : une liste écrite en dur en annoncerait deux) | oui — ⚠️ **corrigé en revue (axe B)** : la 1ʳᵉ livraison composait le catalogue **dans** `bootstrap/`, donc hors de portée des tests ; la cellule « gardé » promettait plus que la preuve, exactement le défaut qu'ADR-0075 documente |
| §3 — registre vide refusé, ordre stable | `RegistreDeFormats.__init__` (`ValueError`) et `.formats` (itère `FormatExport`) — gardés par `test_un_registre_vide_est_refuse_a_la_construction` et `test_les_formats_sortent_dans_l_ordre_du_catalogue_pas_du_cablage` | oui |
| §4 — BOM, séparateur, montants, pas de totaux | `backend/infrastructure/tableur/listes_impression.py` (`utf-8-sig`, `_SEPARATEUR = ";"`, `_montant`, `_ENTETE_CLUB_PAIEMENT` avec `Club` en colonne) | oui |
| §4 bis — une cellule de texte ne devient pas une formule | `backend/infrastructure/tableur/listes_impression.py` (`_neutraliser`, `_AMORCES_DE_FORMULE`) — appliqué aux **colonnes de texte seulement**, jamais aux montants (un `-5,00` préfixé cesserait d'être sommable) ; gardé par `test_un_club_nomme_comme_une_formule_n_est_pas_execute` et `test_les_montants_ne_sont_jamais_neutralises` | oui — ⚠️ **ajouté en revue** : relevé par les **cinq** axes (CWE-1236), le chemin étant complet (import FFTA → CSV → tableur de la trésorière) |
| §4 — le contenu ne dépend pas du format | `backend/application/listes_impression.py` — le contenu est composé **avant** `.pour(format_)` ; gardé par `test_le_contenu_compose_ne_depend_pas_du_format` | oui |
| §5 — un export mono-format, et le refus explicite | `backend/bootstrap/composition.py` (`RegistreDeFormats({FormatExport.PDF: GenerateurFeuilleDeMarquePdf()})`) · `backend/application/erreurs/exploitation.py` (`FormatExportIndisponible`) · `backend/api/erreurs.py` (→ 400) | oui |
| §5 / §1 — l'écran ne tient aucune liste de formats | `frontend/src/features/exports/Exports.tsx` et `api.ts` — les boutons sont produits depuis le catalogue reçu | oui |
| Conséquence — point unique de réponse binaire | `backend/api/documents.py` (`reponse_document`, `reponses_document`, `MEDIA_TYPES`) — module d'API **sans routeur**, appelé par `listes_impression.py` et `feuille_de_marque.py` ; exhaustivité gardée par `test_chaque_format_porte_un_media_type_distinct` | oui — ⚠️ **corrigé en revue (axes A, C2)** : il vivait dans le routeur du catalogue, et le dictionnaire OpenAPI réénumérait les types MIME **à la main**, dans le module même qui importe le registre |
