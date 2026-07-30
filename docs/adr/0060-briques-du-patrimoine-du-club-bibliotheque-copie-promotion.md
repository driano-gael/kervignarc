# ADR-0060 — Les briques de configuration sont le patrimoine du club : bibliothèque, copie, promotion

- **Statut** : Accepté
- **Date** : 2026-07-30
- **Décideurs** : Organisateur / Architecte
- **Portée** : E01US023 (catégories, blasons et formats de tournoi hors périmètre d'un tournoi)
- **Lie** : [ADR-0011](0011-phase-minimale-et-passive.md) et [ADR-0045](0045-sequence-de-phases-cycle-de-vie-typage-source.md)
  (la `Phase` et l'invariant de séquence que cet ADR **ne** touche pas),
  [ADR-0020](0020-blason-zones-vocabulaire-ferme-et-defaut-sur-ensemble.md) (RG-8 : le règlement est
  un template, jamais une contrainte), [ADR-0058](0058-decoupage-de-l-admin-en-trois-axes-d-activite.md)
  (l'axe *atelier* dont cet ADR tient enfin la promesse),
  [DETTE-023](../dette.md#dette-023--latelier-affiche-des-briques-encore-scopées-par-tournoi) (résorbée)

## Contexte et problème

E14US003 range l'appli admin en trois axes d'activité. L'axe **atelier** annonce « fabriquer, **hors
tournoi** » : c'est le patrimoine du club, il vit d'année en année. Huit destinations y sont rangées,
**quatre ne tiennent pas la promesse** — catégories, blasons, barème et phases portent toutes un
`tournoi_id` obligatoire. L'atelier affiche donc « Choisissez un tournoi ci-dessus » sur la moitié de
ses écrans, sans proposer de sélecteur puisque, par construction, il n'en a pas.

Le pré-chargement FFTA en est le symptôme de fond : `precharger_ffta` **recrée** les quatre blasons
canoniques et les catégories officielles **à chaque tournoi**, faute d'un endroit où les ranger une
fois pour toutes. Le référentiel officiel — le moins variable de toutes les données du produit — est
la chose que l'on duplique le plus.

La question posée est donc : **de quoi une brique de configuration est-elle la propriété ?** Du
tournoi qui l'utilise, ou du club qui la possède ?

## Décision

**Une brique appartient au club ; un tournoi en détient une copie.**

### 1. Deux formes distinguées par `tournoi_id`

- `tournoi_id is None` — **modèle de bibliothèque**, patrimoine du club, réutilisable d'une année sur
  l'autre, n'appartenant à aucune édition ;
- `tournoi_id` renseigné — **copie** d'un tournoi, ajustable **sans altérer le modèle**.

Ce n'est **pas un patron neuf** : `gabarit_salle` l'applique depuis E01US007/E01US008 (« appliquer un
modèle (copie), lire et ajuster la copie sans altérer le modèle »). E01US023 le **généralise**. C'est
ce qui rend le changement petit — et cet ADR court.

Le port gagne une lecture `par_bibliotheque()` **distincte** de `par_tournoi()`, et non un
`par_tournoi(None)` : ce sont deux lectures de nature différente, et les confondre laisserait un
appelant demander « les catégories du tournoi `None` ».

### 2. Copier, pas référencer

Assembler un tournoi **copie** la brique. Alternative écartée : que le tournoi **référence** la
brique de bibliothèque.

Le motif est l'**immuabilité de l'archive**, tranché avec le commanditaire le 30/07/2026 : si un
tarif ou un barème change en 2027, le tournoi 2026 archivé **ne doit pas bouger**. Une brique
référencée réécrirait rétroactivement l'histoire de toutes les éditions passées — ce que l'archive en
lecture seule (EPIC-11) et le journal d'audit interdisent. Un classement publié doit rester lisible
avec les règles sous lesquelles il a été établi.

**Contrepartie assumée, et elle est réelle** : un tournoi encore en **brouillon** n'hérite pas d'une
correction faite ensuite dans la bibliothèque — il faut lui réappliquer la brique. On accepte de
recopier parfois pour ne jamais mentir sur le passé.

### 3. La promotion remonte, sans rétroagir

« Si les modifications sont permanentes, on doit pouvoir le dire — cela modifiera la brique de base de
l'atelier. » Une modification faite sur la copie d'un tournoi et déclarée **permanente** est donc
**promue** dans la bibliothèque.

La promotion ne réécrit pas l'histoire pour autant : les tournois **déjà assemblés gardent leur
copie**, seuls les **prochains** assemblages héritent de la correction. C'est le pendant exact du
point 2 — la copie protège le passé dans les deux sens de circulation.

### 4. `OrigineBrique` marque la provenance, pas la conformité

Une brique porte `origine ∈ {ffta, utilisateur}`. Elle sert les **deux listes séparées** demandées par
le commanditaire, et permet, en modifiant un officiel, d'en faire une **copie** plutôt que de
l'écraser.

⚠️ **Cette marque ne dit pas « conforme FFTA ».** Elle dit d'où vient la brique — pas si elle a été
modifiée depuis, ni contre **quelle version** du règlement elle a été établie. Le référentiel
versionné et le contrôle de conformité relèvent d'un lot ultérieur ; tant qu'ils n'existent pas,
`FFTA` signifie « issue du préchargement officiel », rien de plus. C'est cohérent avec RG-8
(ADR-0020) : l'application n'impose ni ne vérifie la conformité au règlement.

### 5. Pour les phases, la brique réutilisable est le **format**, pas la phase

C'est le seul endroit où la généralisation du point 1 **ne s'applique pas**, et il faut dire pourquoi.

Rendre `Phase.tournoi_id` nullable, comme pour les catégories et les blasons, était le geste attendu.
Le code l'interdit, pour deux raisons :

1. **Le barème n'est pas une entité.** Il vit dans la `config` de la phase de type `qualification`
   (`application/bareme_qualification.py`) : il n'y a aucune colonne `tournoi_id` à relâcher.
2. **L'invariant d'une phase est collectif.** Une `Phase` porte `ordre`, `statut`, `source` et
   `effectif` ; `SequencePhases` (ADR-0045 §3) exige que les ordres forment la suite **contiguë
   1..N**. Des phases de bibliothèque au `tournoi_id` nul porteraient un `statut = a_venir` vide de
   sens et des `ordre` en collision les uns avec les autres ; `par_bibliotheque()` renverrait
   `[1, 1, 2, 1…]` et la première composition lèverait `SequenceOrdreInvalide`. Il aurait fallu
   **désarmer** l'invariant qui protège le moteur de phases — payer en sûreté du moteur une
   commodité d'écran.

Ce qui se réutilise d'une année sur l'autre n'est d'ailleurs pas *une phase* : c'est le **format** —
« FFTA officiel : qualification 20×3 en fin de série, puis élimination directe à 16 ». On introduit
donc un agrégat `FormatTournoi` : un nom, une origine, et une **séquence de modèles de phases**
(type, barème, grain, effectif, source) **sans statut ni tournoi**. L'appliquer crée les `Phase` du
tournoi ; le `statut` et le `tournoi_id`, qui n'ont de sens que dans une édition, **naissent à
l'application** — ils ne sont pas « vidés » dans le modèle, ils n'y existent pas.

C'est le même patron qu'aux points 1 à 3 (modèle → copie → promotion), à une maille au-dessus : le
modèle n'est pas une phase mais une **séquence** de phases.

## Conséquences

**Positives**

- L'axe atelier tient sa promesse : ses huit destinations sont réellement hors tournoi (DETTE-023
  résorbée).
- Le référentiel FFTA est chargé **une fois** dans la bibliothèque, plus à chaque tournoi.
- L'archive reste vraie sans effort particulier : elle l'est par construction, pas par discipline.
- Le typage sépare enfin deux choses qui se ressemblaient : un modèle et une instance.

**Négatives, assumées**

- **Un brouillon n'hérite pas d'une correction ultérieure** (point 2). C'est le prix de l'archive
  immuable ; l'écran doit rendre la réapplication facile plutôt que prétendre que le problème
  n'existe pas.
- **La donnée est dupliquée** : chaque tournoi porte sa copie de chaque brique. À l'échelle d'un club
  mono-site (règle 12), c'est quelques centaines de lignes par édition — sans commune mesure avec le
  coût d'une archive fausse.
- **`origine` ne survit pas à une modification** : une brique FFTA modifiée sur place reste marquée
  `ffta` alors qu'elle diverge du règlement. C'est **délibéré** (le règlement évolue, l'organisateur
  doit pouvoir suivre) mais cela ferme la porte à tout contrôle de conformité tant que la **version**
  du règlement n'est pas modélisée.
- **La migration ne peut pas reconstituer l'origine du passé** : `precharger_ffta` était idempotent
  **par nom**, sans marque en base. Les lignes existantes prennent donc `origine = utilisateur` — le
  seul défaut honnête, faute de pouvoir distinguer après coup une catégorie officielle d'une création
  du club.
- **`FormatTournoi` est un agrégat de plus** à maintenir en parallèle de `Phase`, avec le risque
  classique de dérive entre le modèle et ce que le moteur sait dérouler. Le garde-fou est que
  l'application d'un format passe par les **fabriques de `Phase`** : un format qui décrirait une
  phase impossible échoue à l'application, pas silencieusement à l'exécution.

## Alternatives écartées

| Alternative | Pourquoi écartée |
|---|---|
| **Référencer** la brique de bibliothèque depuis le tournoi | Réécrit l'histoire des éditions archivées (point 2) — rédhibitoire vis-à-vis d'EPIC-11 et du journal d'audit |
| `tournoi_id` nullable sur `Phase` | Casse l'invariant `SequencePhases` 1..N ; exigerait de désarmer le garde-fou du moteur de phases (point 5) |
| `par_tournoi(None)` plutôt qu'une lecture `par_bibliotheque()` dédiée | Confond deux lectures de nature différente et autorise « les catégories du tournoi `None` » |
| Versionner les briques (chaque tournoi pointe une **version** figée) | Répond au même besoin que la copie, pour un coût de modèle bien supérieur (historique, purge, résolution de version) ; à reconsidérer si le patrimoine devient volumineux ou partagé entre clubs |
| Marquer la conformité FFTA plutôt que la simple provenance | Suppose la **version du règlement** modélisée et un contrôle de conformité — un lot à part entière, et RG-8 dit que l'application ne vérifie pas la conformité |
