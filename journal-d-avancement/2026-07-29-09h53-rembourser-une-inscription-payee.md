# 29 juillet 2026, 9 h 53 — Rembourser une inscription payée annulée

**Pour qui** : l'organisateur, à la table de gestion.

**Ce qui est nouveau.** Jusqu'ici, si un archer avait **réglé** son inscription et qu'on l'annulait —
en le désinscrivant, ou en supprimant le créneau — la somme encaissée disparaissait des écrans sans
laisser de trace : à l'organisateur de se souvenir « ah oui, il faut lui rendre ses 8,10 € ».
Désormais, l'application **retient** cet argent à rendre.

**Comment ça se présente.** Effacer une inscription **payée** ouvre automatiquement un
**remboursement à traiter**, listé dans un nouvel onglet **« Remboursements »** de l'écran
**Paiements**. Chaque ligne garde le **nom de l'archer**, le **créneau** concerné et le **montant** —
et elle **survit à la suppression du créneau** : même si le départ n'existe plus, le remboursement,
lui, reste visible. L'organisateur le marque ensuite **« Remboursé »** (l'argent a été rendu) ou
**« Reporté »** (réaffecté à un autre créneau, comme note). Un poste traité est définitif.

**Un garde-fou au passage.** Désinscrire un archer qui a **payé** ne se fait plus d'un clic : un
encadré prévient « *(untel)* a réglé ce départ : le désinscrire ouvrira un remboursement de 8,10 € »
et demande de **confirmer**. Un archer qui n'a rien payé (ou un créneau gratuit) se désinscrit
toujours librement, comme avant.

**Ce que ça ne fait pas.** L'application ne manipule pas d'argent réel — elle suit des **statuts**
(comme pour les paiements). Le « report » est une **note** : il ne ré-inscrit pas l'archer
automatiquement ailleurs (à faire à la main si besoin).

Recette pas-à-pas : [`docs/fonctionnel/E08US005.md`](../docs/fonctionnel/E08US005.md).
