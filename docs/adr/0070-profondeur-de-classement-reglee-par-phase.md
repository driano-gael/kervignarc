# ADR-0070 — La profondeur de classement se règle par phase, et son absence reste le podium

- **Statut** : accepté
- **Date** : 04/08/2026
- **US** : E06US006 — Classement intégral 1→N & profondeur configurable
- **Prolonge** : [ADR-0004](0004-moteur-de-phases-politiques.md) (catalogue de politiques),
  [ADR-0011](0011-phase-qualification-anticipee.md) (politique sans migration),
  [ADR-0046](0046-config-policies-politiques-nommees-parametrees.md) (forme `config.policies`),
  [ADR-0061](0061-routing-generique-et-placement-en-cascade.md) (placement intégral),
  [ADR-0066](0066-seuil-de-barrage-porte-par-la-politique-tiebreak.md) (précédent exact : un
  réglage porté par la phase, résolu par le registre)

## Contexte

La politique `depth` existe depuis E05US003 : `ProfondeurUnVersN` classe tout le monde,
`ProfondeurPodium(jusqu_au)` s'arrête au N-ième, `AucunClassement` ne classe rien. E05US010 a rendu
le **placement intégral 1→N** réellement jouable (routing en cascade, oracle 120 vert).

Mais cette politique n'était **branchée nulle part où un organisateur puisse l'atteindre**. Elle
était figée à `ProfondeurPodium()` en deux lignes du composition root, avec ce commentaire :

> *Remplacer `ProfondeurPodium()` par `ProfondeurUnVersN()` sur cette ligne suffit à passer ces
> tableaux au placement intégral 1→N — c'est le levier qu'`E01US024` exposera à l'organisateur phase
> par phase, au lieu de le figer au câblage.*

E01US024 a livré le composeur de déroulé (types, prélèvements, braquets, diagnostic, simulation)
**sans** ce levier. Le moteur savait donc faire une chose que l'organisateur ne pouvait pas
demander : un tournoi de 120 se jouait tronqué au podium, quel que soit le format composé.

## Décision

### 1. La phase porte le **choix**, le registre rend la **stratégie**

`Phase` et `ModelePhase` gagnent un champ `profondeur: ProfondeurClassement | None` — un
**descripteur** sérialisable (`nom` + `jusqu_au`), pas la stratégie. La résolution passe par
`RegistrePolitiques`, exactement comme le seuil de barrage d'ADR-0066.

Mettre une `Depth` sur l'agrégat aurait fait entrer un objet non sérialisable dans une donnée
persistée **et** court-circuité le point d'injection : la politique serait devenue une décoration.

Persistance : `config.policies.depth = {"nom": …, "jusqu_au": …}`, la forme d'ADR-0046. **Aucune
migration Alembic** — la colonne `config` est un document JSON, comme pour `tiebreak`.

### 2. Deux modes en façade, trois au catalogue

L'API et l'écran n'offrent que `un_vers_n` et `podium`. `aucun` (`AucunClassement`) reste au
catalogue mais **hors façade** : ce n'est pas un réglage de tableau, c'est le contenu même du type
`échauffement` (§10.1). L'offrir proposerait de monter un arbre dont on ne lirait aucun rang.

Symétriquement, une profondeur réglée sur un type qui ne monte **aucun** tableau est refusée
(`ProfondeurInvalide` → 422) : une qualification classe toujours tout le monde, une poule classe
sans arbre. Un réglage qui n'agit sur rien est pire qu'absent — il se croit appliqué.

### 3. ⚠️ L'absence de réglage vaut **podium**, et non 1→N

Le CA d'E06US006 dit « mode 1→N (**défaut**) », et ADR-0004 aussi. **Nous ne le suivons pas pour le
preset d'une phase**, et c'est la décision structurante de cet ADR.

Le défaut du *catalogue* — quelle politique un format assemble quand il ne dit rien — n'est pas le
preset d'une *phase déjà écrite en base*. Jusqu'à cette US, **toutes** les phases se jouaient en
`ProfondeurPodium` figée au câblage. Faire de 1→N le preset des phases non réglées aurait converti
d'un coup **tous les tournois existants** au placement intégral : un tableau de 120 serait passé
d'une trentaine de duels à plus d'une centaine, sans que personne ne l'ait demandé, et sans qu'aucun
écran ne le signale — le format composé et validé la veille aurait produit un autre tournoi.

Donc : `profondeur = None` ⇒ preset du type ⇒ `podium(4)` pour un tableau — le mécanisme « politique
sans migration » d'ADR-0011, celui-là même qui fait retomber une phase d'avant E01US015 sur son
grain preset. **1→N est ce que l'organisateur choisit**, jamais ce qu'il subit.

Conséquence assumée : le CA est **corrigé** dans `stories/` plutôt que suivi à la lettre (règle 9 —
un arbitrage tranché en cours d'US est reversé dans la story, dans le même commit).

### 4. Trois états à l'écran, pas deux

Le contrôle offre « Podium — rangs 1 à 4 (défaut) », « Classement intégral » et « S'arrêter à un
rang précis… ». Les deux premières options du bas produisent le même tournoi que la première quand
le rang vaut 4 — c'est voulu. Fondre « ne rien régler » et « podium 4 » en une seule option
obligerait à **écrire** un réglage sur chaque phase déjà composée, et ferait passer un défaut hérité
pour une décision de l'organisateur.

### 5. Une seule lecture pour les deux services de tableau

`ServicePlacementDuels` (qui pose les cibles) et `ServiceSaisieDuels` (qui joue l'arbre) montent le
**même** tableau. La résolution est donc extraite en une fonction partagée, `profondeur_de`, posée
dans `application/prelevement.py` — le module créé par E05US020 pour exactement ce risque.

Ce n'est pas une précaution théorique : la règle d'ensemencement y vivait **recopiée** aux deux
endroits, avec un commentaire affirmant leur parité, et la recopie a lâché à la première évolution
(plan de 8 placements pour un tableau de 4, mesuré en revue adversariale). Deux profondeurs
divergentes donneraient la même classe de panne, en pire : des cibles posées pour un arbre qui n'est
pas celui qu'on joue.

## Conséquences

**Positives**

- le placement intégral 1→N devient **atteignable** depuis l'écran, sur les deux surfaces qui
  composent des phases (« Composer un déroulé » et « Phases » d'un tournoi) ;
- sous ce mode, le palmarès livré par E06US004 rend un rang **exact et décerné** à chaque archer :
  plus aucune fourchette, et la politique `aggregation` n'a plus rien à départager. Le CA « rang
  unique 1→N » est satisfait **sans toucher au palmarès** — il ne connaît que des positions
  acquises, pas la structure qui les a produites ;
- le composition root cesse de porter un choix qui n'était pas le sien ;
- aucune migration, aucun changement de comportement sur l'existant.

**Négatives / à surveiller**

- **le nombre de duels d'un classement intégral n'est pas annoncé au moment du choix.** Le schéma à
  braquets compte les duels de l'**arbre** (`effectif - 1`) et ignore ceux que la profondeur ajoute ;
  la maquette A07 demande pourtant de chiffrer la conséquence au moment du choix (`P-4`). Rendre
  `projeter` sensible à la profondeur suppose soit une reconstruction ensemencée dans une projection
  qui l'évite délibérément, soit une formule fermée qui deviendrait une **seconde** source de vérité
  sur la structure du tableau. Retenu pour l'instant : l'écran énonce la conséquence en clair, et le
  chiffre vient de la **simulation**, qui joue réellement le format. Inscrit en `DETTE-035` ;
- le commentaire d'`ecart` (`application/simulation_format.py`) parlait d'un écart « d'une unité,
  structurel » dû à `ProfondeurPodium` câblée. Il reste vrai au preset, mais l'écart devient bien
  plus grand en 1→N. Les duels étant **déjà** hors du prédicat `ecart`, rien ne casse ; le
  commentaire est mis à jour ;
- l'édition d'une phase est **totale** (PUT) : les deux écrans doivent réémettre la profondeur, sous
  peine de la voir s'effacer en corrigeant un effectif. Le piège est déjà documenté pour
  `barrage_jusqu_au` ; il est plus coûteux ici, puisqu'une profondeur effacée fait **rejouer** un
  tournoi tronqué.

## Alternatives écartées

- **Régler la profondeur au tournoi entier**, comme `aggregation`. Écarté par le commanditaire au
  cadrage du 04/08 : le déroulé se compose déjà phase par phase, et un tournoi peut légitimement
  jouer un tableau principal intégral et une consolante tronquée.
- **Suivre le CA à la lettre (1→N par défaut).** Écarté — cf. §3 : conversion silencieuse de tout
  l'existant.
- **Ajouter une notion de « profondeur publiée »** au palmarès (afficher un top N d'un classement
  complet). Écarté : le mécanisme de fourchette d'E06US004 **est** déjà le regroupement du reliquat,
  et une seconde notion de profondeur aurait fait deux réglages pour une question.
- **Laisser `Depth` injectée au câblage et n'exposer qu'un préréglage de format.** Écarté : le
  format serait resté du code, contre la règle 2 (« un format de tournoi est de la configuration »).
