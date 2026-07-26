"""Tests de l'abstraction Participant (E13US001) — dérivés du CA, pas de l'implémentation.

Règle 9 : ces cas dérivent du CA d'E13US001 (`stories/E13-equipes.md`) et d'ADR-0028 — un match
oppose des **participants** (archer **ou** équipe), que le moteur traite sans jamais brancher sur
leur genre. Value object pur : aucune base, aucun framework.
"""

from __future__ import annotations

from domain.participant import GenreParticipant, Participant


def test_participant_individuel_est_un_archer() -> None:
    # CA : « un tournoi individuel est le cas où chaque participant EST un archer ».
    p = Participant.individuel(42)
    assert p.genre is GenreParticipant.INDIVIDUEL
    assert p.ref_id == 42


def test_participant_equipe_est_une_equipe() -> None:
    # CA : « un Participant est soit un archer individuel soit une équipe ».
    p = Participant.equipe(7)
    assert p.genre is GenreParticipant.EQUIPE
    assert p.ref_id == 7


def test_deux_participants_egaux_ssi_meme_genre_et_meme_reference() -> None:
    # L'égalité par identité permet au moteur de reconnaître un vainqueur parmi les deux camps.
    assert Participant.individuel(1) == Participant.individuel(1)
    assert Participant.individuel(1) != Participant.individuel(2)
    # Même référence numérique mais genre différent : archer 3 et équipe 3 sont distincts.
    assert Participant.individuel(3) != Participant.equipe(3)


def test_participant_est_hashable_et_immuable() -> None:
    # Le moteur place des participants dans des ensembles/clés (podium, camps) : hashable requis ;
    # `frozen` garantit qu'un participant reporté dans l'arbre ne peut pas muter sous ses pieds.
    ensemble = {Participant.individuel(1), Participant.individuel(1), Participant.equipe(1)}
    assert ensemble == {Participant.individuel(1), Participant.equipe(1)}
