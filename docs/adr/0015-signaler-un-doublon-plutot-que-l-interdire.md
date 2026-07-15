# ADR-0015 — Signaler un doublon d'archer plutôt que l'interdire : 409 + confirmation

- **Statut** : Accepté
- **Date** : 2026-07-15
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E02-inscriptions.md`](../../stories/E02-inscriptions.md) (E02US002 : le CA
  imposait un « index UNIQUE de dédoublonnage ») ; [`modele-de-donnees.md`](../modele-de-donnees.md)
  (`ARCHER`, index retiré)
- **Introduit par** : E02US002 (créer un archer) ; **lie** E02US005 (détecter/fusionner les
  doublons), E02US007 (import inscript'arc), et tout futur besoin de **forçage**

## Contexte et problème

E02US002 devait poser `UNIQUE(tournoi_id, nom, prenom, club_id)` pour empêcher qu'un archer soit
inscrit deux fois. Un fait métier casse ce CA : **un père et son fils portent parfois les mêmes nom,
prénom et club** — cas ordinaire en compétition de club. L'index les rejetterait, sans recours, au
guichet, le jour J.

Mais l'inverse est aussi vrai : la double saisie du même archer est l'erreur la plus banale d'une
table d'inscription, et rien ne la rattrape ensuite — **aucun endpoint ne supprime un archer**
(c'est E02US003). Il faut donc un dispositif qui distingue deux cas que **les données ne
distinguent pas**. Seul l'humain devant le guichet le peut : il voit s'il a affaire à une personne
ou à deux.

## Options

1. **`UNIQUE` strict, conforme au CA** — garantie de base, coût nul. Mais il refuse un cas réel et
   légitime, et un refus de base ne se négocie pas.
2. **Aucun contrôle** — tout passe, E02US005 nettoiera. Mais E02US005 est loin (jalon J1, seq 71) et
   le placement (seq 35) arrive avant : on placerait des doublons.
3. **Signaler et laisser confirmer** — le service détecte l'identité déjà inscrite, refuse une
   première fois (`409 homonyme_archer`), et le client rejoue l'appel porteur d'une **confirmation**
   explicite.

## Décision

Retenir l'option 3, **sans index `UNIQUE`**.

- **Le contrôle vit dans le service applicatif**, au sens de `domain.archer.cle_identite` (nom,
  prénom, club ; casse et accents repliés par `domain.club.cle_nom`).
- **Aucune contrainte de base ne le double**, contrairement au patron `Club` (où `nom_club_deja_pris`
  est doublé d'un `UNIQUE`). C'est une rupture assumée : ici, la contrainte **rejetterait le fils**.
- **La confirmation est un drapeau du corps de requête** : `autoriser_homonyme: bool = false` sur
  `POST /api/v1/tournois/{id}/archers`. Le client qui reçoit le 409 réémet le même corps avec le
  drapeau à `true`.
- **Le 409 est une question, pas un verdict.** C'est ce qui le distingue de tous les autres 409 du
  projet (`club_reference`, `blason_reference`, `tournoi_en_cours_non_supprimable`,
  `nom_club_deja_pris`), qui sont des refus fermes sans recours.
- **Le signalement n'est pas un contrôle d'accès** : la route est déjà réservée à l'admin
  (`exiger_admin`). Un client peut poser le drapeau d'emblée — c'est admis (voir Conséquences).

### Pourquoi le contrôle applicatif suffit ici

Le garde-fou d'un `UNIQUE` est de fermer la fenêtre entre « je vérifie » et « j'insère ». Cette
fenêtre **n'existe pas** dans ce projet : toutes les écritures passent par la file d'écriture
consommée par un **writer unique** (règle 7, [ADR-0005](0005-async-et-sqlite.md)), et surtout le
contrôle **et** l'insertion tiennent dans **la même commande soumise** (`ServiceArchers.ajouter`,
routé par une seule lambda depuis `api/v1/competition.py`). Deux inscriptions concurrentes sont
sérialisées ; la seconde voit la première.

**C'est une garantie de déploiement, pas de code** : elle repose sur un processus unique
(mono-club, LAN — ADR-0005). Un second worker uvicorn la romprait en silence. Cette hypothèse est
déjà celle du projet entier ; elle n'est pas introduite ici.

## Conséquences

- **+** Le père et le fils s'inscrivent tous les deux, et le doublon accidentel est arrêté net.
  Le seul dispositif capable de trancher — l'humain — est appelé au seul moment où il peut le faire.
- **+** Le message nomme l'inscrit (« *Jean Dupont* est déjà inscrit à ce tournoi ») : l'admin
  reconnaît sa propre erreur, ou identifie l'homonyme, sans quitter l'écran.
- **−** **C'est le premier protocole « refuser puis confirmer » du projet, et son premier drapeau de
  forçage.** Il fera précédent. Si un autre besoin de forçage apparaît — ADR-0014 en anticipe déjà
  un, la suppression forçante d'un club —, il devra soit suivre cette forme (drapeau booléen dans le
  corps, réservé à l'admin), soit justifier d'en diverger. Ne pas inventer une 2ᵉ convention
  (en-tête, jeton d'idempotence, endpoint `/forcer`) sans ADR.
- **−** **Le drapeau est cru sur parole.** Un client peut poser `autoriser_homonyme: true` dès le
  premier appel et créer autant de doublons qu'il veut. C'est la forme normale d'un flux de
  confirmation, et la route est admin-only — mais cela veut dire que le garde-fou **protège d'une
  erreur, pas d'une volonté**. Il n'y a rien à durcir : un admin déterminé à créer un doublon a
  toujours raison de l'application.
- **−** **E02US007 (import inscript'arc) devra trancher à nouveau.** Un import écrit des archers en
  masse, sans personne pour confirmer : poser le drapeau à `true` globalement désarmerait le
  contrôle pour tout un fichier, et c'est exactement ce que le rapport d'import (E02US008) doit
  éviter. La réponse attendue n'est ni l'un ni l'autre — c'est de **collecter** les homonymes et de
  les présenter en fin d'import. Noté dans la story.
- **−** **L'unicité fonctionnelle n'a aucun garde-fou hors de `ServiceArchers.ajouter`.** Un futur
  chemin d'écriture (import, restauration de sauvegarde, script) doit passer par le service, jamais
  par le repository. Rien ne l'empêche techniquement.
- **−** Côté client, la confirmation doit rester **liée à l'identité signalée** : si l'utilisateur
  modifie le nom après le 409, le signalement ne s'applique plus et doit être effacé — sinon le
  bouton « Inscrire quand même » confirmerait un archer que le serveur n'a jamais examiné. C'est un
  piège réel, trouvé en revue d'E02US002 : voir `InscriptionArcher` (`surIdentite` → `reset()`).

## Alternative écartée — un numéro de licence FFTA

Un identifiant national rendrait le doublon **décidable** et fermerait la question (deux licences
différentes = deux archers). Écartée pour l'instant, mêmes raisons qu'en
[ADR-0014](0014-club-inconnu-plutot-que-club-sentinelle.md) : nullable elle ne dédoublonne rien,
obligatoire elle impose la saisie d'un numéro à 7 chiffres au guichet. Elle arrivera avec E02US007,
où le fichier fédéral la porte déjà — et c'est **là** que ce protocole pourra être reconsidéré.

## Liens

[ADR-0005](0005-async-et-sqlite.md) (writer unique, sur lequel repose la sérialisation) ;
[ADR-0007](0007-erreurs-par-couche.md) (409 par omission à la frontière) ;
[ADR-0014](0014-club-inconnu-plutot-que-club-sentinelle.md) (même arbitrage, même US) ;
`backend/domain/archer.py` (`cle_identite`) ; `backend/application/erreurs.py` (`HomonymeArcher`) ;
[`glossaire.md`](../glossaire.md) (*Homonyme*) ; [`modele-de-donnees.md`](../modele-de-donnees.md)
(`ARCHER`).
