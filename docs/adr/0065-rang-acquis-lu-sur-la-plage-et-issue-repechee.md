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

Trois champs, et ils ne se répètent pas :

| Champ | Ce qu'il dit |
|---|---|
| `rang_final` | Le rang **exact**, décerné par un match terminal (`Tableau.classement()`) |
| `rang_min`/`rang_max` | La **fourchette acquise** — s'y referme quand le rang exact existe |

Effet de bord favorable : `_grille` lit désormais `classement()` là où elle lisait `podium()`. Le
podium n'en est que la restriction aux rangs ≤ 4 ; sous **placement intégral** (E05US010), tous les
rangs sont décernés par des matchs terminaux, donc chacun reçoit son rang **exact** sans un calcul
de plus, et la fourchette se referme d'elle-même. Sous profondeur podium, la sortie est identique à
celle d'hier : ce n'est pas un changement de comportement, c'est le même code qui cesse de jeter ce
qu'il tenait déjà.

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

### 4. Une lecture **collective**, partagée par toutes les surfaces

`ServiceRoutage.affectations(tournoi_id)` ne prend **aucun** identifiant d'archer, contrairement à
`routage()`. La tablette sait qui sont ses quatre archers ; l'écran de salle et le téléphone d'un
spectateur ne savent rien. Leur faire reconstituer la liste d'abord, ce serait leur faire connaître
le tableau — le travail de ce service.

**Même DTO pour les deux lectures**, délibérément : les quatre canaux doivent dire la même chose, et
deux formes de réponse finiraient par diverger sur la butte annoncée — l'écart qu'on ne découvre
qu'à 18 h, quand deux archers se présentent au même endroit.

Conséquence de charge, et c'est ce qui a décidé du câblage front : **les cartes de « ma journée »
(E07US006) consomment la lecture collective**, pas un `useRoutage` par archer suivi. La lecture est
la même pour tout le monde, donc **une seule entrée de cache** sert le gymnase entier, sur ce qui est
la requête la plus chère de l'application (classement + reconstruction de l'arbre + plan de duels).
Une lecture par archer suivi l'aurait multipliée par le nombre de suivis **et** par le nombre de
téléphones. C'est le régime **DETTE-008**, qu'on ne ferme pas ici mais qu'on refuse d'aggraver.

## Conséquences

**Acquis**

- L'archer parti de la salle voit sa prochaine butte, son rang acquis ou sa destination de repêchage.
- L'écran de salle gagne la vue `affectations` — la dernière du CA d'E07US004 qui lui manquait,
  ajoutée **sans migration** exactement comme ADR-0064 l'avait prévu (la valeur persistée est la
  chaîne, pas un rang). La prévision s'est vérifiée au mot près.
- `Q-UX2` (« trier par nom ou par cible ? ») est **fermée par « les deux »**, comme `Q-UX7` en
  E07US004 : l'écran projeté garde l'ordre du pas de tir (il ne peut rien actionner), la table de
  l'organisation bascule d'un bouton.

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
