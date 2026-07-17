# ADR-0022 — La hauteur du centre de l'or vit sur la catégorie ; contrainte de placement de 1er rang

- **Statut** : Accepté
- **Date** : 2026-07-17
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`docs/dette.md`](../dette.md) (**DETTE-002** résorbée) ;
  [`docs/modele-de-donnees.md`](../modele-de-donnees.md) (`CATEGORIE.hauteur_cm`) ;
  [`stories/E03-placement.md`](../../stories/E03-placement.md) (E03US001, CA « capacité & fraction »
  étendu à la hauteur)
- **Introduit par** : E03US001 (moteur de placement) ; **résorbe** [DETTE-002](../dette.md), inscrite
  au cadrage FFTA du 14/07/2026 et **explicitement assignée** à cette US « avant d'écrire l'algorithme ».
- **Voisin** : [ADR-0020](0020-blason-zones-vocabulaire-ferme-et-defaut-sur-ensemble.md), qui traitait
  les **valeurs de score** du blason et laissait la hauteur « hors périmètre, résorbée en EPIC-03 ».

## Contexte et problème

Le moteur de placement (E03US001) répartit les archers sur les cibles sous deux budgets par cible :
l'**espace** (Σ des fractions `Blason.taille` ≤ 1,0) et les **positions** (nombre d'archers ≤
`Cible.capacite`). Ces deux budgets sont **insuffisants** : ils laissent passer un plan
**physiquement intirable**.

La FFTA fixe la **hauteur du centre de l'or** (du sol au centre) à **130 cm** pour la quasi-totalité
des configurations, mais à **110 cm** pour le blason 80 cm des **U11** (art. C.3.1.1 ;
[`docs/referentiel-ffta.md`](../referentiel-ffta.md) §5). Une **butte** (une cible physique) n'a
qu'**une** hauteur de montage : un U11 (110 cm) et un adulte (130 cm) **ne peuvent pas partager une
cible**, quelle que soit la place restante. La règle « Σ fractions ≤ capacité » l'autorise pourtant
— d'où [DETTE-002](../dette.md) : des plans que l'algorithme déclare valides mais que la salle ne
peut pas monter.

Le modèle ne portait **nulle part** cette hauteur : `Blason` connaît sa `taille` (fraction) et sa
`capacite` (nombre d'archers), pas la hauteur de son centre. DETTE-002 laissait ouverte la question
**« où vit la hauteur ? »** — sur le blason, sur la catégorie, ou les deux.

## Options considérées

| # | Option | Verdict |
|---|---|---|
| 1 | **Hauteur sur `Categorie`** (`hauteur_cm`, défaut 130) | **Retenue** |
| 2 | Hauteur sur `Blason` | Écartée |
| 3 | Hauteur sur les deux (nominale catégorie + surcharge blason) | Écartée |
| 4 | Déduire la hauteur des `ages` de la catégorie (U11 → 110) à la volée | Écartée |

- **(2)** rattache la hauteur au **carton**. Mais un même blason (ex. « 80 cm ») peut être le blason
  par défaut de plusieurs catégories, et la hauteur suit l'**archer** (sa catégorie d'âge), pas le
  papier : porter la hauteur sur le blason obligerait à dupliquer un blason par hauteur, ou à figer
  une hauteur pour un carton qui n'en a pas intrinsèquement. La donnée qui varie est la **catégorie**.
- **(3)** offre une flexibilité (une catégorie pourrait tirer plus bas sur un blason donné) dont
  **aucun cas réel du mono-club ne témoigne** : c'est de la sur-conception (règle 12). Le jour où un
  3ᵉ cas réel l'exige, l'override se pose (règle « 3ᵉ occurrence » du § Dette).
- **(4)** évite le champ, mais **couple** le placement au vocabulaire des tranches et rend la hauteur
  **non éditable** : une catégorie créée à la main sans `ages` (permis, E01US003) n'aurait pas de
  hauteur, et un surclassement U11→U13 (art. C.3.1.1) ne pourrait pas garder 110. Une **donnée
  explicite** est plus honnête qu'une heuristique — même motif que le rejet de « déduire le type du
  blason depuis son nom » (ADR-0020, option 4).

## Décision

**1. `Categorie` porte `hauteur_cm: int` (hauteur du centre de l'or, en cm), défaut 130.** Champ
obligatoire en base, un entier strictement positif (`HauteurCentreInvalide` sinon). La chaîne
existante `Archer.categorie_id → Categorie` donne au moteur la hauteur de chaque archer sans
nouvelle jointure.

**2. Le pré-chargement FFTA renseigne la hauteur.** `categories_salle_18m()` marque les catégories
**U11 à 110 cm**, toutes les autres à 130 (la constante `_HAUTEUR_CENTRE_U11` vit dans le référentiel,
pas dans le domaine : c'est une donnée FFTA, `docs/referentiel-ffta.md` §5). Une catégorie créée à la
main part du défaut 130 et reste éditable.

**3. La compatibilité de hauteur est une contrainte de placement de 1er rang**, au même rang que
l'espace et les positions : **tous les archers d'une même cible partagent la même hauteur**. Le
moteur ne pose sur une cible un archer d'une hauteur différente de celle déjà installée que sur une
**cible neuve** ; sinon l'archer bascule sur la cible suivante, et faute de cible, il ressort en
**conflit** (rapport de placement, jamais d'échec silencieux — CA « conflits »).

**4. La migration `0020` backfille la donnée existante.** Colonne ajoutée nullable → backfill (130
partout, **110** pour les catégories dont les `ages` contiennent `U11`) → passage NOT NULL, patron
des migrations `0018`/`0019` (le projet n'emploie pas `server_default`).

## Conséquences

- **+** Le moteur de placement ne peut plus produire un plan **intirable** mêlant 110 et 130 cm sur
  une butte : DETTE-002 est **résorbée** (registre mis à jour, marqueurs `# DETTE-002` retirés).
- **+** La hauteur est **éditable** au CRUD catégorie existant (DTO + `PUT`), sans surface nouvelle :
  un surclassement ou une salle atypique s'ajuste sans code.
- **−** Le champ **traverse toute la slice** catégorie (domaine, ORM, repository, service, DTO,
  référentiel, migration) : le coût d'un champ transverse, assumé pour une donnée qui pilote un
  invariant physique.
- **−** Les catégories antérieures à `0020` **non U11** ressortent à 130 même si la salle les monte
  autrement : c'est le défaut FFTA majoritaire, ajustable à la main. Le backfill U11 (par `ages`)
  couvre le seul écart réglementaire connu.
- **Hors périmètre** : les configurations à **plage** de hauteur (4 blasons : ligne haute ≤ 162,
  basse ≥ 100 ; §5) — le mono-club place au centre 130/110, la plage relève d'une contrainte
  avancée (EPIC-03, MVP+1) si un cas réel l'exige.
