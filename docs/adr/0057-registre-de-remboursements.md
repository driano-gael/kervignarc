# ADR-0057 — Registre de remboursements : mouvement d'argent né d'un effacement

- **Statut** : Accepté
- **Date** : 2026-07-29
- **Décideurs** : Organisateur / Architecte
- **Portée** : E08US005 (rembourser une inscription payée annulée)
- **Complète / amende** : [ADR-0018](0018-supprimer-un-depart-a-inscriptions-confirmable.md)
  (suppression d'un départ à inscriptions — qui **déportait** explicitement le remboursement vers
  cette US : `paye` n'étant qu'un booléen, E02US009 ne pouvait que *signaler* les payées détruites)
- **Lie** : [ADR-0035](0035-atomicite-acte-trace-session-partagee.md) (atomicité acte↔trace en session
  partagée — réemployée pour le traitement audité), E08US002 (suivi des paiements — le remboursement
  est le pendant « sortie » du paiement « entrée »), E10US005 (journal d'audit — action `REMBOURSEMENT`)

## Contexte et problème

Jusqu'ici, le paiement est un **simple booléen** `paye` porté par l'`Inscription` : rien dans le
modèle ne représente un **mouvement d'argent**. Or le CA d'E08US005 veut qu'une **somme encaissée à
rendre** ne disparaisse pas en silence quand une inscription **payée** est effacée — un départ à
inscriptions supprimé (ADR-0018) ou une désinscription. La difficulté centrale : quand l'inscription
est effacée, **sa ligne disparaît** ; le remboursement ne peut donc pas vivre dessus. Le CA laissait
la **forme exacte du registre** (« avoir, report, remboursement effectif ») ouverte, à cadrer avec
l'organisateur.

Arbitrages tranchés au cadrage (avant d'écrire les tests, règle 9) :

1. **Issues de traitement** : « remboursé » **et** « reporté » (le report reste une **intention
   consignée** — pas de ré-inscription automatique, capacité à part). Le report *avec* ré-inscription
   automatique (re-tarification, écart) a été **écarté** de cette US (trop gros pour une branche).
2. **Désinscription d'une inscription payée** : **confirmable** (comme la suppression de départ l'est
   déjà, ADR-0018), pas silencieuse — l'argent ne part jamais par mégarde.

## Décision

**1. Un registre à part, sans FK vers ce qui disparaît.** Nouvel agrégat `Remboursement`
(`domain/remboursement.py`) + table `remboursement` (migration 0033). Il **survit** à l'effacement de
l'inscription (et souvent du départ) : donc **aucune FK** vers `inscription`/`depart`. On fige des
**instantanés textuels** — `archer_prenom`, `archer_nom`, `creneau` — et le `montant_centimes`
encaissé, exactement comme `entree_audit`/`forfait` figent le **nom** de l'auteur plutôt qu'une FK
(la trace survit à la suppression du scoreur, E10US003). Seul `tournoi_id` reste une FK. Cycle de vie
à trois états : `à_rembourser → remboursé | reporté` (transitions terminales).

**2. Création = conséquence atomique de l'effacement, non tracée à l'audit.** Un poste naît **dans la
même transaction** que le `DELETE` de l'inscription payée qui le provoque — nouvelles méthodes de port
`InscriptionRepository.supprimer_avec_remboursement` (désinscription) et
`DepartRepository.supprimer_avec_remboursements` (suppression de départ, avec cascade des
inscriptions). « On n'efface une inscription payée que si sa contrepartie est ouverte » : jamais de
somme encaissée effacée sans trace, jamais de remboursement en double (un échec avant le `commit`
annule tout). La création **n'écrit pas** d'entrée au journal d'audit : la **ligne du registre est
elle-même la trace datée**. L'audit ne suit que l'acte **humain** (point 3).

**3. Traitement = acte humain audité.** Marquer un poste `remboursé`/`reporté` (`ServiceRemboursements`)
est un **mouvement d'argent** — côté sortie, comme le paiement l'est côté entrée — donc **audité**
(`ActionAuditee.REMBOURSEMENT`), atomicité acte↔trace via `RemboursementRepository.enregistrer_avec_trace`
(session partagée, ADR-0035, patron de `definir_paye_avec_trace`). Un poste déjà traité est
**terminal** : le re-traiter lève `RemboursementDejaTraite` (409) — conflit d'**état** porté par le
service (comme les transitions de statut de tournoi), pas par l'entité (pure).

**4. Désinscription payée confirmable.** `ServiceInscriptions.desinscrire(confirme=False)` lève
`InscriptionPayeeARembourser` (409, `details` = montant + archer) sur une inscription **payée d'un
créneau tarifé** tant que `confirme` est faux ; confirmée, elle supprime **et** ouvre le poste. Une
inscription non payée (ou d'un créneau **gratuit**) se désinscrit librement (E02US009 inchangé). Même
règle côté suppression de départ : seules les payées **de tarif > 0** ouvrent un poste (invariant
`montant > 0` de l'entité), et le message de signalement d'ADR-0018 est aligné (`tarif > 0`).

## Conséquences

- **Positif** : le CA « ne pas laisser une somme encaissée sans contrepartie » est tenu de bout en
  bout et **structurellement** (atomicité de l'ouverture) ; aucune donnée comptable ne suit une FK
  vers une ligne partie ; cohérence de langage (confirmation chiffrée `DepartEnCoursNonConfirme`,
  audit `PAIEMENT`↔`REMBOURSEMENT`). Front : onglet « Remboursements » de l'écran Paiements + dialogue
  de confirmation à la désinscription payée.
- **Coût / limite** : `traite_le`/`cree_le` ne sont **pas** validés UTC-*aware* au domaine (contrairement
  à `EntreeAudit`/`Forfait`) — la date vient exclusivement du port `Horloge` (jamais d'une entrée
  utilisateur), simplicité assumée (règle 12) ; le round-trip UTC est réattaché à la relecture comme
  pour l'audit. Le **report** ne ré-inscrit pas (intention seulement) : une US ultérieure pourra
  l'outiller. La **purge liée à la suppression d'un tournoi** reste non tranchée (DETTE-001, comme
  `forfait`/`entree_audit`).
- **Dette signalée (remède structurel, non traité ici)** : la constante `_AUTEUR_ADMIN =
  "Administrateur"` atteint son **3ᵉ site** (`application.paiements`, `application.placement`,
  désormais `application.remboursements`). Le seuil « factoriser au 3ᵉ cas » (CLAUDE.md § Dette) est
  atteint — mais l'extraction d'une constante partagée est un **remède structurel** : à traiter en US
  dédiée, pas en douce dans E08US005. La duplication locale reste **assumée** en attendant.
