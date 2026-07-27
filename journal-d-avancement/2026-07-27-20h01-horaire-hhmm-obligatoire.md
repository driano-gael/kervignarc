# 27 juillet 2026, 20h01 — L'horaire d'un départ devient une vraie heure (et deux garde-fous)

**Pour l'organisateur.** À la démo du matin, un créneau affiché « 8h00 » se lisait « 18h00 » : le
numéro du départ se collait à un horaire tapé à la main, sans format. C'est corrigé.

Désormais, l'horaire d'un créneau (départ) est une **vraie heure du jour**, au format **`HH:MM`** —
par exemple `09:00`. Il est **obligatoire** : on ne crée plus un départ sans heure, et le champ de
saisie **aide** (il n'accepte que des chiffres et place le « : » tout seul). Fini les « 9h00 »,
« matin » ou les cases vides ambiguës.

Deux garde-fous accompagnent ce changement, pour que le cycle de vie du tournoi reste cohérent :

- un tournoi ne peut passer **« prêt »** (le feu vert au démarrage) que s'il a **au moins un
  départ** — sinon il n'y aurait rien à jouer ;
- on ne peut plus **supprimer le dernier départ** d'un tournoi déjà lancé ; pour repartir de zéro,
  il faut d'abord le ramener en brouillon.

Les horaires déjà saisis lors des essais (« 8h00 ») sont **repris automatiquement** en `HH:MM`
(« 08:00 ») à la mise à jour.

*Recette pas à pas : [`docs/fonctionnel/E02US010.md`](../docs/fonctionnel/E02US010.md).*
