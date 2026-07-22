# Résumé du projet — où on en est au 22 juillet 2026

> Ce fichier est la **photo d'ensemble** : ce qui existe et fonctionne aujourd'hui, dans l'ordre où
> ça a été construit. Pour le détail « quelle US est faite, quelle est la suivante », voir
> [`SUIVI-US.md`](SUIVI-US.md). Pour le dernier fait marquant, voir le fichier daté le plus récent.

## Ce qu'est le produit

Kervignarc gère un **tournoi de tir à l'arc en salle (18 m)** pour un seul club, le jour J, sur un
réseau local **sans internet**. Un serveur fait autorité (FastAPI), sert l'application (React), et
pousse les changements en direct par WebSocket vers une trentaine de tablettes personnelles des
bénévoles. La rigueur est concentrée dans le **moteur métier** ; l'infrastructure reste simple parce
que le contexte est petit et local.

## L'état en une phrase

**Les fondations techniques sont complètes, la configuration d'un tournoi et les inscriptions
fonctionnent, le placement des archers sur les cibles existe, la saisie des scores de qualification
tourne en temps réel — y compris quand le wifi saute — et un tournoi de qualification se suit
désormais de bout en bout : les postes de saisie se supervisent, le classement se calcule, et le
public le consulte en direct sans compte — jusqu'à suivre un archer et voir sa feuille de marque se
remplir volée par volée. Côté organisateur, le **suivi des paiements** (qui a réglé, combien reste-t-il
dû, par archer et par club) est en place, un écran de **complétude** dit d'un coup d'œil ce qui
manque avant de terminer le tournoi, une **recherche d'archer** permanente répond à « je tire
où ? » depuis n'importe quel écran admin, et un écran **« Doublons »** repère les fiches en double
et les **fusionne** sans rien perdre.** Il reste à construire les duels (phases finales) et le
pilotage du jour J.

---

## Ce qui a été construit, par blocs

### 1. Les fondations (socle technique) — *terminé*

Tout l'échafaudage sur lequel le reste s'appuie est en place et verrouillé :

- Le **monorepo** (backend Python + frontend React) avec les outils qualité — formatage, typage
  strict, linters — vérifiés automatiquement **avant chaque commit** et en **intégration continue
  bloquante**. Rien de non conforme ne peut entrer.
- L'**architecture en couches** avec son garde-fou : le cœur métier ne peut importer aucun framework,
  c'est vérifié par un test. C'est ce qui garantit que le moteur du tournoi reste pur et testable.
- La **base de données** (SQLite) avec un **writer unique** : toutes les écritures passent par une
  file d'attente, une seule à la fois, pour éviter la corruption quand 30 tablettes écrivent ensemble.
- Le **canal temps réel** (WebSocket) qui diffuse un événement dès qu'une écriture est validée.
- Le **shell React** (gestion de l'état serveur, de l'état d'interface, client temps réel) et un
  **exécutable de développement** qui sert l'application façon production.

### 2. Configurer un tournoi — *terminé*

Tout ce qu'il faut pour préparer un tournoi avant le jour J :

- **Créer, éditer et lister des tournois**, avec un cycle de vie (brouillon / en cours / terminé).
  Plusieurs tournois peuvent être « en cours » en même temps (intérieur + extérieur).
- **Les catégories** (CRUD, pré-chargement des catégories officielles FFTA salle, éligibilité sur
  plusieurs tranches d'âge).
- **Les blasons** (la cible en papier) : taille, capacité, et les valeurs de score admises.
- L'**association catégorie ↔ blason**.
- Les **gabarits de salle** (le plan des cibles, réutilisable et ajustable).
- Le **barème de qualification** et le **grain de validation** d'une phase.
- Le **tarif par départ** (le montant d'inscription).

### 3. Les inscriptions — *terminé pour l'essentiel*

- Le **référentiel des clubs**.
- **Créer, éditer, supprimer un archer**.
- Configurer les **départs** (les créneaux de tir) et **inscrire un archer** sur des départs.
- **Contrôler les quotas** (fait en avance de phase).
- Le **calcul du montant dû** par un archer.
- Le **suivi des paiements** : un écran « Paiements » montre, **par archer** (dû / payé / reste,
  filtrable) et **par club** (mêmes totaux + détail), qui a réglé. On marque un paiement à la ligne,
  ou d'un geste **tout un archer** ou **tout un club** (règlement groupé) ; chaque marquage laisse une
  **trace** dans le journal d'audit (c'est de l'argent). Pas d'encaissement en ligne : c'est un statut.
- **Détecter et fusionner les doublons** : un écran « Doublons » repère les fiches qui désignent
  probablement le même archer saisi deux fois — mêmes nom/prénom/club, ou rapprochement approximatif
  (faute de frappe, prénom abrégé) classé « à vérifier ». L'organisateur choisit la fiche à **garder** ;
  l'autre y est **fusionnée** (ses inscriptions et scores sont repris) puis supprimée. Rien n'est perdu,
  et le geste demande une confirmation explicite.

*Restent à venir : import de fichiers d'inscription.*

### 4. Les rôles et l'accès — *socle en place*

- **Consultation publique ouverte** (n'importe qui sur le réseau peut regarder) et **accès
  administrateur protégé** (les écritures sont derrière un mot de passe).
- Les **scoreurs** du tournoi (définition et session de travail).
- Un **journal d'audit métier** qui trace les actions importantes.
- Le principe : les écritures ont d'abord été **toutes fermées à l'admin**, et seront **élargies**
  ensuite rôle par rôle (le scoreur, l'archer) — sans créer de route parallèle.

### 5. Le placement des archers — *base en place*

- **Placement automatique** des archers sur le plan de cibles.
- **Ajustement manuel** par glisser-déposer.
- **Alerte par calcul d'impact** avant de régénérer un plan : l'appli **ne prévient que quand ça
  compte** — silence tant qu'aucun score n'existe, et **alerte chiffrée** (« 156 archers vont être
  replacés ; 4 cibles ont déjà des scores, conservés ») quand la partie est engagée, où il faut alors
  **taper un mot** pour confirmer. Chaque replacement de ce type laisse une **trace** dans le journal.

*Restent à venir : contraintes (≥ 2 clubs par cible, séparation catégorie/blason), placement des
duellistes côte à côte, et le placement intégral 1→N du grand format.*

### 6. La saisie des scores de qualification — *terminé, et robuste*

C'est le cœur du jour J, et c'est le travail le plus récent :

- **Rattacher une tablette à sa cible** en scannant un **QR code**, avec impression des QR de cible
  et des codes scoreurs.
- Un **poste de cible peut saisir sans s'identifier** (le bénévole n'a pas de compte à créer).
- La **saisie en temps réel** : les volées et flèches se saisissent sur une grille tactile, le total
  se met à jour, et le score validé apparaît en direct sur les autres écrans.
- **La résilience réseau** (dernier fait marquant, 20/07) : si le wifi saute en pleine saisie, rien
  n'est perdu — les volées sont mises en file et **renvoyées automatiquement** au retour du réseau,
  sans doublon, et un **voyant de connexion** indique en permanence l'état. Détail dans
  [`2026-07-20-00h35-saisie-resiste-aux-coupures.md`](2026-07-20-00h35-saisie-resiste-aux-coupures.md).

### 7. Les documents imprimables — *socle en place*

- Le **socle PDF** et la **feuille de marque**.
- L'**impression des QR de cible et des codes scoreurs** (branché sur la saisie ci-dessus).

### 8. L'interface d'administration — *coquille posée*

- L'**ossature de navigation** de l'application admin (la coquille dans laquelle les écrans viennent
  se loger).
- Un **écran d'accueil qui demande le rôle de l'appareil** au premier lancement — **Tablette**,
  **Téléphone (public)**, **Scoreur** ou **Administration** — puis **s'en souvient** et va droit au bon
  écran ensuite. Le spectateur ne peut plus accéder par mégarde au mot de passe admin ou au code
  scoreur ; on change de rôle par un lien discret. Détail dans
  [`2026-07-21-22h10-choisir-son-role-au-lancement.md`](2026-07-21-22h10-choisir-son-role-au-lancement.md).

### 9. Suivre la qualification et l'afficher au public — *en place*

Ce qui transforme la saisie brute en tournoi qu'on suit en direct, dernier bloc construit :

- **Superviser les postes de saisie** : l'organisateur voit, sur un seul écran, l'état de chaque
  cible (rattachée, en ligne, en retard, à valider) — *un poste figé ne se plaint pas, seule la
  supervision le révèle*.
- **Le classement de qualification** : à partir des scores validés, le classement se calcule et se
  met à jour tout seul, par catégorie.
- **Les vues publiques** : n'importe qui sur le réseau consulte, sans authentification et depuis son
  téléphone, les **classements**, le **plan de cibles** (qui tire où), le tout **en direct** — chaque
  validation met les écrans à jour sans rien rafraîchir.
- **Suivre des archers** : on cherche un archer par son nom, on le **suit**, et l'application mémorise
  ce choix sur l'appareil (sans compte) — à la réouverture, elle affiche directement **sa cible / sa
  position / son départ**, à jour en direct. On peut en suivre plusieurs.
- **Le déroulé du tour en direct** : sous la place de l'archer suivi, sa **feuille de marque se remplit
  toute seule** — chaque volée avec ses flèches et son total, marquée **« en attente »** (en ambre,
  score provisoire) tant que le scoreur ne l'a pas confirmée, puis **« validé »** (en vert). Le public
  voit donc le tour se dérouler **avant** validation (choix assumé) ; le total « officiel » reste celui
  du classement, et la vue ne révèle jamais qui a saisi.
- **La complétude du tournoi** : un écran répond à « **qu'est-ce qui manque pour finir ?** » — le
  **sportif** (qualification cible par cible, classement) et le **hors sportif** (paiements) comptés
  **séparément**, chacun avec son état (terminé / à finir / en attente). L'écran dit **ce que
  « terminer » va figer** (le sportif ; les paiements restent modifiables) et, au moment de terminer —
  la seule action irréversible —, **chiffre ce qui reste** avant de laisser confirmer. Détail dans
  [`2026-07-22-00h40-completude-du-tournoi.md`](2026-07-22-00h40-completude-du-tournoi.md).
- **Rechercher un archer depuis n'importe où** : un champ de recherche **toujours présent en haut de
  la barre de navigation admin** — quel que soit l'écran affiché, le bénévole de la table
  d'organisation tape un nom et voit **immédiatement où l'archer tire** (départ, horaire, cible,
  position, pour chaque créneau), sans quitter sa page. C'est le **4ᵉ canal** pour répondre à « je tire
  où ? » (après les tablettes, les téléphones du public et « ma journée »). Détail dans
  [`2026-07-22-14h39-rechercher-un-archer.md`](2026-07-22-14h39-rechercher-un-archer.md).

*Reste à venir sur ce jalon : les **affectations du prochain tour** (phases finales). Les **duels**
eux-mêmes (1/8, 1/4…) apparaissent « à venir » dans la complétude — et la « prochaine affectation » de
la recherche restera vide — tant que leur moteur (EPIC-05) n'est pas construit.*

---

## Ce qui n'existe pas encore (les grands chantiers restants)

Dans l'ordre de valeur prévu par le backlog :

1. **Finir le tournoi de qualification** : l'appli publique ouverte directement sur **« ma journée »**
   (« c'est moi » mémorisé) et quelques listes imprimables.
   *(Supervision des postes, classement, vues publiques, suivi des paiements, complétude du tournoi et
   recherche d'un archer : faits — cf. blocs 3 et 9.)*
2. **Les duels** (phases finales) : arbre d'élimination directe, saisie en duels, abandon /
   disqualification, barrages, podium — **et surtout la bascule de tour**, qui est le moment où le
   produit gagne ou perd sa valeur.
3. **Le placement intégral 1→N** (le grand format du classeur 120) et l'**écran de salle** avec
   l'identité visuelle du tournoi.
4. **Confort et robustesse** : import inscript'arc, presets de barèmes, déroulé horaire, sauvegarde
   et restauration.

Un chantier transverse a été acté à l'entretien du 18/07/2026 et n'est pas encore implémenté : le
**cycle de vie enrichi à 7 statuts**, le **vocabulaire de score configurable**, et les **épreuves par
équipes** (nouvel EPIC-13, désormais dans le périmètre MVP).

---

## Chiffres repères

- **58 US livrées** sur `main` (mergées, revues, CI verte) à la date du 22/07/2026 — E02US005
  optimiste d'un cran sur la branche jusqu'à son merge. **`SUIVI-US.md` fait foi sur le compte exact.**
- Jalon **J0 (walking skeleton) : 100 %**. Jalon **J1 (qualification de bout en bout) : bien avancé
  (43/46)** — supervision, classement, vues publiques, suivi d'archers, déroulé du tour en direct,
  alerte par calcul d'impact, suivi des paiements, complétude du tournoi, recherche d'un archer et
  **détection/fusion des doublons** faits ; restent « ma journée » (« c'est moi ») et quelques
  imprimables.
- Dernière US livrée : **E02US005** (détecter et fusionner les doublons d'archers — écran « Doublons »
  admin : rapprochement heuristique à deux niveaux, fusion conservant inscriptions et scores).
  Elle est aussi la dernière à **surface visible**.
- Prochaine US prévue : cf. [`SUIVI-US.md`](SUIVI-US.md) (reprise de la séquence J1).
