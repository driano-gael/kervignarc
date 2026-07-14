# ADR-0011 — Introduire une `Phase` minimale dès J1 pour héberger le barème de qualification

- **Statut** : Accepté
- **Date** : 2026-07-14
- **Décideurs** : Organisateur / Architecte
- **Précise / anticipe** : ADR-0004 (moteur de phases à politiques injectables, prévu EPIC-05)

## Contexte et problème

E01US009 demande un **barème de qualification** paramétrable par tournoi (nb de volées × nb de
flèches par volée, classement au **cumul**), avec un preset FFTA 18 m (**20 × 3 = 60 flèches**,
[référentiel §6.1](../referentiel-ffta.md)) modifiable. On est au **jalon J1** (tournoi de
qualification de bout en bout) ; le **moteur de phases** et ses politiques injectables (ADR-0004)
relèvent d'EPIC-05 (J2+) et ne sont pas implémentés.

Le modèle de données cible ([`modele-de-donnees.md`](../modele-de-donnees.md)) range pourtant le
barème dans la **config d'une `PHASE`** (`config.scoring`), pas sur le tournoi. Trois endroits
possibles pour le barème de qualif à J1 :

1. **attribut du `Tournoi`** (colonnes/JSON sur `tournoi`) — simple, mais **diverge** du modèle
   cible et imposerait une **migration** des données quand le moteur arrivera ;
2. **entité `BaremeQualification` dédiée** liée 1:1 au tournoi — encore une divergence du modèle
   cible et un 1:1 à garder cohérent ;
3. **une `PHASE` `qualification`** portant le barème dans sa `config` — **conforme au modèle
   cible**, au prix d'introduire le concept `Phase` avant EPIC-05.

## Décision

Retenir l'option 3, **bornée au strict nécessaire** : introduire une entité `Phase` **minimale**
et une table `phase`, dont E01US009 n'exploite qu'**une** phase de type `qualification` par
tournoi, portant le barème dans `config` (`{"scoring": {"volees": N, "fleches": M, "mode":
"cumul"}}`).

**Dans le périmètre (J1, E01US009) :**
- agrégat `Phase` pur (immuable) : `tournoi_id`, `ordre`, `type` (`TypePhase`), `statut`
  (`StatutPhase`), et un barème de qualification typé (`BaremeQualification`, value object validé) ;
- table `phase` **alignée sur le modèle de données** (colonnes `ordre`, `type`, `config`,
  `statut`) — pour ne pas créer une table divergente qu'il faudrait ensuite compléter ;
- un seul type utilisé (`qualification`) et un seul `statut` (`a_venir`) ; `ordre = 1` ;
- barème `BaremeQualification` (nb volées ≥ 1, nb flèches/volée ≥ 1 ; total et score max dérivés) ;
  preset FFTA 18 m (20 × 3), **modifiable** (principe « le règlement est un template », référentiel
  §10.2, arbitré le 2026-07-14).

**Hors périmètre (→ EPIC-05, ADR-0004) :** le **moteur**, les **politiques injectables** (routage,
seeding, byes, départage, profondeur), la **séquence** multi-phases et son édition, les
**transitions de statut**, et les autres **types de phase**. `ordre` et `statut` sont introduits
comme **données** conformes au modèle cible mais ne portent encore **aucun comportement** : le
moteur les exploitera. Le champ `config` n'accueille pour l'instant que la clé `scoring` ; les
autres politiques y viendront sans changement de schéma.

## Conséquences

- **+** Le barème de qualif vit dès J1 **là où le modèle cible l'attend** : pas de migration de
  données à prévoir quand le moteur (EPIC-05) généralisera la `config` de phase.
- **+** `config` en JSON : ajouter les politiques d'ADR-0004 plus tard **n'altère pas** le schéma.
- **+** `Phase` reste un agrégat pur et synchrone (ADR-0003) ; l'écriture passe par la file
  (ADR-0005), comme les autres ressources rattachées au tournoi.
- **−** On introduit `Phase` **avant** le moteur : `ordre`/`statut` sont pour l'instant des champs
  passifs, et le barème typé sur `Phase` est spécifique à la qualification (les autres phases
  porteront des politiques génériques). EPIC-05 généralisera — risque de refactor mesuré, assumé
  ici pour éviter la double migration.
- **−** `phase.tournoi_id` est une nouvelle FK de la descendance de `tournoi` sans politique de
  suppression : **aggrave DETTE-001** (inscrite au registre, marqueur `# DETTE-001` posé).

## Liens

ADR-0004 (moteur de phases à politiques injectables), ADR-0003 (hexagonale), ADR-0005 / ADR-0010
(file d'écriture, unité de travail), ADR-0007 (erreurs par couche) ;
[`referentiel-ffta.md`](../referentiel-ffta.md) §6.1 et §10.2 ; [`dette.md`](../dette.md) DETTE-001.
