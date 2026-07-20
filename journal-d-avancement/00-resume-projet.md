# Résumé du projet — où on en est au 20 juillet 2026

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
fonctionnent, le placement des archers sur les cibles existe, et la saisie des scores de qualification
tourne en temps réel — y compris quand le wifi saute.** Il reste à construire le classement de
qualification, l'affichage public, les duels (phases finales), et le pilotage du jour J.

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

*Restent à venir : import de fichiers d'inscription, détection de doublons.*

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

---

## Ce qui n'existe pas encore (les grands chantiers restants)

Dans l'ordre de valeur prévu par le backlog :

1. **Finir le tournoi de qualification** : superviser les postes de saisie, le **classement de
   qualification**, les vues publiques (classements, plans, live), le suivi des paiements.
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

- **46 US livrées** sur `main` (mergées, revues, CI verte) à la date du 20/07/2026.
- Jalon **J0 (walking skeleton) : 100 %**. Jalon **J1 (qualification de bout en bout) : bien avancé**,
  il reste le classement, l'affichage public et le pilotage.
- Dernière US livrée : **E04US009** (diffusion live & résilience réseau).
- Prochaine US prévue : **E12US001** (superviser les postes de saisie) — cf. [`SUIVI-US.md`](SUIVI-US.md).
