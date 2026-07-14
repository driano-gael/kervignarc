# EPIC-12 — Pilotage du jour J

- **ID** : EPIC-12
- **Statut** : À planifier
- **Priorité** : MVP
- **Dépend de** : EPIC-03, EPIC-04, EPIC-05
- **Réfs** : [`cahier-des-charges-ux.md`](../cahier-des-charges-ux.md) §1, §7.1, §8, §9 (`D-15`→`D-25`) ; CDC fonctionnel M3/M5

## Objectif / valeur

**C'est ici que se trouve la valeur du produit.** Le coût réel d'un tournoi n'est pas la lenteur de la
saisie : c'est le **temps mort entre deux tours** — quelqu'un ramasse les feuilles, recopie, calcule,
constitue le tableau suivant, l'imprime, l'affiche, pendant que **150 archers attendent**.

> **Ce produit ne fait pas gagner du confort : il fait disparaître un temps mort.**

Cet EPIC porte le **poste de commande de l'organisateur** : voir ce qui bloque **avant** que ça bloque, et
faire partir le tour suivant **en deux minutes au lieu de vingt**, sans que personne ne coure, ne recopie,
ni ne crie au micro.

**Métrique de l'EPIC** (`D-25`) : **« dernier duel validé » → « les archers savent où aller » en < 2 min.**

> **Pourquoi un EPIC de plus.** Créé le 14/07/2026 : les 12 EPICs existants couvrent la configuration, les
> inscriptions, le placement, la saisie, le moteur, les classements, l'affichage, les paiements, les
> exports, les rôles et l'exploitation technique — **aucun ne couvrait le pilotage du jour J**, alors que
> c'est là que se joue la valeur. Le trou a été révélé par l'entretien de conception du 14/07/2026.

## Périmètre

### Inclus
- **Console de supervision** : l'état des ~30 postes de cible et des écrans de salle, en direct.
- **Complétude** : « qu'est-ce qui manque pour que ce tournoi soit fini ? », **sportif et hors sportif
  comptés séparément**.
- **Bascule de tour** : feu vert, lancement (global **ou par événement**), forfait tracé.
- **Recherche globale** d'un archer, depuis n'importe quel écran admin.
- **Règle d'alerte transverse** : l'appli **calcule l'impact** d'une modification au lieu de classer les
  actions d'avance.

### Exclus
- Le **calcul** du tour suivant (routage, seeding, byes) : c'est **EPIC-05**. Cet EPIC porte le **geste** et
  **l'affichage**, pas le moteur.
- Le **contenu** des affectations poussées vers les archers : **EPIC-07** (E07US008) et **EPIC-04**
  (E04US018). Ici on **lance** ; là-bas on **affiche**.
- Le **plan de salle** et son glisser-déposer : **EPIC-03** (et `Q-UX8`, non instruit).

## Capacités
- [ ] Superviser les postes (en ligne / hors ligne / non rattaché / dernière activité).
- [ ] Afficher la complétude du tournoi (sportif / hors sportif).
- [ ] Lancer un tour ou un événement, avec feu vert et impact chiffré.
- [ ] Tracer un forfait sans jamais bloquer.
- [ ] Rechercher un archer depuis n'importe où.
- [ ] Alerter par calcul d'impact (pas d'impact → pas d'alerte).

## Incréments
- **J1** : supervision des postes, recherche globale, complétude, règle d'alerte.
- **J2** : bascule de tour (feu vert, lancement global ou par événement, forfait tracé).

## Critères d'acceptation (epic)
- L'admin distingue **« ils tirent lentement »** de **« leur tablette est morte »** — *un écran figé ne se
  plaint pas*.
- Au moment où le dernier duel d'un tour est validé, **le tour suivant est déjà prêt** : le bouton ne
  calcule rien, il ne fait que lancer.
- **Aucune action n'est refusée** tant que le tournoi n'est pas terminé ; les actions à impact **chiffrent**
  leur conséquence avant de l'appliquer.
- Un archer absent **ne bloque jamais** un tour : il devient un **forfait tracé**.
