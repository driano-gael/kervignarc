# ADR-0065 — Le rang acquis se lit sur la plage du match perdu, et un repêché n'est pas un éliminé

- **Statut** : accepté
- **Date** : 02/08/2026
- **US** : E07US008 (vue publique des affectations du prochain tour)
- **Voisins** : [ADR-0061](0061-routing-generique-et-placement-en-cascade.md) (routing générique,
  *Règle R*), [ADR-0062](0062-catalogue-de-types-de-phase.md) (le repêchage est une **politique**,
  pas un type de phase), [ADR-0039](0039-exposition-publique-du-deroule-scores-provisoires.md)
  (exposition publique d'un état non définitif)

## Contexte

E07US008 livre le **canal n°2 des quatre canaux de routage** (`D-09`) : l'archer a validé, rangé ses
flèches et quitté la salle — l'information « où je tire ensuite » doit le suivre sur son téléphone.
Le service (`ServiceRoutage`) et l'endpoint existaient depuis E04US018 ; cette US ajoute la lecture
**collective** et, surtout, se heurte à deux trous que le canal n°1 pouvait ignorer parce que la
tablette s'adresse à quelqu'un **encore présent**.

Deux questions ont été posées au commanditaire au cadrage, et tranchées par lui :

1. **Le rang de l'éliminé.** `ServiceRoutage` ne savait annoncer que les rangs **1 à 4** (le podium).
   Hors podium, il rendait le motif « rang publié en fin de phase », en attendant l'agrégation
   d'E06US004. Arbitrage : **calculer le rang complet ici**.
2. **Le repêché.** `VersRepechage` fait **sortir** un battu du tableau sans le classer ; le service,
   qui ne vise qu'une phase, le rendait `TERMINE`. Arbitrage : **traiter le cas dans l'US**.

## Décision

### 1. Le rang acquis d'un battu est la *moitié basse* de la plage du match qu'il a perdu

Aucune règle de classement n'est écrite dans le service. `Match.plage` porte déjà « les rangs encore
atteignables **avant** ce match » (ADR-0061), et `Plage.moitie_basse()` **est** la *Règle R* — « le
perdant descend dans la moitié basse de sa plage ». Le battu d'un quart d'un tableau de 8 sort donc
de `[1..8]` vers `[5..8]` : **5ᵉ-8ᵉ**.

La conséquence importante est qu'on rend une **fourchette**, pas un chiffre. Ce n'est pas une
approximation faute de mieux : dans un tableau tronqué au podium, **aucun match n'a été joué pour
départager les quatre battus des quarts**. Ils sont *ex æquo*, et c'est le résultat. Choisir un
chiffre dans la fourchette aurait fabriqué un classement que la compétition n'a pas produit.

⚠️ **La borne haute est écrêtée à l'effectif réel** — correctif de revue, relevé indépendamment par
deux axes, preuve d'exécution à l'appui. Une plage est bornée par la **taille** du tableau, une
puissance de 2, pas par le nombre d'archers : sur l'oracle 120 (taille 128), un battu du 1ᵉʳ tour
sortait « 65ᵉ-**128**ᵉ » alors que les rangs 121 à 128 n'existent pas. Le défaut avait échappé aux
tests parce que les deux effectifs du décor — 4 et 8 — sont précisément les seuls où
`taille == effectif` ; un cas à 6 archers a été ajouté pour rompre cette coïncidence.

Trois champs, et ils ne se répètent pas :

| Champ | Ce qu'il dit |
|---|---|
| `rang_final` | Le rang **exact**, décerné par un match terminal (`Tableau.classement()`) |
| `rang_min`/`rang_max` | La **fourchette acquise** — s'y referme quand le rang exact existe |

Effet de bord favorable : `_grille` lit désormais `classement()` là où elle lisait `podium()`. Le
podium n'en est que la restriction aux rangs ≤ 4 ; sous **placement intégral** (E05US010), tous les
rangs sont décernés par des matchs terminaux, donc chacun reçoit son rang **exact** sans un calcul
de plus, et la fourchette se referme d'elle-même.

Sous `ProfondeurPodium()` **par défaut** (`jusqu_au=4`, le câblage de production), la sortie est
identique à celle d'hier : seules `[1..2]` et `[3..4]` sont terminales, donc `classement()` ne rend
jamais de rang > 4. ⚠️ **Mais `jusqu_au` est un paramètre** (correctif de revue) : sous
`ProfondeurPodium(jusqu_au=8)` — l'exemple de sa propre docstring — le service gagne les rangs 5-8
exacts que `podium()` jetait. C'est donc bien un changement de comportement dans cette
configuration, et il est **voulu** ; un premier jet de cet ADR écrivait « ce n'est pas un changement
de comportement », ce qui était faux.

**Ce n'est pas E06US004.** Cette lecture dit ce que *ce tableau* a décidé — sans agrégation
inter-phases ni départage FFTA. E06US004 reste due, et la fourchette ne la préempte pas : elle
occupe l'espace que le motif « rang publié en fin de phase » laissait vide.

### 2. `REPECHE` est une **issue à part entière**, pas un sous-cas de `TERMINE`

`IssueRoutage` passe de trois à quatre valeurs. La distinction est métier, pas technique :
`HorsTableau` **consomme** un rang (le perdant a fini sa compétition), `VersRepechage` n'en consomme
**aucun** — le repêché peut encore remonter disputer le titre (`domain/politiques.py`). Annoncer
« éliminé » à un repêché le fait rentrer chez lui avant son duel : c'est un défaut visible en salle,
pas une nuance d'affichage.

La détection **redemande au routing** (`tableau.routing.route(ContexteRoutage(...))`) plutôt que de
déduire « pas de sous-tableau aval ⇒ repêché ». La déduction serait fausse : un match dont la plage
aval est **élaguée par la profondeur** (`ProfondeurPodium`) n'a pas non plus d'aval, et son battu
est bel et bien éliminé.

⚠️ **Contrat découvert au passage** : on n'interroge **pas** le routing sur une plage *terminale*.
`construire_tableau` sort avant de l'appeler dans ce cas (*Règle T*), si bien que
`PlacementEnCascade` y appelle `moitie_basse()` sur `[1..2]` et lève `PlageInvalide`. Étant le
deuxième appelant du protocole `Routing` — et le premier à l'avoir enfreint — le service redonde la
garde. Métier, elle est vraie de toute façon : un match terminal décerne les deux rangs.

### 3. La **destination** d'un repêché se lit dans les sources de la séquence, pas dans le tableau

La réintégration n'est pas un lien d'arbre mais un **prélèvement** de la phase avale
(`SourcePhase.par_issue_de_tour(ordre, tour, PERDANTS)`, ADR-0062). Le routage parcourt donc les
phases **postérieures** du tournoi et retient la plus proche qui prélève les perdants de ce tour.

Si aucune ne le fait, on le **dit** (`REPECHAGE_SANS_DESTINATION`). `construire_tableau` avait
annoncé ce trou : « si la composition oublie la phase de repêchage, ces battus disparaissent sans
que rien ne le signale ». Le routage est le premier endroit où ce trou de composition rencontre un
**humain** — l'archer demande où il tire, et personne ne peut répondre. Un panneau muet passerait
pour une panne réseau, et l'organisateur ne saurait pas que son déroulé est incomplet.

⚠️ **Le cas symétrique — le seul atteignable aujourd'hui — a failli être manqué** (correctif de
revue, axe adversarial). Les deux moitiés du repêchage se lisent à **deux sources indépendantes** :
le routing (`_est_repeche`) et les sources de la séquence (`_repechages`). Or aucun
`RoutingRepechage` n'est câblé en production (`DETTE-028`), donc `_est_repeche` rend **toujours**
faux — tandis que l'atelier de déroulé (E01US024) permet **déjà** de composer « les perdants du
tour 1 de la phase 2 ». Un premier jet fermait donc soigneusement le trou qu'aucun chemin de
production n'ouvre, et laissait ouvert celui que l'éditeur livré permet d'ouvrir : cet archer-là
lisait « 5ᵉ-8ᵉ », comprenait qu'il était sorti, et rentrait chez lui.

Décision : un battu que la séquence reprend garde l'issue **`TERMINE`** — il a bel et bien acquis un
rang dans *ce* tableau, contrairement au repêché du routing qui n'en consomme aucun — mais sa
**destination est annoncée** (« 5ᵉ-8ᵉ du tableau · repris en 3. Élimination directe »). Forcer
`REPECHE` aurait effacé un rang réellement acquis ; se taire l'aurait renvoyé chez lui. Dire les
deux est vrai des deux côtés.

### 4. Une lecture **collective**, partagée par toutes les surfaces

`ServiceRoutage.affectations(tournoi_id)` ne prend **aucun** identifiant d'archer, contrairement à
`routage()`. La tablette sait qui sont ses quatre archers ; l'écran de salle et le téléphone d'un
spectateur ne savent rien. Leur faire reconstituer la liste d'abord, ce serait leur faire connaître
le tableau — le travail de ce service.

**Même DTO pour les deux lectures**, délibérément : les quatre canaux doivent dire la même chose, et
deux formes de réponse finiraient par diverger sur la butte annoncée — l'écart qu'on ne découvre
qu'à 18 h, quand deux archers se présentent au même endroit.

Conséquence de charge, et c'est ce qui a décidé du câblage front : **les cartes de « ma journée »
(E07US006) consomment la lecture collective**, pas un `useRoutage` par archer suivi. Une seule
entrée de cache **par appareil** sert donc toutes les cartes suivies de cet appareil, sur ce qui est
la requête la plus chère de l'application (classement + reconstruction de l'arbre + plan de duels).

⚠️ **Le gain s'arrête à l'appareil** — correction de revue (deux axes). Un premier jet de cet ADR
écrivait « une seule entrée de cache sert le gymnase entier » : c'est faux. Le cache React Query est
**par navigateur**, il n'existe ni cache serveur ni en-tête HTTP sur cette route, et `useRealtime`
invalide **sans clé** — chaque écriture serveur refetch tous les clients montés. Le coût serveur est
donc d'une reconstruction **par appareil et par invalidation**. Le vrai gain — une requête au lieu
d'une par archer suivi — suffisait à justifier la décision ; le raisonnement inter-appareils était
une image mentale du système, exactement le défaut d'ADR qu'un précédent du projet avait déjà
produit.

La dette concernée est **`DETTE-031`** (« le suivi du déroulé se recalcule intégralement à chaque
lecture »), **pas `DETTE-008`** (l'écho non borné de l'entrée client dans une réponse 400), que
quatre textes de cette US citaient par erreur. Cette US **aggrave** DETTE-031 — second endpoint au
même régime, deux surfaces de polling de plus dont une sur le téléphone de chaque spectateur — et
**élargit sa ligne au registre**, comme la règle du projet l'impose.

## Conséquences

**Acquis**

- L'archer parti de la salle voit sa prochaine butte, son rang acquis ou sa destination de repêchage.
- L'écran de salle gagne la vue `affectations` — la dernière du CA d'E07US004 qui lui manquait,
  ajoutée **sans migration** exactement comme ADR-0064 l'avait prévu (la valeur persistée est la
  chaîne, pas un rang). La prévision s'est vérifiée au mot près.
- `Q-UX2` est fermée **sur son volet « tri »** par « les deux », comme `Q-UX7` en E07US004 : l'écran
  projeté garde l'ordre du pas de tir (il ne peut rien actionner), la table de l'organisation
  bascule d'un bouton. ⚠️ **Son volet « scannabilité » reste ouvert** (correctif de revue) : la
  question enregistrée au CDC UX dit « 200 archers ne tiennent pas à l'écran, donc ça défile, et un
  archer qui rate son nom attend un cycle entier ». Cette US ne livre ni pagination ni cycle — la
  liste déborde de `.salle__scene` comme le fait déjà la vue `classement` depuis E07US004. Déclarer
  la question close en entier l'aurait retirée du radar sans l'avoir résolue.

**À savoir**

- Le CA d'E04US018 est **révisé** : son test exigeait « rang publié en fin de phase » hors podium.
  Le motif ne subsiste que là où **rien** n'est acquis (plage absente). Reversé dans `stories/`.
- Un **participant équipe** (E13US002) est écarté de la vue collective : le routage résout un
  `Participant` en archer, et une équipe n'a pas de nom d'archer. Les afficher rendrait des lignes
  anonymes ; la résolution viendra avec les équipes.
- La vue collective **n'a pas de plafond** analogue à `_MAX_ARCHERS`. Ce plafond bornait
  l'amplification requête→réponse ; ici le client ne demande rien, la taille de la réponse est celle
  du tableau. DETTE-008 est inchangée — ni aggravée, ni fermée.
- Toujours **pas d'heure** dans une affectation, alors que le CA d'E07US008 en cite une : aucun
  horaire n'existe par tour de tableau (les horaires vivent sur les `Depart`, côté qualification).
  Arbitrage déjà pris en E04US018, reconduit ici plutôt que de fabriquer une heure qu'on ne sait pas
  tenir — c'est le lancement du tour (E12US002) qui fait foi.
