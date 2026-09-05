# ADR-0106 — La pose d'une cible appartient à un tour, et le tour suivant se pose seul

- **Statut** : Accepté
- **Date** : 2026-09-05
- **Décideurs** : Organisateur / Architecte
- **Portée** : E03US012 (poser les cibles des tours suivants)
- **S'appuie sur** : [ADR-0048](0048-cote-a-cote-des-duellistes-par-reordonnancement.md) (le plan de
  duels matérialisé et ajustable, dont cet ADR élargit la clé), [ADR-0090](0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md)
  (le tour comme unité d'avancement générique — sans lui, « la pose du tour 2 » n'aurait pas de
  référent), [ADR-0023](0023-moteur-de-placement-glouton-deterministe.md) / [ADR-0049](0049-saisie-et-scoring-des-duels.md)
  (l'appariement **recalculé**, la pose **persistée** : le partage que cet ADR ne touche pas)
- **Voisin** : [ADR-0091](0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md), dont cet
  ADR reprend le **patron de déclencheur** (port neutre, branchement tardif au composition root) et
  respecte la garde de pause

## Contexte

Depuis E03US009, le plan de duels ne pose que le **premier tour**. La conséquence n'était pas
documentée comme une limite de produit, mais elle en est une, et elle est totale : dans
`ServicePilotageTour._duel_a_venir`, la ligne `place = match.tour == 1` rend `cible_attribuee`
**toujours faux** au-delà du tour 1, donc `pret_a_lancer` toujours faux. Passé le premier tour,
**aucun duel n'est jamais prêt à lancer**, et le panneau de routage n'annonce plus aucune cible :
l'organisateur retombe sur le papier pour toute la fin du tableau.

La garde elle-même est **juste** et doit être conservée dans son principe : la pose persistée d'un
archer est celle de son tour 1, et l'annoncer au tour 2 enverrait deux finalistes venus de cibles
distinctes sur l'ancienne butte. Ce n'est pas la garde qu'il faut retirer, c'est la donnée qui lui
manque.

Trois faits ont cadré la décision, tous vérifiés dans le code du jour :

1. **Le moteur n'est pas en cause.** `domain.placement.placer` est un glouton **générique**, sans
   notion de tour. La limite vient de son appelant, qui ne lui passait que
   `paires_du_premier_tour`.
2. **La clé de la table était le blocage.** `placement_tableau` avait pour clé primaire
   `(phase_id, inscription_id)` : elle ne **peut pas** représenter deux poses du même archer, donc
   poser le tour 2 aurait écrasé le tour 1.
3. **Le commentaire qui justifiait la garde était faux.** Il renvoyait à E05US010 « placement
   intégral 1→N » en la disant non livrée. Elle l'est depuis le 31/07/2026 — et ce « 1→N » désigne
   la **profondeur de classement**, pas la pose de cibles. `DETTE-019` avait relevé que le registre
   « attendait une US déjà passée » ; en réalité **aucune US n'a jamais porté ce sujet**.

## Décision

### 1. La pose appartient à un **tour**, et la clé le dit

`placement_tableau` a pour clé primaire `(phase_id, tour, inscription_id)` (migration `0053`). Les
lignes existantes sont reprises en **tour 1** — c'est exactement ce qu'elles étaient. Aucun tournoi
déjà en base ne change d'affichage.

⚠️ **SQLite ne sait pas modifier une clé primaire**, et `batch_alter_table` ne convient pas ici : en
mode batch, Alembic **réfléchit** la table existante et une `PrimaryKeyConstraint` passée en
`table_args` s'y **ajoute** au lieu de la remplacer — SQLAlchemy émet un avertissement et garde
l'ancienne clé, si bien que la migration paraît réussir. La table est donc recréée explicitement.

### 2. Le plan pose **un** tour à la fois, celui qui se joue

`ServicePlacementDuels` charge le décor du **tour à poser** : le plus petit tour portant **au moins
un duel jouable** (`domain.tableau.tour_a_poser`). Un tableau terminé n'en a plus, et garde alors son
dernier tour affiché, pour que le plan de la finale reste consultable.

⚠️ **Ne pas y ajouter de garde « tour entièrement déterminé »**, malgré ce que le nom suggère. La
première rédaction de cet ADR l'affirmait, et le code ne la portait pas : la revue a montré que
l'ajouter **casserait** l'automatisme. Les sous-tableaux de placement portent des matchs nourris par
le **perdant d'un bye**, dont les deux camps restent vides *pour toujours* ; une telle garde rendrait
`None` définitivement. La sûreté ne vient pas de là : elle vient de ce qu'une pose n'est annoncée
que pour le tour auquel elle appartient (décision 1).

**La maille est le tour entier, jamais le duel.** Regrouper les archers suppose de connaître tout
l'ensemble à poser ; poser duel par duel au fil des validations éparpillerait le tour sur le pas de
tir dans l'ordre d'arrivée des résultats.

### 3. Le tableau vient de la **reconstruction**, plus d'une construction locale

`_charger` lisait le classement et remontait son propre arbre par `construire_tableau`. C'était une
**seconde** implémentation de l'ensemencement, à côté de `ServiceSaisieDuels.reconstruire` — un
commentaire du fichier affirmait leur parité, et cette parité avait déjà lâché une fois (E05US024 :
un plan de 8 poses pour un tableau de 4). Surtout, seule la reconstruction **rejoue les duels
validés**, donc seule elle connaît les occupants d'un tour ≥ 2.

Conséquence assumée : `ServicePlacementDuels` n'injecte plus `seeding`, `byes`, `routing`,
`registre` ni le service de classement. Ces politiques sont résolues **par la reconstruction**, en
un seul exemplaire.

### 4. Le tour suivant se pose **seul**, en complétant — jamais en régénérant

Arbitrage du commanditaire (05/09/2026) : dès que le tour est déterminé, ses duellistes reçoivent
une cible **sans geste**, puis restent ajustables au glisser-déposer.

L'acte automatique **complète les trous**, il ne régénère pas — et surtout il ne s'exécute
**qu'une fois par tour** : dès que le tour porte une pose, il ne touche plus à rien.

⚠️ **La première rédaction affirmait que « compléter » était inoffensif. C'était faux, et la revue
l'a prouvé par sonde.** Une **réserve est un trou** : compléter reposait d'office l'archer que
l'organisateur venait délibérément d'écarter. C'est exactement l'objection qui fait exclure le tour 1
ci-dessous — elle valait identiquement aux tours qu'on n'avait pas exclus. Le trou avait été déplacé,
pas fermé. D'où la garde d'unicité, qui est ce qui rend vraies les deux propriétés attendues :

- une validation de duel ne peut jamais **écraser** un ajustement manuel de l'organisateur ;
- l'acte est **idempotent** : un tour déjà posé n'est plus touché, aucune écriture n'est émise.

⚠️ **Ce que la décision ne fait donc PAS** : reposer un tour qu'une correction périme. La première
rédaction le promettait ; outre qu'elle reposait sur la complétion répétée, **aucun chemin ne la
déclencherait** — un résultat de duel ne se corrige pas (`DuelVerrouille`), et la correction d'un
score de *qualification* ne signale pas le poseur. La repose d'un tour périmé est donc un **geste de
l'organisateur** (« Générer le plan »), et c'est écrit tel quel dans la recette.

Deux exclusions, toutes deux nécessaires :

- **le tour 1** garde son geste explicite (« Générer le plan »). Le compléter d'office reposerait un
  archer que l'organisateur a délibérément laissé en réserve ;
- **une phase en pause** ne prépare pas la butte d'après (ADR-0091) : un arrêt programmé éteint la
  salle, et poser les cibles du tour suivant ferait annoncer une butte à des archers qu'on vient
  d'arrêter.

### 5. Le déclencheur est un **port neutre**, branché tardivement, sur **deux** chemins

2ᵉ occurrence du patron d'ADR-0091 (`application.gel_de_pause`), **recopié plutôt qu'abstrait** — le
remède structurel attend une 3ᵉ occurrence réelle. Le port vit dans un module sans dépendance de
service : `ServicePlacementDuels` dépend déjà de `ServiceSaisieDuels`, et brancher dans l'autre sens
à la construction fermerait le cycle.

⚠️ **TROIS chemins, et pas deux** : un tour s'achève par la validation d'un duel **ou** par un
forfait en duel (walkover, qui tranche sans qu'aucun score soit saisi) ; et la **reprise** d'une
phase (`ServicePhases.reprendre`) est le seul chemin qui rattrape la pose sautée pendant une pause.

Ce troisième chemin manquait à la première livraison, et son absence était un **bloquant** : un arrêt
programmé coupe le déroulé **à la fin d'un tour** (ADR-0091), donc précisément à l'instant où le tour
suivant devrait être posé — et la pose est alors sautée, la phase étant en pause. Il ne reste ensuite
plus aucun duel amont à valider : sans signal à la reprise, la pose n'aurait **jamais** lieu, et la
salle repartirait sans cibles. La fonctionnalité s'annulait dans sa configuration nominale.

⚠️ **La pose est un effet système, jamais un geste de rôle.** Deux de ces trois chemins sont ouverts
au **scoreur** (valider un duel, déclarer un forfait), alors que toutes les routes d'écriture du plan
de duels sont `exiger_admin`. Ce n'est pas un élargissement de privilège : aucune donnée du client
n'atteint la pose — le tour, la cible et le couloir sont dérivés serveur —, et l'acte ne peut que
**remplir un tour vide**, jamais déplacer une pose existante.

Le mode de panne de `DETTE-028` vaut pour les trois : un branchement oublié rend la pose muette sans
qu'aucune ligne rougisse — d'où un test qui les nomme un par un.

Le signalement **ne lève jamais** : le résultat est déjà persisté, et un 500 ici ferait ressaisir un
duel validé. Une cible manquante se rattrape d'un clic, pas une feuille de marque.

### 6. Ce que la décision **ne** règle pas

`DETTE-021` — le feu vert dit « prêt » sans vérifier que les deux duellistes sont sur la **même**
cible — n'est pas corrigée ici, et cet ADR l'**aggrave** : le défaut ne valait qu'au tour 1, il vaut
désormais à tous les tours. La ligne du registre est élargie, pas contournée.

## Conséquences

- **La garde tour-1 tombe aux TROIS sites qui la portaient** — `ServicePilotageTour._duel_a_venir`,
  `ServiceRoutage._pose_a_annoncer` et `actionDuel` (front). Elle n'est pas supprimée mais
  **généralisée** : la comparaison n'est plus `match.tour == 1` mais `match.tour == <tour posé>`. Le
  principe de sûreté est intact — une pose n'est annoncée que pour le tour auquel elle appartient.
  ⚠️ Le **quatrième** site que `DETTE-019` énumérait, `partitionner` (front), n'en portait que la
  **justification écrite** : il partitionne sur l'issue, son corps est inchangé, seul son commentaire
  devenu faux a été corrigé. Le dire est le sujet même de la règle 12 — un module nommé sans porteur
  se lit comme une preuve (ADR-0017).
- ⚠️ **Les deux sites front étaient le vrai risque.** Lever la garde côté serveur sans les toucher
  laissait l'écran annoncer une limite disparue (« les cibles ne sont posées qu'au premier tour »),
  **sans qu'aucun test rougisse** : la couture serveur ↔ front n'est tenue par aucun test commun.
- **`DETTE-019` est résorbée** sur son point de fond (la garde tour-1, présente en quatre
  formulations). La jumellerie résiduelle entre `ServiceRoutage` et `ServicePilotageTour`
  (`_sources_en_attente`) reste, et reste inscrite.
- **La route `regenerer` ne touche plus que le tour en cours de pose**, jamais un tour déjà tiré.
  C'est une garantie neuve : auparavant elle purgeait le plan de la phase entière.
- **Pas de sélecteur de tour** à l'écran : il rend le plan du tour en cours, qu'il **nomme**.
  Consulter un tour passé ou à venir est un confort écarté du périmètre, faute de besoin énoncé.
- **E16US013** (lancement automatique ou manuel) redevient utile : c'est le blocage que son cadrage
  avait mis au jour, et la raison d'être de cette US.

## Porté dans le code par

- `backend/domain/tableau.py` — `paires_du_tour` (décision 2 ; elle remplace l'ancienne fonction
  bornée au premier tour) et `tour_a_poser`, fonction **pure** qui porte à elle seule « quel tour
  peut être posé », y compris le `None` d'un tableau terminé.
- `backend/infrastructure/db/models.py` — `PlacementTableauORM.tour`, dans la clé primaire
  (décision 1). L'ordre des colonnes **est** l'ordre de la clé, dont dépendent les `session.get`.
- `backend/migrations/versions/0053_placement_tableau_par_tour.py` — la reprise en tour 1 et la
  recréation explicite de la table (décision 1, y compris l'avertissement sur `batch_alter_table`).
- `backend/domain/ports.py` — `PlacementTableauRepository` : les quatre gestes portent le tour
  (décision 1). ⚠️ `par_phase` **n'y est pas** : cette lecture (toutes poses d'une phase) appartient
  à un autre port, déclaré dans `application/formats.py`, qui pose une question distincte.
- `backend/infrastructure/db/repositories/moteur.py` et `backend/infrastructure/memory/repositories.py`
  — `PlacementTableauRepositorySQL` / `InMemoryPlacementTableauRepository` : `par_phase_et_tour`,
  et `par_phase` conservée pour le seul port des formats.
- `backend/application/placement_duels.py` — `_Contexte.tour` et `_charger` (décisions 2 et 3),
  `PlanDeDuels.tour`, `poser_le_tour_courant` (décision 4 : la garde d'unicité et les deux
  exclusions) et `_completer` ; `_refuser_si_le_tour_a_tire`, qui refuse `regenerer` (409) sur un
  tour dont un duel porte déjà un tir — la justification « au tour 1 aucun score n'existe » étant
  tombée avec cette décision.
- `backend/application/pose_du_tour.py` — `PoseurDeTour` et `DeclencheurPoseDeTour` (décision 5).
- `backend/application/saisie_duels.py` (`brancher_poseur_de_tour`, `_signaler_validation_de`,
  `numeros_avec_tir`), `backend/application/forfaits.py` (`declarer_en_duel`, `annuler_en_duel`) et
  `backend/application/phases.py` (`reprendre`) — les **trois** chemins de la décision 5.
- `backend/bootstrap/composition.py` — le branchement tardif, en un seul endroit visible
  (décision 5) ; et la disparition des cinq dépendances de la décision 3.
- `backend/application/pilotage_tour.py` (`_poses_du_tour_pose`, `_duel_a_venir`) et
  `backend/application/routage.py` (`_PlanLu.tour`, `_pose_a_annoncer`, `_plan_lu`) — la garde
  généralisée, côté serveur.
- `frontend/src/features/feu-vert/etat.ts` (`actionDuel`) — la garde généralisée côté front, et le
  seul site front qui la portait. Il distingue aussi « aucun plan lisible » (pas de gabarit → renvoi
  au plan de duels, CA d'E16US008) de « tour pas encore posé » : les confondre affichait
  « attendez le tour précédent » sur un tour 1, qui n'en a pas.
- `frontend/src/features/duels/Duels.tsx` — le libellé du tour posé (décision 2 : l'écran le nomme).
