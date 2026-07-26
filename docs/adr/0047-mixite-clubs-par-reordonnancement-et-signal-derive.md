# ADR-0047 — Mixité ≥ 2 clubs : ré-ordonnancement de l'entrée + signal dérivé, plutôt qu'une contrainte du glouton

- **Statut** : Accepté
- **Date** : 2026-07-26
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E03-placement.md`](../../stories/E03-placement.md) (E03US006) ;
  [`docs/glossaire.md`](../glossaire.md) (`Plan de cibles`, club inconnu)
- **Introduit par** : E03US006 (mixité des clubs sur une cible, RG-3).
- **S'appuie sur** : [ADR-0023](0023-moteur-de-placement-glouton-deterministe.md) (glouton déterministe,
  seuil d'extraction des contraintes) · [ADR-0024](0024-plan-de-cibles-materialise-ajustable.md) (plan
  matérialisé, raisons **dérivées à la lecture**) · [ADR-0014](0014-club-inconnu-plutot-que-club-sentinelle.md)
  (`club_id NULL` = inconnu, jamais « même club »).

## Contexte et problème

RG-3 veut « **≥ 2 clubs par cible lorsque c'est possible** » (équité : éviter qu'un même club occupe
une cible entière). Le CA d'E03US006 est délibérément mince — « le placement auto **favorise** ≥ 2
clubs/cible ; **signalé si impossible** » — mais la doc versionnée le cadre entièrement :

- **Contrainte molle, best-effort, priorité la plus basse.** EPIC-03 (§ question ouverte) pose l'ordre
  `capacité > catégorie/hauteur > mixité club`. La mixité **cède** devant toute contrainte de rang
  supérieur ; elle n'échoue jamais, elle **signale**.
- **Club inconnu = indécidable.** `Archer.club_id` est `int | None` où `None` = « pas encore su »,
  **jamais** « aucun club » ni « même club » (ADR-0014). Deux archers `None` ne peuvent donc pas être
  réputés du même club : le cas est *indécidable*, on le **signale** au lieu de mentir.

Deux questions structurantes, qu'aucun CA ne tranche :

1. **Comment favoriser la mixité** dans un glouton mono-passe, sans retour arrière, **déterministe**
   (ADR-0023) — et sans casser les contraintes de rang supérieur ni la non-régression d'E03US001 ?
2. **Où et comment signaler** « mixité non garantie », sachant que le plan est **matérialisé**
   (ADR-0024) : le club n'est pas persisté dans la table `placement`.

## Décision

**1. Favoriser la mixité = ré-ordonner l'entrée du glouton, pas ajouter une branche dans la boucle.**
Avant de placer, on remplace le tri `(hauteur, blason, id)` par un **entrelacement des clubs en
round-robin à l'intérieur de chaque groupe `(hauteur, blason)`** (les frontières de groupe sont
**identiques** à l'ancien tri). Le glouton (`_CibleEnCours.accueille`, remplissage cible par cible)
reste **byte-identique**. Trois propriétés le justifient :

- **Les contraintes de rang supérieur sont préservées par construction.** Le moteur n'est pas touché ;
  la mixité ne peut pas provoquer un dépassement de capacité/espace ni un mélange de hauteurs.
- **Aucune régression sur le nombre de placés/conflits, ni sur la structure des cibles.** Dans un
  groupe `(hauteur, blason)`, tous les archers partagent **la même** `taille`, la même
  `capacite_blason` et la même hauteur : ils sont **interchangeables** pour les budgets. Réordonner un
  groupe ne change donc *que l'identité* (et le club) de qui occupe quelle position — jamais *combien*
  tiennent. Les tests de capacité/espace/carton/hauteur d'E03US001 restent verts sans retouche de leur
  oracle.
- **Déterminisme conservé.** L'entrelacement est un round-robin à ordre fixe (clubs connus par `id`
  croissant, puis le paquet `None`), chaque file interne restant triée par `archer_id`. Quand un groupe
  n'a **qu'un** club connu (ou que des `None`) — dont **tous les tests et données existants** où le
  club n'est pas renseigné — l'ordre **retombe exactement** sur `archer_id` : comportement inchangé.

C'est donc du best-effort **par groupe de blason** : le glouton tire d'un groupe des archers désormais
entrelacés par club, si bien qu'une cible qui puise dans ce groupe reçoit des clubs variés quand ils
existent. Le glouton pouvant laisser une cible mono-club sans qu'un réagencement global l'évite (pas de
retour arrière, ADR-0023), **le signal (point 2) dit la vérité** ; l'ajustement manuel (E03US004)
rattrape le reste.

**Pas d'extraction d'un mécanisme de contraintes injectables.** ADR-0023 §2 fixait le seuil : « à la
3ᵉ contrainte **et** si une duplication apparaît ». Ici la mixité n'est **pas** une contrainte du
glouton (pas de nouveau `if` dans `accueille`), donc **aucune duplication n'apparaît** : le seuil n'est
pas franchi, on n'extrait rien. La séparation catégorie/blason (E03US007) reste la prochaine occasion
de réévaluer.

**2. Le signal « mixité non garantie » est une propriété *dérivée*, calculée côté moteur *et* à la
lecture — jamais persistée.** On ajoute à `CiblePlacee` un booléen `mixite_non_garantie`. Sa vérité
tient dans un prédicat **pur et unique**, `cible_mixite_non_garantie(clubs)` :

> une cible est « non garantie » quand elle porte **≥ 2 archers** mais **< 2 clubs connus distincts**.

Cas couverts : deux clubs connus différents → garantie (pas de signal) ; deux fois le même club connu →
non garantie ; un connu + un `None`, ou deux `None` → non garantie (indécidable, ADR-0014) ; cible à
0 ou 1 archer → **sans objet**, pas de signal (une cible d'un seul archer ne peut structurellement pas
mêler deux clubs — signaler serait du bruit).

Comme le plan est **matérialisé** (ADR-0024) et que la table `placement` ne stocke pas le club, le
signal se **recalcule à la lecture** — exactement comme la raison de réserve (`EN_RESERVE`/`NON_PLACE`)
d'ADR-0024. `ServicePlacement._construire_plan`, qui a déjà la jointure archer → club sous la main
(`contexte.donnees[...]`), appelle le même prédicat pur. Une seule source de vérité, deux points
d'appel (moteur pur pour les tests domaine ; service pour tout plan rendu à l'API).

## Conséquences

- **+** Le moteur glouton reste **inchangé et prouvablement non régressif** : la mixité vit dans un
  pré-tri isolé, pas dans les budgets.
- **+** Le signal suit le régime **dérivé/non persisté** déjà établi (ADR-0024) : rien de nouveau à
  migrer, pas de champ de plus dans la table `placement`, pas de risque de désynchronisation club↔plan.
- **+** `club_id NULL` est traité en **indécidable** de bout en bout (ADR-0014) : le placement ne
  suppose jamais deux inconnus du même club, il l'avoue.
- **−** Mixité **best-effort par groupe de blason**, pas globale : le glouton mono-passe peut laisser
  une cible mono-club qu'un réagencement global aurait mixée. Contrepartie assumée (cohérente avec la
  sous-optimalité d'ADR-0023) — le signal l'expose, l'admin ajuste (E03US004).
- **−** Le signal se **recalcule** à chaque lecture (jointure club déjà chargée, coût négligeable sur
  le LAN mono-club) plutôt que d'être lu d'une colonne.
- **−** La priorité « mixité en dernier » est **implicite** dans le fait que le glouton est inchangé
  (elle ne peut rien enfreindre) plutôt qu'exprimée par un ordonnanceur de contraintes explicite. Si
  E03US007 amène enfin la duplication attendue, on reverra l'extraction (ADR-0023 §2).
