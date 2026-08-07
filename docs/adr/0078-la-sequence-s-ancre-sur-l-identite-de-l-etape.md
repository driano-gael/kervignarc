# ADR-0078 — La séquence s'ancre sur l'identité de l'étape, pas sur son rang

- **Statut** : Accepté
- **Date** : 2026-08-07
- **Décideurs** : Organisateur / Architecte
- **Amende** : [ADR-0045](0045-sequence-de-phases-cycle-de-vie-typage-source.md) §3 (`SourcePhase`
  désigne sa source par `ordre_source`) et [ADR-0076](0076-un-deroule-defini-une-fois-un-avancement-par-depart.md)
  (le rang sert de clé de jointure définition ↔ avancement)
- **Résorbe** : [DETTE-026](../dette.md) — une source de phase est ancrée par `ordre`, pas par
  identité
- **Introduit par** : arbitrage du commanditaire du 07/08/2026, sur constat de dépassement du seuil
  de la règle 16

## Contexte et problème

Depuis E05US001, une source de phase désigne sa phase amont par son **rang dans la séquence**
(`SourcePhase.ordre_source`), pas par son identité. Toute opération qui renumérote — réordonner,
supprimer avec recompactage, insérer la qualification en tête — doit donc **réécrire** les
références de toutes les phases qui citaient la phase déplacée.

Le registre avait explicitement décidé d'attendre : « règle 16 : 2 sites aujourd'hui, on ne pose pas
de pattern ». **Ce rendez-vous a eu lieu.** ADR-0076 a changé trois choses le même jour :

1. **le rang n'est plus seulement la clé de la séquence, il est aussi la clé de jointure**
   définition ↔ avancement. `Phase` ne porte plus sa définition : elle la reçoit de l'étape de
   **même `ordre`**. Un rang mal remappé ne fait donc plus seulement pointer une *source* vers la
   mauvaise phase — il fait exécuter à un créneau le **barème, le grain et les prélèvements d'une
   autre étape**, sans erreur ni signal ;
2. **les écrivains passent de 2 à 4** : `ServicePhases._remapper` et
   `ServiceBaremeQualification._decaler_dun_cran` sont rejoints par `DerouleRepository.reordonner`
   et `PhaseRepository.reordonner` — deux méthodes de port **dont l'unique raison d'être** est de
   garer les rangs hors de portée avant de les reposer, pour contourner l'unicité
   `(tournoi, ordre)` / `(départ, ordre)` ;
3. `DETTE-025` s'en trouve aggravée : ces écritures n'étant pas atomiques, une panne fige
   précisément l'état où les rangs mentent.

La preuve est donc **dans le code d'aujourd'hui**, pas dans une évolution supposée : 4 occurrences
réelles, un invariant déjà dupliqué, et une conséquence qui est passée de « source mal ancrée » à
« mauvais barème exécuté ».

## Décision

**Le lien entre une phase et sa définition, et entre une source et sa phase amont, passe par une
identité — le rang ne décrit plus que l'ordre d'affichage.**

1. **`phase.etape_id → deroule_etape.id`** (clé étrangère). Le rang reste porté par la **seule**
   étape ; l'avancement d'un créneau n'a plus besoin d'en connaître un.
2. **`SourcePhase.ordre_source` devient `etape_source_id`** dans les `config` d'une **édition
   concrète** (`deroule_etape`), avec migration des JSON existants.
3. **`FormatTournoi` garde l'ancrage par `ordre`** — et c'est la partie asymétrique de la décision.
   Ses `ModelePhase` n'ont **pas** d'identité, par construction ([ADR-0060](0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md) §5) :
   un format de bibliothèque décrit un déroulé *type*, réutilisable, dont les étapes n'existent
   dans aucun tournoi. L'ancrage par ordre y est **correct**, pas dégradé.
4. **La conversion se fait à l'application du format** : `appliquer` crée les étapes, obtient leurs
   identités, puis résout les `ordre_source` du modèle en `etape_source_id` concrets. C'est le seul
   endroit où les deux mondes se touchent, et c'est déjà celui qui matérialise le déroulé.
5. **Les deux `reordonner` de port disparaissent** : renuméroter ne touche plus qu'une colonne
   `ordre` sans signification relationnelle, donc plus aucun état transitoire à doublon, donc plus
   d'écriture d'ensemble à orchestrer. `DETTE-025` s'en trouve allégée d'autant.

### Le contre-argument, et pourquoi il est écarté

`infrastructure/db/models.py` porte l'objection, et elle est sérieuse — elle mérite d'être citée
plutôt que résumée : *« le déroulé s'édite par rang — un réordonnancement remappe déjà les ordres
partout (DETTE-026), et une FK dupliquerait l'information tout en pouvant en diverger »*.

**Ce qui la rendait juste, et ce qui ne l'est plus.** L'argument suppose que le rang est la source
de vérité du lien, la FK n'en étant qu'un double. C'était exact tant que la séquence *était* le
modèle. Depuis ADR-0076, le rang porte **deux** rôles — l'ordre d'affichage **et** l'appariement
définition ↔ avancement — et ce sont eux qui divergent : c'est le cumul des deux rôles sur une même
colonne qui produit le « mauvais barème silencieux », pas la présence d'une FK.

Le remède ne duplique donc pas l'information : il la **sépare**. `etape_id` dit *quoi*, `ordre` dit
*où dans la liste*. Une fois séparés, aucun des deux ne peut mentir sur l'autre — et l'unicité
`(tournoi, ordre)` peut même être relâchée si un jour un réordonnancement transitoire l'exige.

### Autres options écartées

- **Garder l'ordre et rendre les écritures atomiques** (résorber `DETTE-025` seule). Cela ferme la
  fenêtre de panne, pas la **charge de vigilance** : tout futur écrivain devra encore penser au
  remappage, et l'oublier resterait silencieux. On traiterait le symptôme.
- **Un identifiant stable non-FK** (UUID posé sur l'étape, cité dans la `config`). Évite la
  migration de schéma mais perd l'intégrité référentielle — donc rend possible exactement ce qu'on
  veut interdire : une source citant une étape disparue.

## Conséquences

**Positives**

- **La classe d'erreurs entière disparaît.** Il n'y a plus rien à remapper : les 4 écrivains
  perdent leur raison d'exister, et `PhaseSourceReferencee` devient une garde d'intégrité
  référentielle plutôt qu'une vérification applicative.
- **`DETTE-025` est allégée** : moins d'écritures à réunir, et celles qui restent ne peuvent plus
  produire d'appariement faux.

**Coûteuses / à surveiller**

- **Migration des `config` JSON** d'une table (`deroule_etape`), plus la colonne `phase.etape_id`.
  La reprise doit résoudre `ordre_source → etape_source_id` **avant** de perdre les rangs.
- ⚠️ **L'asymétrie format ↔ édition est permanente**, pas transitoire. Deux ancrages coexistent, et
  quiconque lit `SourcePhase` devra savoir lequel il tient. C'est le prix de la décision, et il faut
  qu'un lecteur puisse le comprendre sans relire cet ADR : les deux formes doivent porter des
  **noms différents** dans le code, jamais un champ polymorphe.
- **Le rang ne disparaît pas** : il reste la donnée que l'organisateur manipule à l'écran (« la
  phase 2 »). On lui retire son rôle relationnel, pas son rôle d'interface.

## Porté dans le code par

*(à renseigner par l'US de résorption — cet ADR est une décision. La section nommera : `domain/phase.py`
(`SourcePhase`), `domain/deroule_etape.py`, `infrastructure/db/models.py` (`PhaseORM.etape_id`,
FK), la migration de reprise, `application/formats.py` (`appliquer`, seul point de conversion
modèle → édition), et la disparition de `DerouleRepository.reordonner` / `PhaseRepository.reordonner`
dans `domain/ports.py`.)*
