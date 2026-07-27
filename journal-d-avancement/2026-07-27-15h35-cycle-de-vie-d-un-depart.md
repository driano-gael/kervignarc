# Un créneau de tir connaît son état — et se protège une fois lancé

**27 juillet 2026, 15h35 — E12US008**

Jusqu'ici, un **créneau** (départ) se modifiait ou se supprimait de la même façon, qu'il soit vide ou
en plein tir. Rien n'empêchait d'effacer par mégarde un créneau où des archers avaient déjà des
scores.

Désormais, chaque créneau **affiche son état**, dans la liste des départs, par un badge :

- **Ouvert** (gris) : personne n'a encore tiré → on l'édite et le supprime librement, comme avant ;
- **Lancé** (ambre) : au moins une flèche a été validée → une session de tir est en cours ;
- **Clos** (vert) : tout le monde a terminé (ou est forfait).

Cet état n'est **jamais saisi** : il se **déduit tout seul** du tir réel. Et sur un créneau **lancé
ou clos**, éditer ou supprimer déclenche un **avertissement chiffré** — « ce créneau est lancé, 8
archers ont déjà tiré » — avec un bouton pour **confirmer quand même**. Rien n'est fait sans ce
geste ; on ne détruit plus une session de tir par accident. Un créneau **ouvert**, lui, reste aussi
souple qu'avant.

Pour l'organisateur, c'est un garde-fou discret : la liste des créneaux devient une **photo du
déroulé** (ce qui n'a pas commencé, ce qui tire, ce qui est fini), et les gestes dangereux demandent
un instant de réflexion pile quand il le faut.

*Sous le capot : l'état est **calculé**, pas stocké — en réutilisant le moteur de complétude déjà en
place. Décisions dans l'ADR-0051 ; pas à pas de recette dans `docs/fonctionnel/E12US008.md`.*
