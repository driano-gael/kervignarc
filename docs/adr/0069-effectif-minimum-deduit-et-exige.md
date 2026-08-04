# ADR-0069 — L'effectif minimum se **déduit** du déroulé, et le club peut exiger plus

- **Statut** : accepté
- **Date** : 04/08/2026
- **US** : E05US021
- **Prolonge** : [ADR-0068](0068-le-moteur-consomme-les-prelevements-declares.md) §6, qui ouvrait
  cette US ; [ADR-0063](0063-brouillon-de-format-invariant-a-l-application.md) (le brouillon
  s'enregistre, l'application refuse) ; [ADR-0060](0060-briques-du-patrimoine-du-club.md) §5 (un
  format n'a pas de copie de tournoi : sa copie, ce sont ses phases).

## Contexte

Un déroulé composé pour 120 archers, appliqué à une édition qui en réunit 40 : la phase « les rangs
33 et suivants » ne prélève personne, et le moteur **refuse** de monter le tableau
(`EffectifTableauInvalide`). Ce refus est juste — retomber sur « tous les archers en lice »
ressusciterait le défaut qu'E05US020 venait de corriger — mais il arrive **sur la tablette, en
pleine compétition**, quand il n'est plus temps de changer de format.

Arbitrage du commanditaire (03/08/2026, ADR-0068 §6) : *« les inscrits sont connus au lancement,
donc on ne peut pas lancer un tournoi qui n'a pas assez d'inscrits pour son format ; le logiciel
doit connaître la fourchette basse et avertir l'admin avant de lancer. »*

Le CA d'origine laissait **deux options ouvertes** sans trancher — « un format *déclare*, ou
l'application *dérive* de ses prélèvements » — et ne prévoyait qu'un refus au clic « Démarrer ».
Les deux points ont été arbitrés au cadrage du 04/08/2026 et reversés dans `stories/`.

## Décision

### 1. Le plancher se **déduit**, il ne se saisit pas

Le minimum technique est **calculé** des prélèvements, jamais déclaré seul. Une phase en tableau a
besoin de **deux** participants ; un prélèvement « à partir du rang *d* » n'en trouve deux que
lorsque sa phase source en classe *d + 1*. D'où `d - 1 + 2` inscrits — 34 pour « les rangs 33 et
suivants ». Entre phases, le **plus exigeant** l'emporte ; entre prélèvements d'une même phase, le
**plus bas** décide (ils se cumulent).

**Pourquoi pas un champ saisi.** Un nombre saisi peut contredire le déroulé écrit juste en dessous :
déclarer « 10 » sur un format qui en exige 34 laisserait démarrer un tournoi que le moteur refusera
en salle — exactement le défaut que l'US corrige, avec en plus l'illusion d'un garde-fou. Un fait
dérivable ne se duplique pas : la copie serait fausse au premier ajustement du déroulé.

### 2. Portée **délibérément étroite** : seuls les prélèvements de la première phase comptent

Un rang se lit dans le classement de sa **phase source**, pas dans les inscrits. Seuls les
prélèvements visant la **première** phase — la seule que les inscriptions peuplent — se traduisent
en nombre d'inscrits. « Les rangs 33 et suivants **du tableau** » ne dit rien sur le nombre
d'inscrits nécessaires ; l'inclure produirait un chiffre **faux**, ce qui est pire que pas de
chiffre du tout. Même raison pour les natures qui ne se lisent pas en rangs (`issue_de_tour`,
`le_reste`) : leur compte dépend du déroulé, pas de l'effectif de départ.

Ces cas restent couverts, à effectif simulé, par `PrelevementVide` et `RangsSourceInexistants` —
qui existaient déjà.

### 3. Le club peut exiger **davantage**, jamais moins

`FormatTournoi.effectif_minimum_exige` porte la règle sportive (« pas de tournoi de ce type sous 40
archers »). Le minimum effectif est le **plus haut des deux**. Une exigence **inférieure** au déduit
n'abaisse rien : elle est signalée `EffectifMinimumIncoherent`, **bloquante**, et rend le format
inapplicable — la contradiction est vraie à tout effectif, donc elle bloque (régime ADR-0063 §3).

L'anomalie naît dans `FormatTournoi.projeter`, pas dans `domain.deroule` : c'est une propriété du
format **en tant qu'objet de bibliothèque**, comme `FormatSansEtape` dont elle reprend le patron.
`domain.deroule`, qui ne voit qu'une suite d'étapes, ne peut pas la formuler.

### 4. L'exigence **voyage** vers le tournoi, le plancher se **recalcule**

Un tournoi ne garde aucun lien vers son format : sa copie, ce sont ses **phases** (ADR-0060 §5).
D'où deux traitements opposés, et c'est le cœur de la décision :

- le **plancher technique** ne se stocke pas — les phases sont en base, le recalculer à la lecture
  garantit qu'il ne peut pas se périmer quand l'organisateur retouche son déroulé ;
- le **minimum exigé** est une donnée saisie que rien ne permet de retrouver : il est **recopié**
  sur le tournoi à l'application du format (migration `0040`), au patron du gabarit de salle —
  modèle → copie → ajustement sans altérer le modèle.

Côté format, l'exigence entre dans le JSON `format_tournoi.config` **sans migration**, comme les
prélèvements l'avaient fait : une config antérieure relue sans la clé rend `None`, soit le
comportement d'avant l'US.

### 5. Le minimum est une **donnée** du diagnostic, pas une anomalie de plus

`ProjectionDeroule.effectif_minimum` transporte le chiffre ; aucune anomalie nouvelle n'est émise à
la composition. Le cas « à cet effectif, ce prélèvement ne prend personne » remonte **déjà** en
`PrelevementVide` : en ajouter un second, avertissement et de même cause, ferait signaler le même
défaut deux fois — le piège déjà documenté sous `_anomalies_effectif_declare`. L'écran affiche donc
le chiffre en registre **neutre** (`carte__aide`) et ne bascule en **ambre** (`--warn`, `DV-03`) que
lorsque l'effectif simulé passe dessous.

### 6. Le refus au lancement, et l'annonce **avant** le clic

`ServiceTournois.demarrer` porte la garde (`EffectifInsuffisantPourDemarrer` → 409), sur le patron
de `vers_pret` / `TournoiSansDepart` dont elle est la voisine. Elle ne s'exprime **que si un déroulé
est composé** : sans phase, aucun prélèvement à honorer, donc rien à exiger — ce qui laisse intact
tout le cycle de vie antérieur.

`GET /tournois/{id}/exigence-effectif` rend le même calcul **sans rien déclencher**, pour que
l'écran affiche « 28 inscrits / 34 requis » en continu. Le CA d'origine ne prévoyait que le refus au
clic ; un refus qu'on ne découvre qu'en cliquant n'apprend rien tant qu'on ne clique pas.

Le message **chiffre** ce qui manque et **nomme la phase et son prélèvement** (`D-16` / `P-4` :
« une alerte qui ne chiffre pas son impact est un clic de plus, pas une protection »).

## Conséquences

- **Ce qui devient vrai** : un tournoi dont le déroulé exige plus d'inscrits qu'il n'en a ne peut
  plus être lancé, et l'organisateur le voit venir au lieu de le découvrir en salle.
- **Exception assumée à `D-15`** (« en cours, tout passe ») : le refus ne porte pas sur une saisie
  mais sur l'**ouverture** d'un tournoi qu'on sait déjà impossible à dérouler.
- **`EffectifTableauInvalide` reste** — dernier garde-fou, désormais hors d'atteinte par le chemin
  nominal. On ne le retire pas : il protège encore les chemins qui ne passent pas par `demarrer`
  (simulation, jeu d'essai, base éditée à la main).
- **`ServiceTournois` gagne deux dépendances** (`LecteurSequencePhases`, `CompteurEngages`), toutes
  deux des **ports étroits**, au patron de `LecteurDonneesDePhase`. Le compteur d'engagés est
  **partagé** avec le suivi de déroulé (une seule instance en composition root) pour que « combien
  sommes-nous » n'ait qu'une définition.
- **`FormatTournoi.modifier` remplace l'exigence au lieu de la fusionner** — contrat d'un `PUT`. Un
  appelant partiel qui omettrait le champ **effacerait** la règle du club sans s'en apercevoir ;
  c'est documenté sur la méthode et sur le DTO front.
- **Le calcul reste aveugle** à `le_reste`, `issue_de_tour` et aux prélèvements intermédiaires
  (§2). C'est une limite **énoncée**, pas un oubli : elle disparaîtra d'elle-même le jour où ces
  natures auront un consommateur (`DETTE-028`, `DETTE-033`).
- **Un test de migration a dû être rendu insensible aux colonnes futures** : il insérait un tournoi
  via le mapping ORM **courant** dans un schéma arrêté à `0027`, donc toute colonne nouvelle le
  cassait. Il insère désormais en SQL explicite — un test de migration décrit un passé, que le
  présent n'a pas à réécrire.
