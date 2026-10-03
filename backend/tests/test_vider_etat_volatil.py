"""`vider()` des cinq registres en mémoire que la restauration oublie (E11US006, CA 5).

Le câblage de l'ensemble est éprouvé par `test_sauvegardes_api` (scoreur et idempotence) ; ici,
chaque registre tient sa propre promesse.
"""

from __future__ import annotations

import datetime
from typing import cast

from domain.ecran import PriseDeControle
from domain.poste import PosteId
from domain.scoreur import ScoreurId
from infrastructure.idempotence import RegistreIdempotence
from infrastructure.postes import (
    PosteSessionStore,
    RegistreConsignesMemoire,
    RegistrePresenceMemoire,
)
from infrastructure.scoreurs import ScoreurSessionStore

_POSTE = PosteId(1)


def test_sessions_de_poste() -> None:
    store = PosteSessionStore()
    jeton = store.ouvrir(_POSTE)

    store.vider()

    assert store.poste_de(jeton) is None


def test_sessions_de_scoreur() -> None:
    store = ScoreurSessionStore()
    jeton = store.ouvrir(ScoreurId(1))

    store.vider()

    assert store.scoreur_de(jeton) is None


def test_consignes_d_ecran() -> None:
    registre = RegistreConsignesMemoire()
    registre.poser(_POSTE, cast(PriseDeControle, object()))  # le registre n'inspecte pas la prise

    registre.vider()

    assert registre.toutes() == {}


def test_presence_des_postes() -> None:
    registre = RegistrePresenceMemoire()
    registre.enregistrer(_POSTE, datetime.datetime(2026, 10, 3, tzinfo=datetime.UTC), None)

    registre.vider()

    assert registre.derniere_activite(_POSTE) is None


def test_idempotence() -> None:
    registre = RegistreIdempotence()
    registre.executer("volee-1", lambda: "premiere")

    registre.vider()

    assert registre.executer("volee-1", lambda: "rejouee") == "rejouee"
