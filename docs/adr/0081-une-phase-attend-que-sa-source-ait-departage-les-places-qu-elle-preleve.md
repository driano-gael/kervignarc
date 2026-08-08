# ADR-0081 — une phase attend que sa source ait départagé les places qu'elle prélève

- **Statut** : accepté
- **Date** : 2026-08-08
- **US** : E05US024
- **Complète** : [ADR-0080](0080-un-prelevement-lit-le-classement-de-sa-phase-source.md) (dont il
  corrige une conséquence affichée), [ADR-0065](0065-rang-acquis-lu-sur-la-plage-et-issue-repechee.md)
  (Règle R), [ADR-0067](0067-palmares-agregation-des-rangs-de-phases.md)

## Contexte

ADR-0080 a fait lire à un prélèvement le classement de **sa** phase source, y compris quand cette
source est un tableau. Pour cela, `domain/classement_de_tableau.py` lit un `Tableau` comme un
classement, en s'appuyant sur `Tableau.positions_acquises()`.

Or un tableau ne décerne pas des rangs, il décerne des **fourchettes**, et
`PositionAcquise.en_lice` distingue deux natures que ADR-0065 et ADR-0067 avaient déjà séparées :

- une fourchette **fermée** (`en_lice=False`) — les quatre battus des quarts sortent tous sur
  `[5..8]`, plus aucun match ne les départagera. Ce sont des *ex æquo*, et la politique
  `aggregation` a le droit de les ordonner (Règle R) ;
- une fourchette **indécise** (`en_lice=True`) — les deux finalistes sont `[1..2]` tous les deux,
  et c'est la finale qui tranchera.

ADR-0080 §2 traitait les deux de la même façon, avec un argument juste mais **incomplet** : « une
phase aval qui prélève « les rangs 1 à 2 » les prend **tous les deux**, ce qui est la bonne
réponse : elle veut les deux finalistes ». Vrai quand la fenêtre demandée **coïncide** avec le bloc
indécis. Faux dès qu'elle le **coupe**.

Et le cas où elle le coupe n'est pas exotique : c'est le cas nominal. **Avant le premier duel d'un
tableau de 8, les huit archers ont un quart en cours, et un quart décide les rangs 1 à 8** — ils
partagent donc tous la fourchette `[1..8]`, un unique paquet, que `aggregation` ordonne sur le rang
de qualification. Le classement du tableau *est* alors l'ordre de la qualification.

Conséquence mesurée en revue adversariale : une consolante déclarant « les rangs 5 à 8 de la phase
2 » — dans l'intention de l'organisateur, **les quatre battus des quarts** — recevait les **quatre
derniers qualifiés**. Une fois les quarts tirés, la population basculait entièrement.

Trois surfaces consommaient ce classement sans garde : l'affichage **public** des tableaux (projeté
en salle), le **plan de cibles** (persisté, imprimé et affiché), et la **saisie** — où un score entré
avant la bascule était ensuite écarté en silence par `_rejouer`, faute de duellistes correspondants.

**Ce que le défaut avait de particulier, et qui a motivé cet ADR plutôt qu'un correctif discret** :
avant E05US024, la même consolante recevait *tous* les archers en lice — 8 pour 4 places, absurde et
donc **immédiatement visible**. Après, elle recevait le bon nombre d'archers avec des noms
crédibles. L'US qui se donnait pour mission de fermer « un tableau bien formé, plausible, et faux »
avait, sur ce chemin, **déplacé le défaut en le rendant moins détectable**.

## Décision

**Une fenêtre de prélèvement est honorée si et seulement si elle ne *coupe* aucun bloc de rangs
encore indécis.** « Couper », c'est chevaucher **sans contenir**.

1. `domain/classement_de_tableau.py` rend un `ClassementSource` — le classement **plus** la liste
   des `plages_indecises`, blocs de rangs portés par des archers encore en lice. Les rangs
   provisoires continuent d'être produits : le palmarès en a besoin pour situer tout le monde à
   chaque instant. Ce qui change, c'est qu'ils sont désormais **étiquetés**.
2. `application/prelevement.py:preleves` lève `PrelevementEnAttente` quand la fenêtre coupe un de
   ces blocs. Le raisonnement d'ADR-0080 §2 est **préservé, pas jeté** : une fenêtre qui contient
   entièrement le bloc reste honorée, et les deux finalistes sont toujours pris ensemble.
3. Le refus est un **état affiché**, pas une panne. `PrelevementEnAttente` est un
   `ApplicationError` (→ 409), et il porte l'`ordre` de la phase attendue :
   - `ServiceTableauxPublics` rend un `TableauPublic` **sans arbre** et avec `attente` renseigné,
     au lieu de retirer la phase de la liste ;
   - `api/v1/tableaux.py` expose `en_attente_de` ;
   - le front affiche « les places disputées ici ne sont pas encore connues : le tableau *n* doit
     d'abord être joué » ;
   - `ServicePlacementDuels` rend un **plan vide** — le chemin gracieux déjà prévu pour « pas assez
     de participants » — plutôt qu'un écran en erreur, et la saisie refuse (409) ;
   - `ServicePalmares` écarte la phase — elle n'a effectivement rien à publier.

4. **Le refus rejoint les points de tolérance existants.** Le dépôt a un patron établi —
   `except EffectifTableauInvalide` = « trop tôt, on saute cette phase ». `PrelevementEnAttente` est
   sémantiquement le **même** cas, et l'introduire sans l'y ajouter faisait échouer en bloc six
   surfaces qui fonctionnaient la veille : simulation, cockpit de pilotage (×3), routage, feu vert.
   Elles le traitent donc comme leur voisin. *(Relevé par trois axes en 2ᵉ passe : le refus typé
   avait été poussé sans en suivre la propagation — la régression que le correctif de `preleves`
   avait précisément fermée un étage plus bas.)*

## Conséquences

**Positives.** Le défaut n'est plus déplacé mais fermé : sur ce chemin, le moteur honore, refuse
**en le disant**, ou reste inerte — il ne fabrique plus de population. Le spectateur lit ce qui
manque au lieu de voir un bracket disparaître ou, pire, afficher les mauvais noms. Et la
distinction `en_lice` d'ADR-0065, jusqu'ici consommée par le seul palmarès, devient une information
de premier ordre pour le moteur de composition.

**Négatives, et assumées.** L'onglet public montre une phase « en attente » pendant toute la matinée
d'un tournoi à consolante — c'est la vérité, mais c'est une case vide de plus à l'écran. Le refus
est calculé à **chaque** lecture (il dépend de l'état des duels), donc il s'ajoute au régime de
`DETTE-031` sans le changer.

**Ce que cet ADR ne tranche pas.** Le sort d'un archer déclaré **forfait dans le tableau source**
(walkover, ADR-0050) : il garde une position acquise, ressort `EN_LICE` du classement dérivé, et
reste donc prélevable en aval. C'est une **règle de compétition** à trancher avec le club, inscrite
au registre en `DETTE-051` plutôt que devinée ici — même parti qu'ADR-0065 §3 pour
`par_issue_de_tour`.

## Porté dans le code par

| Module | Ce qu'il applique |
|---|---|
| `backend/domain/classement_de_tableau.py` | `ClassementSource.plages_indecises` et `coupe()` — la règle « chevaucher sans contenir » ; `rang_premier` pour le cumul de tranche |
| `backend/application/prelevement.py` | `preleves` lève `PrelevementEnAttente` ; `tranche` cumule le décalage le long de la chaîne |
| `backend/application/erreurs/moteur.py` | `PrelevementEnAttente` (409) et son `ordre_source` |
| `backend/application/saisie_duels.py` | `_classement_de_l_ordre` construit le `ClassementSource` et calcule le `rang_premier` de chaque tableau |
| `backend/application/tableaux_publics.py` | `pour_depart` distingue les trois issues : arbre, attente, échec avalé |
| `backend/application/palmares.py` | écarte une phase en attente (elle n'a rien à publier), **pas** un déroulé cyclique |
| `backend/api/v1/tableaux.py` | `TableauPublicReponse.en_attente_de` et la branche « pas d'arbre » |
| `backend/application/placement_duels.py` | `_charger` retombe sur le plan vide au lieu de lever |
| `backend/application/simulation.py`, `pilotage_simulation.py`, `routage.py`, `pilotage_tour.py` | traitent l'attente comme « phase pas encore jouable » |
| `backend/application/erreurs/moteur.py` | `DerouleCyclique` (409), introduit par le même lot pour que le refus de cycle cesse d'être un 404 avalé par le palmarès |
| `frontend/src/features/tableaux/VueTableaux.tsx` | le rendu « en attente du tableau *n* » |

## Tests qui le tiennent

- `backend/tests/test_prelevement_phase_source.py` — `test_une_fenetre_qui_coupe_un_bloc_indecis_est_refusee`,
  `test_la_meme_fenetre_se_resout_une_fois_les_quarts_tires`,
  `test_une_fenetre_qui_contient_un_bloc_indecis_reste_honoree` (le verrou d'ADR-0080 §2),
  `test_le_rang_premier_du_tableau_amont_est_reellement_cable`,
  `test_l_ecran_public_annonce_la_phase_en_attente_au_lieu_de_la_retirer`,
  `test_le_dto_public_expose_l_attente_et_ne_ment_pas_sur_les_dimensions`
- `frontend/src/features/tableaux/VueTableaux.test.tsx` — le rendu et l'absence d'arbre

⚠️ **Les trois derniers tests backend ont été ajoutés en 2ᵉ passe, sur relevé adversarial**, et une
version antérieure de cette section citait à leur place `test_tableaux_api.py` — qui ne fait que
lister le **nom** du champ dans une liste blanche. La revue l'a prouvé par mutation : annuler le
cumul de `rang_premier`, puis le `except PrelevementEnAttente` de `ServiceTableauxPublics`, laissait
**la suite complète verte** dans les deux cas. Les tests visaient la fonction pure et laissaient le
**câblage** — l'endroit précis où E05US020 avait déjà cassé — sans oracle. Les deux mutations
échouent désormais, vérifié.
