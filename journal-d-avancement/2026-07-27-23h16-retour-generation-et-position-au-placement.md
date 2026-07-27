# 27 juillet 2026, 23h16 — Le placement dit ce qu'il fait, et montre la position de chacun

*(Retour de la démo du 27/07 — E03US011. Correctif d'affichage : rien ne change dans le calcul du
placement, seulement ce que l'organisateur en voit.)*

Deux petits agacements repérés à la démo, côté écran de **placement des archers sur les cibles**.

**« Générer le plan » ne paraît plus muet.** Avant, on cliquait sur le bouton et… rien ne semblait se
passer : pas de « je travaille », et si la génération n'aboutissait à rien (départ sans archer) ou
laissait des archers **en réserve**, on pouvait croire que le clic n'avait rien fait. Désormais le
bouton affiche **« Génération… »** pendant qu'il calcule, puis **confirme le résultat** :
- **« Plan prêt : tous les archers sont placés. »** quand tout le monde a une place ;
- **« Plan généré : N placés, M en réserve. »** quand certains restent à caser ;
- **« Plan généré : aucun archer à placer sur ce départ. »** si le créneau est vide.

Et si l'opération échoue (réseau coupé au mauvais moment, par exemple), un **message d'erreur lisible**
s'affiche au lieu d'un silence — le plan reste inchangé, on peut réessayer.

**La position de chaque archer est visible.** La lettre de position (**A, B, C, D…**) n'apparaissait
que sur les cases **vides** ; dès qu'un archer était posé, on ne voyait plus que son nom. Maintenant,
**devant le nom** de chaque archer posé, sa **position** est affichée en couleur d'accent — la même
information que sur l'écran public, ce qui rend les deux vues cohérentes et facilite la vérification.

Pour tester pas à pas : [`docs/fonctionnel/E03US011.md`](../docs/fonctionnel/E03US011.md).
