# ADR-0077 — Supprimer un tournoi : signaler sa descendance, puis confirmer — jamais cascader en silence

- **Statut** : Accepté
- **Date** : 2026-08-07
- **Décideurs** : Organisateur / Architecte
- **Étend** : [ADR-0016](0016-supprimer-un-archer-engage-plutot-que-le-refuser.md) — même protocole,
  un cran au-dessus : ce qui valait pour l'**archer engagé** vaut pour le **tournoi peuplé**
- **Complète** : [ADR-0015](0015-signaler-un-doublon-plutot-que-l-interdire.md) (protocole
  « refuser puis confirmer »)
- **Résorbe** : [DETTE-001](../dette.md) — suppression de tournoi non cascadée
- **Introduit par** : arbitrage du commanditaire du 07/08/2026, en revue d'E01US025

## Contexte et problème

`DETTE-001` est ouverte depuis E01US002 et s'est aggravée à **chaque** table ajoutée à la
descendance du tournoi : `categorie`, `archer`, `blason`, `gabarit_salle`, `depart`, `scoreur`,
`poste`, `entree_audit`, `remboursement`, `deroule_etape` en enfants directs, et tout ce qui pend
en dessous (`score`, `inscription`, `serie`, `forfait`, `phase`, `barrage`, `barrage_tir`…).

Aucune de ces clés étrangères ne porte de politique de suppression, et le service ne purge rien.
Supprimer un tournoi non vide lève donc une `IntegrityError` — c'est-à-dire un **500**, la pire des
réponses : ni un refus qu'on comprend, ni une suppression qui aboutit.

**Le blocage n'était pas technique.** Écrire la cascade est mécanique ; ce qui manquait, c'est la
**décision** : purger en silence, ou refuser ? Le registre porte cette question ouverte depuis
treize mois, et chaque US qui ajoutait une table l'a contournée en posant un marqueur de plus.

**Ce qui a rendu la question urgente.** E02US010 a rendu le 500 **systématique** : passer un tournoi
à `prêt` exige désormais au moins un départ, donc plus aucun tournoi `prêt` / `en cours` / `terminé`
n'est vide. Le test `test_supprimer_un_termine` est en `xfail` depuis.

## Décision

**Le tournoi suit le protocole de l'archer engagé (ADR-0016) : on signale, l'admin confirme, puis
on détruit — en cascade applicative, jamais par `ON DELETE CASCADE` en base.**

1. **Un tournoi vide se supprime sans rien demander.** Aucun signalement inutile : la confirmation
   doit rester rare pour rester lue.
2. **Un tournoi peuplé est signalé en 409**, avec un **décompte chiffré** de ce qui partira —
   archers, inscriptions, scores, séries, duels, forfaits, barrages, remboursements. « Une alerte
   qui ne chiffre pas son impact est un clic de plus, pas une protection » (`D-16`) : le message
   nomme les natures et leurs nombres, il ne dit pas « des données existent ».
3. **L'admin confirme explicitement** (`autoriser_suppression_peuplee=true`), et la suppression
   s'exécute alors **en une transaction**, dans l'ordre imposé par les liens latéraux.
4. **Les gardes d'état existantes ne bougent pas** : `TournoiEnCoursNonSupprimable` reste un refus
   **définitif**, non confirmable. Un tournoi qu'on est en train de tirer ne se supprime pas, quelle
   que soit la confirmation — ce n'est pas la même question.
5. **Pas d'`ON DELETE CASCADE` en base**, pour la raison exacte qu'ADR-0016 a écartée sur `score` :
   la confirmation vit **en amont**, dans le service. Une cascade SQL ne contournerait pas la
   confirmation *sur ce chemin*, mais elle armerait une purge **silencieuse** sur **tout autre**
   chemin — import, script de maintenance, futur endpoint. Le garde-fou doit être là où la décision
   se prend.

### Ce qui a été écarté

- **Refuser définitivement.** C'est l'arbitrage qu'ADR-0016 avait pris puis **corrigé** : il produit
  un cul-de-sac. Un tournoi d'essai peuplé par erreur deviendrait indéboulonnable, et le message
  prescrirait des gestes introuvables (« videz-le d'abord »).
- **Cascader sans confirmation.** Supprimer en silence des paiements encaissés et des flèches
  validées est exactement ce que le projet refuse partout ailleurs.
- **Archiver au lieu de supprimer.** Le cycle de vie a déjà `archive` (ADR-0026) : c'est le geste de
  celui qui veut *garder*. La suppression doit rester possible pour celui qui veut *jeter*.

## Conséquences

**Positives**

- La dette la plus ancienne du registre se ferme, et avec elle le `xfail` d'E02US010.
- **La règle devient uniforme** : archer, départ, tournoi suivent le même protocole. Une seule
  chose à apprendre, et le prochain enfant direct n'aura qu'à s'ajouter au décompte.

**Coûteuses / à surveiller**

- ⚠️ **La cascade applicative a un ordre, et il n'est pas commutatif.** Les `inscription` doivent
  partir **avant** les archers *et* avant les départs (deux FK) ; les `phase` **avant** les départs
  (elles y pendent depuis [ADR-0075](0075-le-depart-est-la-portee-sportive.md), ce n'est plus un
  enfant direct du tournoi) ; la `categorie` avant son `blason`, l'`archer` avant sa `categorie`.
  Se tromper d'ordre redonne une `IntegrityError`, c'est-à-dire le défaut qu'on corrige.
- **Trois adapters connaissent déjà la descendance d'`archer`** (`supprimer`, `fusionner`, et les
  cascades partielles d'E02US003/E02US009). Le résolveur devra les **réutiliser**, pas en écrire un
  quatrième — sans quoi une table ajoutée demain sera oubliée dans l'un des quatre.
- **`remboursement` est un cas à part** : effacer une somme encaissée sans ouvrir de remboursement
  est précisément ce que `DETTE-018` décrit. Le décompte doit le **dire**, et l'US devra trancher
  si la suppression d'un tournoi ouvre des remboursements ou les efface avec le reste.

## Porté dans le code par

*(à renseigner par l'US de résorption — cet ADR est une décision, la section nommera les modules qui
l'appliquent : `application/tournois.py` (`ServiceTournois.supprimer`), l'adapter concret portant la
cascade transactionnelle, `api/v1/tournois.py` pour le 409 et le drapeau de confirmation, et le
front pour le `<dialog>` de confirmation — [ADR-0072](0072-confirmation-destructrice-dialog-natif.md).)*
