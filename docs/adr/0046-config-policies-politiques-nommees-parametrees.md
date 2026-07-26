# ADR-0046 — `config.policies` : politiques nommées et paramétrées (résorption de DETTE-003)

- **Statut** : Accepté
- **Date** : 2026-07-26
- **Décideurs** : Organisateur / Architecte
- **Amende** : [ADR-0011](0011-phase-qualification-anticipee.md) (forme de `config` de la phase de
  qualification) · **Précise** : [ADR-0004](0004-moteur-de-phases-politiques.md) (moteur à
  politiques injectables)
- **Résorbe** : [DETTE-003](../dette.md)

## Contexte et problème

E05US003 introduit les **politiques injectables** du moteur de phases (ADR-0004) : six familles
(`routing`, `scoring`, `seeding`, `byes`, `tiebreak`, `depth`), chacune une interface du domaine
assemblable par la `config` JSON d'une phase. Avant d'écrire ce moteur, il faut trancher **DETTE-003**
— deux conventions contradictoires coexistaient pour la même `config`, et rien dans le code ne disait
laquelle faisait foi :

1. **Où logent les politiques ?** L'implémentation (E01US009) les écrit **à plat à la racine**
   (`{"scoring": {…}}`) ; le modèle cible (ADR-0004, `modele-de-donnees.md`) les range sous
   **`config.policies`**.
2. **Comment une politique est-elle désignée ?** L'implémentation écrit `scoring` en **objet
   paramétré** (`{"volees": 20, "fleches": 3, "mode": "cumul"}`) ; le modèle cible d'origine
   suggérait un **nom de preset** fermé (`"sets_4pts"`).

DETTE-003 avait **volontairement** laissé la question ouverte : la trancher demandait de savoir « ce
que le moteur attend », et figer la forme au fil d'une US de configuration, **avant** le seul code
qui la consomme, aurait été le reproche exact qu'on ferait à l'inverse. E05US003 **est** ce moment :
le moteur arrive, la forme peut se décider sur pièces.

## Décision

### 1. Les politiques vivent sous `config.policies`

On adopte la forme cible d'ADR-0004. La `config` d'une phase distingue désormais explicitement les
**politiques du moteur** (sous `policies`) du reste de la configuration :

```json
{
  "policies": { "scoring": {"nom": "cumul", "volees": 20, "fleches": 3} },
  "validation": {"grain": "fin_de_serie"},
  "source": {"ordre_source": 1, "rang_debut": 1, "rang_fin": 16},
  "effectif": 16
}
```

**Pourquoi maintenant** : DETTE-003 objectait que `policies` « n'a de sens que face à plusieurs
politiques hétérogènes ». C'est précisément ce qu'E05US003 introduit — six familles. Le regroupement
**gagne sa place** au moment où il cesse d'être une abstraction à clé unique. Il donne au moteur un
point d'accès unique (« les politiques de cette phase ») et sépare nettement ce qui est **stratégie
injectable** de ce qui n'en est pas.

### 2. Une politique = un **nom** d'implémentation **et** des **paramètres**

Chaque politique est un objet `{"nom": <implémentation>, …paramètres}`. Le `nom` sélectionne
l'implémentation (résolue par le registre, cf. §4) ; les autres clés la paramètrent.

**Pourquoi ni l'un ni l'autre des deux extrêmes** : le barème de qualification se **paramètre**
librement (nb de volées × nb de flèches, « valeurs modifiables », CA E01US009) — un **nom de preset**
seul (catalogue fermé `"cumul"`) ne saurait le porter. Mais un objet paramétré **sans nom** ne dit
pas *quelle* implémentation appliquer quand plusieurs coexistent pour un même type (duel par sets
*vs* finales 6 pts). Le couple **nom + paramètres** réconcilie les deux : il nomme la stratégie **et**
la règle.

### 3. Le grain de `validation` **n'est pas** une politique de moteur → hors `policies`

ADR-0004 énumère six familles de politiques ; le **grain de validation** (`fin_de_serie`,
`fin_de_duel`, `toutes_les_n_volees`) n'en fait pas partie — c'est une cadence de **saisie/validation**
(`D-11`, E01US015), pas une stratégie du moteur de tableau. Il reste donc **à la racine** de `config`,
à côté (et non à l'intérieur) de `policies`. Cela **tranche une incohérence de documentation** :
l'exemple cible de `modele-de-donnees.md` plaçait tantôt `validation` sous `policies`, tantôt à côté,
avec une clé `policies` dupliquée. La règle est désormais : **sous `policies`, les six familles
d'ADR-0004, et elles seules**. L'assemblage refuse toute autre clé (`PolitiqueMalFormee`).

De même, `source` (peuplement) et `effectif` (dimensionnement) restent **à la racine** : ce sont des
données de la phase, pas des politiques.

### 4. L'assemblage est résolu par la composition root

Le domaine définit les interfaces (`Protocol`) et une implémentation par famille (stratégies
**pures**), plus un `RegistrePolitiques` (catalogue `nom → fabrique` par famille) et une fonction
`assembler_politiques(config.policies, registre) → PolitiquesPhase`. La **composition root** peuple
le registre (`registre_par_defaut()`), conformément à la règle 2 (le domaine définit, le bootstrap
assemble) : ajouter une implémentation = l'enregistrer, sans toucher au domaine. C'est le point
d'injection concret d'ADR-0004 — « un format est de la **configuration**, pas du code ».

### 5. Migration + relecture tolérante

- **Migration de données** `0028_phase_config_policies` : réécrit les lignes `phase` existantes
  (`config.scoring` racine → `config.policies.scoring`, `mode` → `nom`). Idempotente.
- **Relecture tolérante** : `repositories._lire_scoring` lit la forme cible **ou** l'ancienne forme à
  plat — filet pour une base restaurée d'une **sauvegarde antérieure** à la migration. Même patron
  « politique sans migration » que le grain (ADR-0011). Le barème ne dépend jamais du champ
  `mode`/`nom` (seuls `volees`/`fleches` l'alimentent), donc les deux formes se relisent à l'identique.

## Conséquences

- **+** DETTE-003 est **résorbée** : une seule convention fait foi, alignée sur le modèle cible.
- **+** Le moteur (E05US005/E05US010) dispose d'un socle de politiques éprouvé et d'un point
  d'assemblage unique ; ajouter un format n'ajoute pas de code moteur.
- **+** La documentation (`modele-de-donnees.md`, ADR-0004) est réconciliée avec le code.
- **−** Les implémentations de ce socle sont volontairement **minimales** : les stratégies couplées à
  la structure d'arbre (`routing` en cascade, `scoring` par sets) exposent leur méthode **fondatrice**
  et seront **enrichies** par les US consommatrices (extension du contrat, pas rupture). C'est le
  risque que DETTE-003 signalait — sur-geler la forme du `scoring` avant le moteur : on l'assume en
  gardant les interfaces étroites et honnêtes, plutôt qu'en inventant des signatures spéculatives.
- **−** `PolitiquesPhase` n'est pas encore **consommé** par un moteur (E05US005 le fera) : le socle
  est livré testé et câblé, mais sa valeur d'usage n'apparaît qu'à l'US suivante. Assumé : c'est une
  US de **fondation** (ex-E05US003 « interfaces » = cœur d'ADR-0004).

## Liens

ADR-0004 (moteur à politiques injectables), ADR-0011 (Phase minimale, forme `config` d'origine),
ADR-0045 (séquence de phases) ; [`docs/dette.md`](../dette.md) DETTE-003 ;
[`docs/modele-de-donnees.md`](../modele-de-donnees.md) § « Config d'une PHASE » ;
`stories/E05-moteur-phases.md` (E05US003).
