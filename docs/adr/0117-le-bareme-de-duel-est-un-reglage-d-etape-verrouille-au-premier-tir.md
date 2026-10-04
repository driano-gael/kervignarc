# ADR-0117 — Le barème de duel est un réglage d'étape, aux surcharges par arme explicites, verrouillé au premier tir

- **Statut** : Accepté
- **Date** : 2026-10-01
- **US** : E01US011
- **Décideurs** : Organisateur / Architecte
- **Amende** : [ADR-0049](0049-saisie-et-scoring-des-duels.md) §2 (la résolution « par (phase,
  arme) » que son titre annonçait devient vraie) et §4 (le barème reste non stocké avec le tir, ce
  qui impose le verrou décrit ici).
- **Amendé** : 2026-10-03, E01US027 — §8 (barème des derniers tours), §4, §5, §7 et Conséquences.

## Contexte

ADR-0049 a livré le scoring de duel avec un **résolveur injecté** à défaut FFTA, câblé en dur au
composition root : sets à 6 points, et cumul pour toute arme dont le libellé contient « poulie » ou
« compound ». Son titre promettait une résolution « par (phase, arme) » ; sa section « Porté dans le
code par » constatait que seule l'arme comptait. Le domaine connaissait déjà `preset_club` (sets à
4 points), qu'aucun appelant n'utilisait.

E01US011 rend le barème **réglable**. Le cadrage du 01/10/2026 a tranché trois points avec le
commanditaire : le barème se règle **par phase** (un tableau principal FFTA et une repasse club
peuvent coexister) ; les poulies passent par une **surcharge explicite** et non plus par une
devinette sur le libellé ; il n'y a **pas de bibliothèque** de barèmes hors format.

Une contrainte vient d'ADR-0049 §4 : **le barème n'est pas stocké avec le tir**, il est recalculé à
chaque lecture. Tant qu'il ne dépendait que de l'arme, c'était sans risque. Réglable, il devient un
moyen de **réinterpréter en silence** des duels déjà validés : passer de 6 à 4 points en plein
tableau peut faire basculer un vainqueur.

## Décision

1. **`ReglageBaremeDuel`** (`domain/duel.py`) : un barème **par défaut** et des **surcharges par
   arme**. L'arme se compare sans casse ni espaces de bord, **jamais par inclusion** (« Poulies » ne
   désigne pas « Arc à poulies »). Deux surcharges pour la même arme sont refusées.
2. **Porté par l'étape** (`EtapeDeroule.bareme_duel`), donc par le tournoi et non par le créneau
   ([ADR-0076](0076-un-deroule-defini-une-fois-un-avancement-par-depart.md)). Il voyage avec
   le format (`ModelePhase.bareme_duel`) et se range à la racine du JSON `config`, **sans
   migration**. Seuls les types de `TYPES_A_BAREME_DE_DUEL` l'acceptent — ensemble **dérivé** du
   contrat de phase (joué par un service, décor en duels) : élimination directe, poules, suisse,
   colline.
3. **Résolution** : le réglage de la phase s'il existe, sinon le `ResolveurBaremeDuel` injecté, qui
   reste le défaut FFTA. Une étape écrite avant cette US se relit « non réglée » et joue exactement
   ce qu'elle jouait.
4. **Presets** *FFTA officiel* (sets à 6) et *format club* (sets à 4) : tous deux posent les
   **poulies au cumul**, règle d'arme et non choix FFTA/club. Ils vivent **au front**, seul
   appelant : la reconnaissance par libellé n'y sert qu'au **pré-remplissage**, visible et
   corrigeable. Ils **attendent** les armes chargées, et la fiche signale un arc à poulies sans
   surcharge comme une surcharge sans catégorie. Le domaine ne porte que la structure.
   *(E01US027)* Le *format club* pose en plus le barème des **½ finales** (§8) : sets à 6, poulies
   au cumul — le référentiel §10.1 sans retouche à la main. Le *FFTA officiel* n'en pose pas.
5. **Verrou au premier tir** : changer le barème d'une étape — y compris le retirer ou en poser un
   sur une étape qui n'en avait pas — est **refusé** (`BaremeDuelVerrouille`, 409) dès qu'une
   phase de cette étape a un tir enregistré, **dans n'importe quel créneau**. L'égalité est
   **sémantique** : l'ordre des surcharges et le seuil ignoré au cumul n'en font pas partie.
   *(E01US027)* Elle couvre le réglage **entier** : poser, retirer ou changer le barème des
   derniers tours, ou son nombre de tours, est un changement comme un autre.
6. **Égalité au seuil** *(arbitrage du 01/10/2026, revue)* : deux archers au seuil **dans la même
   manche** — 4-4 au format club — se départagent au **barrage**, comme 5-5 (§7). Au barème FFTA
   le cas est impossible ; le preset club le rendait atteignable, et le mieux placé gagnait. Un
   seuil hors d'atteinte reste licite : personne au seuil, le meneur gagne (2ᵉ passe).
7. **L'arme d'une catégorie se fige quand la changer changerait un barème tiré** *(arbitrage
   reposé en 2ᵉ passe)* : refus (`ArmeDeCategorieVerrouillee`, 409) dès que, pour une étape **déjà
   tirée — réglée ou non** —, l'ancienne et la nouvelle arme ne résolvent pas le même barème. La 1ʳᵉ
   rédaction exemptait les étapes non réglées : faux, le défaut bascule sets/cumul au libellé.
   *(E01US027)* « Le même barème » s'entend des **deux** portées : une arme que seul le barème des
   derniers tours distingue se fige aussi.
8. **Barème des derniers tours** *(E01US027, cadrage du 03/10/2026)* : un réglage peut porter un
   `BaremeDesDerniersTours` — un nombre **K ≥ 1** et un réglage complet (défaut et surcharges), qui
   n'en porte pas lui-même un second. Un duel le tire s'il se joue dans l'un des **K derniers
   tours** de sa phase. Le compte se fait **à rebours** (`tours_restants`, 0 au dernier tour) et
   **par format** : tour de tableau contre `Tableau.nb_tours` ; tour de rencontre contre le nombre
   de tours **de sa poule** ; ronde contre les rondes **jouables** (le réglage, borné par l'effectif) ; manche contre `nb_manches`. Compter
   depuis la fin plutôt que nommer « ½ finale » vaut pour les quatre formats, dont seul le tableau
   nomme ses tours ; le front traduit K en « ½ finales » au tableau. La **petite finale** et tout
   match de classement suivent le barème de leur tour, sans cas particulier.

## Alternatives écartées

- **Stocker le barème avec le tir.** Plus juste — un tir porterait la règle sous laquelle il a été
  joué —, mais c'est une migration de la table `duel` et la réécriture d'ADR-0049 §4, pour un besoin
  que personne n'a exprimé : changer de barème **en cours** de tableau. Le verrou suffit.
- **Un réglage au tournoi.** Écarté par le commanditaire : il ne couvre pas un tournoi qui mélange
  les formats.
- **Garder la devinette et ne rendre réglable que le défaut.** Écarté par le commanditaire : une
  arme mal orthographiée basculait en sets sans que rien ne le montre.
- **Une bibliothèque de barèmes nommés.** Écartée : les formats du patrimoine
  ([ADR-0060](0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md)) emportent déjà leur réglage.

## Conséquences

- **+** La composante « phase » d'ADR-0049 est tenue, au seul point de résolution existant
  (`ServiceSaisieDuels.bareme_de`), que tableau, poules, suisse et colline partagent déjà.
- **+** Rétro-compatible sans migration ni reprise de données.
- **−** La devinette sur le libellé **survit** sur toute phase non réglée. C'est le prix de la
  rétro-compatibilité ; elle disparaîtra quand l'arme sera un énuméré (E01US018).
- **−** Le verrou est **conservateur** : il compte tout tir enregistré, y compris un vestige que la
  règle de désynchronisation d'ADR-0049 §4 masque déjà. Une étape dont le seul tir est un vestige
  reste verrouillée.
- **−** Il ne ferme pas la route jumelle : **déplacer un archer** vers une catégorie d'une autre
  arme après son duel relit ses duels. Arbitrage : pas de refus, le message de confirmation le dit ;
  `DETTE-118`, remède attendu le gel du classement (E01US017/E12US002).
- **+** *(E01US027)* Le barème club des ½ finales et finales (6 points, référentiel §10.1) est
  exprimable, et posé par le preset : `DETTE-117` est soldée. La résolution prend le **tour** en
  argument **obligatoire** (`pour(arme, tours_restants=…)`) : l'oublier échoue à `mypy`.
- **−** *(E01US027)* En **poules**, toutes contre toutes, le « dernier tour » n'est qu'un ordre de
  calendrier : le réglage s'y applique quand même, par cohérence (arbitrage du 03/10/2026).
- **−** *(E01US027)* Un match de classement (places 5-8…) joué à l'un des K derniers tours suit le
  barème des derniers tours : c'est la conséquence de la règle « par tour », assumée.
- **−** Les presets ont un **miroir** de la reconnaissance des poulies au front (`estPoulies`, de
  `_est_poulies`), dont dépendent aussi les avertissements d'écart : `DETTE-119`.
- **=** `DETTE-054` n'est **pas** élargie : `ReglageBaremeDuelDTO` est défini une fois dans
  `api/v1/phases.py` et importé par `api/v1/formats.py`.

## Porté dans le code par

- `backend/domain/duel.py` — `ReglageBaremeDuel` (`pour`, surcharges rangées, `baremes_pour`) et
  `SurchargeArme` (`designe`) ; `BaremeDesDerniersTours` (`couvre`, §8) ; `BaremeDuel.__post_init__`
  (seuil ramené à 0 au cumul) ; `Duel._resultat_sets` et `_issue_d_egalite` (§6), et la garde de
  `saisir_manche`.
- `frontend/src/shared/phases/baremeDuel.ts` — `presetFfta`, `presetClub`, `estPoulies` (§4),
  `ecartsDArmes` (les deux portées), `derniersToursDepuis` et `libelleDerniersTours` (§8) ; rendus
  par `frontend/src/shared/phases/ReglageBaremeDuel.tsx`, qui retient ses presets tant que `armes`
  vaut `null`.
- `backend/application/verrou_bareme.py` — `VerrouBaremeDuel` (`etape_tiree`, `arme_figee` via
  `_baremes`, les deux portées), qui résout avec le **même** `ResolveurBaremeDuel` que la saisie ;
  une instance, câblée dans bootstrap/composition.py, partagée par les services de phases et de
  catégories.
- `backend/application/categories.py` — `ServiceCategories.modifier` (§7).
- `backend/domain/duel.py` — `memes_baremes`, l'égalité à la casse près que compare le §5.
- `frontend/src/features/saisie-duels/duel.ts` — `mancheNeuveFermee` (§6 : pas de 5ᵉ manche).
- `backend/application/archers.py` — message de `_signaler_changement_categorie` (`DETTE-118`).
- `backend/domain/contrat_phase.py` — `TYPES_A_BAREME_DE_DUEL`, dérivé de `_CONTRATS`.
- `backend/domain/phase.py` — `Phase.bareme_duel` et sa garde de type dans `__post_init__`.
- `backend/domain/deroule_etape.py` — `EtapeDeroule.bareme_duel`, recopié par `instancier`.
- `backend/domain/format_tournoi.py` — `ModelePhase.bareme_duel`, traduit par `pour_tournoi` et
  `d_etape`.
- `backend/application/saisie_duels.py` — `_bareme_du` (réglage, sinon résolveur), qui reçoit
  `tours_restants = tableau.nb_tours - match.tour` de ses six appelants ; le réglage est rendu par
  `_decor`, qui a déjà la phase ; `bareme_de` reçoit le tour des trois formats suivants (§8).
- `backend/application/poules.py` — `_photo` : dernier tour **de la poule**.
- `backend/application/suisse.py` et `backend/application/colline.py` — `_rejouer` : rondes
  jouables et manches.
- `backend/application/phases.py` — `ServicePhases.modifier` (verrou du §5, via `VerrouBaremeDuel`).
- `backend/infrastructure/db/repositories/moteur.py` — `_politiques_json` (écriture, deux
  appelants, via `_reglage_bareme_duel_json`) et `_lire_bareme_duel` (deux lectures, via
  `_vers_reglage_bareme_duel`) ; clé `derniers_tours` absente = pas de barème des derniers tours.
- `backend/api/v1/phases.py` — `ReglageBaremeDuelDTO` (qui embarque `BaremeDesDerniersToursDTO`, à
  plat, sans second niveau), importé par `backend/api/v1/formats.py`.
