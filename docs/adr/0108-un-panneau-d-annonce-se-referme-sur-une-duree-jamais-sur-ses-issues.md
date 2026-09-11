# ADR-0108 — Un panneau d'annonce se referme sur une durée, jamais sur ses issues

- **Statut** : Accepté
- **Date** : 2026-09-10
- **Décideurs** : Organisateur / Architecte
- **Portée** : E16US018 (le panneau de routage rend la tablette tout seul)
- **S'appuie sur** : [ADR-0074](0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md)
  (les maquettes font foi — la planche `S06` porte désormais le signal, et sa question « combien de
  temps » y passe à *tranchée*)

## Contexte

Le panneau « Où tire-t-on ensuite ? » (`E04US018`, canal n°1 de `D-09`) s'ouvre **tout seul** quand
une cible a fini de tirer ou qu'un duel vient d'être validé. Il ne se refermait que si **quelqu'un**
appuyait sur « Retour ». Le jour J, personne n'appuie : l'archer lit sa destination et s'en va ; la
tablette reste sur l'écran d'annonce, inutilisable pour le tireur suivant tant qu'un organisateur ne
passe pas.

Le questionnaire `S06` demandait *« 3 mn si un autre tour suit »*, et retenait la variante **A**
(retour automatique **non compté**) contre la **C** (*« retour automatique compté »*).

**Le fait qui commande tout le reste** : le panneau porte **plusieurs archers**. `SaisieDuels.tsx`
le monte sur les **deux duellistes** du duel qu'on vient de valider — donc il y a **une ligne
terminale à chaque duel, à tous les tours** — et `Saisie.tsx` sur les quatre archers d'une cible,
avec jusqu'à quatre issues différentes.

## Décision

**1. Une durée unique — 3 minutes — aveugle aux issues des lignes.** Le minuteur ne lit aucune
`IssueRoutage`. La condition « si un autre tour suit » du questionnaire est **retirée** : trois
minutes suffisent à lire « 3ᵉ du tableau », et le cas terminal est couvert par la durée elle-même.

**2. Toute porte automatique porte une poignée.** Un panneau refermé — au bouton **ou** au délai —
se rouvre à la main, des **deux** côtés. La qualification l'avait depuis `E04US018` ; les duels
l'ont gagnée ici. En duels la poignée **nomme son duel** (« — duel n°3 ») : elle rouvre un
instantané qui peut dater d'une heure, là où la qualification suit la cible affichée.

**3. Un écriteau ne se referme pas.** Un avis **global** — « tir suspendu : restez à disposition »,
« phase finale non configurée », « tableau non constitué » — vaut **tant que la situation dure** ; une
pause tient 15 à 20 minutes. C'est le **serveur** qui le déclare (`Routage.avis_permanent`, posé par
l'unique constructeur `_tous_indisponibles`), jamais le front qui le devine : « toutes les lignes sont
en attente » a exactement la même forme qu'une ronde suisse où les quatre archers d'une cible portent
un bye.

**4. Le signal est discret et non chiffré** — une barre de progression et la mention « Retour
automatique ». Pas de secondes, **et pas de pourcentage** : la jauge est en `role="img"` et non
`progressbar`, qui publierait `aria-valuenow` aux technologies d'assistance.

**5. Le décompte est du temps d'horloge, veille comprise, ancré au MONTAGE du panneau** — et c'est
précisément pourquoi **les deux appelants rendent le panneau avant toute sortie `isPending` /
`isError`**. Placé après, un refetch en échec (`retry: false`, et `useRealtime` invalide sans clé) le
démontait puis le remontait avec trois minutes neuves : sur un wifi de salle, il pouvait ne **jamais**
se refermer. ⚠️ **L'ordre des branches EST la décision** ; le déplacer réintroduit le défaut sans
qu'un test rougisse (un test de rendu monte le composant une fois).

*(Remonter l'instant d'ouverture chez l'appelant — la correction proposée en revue — se heurte à deux
règles du dépôt : `react-hooks/purity` interdit `Date.now()` pendant le rendu, et
`react-hooks/set-state-in-effect` interdit le repli en effet. L'ordre des branches obtient le même
résultat sans les contourner.)*

## Ce qui a été écarté, et pourquoi

- **« Le panneau reste dès qu'une ligne est terminale. »** Écarté **sur mesure**, et c'est la
  décision centrale : en élimination directe il y a un battu à **chaque** duel, donc cette règle
  n'aurait **jamais** refermé l'écran de duels. L'US aurait été livrée sans effet, **tests verts**.
  ⚠️ `presentation.ts` exporte `encoreEnLice` — un `Record<IssueRoutage, boolean>` exhaustif, dans le
  **même fichier**. S'en servir pour « durcir » la fermeture rétablirait exactement cette règle, sans
  qu'aucun test ne rougisse.
- **La fermeture ligne à ligne** (chaque ligne à suite s'efface, les terminales restent) : même
  conséquence, plus un redécoupage du panneau.
- **Le compte à rebours chiffré** (« Retour dans 2:41 ») : signature de la variante **C** du
  questionnaire `S06`, écartée au profit de la **A**.
- **Ne compter que le temps visible** (suspendre le décompte écran éteint) : écarté par le
  commanditaire le 10/09/2026 au profit d'un seul concept. ⚠️ **Coût assumé et nommé** : sur une
  tablette BYOD qui se met en veille, le panneau peut avoir disparu avant que l'archer revienne. La
  poignée le rouvre — encore faut-il savoir qu'il y avait quelque chose à lire.

## Porté dans le code par

| Module | Ce qu'il applique |
|---|---|
| `frontend/src/features/routage/presentation.ts` | `FERMETURE_MS`, `avanceeFermeture`, `doitSeRefermer` — décisions 1 et 5. **Ne lit aucune issue** : c'est là que la décision 1 se vérifie, et là que `encoreEnLice` ne doit pas entrer |
| `frontend/src/features/routage/PanneauRoutage.tsx` | Ancre de montage et branchement du battement (`useMaintenant`, décision 5), garde de tir unique, `JaugeRetour` (décision 4), garde `ecriteau` (décision 3) |
| `frontend/src/features/saisie/Saisie.tsx` | Poignée de qualification, via `panneauOuvert` / `apresRetour` (décision 2) |
| `frontend/src/features/saisie-duels/SaisieDuels.tsx` | Poignée **nommée** côté duels (décision 2) ; **branche du panneau placée avant `isPending` / `isError`** (décision 5) |
| `backend/application/routage.py` | `Routage.avis_permanent`, posé par `_tous_indisponibles` — **autorité serveur** de la décision 3 |
| `backend/api/v1/routage.py` | `RoutageReponse.avis_permanent` — la décision 3 traverse la frontière API |
| `maquettes/s06-routage.html` | La planche porte le signal (décision 4) et la question « combien de temps » y est marquée tranchée |

**Épinglé par** : `PanneauRoutage.test.tsx` (fermeture malgré une ligne terminale ; signal sans
chiffre, assertion portée sur le **bloc entier** ; écriteau qui ne part pas),
`SaisieDuels.routage.test.tsx` (poignée, et « **dernier** duel validé »),
`presentation.test.ts` (bornes du calcul),
`backend/tests/test_service_routage.py` (`avis_permanent` posé sur un avis global, absent d'une annonce).

## Ce que cet ADR n'est pas

⚠️ **Il n'entre pas à la liste nominative d'[ADR-0075 § « Portée de la règle »](0075-le-depart-est-la-portee-sportive.md).**
C'est une décision d'**IHM** : le moteur sportif ne lit rien de ce minuteur, aucune portée ne change,
aucune politique injectable au sens de la règle 2 n'est en jeu. Le dire explicitement évite qu'une
revue future le compte comme une omission — c'est le geste qu'`ADR-0098` a formalisé.

## Conséquences

- Une tablette qui a fini se remet d'aplomb seule, sur les deux surfaces de saisie.
- Le raisonnement « pourquoi pas d'agrégation » a un **domicile** : il était recopié à onze endroits
  sans qu'aucun fasse foi. Les commentaires du code y renvoient désormais en une ligne (règle 13c).
- Le DTO de routage gagne un champ **additif** (`avis_permanent`) : pas de migration, pas de route
  neuve, mais `test_routage_api.py` épinglait la forme complète de la réponse et a été mis à jour.
- ⚠️ **Ce qui cassera plus tard, si personne ne lit ceci** : quelqu'un « durcira » la fermeture en
  lisant `encoreEnLice`, de bonne foi, et l'écran de duels cessera de se refermer — sans un seul test
  rouge. C'est la raison d'être de cet ADR bien plus que la durée de 3 minutes.
