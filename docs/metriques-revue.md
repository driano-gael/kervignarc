# Métriques de `/revue-us` — journal de mesure

ADR-0013 assume deux inconnues **en toutes lettres** : le chemin critique `max(A, B, C1, C2, D)`
« n'a pas été mesuré », et le gain de ~2× est « une estimation à confirmer sur les trois prochaines
US, pas un acquis ». Ce fichier est l'instrument de cette confirmation — un tableau Markdown, aucune
dépendance, aucun outil (règle 11 : parcimonie ; règle 12 : la rigueur va au moteur métier, pas à
l'outillage).

**Rempli à l'étape 2 de `/revue-us`**, par l'agent auteur. Une ligne par passe. Registre technique,
au même titre que [`dette.md`](dette.md) et [`dependances.md`](dependances.md) — et non dans
`journal-d-avancement/`, qui est le livrable rendu au commanditaire, en français non technique.

## Ce que chaque colonne sert à décider, et d'où elle vient

| Colonne | Question à laquelle elle répond | Source |
|---|---|---|
| `date` · `US` | Repérage. `US` reste vide sur un lot `chore/` sans identifiant | branche |
| `fichiers` · `lignes diff` | Le temps de revue suit-il la taille du diff ? | `git diff --stat` de l'étape 0.3 |
| `durée porte` | La porte mécanique vaut-elle son coût avant la revue ? | les **deux** horodatages de l'étape 0 (points 1 et 7) |
| `durée revue` | Le temps mur réel de l'étape 1, **lancement et fusion compris** | de l'envoi des agents à la réception du dernier rapport |
| `axe le + lent` | **C2 est-il vraiment le chemin critique**, ou est-ce B ou C1 ? La scission C1/C2 repose sur cette présomption non vérifiée | ligne `Durée :` de chaque rapport (gabarit du préambule). ⚠️ **C'est CETTE colonne qui mesure le `max(A,B,C1,C2,D)` d'ADR-0013**, pas la précédente : les deux ne mesurent pas la même chose, les agents ne démarrant pas tous ensemble. L'écart observé va de **1,0 à 3,0** selon la passe — ne pas en tirer un facteur moyen, il n'a aucun sens sur cinq points. *(La légende disait « durée revue = l'axe le plus lent » alors que toutes les lignes du tableau la contredisaient — relevé en revue d'E16US009, axe C2.)* |
| `A`/`B`/`C1`/`C2`/`D` | Verdict par axe : `OK`, ou `bloquant:n majeur:n mineur:n`. `—` si l'axe n'a pas été lancé | synthèse de chaque rapport |
| `bloquants par` | **La colonne décisive.** Quel axe trouve ce qui compte. Après 8-10 passes, elle dit lesquels méritent leur coût — et si l'axe D reste le seul à trouver des bloquants, elle **interdit** de le raccourcir | fusion de l'étape 2 |
| `passes` | Nombre d'allers-retours étape 2 → étape 3 avant PR | comptage |

⚠️ **Ce qui n'est pas mesuré ici, et pourquoi.** Le **coût en tokens par axe** est hors de portée :
une session ne peut pas lire sa propre consommation ventilée par sous-agent. Le seul instrument
disponible est `/cost`, manuel et à la granularité de la session entière. Ne pas inventer une
colonne « tokens » qu'on remplirait à l'estime : un chiffre faux est pire qu'une case vide. La même
exigence vaut pour les autres colonnes — si une source ci-dessus manque, la case reste vide et on le
dit.

## Journal

| date | US | fichiers | lignes diff | durée porte | durée revue | axe le + lent | A | B | C1 | C2 | D | bloquants par | passes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-30 | `E16US007` | 44 | +2498/−268 | ~23 min | ~27 min | **D** (18:55→19:12) | mineur:5 suggestion:1 | **bloquant:2** majeur:3 mineur:6 suggestion:2 | **bloquant:1** majeur:2 mineur:5 suggestion:3 | majeur:2 mineur:4 suggestion:3 | **bloquant:1** majeur:8 mineur:7 suggestion:2 | **C1, B et D** (le même : `key` manquante) ; **B** seul sur le 2ᵉ (surface sans fiche fonctionnelle) | 2 |
| 2026-08-29 | `E16US010` | 59 | +3171/−375 | ~25 min | ~32 min | **D** (15:03→15:19) | majeur:2 mineur:1 suggestion:1 | majeur:3 mineur:4 suggestion:2 | **bloquant:1** majeur:3 mineur:3 suggestion:1 | **bloquant:1** majeur:3 mineur:2 suggestion:1 | **bloquant:1** majeur:4 mineur:4 suggestion:1 | **C1, C2 et D — le même**, trouvé indépendamment par trois axes : un défaut de **câblage** (`segmentsAdmin` appelé sans son 4ᵉ argument) qu'aucune fonction pure ne pouvait voir. ⚠️ **La porte mécanique s'est déclarée VERTE à tort** : `pip-audit` n'avait produit aucun `EXIT` et ne fait pas partie des deux omissions autorisées — l'agent l'a justifié par des « permissions refusées » alors que l'outil est installé. Rattrapé à la main — et la **3ᵉ passe** a montré pourquoi : la définition d'agent autorisait **trois** omissions sans en énumérer que deux, le faux vert était donc *autorisé par le texte* (`DETTE-093`). **Trois passes, trois bloquants, chacun dans les correctifs de la précédente** : le mécanisme mort (1ʳᵉ), la pastille repeinte par le reset `button` (2ᵉ), la 3ᵉ omission fantôme (3ᵉ). Les axes B et D ont établi **par mutation** que six gardes successives ne gardaient rien. ⚠️ **Et la CI a rougi APRÈS l'ouverture de la PR**, sur un test de cette US : la porte locale exécute `pytest` avec `frontend/dist/` **présent**, le job `backend` de la CI **sans** — la SPA montée à la racine change alors des codes de réponse (`404` contre `405`). Une suite verte en local pouvait donc être rouge en CI **sans qu'aucun code ait bougé** : le geste est désormais verrouillé dans la définition de l'agent de porte (`KERVIGNARC_FRONTEND_DIST` sur un chemin inexistant). Même famille que `DETTE-093`. | 3 |
| 2026-08-28 | `E16US008` | 23 | +940/−94 | ~15 min | ~32 min | **D** (15:22→15:44) | majeur:2 mineur:1 suggestion:1 | majeur:3 mineur:5 suggestion:3 | **bloquant:1** majeur:1 mineur:3 suggestion:1 | majeur:2 mineur:4 suggestion:1 | **bloquant:2** majeur:2 mineur:2 | **D (2)** + **C1 (1, partagé avec D)** — le bloquant propre à D (forfait sans effet sur un duel amont à demi connu) est le seul trouvé par **exécution** (sondes sur les effectifs 2→39) ; les quatre axes de grille ne l'ont pas vu. C2 seul a vu l'ADR-0050 rendu faux, A seul la garde de type de phase manquante | 4 |
| 2026-08-28 | `E16US008` (2ᵉ passe, sur les correctifs) | 20 | +576/−94 | ~12 min | ~27 min | **D** (16:29→16:49) | majeur:2 mineur:2 | majeur:2 mineur:8 suggestion:1 | majeur:2 mineur:5 suggestion:1 | majeur:5 mineur:6 suggestion:3 | **bloquant:1** majeur:3 mineur:6 suggestion:2 | **D (1 bloquant : atlas périmé, CI rouge)**. ⚠️ **La passe la plus instructive du registre** : les correctifs d'un bloquant contenaient eux-mêmes 2 majeurs et une régression. **A seul** a vu que la garde neuve était une *denylist* là où `TYPES_EN_TABLEAU_JOUE` (ADR-0083) existe ; **A, B, C1 et C2** ont convergé sur une régression d'identité invisible (retirer un paramètre `portee` fait retomber `fetchJson` sur son défaut `'admin'`) ; **C2 seul** a vu qu'un ID d'US écrit dans la cellule *Résorption* fait publier à l'atlas qu'une US livrée a soldé une dette ouverte ; **D seul**, par **sonde**, a montré que le correctif de texte de la 1ʳᵉ passe était **lui aussi faux**. ⚠️ **Et sa propre conclusion l'était aussi** — voir la 3ᵉ passe : la réalité est « une **ou** deux sources selon les byes », pas « deux ». Aucun axe de grille ne pouvait attraper ça : il fallait exécuter le moteur | 4 |
| 2026-08-28 | `E16US008` (3ᵉ passe, sur les correctifs) | 22 | +263/−122 | ~10 min | ~21 min | **D** (17:05→17:26) | majeur:2 mineur:2 suggestion:1 | majeur:4 mineur:8 suggestion:2 | majeur:3 mineur:6 suggestion:2 | majeur:4 mineur:4 suggestion:1 | **bloquant:1** majeur:6 mineur:3 suggestion:2 | **D (1 bloquant)** — et c'est **la leçon la plus chère du registre** : le même point a été écrit FAUX **trois passes de suite** (« une source », puis « deux sources », conclusion d'alors, elle-même fausse (voir la 4ᵉ passe) : « une ou deux **selon les byes** »). Chaque passe transposait le raisonnement de la précédente sans **re-sonder** le moteur. Ce qui a brisé le cycle n'est pas une relecture de plus : c'est d'avoir sorti l'oracle de la prose pour l'écrire en **test** (`test_une_ligne_bloquee_attend_une_ou_deux_sources_selon_ce_qui_reste_a_trancher`), les cinq textes n'en étant plus que la traduction. **Tant qu'un oracle ne vit que dans `docs/`, chaque passe en produit une version fausse.** A seul a vu que le correctif du message de succès était un **no-op** dont le commentaire affirmait le contraire ; C2 seul que la purge de l'artefact d'atlas était incomplète | 4 |
| 2026-08-28 | `E16US008` (4ᵉ passe, sur les correctifs) | 24 | +316/−130 | ~8 min | ~26 min | **D** (18:48→19:05) | majeur:2 mineur:6 suggestion:2 | majeur:2 mineur:6 suggestion:2 | majeur:5 mineur:6 suggestion:3 | majeur:6 mineur:7 suggestion:2 | **bloquant:1** majeur:4 mineur:5 suggestion:1 | **D (1 bloquant)** — **la leçon du registre, cran 2.** La 3ᵉ passe avait sorti l'oracle de la prose vers un test : bon geste, mais le test était écrit sur un tableau **vierge**, alors que l'organisateur lit le feu vert **pendant** le tour. D'où une **4ᵉ** version fausse du même point (« puissance de 2 ⇒ toujours deux », démenti par sonde : après un seul duel validé, `{1: 1, 2: 3}` sur 8 archers sans aucun bye). **Un oracle en test ne vaut que si sa fixture est l'état que l'utilisateur observe.** Les quatre axes de grille ont convergé sur deux résidus que D n'a pas eu à sonder : la phrase réfutée **réintroduite en commentaire** du test censé la tuer, et un second test dont l'assertion ne correspondait pas à son nom (vrai par construction). C1 seul a vu que le `reset()` ajouté avalait succès ET erreur si l'on repliait pendant le vol | 4 |
| 2026-08-28 | `E00US027` (2ᵉ passe, sur les correctifs) | 474 | +9871/−20265 | ~14 min | ~29 min | C1 (09:24→09:51) | majeur:3 mineur:5 suggestion:3 | majeur:2 mineur:6 suggestion:1 | majeur:5 mineur:2 | majeur:3 mineur:5 suggestion:1 | majeur:6 mineur:3 suggestion:1 | **aucun bloquant** — les 3 majeurs structurants (faux négatif du détecteur, 3 symboles vivants dé-backtickés, 17 modules coupés de leur ADR) viennent de **D**, la conjonction « borne durcie d'un seul côté » de **C1** | 2 |
| 2026-08-28 | `E00US027` | 452 | +8521/−19613 | ~15 min | ~44 min | D (07:53→08:24) | **bloquant:1** majeur:2 mineur:3 suggestion:3 | **bloquant:1** majeur:6 mineur:9 suggestion:1 | majeur:6 mineur:6 suggestion:2 | majeur:6 mineur:5 suggestion:2 | **bloquant:3** majeur:9 mineur:6 suggestion:1 | **A + C2 + B + D** sur le même bloquant (détecteur front aveugle au JSX) ; **D seul** sur la régression de portage absorbée par l'atlas | 1 |
| 2026-08-27 | `E16US009` (3ᵉ passe, sur les correctifs) | 18 | +341/−81 | ~11 min | ~19 min | C1 (21:45→22:00) | — *(non rejoué : aucun fichier de porte touché, aucun port ni adapter ni couche ajoutés)* | bloquant:0 **majeur:5** mineur:4 suggestion:3 | bloquant:0 **majeur:5** mineur:5 suggestion:1 | — *(non rejoué : ses trois majeurs cumulés portaient sur l'ADR et les renvois de dette, corrigés selon ses propres prescriptions et re-vérifiés par lui cellule par cellule en 2ᵉ passe)* | bloquant:0 **majeur:2** mineur:5 suggestion:1 | **aucun bloquant — mais le trou s'est déplacé une TROISIÈME fois, et c'est le fait marquant de cette US.** Le plafond posé en 2ᵉ passe sous-évaluait le chrome de ~95 px (il omettait le sous-titre de la vue, le `gap`, et **l'en-tête de page lui-même** — l'élément qu'ADR-0098 exige de rendre gros) : ~9 lignes utiles à 720p, pas 13. Et il a **supprimé le signal** — au-delà de 27 noms réglés le classement ne bouge plus, pendant que `VueAffectations`, sans plafond, déborde vers 55-66 : le conseil « réglez sur le classement », écrit dans le même commit, devenait faux sur les deux tiers de la plage. ⚠️ **Arbitrage de méthode, tiré au terme de trois décomptes successifs (144 → 232 → 273 px) : on cesse de raffiner un nombre que personne ne peut mesurer.** Le plafond retient le décompte le plus pessimiste (direction de l'erreur, pas justesse) et le reste est **inscrit au registre — `DETTE-086` élargie**, dont l'entrée prédisait mot pour mot ce défaut (« un 4ᵉ du même type est probable, aucun garde-fou du dépôt ne peut le voir »). B trouve en outre la 4ᵉ occurrence du conseil inversé et l'absence totale de test de rendu pour `VueAffectations` ; D trouve que la liste d'ADR hors critère, réparée en 2ᵉ passe sur le cas signalé, n'avait **pas été auditée** — `0087` et `0089` manquaient aux deux listes | 3 |
| 2026-08-26 | `E16US009` (2ᵉ passe, sur les correctifs) | 22 | +565/−108 | ~9 min | ~26 min | D (21:00→21:26) | — *(non rejoué : aucun fichier de porte touché, aucun port ni adapter ni couche ajoutés, et sa seule surface de production modifiée — `exploitation.py` — porte le remède qu'il réclamait lui-même ; il aurait relu son propre correctif)* | bloquant:0 **majeur:2** mineur:6 suggestion:3 | bloquant:0 **majeur:3** mineur:4 suggestion:3 | bloquant:0 **majeur:1** mineur:7 suggestion:2 | bloquant:0 **majeur:3** mineur:7 suggestion:3 | **aucun bloquant, mais la passe était justifiée : le trou s'était DÉPLACÉ trois fois.** (1) `ceil(n/3)` fermait le *facteur* et laissait deux termes — un chrome fixe (tête figée + `thead`, qui ne se divise pas) et une hauteur de ligne différente (`padding` en **px** dans `.table`, en **em** dans `.salle-pages__nom`), dont le résidu *croît* quand l'écran rétrécit : à 1280×720 le **défaut livré** débordait encore. C1, C2 et D l'ont chiffré **séparément**. (2) Pire, les trois textes écrits par le correctif disaient « réglez en regardant la liste de noms » — donc envoyaient l'organisateur remplir une page qui occupe toute la hauteur (`flex: 1`), droit dans la brèche : le correctif fabriquait le geste qui le défait. (3) L'étape 0 ajoutée pour rendre le scénario 1 exécutable rendait le **scénario 2** faux (quatre axes). B trouve en plus que la moitié « cadence » du CA n'était prouvée par **aucun** test — toutes les fixtures valaient 20, soit le défaut du module. D trouve le témoin `VueAffectations` resté muet à quarante lignes de celui qu'on venait d'instrumenter, et l'omission de `0097` dans la liste d'ADR hors critère — **par le paragraphe même qui dénonce ce mode de panne** | 2 |
| 2026-08-26 | `E16US009` | 45 | +2269/−308 | ~29 min | ~33 min *(recalculée sur la définition tranchée le 27/08 ; la valeur d'origine, ~24 min, appliquait l'ancienne légende)* | D (20:11→20:22) | bloquant:0 majeur:1 mineur:2 suggestion:2 | bloquant:0 **majeur:3** mineur:5 suggestion:3 | **bloquant:1** majeur:0 mineur:3 suggestion:1 | bloquant:0 **majeur:3** mineur:8 suggestion:3 | **bloquant:1** **majeur:4** mineur:5 suggestion:1 | **C1 et D, convergents et indépendants** — le même bloquant, calculé deux fois depuis le CSS du dépôt par deux arithmétiques distinctes : `noms_par_page` était calibré pour une liste **à trois colonnes** et appliqué tel quel à un tableau **mono-colonne**, si bien qu'au réglage livré par défaut le bas de chaque page de classement tombait sous le bord de l'image — sur la seule surface où personne ne peut faire défiler. ⚠️ **C2 voit le même fait et le classe majeur** (« la table débordait déjà avant l'US ») : l'arbitrage a retenu **bloquant**, sur le fait que D apporte — avant, l'archer de rang 60 finissait par apparaître ; après, la fenêtre avance de 40 en 40 et les rangs du bas de page ne sortent **jamais** de la journée. Une US qui régresse sur son propre CA n'est pas de la dette. Par ailleurs **quatre axes sur cinq** trouvent la même ligne d'ADR fausse (`teteFigee` attribuée à un module qui ne la porte pas, gardée par un test **inexistant**) — la 4ᵉ fois en trois US que la section « Porté dans le code par » ment, et l'atlas est **structurellement aveugle** à ce cas (le fichier cité n'a pas de `/`) | 1 |
| 2026-08-26 | `E16US006` (3ᵉ passe, sur les correctifs) | 23 | +1102/−211 | ~10 min | ~46 min | B (14:11→14:38) | bloquant:0 **majeur:3** mineur:4 suggestion:2 | bloquant:0 **majeur:4** mineur:6 suggestion:3 | — *(non rejoué : ses deux majeurs de la 2ᵉ passe étaient partagés avec D, et le remède qu'il préconisait est celui qui a été implémenté ; A, B et C2 étaient, eux, rendus obligatoires par la procédure)* | bloquant:0 **majeur:3** mineur:8 suggestion:2 | bloquant:0 **majeur:6** mineur:5 suggestion:4 | **aucun bloquant** — mais **A et D trouvent, chacun à l'exécution et indépendamment, que le durcissement de la 2ᵉ passe est encore écrit contre les exemples du rapport** : `_PREFIXE_XML` exigeait `[a-z]`, donc `<_x:script>` franchissait *tout*, y compris ce que la 1ʳᵉ rédaction attrapait. D montre en plus un **rétrécissement net** — les entités internes ne sont plus refusées mais toujours pas développées, donc une charge coupée en deux entités passe là où la 2ᵉ rédaction la bloquait. B ajoute le manquement que personne n'avait vu : les arbitrages tranchés en cours d'US n'étaient **pas reversés dans `stories/`** (règle 9) | 3 |
| 2026-08-26 | `E16US006` (2ᵉ passe, sur les correctifs) | 29 | +1105/−123 | ~11 min | ~33 min | D (12:56→13:19) | bloquant:0 majeur:0 mineur:3 suggestion:3 | bloquant:0 majeur:3 mineur:8 suggestion:5 | bloquant:0 majeur:2 mineur:6 suggestion:2 | bloquant:0 majeur:3 mineur:4 suggestion:2 | bloquant:0 **majeur:8** mineur:5 | **aucun bloquant** — mais **cinq des huit majeurs de D sont des trous DÉPLACÉS par les correctifs eux-mêmes** : la denylist SVG élargie tombait entièrement sur un préfixe de namespace (`<svg:script>` franchissait *aussi* les quatre formes que la 1ʳᵉ rédaction attrapait), le contrôle PNG avait été **relâché pour accommoder un test** de bourrage, et les deux garde-fous front réécrits restaient franchissables par la forme la plus idiomatique de leur cible (`setProperty`, `lazy(() => import(…))`). Trois autres remarques — dont une de chaque axe de grille — visaient des **assertions qui annonçaient plus qu'elles ne prouvaient** (la cascade, la minimalité, le nom accessible) | 2 |
| 2026-08-26 | `E16US006` (absorbe `E01US016`) | 43 | +4619/−220 | ~10 min | ~32 min | D (11:26→11:58) | bloquant:0 majeur:2 mineur:7 suggestion:1 | bloquant:0 majeur:3 mineur:7 suggestion:3 | bloquant:0 majeur:2 mineur:5 suggestion:6 | bloquant:0 majeur:3 mineur:4 suggestion:1 | **bloquant:1** majeur:6 mineur:4 | **D seul** — et c'est le fait de la passe : les **quatre axes de grille ont rendu zéro bloquant**. D a trouvé qu'un tournoi dont on avait effleuré l'écran d'identité devenait *définitivement* indéracinable (500), en **exécutant** `POST` → `PUT identité` → `DELETE` avec la baseline 204 sur le même code. Les quatre autres avaient lu la FK nue **et son marqueur `DETTE-001`**, et conclu à une aggravation régulière | 1 |
| 2026-08-24 | `E16US005` (1ʳᵉ passe) | 14 | +1089/−161 | ~14 min | ~12 min | D (17:36→17:48) | bloquant:0 majeur:0 mineur:2 suggestion:1 | **bloquant:1** majeur:2 mineur:3 suggestion:2 | **bloquant:1** majeur:1 mineur:3 suggestion:2 | **bloquant:1** majeur:2 mineur:2 suggestion:3 | **bloquant:2** majeur:2 mineur:4 suggestion:1 | **B, C1, C2 et D convergents** (1 bloquant : le jumeau des duels non aligné) ; **D seul** pour le 2ᵉ (l'arithmétique de largeur : l'US rendait l'écran plus tassé qu'avant) et pour le fond transparent de la réserve collante | 3 |
| 2026-08-24 | `E16US005` (2ᵉ passe, sur les correctifs) | 11 | +533/−94 | ~13 min | ~15 min | D (18:32→18:47) | *non rejoué* (aucun fichier de porte touché) | bloquant:0 **majeur:4** mineur:4 suggestion:2 | **bloquant:1** majeur:1 mineur:4 suggestion:2 | bloquant:0 **majeur:1** mineur:7 suggestion:1 | **bloquant:1** majeur:4 mineur:6 suggestion:1 | **C1 et D** (1 bloquant convergent : la troncature efface la catégorie et le blason, donc la moitié RG-4 du CA — B l'avait gradé majeur en annonçant l'escalade si la mesure confirmait ; elle a confirmé). **D seul** : le seuil corrigé n'a pas franchi son propre critère (96 px à 1366 contre 125 avant l'US) et crée une falaise au point de bascule | 3 |
| 2026-08-24 | `E16US005` (3ᵉ passe, sur les correctifs) | 11 | +618/−188 | ~11 min | ~19 min | D (19:12→19:31) | *non lancé* (front seul, règles 1-8 sans objet) | bloquant:0 **majeur:3** mineur:5 suggestion:3 | bloquant:0 **majeur:3** mineur:4 suggestion:2 | bloquant:0 **majeur:3** mineur:5 | **bloquant:2** majeur:3 mineur:7 suggestion:2 | **D seul** pour les deux bloquants : la bande [1249, 1377] px *toujours* pire qu'avant l'US (le même bloquant qu'en 2ᵉ passe, déclaré clos et non clos), et le `min-height` posé en correctif de 2ᵉ passe qui régressait **23 écrans hors périmètre**. Convergence des quatre axes sur le blason encore illisible et sur les chiffres faux du tracker | 3 (sortie) |
| 2026-08-23 | `E16US012` (7ᵉ passe, ciblée B+D) | 17 | +143/-52 | ~2 min | ~13 min | D (21:59→22:11) | — | majeur:3 mineur:5 suggestion:1 | — | — | **bloquant:0** majeur:3 mineur:3 suggestion:2 | **aucun bloquant** | 7 (sortie) |
| 2026-08-23 | `E16US012` (6ᵉ passe, sur les correctifs) | 16 | +205/-62 | ~2 min | ~26 min | D (21:10→21:36) | — | majeur:4 mineur:2 suggestion:2 | majeur:5 mineur:3 suggestion:1 | — | **bloquant:0** majeur:7 mineur:4 suggestion:1 | **aucun bloquant** | 7 |
| 2026-08-23 | `E16US012` (5ᵉ passe, sur les correctifs) | 14 | +234/-83 | ~2 min | ~18 min | D (20:29→20:46) | — | majeur:2 mineur:4 suggestion:2 | majeur:3 mineur:3 suggestion:2 | majeur:3 mineur:4 suggestion:1 | **bloquant:1** majeur:3 mineur:3 suggestion:1 | **D (1)** | 6 |
| 2026-08-23 | `E16US012` (4ᵉ passe, sur les correctifs) | 17 | +260/-61 | ~2 min | ~40 min | D (19:12→19:52) | **OK** mineur:5 suggestion:1 | majeur:1 mineur:5 suggestion:4 | majeur:1 mineur:5 | majeur:3 mineur:5 suggestion:1 | **bloquant:1** majeur:2 mineur:4 suggestion:1 | **D (1)** | 5 |
| 2026-08-23 | `E16US012` (3ᵉ passe, sur les correctifs) | 27 | +613/-186 | ~2 min | ~20 min | D (13:52→14:10) | majeur:2 mineur:4 suggestion:1 | majeur:5 mineur:3 suggestion:1 | majeur:4 mineur:4 | majeur:5 mineur:4 suggestion:1 | **bloquant:1** majeur:3 mineur:4 suggestion:1 | **D (1)** | 4 |
| 2026-08-23 | `E16US012` (2ᵉ passe, sur les correctifs) | 27 | +1025/-230 | ~5 min | ~37 min | D (12:41→13:18) | majeur:3 mineur:4 | majeur:2 mineur:4 suggestion:1 | majeur:3 mineur:2 suggestion:1 | majeur:2 mineur:4 suggestion:2 | **bloquant:1** majeur:3 mineur:4 | **D (1)** | 3 |
| 2026-08-23 | `E16US012` | 35 | +2385/−119 | ~22 min | ~28 min | D (12:12→12:20) | majeur:1 mineur:2 | majeur:2 mineur:3 suggestion:2 | mineur:4 suggestion:1 | majeur:3 mineur:2 suggestion:2 | **bloquant:1** majeur:6 mineur:5 suggestion:2 | **D (1)** | 2 |
| 2026-08-22 | `E16US002` (2ᵉ passe, sur les correctifs) | 43 | +718/−128 | ~25 min | ~21 min | D (22:39→22:58) | majeur:2 mineur:4 suggestion:2 | majeur:3 mineur:4 suggestion:1 | majeur:3 mineur:4 suggestion:1 | majeur:2 mineur:6 suggestion:2 | majeur:7 mineur:5 suggestion:1 | **bloquant:0** — les deux de la 1ʳᵉ passe fermés et vérifiés par exécution | 2 |
| 2026-08-22 | `E16US002` | 48 | +1579/−161 | ~18 min | ~20 min | D (21:19→21:39) | **bloquant:1** mineur:2 suggestion:1 | **bloquant:1** majeur:4 mineur:5 suggestion:1 | **bloquant:1** majeur:2 mineur:4 suggestion:2 | majeur:6 mineur:7 suggestion:2 | **bloquant:2** majeur:6 mineur:3 | **A, B, C1, D** (le même bloquant, quatre fois) **+ D seul** (le 2ᵉ : un ADR attestant « vérifié » une traversée inexistante) | 2 |
| 2026-08-22 | `E05US027` | 76 | +5909/−237 | ~23 min | ~76 min | D (15:41→16:24) | **bloquant:1** majeur:0 mineur:3 | bloquant:0 **majeur:6** mineur:8 suggestion:3 | bloquant:0 **majeur:2** mineur:5 suggestion:2 | **bloquant:1** majeur:3 mineur:5 suggestion:3 | bloquant:0 **majeur:5** mineur:4 suggestion:1 | **A et C2, un chacun et disjoints** — C2 : `useRegenererPlanColline` sans appelant, donc plan de cibles inatteignable et **format injouable** (3ᵉ récidive du défaut d'E05US023) ; A : `test_arrets_api.py` non élargi au 6ᵉ service, alors que le composition root affirmait l'inverse. ⚠️ **Trois majeurs sont des trous *déplacés*** — `_nb_tours_a_la_composition` (E05US035), `MOTEUR_SAIT_JOUER` (E05US028), le montage du plan (E05US023) : le raisonnement avait été tenu et tranché sur le format précédent, jamais rejoué sur le format neuf | 2 |
| 2026-08-22 | `E05US027` (2ᵉ passe, sur les correctifs) | 34 | +1512/−161 | ~14 min | ~31 min | D (16:58→17:19) | *non rejoué* (aucun fichier de porte touché) | bloquant:0 **majeur:1** mineur:5 suggestion:2 | bloquant:0 **majeur:1** mineur:6 suggestion:2 | bloquant:0 **majeur:10** mineur:5 suggestion:2 | bloquant:0 **majeur:2** mineur:6 suggestion:2 | **aucun bloquant** — mais quatre majeurs décrivent des défauts *introduits par les correctifs eux-mêmes* : un frein sans porte de sortie (D), les deux régimes de borne inversés (C1), un test anti-récidive qui promettait par écrit ce qu'il ne faisait pas (D), et le jumeau suisse laissé cassé sur l'écran que le correctif venait d'ouvrir (B). C2 a rendu 10 majeurs, dont 5 « traces fausses qui se lisent comme des preuves » | 2 |
| 2026-08-21 | `E05US029` | 33 | +1878/−121 | ~10 min | ~52 min | D (13:12→14:04) | bloquant:0 **majeur:1** mineur:1 | bloquant:0 **majeur:2** mineur:6 suggestion:1 | **bloquant:1** majeur:3 mineur:3 suggestion:2 | bloquant:0 **majeur:4** mineur:1 suggestion:1 | **bloquant:1** majeur:1 mineur:6 | **C1 et D, un chacun et disjoints** — C1 : `nb_qualifies` désigne un peigne de rangs qu'aucun prélèvement ne sait exprimer ; D : le refus neuf ignorait la **nature** des sources, donc bloquait un format valide. Aucun des deux n'était atteignable par une grille : l'un naît d'une **conjonction** (code juste, CA juste, rencontre fausse), l'autre d'un **voisin non rejoué**. ⚠️ Le majeur `_motif_de_choc` a été trouvé **par trois axes indépendamment** (A, C2, D) — première convergence à trois du registre | 2 (en cours) |
| 2026-08-21 | `E05US029` (2ᵉ passe, sur les correctifs) | 20 | +721/−91 | ~9 min | ~43 min | D (14:12→14:55) | bloquant:0 majeur:2 mineur:3 | bloquant:0 **majeur:3** mineur:4 suggestion:1 | bloquant:0 **majeur:3** mineur:6 suggestion:2 | bloquant:0 majeur:2 mineur:4 | bloquant:0 **majeur:5** mineur:3 | **aucun bloquant** — les deux de la 1ʳᵉ passe sont fermés, et C1 comme D l'ont vérifié en cherchant un chemin qui les rouvre (aucun). ⚠️ **Trois des cinq majeurs de D étaient dans le code neuf des correctifs**, dont deux **trous déplacés** au sens strict : une garde `effectif < 1` que l'auteur applique 180 lignes plus bas, et une aide « sans objet » ajoutée au champ *ignoré* en oubliant le champ *refusé*. Un 3ᵉ défaut est une **affirmation d'exactitude mesurée fausse** (25 % de faux positifs) — inscrite en docstring et en ADR, c'est-à-dire au seul endroit où le dépôt garde ses preuves | 2 (close) |
| 2026-08-21 | `E05US035` | 53 | +1892/−147 | ~14 min | ~32 min | D (09:12→09:44) | **bloquant:1** majeur:4 mineur:1 | **bloquant:2** majeur:3 mineur:3 suggestion:3 | **bloquant:1** majeur:2 mineur:3 suggestion:2 | **bloquant:1** majeur:2 mineur:3 | **bloquant:3** majeur:2 mineur:4 suggestion:2 | **les 5 axes** sur l'arrêt inerte (1 convergent, le seul de l'histoire de ce registre à être trouvé par les cinq) ; **D seul** sur les deux autres — le réglage monté dans une **branche morte** et le filtre forfait aveugle hors du premier créneau (`DETTE-047`) ; **B seul** sur la fiche fonctionnelle absente ; **l'auteur** sur un 5ᵉ, trouvé en corrigeant (`ReglageBarrage` n'aurait pas réémis `decoupage`, donc régler un barrage l'effaçait) | 2 |
| 2026-08-21 | `E05US035` (2ᵉ passe, sur les correctifs) | 28 | +1029/−105 | ~4 min | ~36 min | C1 (09:44→10:20) | — | **bloquant:1** majeur:5 mineur:7 suggestion:2 | **bloquant:1** majeur:2 mineur:7 suggestion:1 | — | *(voir note)* | **B et C1, convergents** : le correctif du bloquant front avait fermé la moitié `decoupage` du trou de câblage et laissé la moitié `arrets` ouverte — on pouvait découper la qualification sans pouvoir y poser la pause, donc l'US restait inerte sur le geste même pour lequel le découpage existe. Le **même défaut, déplacé d'un cran** | — |
| 2026-08-20 | `E05US034` | 41 | +3310/−147 | ~7 min | ~24 min | D (11:47→12:02) | **bloquant:1** majeur:2 mineur:2 suggestion:1 | **bloquant:1** majeur:3 mineur:5 suggestion:2 | **bloquant:1** majeur:1 mineur:3 suggestion:3 | **bloquant:1** majeur:2 mineur:2 | **bloquant:2** majeur:2 mineur:4 suggestion:2 | **les 5 axes** sur le fuseau (1 convergent) + **C2 et D seuls** sur l'écran de salle (1) ; **D seul** sur le rappel indélébile (majeur) | 2 |
| 2026-08-20 | `E05US034` (2ᵉ passe, sur les correctifs) | 26 | — | ~8 min | ~30 min | D (14:05→14:31) | — | **bloquant:1** majeur:3 mineur:6 suggestion:3 | — | — | bloquant:0 majeur:3 mineur:7 suggestion:1 | **B seul** (1 bloquant : le grain de l'annonce de salle) ; **D seul** (2 majeurs : le comptage des phases, le refus dupliqué) | — |
| 2026-08-19 | `E05US033` | 61 | +4966/−161 | ~7 min | ~50 min | D (11:52→12:39) | **bloquant:2** majeur:6 mineur:4 suggestion:2 | **bloquant:4** majeur:4 mineur:3 | **bloquant:4** majeur:4 mineur:2 suggestion:1 | **bloquant:2** majeur:3 mineur:3 suggestion:2 | **bloquant:3** majeur:4 mineur:4 | **les 4 axes de grille** (2 convergents) + **D seul** (1) | 2 |
| 2026-08-19 | `E05US033` (2ᵉ passe, sur les correctifs) | 74 | +5188/−404 | ~6 min | ~45 min | D | **bloquant:0** majeur:4 mineur:6 | **bloquant:1** majeur:7 mineur:4 | **bloquant:2** majeur:5 mineur:5 suggestion:2 | **bloquant:1** majeur:9 mineur:4 | **bloquant:2** majeur:7 mineur:14 | **C1** (1) + **C2** (1) + **D** (2) + **B** (1), 1 partagé | — |
| 2026-08-19 | `E05US032` | 26 | +1456/−113 | ~15 min | ~35 min | D (00:20→00:47) | majeur:2 mineur:4 suggestion:2 | majeur:5 mineur:6 | majeur:6 mineur:4 suggestion:2 | majeur:3 mineur:5 suggestion:3 | majeur:5 mineur:6 suggestion:2 | **aucun bloquant** — 5 majeurs de conjonction trouvés par D et C1 seuls | 1 |
| 2026-08-18 | `E05US031` | 43 | +3064/−177 | ~10 min | ~45 min | D (16:12→16:57) | majeur:2 mineur:2 suggestion:2 | majeur:3 mineur:4 suggestion:2 | **bloquant:1** majeur:3 mineur:5 suggestion:3 | majeur:2 mineur:3 suggestion:2 | majeur:4 mineur:2 suggestion:1 | C1 | 1 |
| 2026-08-16 | — (`chore/agents-dedies-revue`) | 13 | +719/−133 | ~1 min | ~12 min | C2 | bloquant:2 majeur:6 mineur:4 | majeur:5 mineur:5 | majeur:6 mineur:5 | majeur:9 mineur:5 | bloquant:3 majeur:6 mineur:3 | **A (2), D (3)** | 2 |

**Lecture de la première ligne.** Elle contredit déjà une présomption d'ADR-0013 et en confirme une
autre. C2 est bien l'axe le plus lent — la scission C1/C2 tient. Mais les **bloquants** viennent de A
et de D, pas du chemin critique : la vitesse d'un axe ne prédit pas ce qu'il trouve. Et pour la
troisième fois consécutive, l'axe adversarial trouve le plus grand nombre de bloquants — dont deux
qu'aucun axe de conformité n'avait vus.

**Lecture de la deuxième ligne (E05US031).** Trois enseignements, dont deux vont contre la première
ligne.

1. **L'axe adversarial n'a PAS trouvé le bloquant** — c'est C1, un axe de conformité, qui l'a vu
   (un compteur d'archers « encore en lice » qui affichait combien il en resterait à la fin). La
   série « D trouve le plus de bloquants » s'arrête à trois. Ce que D a apporté ici est d'un autre
   ordre : deux défauts de **raisonnement transporté** — une règle juste chez son auteur d'origine,
   réutilisée là où son hypothèse ne tient plus — qu'aucune grille ne décrit.
2. **D reste l'axe le plus lent** (45 min), et de loin, alors que la première ligne désignait C2.
   L'écart tient au périmètre : ici D a relu du code d'appui hors diff pour vérifier une affirmation
   de l'auteur. C'est ce qu'on lui demande ; le chemin critique s'allonge en conséquence.
3. **Les cinq axes ont trouvé, et aucun n'était redondant.** Quatre défauts n'ont été vus que par un
   seul axe : le bloquant (C1), le portage d'ADR hors de portée du vérificateur d'atlas (C2, confirmé
   par D), l'inversion `shared/ → features/` exprimée en CSS (A), et une section de registre décrivant
   une version antérieure de l'US (D). La grille de conformité et l'adversarial ne se recouvrent pas.

⚠️ **Le coût réel de la passe est sous-estimé par la colonne « durée revue ».** Les correctifs ont
demandé une heure de plus que la revue elle-même, l'essentiel étant les **trois fichiers de tests de
montage** qui manquaient (+26 cas). C'est la contrepartie honnête d'un axe B qui fait son travail :
il ne coûte rien à la revue et beaucoup à la correction.

---

### Passe `E05US032` (19/08/2026) — zéro bloquant, et pourtant la passe la plus corrective

**Ce que cette ligne apprend, et qui contredit une lecture naïve du tableau** : *aucun* axe n'a rendu
de bloquant, et c'est pourtant la passe qui a demandé le plus de correctifs de code — cinq défauts de
correction réels, dont un qui faisait se contredire deux écrans du produit. « Zéro bloquant » ne veut
pas dire « peu à corriger » : la sévérité mesure ce qui empêche de merger, pas ce qui est faux.

**Convergence et complémentarité, mesurées** :

- **`DETTE-031` aggravée sans que le registre bouge** a été trouvée par les **cinq** axes. C'est le
  score le plus élevé jamais observé sur une remarque, et il dit quelque chose de désagréable : ce
  n'est pas la détection qui manque, c'est le réflexe d'écriture. La ligne du registre portait déjà
  « 3ᵉ récidive » ; c'était la 4ᵉ.
- **Le filet trop étroit et muet** (`except` sans `KeyError`, sans log) : cinq axes également.
- **Trois majeurs n'ont eu qu'un seul trouveur**, et tous trois étaient des bugs :
  - *poules : le tour avance avant validation* — **D seul** (adversarial) ;
  - *« Finale » annoncée sur un tableau de placement* — **D seul** ; c'était nommément le « risque
    assumé » que l'ADR demandait à la revue de vérifier, et aucun axe de grille ne l'a vu ;
  - *le CA « une phase à un seul tour n'annonce pas de numéro » non appliqué, et le test réécrit pour
    coller au code* — **B seul**. C'est la raison d'être de la règle 9, prise en flagrant délit.
- **Deux CA effacés sans trace au recadrage** — **D seul**. Le bloc de CA supprimé en portait trois,
  un seul avait été explicitement révoqué. La règle 9 sait détecter un CA *périmé* ; elle ne voit pas
  un CA *effacé*.

**L'enseignement de procédure** : l'axe adversarial a produit **trois** des cinq majeurs uniques.
Sur une US qui pose une abstraction neuve, il ne double pas la grille — il regarde ailleurs. La
décision d'ADR-0013 de le rendre *requis* sur les changements structurels est confirmée par les
chiffres, pour la deuxième passe consécutive.

**Un cas nouveau, à retenir** : l'axe C2 a montré qu'un **encart rédactionnel placé dans la section
« Porté dans le code par » d'un ADR neutralisait le contrôle `portage-symbole-absent` de l'atlas** —
en citant un fichier non lisible symbole par symbole, le parseur y rattachait toute la liste. Un
garde-fou désarmé par la mise en forme, invisible au vert. C'est la première fois qu'une revue trouve
un garde-fou neutralisé *sans* qu'aucun fichier de configuration soit touché.

**Lecture de la ligne E05US033 — la passe la plus lourde à ce jour, et celle qui renverse deux
présomptions.**

**1. Pour la première fois, les quatre axes de grille convergent sur les mêmes bloquants.** A, B, C1 et
C2 ont trouvé *indépendamment* les deux mêmes : le `None` polysémique du déclencheur, et le gel posé sur
2 des 5 chemins d'écriture. Les trois passes précédentes montraient l'inverse — des bloquants trouvés
par **un seul** axe. L'explication tient à la nature du défaut : ce ne sont pas des défauts de
conjonction subtils mais des **capacités non branchées**, visibles depuis n'importe quel angle dès qu'on
compte les surfaces. Enseignement : la convergence n'est pas un gâchis, c'est le signal qu'un défaut est
grossier — et qu'il aurait dû être vu par l'auteur.

**2. L'axe adversarial reste indispensable, mais son apport a changé de nature.** Pour la quatrième
passe consécutive, D trouve ce que les grilles ne voient pas — sauf que cette fois il l'a trouvé **contre
un correctif en vol**. L'auteur avait commencé à réparer le bloquant n°1 pendant la revue ; D a
démontré, en le reproduisant, que le correctif **ne fermait rien** (le discriminant choisi ne
discriminait pas). Aucune grille n'aurait pu le voir : le code committé était faux d'une façon, l'arbre
de travail d'une autre. C'est le premier cas où l'axe adversarial relit **le correctif** plutôt que la
livraison, et c'est ce qui a évité de livrer une réparation cosmétique.

**3. Le vrai enseignement est sur les doublures, pas sur les axes.** Les trois bloquants sont passés au
travers de **3453 tests verts**, et les cinq axes ont convergé sur la même cause : la doublure
d'avancement des tests de service codait `nb_tours=9` en dur. Elle **rendait la borne intestable** — le
cas qui casse n'était pas exprimable dans le décor. Ce n'est pas un défaut de couverture (le CA était
couvert) mais un défaut de **doublure**, et aucune métrique de couverture ne l'aurait montré. À
retenir : quand un test passe par un double, se demander *quelles valeurs le double ne peut pas
produire* — c'est là que vivent les bloquants.

**4. Un fait à noter sur l'auteur.** Trois manques ont été trouvés par **auto-contrôle avant** le
lancement des axes (fiche fonctionnelle absente, marqueur de dette non posé, affirmation d'ADR
imprécise). Ils ne figurent pas dans les colonnes ci-dessus, et c'est volontaire : ce ne sont pas des
trouvailles de revue. Mais ils disent quelque chose d'utile — l'étape 0 de la procédure, qui force à
recenser le périmètre et à relire le log, produit des détections *par elle-même*.

**5. Durée porte : 7 min, et elle a servi deux fois.** Verte au premier passage, elle a permis de
lancer les cinq axes sans attendre. Repassée **entière** après correctifs (décision 1 d'ADR-0013), elle
a coûté 3 min de plus — sur une passe où le code de production a été profondément remanié, c'est le
seul contrôle qui garantissait que les 28 oracles neufs ne masquaient pas une régression ailleurs.

**6. La 2ᵉ passe a trouvé six bloquants de plus, et c'est le fait le plus instructif de la ligne.**
Une seconde passe complète a été lancée **sur les correctifs** de la première, ce qui n'était pas
arrivé jusqu'ici. Elle n'a pas rendu un rapport résiduel : elle a trouvé **six** bloquants neufs, tous
introduits ou révélés par les correctifs eux-mêmes — dont deux d'un genre qu'aucune première passe ne
pouvait produire :

- une garde de gel posée par recherche de motif dans le **mauvais** corps de méthode
  (`ServiceBigShootOff.projection`, une **lecture**, au lieu de `saisir_volee`) : les deux premières
  lignes se ressemblaient. Un correctif appliqué par script sur une ancre non unique ;
- un ordre d'écriture (trace puis pause) qui, inversé, laissait une phase `EN_PAUSE` **sans bouton de
  relance** si la seconde écriture échouait — c'est-à-dire le mode de panne exact que l'ADR est écrit
  pour empêcher, atteint par la porte de l'`except`.

Enseignement : **un correctif de revue est du code neuf, et il n'a été relu par personne.** Le tenir
pour acquis parce qu'il répond à une remarque est l'angle mort de la procédure. Contrepartie honnête :
la 2ᵉ passe coûte presque autant que la première, donc elle ne se justifie que quand la 1ʳᵉ a produit
des correctifs **structurels** — ce qui était le cas ici (une frontière de couche, cinq points
d'écriture, un prédicat de domaine réécrit).

**7. Deux défauts sur six venaient d'un outil, pas d'un raisonnement.** Un script de re-justification
de commentaires, lancé pour tenir la limite de 100 colonnes, a fusionné des blocs de définitions de
liens Markdown dans la prose qui les précédait — créant **trois références mortes** — et transformé
neuf titres `## X` en `# # X`. Il a aussi produit ~540 lignes de diff sans contenu dans un commit de
correctifs, ce qui rend la relecture humaine du diff impraticable. Les axes C1, C2 et D l'ont relevé
ensemble. Enseignement : **ne pas reformer un paragraphe entier pour rentrer une ligne.** Le correctif
retenu est mécanique et local — un mot rejeté sur la ligne suivante — et les fichiers abîmés ont été
**repris depuis `main`** puis re-patchés à la main, hunk par hunk, ce qui a ramené le diff de
`composition.py` de 247/206 à **65/0**.

**8. Le périmètre a été redécoupé en fin de revue, et c'est un résultat de la revue.** Quatre des six
bloquants de la 2ᵉ passe vivaient dans le même volet : le lecteur d'avancement de la qualification et
son réglage « découper en x tours ». En les instruisant, il est apparu que dériver le tour d'une
qualification demande trois choses non budgétées — la population réelle de la phase (ADR-0082), le
plan de cibles, les forfaits. Le commanditaire a arbitré leur sortie vers `E05US034`, l'arrêt étant
désormais **refusé** sur tout type dont l'application ne lit pas le tour. Enseignement : une revue ne
rend pas seulement une liste de correctifs — elle peut établir qu'une **tranche était mal découpée**,
et c'est une information plus utile que les correctifs eux-mêmes.

**9. Un défaut de *point de montage* est invisible à tous les tests de logique pure.** Le bloquant le
plus grave d'`E05US034` n'était dans aucune fonction : `resumeDeRelance`, `peutPoserUnePause` et
`libelleEtatDuTour` étaient justes, et 88 tests étaient verts. Le bandeau de pause vivait simplement
dans `VueEnCours`, alors que `EN_COURS` n'est pas au déroulé par défaut d'un écran de salle — donc
l'annonce ne s'affichait *jamais* sur la seule surface qui n'a personne devant elle pour changer de
vue. Deux axes seulement l'ont vu (C2 et adversarial), et tous deux en **lisant le domaine du
serveur** (`SequenceVues.par_defaut`) depuis un défaut du front. Enseignement : quand un CA nomme
une **surface**, l'oracle doit monter cette surface — et la couvrir dans l'état où elle est livrée,
pas dans celui qui arrange le test. `EcranSalle.test.tsx` est né de là.

**10. Quatre documents affirmaient la couverture que le code n'avait pas.** Le même diff qui laissait
le trou ci-dessus remplaçait le commentaire de `routage.py` qui le **traçait** (« conséquence assumée
et détectable depuis ici ») par « est **livrée** par E05US034 », et l'affirmait encore dans la section
*Porté dans le code par* d'ADR-0092, dans la fiche de recette et dans le journal. C'est exactement le
défaut qu'ADR-0075 a créé sa règle pour empêcher — un ADR qui nomme un module ne prouve rien si l'on
n'a pas vérifié dans le code du jour — reproduit à l'intérieur même d'un ADR qui porte l'avertissement
en tête de section. Enseignement : **ce qui déclare un trou fermé mérite plus de suspicion que ce qui
le laisse ouvert**, parce que le premier retire la détection en plus du défaut.

**11. Un seul axe a trouvé un majeur que quatre autres ont manqué.** L'axe adversarial est le seul à
avoir remarqué que le pilotage offre « Reprendre » (cycle de vie) *à côté* de « Relancer », et que le
premier laisse le rappel de relance allumé pour toujours — trou hérité d'`E05US033`, mais qu'`E05US034`
hisse au tableau de bord avec un compteur croissant. Aucune grille ne contient « regarder le bouton
d'à côté ». La colonne « bloquants par » commence à dire ce qu'ADR-0013 espérait qu'elle dise : sur
cinq passes, l'axe D a trouvé seul au moins un défaut à chaque fois.

**12. Corriger un bloquant en introduit un autre — et la 2ᵉ passe n'est pas facultative.** Le
correctif de l'écran de salle (n° 9 ci-dessus) a fermé le trou en en ouvrant un symétrique : il
allumait le bandeau dès qu'**une** phase du créneau était en pause, alors que la portée par défaut
d'un arrêt est *la phase seule*. L'écran projeté aurait donc annoncé une suspension générale pendant
qu'une autre phase tirait — ce que le test frère de `VueEnCours` qualifie lui-même de « pire que pas
d'annonce ». Deux tests neufs l'accompagnaient et **ne pouvaient pas le voir** : à créneau
mono-phase, « une phase est en pause » et « la salle est arrêtée » sont indiscernables. Même motif
sur le rappel de relance : filtrer l'**allumage** sur l'état réel des phases laissait le **comptage**
sur la liste historique, si bien que le tableau de bord annonçait « 2 phases attendent » quand une
seule était éteinte. Enseignement : un correctif de bloquant mérite la même défiance que le code
qu'il remplace, et le décor d'un test de correctif doit contenir **au moins deux** exemplaires de ce
que la règle discrimine — sinon il vérifie une tautologie.

**13. La 2ᵉ passe cadrée a été réduite à deux axes pour raison de coût, et cela doit se lire.** Cinq
relecteurs à modèle fort sur un diff de 3300 lignes ont épuisé la limite de session en une passe. La
seconde n'a donc lancé que **B** (obligatoire : les correctifs touchent du code de production, et la
règle 9 détecte une absence) et **D** (le plus productif empiriquement). **C2 n'a pas relu** la
création de `DETTE-075`, l'élargissement de `DETTE-001`/`DETTE-031` ni l'amendement d'ADR-0092 —
c'est un angle non couvert, pas un angle vérifié, et il est signalé comme tel dans le corps de la PR.
Enseignement pratique : sur une US de cette taille, lancer la 2ᵉ passe **après** confirmation de la
porte verte, jamais en parallèle — sinon on paie deux fois quand la porte rougit.

**14. La convergence de cinq axes ne dit rien sur ce que les autres n'ont pas vu — et c'est le
contraire de rassurant.** Les cinq relecteurs ont trouvé le **même** bloquant (`nb_tours=None` passé
à `verifier_arrets`), première fois dans ce registre. La tentation est d'y lire une revue solide ;
la lecture juste est l'inverse. Ce bloquant-là était **inscrit dans le diff** — un `None` passé à un
paramètre que l'US venait de rendre calculable —, donc visible de n'importe quel angle. Les deux
bloquants qui **n'ont été vus que par D** ne l'étaient pas : l'un demandait de vérifier qu'une
branche JSX est **atteignable** (`TYPES_AJOUTABLES` + `gereeAilleurs`, deux verrous à soixante lignes
du code ajouté), l'autre de remonter la chaîne d'**écriture** d'un forfait pour découvrir que
`par_phase` ne trouve jamais rien hors du premier créneau (`DETTE-047`). Aucune grille ne demande
ça ; c'est exactement la mission de l'axe adversarial. **Sur cette passe, D a doublé la détection de
bloquants à lui seul** — et la colonne « bloquants par » interdit désormais de le raccourcir, comme
sa définition l'annonçait.

**15. Un correctif de bloquant en révèle un autre, et l'auteur est bien placé pour le voir.** En
appliquant le remède déjà validé pour le barrage (le contrôle dédié hors du formulaire mort),
l'auteur a lu le code de `ReglageBarrage` — qui réémet **tous** les champs parce que le `PUT` est une
édition totale — et constaté qu'il ne réémettait pas `decoupage`. Régler un barrage aurait donc
effacé le découpage, donc rendu inertes toutes les pauses posées dessus. Aucun axe ne l'avait relevé,
et c'est logique : ce chemin n'est pas dans le diff de l'US, il est dans le code **qu'elle rend
faux**. Le commentaire de cette fonction raconte pourtant la même leçon **deux fois** (pour
`barrage_jusqu_au` en E06US003, pour `arrets` en E05US033) — troisième occurrence en un an, au même
endroit. Enseignement : quand un diff ajoute un champ à un agrégat édité en **totalité**, la question
« qui d'autre écrit cet agrégat sans passer par mon formulaire ? » mérite un `grep` systématique, et
elle n'est dans aucune grille.

**16. Un correctif de bloquant ferme le trou qu'on lui montre, pas la classe de trous.** Les cinq
axes avaient nommé un défaut de câblage : `ReglageDecoupage` monté dans une branche morte. Le
correctif a déplacé ce contrôle-là au bon endroit — et laissé `ReglageArrets`, son jumeau
indispensable, dans la branche morte. Résultat : on pouvait découper la qualification mais pas y
poser la pause, c'est-à-dire que l'US restait inerte **sur le geste même pour lequel le découpage
existe**. La 2ᵉ passe l'a trouvé par deux axes convergents, et le mot juste est celui du rapport :
« le même défaut, déplacé d'un cran ».

Ce qui aurait évité le second tour : après un bloquant d'atteignabilité, ne pas se demander « ce
contrôle est-il atteignable ? » mais **« le geste complet du CA est-il exécutable de bout en bout,
écran par écran ? »**. La fiche fonctionnelle écrite dans le même commit décrivait d'ailleurs le
geste impossible — un scénario de recette qu'on ne peut pas jouer est un signal, et il était sous
les yeux de l'auteur.

**17. Réduire la 2ᵉ passe à trois axes se paie, et il faut le dire.** A et C2 n'ont pas relu les
correctifs (choix de coût, cf. enseignement 13). Deux de leurs angles ont dû être rattrapés par B et
C1, qui les ont trouvés hors grille : un registre de dette devenu **faux dans le commit qui le
rendait faux** (`DETTE-022`, l'union des forfaits contredisant la note écrite trois heures plus tôt)
et un **signal d'atlas neuf** introduit par une ligne d'ADR agrégeant quatre fichiers. Les deux
relèvent de C2. Ils ont été vus ; rien ne dit que le troisième l'aurait été.

**18. La 2ᵉ passe a trouvé ses majeurs dans les PHRASES DE CLÔTURE, pas dans le code.** C'est le
constat le plus net de cette US, et l'axe adversarial l'a formulé lui-même : « les deux majeurs sont
dans les phrases où l'auteur déclare le problème résolu. Sur ce commit-ci, ce sont les affirmations
de clôture qui ont le plus mal vieilli, pas le code. » Les quatre correctifs de fond ont résisté à
l'attaque ; ce qui a cédé, ce sont « ce frein n'a aucun effet de bord » (faux : pas de porte de
sortie), « un type ajouté demain fera tomber le dernier cas » (faux : décor en dur), « les trois
autres sources étaient à jour » (faux : la puce CA), et « le troisième `ignore` » (il y en avait
quatre). **Une affirmation de clôture est une assertion non testée** : elle mérite la même méfiance
qu'un test qu'on n'a pas vu rougir.

**19. Corriger un défaut chez un format et pas chez son jumeau *aggrave* le jumeau.** La 1ʳᵉ passe
avait relevé trois « trous déplacés » — un raisonnement tenu sur le format précédent, jamais rejoué
sur le neuf. Le commit qui les ferme en a créé un quatrième, à l'identique : la borne d'effectif
corrigée sur la colline, laissée en l'état sur le suisse, **vingt lignes plus haut dans le même
fichier**. C1 l'avait pourtant signalé en 1ʳᵉ passe (« le même geste vaut pour `ReglageSuisse`, mais
je le laisse hors périmètre »), et cette phrase a été lue comme une dispense. Elle ne l'était pas :
le correctif installe la **preuve que le raisonnement était connu**, ce qui rend l'omission voisine
plus difficile à défendre qu'avant. Règle pratique : quand un correctif touche une famille de
jumeaux, soit on les traite tous, soit on inscrit les autres au registre — jamais « on verra ».

**20. Un garde-fou qui *promet* est plus dangereux qu'un garde-fou absent.** `PlansDeCibles.test.tsx`
a été écrit en 1ʳᵉ passe pour fermer une récidive vécue trois fois, et son en-tête annonçait couvrir
la quatrième. Son décor était une liste de trois types en dur : il ne pouvait structurellement pas
voir un quatrième. Le prochain implémenteur y aurait lu qu'il était couvert. Le correctif ne consiste
pas à retirer la phrase mais à **rendre la promesse vraie** — dériver décor, montage et test d'une
même table (`TYPES_A_PLAN_PAR_BLOCS`), puis vérifier en ajoutant un type qu'il rougit bien. La
vérification compte autant que le correctif : sans elle, on remplace une fausse assurance par une
autre.

**21. Un champ neuf a plusieurs écrivains — les lister par `grep` sur un champ voisin déjà éprouvé.**
E16US002 a ajouté `titre` partout où il se **déclare** (deux agrégats, trois DTO, trois types TS,
l'ADR, le glossaire, le registre, le journal, la recette) et l'a manqué là où il se **traverse** :
`_politiques_json` a **deux** appelants, un seul avait été câblé, et un format perdait donc tous ses
titres à l'écriture. Le geste qui l'aurait vu tient en une ligne — `grep -n "arrets" moteur.py` rend
**quatre** sites, `titre` n'en avait que trois. Le même écart vaut côté écran : `Phases.tsx` affichait
le titre, ses trois jumeaux (`Deroule.tsx`, les deux sélecteurs de source, `decrireEtape`) non.
Corollaire de la leçon 19, un cran plus haut : quand un correctif touche une famille de jumeaux, on
les traite tous — mais encore faut-il **savoir qu'elle est une famille**, et c'est un `grep` sur le
voisin, pas une relecture, qui le dit.

**22. Une case « vérifié : oui » non exécutée est pire qu'une section absente.** La section « Porté
dans le code par » d'ADR-0095 attestait l'aller-retour persistant « pour les **deux** tables » alors
qu'une des deux ne l'avait jamais fait. C'est le défaut d'ADR-0017 que `CLAUDE.md` met en garde,
commis dans la section dont l'en-tête affirme « écrite en vérifiant dans le code du jour ». La nuance
qui manquait : *lire* le code n'est pas *l'exécuter*. Les quatre lignes de cette section qui tenaient
réellement sont celles adossées à un **test nommé** ; celles adossées à un module l'étaient à un
instantané. Règle pratique : dans cette section, citer un test plutôt qu'un module chaque fois qu'un
test existe — un module se lit, un test rougit.

**23. Un test qui tourne sur un faux repository ne prouve pas l'aller-retour, même s'il l'annonce.**
`test_promouvoir_capture_le_titre_…` portait en docstring « le test couvre les **deux** sens, parce
qu'un seul serait vert avec la moitié du câblage » — et tournait en mémoire, donc n'atteignait jamais
la sérialisation où le câblage manquait précisément. Trois axes l'ont relevé. Le tri est mécanique :
un test de **service** sur dépôt factice garde la logique d'orchestration ; seul un test de
**repository** ou d'**API** garde une traversée. Écrire « aller-retour » dans une docstring de test
de service devrait déclencher la question « lequel, et jusqu'où ? ».

**24. Corriger un renommage, c'est greper le GESTE, pas seulement le NOM.** E16US002 a renommé deux
destinations et balayé 14 fiches de recette sur les deux libellés de menu — en laissant intactes
trois fiches qui demandent de cliquer un bouton (« Éditer ») que la même US **supprime**. Le
raisonnement qui justifiait le premier balayage (« une recette qui nomme un bouton absent est
inexécutable par son destinataire ») s'appliquait mot pour mot au second, et il n'a pas été fait :
la substitution mécanique ne relit pas ce qui l'entoure. Règle pratique : lister d'abord **tout ce
que l'US retire de l'écran** — libellés, boutons, emplacements de réglage — puis greper chaque
élément séparément.

**25. Un correctif de revue déplace le trou aussi souvent qu'il le ferme.** Cinq des sept majeurs de
la 2ᵉ passe d'E16US002 étaient des trous *déplacés* : le garde-fou de type posé sur le petit
écrivain et pas sur le grand ; le mécanisme de `_politiques_json` laissé intact derrière un 4ᵉ
commentaire ; un `decrireEtape` corrigé sur le mauvais des deux homonymes ; une classe CSS renommée
qui a perdu une de ses deux déclarations. Aucun n'aurait été vu par une relecture du seul correctif —
il fallait relire ce que le correctif **touche**, pas ce qu'il **répare**. C'est la justification
empirique de la règle « si les correctifs ont débordé des fichiers déjà relus, tous les axes se
rejouent » : ici ils avaient débordé, et la 2ᵉ passe complète a rendu sept majeurs.

**26. Une affirmation écrite sous pression est un défaut à part entière, et elle se loge dans les
registres.** Cette US a produit, dans ses *correctifs*, quatre énoncés faux : un ADR nommant un
symbole que le même commit venait de renommer ; une docstring affirmant l'absence d'une porte que le
même commit venait de créer ; une ligne de registre disant « aucun champ réinitialisé » là où il y
en avait sept ; un export justifié par un test qui n'existait pas. Aucun ne casse un cas utilisateur,
et c'est précisément le danger — ils se lisent comme des preuves, et les US suivantes en dérivent
leurs tests. Deux garde-fous mécaniques ont attrapé le premier (l'atlas, en passant de 39 à 42
signaux) ; **le compteur de signaux avait été lu et ignoré**, parce que « 0 écart bloquant » suffisait
à la porte. Un compteur qui monte est une information, pas de la décoration.

**27. Un compteur de signaux relevé en cours de correction compte ceux que la correction vient de
créer.** E16US012 a annoncé « zéro `portage-symbole-absent` contre **quatre** avant » : il y en avait
**deux** au commit d'origine, les deux autres ayant été introduits — puis refermés — par les
correctifs eux-mêmes, entre deux régénérations de l'atlas. Un compteur ne veut rien dire s'il n'est
pas mesuré contre `origin/main` : c'est la seule borne qui ne bouge pas pendant qu'on travaille.

**28. « L'axe X a dit que » n'est pas un fait — et un axe se trompe aussi.** La 1ʳᵉ passe a affirmé
que le module de test en cause était « le **seul** du dépôt à importer des symboles privés d'un
autre module de test ». L'auteur l'a recopié dans un commentaire de `conftest.py`, à l'endroit exact
où se décide « faut-il factoriser ? ». **Deux mesures distinctes** avaient été confondues : les
modules qui **importent** un symbole privé d'un autre module de test, et ceux qui **gardent une
copie locale** de `FauxTournoiRepository` (~25). Le commentaire répondait à la seconde question en
croyant répondre à la première.

⚠️ **Et il a fallu trois passes de plus pour arrêter de se tromper de chiffre.** La 3ᵉ a regravé le
décompte des copies ; la 4ᵉ l'a corrigé en « 13 » ; la 5ᵉ a produit une troisième valeur, parce que
la mesure elle-même est ambiguë (imports parenthésés, symboles privés seuls ou non). La leçon n'est
donc pas seulement « re-vérifier » : **un chiffre dont la définition n'est pas évidente ne se grave
pas**. On écrit l'ordre de grandeur et la commande qui le reproduit — un ordre de grandeur ne se
périme pas, et il suffit à décider s'il faut factoriser.

**29. Sur une famille, le correctif doit être rejoué sur chaque membre — sinon il *déplace* le
défaut d'un membre à l'autre.** E16US012 livre deux écrans « prêt à… » partageant une coquille. À
chacune des trois passes, la correction a été menée à fond sur le membre qui venait d'être relevé et
pas sur son voisin : la garde de statut fermée au domaine et pas sur l'écran *terminer* (2ᵉ passe,
bloquant) ; puis la liste vidée sur *démarrer* et pas sur *terminer*, le moment dérivé sur l'un et
écrit en dur sur l'autre (3ᵉ passe, bloquant). Le mécanisme est structurel, pas de l'inattention :
on corrige là où le rapport pointe. Sur une abstraction partagée, le réflexe doit être « et l'autre
membre ? » avant de repasser la porte.

**30. Une prop, un champ ou une garde qui ne peut plus être observé n'est pas neutre : il se lit
comme une preuve.** E16US012 a livré successivement trois conditions inertes — `bloquant={!enCours}`
puis `pret={enCours && …}` sur le même appel, et un `moment` que le domaine ne produisait pas. Aucune
ne changeait le rendu ; toutes étaient citées, en revue ou dans la section « Porté dans le code par »
de l'ADR, comme portant la décision. Le test qui « les garde » passe alors quoi qu'on fasse. Le
symptôme se détecte en une minute par mutation : si remplacer la condition par une constante laisse
la suite verte, elle ne porte rien — et il faut soit la retirer, soit cesser de l'invoquer comme
garantie.

**31. Sur un écran, le correctif se rejoue sur chaque bloc qui rend du texte.** Le constat 29 disait
« et l'autre membre ? ». Trois passes de plus ont montré la variante intra-écran : la même
contradiction de temps (« figera » / « est figé ») a été corrigée dans le **pied** d'un écran, puis
retrouvée dans sa **tête** au tour suivant, sur le même statut. Un écran a typiquement quatre zones
de texte — intro, verdict, liste, pied — plus son aide contextuelle, qui vit dans un autre fichier
et qu'aucune recette n'ouvre. Les cinq se relisent ensemble, ou le défaut se déplace de l'une à
l'autre au rythme d'une par passe.

**32. Avant d'armer un effet global, compter les consommateurs — la commande, pas la mémoire.**
E16US012 a ajouté un `refetchInterval` à `useTournois()` en justifiant : « deux consommateurs, tous
deux des écrans d'administration ». Ils sont trois, et le troisième est la **porte publique**, qui
monte le même composant sans condition : chaque téléphone de spectateur se serait mis à interroger le
serveur toutes les 5 s, jour J, sur le LAN — contre une doctrine que le dépôt écrit noir sur blanc
pour les routes ouvertes. L'inventaire tenait en un `grep`. C'est la même classe d'erreur que les
chiffres du constat 28, appliquée non plus à une phrase de doc mais à une **décision d'architecture**,
et son coût n'est pas documentaire.

**33. Remplacer un commentaire par un champ ne garde rien de plus si le champ n'est pas asserté.**
E16US012 a constaté qu'une convention ne vivait qu'en commentaire d'avertissement, et l'a remplacée
par un champ de contrat — geste juste. Mais le champ est parti en production avec **zéro assertion**
dans le dépôt, une valeur par défaut côté serveur, et une ligne d'ADR affirmant qu'il était gardé.
Le déplacement d'une promesse d'un support à un autre ne devient une garantie qu'au moment où une
mutation la fait rougir. Le réflexe : après avoir ajouté un champ ou une prop qui « porte » une
règle, le figer et relancer — s'il ne tombe rien, on a déplacé le commentaire, pas fermé le trou.

**34. Une mise en page qu'aucun test ne prouve ne se livre pas sans l'avoir regardée — et si on ne
peut pas la regarder, il faut la rendre robuste plutôt que juste.**
E16US005 a produit **deux bloquants de même racine**, et aucun n'était atteignable par la relecture
d'un diff. Le premier est un *non-changement* : le hunk manquant côté `Duels.tsx` n'apparaît nulle
part dans le diff, par définition. Le second est une **erreur d'arithmétique** — un point de bascule
`@media` mesuré sur le viewport alors que la contrainte était la colonne de contenu, 368 px plus
étroite sous la coquille : l'US divisait par deux la largeur de texte utile *tout en la doublant en
quantité*, donc rendait l'écran plus tassé que ce qu'elle prétendait corriger. Les deux se voyaient
en trente secondes d'application lancée.

La leçon utile n'est pas « lancer l'app » — le contrôle visuel s'est révélé **impossible sur ce
poste** (extension navigateur non connectée), et un banc d'essai statique reproduisant le DOM n'a pas
pu être ouvert non plus. C'est : **quand on ne peut pas mesurer, on choisit le réglage qui ne dépend
pas de la mesure.** Le correctif décisif n'a pas été de retoucher le seuil, mais de tronquer les
repères avec une bulle au lieu de les laisser se casser — une mise en page robuste à la largeur, au
lieu d'une mise en page accordée à une fenêtre supposée. Le seuil, lui, reste un pari, mais un pari
**commenté avec son offset**, donc réfutable.

**35. Un `replace(texte, 1)` sur un texte qui n'est pas unique produit un défaut de traçabilité
silencieux — et l'`assert` qui l'accompagne ne protège de rien.**
Deux défauts de cette US viennent du même geste. La puce « vocabulaire vérifié » a été barrée dans le
bloc d'`E16US004` au lieu d'`E16US005` : l'avertissement est rédigé **à l'identique dans deux blocs**
(`E16US004` et `E16US005` — deux autres en portent une variante voisine), et le script a patché la
première occurrence. *(La 1ʳᵉ rédaction de ce constat disait « quatre blocs identiques » : faux d'un
facteur deux, relevé en 2ᵉ passe. Une collision **à deux** suffit — c'est même le cas le plus
traître, puisqu'on ne se méfie pas.)* L'`assert avant in s` passait, évidemment — il
prouve la *présence*, jamais l'*unicité*. Résultat : une US déjà mergée annotée d'une vérification
portant sur la planche d'une autre, et l'US courante livrée avec un ⚠️ ouvert que son propre tracker
déclarait fermé. Le réflexe : sur un fichier de backlog où les puces se répètent d'une US à l'autre,
**compter les occurrences avant de remplacer** (`s.count(avant) == 1`), ou ancrer le remplacement sur
les bornes du bloc visé.

La seconde occurrence du même geste est plus retorse : la cellule *Résorption* de `DETTE-085` citait
`E05US027` comme **précédent** de refactor. Or l'atlas extrait `resorption_us` de cette cellule par
expression régulière — il a donc déclaré une dette du 24/08 **résorbée** par une US mergée le 22/08,
sans qu'aucun contrôle bronche (`controles.py` ne signale que les US *non spécifiées*). Nommer une US
dans cette colonne, fût-ce en exemple, la désigne comme résorbante.

⚠️ **Et la correction a rejoué le piège, dans le commit même qui écrivait ce constat.** L'identifiant
retiré a été remplacé par « garde-fou posé en attendant (E16US005) » — dans la même cellule. L'atlas
publiait alors une US qui *introduit* et *résorbe* la même dette : donnée parfaitement plausible,
donc plus dangereuse que l'absurdité de départ. Trois écrits du commit affirmaient l'inverse, dont
ce constat. **La leçon complète n'est donc pas « ne pas nommer une US en exemple » mais « ne nommer
aucune US, quel que soit le rôle qu'on lui prête » — et vérifier la donnée générée, pas le texte
source.** Le contrôle qui manque est décrit dans `DETTE-085`, avec la raison pour laquelle le
prédicat évident ne convient pas.

**36. Trois passes sur la même US, trois bloquants du même type : le dispositif ne converge pas
quand l'oracle manque.**
E16US005 a produit 2 bloquants en 1ʳᵉ passe, 1 en 2ᵉ (visant le correctif de la 1ʳᵉ), 2 en 3ᵉ (dont
**le même** qu'en 2ᵉ, déclaré clos, plus un défaut **neuf créé par un correctif de revue** : un
`min-height` qui régressait 23 écrans hors périmètre). Signature commune : **du CSS corrigé par
arithmétique, jamais par observation.**

Ce que la série démontre, et qui vaut au-delà de cette US : **une revue multi-axes ne remplace pas un
oracle.** Quatre relecteurs à modèle fort ont refait le même calcul que l'auteur — ils ont donc
trouvé ses erreurs de calcul, ce qui est déjà beaucoup, mais aucun n'a pu voir l'écran. Là où le
dépôt a un oracle (les 4 800 tests), la revue arbitre des jugements ; là où il n'en a pas, elle
**recalcule**, et un recalcul juste sur une prémisse invérifiable reste invérifiable.

Le geste correct n'est pas une 4ᵉ passe : c'est de **nommer l'absence d'oracle comme une dette**,
avec un critère de fin observable (`DETTE-086` : trois captures annexées à la fiche de recette). Un
aveu en prose dans un tracker ne survit ni à un `/compact`, ni à un merge, ni à un `grep` ; une ligne
de registre avec marqueur dans le fichier concerné, si. Corollaire de pilotage : **avant d'ouvrir une
US dont le livrable est visuel, vérifier qu'on peut le rendre** — c'est un prérequis de poste, au
même titre qu'un venv qui marche.

**37. Un marqueur de dette peut faire passer un bloquant pour une aggravation réglementaire.**
E16US006 a posé une clé étrangère **nue** vers `tournoi.id`, commentée `# DETTE-001` aux deux bons
endroits — application impeccable de la procédure d'aggravation du registre. Les quatre axes de
grille l'ont lue ainsi et n'ont rien relevé de bloquant ; l'un d'eux a même relevé, à juste titre,
que la **ligne du registre** n'avait pas été élargie. Aucun n'a demandé si la FK devait être nue.

Le mécanisme est intéressant parce qu'il n'a rien d'une inattention : le marqueur **répond d'avance**
à la question « pourquoi ce raccourci ? », et un relecteur qui trouve une réponse cohérente à
l'endroit prévu passe à la suite. La dette assumée est un dispositif de confiance ; ce qui a manqué
ici, c'est que la table en question — une ligne, sans descendance, créée au premier réglage et jamais
retirée — n'était pas de la même famille que la descendance non tranchée du registre, et que le
raccourci **cassait un cas utilisateur maintenant** (`CLAUDE.md` § Dette : ce n'est alors plus de la
dette, c'est un bloquant).

Ce qui l'a trouvé : l'axe adversarial, **à l'exécution**, avec une baseline sur le même code (`DELETE`
d'un brouillon sans identité → 204 ; avec identité → 500). Aucune lecture ne l'aurait produit, parce
que la lecture menait au marqueur et que le marqueur était bien écrit.

Deux conséquences déjà portées : la section *Détail* de `DETTE-001` dit désormais que la procédure
d'aggravation « dit quoi faire d'une FK qu'on **choisit** de laisser nue, et ne dispense pas de se
demander si on doit la laisser nue » ; et la revue confirme, pour la deuxième fois consécutive
(cf. n° 36), que **l'axe D ne se raccourcit pas** — 4 axes de grille, 10 majeurs pertinents, zéro
bloquant.

**38. Un durcissement qui n'est pas attaqué déplace le trou au lieu de le fermer.**
La 2ᵉ passe d'E16US006 a rendu **zéro bloquant et seize majeurs — treize distincts** une fois les
convergences fusionnées —, dont cinq portaient sur des correctifs de la 1ʳᵉ. Le motif est constant : chaque durcissement avait été écrit **contre les
exemples du rapport précédent**, donc il fermait exactement ces exemples-là et rien d'autre. La
denylist SVG en est le cas d'école — élargie à SMIL, aux entités et aux références externes, elle
restait écrite sur des balises **non préfixées**, si bien que `<svg:script>` franchissait le tout,
*y compris les quatre formes que la toute première rédaction attrapait déjà*. Le durcissement avait
mathématiquement **réduit** la couverture réelle.

Ce qui distingue les remarques qui ont tenu de celles qui se sont effondrées n'est ni l'axe ni la
sévérité : c'est **l'exécution**. Les huit majeurs de l'axe D ont tous été obtenus en déposant des
fichiers, en instrumentant `setAttribute`, en posant des mutants — jamais en lisant. Les axes de
grille, qui lisaient, ont trouvé les défauts *documentaires* (une ligne d'ADR fausse, un marqueur non
inscrit, une procédure commentée au lieu d'être amendée) et les ont trouvés très bien ; aucun n'a vu
qu'un préfixe de deux caractères annulait la barrière.

Trois gestes en sont tirés, tous portés dans le dépôt plutôt qu'en prose :
- **tout durcissement porte désormais son corpus d'ACCEPTATION**, pas seulement son corpus
  d'attaque. La 2ᵉ rédaction refusait un texte accentué échappé, une bannière `&copy;`, un
  `<use href="#symbole">` et — comble — le bloc `<!ENTITY ns_extend>` qu'Illustrator écrit dans le
  `<!DOCTYPE>` qu'on venait d'accepter *au motif qu'Illustrator le produit*. Un refus injustifié
  casse le CA aussi sûrement qu'une acceptation de trop ;
- **on n'ajuste jamais un contrôle pour accommoder un test.** `IEND` avait cessé d'être exigée en
  fin de fichier parce qu'un test de poids bourrait *après* la fin ; vingt octets suffisaient alors
  à reconstruire un polyglotte. Le bourrage a été déplacé, la contrainte rendue au code ;
- **une assertion qui décrit une preuve doit être exécutée pour la prouver.** Trois assertions de la
  1ʳᵉ correction ne pouvaient pas échouer — un 404 rendu par la disparition du tournoi et non par la
  cascade, une médiane de clarté qui ne détectait qu'un dépassement de 100 %, un `textContent` qui
  n'inclut jamais un `alt`. Les trois étaient écrites en toutes lettres comme la moitié qui compte.

**39. Trois passes, trois rédactions du même contrôle, et deux d'entre elles ont RÉDUIT la
couverture — le seul geste qui ait jamais fermé un trou est l'exécution.**
La denylist SVG d'E16US006 a été écrite quatre fois. À chaque passe, la rédaction suivante était
composée **en lisant le rapport précédent**, donc contre ses exemples : la 2ᵉ a fermé `<script>` et
`javascript:` littéraux mais restait aveugle aux préfixes de namespace, si bien qu'elle couvrait
*moins* que la 1ʳᵉ ; la 3ᵉ a fermé `<svg:script>` mais a exigé `[a-z]` en tête de préfixe, laissant
passer `<_x:script>`, et a cessé de refuser les entités sans se mettre à les développer — deuxième
rétrécissement. Deux fois sur trois, « durcir » a diminué la protection.

Ce qui a fini par fonctionner n'est pas une meilleure regex, c'est un **changement de méthode**, et
il tient en trois gestes, tous portés dans le dépôt :
- **écrire le motif contre la grammaire, pas contre les exemples.** `_PREFIXE_XML` ne dit plus quels
  caractères un préfixe peut porter, il dit « tout ce qui précède un `:` » ; la clause de référence
  externe ne s'ancre plus sur `<use>`/`<image>` mais sur **toute valeur d'`href`**. Un motif qui
  énumère se trompera encore ; un motif qui délègue au nom **local** ne peut plus être contourné par
  un préfixe ;
- **balayer toutes les lectures du fichier**, pas ses octets. Entités et références de caractère sont
  deux façons d'écrire la même chaîne, elles se combinent, et le parseur les résout toutes avant
  d'interpréter quoi que ce soit. `_lectures_possibles` matérialise cela ;
- **tout durcissement porte son corpus d'acceptation**, exécuté sur des exports réels — les trois SVG
  du dépôt compris.

Corollaire de pilotage, à lire avec la leçon n° 38 : **le nombre de passes n'est pas la mesure de la
qualité d'une revue ; la proportion de remarques obtenues par exécution l'est.** Sur les trois passes,
tous les défauts structurels — le bloquant, les cinq trous déplacés de la 2ᵉ, les six de la 3ᵉ — ont
été trouvés en déposant des fichiers, en instrumentant `setAttribute`, en posant des mutants ou en
forçant une sonde SQL. Aucun ne l'a été en lisant. Les axes de grille, eux, ont trouvé ce que
l'exécution ne montre pas : une ligne d'ADR fausse trois fois de suite, un marqueur de dette non
inscrit, une procédure commentée au lieu d'être amendée, et un CA qui ne disait plus ce que le code
faisait. **Les deux moitiés sont nécessaires, et elles ne se remplacent pas.**

## Passe du 30/08/2026 (`E16US007`) — ce que ce lot ajoute au constat

**Trois enseignements, et le dernier est le plus utile.**

**1. La porte mécanique a rattrapé une mesure approchante de l'auteur.** Le front avait été validé
avec `npx tsc --noEmit` au lieu de `npm run typecheck` (= `tsc -b`) : configurations différentes,
donc `noUncheckedIndexedAccess` non appliqué aux fichiers de test. Deux erreurs bloquantes, invisibles
jusqu'à l'étape 0.5. C'est le cas d'école de la **décision 1 d'ADR-0013** (« une commande approchante
n'est pas la même mesure ») et il coûte un aller-retour d'agent complet — soit plus cher que la
commande qu'il prétendait éviter.

**2. Les deux bloquants venaient du RELIQUAT — mais pas « tous les défauts de fond », et la
première rédaction de ce paragraphe s'arrangeait.** ⚠️ **Corrigé en 2ᵉ passe, axe C2**, qui a
recompté : le décompte honnête est **2 bloquants sur 2** et **5 majeurs sur 10** imputables au
reliquat. Le volet exports en porte **trois** — le CA « audit » déclaré caduc à tort (défaut de
**cadrage**, le plus coûteux du lot), les types MIME réénumérés à la main, et la dérivation
intestable — **plus le seul défaut de sécurité**, l'injection de formule CSV (CWE-1236) dans
`infrastructure/tableur/`, qui est du code purement E16US007 et que la 1ʳᵉ rédaction avait déplacé
hors de son volet.

⚠️ **C'est le fait le plus instructif de la passe, et il porte sur ce fichier même** : l'auteur est
la partie relue **et** le rédacteur des métriques. Une revue ne mesure rien si son compte rendu est
écrit par l'intéressé sans être relu — c'est pourquoi la procédure joint les rapports bruts en
annexe, et pourquoi cette ligne existe. Le raccourci n'était pas un mensonge, c'était une
généralisation flatteuse qui a survécu à sa propre vérification.

**3. La leçon de pilotage tient quand même, sur le décompte corrigé.** Les 2 bloquants et 5 des 10
majeurs viennent d'un reliquat d'une **autre** US
(`E16US010`, élargissement d'une frontière de rôles) greffé sur le lot parce qu'il « ne coûtait
qu'une ligne » : `key` React manquante, aucune fiche fonctionnelle, deux fiches contredites, `stories/`
non reversé, ADR-0050 laissé au passé, deux tests désarmés en silence, pas de confirmation.

⚠️ **Le motif est net et vaut au-delà de ce lot** : un changement **petit en lignes** peut être
**gros en surface documentaire** — une frontière de rôles touche un ADR, deux fiches de recette, un
CA, une dette et une couverture de test. Le volume du diff n'en dit rien. Ce reliquat méritait son
cadrage et sa propre US ; l'agréger a coûté plus cher que de le prendre à part.

**4. L'axe D reste le plus productif, pour la 3ᵉ passe consécutive** — et cette fois il a trouvé le
défaut qu'aucune grille ne pouvait attraper : un **CA déclaré caduc à tort**. L'auteur avait jugé sur
le serveur (`ServiceAudit.lister` sans restriction de statut) un CA écrit du point de vue de
l'organisateur ; `grep` sur `frontend/src` montre qu'**aucun écran ne consomme la route**. La
conclusion fausse avait été inscrite dans **quatre artefacts durables**, dont un livrable rendu au
commanditaire. Aucune règle de grille ne demande « le CA que tu déclares caduc est-il caduc **pour
l'utilisateur** ? » — seule une lecture adversariale le pose.

### 2ᵉ passe — ce que la relecture des correctifs a rendu

**Elle a payé, et largement.** 1 bloquant et 16 majeurs sur un commit de correctifs de 36 fichiers,
dont **trois régressions créées par les correctifs eux-mêmes** :

1. `BoutonConfirme` reçu **sans `disabled`** : la garde anti-double-écriture du seul acte destructif
   de l'écran a été perdue en remplaçant un `<button disabled={isPending}>`. Les quatre autres
   appelants du dépôt passent les deux props.
2. Deux corrections documentaires « partout » **appliquées à l'artefact visible et pas à son
   jumeau** : le CA `audit` corrigé dans le récit du tracker mais pas dans sa table 900 lignes plus
   bas, ni dans l'epic ; deux blocs de `docs/fonctionnel/E16US010.md` remplacés **sur leur première
   ligne**, laissant des fragments orphelins qui réaffirmaient le faux.
3. Le compte rendu de revue lui-même **s'arrangeait** : « tous les défauts de fond viennent du
   reliquat » était faux — le seul défaut de sécurité du lot (injection CSV) est du code purement
   E16US007. Relevé par l'axe C2, sur ce fichier même.

⚠️ **Le point 3 est structurel, pas anecdotique** : l'auteur est la partie relue **et** le rédacteur
des métriques. Sans une passe qui relit aussi le compte rendu, cette ligne mesure ce que l'auteur
veut bien y lire.

**Conseil de conduite, reversé de l'axe D** : *une correction faite « partout » se termine par un
`grep`, pas par une relecture.* `grep -rn "audit en cours"`, `grep -rn DETTE-090`,
`grep -rn "CSV (tableur)"` ont rendu en trente secondes ce que deux relectures avaient manqué.
