# ADR-0064 — L'écran de salle est un poste typé, et son pilotage est un état lu

- **Statut** : accepté
- **Date** : 01/08/2026
- **US** : E07US004 — « Écran de salle : déroulé automatique, pilotage admin, et suivi du plan »
- **Liés** : [ADR-0029](0029-mode-d-identite-poste-de-cible-et-jeton-de-poste.md) (session de poste),
  [ADR-0038](0038-presence-des-postes-par-heartbeat.md) (supervision par heartbeat),
  [ADR-0063](0063-brouillon-de-format-invariant-a-l-application.md) (schéma à braquets),
  [ADR-0056](0056-lancement-d-un-tour-acte-audite-et-diffuse.md) (lancement-événement)

## Contexte

E07US004 demande trois choses : qu'un écran projeté dans le gymnase **informe tout seul** (un
déroulé de vues à cadence réglable), que l'organisateur puisse **lui imposer une vue à distance**
sans traverser la salle, et que le **plan du tournoi se regarde se remplir** (phases, tour en cours,
duels joués sur duels attendus).

Trois éléments de terrain cadrent la décision :

1. Le CA est explicite sur la nature de l'écran : *« ce n'est ni une 4ᵉ appli, ni une vue autonome :
   c'est un **poste**, comme une tablette de cible — donc rien de neuf à inventer (réemploi du
   jeton, du QR, de la supervision) »*.
2. Le hub temps réel (`infrastructure.realtime.broadcaster`) est **mono-canal** : il diffuse à tous
   les abonnés, sans ciblage par destinataire. Il n'existe aucun canal serveur → poste.
3. Le CA exige qu'« une prise de contrôle sache se terminer » et qu'il n'y ait « **jamais un état
   forcé qu'on oublie** ». Le motif est écrit dans la story : *basculer sur le podium à 17 h et
   partir serrer des mains, c'est un écran figé sur le podium à 18 h pendant que les gens cherchent
   leur classement.*

## Décision

### 1. L'écran de salle est un `Poste` **typé**, pas un agrégat parallèle

`Poste` gagne un `type` (`cible` | `ecran`). Un écran porte un **libellé** de place dans le gymnase
au lieu d'un `cible_index`, et son **déroulé de vues** (`SequenceVues`).

Le typage rend `cible_index` facultatif. Plutôt que de laisser chaque appelant décider quoi faire
d'un `None` — et parfois l'oublier —, l'invariant « seul un poste de cible a une cible » est **rendu
exigible au point d'usage** : `Poste.cible()` lève `PosteSansCible`. Symétriquement,
`PosteSansEcran` garde `deroule_effectif` / `avec_libelle`.

L'exclusivité `cible_index` ↔ `libelle` **n'est pas** un `CHECK` en base : le projet n'en utilise
nulle part, et en poser un ferait vivre une règle métier hors du domaine (règle 2). Le prix assumé :
une écriture SQL directe pourrait produire une ligne incohérente.

### 2. Le pilotage admin est un **état lu**, pas un ordre poussé

Quand l'organisateur impose une vue, la consigne est **posée** dans un registre ; l'écran la **lit**
et décompte lui-même. Aucun ordre n'est envoyé, rien n'est acquitté.

Deux raisons, et **la seconde suffirait** :

- le hub est mono-canal (cf. contexte) : pousser un ordre à *un* écran demanderait l'abonnement par
  sujet, qui n'existe pas ;
- surtout, la **fin** d'une prise de contrôle naît du **temps qui passe** — et aucun événement
  serveur ne peut pousser le temps qui passe. C'est mot pour mot le raisonnement d'ADR-0038 §4, qui
  a valu à la console de supervision d'être en *poll* plutôt qu'en WebSocket : le passage hors-ligne
  d'un poste ne se diffuse pas, il se dérive à la lecture.

Conséquence pratique, et c'est un gain : la reprise du déroulé **ne dépend d'aucun message**. Un
écran qui perd le réseau pendant la prise reprend quand même à l'heure — il connaît le début et la
durée, il décompte en local (`domain.ecran.reste_secondes`).

⚠️ **Trois conditions rendent cette phrase vraie**, et il a fallu **deux passes de revue** pour les
réunir — ce qui est en soi l'enseignement le plus utile de cet ADR :

1. l'affichage porte un champ **`deroule_repli` distinct**, toujours égal au déroulé propre de
   l'écran ;
2. le front **cesse d'honorer** `vue_figee` dès que le reste atteint zéro ;
3. et il **rejoue le repli**, pas `sequence`.

La première version n'en honorait aucune (l'écran ne recevait rien vers quoi retomber). La deuxième
repliait `sequence` sur le déroulé propre : correct pour une **vue figée**, faux pour une **séquence
imposée**, où `sequence` porte déjà la consigne — l'écran isolé continuait alors de la jouer *en
affirmant au bandeau avoir repris son déroulé*. D'où un champ distinct plutôt qu'un champ à deux
sens : quand une valeur doit signifier deux choses selon le contexte, elle finit par mentir dans
l'un des deux.

Rappel général : **une garantie annoncée dans un ADR n'existe que si un chemin de code la produit —
et qu'un test l'exerce.** Ici la logique d'arbitrage vivait dans le JSX, donc hors de toute épreuve ;
elle a été extraite dans `rotation.ts` (`vueAAfficher`) et couverte, sur les trois cas.

### 3. Déroulé **persisté**, prise de contrôle **en mémoire**

Le déroulé de vues est un réglage de **préparation** (« paramétré à la préparation du tournoi ») :
il est en base, sur le poste, et survit au redémarrage du serveur le matin du jour J.

La prise de contrôle est un geste du **jour J** : elle vit dans un registre en mémoire, comme les
sessions de poste (ADR-0029) et la présence (ADR-0038). Effet de bord **voulu** : un redémarrage du
serveur **libère** les écrans au lieu de les figer — c'est le CA « jamais un état forcé qu'on
oublie », appliqué à la panne.

### 4. Q-UX7 tranchée : durée **et** retour explicite

Une prise de contrôle porte une durée bornée **ou** aucune (« jusqu'à ce que je rende la main »), et
« Rendre la main » reste disponible dans les deux cas. Une consigne sans échéance porte
`Consigne.exige_rappel` — un drapeau **nommé dans le domaine**, que la console transforme en rappel
très visible. Le domaine ne peut pas empêcher un oubli ; il peut le nommer, et sans ce point
d'ancrage « jamais oublié » serait resté une intention de rédaction.

### 5. Le suivi **superpose**, il ne recalcule pas

`domain.deroule.projeter` (ADR-0063) dit ce qui est **attendu** — les braquets, la *Règle R*, les
duels par tour. `domain.suivi_deroule` y superpose ce qui est **fait**. Les deux structures restent
**séparées** jusque dans le DTO (`blocs` + `avancement`, appariés par `ordre`).

C'est la contrainte du CA — *« le **même** schéma à braquets que l'atelier »* : un suivi qui
recalculerait les duels attendus pourrait diverger du schéma que l'organisateur a composé. C'est
aussi ce qui permet **un seul composant de dessin pour trois surfaces** côté front.

**Deux écarts à combler pour que « joués » et « attendus » parlent de la même chose** — et le second
n'a été trouvé que par la relecture adversariale :

1. **Un exempt (bye) n'est pas un duel joué.** Dans un tableau incomplet, les exempts sont gagnés
   d'office dès la construction : les compter afficherait « premier tour terminé » avant que
   quiconque ait tiré. La projection ne les compte pas non plus (`_braquets` : *« 24 duellistes dans
   un tableau de 32 → 8 duels, 8 exemptés »*).
2. **Un braquet décrit une branche, pas un rang de l'arbre.** `_braquets` ne suit que la branche des
   **gagnants** : au dernier tour il annonce **un** duel, alors que le tableau réel en porte
   **deux** — la finale (places 1-2) et la **petite finale** (places 3-4), que `PlacementEnCascade`
   fait jouer aux perdants des demies. Les compter ensemble donnait « 2 joués sur 1 attendu »,
   plafonné à 1 : dès que la petite finale tombait, la phase s'affichait **terminée pendant que la
   finale se tirait**, sur l'écran projeté, au moment de la journée où il est le plus regardé. On
   filtre donc la **réalité** sur la plage du braquet (`Match.plage`), et non le dessin — corriger
   `_braquets` le ferait diverger de ce que l'organisateur a composé, ce que le §5 interdit.
3. **Les deux plages ne sont pas dans le même repère.** `_braquets` produit des rangs **absolus**
   (« un tableau des rangs 33-64 rend des perdants en 49-64 ») ; `construire_tableau` engendre des
   `Match.plage` **relatives au tableau**, toujours à partir de 1. Le filtre du point 2 ne pouvait
   donc fonctionner que pour une tranche partant du rang 1 — le seul cas que montaient les fixtures.
4. **Et les deux arbres n'ont pas la même taille.** `# DETTE-028` : `ServiceSaisieDuels._decor`
   ensemence le tableau avec *tous* les archers en lice, sans lire `Phase.sources`, quand
   `_braquets` compte l'effectif **déclaré**. Un format FFTA courant — qualification à 120, puis
   élimination directe déclarée « rangs 1-32 » — donne **7 tours réels contre 5 projetés**.

**La décision : apparier les braquets aux tours réels par la FIN, jamais par le début.** Un braquet
décrit la branche des gagnants qui se resserre jusqu'à la finale ; le tableau réel s'y resserre
aussi. Les *N* tours projetés sont donc les *N* **derniers** tours réels. Et la branche des gagnants
se reconnaît à deux traits **indépendants du repère** : elle part du haut du tableau
(`plage.debut == 1`) et sa **largeur** vaut celle du braquet — une largeur est un nombre de rangs,
pas une position.

Propriétés obtenues : **identité** quand les structures concordent, lecture **monotone et jamais
prématurée** sinon (`0, 0, 16, 24, 28, 30, 31` sur 32 déclarés / 120 en lice), et la phase ne se
ferme **qu'au tour qui porte la finale**. Quand le tableau est plus large que la phase déclarée, les
premiers tours réels ne remplissent rien — ce qui est honnête : ils font tirer des archers que le
format déclaré ne comptait pas.

Ces quatre écarts illustrent la même chose : **superposer deux calculs oblige à prouver qu'ils
comptent la même population, dans le même repère et à la même profondeur** — et cette preuve ne se
lit ni dans les noms, ni dans les types. Il a fallu **trois passes de revue** pour la faire, parce
que chaque correctif intermédiaire était juste sur le cas que la fixture d'alors montait, et faux
sur la classe dont il faisait partie. Le test qui verrouille aujourd'hui n'affirme donc pas un
chiffre : il affirme l'**invariant** — tant que la finale n'est pas tirée, la phase n'est pas
terminée — et le vérifie **à chaque tour**, sur une divergence de taille réaliste.

### 6. Un composant de dessin, trois surfaces — **sans variation de géométrie**

| Surface | Écran | Interaction | Habillage |
|---|---|---|---|
| Atelier — composer (E01US024) | PC | on compose | outil (`D-27`) |
| Pilotage — suivre | PC | oui | outil |
| Salle — projeter | ≥ 1920 px, vu de loin | **aucune** | identité (`D-27`, `DV-08`) |

La géométrie (`shared/schema-braquets/geometrie.ts`) rend le **même** plan partout. Ce qui varie est
au-dessus : la taille de rendu (fixe et défilante / ajustée à l'écran), l'habillage, et le calque
d'avancement. C'est le `viewBox` du SVG qui met tout à l'échelle, **texte compris** : l'écran de
salle affiche le dessin de l'atelier, simplement plus gros.

## Conséquences

**Positives**

- L'écran hérite gratuitement du **jeton**, du **mécanisme de rattachement par code**, du
  **heartbeat** et de la **console de supervision** — donc du CA « un écran figé ne se plaint pas,
  seule la supervision le révèle ». ⚠️ En revanche l'**étiquette QR imprimée** reste propre aux
  cibles : `ServiceDocumentsSalle` exclut explicitement les écrans du PDF d'étiquettes, et leur
  code s'affiche en clair dans l'écran d'administration. Le mécanisme d'URL `?poste=CODE` est
  réutilisable, l'artefact imprimé n'est pas produit *(précision de revue — une première rédaction
  disait « du QR », ce qui aurait laissé croire le PDF déjà livré)*.
- Un seul flux de rattachement côté front : le même code mène à la saisie ou à l'affichage.
- La reprise du déroulé est insensible au réseau et au redémarrage serveur.
- Le suivi ne peut pas diverger du schéma composé : il ne le recalcule pas.

**Négatives / à surveiller**

- `uq_poste_tournoi_cible` est **affaiblie** : `cible_index` étant nullable et SQLite considérant
  chaque `NULL` comme distinct, la contrainte ne protège plus que les lignes de type `cible`. C'est
  précisément le CA (« plusieurs écrans possibles »), mais c'est une garantie de moins en base.
- Le pilotage n'est pas instantané : l'écran voit la consigne à son prochain poll (~15 s). « En
  direct » au sens du CA est tenu à cette granularité, pas à la seconde.
- Le registre de consignes est **par processus**. Le déploiement est mono-processus (règle 7,
  single-writer SQLite) ; un jour où l'application tournerait en plusieurs workers, les prises de
  contrôle deviendraient incohérentes — au même titre que les sessions de poste, déjà dans ce cas.
- ~~Le catalogue de vues (`VueEcran`) est **plus court que le CA**~~ — **prédiction vérifiée, et
  close le 04/08/2026.** Cet ADR annonçait que `affectations` et `tableaux` s'ajouteraient « avec
  leur US, sans migration : la valeur persistée est la chaîne, pas un rang ». C'est arrivé **trois
  fois** — `palmares` (E06US004), `affectations` (E07US008), `tableaux` (E07US005) — et **aucune
  migration** n'a été nécessaire. Le catalogue couvre désormais le CA en entier. La règle qui a
  tenu à chaque fois, et qui vaut pour la vue suivante : **on n'inscrit une vue qu'une fois son
  écran capable de l'afficher**, sinon le réglage programme une page vide — et un écran de salle
  n'a personne devant lui pour comprendre ce qui manque.
  *(Cette ligne a été laissée périmée par E07US008, qui n'en avait corrigé que la moitié : un ADR
  qui prédit juste et que personne ne vient clore finit par être le seul document à dire le
  contraire de la réalité. Relevé à la revue d'E07US005.)*
- L'habillage « identité » se distingue aujourd'hui par la mise en page, **pas par la palette** :
  `DV-08` ne sera pleinement honoré que quand E01US016 aura livré l'identité visuelle du tournoi.

## Alternatives écartées

- **Un agrégat `EcranSalle` distinct.** Aurait dupliqué le credential, le jeton, la présence et la
  supervision — quatre mécanismes recopiés pour changer un champ. Contraire au CA, qui dit
  explicitement « rien de neuf à inventer ».
- **Pousser l'ordre par WebSocket.** Aurait demandé l'abonnement par sujet (inexistant) *et*
  n'aurait toujours pas su terminer une prise à durée : le temps qui passe ne se diffuse pas.
- **Persister la prise de contrôle.** Aurait figé les écrans au redémarrage — l'inverse du CA.
- **Un composant de dessin par surface.** Trois dessins cousins à maintenir, et la promesse « le
  même schéma » perdue à la première divergence.
- **Paramétrer la géométrie par densité.** Même problème sous une autre forme : le lecteur aurait dû
  réapprendre le dessin d'un écran à l'autre, alors que le `viewBox` suffit à changer d'échelle.

---

## Amendement du 05/08/2026 — une seconde cadence, non pilotée, sur la surface projetée

Le lot « retours du questionnaire de maquettes » a **paginé** la vue « affectations » de l'écran de
salle (`maquettes/questionnaires/p06-salle-affectations.md`), fermant une question que E07US008
laissait explicitement ouverte — « 200 archers ne tiennent pas sur un écran projeté ».

**Compatible sur le mécanisme.** La page se déduit du temps écoulé, jamais d'un compteur incrémenté :
c'est le raisonnement du §2 de cet ADR et de `salle/rotation.ts`, et pour la même raison (minuteurs
bridés en arrière-plan, huit heures d'affilée).

**⚠️ Divergent sur le modèle, et il faut le dire.** Le §3 pose que tout ce qui gouverne l'affichage
d'un écran de salle est un **état lu** : le déroulé est un réglage persisté sur le poste, la prise de
contrôle un registre serveur. La cadence de page est la **première horloge de cette surface qui n'est
ni persistée, ni réglable, ni visible en supervision** — l'organisateur ne peut ni la voir ni la
changer. Elle est inscrite au registre de dette (**DETTE-039**) et son réglage est spécifié en
`E16US009`.

**Deux cadences coexistent donc**, et leur rencontre a produit un défaut réel, corrigé avant merge :
la pagination était d'abord calée sur l'heure absolue, comme la rotation de vues. L'analogie était
fausse d'un cran — la rotation tourne **en continu**, la vue paginée non, elle n'est à l'écran qu'une
étape sur N. Résultat : certaines pages ne sortaient **jamais** (déroulé « affectations 30 s +
classement 30 s », trois pages → la page 2 jamais projetée de la journée). La pagination compte
désormais son **temps d'affichage cumulé**, et reprend où elle s'était arrêtée.

**Conséquence de ce correctif, à connaître** : deux écrans voisins portant le même déroulé ne
tournent plus forcément sur la même page — ils tournent ensemble sur les **vues** (heure absolue),
plus sur les **pages** (temps d'affichage propre, qui dépend de l'instant d'allumage). C'est le prix
assumé pour que toutes les pages sortent : mieux vaut deux écrans décalés que des archers dont le nom
n'est jamais projeté.

---

## Amendement du 18/08/2026 — le catalogue porte des **phases**, pas des arbres

`VueEcran.TABLEAUX` est devenue `VueEcran.EN_COURS`
([ADR-0089](0089-le-catalogue-de-vues-porte-des-phases-pas-des-arbres.md), `E05US031`) : la vue rend
désormais la phase qui se joue quel que soit son format — poule, ronde de système suisse, manche de
Big Shoot Off, arbre de duels. Les trois formats sans arbre étaient jouables de bout en bout depuis
plusieurs semaines sans qu'aucun n'atteigne jamais l'écran de salle : le trou était dans la **forme**
de ce catalogue, dont la seule valeur de rencontre supposait un arbre.

⚠️ **Ce que cet amendement retire au §1 ci-dessus, et lui seul.** La section se félicitait — à juste
titre — que le catalogue se soit élargi **trois fois sans une seule migration**, preuve que persister
la **chaîne** valait mieux qu'un rang. La propriété tient toujours : elle rend un **ajout** gratuit.
Elle ne dit rien d'un **renommage**, et le quatrième mouvement en fut un : il a coûté la migration
`0047`. Lire le §1 comme « le catalogue ne coûte jamais de migration » serait un contresens.

La règle du §1 qui gouverne les ajouts — *on n'inscrit une vue qu'une fois son écran capable de
l'afficher* — n'est pas touchée, et elle a été **tenue** : l'aiguilleur front et le DTO public du Big
Shoot Off sont livrés dans le même diff que la valeur d'enum.
