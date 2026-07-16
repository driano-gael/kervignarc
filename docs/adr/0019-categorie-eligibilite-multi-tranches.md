# ADR-0019 — La catégorie porte un ensemble de tranches d'âge, pas une tranche unique

- **Statut** : Accepté
- **Date** : 2026-07-16
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E01-configuration.md`](../../stories/E01-configuration.md) (E01US013 :
  périmètre de l'invariant d'éligibilité précisé — propriété du preset, pas contrôle à l'exécution) ;
  [`docs/glossaire.md`](../glossaire.md) (*Tranche d'âge* : les huit tranches FFTA ; *Scratch* et
  *U18 arc nu* deviennent des **libellés** de catégorie) ; [`docs/modele-de-donnees.md`](../modele-de-donnees.md)
  (`CATEGORIE.ages` — déjà cible depuis le cadrage FFTA du 14/07/2026, mise en œuvre ici)
- **Introduit par** : E01US013 ; **corrige** E01US003 (agrégat `Categorie`) et E01US004 (référentiel
  FFTA préchargeable). **Prépare** l'US qui donnera arme/âge/sexe à l'`Archer` et pourra alors
  *vérifier* l'éligibilité (aujourd'hui seulement *garantie* par le preset).

## Contexte et problème

L'agrégat `Categorie` (E01US003) modélisait l'âge par un **scalaire** `tranche_age: str | None` en
texte libre, et le préchargement FFTA (E01US004) encodait les **regroupements** de l'arc nu dans un
tuple de libellés (`_AGES_NU = ("U18", "Scratch")`). Deux défauts en découlaient :

- **`tranche_age` a deux sens selon l'arme.** `"U18"` signifie « U18 seul » en arc classique/poulies,
  mais « U15 **ou** U18 » en arc nu (le classement FFTA regroupe ces deux tranches sous une seule
  catégorie « U18 » — [`docs/referentiel-ffta.md`](../referentiel-ffta.md) §3). Même valeur, deux
  sens : un archer U15 n'est pas rattachable de façon fiable à sa catégorie.
- **« Scratch » n'est pas une tranche d'âge.** C'est le **libellé** d'un regroupement arc nu
  (U21+S1+S2+S3), stocké à tort comme une valeur de `tranche_age`.

Le texte libre n'imposait par ailleurs aucun vocabulaire : `"senior"`, `"cadet"`, `"vétéran"`
coexistaient avec les codes FFTA, sans qu'aucun invariant d'éligibilité ne soit exprimable.

## Options

1. **Garder le scalaire** — écarté : ne peut pas représenter un regroupement, laisse « U18 »
   ambigu, et « Scratch » restant une pseudo-tranche.
2. **`ages` = ensemble de tranches d'un vocabulaire fermé** (retenu) — une catégorie porte **une ou
   plusieurs** tranches ; les regroupements deviennent des libellés découplés de la liste.
3. **Option 2 + vérification d'éligibilité sur l'archer** (l'archer ne pourrait rejoindre qu'une
   catégorie couvrant sa tranche) — **reporté**, pas retenu dans cette US : l'agrégat `Archer` ne
   porte aujourd'hui **ni arme, ni âge, ni sexe** (juste `categorie_id`). Vérifier l'éligibilité
   exigerait de l'en doter — un tout autre périmètre. Le périmètre écrit de l'US ne mentionne pas
   `domain/archer.py`, cohérent avec ce report.

## Décision

- **`Categorie.ages: tuple[TrancheAge, ...]` remplace `tranche_age`.** `TrancheAge` est un **enum
  fermé** des huit tranches FFTA (`U11, U13, U15, U18, U21, S1, S2, S3`, §2). `ages` est un
  **ensemble** d'éligibilité : dédoublonné et **ordonné canoniquement** (U11 → S3) à la construction,
  pour que deux catégories aux mêmes tranches soient égales. Vide = **aucune contrainte d'âge**
  (pendant de l'ancien `None`), permis pour une catégorie créée à la main, jamais pour le preset.
- **Les regroupements sont des libellés, pas des tranches.** Le référentiel encode « U18 » (arc nu)
  → `ages = (U15, U18)` et « Scratch » → `ages = (U21, S1, S2, S3)` ; le **libellé** affiché est
  découplé de la liste d'âges. « Scratch » disparaît des valeurs de tranche.
- **Vocabulaire fermé à la frontière.** Le DTO API prend `list[TrancheAge]` : une valeur hors des
  huit tranches est rejetée en **400** (Pydantic), le domaine n'en voit jamais (règle 6).
- **L'invariant « un archer (arme, âge, sexe) n'est éligible qu'à une seule catégorie » est une
  propriété *du preset*, testée, non un contrôle à l'exécution.** On le vérifie sur le jeu FFTA : à
  (arme, sexe) fixés, les tranches des catégories sont **disjointes** — tout triplet retombe donc sur
  au plus une catégorie. La vérification runtime est **reportée** à l'US qui modélisera arme/âge/sexe
  sur l'`Archer` (cf. option 3).
- **Stockage** : `ages` est persisté en **tableau JSON de codes** (`["U15","U18"]`,
  [`docs/modele-de-donnees.md`](../modele-de-donnees.md)), (dé)sérialisé par le repository sur le
  patron de la `config` des gabarits/phases ; un contenu illisible → `InfrastructureError` (ADR-0007).
- **Migration `0018` de données, pas seulement de schéma.** La colonne scalaire devient `ages` et les
  valeurs sont **reconstruites** depuis `(arme, tranche_age)` : `("Arc Nu","U18")` → `["U15","U18"]`,
  `"Scratch"` → `["U21","S1","S2","S3"]`, une tranche FFTA → `[tranche]`, sinon (texte libre non
  reconnu, ou vide) → `[]`. Une reconstruction naïve `"U18"` → `["U18"]` ré-introduirait le bug.

## Conséquences

- **+** Le modèle colle au classement FFTA : les regroupements arc nu sont exprimés fidèlement, et le
  vocabulaire des tranches est fermé (plus de `"senior"` ambigu).
- **+** Le front passe d'un champ texte libre à une **sélection multiple** des huit tranches.
- **−** **On retravaille du livré** (E01US003 + E01US004) et on migre des données. Coût contenu :
  pré-production (J1), volume faible, et la migration reconstruit les regroupements plutôt que de les
  perdre. Une catégorie au **texte libre non mappable** (`"senior"`) perd sa contrainte d'âge (`[]`) —
  elle n'était de toute façon pas exploitable.
- **−** **L'invariant d'éligibilité n'est pas garanti à l'exécution.** Rien n'empêche encore un admin
  de créer deux catégories aux tranches qui se chevauchent ; seul le **preset** est prouvé disjoint.
  Le garde-fou runtime attend que l'`Archer` porte arme/âge/sexe (report explicite, pas un oubli).
- **−** **`Categorie.ages` reste sans consommateur métier avant** cette US-là et le placement : une
  liste de tranches ne *classe* effectivement un archer que lorsqu'on compare son âge à `ages`. Ce
  n'est pas une donnée morte pour autant — c'est une donnée de **configuration** éditée dès ici.

## Liens

[ADR-0006](0006-ubiquitous-language.md) (vocabulaire `Categorie`, français FFTA) ;
[ADR-0007](0007-erreurs-par-couche.md) (incohérence de (dé)sérialisation → `InfrastructureError`) ;
[`docs/referentiel-ffta.md`](../referentiel-ffta.md) (§2 tranches, §3 catégories par division) ;
[`docs/modele-de-donnees.md`](../modele-de-donnees.md) (`CATEGORIE.ages`) ;
[`docs/glossaire.md`](../glossaire.md) (*Tranche d'âge*, *Scratch*) ;
[`stories/E01-configuration.md`](../../stories/E01-configuration.md) (E01US013).
