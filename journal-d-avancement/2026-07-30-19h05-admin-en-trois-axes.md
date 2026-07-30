# 30/07/2026 — 19 h 05 · L'administration ne ressemble plus à une liste de tout ce que le logiciel sait faire

## Le problème, dit par le commanditaire

> « Bien que le backend soit solide, le pilotage de l'interface ne me va pas du tout : je n'arrive pas
> à sentir si le code fait ce que je veux, et surtout ce dont j'ai besoin pour mon client. »

L'écran d'administration alignait **25 destinations** dans deux tiroirs — « Préparation » (19) et
« Jour J » (6). Ce rangement suivait **le temps du tournoi**. En pratique, il suivait surtout
**l'ordre dans lequel les fonctions avaient été développées** : chaque nouvelle fonctionnalité
ajoutait sa ligne au menu. L'écran racontait l'histoire du chantier, pas le travail de l'organisateur.

## Ce qui change

L'administration s'ouvre maintenant sur **trois cartes**, une par **nature d'activité** :

- **Atelier** — fabriquer ce qui ressert d'une année sur l'autre : catégories, blasons, clubs, salles
  types, barèmes, formats de déroulé, plus le banc d'essai. **Sans tournoi** : ce sont les pièces du
  club, pas d'une édition.
- **Pilotage** — faire tourner la journée : tableau de bord, supervision des tablettes, feu vert,
  classement en direct, placement, staff.
- **Gestion** — l'administratif : inscriptions, paiements, exports, archives.

On entre dans un axe, et on ne voit **que** ses écrans. Plus de tiroirs à déplier. On revient au choix
par « ← Accueil », toujours visible.

**Pourquoi ce n'est pas un simple rangement.** Le critère précédent — le temps — **coupait en
morceaux** les activités qui durent. Le suivi des inscriptions et des paiements commence des semaines
avant le tournoi, encaisse le jour même et se termine après : il se retrouvait éclaté entre les deux
tiroirs. Le nouveau critère les garde ensemble.

## Deux écrans sortent enfin de l'ombre

Le **tableau de bord** d'un tournoi (sa frise de vie, ce qui reste à faire, les chiffres-clés) et le
**cockpit de simulation** (qui rejoue un tournoi entier en accéléré, sans rien enregistrer) étaient
rangés comme deux entrées de menu parmi dix-neuf, entre « Blasons » et « Postes de cible ». Ce sont
pourtant les deux écrans qui **montrent ce que le produit sait faire**. Le premier est désormais
l'écran d'ouverture du Pilotage, le second l'entrée du banc d'essai de l'Atelier.

## Chaque écran a maintenant une adresse

`…/admin/12/pilotage/supervision` désigne la supervision **du tournoi 12**. Concrètement :

- **`F5` ne fait plus perdre son écran** — ni le tournoi sur lequel on travaillait ;
- **un lien s'envoie** : « regarde cette adresse » ouvre exactement la même vue chez le destinataire ;
- **plusieurs écrans s'ouvrent côte à côte** dans plusieurs onglets — ce qui sert directement à
  vérifier le produit et à le présenter.

Les quatre mondes ont aussi la leur : `/public`, `/scoreur`, `/cible`, `/admin`. L'adresse d'une
tablette dit **`/cible`** — le mot que le bénévole lit sur l'étiquette collée devant la cible.

**Les QR déjà imprimés continuent de fonctionner** : aucune étiquette n'est à réimprimer.

Et le verrou de sécurité tient : une tablette rattachée à une cible **ne sort pas** de son écran de
saisie parce qu'on tape une autre adresse. Pour en sortir, il faut la détacher.

## Ce qui ne va pas encore, et qu'il faut savoir

**Quatre écrans de l'Atelier dépendent encore d'un tournoi** : Catégories, Blasons, Barème et Phases.
Ils vous renverront vers le Pilotage. Ce n'est pas un oubli : dans la version actuelle du logiciel,
ces réglages appartiennent à *un tournoi* et non *au club* — les en sortir est précisément le chantier
suivant. Seuls **Clubs** et **Gabarits** tiennent déjà toute la promesse de l'Atelier.

## Ce que la relecture a rattrapé

Cinq relecteurs indépendants ont examiné ce travail avant livraison. Trois défauts méritent d'être
connus, parce qu'ils disent quelque chose sur la façon dont ce logiciel est fabriqué :

- **« Détacher cette tablette » ne ramenait plus à l'écran d'accueil** mais au formulaire de
  rattachement — une régression née d'un enchaînement entre un changement d'adresse immédiat et une
  déconnexion, elle, différée. Invisible sans réseau lent ; visible au gymnase.
- **Trois documents promettaient qu'un lien se partage** alors que le tournoi ne voyageait pas encore
  dans l'adresse. La promesse a été rendue vraie plutôt que raturée.
- **Le serveur renvoyait une page d'application** au lieu d'une erreur pour certaines adresses mal
  formées, et pour des fichiers manquants comme l'icône du site.

---

*Détail technique : ADR-0058 (découpage en trois axes), ADR-0059 (une adresse par rôle, routeur
maison — remplace ADR-0032). Recette : `docs/fonctionnel/E14US003.md`. Réserves suivies :
DETTE-023, DETTE-024.*
