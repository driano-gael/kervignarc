# E08 — Suivi des paiements — User Stories

> EPIC : [EPIC-08](../epics/EPIC-08-paiements.md) · Réfs : CDC fonctionnel M8.

> ⚠️ Maille révisée le 17/07/2026 — E08US001 (livrée) reste atomique ; E08US002 absorbe E08US003/004.
> Regroupement des US de *suivi* (marquer / consulter par archer / consulter par club) — trois facettes
> d'une même capacité, sans dépendance séquentielle entre elles au-delà de E08US001. **Aucun comportement
> n'est perdu** (règle 9 — chaque ancien titre devient une puce CA identifiée). E08US001, déjà **livrée**,
> est recopiée à l'identique : ni son CA, ni ses dépendances, ni son jalon ne changent. E08US005 reste
> également inchangée (US seule dès l'origine). Correspondance ancien → nouveau en fin de fichier.

---

### E08US001 — Calculer le montant dû
*En tant qu'*administrateur, *je veux* le montant dû par archer, *afin de* facturer.
- **CA** : montant dû d'un archer = **somme des tarifs des départs** auxquels il est inscrit (E02US004 pose les tarifs des créneaux, E02US009 les inscriptions) ; recalculé si les inscriptions ou les tarifs changent. *(Révisé le 16/07/2026 — [ADR-0017](../docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md) : les prix pouvant différer par créneau, c'est une **somme**, non plus `tarif × nb`.)*
- **Notes — 21/07/2026** ([ADR-0041](../docs/adr/0041-tarification-configuration-du-tournoi.md)) : cette formule est désormais la **stratégie de tarification par défaut** (sujet `archer`, sans dégressif), et la **seule implémentée**. E08US002 **re-dérive** ce même calcul (`recapituler`, 2ᵉ occurrence admise règle 9) plutôt que d'appeler `montant_du_par_archer` : il y a donc **deux** sites de calcul du dû, à rediriger ensemble quand une politique injectable produira le dû (forfait club, dégressif — E01US020/E01US021). Le CA d'E08US001 **ne change pas** ; sa portée est simplement reconnue comme « un cas ».
- **Dépend de** : E02US004, E02US009 · **Jalon** : J1

### E08US002 — Suivi des paiements (marquer, vue par archer, vue par club)
*En tant qu'*administrateur, *je veux* marquer le statut de paiement et le consulter par archer et par club, *afin de* savoir qui a réglé et de gérer les règlements groupés.
- **CA — statut (ex-002)** : statut payé/non payé **par départ** (le booléen `paye` porté par l'inscription, E02US009) ; modifiable ; pas de transaction en ligne. *(Le CA disait « par archer (ou par départ) » ; tranché **par départ** le 21/07/2026 — c'est déjà la granularité du modèle, cohérente avec E08US005 qui présuppose une inscription « marquée payée ». Le « par archer » se dérive : réglé ⇔ toutes ses inscriptions payées.)*
- **CA — vue par archer (ex-003)** : liste des archers avec dû / payé / reste ; filtrable. (`reste = dû − payé` ; `dû` = somme des tarifs des créneaux inscrits, E08US001 ; `payé` = somme des tarifs des créneaux marqués payés.)
- **CA — vue par club (ex-004)** : totaux par club (dû, payé, reste) ; détail des archers du club. Les archers **sans club** (`club_id` `NULL`, [ADR-0014](../docs/adr/0014-club-inconnu-plutot-que-club-sentinelle.md)) forment un regroupement « Sans club » à part (placé en dernier) — sans quoi la somme des clubs ne retomberait pas sur le total du tournoi.
- **CA — règlement groupé** : marquer d'un geste **tout un archer** ou **tout un club** (les inscriptions de ses archers présents dans ce tournoi), pas seulement inscription par inscription. *(Arbitrage du 21/07/2026, dérivé du but « gérer les règlements groupés ». Le marquage simple par inscription — jusque-là dans E02US009 — migre dans cette capacité : **une seule voie d'écriture** du paiement, donc **toute tracée**.)*
- **CA — trace** : chaque marquage (simple ou groupé) laisse une entrée au **journal d'audit** (E10US005, action `paiement`). *(Arbitrage du 21/07/2026 : un paiement est un **mouvement d'argent**, il se trace comme la validation d'un score. Atomicité acte↔trace via le repository, [ADR-0035](../docs/adr/0035-atomicite-acte-trace-session-partagee.md) — jamais un paiement basculé sans trace.)*
- **CA — dû re-dérivé, tarification différée** ([ADR-0041](../docs/adr/0041-tarification-configuration-du-tournoi.md), 21/07/2026) : le suivi **re-dérive** le montant dû (somme des tarifs, `recapituler` — **2ᵉ occurrence**, il n'appelle pas `montant_du_par_archer`) : il n'est **pas** découplé de la stratégie par défaut, il l'**incarne**. Le payé est **binaire par créneau** (booléen `paye`) ; le partiel *au niveau archer/club* existe par **dérivation** (une partie des créneaux réglés), jamais comme montant saisi. **Différés** en tarification configurable (E01US020/E01US021 — le sujet `club` sur `club_id`/[ADR-0014](../docs/adr/0014-club-inconnu-plutot-que-club-sentinelle.md), pas via les équipes) : le **partiel fractionnaire** d'un créneau, le **sujet de facturation `club`** (unité facturée) et le **dégressif**.
- **Notes** : les trois anciennes US décrivaient une seule capacité vue sous trois angles (marquer, puis
  consulter individuellement, puis consulter par club) — aucune ne pouvait être livrée utilement sans les
  deux autres (une vue sans statut à afficher, un statut sans vue pour le lire). Le regroupement ne change
  aucun CA, il supprime seulement la dépendance séquentielle artificielle (003 et 004 dépendaient toutes
  deux de 002 sans dépendre l'une de l'autre). **Pas de transaction en ligne** (comme E08US005) : le
  paiement est un simple **statut**, pas un encaissement ; le « reste à payer » est **dérivé** (dû −
  encaissé), jamais stocké. La destination admin **« Paiements »** du CDC §7.1 est matérialisée par cette US.
- **Absorbe** : ex-E08US002, E08US003, E08US004. **Dépend de** : E08US001 · **Jalon** : J1

### E08US005 — Rembourser une inscription payée annulée
*En tant qu'*administrateur, *je veux* tracer le remboursement d'une inscription **payée** qui disparaît (créneau supprimé ou archer désinscrit), *afin de* ne pas laisser une somme encaissée sans contrepartie.
- **CA** : quand une inscription **marquée payée** est effacée — suppression d'un départ à inscriptions confirmée (E02US009, [ADR-0018](../docs/adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md)) ou désinscription — le montant encaissé devient un **remboursement à traiter** ; l'admin le marque **remboursé** (daté, tracé) ou **reporté** sur un autre créneau ; aucun encaissement en ligne (comme E08US002).
- **Notes** : **déportée d'E02US009** ([ADR-0018](../docs/adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md)) : E02US009 ne fait que *décompter* les payées détruites dans le message de confirmation ; le remboursement est un **mouvement d'argent**, absent du modèle tant que `paye` reste un simple booléen. Cette US introduit la notion de transaction/remboursement (registre daté), pas E02US009. **Ouverte** : forme exacte du registre (avoir, report, remboursement effectif) à cadrer avec l'organisateur.
- **Dépend de** : E02US009, E08US002 · **Jalon** : J2

---

## Correspondance ancien → nouveau (maille révisée du 17/07/2026)

| Ancienne US | Titre d'origine | Devient |
|---|---|---|
| E08US001 | Calculer le montant dû | **E08US001** (inchangée — livrée) |
| E08US002 | Marquer payé / non payé | **E08US002** — CA « statut » |
| E08US003 | Vue paiement par archer | **E08US002** — CA « vue par archer » |
| E08US004 | Vue paiement par club | **E08US002** — CA « vue par club » |
| E08US005 | Rembourser une inscription payée annulée | **E08US005** (inchangée) |
