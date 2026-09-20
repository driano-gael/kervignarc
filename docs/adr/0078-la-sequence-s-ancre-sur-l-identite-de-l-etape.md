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

## Amendements (E05US022, 20/09/2026)

Deux points de cet ADR ont été **corrigés en le mettant en œuvre**, parce qu'ils décrivaient le
code tel qu'on l'imaginait, pas tel qu'il est.

**1. §5 sur-promettait — une seule des deux méthodes disparaît d'elle-même.**
Le §5 annonçait que « les deux `reordonner` de port disparaissent », au motif que renuméroter « ne
touche plus qu'une colonne sans signification relationnelle, donc plus aucun état transitoire à
doublon ». Le premier terme est juste, le second ne l'était pas :
`PhaseRepository.reordonner` disparaît bien (la colonne `phase.ordre` n'existe plus), mais
`DerouleRepository.reordonner` n'existait **pas** à cause de l'ancrage — il existait à cause de la
contrainte SQL `uq_deroule_tournoi_ordre`, qu'ADR-0078 ne touchait pas. Échanger deux rangs voisins
transitait par un doublon quel que soit l'ancrage.

⚠️ **Sur `DETTE-025`, en revanche, le §5 disait vrai et c'est son amendement qui se trompait**
(relevé en revue, axe C2, et vérifié) : `ServicePhases.reordonner` passait de **deux** écritures
(le réordonnancement, puis le réalignement des avancements — une par créneau) à **une seule**. La
dette est donc bien **allégée**, comme l'ADR l'annonçait. La première rédaction de cet amendement
affirmait le contraire : avoir corrigé l'ADR là où il sur-promettait avait entraîné à le
« corriger » là où il disait juste.

**Arbitrage du commanditaire, 20/09/2026** : **relâcher l'unicité** — issue que la section
« contre-argument » de cet ADR envisageait déjà (« l'unicité `(tournoi, ordre)` peut même être
relâchée si un jour un réordonnancement transitoire l'exige »). Le rang ne désignant plus rien, le
second verrou n'avait plus de rôle à défendre, et il coûtait une manœuvre en deux passes dont
l'oubli d'un `flush` produisait une collision au hasard des exécutions. La suite 1..N reste tenue
par le domaine (`verifier_sequence`), à chaque écriture. Ce qui subsiste est une méthode
honnêtement nommée — `enregistrer_plusieurs` —, gardée pour l'**atomicité** seule : une
renumérotation à moitié écrite laisserait une séquence trouée à l'écran.

**2. §4 ne nommait qu'un sens de la conversion ; il y en a deux.**
Le §4 décrit le passage modèle → édition, à l'application d'un format. Le sens inverse existe
aussi et l'ADR l'ignorait : la **promotion** (`FormatTournoi.de_deroule`) capture le déroulé d'un
tournoi en brique de bibliothèque, et doit donc redescendre des identités vers des rangs. Le même
besoin réapparaît pour entrer dans le **moteur**, qui raisonne en rangs et dont les anomalies
parlent à l'organisateur de « la phase 2 ». Les deux emprunte la même traduction
(`projeter_sur_les_rangs`), pour qu'il n'y ait pas deux versions à garder d'accord.

**3. Conséquence non prévue : `appliquer` ne peut plus être une fonction pure.**
Ancrer un prélèvement demande l'identité de l'étape visée, que seule la persistance attribue.
`FormatTournoi.appliquer` — qui rendait un déroulé complet d'un seul appel — est donc scindé en
`verifier_applicable()` (le garde, appelable **avant** toute écriture, ce qui préserve la garantie
« instancier avant de détruire » d'E01US024) et une pose **incrémentale** dans le service. Elle est
correcte parce qu'une source ne vise jamais qu'une phase **antérieure** : quand l'étape *k* se
pose, les étapes 1..*k-1* sont déjà écrites, donc déjà identifiées.

## Porté dans le code par

*(Renseigné par E05US022, le 20/09/2026, **en ouvrant chaque module cité** — pas en déduisant de la
décision. Deux points de cet ADR ont été corrigés à cette occasion : voir § « Amendements ».)*

- **`backend/domain/phase.py`** — `Prelevement` (le socle commun), `SourceModele` (ancre par rang)
  et `SourcePhase` (ancre par identité), les deux traductions `ancrer_sur_les_etapes` /
  `projeter_sur_les_rangs`, et `VueParRangs` / `vues_par_rangs`, par lesquelles une édition
  concrète entre dans les contrôles de séquence. `Phase.etape_id` y est déclaré ; `Phase.ordre`
  subsiste comme **rang d'affichage**, dérivé de l'étape et non persisté.
- **`backend/domain/deroule_etape.py`** — `EtapeDeroule.instancier`, qui pose `etape_id` sur
  l'avancement, plus `table_des_rangs` et `vues_du_deroule`.
- **`backend/domain/format_tournoi.py`** — `ModelePhase.sources` reste en `SourceModele` (§3) ;
  `ModelePhase.pour_tournoi` et `ModelePhase.d_etape` **sont** les deux sens de la conversion (§4) ;
  `FormatTournoi.verifier_applicable` et `FormatTournoi.etapes_ordonnees` ont remplacé
  `FormatTournoi.appliquer`. ⚠️ `verifier_applicable` **pose ET instancie à blanc** : les
  invariants d'`EtapeDeroule` et les quatre gardes de `Phase.__post_init__` (`DETTE-078`) ne se
  lèvent qu'à la construction, et `ServiceFormats.appliquer` détruit le déroulé en place avant de
  poser le neuf. Sans les deux moitiés, un format invalide laissait le tournoi sans phases.
- **`backend/domain/ports.py`** — `PhaseRepository.reordonner` a **disparu** ;
  `DerouleRepository.reordonner` est devenu `enregistrer_plusieurs` (§5, amendé ci-dessous).
- **`backend/application/formats.py`** (`ServiceFormats.appliquer`) et
  **`backend/application/simulation_format.py`** — les **deux** sites qui matérialisent un format :
  ils posent les étapes dans l'ordre des rangs et enrichissent la table au fur et à mesure.
  ⚠️ Jumeaux : les faire diverger ferait simuler un déroulé dont les prélèvements ne sont pas ceux
  du vrai.
- **`backend/application/phases.py`** — `_remapper` et `_realigner_avancements` ont **disparu** ;
  la garde `PhaseSourceReferencee` compare désormais des identités.
- **`backend/application/bareme_qualification.py`** — `_decaler_dun_cran` a **disparu** : insérer
  la qualification en tête ne décale plus qu'un rang.
- **`backend/application/prelevement.py`** et **`backend/application/saisie_duels.py`** — le
  résolveur de classement (`ResolveurClassement`, `_classement_de_l_etape`) est indexé sur
  l'identité ; `ClassementSource.ordre` reporte le rang, **pour les messages seulement**.
- **`backend/application/palmares.py`** et **`backend/application/routage.py`** — les deux lectures
  du graphe des sources (« rien ne prélève ici » ; « où vont les perdants ») comparent des
  identités.
- **`backend/infrastructure/db/models.py`** — `PhaseORM.etape_id` (FK vers `deroule_etape.id`),
  `uq_phase_depart_etape`, et la disparition de `PhaseORM.ordre` comme de
  `uq_deroule_tournoi_ordre`.
- **`backend/infrastructure/db/repositories/moteur.py`** — `_source_json` (le **seul** endroit du
  dépôt où les deux ancres se croisent), `_vers_sources_d_etape` / `_vers_sources_de_modele`, et
  `PhaseRepositorySQL._etapes` / `_assembler`, qui joignent par identité.
- **`backend/infrastructure/memory/repositories.py`** — le jumeau en mémoire
  (`InMemoryPhaseRepository._etape`).
- **`backend/migrations/versions/0056_ancrage_par_identite.py`** — la reprise : `phase.etape_id`
  rempli par la jointure d'hier, les `config` réécrites, puis seulement le retrait du rang.
- **`frontend/src/features/phases/`** (`api.ts`, `source.ts`, `Phases.tsx`) — le côté édition
  concrète. **`frontend/src/features/patrimoine/` et `features/deroule/` ne changent pas** : ils
  éditent un format de bibliothèque, dont l'ancrage par rang est correct (§3).

**Ce que la section ne peut pas promettre.** L'asymétrie §3 n'est tenue par aucun test mécanique :
rien n'empêche un futur développeur de réunir `SourceModele` et `SourcePhase`. Ce qui la défend est
le typage (`ModelePhase.sources` n'accepte pas un `SourcePhase`) et le fait que `_source_json`
choisisse sa clé sur la classe — un mélange casserait la sérialisation, donc bruyamment.
