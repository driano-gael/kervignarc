# ADR-0016 — Supprimer un archer engagé : confirmer et détruire, plutôt que refuser — et ne pas confondre avec le forfait

- **Statut** : Accepté
- **Date** : 2026-07-16
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E02-inscriptions.md`](../../stories/E02-inscriptions.md) (E02US003 : le CA
  disait « suppression bloquée … **ou** confirmation + recalcul », et l'arbitrage du 15/07 avait
  d'abord retenu le **refus définitif**) ; [`stories/E12-pilotage-jour-j.md`](../../stories/E12-pilotage-jour-j.md)
  et [`stories/E04-saisie-scores.md`](../../stories/E04-saisie-scores.md) (le CA du forfait ne disait
  pas qu'il **préserve** les flèches — c'est pourtant ce qui le distingue de la suppression)
- **Complète** : [ADR-0015](0015-signaler-un-doublon-plutot-que-l-interdire.md) (protocole
  « refuser puis confirmer »), qui reste **Accepté** — sa décision sur les doublons ne change pas
- **Introduit par** : E02US003 (éditer / supprimer un archer) ; **lie** E04US015 (abandon / DSQ en
  qualification), E12US004 (tracer un forfait en duels), E10US005 (audit), et la résorption de
  [DETTE-001](../dette.md)

## Contexte et problème

E02US003 devait permettre de retirer un archer de la liste. Le CA offrait deux branches sans
choisir : « suppression bloquée si l'archer est déjà placé/engagé **(ou confirmation + recalcul)** ».

**Premier arbitrage (15/07/2026) : refus définitif.** Motif : le patron constant du projet — on
refuse plutôt que de cascader en silence (`ClubReference`, `BlasonReference`,
`TournoiEnCoursNonSupprimable`) — et rien à recalculer avant EPIC-03. La revue d'US a montré que ce
refus produisait un **cul-de-sac** : aucun geste ne permettant de retirer un placement (`placer`
n'accepte qu'une cible ≥ 1) ni d'effacer un score (métier d'EPIC-04), un archer placé ou ayant tiré
devenait **définitivement** indéboulonnable — et le message lui prescrivait « retirez-le de son
placement », geste introuvable. Une dette a été ouverte pour tracer ce trou.

**Le trou n'était pas là où on le croyait.** Ce que le premier arbitrage avait manqué, c'est que la
vraie alternative au refus n'était pas « purger », c'était **« déclarer forfait »** — un concept que
le backlog portait **déjà** ([E04US015](../../stories/E04-saisie-scores.md) pour la qualification,
[E12US004](../../stories/E12-pilotage-jour-j.md) pour les duels) et qui n'avait pas été cherché. Le
refus définitif tenait la place du forfait sans en être un : il produisait un mur là où le métier
veut **documenter une absence**.

Il y a donc **deux besoins distincts**, que les données ne distinguent pas et que le premier
arbitrage avait fusionnés en un seul refus :

| | L'archer **abandonne** | L'archer **n'aurait jamais dû être inscrit** |
|---|---|---|
| Fréquence | courant le jour J | rare (erreur de saisie, doublon confirmé à tort) |
| Ses flèches | **font partie de la compétition** | n'auraient pas dû exister |
| Réponse juste | **forfait** — daté, attribué, motif, réversible, audité | **suppression** — la ligne disparaît |
| Effet sur les résultats | **préservés** | **détruits** |
| US porteuse | E04US015 (qualif.) / E12US004 (duels) | E02US003 |

Confondus, l'un des deux est forcément faux : refuser la suppression rend l'erreur de saisie
inrattrapable ; supprimer un abandon détruit les résultats d'un archer qui a réellement tiré.

## Options

1. **Refus définitif** (arbitrage du 15/07, écarté). Conforme au patron du projet, mais **prescrit
   l'impossible** : le message nomme une porte de sortie qu'aucun écran n'ouvre, et l'archer reste
   à vie dans la liste. Le patron « on refuse » suppose une **issue** (`ClubReference` : « réaffectez
   ces archers » — geste qui, lui, existe). Sans issue, ce n'est plus un garde-fou, c'est un mur.
2. **Cascade silencieuse.** Supprimer emporte scores et placement, sans rien demander. Écartée : elle
   détruit des données saisies sur un simple clic, et fait de la destruction le chemin par défaut de
   l'archer qui s'en va — exactement ce que le forfait doit servir.
3. **Signaler, puis détruire sur confirmation** (retenue). Le service refuse une première fois
   (`409 archer_engage`) en **énumérant ce qui sera perdu** et en nommant le forfait ; le client
   rejoue l'appel porteur d'une confirmation explicite.

## Décision

Retenir l'option 3, et **séparer explicitement forfait et suppression** dans le vocabulaire du
projet ([`glossaire.md`](../glossaire.md) : *Engagé*, *Placé*, *Forfait*).

- **`ArcherEngage` est un signalement**, 3ᵉ de la famille ADR-0015 : 409, drapeau de confirmation,
  `False` par défaut, route admin. Il se déclenche si l'archer est **placé** (`cible` renseignée)
  **ou** **engagé** (au moins un score).
- **Sa confirmation détruit** — et c'est le premier du projet dans ce cas. Les deux autres
  signalements *créent* (`HomonymeArcher`) ou *déplacent* (`ChangementCategorieArcherEngage`).
  **Rupture assumée** avec « on refuse plutôt que de cascader en silence » : on cascade, mais **pas
  en silence** — c'est toute la différence, et c'est ce que le message porte.
- **Le message énumère la perte** (nombre de flèches, numéro de cible) et **nomme le forfait** comme
  l'autre chemin. Il ne dit pas « confirmez pour supprimer » : un message qui invite à cliquer ferait
  de la destruction le geste réflexe.
- **À l'écran, ce signalement ne ressemble pas aux deux autres** : bouton `--danger`, libellé qui
  nomme la perte (« Supprimer définitivement, avec ses résultats ») là où les autres disent
  « … quand même ». Les trois se ressemblent, leurs conséquences non.
- **Transport du drapeau : paramètre de requête** (`?autoriser_suppression_engage=true`), et non le
  corps qu'ADR-0015 pose comme forme. **Divergence de transport, pas de protocole** — un `DELETE`
  n'a pas de corps par convention HTTP et des intermédiaires le suppriment. La substance d'ADR-0015
  est tenue : booléen explicite, `False` par défaut, 409 puis rejeu, route admin ; aucune des formes
  qu'il prohibe nommément (en-tête, jeton d'idempotence, endpoint `/forcer`). **C'est cet ADR qui
  sanctionne la variante** — ADR-0015 étant immuable, il ne pouvait pas l'accueillir.
- **La purge est applicative, et atomique** : `ArcherRepositorySQL.supprimer` efface les scores puis
  l'archer dans **une seule transaction**. `score.archer_id` est une FK sans `ON DELETE`
  ([DETTE-001](../dette.md)) : deux transactions successives laisseraient, si la seconde échouait, un
  archer dépouillé de ses flèches. C'est la cascade **maîtrisée** qui manque au reste de la
  descendance de `tournoi`.
- **La confirmation vit dans le service** (`ServiceArchers.supprimer`), la **purge dans l'adapter**.
  Le port l'exige (`ArcherRepository.supprimer`), parce que le service ne peut pas obtenir
  l'atomicité en orchestrant deux repositories : la frontière transactionnelle est la commande
  d'écriture, pas le service (règle 7, [ADR-0005](0005-async-et-sqlite.md)).

## Conséquences

- **+** L'erreur de saisie redevient rattrapable, y compris après une flèche. C'était le cul-de-sac
  du 15/07, et c'est le cas d'usage même de l'écran d'administration des archers.
- **+** ADR-0015 tient sa promesse : son Contexte notait que la double saisie « n'est rattrapée par
  rien — **aucun endpoint ne supprime un archer** (c'est E02US003) ». Le rattrapage existe, et il est
  **complet** : même engagé, le doublon confirmé à tort s'efface.
- **−** **La destruction est irréversible et aucun journal ne l'enregistre.** L'audit des actions
  sensibles est E10US005 ; d'ici là, un archer supprimé ne laisse aucune trace — ni qui, ni quand, ni
  quoi. C'est le prix accepté d'un outil mono-club dont l'admin est le seul opérateur, et c'est un
  argument pour E10US005.
- **−** **Le bouton « Supprimer » existe, le forfait pas encore.** Tant qu'E04US015 / E12US004 ne sont
  pas livrées, un archer qui abandonne n'a **aucun** moyen propre d'être enregistré — et la
  suppression est là, à portée de clic, prête à faire exactement la mauvaise chose. Seul le message
  s'y oppose. **C'est une raison de prioriser E04US015**, pas d'employer la suppression à sa place.
- **−** **E04US015 et E12US004 héritent d'une contrainte** : le forfait **doit préserver les flèches
  déjà tirées**. C'est la propriété sur laquelle repose toute la distinction posée ici ; leurs CA la
  portent désormais. Un forfait qui effacerait les résultats rendrait cet ADR faux.
- **−** **Ne pas poser `ON DELETE CASCADE` sur `score.archer_id`** en résorbant DETTE-001. La
  confirmation vit **en amont**, dans le service : une cascade en base ne la contourne pas sur ce
  chemin, mais elle armerait une purge **silencieuse** sur tout **autre** chemin de suppression d'un
  `archer` (cascade depuis `tournoi`, import, script) — c'est-à-dire l'option 2, écartée ici.
- **−** **Les drapeaux de confirmation doivent s'accumuler côté client.** Le serveur teste chaque
  signalement à chaque appel et n'en lève qu'un ; un client qui n'enverrait que le dernier drapeau
  confirmé boucle indéfiniment entre deux 409, et l'édition devient impossible. Piège réel, trouvé en
  revue d'E02US003 : voir `FormulaireArcher` (`cumul`). Il vaut pour tout futur cumul de forçages,
  et il s'ajoute à la contrainte d'ADR-0015 (la confirmation reste **liée aux valeurs signalées** —
  donc les drapeaux se purgent dès qu'un champ change).
- **−** **Le drapeau est cru sur parole**, comme celui d'ADR-0015 : un client peut le poser d'emblée.
  Ici la conséquence est une **destruction**, pas une création. La route est admin-only et rien n'est
  à durcir contre une volonté — mais la clause d'ADR-0015 (« c'est la forme normale d'un flux de
  confirmation ») avait été raisonnée pour un protocole de **création**, où poser le drapeau à
  l'aveugle ajoute une ligne. Elle est reprise ici pour une **destruction** ; c'est un choix, pas une
  reconduction tacite.
- **−** **La confirmation est aveugle, et c'est la faiblesse de cette décision**
  ([DETTE-007](../dette.md)). Toute la sûreté du dispositif repose sur le message ; or le rejeu ne
  revérifie pas le compte annoncé. Entre le 409 et le clic, les 30 tablettes du jour J saisissent :
  confirmer une suppression annoncée à « 1 flèche » peut en détruire sept. La sérialisation par le
  writer unique (ADR-0015 §*Pourquoi le contrôle applicatif suffit*) **ne couvre pas ce cas** — elle
  ferme la fenêtre *dans* une commande, pas *entre deux requêtes HTTP*. Le remède est une
  confirmation **contractuelle** (le client renvoie le compte vu, le service re-signale s'il a
  changé) ; il attend que le champ `details` de la réponse d'erreur soit peuplé — règle 5 le prévoit,
  rien ne l'a jamais utilisé. **Reconnu à la revue d'E02US003, différé en US dédiée.**

## Alternative écartée — ouvrir « retirer le placement » dans E02US003

Une revue a proposé de fermer la moitié « placement » du cul-de-sac en ajoutant `Archer.deplacer()`
(`cible = None`) + `DELETE /archers/{id}/placement`, ~5 lignes. Écartée par l'arbitrage métier, qui
la rend **sans objet** : la suppression étant confirmable, il n'y a plus de cul-de-sac à ouvrir. Et
elle n'aurait fermé qu'une moitié — effacer un score reste le métier d'E04US015, avec ses règles
propres (une flèche validée ne s'efface pas comme une flèche en cours de saisie). Le retrait d'un
placement viendra avec EPIC-03, qui remplace de toute façon le placement provisoire du walking
skeleton (« un simple numéro », E00US011) par le vrai moteur.

## Liens

[ADR-0015](0015-signaler-un-doublon-plutot-que-l-interdire.md) (protocole « refuser puis
confirmer », que cet ADR complète et dont il sanctionne la variante `DELETE`) ;
[ADR-0005](0005-async-et-sqlite.md) (writer unique, frontière transactionnelle) ;
[ADR-0007](0007-erreurs-par-couche.md) (409 par omission à la frontière) ;
[ADR-0014](0014-club-inconnu-plutot-que-club-sentinelle.md) (l'écran des archers, où le club inconnu
devient corrigeable) ; `backend/application/erreurs.py` (`ArcherEngage`) ;
`backend/domain/ports.py` (`ArcherRepository.supprimer`, contrat de purge) ;
[`glossaire.md`](../glossaire.md) (*Engagé*, *Placé*, *Forfait*) ; [`dette.md`](../dette.md)
(DETTE-001) ; [E04US015](../../stories/E04-saisie-scores.md) et
[E12US004](../../stories/E12-pilotage-jour-j.md) (le forfait — ce que la suppression n'est pas).
