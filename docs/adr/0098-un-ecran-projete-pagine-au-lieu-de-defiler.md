# ADR-0098 — Un écran projeté **pagine**, il ne défile pas

- **Statut** : Accepté
- **Date** : 2026-08-26
- **US** : `E16US009`
- **Amende** : [ADR-0064](0064-ecran-de-salle-poste-type-et-pilotage-par-etat-lu.md) (écran de salle piloté par état lu)

> ⚠️ **Cet ADR ne figure pas à la liste nominative d'[ADR-0075 § « Portée de la règle »](0075-le-depart-est-la-portee-sportive.md#portée-de-la-règle--porté-dans-le-code-par--tranchée-le-08082026), et c'est volontaire.**
> Il est d'**IHM** : le moteur sportif ne lit rien de ce réglage, aucune portée ne change, aucune
> politique injectable n'est en jeu — un écran de salle *montre* un classement, il n'en produit
> aucun. Le critère de `CLAUDE.md` exclut nommément les ADR d'UI ; les précédents existent (`0086`,
> `0088`, `0095`, `0096`). Il porte en revanche sa section « Porté dans le code par », exigée de
> **tout ADR neuf** sans condition.
>
> *(Noté explicitement, sur le précédent d'ADR-0096 : un trou **non commenté** dans cette liste est
> précisément ce qui a produit quatre omissions consécutives.)*

## Contexte

Le questionnaire de maquettes du 04/08/2026 rend deux réponses sur l'écran de salle, et elles se
lisent mal ensemble.

- **P07** : *« ok pour les 3 premiers toujours visible, mais **défilement** de tous les autres
  archers dessous »*.
- **P06**, sur les listes de noms projetées : *« on peut dire que **20 s (réglable)** par écran de
  liste de noms est correct »*, avec *« oui pour le compteur de pages »*.

Le second a été livré en `E07US008` sous forme de **pagination** — des pages qui tournent toutes les
20 s, avec compteur et râteau de noms. Le premier ne l'a pas été : `E16US005` a livré la tête figée
sur les surfaces qu'on manipule (`teteFigee = 8`) mais l'a laissée **à zéro** sur l'écran de salle,
avec ce commentaire dans `VueClassement.tsx` :

> un cadre `overflow-y: auto` sur un vidéoprojecteur est un cadre que **personne ne peut faire
> défiler** : ni souris, ni doigt, « aucune interaction » (CA E07US004). Livrer la tête figée sans le
> défilement automatique aurait réduit un classement de 40 archers à 3 lignes — une **régression**.

La question laissée ouverte est donc : que veut dire « défilement » sur une surface **sans aucun
dispositif de pointage**, et faut-il deux mécanismes de lecture longue sur le même écran ?

## Décision

**Sur une surface projetée, « défiler » se réalise par une pagination temporelle — jamais par un
cadre à ascenseur.** Concrètement :

1. **La tête figée passe à 3** sur l'écran de salle (P07 au mot près), et le reste du classement
   **tourne page par page**, exactement comme les listes de noms d'affectations depuis `E07US008`.
2. **Le lien est mécanique** : la tête figée n'est portée à 3 que **si** un réglage de pages est
   fourni. Sans lui, elle retombe à zéro et l'écran rend le classement entier. On ne peut donc pas
   livrer par inadvertance « 3 lignes et rien d'autre », qui est la régression que `E16US005` avait
   refusée.
3. **Un seul mécanisme de lecture longue** sur cette surface : le module de pagination, ses
   fonctions pures et son en-tête (compteur + râteau) servent les deux vues. Le cadre
   `overflow-y: auto` reste, inchangé, sur les surfaces qu'on **manipule** — PC d'organisation et
   tablette —, où l'ascenseur est le bon geste.
4. **La cadence et la taille d'une page se règlent par écran**, servies par le serveur avec
   l'affichage (cf. § suivant). Le « (réglable) » de P06 est ainsi tenu, et `DETTE-039` refermée.
5. **Le réglage compte des NOMS, pas des lignes — chaque vue le convertit selon sa densité.**
   `noms_par_page` s'entend tel que la page d'affectations dispose ses noms : sur **trois colonnes**
   CSS (`.salle-pages__noms { columns: 3 22ch }`), où 40 noms tiennent sur ~14 lignes de haut. Le
   classement, lui, est un tableau **mono-colonne** : une ligne pleine largeur par archer. Une page
   de classement porte donc `ceil(noms_par_page / 3)` lignes.

   ⚠️ **Ce point est né d'un bloquant de revue, et il n'est pas cosmétique.** Appliquer la valeur
   brute à un tableau produisait, *au réglage livré par défaut*, une page trois fois plus haute que
   l'écran — et comme le §3 interdit précisément tout ascenseur ici, le bas de chaque page n'était
   pas « mal lu », il n'était **jamais montré**. La fenêtre avançant ensuite du même pas, les
   archers concernés ne seraient jamais sortis de la journée : le défaut exact que cette US existe
   pour corriger, réintroduit par son propre correctif. Deux axes l'ont calculé séparément depuis le
   CSS du dépôt.

   Le ratio n'est donc **pas un goût** : c'est le nombre de colonnes de la liste projetée, et il est
   nommé (`NOMS_PAR_LIGNE_PROJETEE`) à côté de la règle CSS qui le fonde. Un troisième champ
   persisté (`lignes_par_page_classement`) a été écarté : migration, DTO et champ de formulaire de
   plus pour un écran que personne n'a encore vu, alors qu'une conversion dérivée suffit et se
   prouve (règle 16).

## Pourquoi la pagination plutôt qu'un défilé continu

Une animation continue (`marquee`, `translateY` en boucle) satisferait aussi « aucune interaction ».
Quatre raisons l'écartent, dont la deuxième suffirait :

1. **Le commanditaire a déjà accepté la forme paginée** pour une liste projetée, dans le **même**
   questionnaire (P06), en demandant explicitement un compteur de pages. Ce n'est donc pas une
   réinterprétation de sa réponse : c'est la forme qu'il connaît sur cet écran.
2. **Une page paginée se prouve, un défilé ne se prouve pas.** `pageCourante(nbPages, secondes)` est
   une fonction pure, testée, et déjà éprouvée sur un défaut réel (une page qui ne sortait jamais de
   la journée). Une animation CSS ne se teste que par capture d'écran — or l'US précédente a
   justement livré deux bloquants sur une mise en page qu'aucun test ne pouvait prouver.
3. **Un texte qui bouge ne se lit pas à dix mètres.** Le repère de lecture, dans un gymnase, est
   « mon nom est-il sur cette page » — question à laquelle le râteau (`DUP → LEF`) répond, et qu'un
   défilé continu rend insoluble.
4. **Le temps d'affichage est déjà la brique du dispositif** (rotation des vues, expiration d'une
   prise de contrôle) : la page s'en déduit sans introduire une seconde notion de mouvement.

## Le réglage appartient à l'écran, pas à la vue

Les deux valeurs — noms par page, durée d'une page — dépendent de la **diagonale du projecteur, de
la distance de lecture et de la longueur des noms du club**. Ce sont trois propriétés du **lieu** :
identiques pour toutes les vues d'un même écran, différentes d'un écran à l'autre (le
vidéoprojecteur du fond de salle et l'écran d'accueil n'ont pas les mêmes). Les porter sur
`VueProgrammee` aurait obligé à les répéter à chaque étape du déroulé, avec la possibilité d'en
diverger sans qu'aucune règle ne le justifie.

⚠️ **Deux durées coexistent donc sur un écran, et les confondre est le piège de cette décision** :
`VueProgrammee.cadence_s` dit combien de temps l'écran reste sur *une vue* ; `cadence_page_s` dit à
quel rythme la liste tourne **à l'intérieur** de cette vue. Rien n'exige que l'une divise l'autre —
le cumul du temps d'affichage fait reprendre la séquence de pages où elle s'était arrêtée.

**Cohérent avec ADR-0064** : le réglage est un **état lu**, servi avec l'affichage que l'écran
répète, jamais poussé. Il accompagne aussi les prises de contrôle — une prise change *ce qu'on
montre*, jamais *comment une liste se lit de loin*.

## Conséquences

- Migration `0051` : deux colonnes nullables sur `poste`. Nul = « rien réglé », donc les valeurs par
  défaut du domaine, **identiques** à celles que le front tenait en dur : aucun écran déjà installé
  ne change de comportement au déploiement.
- `DETTE-039` est **refermée**. Sa seconde moitié — « valeur jamais mesurée sur un vidéoprojecteur
  réel » — ne se referme pas par du code : elle devient un **geste d'exploitation**, et l'écran
  d'admin le dit en toutes lettres sous les deux champs.
- Le module de pagination et l'en-tête de page **quittent `features/routage/`** pour `shared/ui/` :
  deux consommateurs réels dans deux features, donc une remontée sur preuve, pas une abstraction sur
  pari (même geste qu'`etatRencontre` en `E05US027`). Sans cela, `competition → routage` aurait
  ajouté une arête d'enchevêtrement que la carte du code mesure (`DETTE-083`, signal
  `features-enchevetrees`).
- ⚠️ **Le cumul du temps d'affichage devient indexé par vue.** Il tenait un compteur unique au
  module, sous le postulat « une seule surface projetée par onglet, donc pas de collision
  possible » — vrai tant qu'**une** vue paginait. Avec deux, les pages du classement avançaient
  pendant que l'écran montrait les affectations.
- **Angle mort assumé** : comme pour `E16US005`, l'écran n'a pas été vu sur un vidéoprojecteur. Les
  valeurs par défaut (40 noms, 20 s) restent un pari — c'est précisément ce que le réglage rend
  corrigeable sans toucher au code, mais **une relecture humaine en salle reste requise** pour
  savoir si 3 lignes de tête et une page de 40 tiennent réellement à dix mètres.

## Porté dans le code par

⚠️ Section écrite en **vérifiant dans le code du jour**, pas en déduisant de la décision.

| Décision | Module qui l'applique | Vérifié |
|---|---|---|
| §1 — tête figée à 3 sur l'écran projeté | `frontend/src/features/competition/teteFigee.ts` (`teteFigee`, fonction pure), **appelée depuis** `frontend/src/features/competition/VueClassement.tsx` — gardée par `frontend/src/features/competition/teteFigee.test.ts` | oui |
| §2 — le lien tête figée ↔ pagination est **mécanique** : sans réglage, la tête retombe à zéro | `frontend/src/features/competition/teteFigee.ts` (`teteFigee(filtrable, mode, pagination)` — le cas `!filtrable && pagination === undefined` rend `0`) — gardé **des deux côtés** : `frontend/src/features/competition/teteFigee.test.ts` pour la règle, `frontend/src/features/competition/VueClassement.test.tsx` pour le fait que la valeur atteigne réellement la table | oui — c'est le garde-fou contre la régression « 3 lignes et rien d'autre » |
| §1 et §3 — le reste tourne page par page, sans aucune propriété de défilement | `frontend/src/features/competition/TableClassement.tsx` (`ResteProjete`, `NOMS_PAR_LIGNE_PROJETEE`) | oui |
| §3 — la feuille de style ne réintroduit aucun ascenseur sur la surface projetée | `frontend/src/app/App.css` (`.classement__pages`, volontairement sans `overflow-y`) | oui — vérifié à la lecture de la règle, non contrôlable symbole par symbole |
| §3 — un seul mécanisme, partagé par les deux vues | `frontend/src/shared/ui/pagination.ts` (`nombreDePages`, `pageCourante`, `trancheDePage`, `rateauDePage`) · `frontend/src/shared/ui/EnteteDePage.tsx`, consommés par `TableClassement.tsx` **et** `features/routage/VueAffectations.tsx` | oui — deux consommateurs réels |
| §3 — le cadre à ascenseur subsiste sur les surfaces manipulables | `frontend/src/features/competition/TableClassement.tsx` (branche `pagination === undefined`) · `.classement__defilement` | oui — inchangé par cette US |
| §4 — le réglage est **par écran**, persisté | `backend/domain/ecran.py` (`ReglagePages`, bornes et défaut) · `backend/domain/poste.py` (`pages`, `avec_pages`, `pages_effectives`) · `backend/migrations/versions/0051_reglage_pages_ecran.py` | oui |
| §4 — servi comme **état lu**, avec l'affichage, y compris sous contrôle | `backend/application/ecrans.py` (`AffichageEcran.pages`, renseigné dans les deux branches) · `backend/api/v1/ecrans.py` (`AffichageReponse.pages`) — gardé par `backend/tests/test_ecrans_api.py` (`test_une_prise_de_controle_ne_change_pas_le_reglage_de_pages`) | oui |
| §4 — geste d'admin **distinct** du déroulé | `backend/api/v1/ecrans.py` (`PUT …/ecrans/{poste_id}/pages`) · `backend/application/postes.py` (`regler_pages_ecran`) · `frontend/src/features/ecrans/Ecrans.tsx` (`ReglagePagesProjetees`) — gardé par `backend/tests/test_ecrans_api.py` (`test_regler_les_pages_ne_touche_pas_au_deroule`) | oui |
| Le défaut front et le défaut serveur sont **épinglés chacun de son côté** | `frontend/src/shared/ui/pagination.test.ts` (« les défauts du module et ceux du serveur ») · `backend/tests/test_domain_ecran.py` (`test_le_reglage_de_pages_par_defaut_est_utilisable_sans_rien_regler`) | oui — mais ⚠️ **ce sont deux littéraux indépendants qui s'entre-citent, pas une contrainte de compilation** : changer le défaut serveur *et* son propre test laisse le test front vert. Le garde-fou est de **lecture** ; le dire est le prix de la crédibilité de cette ligne (correctif de revue) |
| Le cumul de temps d'affichage est **indexé par vue** | `frontend/src/shared/ui/pagination.ts` (`useSecondesDAffichage(cle: CleDePage)`, `Map<string, number>`) — clés `'classement'` et `'affectations'`, **énumérées par le type** `CleDePage` pour qu'une 3ᵉ vue ne puisse pas réutiliser une clé prise par copier-coller | oui |
| §5 — le réglage compte des **noms de liste**, converti en **lignes de tableau** pour le classement | `frontend/src/features/competition/TableClassement.tsx` (`NOMS_PAR_LIGNE_PROJETEE`, `parPage`) — gardé par `frontend/src/features/competition/TableClassement.test.tsx` (« convertit les NOMS réglés en LIGNES de tableau ») | oui |
| Le câblage `affichage.pages` → vue projetée est **épinglé à chaque étage** | `frontend/src/features/salle/EcranSalle.test.tsx` (le témoin de `VueClassement` recopie sa prop) · `frontend/src/features/competition/VueClassement.test.tsx` | oui — les deux vérifiés **en réintroduisant le défaut**, pas seulement au vert |
| Les bornes du formulaire d'admin et celles du domaine sont épinglées | `frontend/src/features/ecrans/api.test.ts` · `backend/tests/test_domain_ecran.py` (`test_les_bornes_du_reglage_de_pages_sont_inclusives`) | oui — même réserve d'honnêteté que pour les défauts : garde-fou de lecture, pas de compilation |
