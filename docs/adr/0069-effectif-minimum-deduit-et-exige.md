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

Le minimum technique est **calculé** des prélèvements, jamais déclaré seul. Une phase qui **oppose**
des tireurs en exige **deux** ; un prélèvement « à partir du rang *d* » n'en trouve deux que lorsque
sa phase source en classe *d + 1*. D'où `d - 1 + 2` inscrits — 34 pour « les rangs 33 et suivants ».
Entre phases, le **plus exigeant** l'emporte ; entre prélèvements d'une même phase, le **plus bas**
décide (ils se cumulent). Seuls la qualification et l'échauffement se contentent d'un participant :
la liste est énoncée **en négatif** pour qu'un type ajouté au catalogue hérite du plancher prudent.

**Pourquoi pas un champ saisi.** Un nombre saisi peut contredire le déroulé écrit juste en dessous :
déclarer « 10 » sur un format qui en exige 34 laisserait démarrer un tournoi que le moteur refusera
en salle — exactement le défaut que l'US corrige, avec en plus l'illusion d'un garde-fou. Un fait
dérivable ne se duplique pas : la copie serait fausse au premier ajustement du déroulé.

### 2. Portée **délibérément étroite** : seuls les prélèvements de la qualification comptent

Un rang se lit dans le classement de sa **phase source**, pas dans les inscrits. Le seul classement
traduisible en nombre d'inscrits est celui de la **qualification** — et c'est une contrainte du
**moteur**, pas une commodité : `ServiceSaisieDuels._ordre_de_la_qualification` n'honore un
prélèvement que s'il vise la phase de type `qualification`.

**Viser la « première phase » au lieu de la qualification était un défaut bloquant**, trouvé en
revue : un déroulé « échauffement → qualification → tableau 33+ » — dont tous les éléments sont
offerts par l'écran de composition — annonçait un plancher de **1**, laissait démarrer, et cassait
en salle. Le contrôle était donc désactivé par une composition banale. Symétriquement, un déroulé
**sans** qualification se voyait réclamer 34 inscrits alors que le moteur, n'ayant aucun classement
à lire, ensemence avec tout le monde : un **refus abusif** le jour J, aussi grave qu'un oubli.

Restent hors calcul : « les rangs 33 et suivants **du tableau** » (le rang y désigne un classement
intermédiaire) et les natures qui ne se lisent pas en rangs (`issue_de_tour`, `le_reste`). Les
inclure produirait un chiffre **faux**, pire que pas de chiffre.

⚠️ **Ces cas ne sont couverts par rien d'autre à la composition.** `PrelevementVide` et
`RangsSourceInexistants` ne naissent que dans la branche `RANGS` de la résolution, et
`PhaseSansParticipant` exige un compte **nul** — une phase qui n'attrape qu'un participant n'émet
aucune anomalie. *(Une première rédaction affirmait ici que ces anomalies couvraient le reste :
c'était faux, et cela rendait la limite invisible.)* Le seul filet est donc le **plancher
structurel** : il est retenu dans **tous** les cas de repli, parce qu'une phase à duels exige deux
tireurs quelle que soit la source qui l'alimente. C'est une borne inférieure jamais surestimante.

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

`ProjectionDeroule.effectif_minimum` transporte le chiffre ; **aucune anomalie nouvelle n'est émise
au titre du plancher déduit**. Le cas « à cet effectif, ce prélèvement ne prend personne » remonte
**déjà** en `PrelevementVide` : en ajouter un second, avertissement et de même cause, ferait
signaler le même défaut deux fois — le piège déjà documenté sous `_anomalies_effectif_declare`.
*(La seule anomalie que l'US ajoute est `EffectifMinimumIncoherent` du §3, qui porte sur la
contradiction entre l'exigence saisie et le déroulé, jamais sur l'effectif simulé — la formulation
d'origine, « aucune anomalie nouvelle », contredisait §3 dix lignes plus haut.)* L'écran affiche donc
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
- **`EffectifTableauInvalide` reste** — dernier garde-fou, et il **n'est pas hors d'atteinte**.
  ⚠️ La garde compare les **inscrits** (`nb_engages`) à un plancher, alors que le moteur prélève les
  classés **en lice** : un tournoi lancé à 34 inscrits qui enregistre deux abandons se retrouve à 32
  en lice, et « les rangs 33 et suivants » ne prélève plus personne. Le manque naît **après** le
  lancement, donc hors de portée d'une garde au démarrage — mais la limite doit être écrite, faute
  de quoi la prochaine US bâtira sur une fausse assurance. *(Relevé par la revue adversariale ; une
  première rédaction annonçait le garde-fou « hors d'atteinte par le chemin nominal ».)*
- **`ServiceTournois` gagne deux dépendances** (`LecteurSequencePhases`, `CompteurEngages`), toutes
  deux des **ports étroits**, au patron de `LecteurDonneesDePhase`. `LecteurSequencePhases` reprend
  la signature de `domain.ports.PhaseRepository` : la revue a relevé la redondance, et elle est
  assumée — un port à une méthode dit exactement le couplage réel et laisse les doubles de test à
  une méthode, là où le port complet en imposerait sept. Le compteur d'engagés est
  **partagé** avec le suivi de déroulé (une seule instance en composition root) pour que « combien
  sommes-nous » n'ait qu'une définition.
- **`FormatTournoi.modifier` remplace l'exigence au lieu de la fusionner** — contrat d'un `PUT`.
  ⚠️ Le paramètre a d'abord eu un **défaut `None`**, et la revue a trouvé **quatre** appelants qui
  l'omettaient, dont deux de production : `ServiceFormats.promouvoir` et l'écran Patrimoine →
  « Modifier » effaçaient la règle du club **en silence**. Une documentation ne suffit pas à tenir un
  invariant : le paramètre est désormais **sans défaut** des deux côtés (Python et TypeScript), et ce
  sont les compilateurs qui nomment les appelants fautifs. Un paramètre dont l'omission détruit une
  donnée ne doit pas pouvoir s'omettre.
- **Le calcul reste aveugle** à `le_reste`, `issue_de_tour` et aux prélèvements intermédiaires
  (§2). C'est une limite **énoncée**, pas un oubli : elle disparaîtra d'elle-même le jour où ces
  natures auront un consommateur (`DETTE-028`).
- **Un test de migration a dû être rendu insensible aux colonnes futures** : il insérait un tournoi
  via le mapping ORM **courant** dans un schéma arrêté à `0027`, donc toute colonne nouvelle le
  cassait. Il insère désormais en SQL explicite — un test de migration décrit un passé, que le
  présent n'a pas à réécrire.
