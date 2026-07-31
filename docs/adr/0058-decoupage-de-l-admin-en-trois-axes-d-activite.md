# ADR-0058 — Découpage de l'appli admin en trois axes d'activité, plus par temps du tournoi

- **Statut** : Accepté
- **Date** : 2026-07-30
- **Décideurs** : Organisateur / Architecte
- **Portée** : E14US003 (accueil admin à trois axes + répartition des 25 destinations livrées)
- **Lie** : `D-19` / `D-20` du [CDC UX §7.1](../../cahier-des-charges-ux.md) (l'ossature que cet ADR
  remplace et l'accueil contextualisé qu'il conserve), [ADR-0042](0042-modele-d-entree-choix-de-role-explicite.md)
  (les quatre portes par rôle — niveau au-dessus, inchangé), [ADR-0026](0026-cycle-de-vie-du-tournoi-sept-statuts.md)
  (les 7 statuts qui contextualisent l'accueil du pilotage), [DETTE-023](../dette.md#dette-023--latelier-affiche-des-briques-encore-scopées-par-tournoi)
  (les briques que l'atelier annonce mais ne libère pas encore)

## Contexte et problème

E00US015 avait livré une **sidebar groupée par temps du tournoi** (Préparation / Jour J), conforme au
CDC UX §7.1 : « les groupes suivent la vie du tournoi ; le groupe du moment est ouvert, les autres
repliés ». Chaque US front livrée ajoutait sa destination — le fichier le disait en commentaire :
« chaque destination = une **feature autonome** montée par **une seule entrée** ».

Au bout de 24 US front, l'ossature comptait **25 destinations : 19 sous « Préparation », 6 sous
« Jour J »**. Le commanditaire l'a refusée après l'avoir utilisée :

> « la sidebar fait vivre le tournoi sous tous ses états en même temps, je trouve cela confus. Un
> tournoi en préparation est le moment où il est créé, il mérite son propre cycle de vie, on ne doit
> pas être pollué par jour J et après. »

Et, plus fondamentalement, sur ce que l'interface lui renvoyait du produit :

> « bien que le backend soit solide, le pilotage de l'interface ne me va pas du tout, je n'arrive pas
> à sentir si le code fait ce que je veux et surtout ce dont j'ai besoin pour mon client. »

**Le diagnostic.** L'interface était devenue **l'inventaire du backlog, pas la carte du métier**. Son
ordre était celui de l'historique de livraison, pas celui du travail de l'organisateur.

**Et le rangement temporel avait un défaut propre, mesurable** : il **coupe en morceaux une activité
qui dure**. La gestion administrative commence des semaines avant le tournoi, encaisse pendant,
exporte après — rangée par temps, elle se disperse. C'est exactement ce qui s'était produit :
`Inscriptions`, `Doublons` et `Paiements` sous *Préparation*, `Exports` et `Archive` sous *Jour J*.
Personne n'avait pris cette décision ; elle découlait de l'ordre d'arrivée des US.

Symétriquement, les **briques du club** (catégories, blasons, gabarits, barèmes, formats) ne
dépendent d'aucun tournoi : elles vivent d'année en année. Les ranger sous un sélecteur de tournoi
— que le §7.1 posait « au-dessus de tout » — est un contresens, que le commanditaire avait déjà
signalé le 29/07 (« les briques sont le patrimoine du club, pas d'un tournoi »).

## Décision

**1. Le critère de découpage n'est plus *quand*, c'est *quelle activité*.** Trois axes :

| Axe | Activité | Durée de vie | Utilisateur · tempo | Travaille sur un tournoi ? |
|---|---|---|---|---|
| **Atelier** | Fabriquer : briques du club, salles types, formats de déroulé, modèles réutilisables, banc d'essai | Pluriannuelle | Le concepteur du format · posé, hors urgence | **Non** |
| **Pilotage** | Le temps réel : lancer, superviser, valider, faire tourner la journée | La journée | La table d'organisation · la seconde, sous pression | Oui |
| **Gestion** | L'administratif : inscriptions, paiements, exports, archives | Semaines avant → après | Secrétaire, trésorier · le jour, la semaine | Oui |

Ce qui justifie la séparation n'est pas esthétique : les trois axes n'ont **ni le même utilisateur, ni
le même tempo, ni la même durée de vie**. Deux d'entre eux peuvent être ouverts le même jour sur le
même tournoi sans se gêner (`P-3` : le retardataire de 8 h 50 s'inscrit et paie pendant qu'on tire).

**2. Un accueil admin choisit l'axe, et un seul axe est ouvert à la fois.** Les en-têtes de groupe
repliables disparaissent : la sidebar d'un axe est une **liste plate**. `P-3` n'est pas abandonné — il
est tenu autrement : l'accueil est à **un clic**, rien n'est interdit. Ce qui disparaît, c'est d'avoir
en permanence sous les yeux ce qu'on ne fera pas aujourd'hui.

**3. Le sélecteur de tournoi ne coiffe plus tout — il coiffe les axes qui en ont besoin.** L'atelier
n'en affiche pas, ni la recherche d'archer (scopée au tournoi). L'exception « ici le sélecteur ne
s'applique pas » **cesse d'être une exception** : elle devient une propriété de l'axe.

**4. L'accueil porte l'assemblage.** La liste des tournois, leur création et leur cycle de vie ne
relèvent d'aucun axe : ce geste **crée l'objet** sur lequel deux d'entre eux travaillent. L'ancienne
destination « Tournoi » quitte donc le système de destinations pour l'accueil — en gardant son aide
contextuelle (E14US002).

**5. Le tableau de bord et le cockpit de simulation cessent d'être des entrées de menu.** L'accueil
contextualisé (E14US001, `D-20`) devient la **destination d'ouverture du pilotage** ; le cockpit de
simulation (E15US003) est l'entrée du **banc d'essai** de l'atelier. Tous deux étaient rangés parmi
dix-neuf destinations, entre « Blasons » et « Postes de cible » — alors que ce sont précisément les
deux écrans qui **montrent la valeur du produit**.

## Alternatives écartées

- **Renommer les groupes sans changer le critère** (« espaces » Préparation / Déroulé / Résultats,
  proposé le 29/07). Écarté : le problème n'était pas le vocabulaire mais le **critère** — un
  rangement temporel disperse l'axe administratif quel que soit le nom des groupes.
- **Trois URL de premier niveau** (`/atelier`, `/pilotage`, `/gestion`), à côté de `/cible`,
  `/scoreur`, `/public`. Séduisant parce que l'absence de tournoi serait portée par l'adresse.
  **Écarté par le commanditaire** : les trois axes sont **le travail de l'administrateur**, ils vivent
  donc derrière la porte admin, et c'est un accueil admin qui choisit — cohérent avec sa demande du
  29/07 (« cela doit plutôt passer par un accueil, qui choisit le cycle »).
- **Trois applications distinctes, avec des droits par axe** (trésorier / concepteur / table
  d'organisation). Écarté **pour l'instant** : toutes les écritures sont derrière un unique
  `exiger_admin` (E10US001), un modèle de droits par axe est une US à part entière. Le découpage
  retenu ne ferme pas cette porte.

## Conséquences

- **+** L'ordre de l'interface cesse d'être celui du backlog. Une US front nouvelle s'ajoute dans
  **son** axe, sans allonger une liste unique de dix-neuf entrées.
- **+** L'atelier existe comme lieu, ce qui donne une place aux 17 US non livrées qui en relèvent
  (EPIC-01, 03, 05, 06, 13) et qui étaient jusqu'ici sans domicile.
- **+** Aucun changement de domaine, d'API ni de base : la répartition est **front seul**. Les 25
  écrans livrés fonctionnent à l'identique — seule leur place change.
- **−** **L'atelier promet plus qu'il ne tient**, tant que les briques ne sont pas libérées :
  Catégories, Blasons, Barème et Phases portent encore un `tournoi_id` et exigent donc un tournoi que
  l'axe ne propose pas de choisir. Inscrit en **DETTE-023** (majeur), résorption cadrée.
- **−** Un niveau de navigation de plus pour atteindre un écran d'un autre axe (accueil, puis axe).
  Assumé : c'est le prix de ne pas être pollué, et c'est ce que le commanditaire a demandé.
- **⚠️** `D-19` du CDC UX est **révisée**, pas complétée. Toute maquette ou story qui décrit une
  « sidebar groupée par temps » est désormais fausse — les planches A02, A03, A04, A06 et A09 du
  dossier `maquettes/` sont à réaligner (A02 l'est, dans la même US).
