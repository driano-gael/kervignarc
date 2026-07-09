# EPIC-05 — Moteur de phases & tableaux

- **ID** : EPIC-05
- **Statut** : À planifier
- **Priorité** : MVP (séquence simple) → MVP+1 (placement intégral)
- **Dépend de** : EPIC-02, EPIC-04
- **Réfs** : `moteur-placement-lucky-loser.md` ; CDC technique §4.2 ; ADR-0004

## Objectif / valeur
Le **cœur du produit** et le point de risque n°1 : composer une séquence de phases et dérouler les tableaux (duels, repêchage, placement) via des **politiques injectables**. Un format = un assemblage de politiques, pas du code dédié.

## Périmètre
### Inclus
- **Constructeur de séquence** de phases (ajouter/ordonner/typer) + enregistrement en **modèle** réutilisable.
- **Politiques injectables** : `routing`, `scoring`, `seeding`, `byes`, `tiebreak`, `depth`.
- **Génération d'arbre** : arrondi 2^k, **seeding serpent**, gestion des **byes** (aux mieux classés).
- **Progression** automatique (gagnant avance ; perdant routé selon `routing`).
- **Peuplement** d'une phase depuis les sorties précédentes (rangs N→M, gagnants, perdants).
- Contrôles de cohérence (phase mal alimentée).

### Exclus
- Le calcul des classements finaux (EPIC-06) ; la saisie (EPIC-04).

## Capacités
- [ ] Modèle de séquence + éditeur.
- [ ] Bibliothèque de politiques + point d'assemblage.
- [ ] Générateur d'arbre + seeding + byes.
- [ ] Moteur de progression.

## Incréments
- **MVP** : séquence simple **qualif → élimination directe → podium** (`routing = élimination sèche`, `depth = podium`).
- **MVP+1** : **placement intégral en cascade 1→N** (routing = cascade), **repêchage** (routing = réintégration), **Big Shoot Off**, tableaux de placement.

## Critères d'acceptation (epic)
- **Oracle 120** : rejouer le tournoi de `Tableaux.xlsx` reproduit exactement l'arbre, le routage des perdants et le classement 1→120.
- Un format simple et le format intégral sont deux assemblages du même moteur.

## Risques
- Abstraction du **routage** (R1) : la concevoir avec l'oracle 120 dès le départ.
