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

L'API et l'écran n'offrent que `un_vers_n` et `top_n`. `aucun` (`AucunClassement`) reste au
catalogue mais **hors façade** : ce n'est pas un réglage de tableau, c'est le contenu même du type
`échauffement` (§10.1). L'offrir proposerait de monter un arbre dont on ne lirait aucun rang.

⚠️ **`top_n`, et non `podium`** (corrigé en revue). La stratégie s'appelle `ProfondeurPodium`
depuis E05US003, mais `docs/glossaire.md` réserve le mot *Podium* aux **rangs 1-4 décernés par un
match**. Ce nom devenant ici un **contrat REST et une valeur persistée**, un « podium jusqu'au 8ᵉ »
aurait rompu la règle 3 dans les quatre sens (code, API, UI, doc). Le renommage est **gratuit
aujourd'hui** — la clé `config.policies.depth` n'a jamais été écrite, aucune base ne la porte — et
coûteux dès la première base de production. La **classe** garde son nom, qui est interne.

Symétriquement, une profondeur réglée sur un type qui ne monte **aucun** tableau est refusée
(`ProfondeurInvalide` → 422) : une qualification classe toujours tout le monde, une poule classe
sans arbre. Un réglage qui n'agit sur rien est pire qu'absent — il se croit appliqué.

⚠️ **Ce refus vaut pour une `Phase`, pas pour un `ModelePhase`.** Une étape de format incohérente
s'enregistre — c'est le régime brouillon d'ADR-0063 — et n'est refusée qu'à `pour_tournoi`. Elle
n'est pas non plus **diagnostiquée** (`projeter` ne lit pas la profondeur), donc l'organisateur ne
l'apprend qu'à l'application. Inatteignable depuis l'écran, qui force `profondeur: null` hors
tableau ; c'est par l'API seule que le cas se produit.

### 3. ⚠️ L'absence de réglage vaut **podium**, et non 1→N

Le CA d'E06US006 dit « mode 1→N (**défaut**) », et ADR-0004 aussi. **Nous ne le suivons pas pour le
preset d'une phase**, et c'est la décision structurante de cet ADR.

Le défaut du *catalogue* — quelle politique un format assemble quand il ne dit rien — n'est pas le
preset d'une *phase déjà écrite en base*. Jusqu'à cette US, **toutes** les phases se jouaient en
`ProfondeurPodium` figée au câblage. Faire de 1→N le preset des phases non réglées aurait converti
d'un coup **tous les tournois existants** au placement intégral : un tableau de 120 serait passé
de **128 duels à 436** (mesuré sous `PlacementEnCascade`, le routing câblé en production ; sous un repêchage ce serait 128 → 256, et sous élimination sèche la profondeur n'a aucun effet), sans que personne ne l'ait demandé, et sans qu'aucun
écran ne le signale — le format composé et validé la veille aurait produit un autre tournoi.

Donc : `profondeur = None` ⇒ preset du type ⇒ `top_n(4)` pour une élimination directe — le mécanisme
« politique sans migration » d'ADR-0011, celui-là même qui fait retomber une phase d'avant E01US015
sur son grain preset. **1→N est ce que l'organisateur choisit**, jamais ce qu'il subit.

⚠️ **L'argument couvre aussi les phases créées après cette US**, et il faut le dire — la revue a
relevé que la formulation ci-dessus (« les tournois **existants** ») ne couvrait que la moitié du
périmètre. La raison est mécanique : l'absence de clé ne permet **pas** de distinguer une phase
ancienne d'une phase neuve. Il faudrait pour cela une migration — donc matérialiser `top_n(4)` sur
chaque phase déjà composée, soit un défaut hérité maquillé en décision — ou un marqueur de version.
On choisit un seul preset pour les deux, et le CA est corrigé en conséquence. *Si le commanditaire
voulait 1→N par défaut sur les nouvelles phases, c'est un arbitrage produit à lui soumettre, pas
une correction technique.*

**Exception : le type `placement`.** Son preset est `un_vers_n`, et l'asymétrie est voulue.
L'argument de rétro-compatibilité ne s'y applique pas — **aucun service ne monte de tableau pour ce
type** (`# DETTE-028`), donc il n'y a rien à ne pas casser — tandis que le catalogue promet à
l'organisateur « tableau qui classe tout le monde, du 1ᵉʳ au dernier ». Lui donner le podium aurait
affiché « Podium (défaut) » sur le type dont le nom dit l'inverse. La fenêtre est **maintenant** :
après la livraison de son moteur, corriger ce preset exigerait la conversion silencieuse que ce
paragraphe refuse. *(Relevé en revue par deux axes, sous deux angles opposés — l'un demandant le
changement de preset, l'autre notant que le réglage n'est lu par personne sur ce type.)*

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
(plan de 8 placements pour un tableau de 4, mesuré en revue adversariale).

⚠️ **Mais la panne symétrique n'existe pas encore, et un premier jet de cet ADR l'affirmait à
tort.** Sous `PlacementEnCascade`, les **paires du premier tour sont identiques quelle que soit la
profondeur** (mesuré : `top_n(4)` et `un_vers_n` sur 8 participants rendent les mêmes paires), et
`ServicePlacementDuels` ne consomme **que** ce premier tour. Sa sortie est donc structurellement
insensible à la profondeur : neutraliser sa lecture laisse la suite de tests entièrement verte —
non par défaut de couverture, mais **parce qu'il n'y a rien à distinguer**. Écrire malgré tout un
test de parité aurait produit un test décoratif, vert quoi qu'il arrive.

Ce que la lecture partagée achète est donc une garantie **future**, pas une divergence évitée
aujourd'hui : le jour où le plan couvrira les tours suivants, la parité sera acquise sans qu'on ait
à y penser. Un test de caractérisation (`test_le_plan_de_cibles_reste_le_meme_a_toute_profondeur`)
fige l'état actuel et **échouera** ce jour-là — c'est exactement ce qu'on lui demande.

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
  tournoi tronqué ;
- **deux politiques de phase, deux modélisations.** `barrage_jusqu_au` est un **entier nu**
  (E06US003) ; `profondeur` est un **descripteur** `nom` + paramètres. La seconde forme est la
  bonne — c'est elle qui rendrait atteignable le `sinon` du composite `tiebreak`, que
  `docs/modele-de-donnees.md` signale aujourd'hui comme impossible à écrire — mais la première n'a
  pas été convertie : le faire aurait élargi le périmètre de l'US. **La 3ᵉ politique portée par une
  phase doit converger vers le descripteur**, et non inventer une forme de plus. C'est aussi à ce
  moment-là que « résoudre une politique de phase par le registre » atteindra sa 3ᵉ occurrence,
  seuil auquel le projet autorise un remède structurel (règle 16) — aujourd'hui il n'y en a que
  deux, aux formes encore divergentes, donc **on duplique et on attend**.

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

## Porté dans le code par

> *Section ajoutée le 08/08/2026 (rétro-équipement des ADR structurants encore actifs). La règle
> « un ADR nomme les modules qui le portent » a été instituée le 06/08/2026 par
> [ADR-0075](0075-le-depart-est-la-portee-sportive.md) et n'avait pas été appliquée rétroactivement.
> Les modules ci-dessous ont été **vérifiés dans le code du jour**, pas déduits de l'ADR — nommer un
> module vide reproduirait exactement le défaut que la section existe pour empêcher.*

- `backend/domain/politiques.py` — `ProfondeurClassement` (le **descripteur** sérialisable : `nom` +
  `jusqu_au`), `NomProfondeur`, et les trois stratégies `ProfondeurUnVersN`, `ProfondeurPodium`,
  `AucunClassement`. La distinction descripteur / stratégie **est** la décision §1.
- `backend/domain/phase.py` — `Phase.profondeur: ProfondeurClassement | None` et
  `profondeur_par_defaut(type_phase)` : l'absence de réglage vaut **preset du type** (podium pour une
  élimination directe, intégral pour un placement), et ce preset vit en **un seul endroit**.
- `backend/application/prelevement.py` — `profondeur_de(phase, registre)`, la résolution
  descripteur → stratégie par le `RegistrePolitiques`, exactement comme le seuil de barrage
  d'[ADR-0066](0066-seuil-de-barrage-porte-par-la-politique-tiebreak.md).

Conforme à [ADR-0046](0046-config-policies-politiques-nommees-parametrees.md) : persistance sous
`config.policies.depth`, **aucune migration Alembic**. `aucun` reste **au catalogue mais hors
façade** (§2) — c'est le contenu du type `échauffement`, pas un réglage de tableau ; l'offrir
proposerait un tableau qui ne classe personne.
