# ADR-0117 — Le barème de duel est un réglage d'étape, aux surcharges par arme explicites, verrouillé au premier tir

- **Statut** : Accepté
- **Date** : 2026-10-01
- **US** : E01US011
- **Décideurs** : Organisateur / Architecte
- **Amende** : [ADR-0049](0049-saisie-et-scoring-des-duels.md) §2 (la résolution « par (phase,
  arme) » que son titre annonçait devient vraie) et §4 (le barème reste non stocké avec le tir, ce
  qui impose le verrou décrit ici).

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
   **poulies au cumul**, règle d'arme et non choix FFTA/club. La reconnaissance par libellé ne
   survit que là, en **pré-remplissage** visible et corrigeable.
5. **Verrou au premier tir** : changer le barème d'une étape — y compris le retirer ou en poser un
   sur une étape qui n'en avait pas — est **refusé** (`BaremeDuelVerrouille`, 409) dès qu'une
   phase de cette étape a un tir enregistré, **dans n'importe quel créneau**.

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
- **−** Il ne ferme pas le cas résiduel d'ADR-0049 « mutation d'arme » : changer la catégorie d'un
  archer en cours de tableau change toujours son barème. Même remède attendu, le gel du classement.
- **=** `DETTE-054` n'est **pas** élargie : `ReglageBaremeDuelDTO` est défini une fois dans
  `api/v1/phases.py` et importé par `api/v1/formats.py`.

## Porté dans le code par

- `backend/domain/duel.py` — `ReglageBaremeDuel` (`pour`, `preset_ffta`, `preset_club`),
  `SurchargeArme` (`designe`), `_poulies_au_cumul`.
- `backend/domain/contrat_phase.py` — `TYPES_A_BAREME_DE_DUEL`, dérivé de `_CONTRATS`.
- `backend/domain/phase.py` — `Phase.bareme_duel` et sa garde de type dans `__post_init__`.
- `backend/domain/deroule_etape.py` — `EtapeDeroule.bareme_duel`, recopié par `instancier`.
- `backend/domain/format_tournoi.py` — `ModelePhase.bareme_duel`, traduit par `pour_tournoi` et
  `d_etape`.
- `backend/application/saisie_duels.py` — `_bareme_du` (réglage, sinon résolveur) et
  `_reglage_de`, lu une fois par opération ; `bareme_de` reçoit le réglage de `poules.py`,
  `suisse.py` et `colline.py`.
- `backend/application/phases.py` — `ServicePhases.modifier` (verrou) et `_a_deja_un_tir`.
- `backend/infrastructure/db/repositories/moteur.py` — `_politiques_json` (écriture, deux
  appelants) et `_lire_bareme_duel` (deux lectures).
- `backend/api/v1/phases.py` — `ReglageBaremeDuelDTO`, importé par `backend/api/v1/formats.py`.
