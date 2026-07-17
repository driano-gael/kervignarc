# ADR-0020 — Le blason porte ses valeurs de score admises ; défaut = blason simple complet

- **Statut** : Accepté
- **Date** : 2026-07-17
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E01-configuration.md`](../../stories/E01-configuration.md) (E01US014 :
  défaut nommé, règles de validation explicitées) ; [`docs/modele-de-donnees.md`](../modele-de-donnees.md)
  (`BLASON.zones` — déjà cible depuis le cadrage FFTA du 14/07/2026, mise en œuvre ici)
- **Introduit par** : E01US014 ; **corrige** E01US005 (agrégat `Blason`, réduit à `taille` +
  `capacite`). **Prépare** EPIC-04 (pavé de saisie), qui consommera `zones`.
- **Suit** [ADR-0019](0019-categorie-eligibilite-multi-tranches.md), dont il reprend le régime de
  vocabulaire fermé — voir « Décision », point 1.

## Contexte et problème

L'agrégat `Blason` (E01US005) modélise l'occupation d'une cible par une `taille` (fraction de place)
et une `capacite`. Il ne dit **rien des valeurs qu'on peut y marquer**. Or elles dépendent du
blason :

- un **triple 40** n'a **pas les zones 5 → 1** : le carton s'arrête au bleu clair, qui vaut **6**
  ([`docs/referentiel-ffta.md`](../referentiel-ffta.md) §4.4) ;
- le vocabulaire complet en salle est `10 → 1` plus `M` (manqué, hors blanc) — §4.2.

Sans cette donnée, le pavé de saisie de la tablette (EPIC-04, EF-5.2) ne peut pas se construire : il
proposerait un « 4 » sur un trispot, et rien n'empêcherait de l'enregistrer. Le pavé se déduit du
**blason**, pas du barème de la phase.

**Le problème dur : le défaut n'est pas dérivable.** `Blason.taille` est une **fraction de place**
(`]0, 1]`), **pas un diamètre**. Rien, dans l'agrégat ni en base, ne distingue un triple 40 d'un
blason simple. Le CA d'E01US014 demandait « une valeur par défaut **cohérente** » sans pouvoir dire
cohérente **avec quoi** : le défaut ne peut être qu'une **constante choisie**. C'est un arbitrage
produit, pas un doute technique — il a donc été soumis à l'organisateur (règle 9).

## Options considérées

| # | Option | Verdict |
|---|---|---|
| 1 | **Défaut = blason simple complet** (`10 → 1` + `M`) | **Retenue** |
| 2 | Défaut = triple 40 (`10 → 6` + `M`) — le cas le plus fréquent du club | Écartée |
| 3 | Pas de défaut : `zones` obligatoires à la création | Écartée |
| 4 | Déduire le type du blason depuis son `nom` (« Trispot… ») | Écartée |

- **(2)** est le cas majoritaire (la plupart des catégories adultes tirent sur triple 40 ; les
  poulies **toujours** — §4.1). Son mode d'échec est **visible** : un blason simple laissé au défaut
  bride la saisie, le scoreur ne peut pas entrer un 4 légitime et le signale. Écartée par
  l'organisateur.
- **(3)** supprime la question du défaut, mais laisse entière celle du **backfill** (il faut bien
  écrire quelque chose dans les lignes existantes) et alourdit la création. Écartée par
  l'organisateur.
- **(4)** est une heuristique sur du **texte libre**, qui se tromperait **en silence** sur une donnée
  qui pilote la saisie. Écartée sans hésitation.

## Décision

**1. Vocabulaire fermé, validé à la frontière — même régime qu'ADR-0019.** Les onze valeurs du §4.2
deviennent l'énuméré `ZoneScore(str, Enum)` du domaine (`10`…`1`, `M`), exposé tel quel par les DTO.
Une valeur hors vocabulaire est rejetée en **400** par Pydantic, avant que le domaine ne la voie
(règle 6) — comme `TrancheAge` pour `Categorie.ages`. Les règles **structurelles** restent au
domaine et sortent en **422**. La **mouche (X)** n'est pas une zone : le §4.3 la donne comme un
**diamètre** (le « 10 intérieur » des poulies), pas comme une valeur de score, et aucun consommateur
ne la demande — E06US001 départage au nombre de 10 puis de 9. Si EPIC-06 la réclame, c'est là qu'elle
naîtra.

**2. Trois règles structurelles, et pas une de plus** : `M` toujours admis (un manqué est
physiquement possible sur tout blason ; sans lui le scoreur ne peut pas saisir un raté), au moins une
zone marquante, pas de doublon. Les zones sont normalisées dans l'**ordre canonique** (centre →
extérieur), l'ordre de saisie ne portant aucune information.

**3. La contiguïté n'est pas exigée.** Un jeu troué (`10, 8, M`) est admis. Le motif est qu'elle **ne
sert aucun consommateur** : le pavé affiche ce qu'on lui donne, EPIC-04 somme des valeurs
indépendantes. RG-8 (« l'application n'impose ni ne vérifie la conformité au règlement ») **confirme**
ce choix mais ne le **dicte pas** — sous sa lecture littérale, les trois règles du point 2 seraient
elles aussi de la conformité. Ce qui les distingue est l'**intégrité aval**, pas le règlement. Le but
de l'US est de **restreindre la saisie**, pas de normer le carton.

**4. Défaut = option (1), le sur-ensemble** — arbitrage de l'organisateur, 17/07/2026. Le même
littéral sert de **backfill** à la migration `0019`, pour la raison qui interdit l'option (4) : rien
en base ne reconnaît un triple.

**5. L'édition est un remplacement complet.** `zones` est **obligatoire** au `PUT /blasons/{id}`,
comme le nom, la taille et la capacité ; `None` n'a donc pas un second sens (« inchangé »). En faire
le seul champ partiel d'un PUT par ailleurs total tendrait un piège de read-modify-write au prochain
client (import, script) qui construirait son corps depuis un modèle incomplet : il effacerait les
autres champs mais pas celui-là, et la cause serait invisible à la lecture de l'appelant. `None` ne
garde qu'un sens, à la **création** : « applique le défaut ».

**6. La relecture rejoue la validation du domaine.** `_vers_blason` repasse par `valider_zones` —
comme `_vers_phase` repasse par `BaremeQualification.creer` — et non par une simple coercition
`ZoneScore(...)`. Motif : la coercition ne voit que le **vocabulaire**, pas la **structure**. Une
colonne contenant `'{"10": 1}'` réhydraterait `('10',)` (les clés d'un objet JSON, vocabulaire
valide, mais sans `M`) : un blason hors invariant, qui piloterait le pavé sans qu'aucune erreur ne
soit levée. Une colonne illisible **ou hors règle** est une incohérence technique →
`InfrastructureError` (ADR-0007), jamais un agrégat silencieusement invalide.

## Conséquences

- **+** Le pavé de saisie d'EPIC-04 a enfin sa source de vérité, portée par le blason.
- **+** Le vocabulaire fermé aligne le contrat client sur celui des catégories (400 vocabulaire /
  422 structure) et fait détecter `Blason(zones=("foo",))` par **mypy**. Attention à ne pas
  sur-lire cette garantie : une dataclass `frozen` ne valide **rien à l'exécution** — les portes
  validantes sont `creer`, `modifier` et `_vers_blason`, pas le constructeur brut.
- **−** **Un triple 40 laissé au défaut ouvre le pavé sur `5 → 1`, intirables — soit exactement ce
  que l'US veut empêcher.** C'est la contrepartie assumée de l'option (1), sur le cas majoritaire.
  L'admin doit décocher `5 → 1` à la création d'un triple.
- **−** **Les blasons antérieurs à la migration `0019` ressortent tous en blason simple complet.**
  Les triples déjà en base portent donc des zones fausses jusqu'à reprise **manuelle** — cf. le point
  de vigilance de [`docs/fonctionnel/E01US014.md`](../fonctionnel/E01US014.md). Aucune implémentation
  n'aurait fait mieux : l'information n'a jamais existé en base.
  > ⚠️ **EPIC-04 ne doit pas supposer `zones` fiable sur une donnée antérieure à `0019`.** C'est la
  > raison d'être de cette section : `stories/` porte le CA et la fiche fonctionnelle s'adresse à un
  > non-technicien — ni l'un ni l'autre n'est lu par qui construira le pavé.
- **−** Deux concepts voisins cohabitent (`ZONES_CANONIQUES`, le vocabulaire ; `ZONES_DEFAUT`, le jeu
  par défaut), aujourd'hui identiques. Ils sont énumérés **séparément** à dessein : ajouter X au
  vocabulaire ne doit pas la faire entrer en silence dans le défaut de tous les blasons.
- **Hors périmètre** : la **hauteur** du blason ([DETTE-002](../dette.md)) — orthogonale aux valeurs
  de score, résorbée en EPIC-03.
